"""Lectura de espectros y cubos FITS para M1.

Un cubo no se analiza directamente como imagen dentro de M1: se extrae un
espectro 1-D de un píxel o apertura, se conserva WCS/procedencia y se exporta a
un .dat persistente. Desde ese punto comparte exactamente la ruta científica de
los datos de antena única.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import math
import re
from typing import Any

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy import units as u

from czspec.paths import FITS_IMPORT_OUTPUT_DIR
from czspec.logic.source_metadata import C_KMS

@dataclass(frozen=True)
class FitsHDUInfo:
    index: int
    name: str
    shape: tuple[int, ...]
    ndim: int
    spectral_numpy_axis: int | None
    celestial: bool
    bunit: str


def _spectral_axis_from_header(header, ndim: int) -> int | None:
    # FITS axis 1 corresponde al último eje NumPy.
    for fits_axis in range(1, ndim + 1):
        ctype = str(header.get(f"CTYPE{fits_axis}", "")).upper()
        if any(token in ctype for token in ("FREQ", "VRAD", "VELO", "VOPT", "FELO", "WAVE")):
            return ndim - fits_axis
    try:
        wcs = WCS(header)
        types = list(wcs.world_axis_physical_types or [])
        # En WCS sencillo el orden world/pixel sigue FITS; buscamos el pixel axis
        # vía wcs.wcs.spec cuando está disponible.
        spec = int(getattr(wcs.wcs, "spec", -1))
        if spec >= 0:
            return ndim - 1 - spec
    except Exception:
        pass
    return None


def _image_shape_from_header(header) -> tuple[int, ...]:
    """Devuelve la forma NumPy de una imagen FITS sin tocar ``hdu.data``.

    Esto es deliberado: Astropy no puede exponer mediante ``memmap=True`` una
    imagen entera que requiera escalado BSCALE/BZERO o tratamiento de BLANK.
    La inspección de M1 sólo necesita la geometría/WCS, por lo que leer los
    NAXISn evita cargar cubos completos y, además, evita ese error de Astropy.
    """
    try:
        ndim = int(header.get("NAXIS", 0) or 0)
    except Exception:
        return ()
    if ndim < 1:
        return ()
    dims: list[int] = []
    for fits_axis in range(ndim, 0, -1):
        try:
            size = int(header.get(f"NAXIS{fits_axis}", 0) or 0)
        except Exception:
            return ()
        if size < 1:
            return ()
        dims.append(size)
    return tuple(dims)


def _fits_scaling_metadata(header) -> dict[str, Any]:
    """Resume el escalado físico almacenado por FITS, si existe."""
    out: dict[str, Any] = {}
    for key in ("BITPIX", "BSCALE", "BZERO", "BLANK", "DATAMIN", "DATAMAX"):
        if key in header:
            value = header.get(key)
            if isinstance(value, np.generic):
                value = value.item()
            out[key] = value
    return out


def inspect_fits_file(path: str | Path) -> list[FitsHDUInfo]:
    result = []
    # do_not_scale_image_data=True permite mantener memmap durante la inspección
    # incluso para FITS GILDAS/CLASS almacenados como enteros escalados. No se
    # accede a hdu.data: la forma se reconstruye de NAXISn.
    with fits.open(path, memmap=True, do_not_scale_image_data=True, lazy_load_hdus=True) as hdul:
        for idx, hdu in enumerate(hdul):
            header = hdu.header
            shape = _image_shape_from_header(header)
            if not shape:
                continue
            spec_axis = _spectral_axis_from_header(header, len(shape))
            celestial = any(
                str(header.get(f"CTYPE{i}", "")).upper().startswith(("RA", "DEC", "GLON", "GLAT"))
                for i in range(1, len(shape) + 1)
            )
            result.append(
                FitsHDUInfo(
                    idx,
                    str(getattr(hdu, "name", "") or f"HDU{idx}"),
                    shape,
                    len(shape),
                    spec_axis,
                    celestial,
                    str(header.get("BUNIT", "") or ""),
                )
            )
    return result


def _header_float(header, *keys):
    for key in keys:
        value = header.get(key)
        try:
            number = float(value)
            if math.isfinite(number):
                return number
        except Exception:
            pass
    return None


def _metadata_from_header(header, wcs: WCS | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    obj = str(header.get("OBJECT", header.get("SOURCE", "")) or "").strip()
    if obj:
        out["raw_source_name"] = obj
    out["telescope"] = str(header.get("TELESCOP", "") or "").strip()
    out["instrument"] = str(header.get("INSTRUME", "") or "").strip()
    out["bunit"] = str(header.get("BUNIT", "") or "").strip()
    rest_hz = _header_float(header, "RESTFRQ", "RESTFREQ")
    if rest_hz:
        out["rest_frequency_mhz"] = rest_hz / 1e6
    for key in ("VLSR", "VELO-LSR", "VELOSYS"):
        value = _header_float(header, key)
        if value is not None:
            # VELOSYS es m/s por estándar FITS. GILDAS escribe VELO-LSR en m/s
            # (p. ej. 3940 -> 3.94 km/s), mientras que VLSR en muchos productos
            # históricos se expresa directamente en km/s. Conservamos esa
            # distinción en vez de aplicar una heurística por magnitud.
            origin = str(header.get("ORIGIN", "") or "").upper()
            if key == "VELOSYS" or (key == "VELO-LSR" and "GILDAS" in origin):
                out["vlsr_kms"] = value / 1000.0
            else:
                out["vlsr_kms"] = value
            break
    out["spectral_reference_frame"] = str(header.get("SPECSYS", "") or "").strip()
    bmaj = _header_float(header, "BMAJ")
    bmin = _header_float(header, "BMIN")
    bpa = _header_float(header, "BPA")
    if bmaj is not None:
        out["beam_major_arcsec"] = bmaj * 3600.0
    if bmin is not None:
        out["beam_minor_arcsec"] = bmin * 3600.0
    if bpa is not None:
        out["beam_pa_deg"] = bpa
    # Coordenadas de referencia: preferencia a CRVAL RA/DEC.
    ra, dec = None, None
    for fits_axis in range(1, int(header.get("NAXIS", 0)) + 1):
        ctype = str(header.get(f"CTYPE{fits_axis}", "")).upper()
        if ctype.startswith("RA"):
            ra = _header_float(header, f"CRVAL{fits_axis}")
        if ctype.startswith("DEC"):
            dec = _header_float(header, f"CRVAL{fits_axis}")
    ra = _header_float(header, "RA", "OBJRA") if ra is None else ra
    dec = _header_float(header, "DEC", "OBJDEC") if dec is None else dec
    if ra is not None and dec is not None:
        out["ra_deg"], out["dec_deg"] = ra, dec
    out["origin"] = str(header.get("ORIGIN", "") or "").strip()
    out["fits_data_scaling"] = _fits_scaling_metadata(header)
    out["fits_header_summary"] = {
        "OBJECT": obj, "TELESCOP": out.get("telescope", ""), "INSTRUME": out.get("instrument", ""),
        "BUNIT": out.get("bunit", ""), "SPECSYS": out.get("spectral_reference_frame", ""),
        "ORIGIN": out.get("origin", ""),
    }
    out["provenance"] = {"fits_header": "FITS header/WCS"}
    return out


def _spectral_world_axis(header, length: int, numpy_axis: int) -> tuple[np.ndarray, str]:
    ndim = int(header.get("NAXIS", 0))
    fits_axis = ndim - numpy_axis
    ctype = str(header.get(f"CTYPE{fits_axis}", "FREQ")).upper()
    cunit = str(header.get(f"CUNIT{fits_axis}", "") or "").strip()
    crpix = float(header.get(f"CRPIX{fits_axis}", 1.0))
    crval = float(header.get(f"CRVAL{fits_axis}", 0.0))
    cdelt = float(header.get(f"CDELT{fits_axis}", 1.0))
    pix = np.arange(length, dtype=float) + 1.0
    world = crval + (pix - crpix) * cdelt
    if "FREQ" in ctype:
        unit = u.Unit(cunit or "Hz")
        return (world * unit).to_value(u.MHz), "frequency"
    if any(token in ctype for token in ("VRAD", "VELO", "VOPT", "FELO")):
        unit = u.Unit(cunit or "m/s")
        velocity = (world * unit).to_value(u.km/u.s)
        rest = _header_float(header, "RESTFRQ", "RESTFREQ")
        if not rest:
            raise ValueError("El FITS usa un eje de velocidad pero no contiene RESTFRQ/RESTFREQ.")
        rest_mhz = rest / 1e6
        # Para M1 normalizamos a frecuencia con convención radio. Conservamos el
        # eje de velocidad original en metadatos.
        freq = rest_mhz * (1.0 - velocity / C_KMS)
        return freq, "velocity"
    raise ValueError(f"Eje espectral FITS no soportado: {ctype}")


def extract_fits_spectrum(path: str | Path, *, hdu_index: int = 0,
                          x: float | None = None, y: float | None = None,
                          ra_deg: float | None = None, dec_deg: float | None = None,
                          aperture_radius_px: float = 0.0, statistic: str = "mean",
                          stokes_index: int = 0) -> dict[str, Any]:
    p = Path(path).expanduser().resolve()
    # La extracción necesita valores físicos, no los enteros crudos almacenados
    # por FITS. Con memmap=False Astropy puede aplicar correctamente BSCALE,
    # BZERO y BLANK (caso típico de cubos exportados por GILDAS/CLASS).
    # memmap=True produciría: "Cannot load a memory-mapped image: BZERO/BSCALE/BLANK...".
    with fits.open(p, memmap=False, lazy_load_hdus=True) as hdul:
        hdu = hdul[int(hdu_index)]
        if getattr(hdu, "data", None) is None:
            raise ValueError("El HDU seleccionado no contiene datos de imagen.")
        data = np.asarray(hdu.data)
        header = hdu.header.copy()
        if data.ndim < 1:
            raise ValueError("El HDU seleccionado no contiene un espectro o cubo.")
        spec_axis = _spectral_axis_from_header(header, data.ndim)
        if spec_axis is None:
            if data.ndim == 1:
                spec_axis = 0
            else:
                raise ValueError("No se pudo identificar el eje espectral FITS (CTYPE FREQ/VRAD/VELO/VOPT).")
        freq_mhz, native_axis = _spectral_world_axis(header, data.shape[spec_axis], spec_axis)
        meta = _metadata_from_header(header)
        meta["input_fits"] = str(p)
        meta["fits_hdu"] = int(hdu_index)
        meta["fits_native_spectral_axis"] = native_axis

        # Mover espectral al primer eje; dimensiones restantes son espaciales/Stokes.
        cube = np.moveaxis(data, spec_axis, 0)
        while cube.ndim > 3:
            # Típicamente STOKES es el eje extra. Selección conservadora del índice solicitado.
            axis = 1
            idx = max(0, min(int(stokes_index), cube.shape[axis]-1))
            cube = np.take(cube, idx, axis=axis)
            meta["stokes_index"] = idx

        if cube.ndim == 1:
            spectrum = cube.astype(float)
        else:
            # En cube ndim 2: espectral + una dimensión; ndim 3: espectral+y+x.
            if cube.ndim == 2:
                pos = int(round(x if x is not None else (cube.shape[1]-1)/2))
                pos = max(0, min(pos, cube.shape[1]-1))
                spectrum = cube[:, pos].astype(float)
                meta["extraction_pixel"] = [pos]
            else:
                ny, nx = cube.shape[1], cube.shape[2]
                px, py = x, y
                if ra_deg is not None and dec_deg is not None:
                    try:
                        from astropy.coordinates import SkyCoord
                        w = WCS(header).celestial
                        wx, wy = w.world_to_pixel(SkyCoord(float(ra_deg)*u.deg, float(dec_deg)*u.deg, frame="icrs"))
                        px, py = float(wx), float(wy)
                    except Exception:
                        pass
                px = (nx-1)/2 if px is None else float(px)
                py = (ny-1)/2 if py is None else float(py)
                px = max(0.0, min(px, nx-1.0)); py = max(0.0, min(py, ny-1.0))
                radius = max(0.0, float(aperture_radius_px))
                yy, xx = np.ogrid[:ny, :nx]
                if radius <= 0:
                    mask = (xx == int(round(px))) & (yy == int(round(py)))
                else:
                    mask = (xx-px)**2 + (yy-py)**2 <= radius**2
                values = cube[:, mask]
                if statistic == "median":
                    spectrum = np.nanmedian(values, axis=1)
                elif statistic == "sum":
                    spectrum = np.nansum(values, axis=1)
                else:
                    spectrum = np.nanmean(values, axis=1)
                meta["extraction_pixel"] = [px, py]
                meta["aperture_radius_px"] = radius
                meta["extraction_statistic"] = statistic
                # Coordenada celeste del punto extraído si hay WCS.
                try:
                    sky = WCS(header).celestial.pixel_to_world(px, py)
                    meta["ra_deg"], meta["dec_deg"] = float(sky.ra.deg), float(sky.dec.deg)
                except Exception:
                    pass

    finite = np.isfinite(freq_mhz) & np.isfinite(spectrum)
    freq_mhz = np.asarray(freq_mhz, float)[finite]
    spectrum = np.asarray(spectrum, float)[finite]
    order = np.argsort(freq_mhz)
    freq_mhz, spectrum = freq_mhz[order], spectrum[order]
    if freq_mhz.size < 3:
        raise ValueError("La extracción FITS no contiene suficientes canales finitos.")

    digest = hashlib.sha1((str(p)+json.dumps(meta, sort_keys=True, default=str)).encode()).hexdigest()[:10]
    source = re.sub(r"[^A-Za-z0-9_.+-]+", "_", str(meta.get("raw_source_name") or p.stem)).strip("_") or "fits"
    FITS_IMPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FITS_IMPORT_OUTPUT_DIR / f"{source}_hdu{hdu_index}_{digest}.dat"
    header_lines = ["CZSpec FITS extraction", "columns: frequency_MHz intensity"]
    for key in ("raw_source_name", "ra_deg", "dec_deg", "vlsr_kms", "rest_frequency_mhz", "spectral_reference_frame",
                "telescope", "instrument", "bunit", "beam_major_arcsec", "beam_minor_arcsec", "beam_pa_deg"):
        if meta.get(key) not in (None, ""):
            header_lines.append(f"{key}={meta[key]}")
    np.savetxt(out_path, np.column_stack([freq_mhz, spectrum]), fmt="%.9f %.10g", header="\n".join(header_lines))
    meta["path"] = str(out_path)
    meta["display_name"] = f"{meta.get('raw_source_name') or p.stem} · FITS HDU {hdu_index}"
    return {"path": str(out_path), "metadata": meta, "freq": freq_mhz, "inten": spectrum}
