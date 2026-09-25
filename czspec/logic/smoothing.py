"""Suavizado interactivo de espectros ASCII para M1.

Los archivos CLASS .30m se suavizan con el propio motor GILDAS/CLASS. Este
módulo ofrece Hanning, Box y Gauss para espectros ASCII normalizados en MHz.
Los espectros que contienen varios tramos con distinto espaciado espectral se
procesan por tramos, sin convolucionar a través de discontinuidades de backend.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter1d

from czspec.logic.peak_detection import read_spectrum_file

_C_KMS = 299792.458


def _spacing_metadata(freq: np.ndarray) -> tuple[float, float]:
    freq = np.asarray(freq, dtype=float)
    if freq.size < 2:
        raise ValueError("El espectro contiene muy pocos canales.")
    diffs = np.diff(freq)
    if not np.all(np.isfinite(diffs)) or np.any(diffs <= 0):
        raise ValueError("El eje de frecuencia debe ser finito y estrictamente creciente.")
    spacing = float(np.median(diffs))
    center = max(float(np.nanmedian(np.abs(freq))), 1e-12)
    return spacing, _C_KMS * abs(spacing) / center


def _regular_segments(freq: np.ndarray) -> list[slice]:
    """Divide una malla monótona en tramos de resolución aproximadamente constante."""
    x = np.asarray(freq, dtype=float)
    _spacing_metadata(x)
    if x.size < 4:
        return [slice(0, x.size)]
    d = np.diff(x)
    # Separamos discontinuidades reales (huecos grandes entre ventanas), no pequeñas
    # irregularidades de regridding/representación decimal. Hanning y BOX operan por
    # canal y GAUSS usa el dν mediano del tramo.
    typical = max(float(np.median(d)), 1e-12)
    breaks = np.where((d > 3.0 * typical) | (d < 0.25 * typical))[0]
    edges = [0] + [int(i + 1) for i in breaks] + [x.size]
    segments = []
    for a, b in zip(edges[:-1], edges[1:]):
        if b - a >= 3:
            segments.append(slice(a, b))
    if not segments:
        segments = [slice(0, x.size)]
    return segments


def _smooth_regular_segment(x: np.ndarray, y: np.ndarray, method: str, value=None):
    _, spacing_kms = _spacing_metadata(x)
    if method == "none":
        return x.copy(), y.copy()
    if method == "hanning":
        if x.size < 5:
            return x.copy(), y.copy()
        filtered = np.convolve(y, np.array([0.25, 0.50, 0.25]), mode="valid")
        centers = x[1:-1]
        return centers[::2], filtered[::2]
    if method == "box":
        nchan = int(round(float(value or 2)))
        if not 2 <= nchan <= 50:
            raise ValueError("BOX requiere entre 2 y 50 canales.")
        nblocks = x.size // nchan
        if nblocks < 1:
            return x.copy(), y.copy()
        cut = nblocks * nchan
        return (
            x[:cut].reshape(nblocks, nchan).mean(axis=1),
            y[:cut].reshape(nblocks, nchan).mean(axis=1),
        )
    if method == "gauss":
        width_kms = float(value or 1.0)
        if not 0.01 <= width_kms <= 100.0:
            raise ValueError("El ancho gaussiano debe estar entre 0.01 y 100 km/s.")
        sigma_channels = width_kms / (2.0 * np.sqrt(2.0 * np.log(2.0))) / max(spacing_kms, 1e-12)
        if sigma_channels < 0.05:
            raise ValueError(
                "El ancho gaussiano es demasiado pequeño respecto al muestreo espectral."
            )
        return x.copy(), gaussian_filter1d(
            y, sigma=sigma_channels, mode="nearest", truncate=4.0
        )
    raise ValueError(f"Método de suavizado no reconocido: {method}")


def smooth_arrays(freq, inten, method: str, value=None):
    """Devuelve ``(freq_out, inten_out, metadata)`` tras aplicar el suavizado."""
    x = np.asarray(freq, dtype=float)
    y = np.asarray(inten, dtype=float)
    if x.shape != y.shape:
        raise ValueError("Frecuencia e intensidad deben tener la misma longitud.")
    _spacing_metadata(x)
    method = str(method or "none").lower()
    if method not in {"none", "hanning", "box", "gauss"}:
        raise ValueError(f"Método de suavizado no reconocido: {method}")

    segments = _regular_segments(x)
    xs, ys = [], []
    for segment in segments:
        xo, yo = _smooth_regular_segment(x[segment], y[segment], method, value)
        if xo.size:
            xs.append(xo)
            ys.append(yo)
    if not xs:
        raise ValueError("El suavizado no produjo canales de salida.")
    xo = np.concatenate(xs)
    yo = np.concatenate(ys)
    order = np.argsort(xo)
    xo, yo = xo[order], yo[order]
    _, output_spacing_kms = _spacing_metadata(xo)

    if method == "none":
        note = "Sin suavizado; se restauró el espectro de entrada."
    elif method == "hanning":
        note = "Hanning 3 puntos + decimación x2 por tramo espectral (CZSpec nativo)."
    elif method == "box":
        note = f"Promedio BOX de {int(round(float(value or 2)))} canales por tramo (CZSpec nativo)."
    else:
        note = (
            f"Convolución gaussiana FWHM={float(value or 1.0):g} km/s "
            "por tramo espectral (CZSpec nativo)."
        )

    meta = {
        "smooth_method": method,
        "smooth_value": None if method in {"none", "hanning"} else value,
        "smooth_engine": "czspec-native",
        "channel_spacing_kms": float(output_spacing_kms),
        "smoothing_segments": len(segments),
        "smoothing_note": note,
    }
    return xo, yo, meta


def smooth_ascii_file(input_path: str, output_path: str, method: str, value=None) -> dict:
    """Suaviza un espectro ASCII y guarda una copia derivada sin tocar el original."""
    freq, inten, read_meta = read_spectrum_file(str(input_path))
    xo, yo, meta = smooth_arrays(freq, inten, method, value)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(output, np.column_stack([xo, yo]), fmt="%.9f %.10g")
    return {
        "path": str(output),
        "input_path": str(Path(input_path).expanduser().resolve()),
        "read_metadata": dict(read_meta or {}),
        **meta,
    }
