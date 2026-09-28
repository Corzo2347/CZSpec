import os
import re
import uuid
from pathlib import Path
from datetime import datetime

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
import numpy.linalg as npl
import plotly.io as pio
from scipy.optimize import curve_fit, least_squares
from scipy.signal import find_peaks, peak_widths
from scipy.ndimage import gaussian_filter1d
from scipy.special import wofz

from czspec.paths import PEAK_DETECTION_OUTPUT_DIR
from czspec.plot_styles import (
    DEFAULT_FIT_COLOR,
    DEFAULT_PLOT_STYLES,
    normalize_plot_styles,
)
from czspec.science_defaults import DEFAULT_DETECTION_SIGMA
from czspec.logic.source_metadata import parse_ascii_header, merge_metadata, velocity_from_frequency, line_velocity_kms, velocity_axis_from_metadata
from czspec.utils.numerics import trapezoidal_integral


# =========================================================
# Lectura y normalización de espectros
# =========================================================
def normalize_frequency_to_mhz(freq):
    """Devuelve un eje de frecuencia en MHz y la escala aplicada.

    Los espectros ASCII históricos de CZSpec no almacenaban la unidad de forma
    explícita. Se usan rangos astronómicos razonables para reconocer GHz, MHz,
    kHz o Hz sin alterar los archivos que ya estaban en MHz.
    """
    values = np.asarray(freq, dtype=float)
    finite = np.abs(values[np.isfinite(values)])
    if finite.size == 0:
        raise ValueError("El eje de frecuencia no contiene valores finitos.")
    representative = float(np.nanmedian(finite))
    if representative <= 0:
        raise ValueError("El eje de frecuencia debe contener valores positivos.")

    if representative < 1.0e3:       # GHz -> MHz (p.ej. 143.5)
        factor, unit = 1.0e3, "GHz"
    elif representative < 1.0e6:     # MHz (p.ej. 143500)
        factor, unit = 1.0, "MHz"
    elif representative < 1.0e9:     # kHz -> MHz
        factor, unit = 1.0e-3, "kHz"
    else:                             # Hz -> MHz
        factor, unit = 1.0e-6, "Hz"
    return values * factor, factor, unit




def normalize_intensity_unit(unit: str | None) -> str:
    """Return a canonical display unit for simple intensity conversions.

    Only algebraic unit-prefix conversions are handled here.  Physically
    model-dependent conversions such as Jy/beam <-> K are deliberately not
    included because they require beam and frequency information.
    """
    raw = str(unit or "").strip()
    if not raw:
        return ""
    text = raw.replace("μ", "µ").replace("−", "-").replace("⁻", "-")
    compact = re.sub(r"\s+", "", text).lower()
    compact = compact.replace("perbeam", "/beam")
    aliases = {
        "k": "K", "mk": "mK", "µk": "µK", "uk": "µK",
        "jy": "Jy", "mjy": "mJy", "µjy": "µJy", "ujy": "µJy",
        "jy/beam": "Jy/beam", "jybeam-1": "Jy/beam", "jybeam^-1": "Jy/beam",
        "mjy/beam": "mJy/beam", "mjybeam-1": "mJy/beam", "mjybeam^-1": "mJy/beam",
        "µjy/beam": "µJy/beam", "ujy/beam": "µJy/beam",
        "µjybeam-1": "µJy/beam", "ujybeam-1": "µJy/beam",
    }
    if compact in aliases:
        return aliases[compact]
    # Accept common spellings of SI spectral flux density.
    si = compact.replace("^", "").replace("**", "")
    if si in {
        "w/m2/hz", "wm-2hz-1", "w*m-2*hz-1", "w/m²/hz",
        "wm-2hz−1", "wm−2hz−1",
    }:
        return "W m⁻² Hz⁻¹"
    return raw


def intensity_conversion_factor(source_unit: str | None, target_unit: str | None):
    """Return ``(factor, canonical_target)`` for a direct unit conversion.

    ``None`` is returned when the requested transformation is not a pure unit
    conversion.  That prevents CZSpec from silently treating Jy/beam <-> K as
    equivalent, for example.
    """
    source = normalize_intensity_unit(source_unit)
    target = normalize_intensity_unit(target_unit)
    if not target or target.lower() in {"native", "input", "original"}:
        return 1.0, source
    if not source:
        return None
    if source == target:
        return 1.0, target

    temperature = {"K": 1.0, "mK": 1.0e-3, "µK": 1.0e-6}
    flux = {"Jy": 1.0, "mJy": 1.0e-3, "µJy": 1.0e-6, "W m⁻² Hz⁻¹": 1.0e26}
    flux_beam = {"Jy/beam": 1.0, "mJy/beam": 1.0e-3, "µJy/beam": 1.0e-6}
    for family in (temperature, flux, flux_beam):
        if source in family and target in family:
            # family scales are expressed in the corresponding base unit.  For
            # SI flux density the scale is Jy per SI unit (1 W m^-2 Hz^-1=1e26 Jy).
            return family[source] / family[target], target
    return None


def intensity_conversion_factor_at_frequency(source_unit: str | None, target_unit: str | None, frequency_mhz: float | None):
    """Return a display conversion factor at one explicit reference frequency.

    This extends :func:`intensity_conversion_factor` only for brightness
    temperature <-> spectral-radiance conversions.  Such a conversion depends
    on frequency, so it cannot define a unique secondary Y scale across a wide
    spectrum without choosing a reference coordinate.  CZSpec therefore uses
    the centre/median frequency of the displayed panel and records that
    reference in the plot metadata/title.  Primary-Y radiance conversion remains
    channel-by-channel and is unchanged.
    """
    direct = intensity_conversion_factor(source_unit, target_unit)
    if direct is not None:
        return direct
    source = normalize_intensity_unit(source_unit)
    target = normalize_intensity_unit(target_unit)
    try:
        nu_mhz = float(frequency_mhz)
    except Exception:
        return None
    if not np.isfinite(nu_mhz) or nu_mhz <= 0:
        return None

    temperature = {"K": 1.0, "mK": 1.0e-3, "µK": 1.0e-6}
    # SI W m^-2 Hz^-1 sr^-1 represented by one unit of each radiance scale.
    radiance_si = {
        "Jy/sr": 1.0e-26,
        "MJy/sr": 1.0e-20,
        "W m⁻² Hz⁻¹ sr⁻¹": 1.0,
    }
    k_b = 1.380649e-23
    c = 299792458.0
    rj_per_kelvin_si = 2.0 * k_b * (nu_mhz * 1.0e6) ** 2 / (c * c)

    if source in temperature and target in radiance_si:
        factor = temperature[source] * rj_per_kelvin_si / radiance_si[target]
        return float(factor), target
    if source in radiance_si and target in temperature:
        factor = radiance_si[source] / (rj_per_kelvin_si * temperature[target])
        return float(factor), target
    if source in radiance_si and target in radiance_si:
        return float(radiance_si[source] / radiance_si[target]), target
    return None

def read_spectrum_file(file_path: str):
    """Lee un espectro ASCII de dos columnas y normaliza frecuencia a MHz."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")

    try:
        data = np.loadtxt(file_path)
    except Exception:
        # Lector tolerante para archivos con encabezados libres (#, !, %, ; o
        # texto sin prefijo). Conserva las dos primeras columnas numéricas.
        rows = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped or stripped.startswith(("#", "!", "%", ";")):
                        continue
                    tokens = [tok for tok in re.split(r"[,;\s]+", stripped) if tok]
                    if len(tokens) < 2:
                        continue
                    try:
                        rows.append([float(tokens[0].replace("D","E").replace("d","e")),
                                     float(tokens[1].replace("D","E").replace("d","e"))])
                    except ValueError:
                        continue
        except Exception:
            rows = []
        if rows:
            data = np.asarray(rows, dtype=float)
        else:
            frame = pd.read_csv(file_path, sep=None, engine="python", comment="#")
            numeric = frame.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
            if numeric.shape[1] < 2:
                raise ValueError("El archivo debe contener al menos dos columnas numéricas.")
            data = numeric.iloc[:, :2].dropna().to_numpy(dtype=float)

    data = np.asarray(data, dtype=float)
    if data.ndim != 2 or data.shape[1] < 2 or data.shape[0] < 3:
        raise ValueError("El espectro debe contener al menos tres canales y dos columnas.")

    freq_raw = data[:, 0].astype(float)
    inten = data[:, 1].astype(float)
    finite = np.isfinite(freq_raw) & np.isfinite(inten)
    freq_raw = freq_raw[finite]
    inten = inten[finite]
    if freq_raw.size < 3:
        raise ValueError("No hay suficientes canales finitos para analizar el espectro.")

    freq, factor, input_unit = normalize_frequency_to_mhz(freq_raw)
    order = np.argsort(freq)
    freq = freq[order]
    inten = inten[order]

    # Elimina canales repetidos conservando el primero; los duplicados causan
    # anchos de canal nulos y ajustes degenerados.
    keep = np.r_[True, np.diff(freq) > 0]
    freq = freq[keep]
    inten = inten[keep]
    if freq.size < 3:
        raise ValueError("El eje de frecuencia no contiene canales únicos suficientes.")

    header_meta = parse_ascii_header(file_path)
    # Los ASCII de dos columnas no tienen un estándar de metadatos. En el uso
    # espectroscópico de CZSpec la unidad de intensidad de trabajo por defecto es K.
    # Se registra el origen de esta suposición para no confundirla con una unidad
    # declarada explícitamente por el archivo.
    if not str(header_meta.get("bunit") or header_meta.get("intensity_unit") or "").strip():
        header_meta["bunit"] = "K"
        header_meta["bunit_source"] = "assumed_default_ascii"
    return freq, inten, merge_metadata(header_meta, {
        "input_frequency_unit": input_unit,
        "frequency_scale_to_mhz": float(factor),
    })


# =========================================================
# Utilidades de perfiles
# =========================================================
def gaussian(x, amp, cen, sigma):
    return amp * np.exp(-(x - cen) ** 2 / (2.0 * sigma ** 2))


def lorentzian(x, amp, cen, gamma):
    return amp * (gamma ** 2 / ((x - cen) ** 2 + gamma ** 2))


def voigt(x, amp, cen, sigma, gamma):
    """Perfil Voigt normalizado para que ``amp`` sea la intensidad pico [K]."""
    sigma = max(abs(float(sigma)), 1e-12)
    gamma = max(abs(float(gamma)), 1e-12)
    z = ((x - cen) + 1j * gamma) / (sigma * np.sqrt(2.0))
    raw = np.real(wofz(z)) / (sigma * np.sqrt(2.0 * np.pi))
    z0 = 1j * gamma / (sigma * np.sqrt(2.0))
    peak_norm = float(np.real(wofz(z0)) / (sigma * np.sqrt(2.0 * np.pi)))
    return amp * raw / max(peak_norm, 1e-30)


# =========================================================
# Utilidades matemáticas
# =========================================================
def _robust_sigma(values):
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size < 3:
        return float(np.nanstd(finite)) if finite.size else 0.0
    med = float(np.nanmedian(finite))
    mad = float(np.nanmedian(np.abs(finite - med)))
    sigma = 1.4826 * mad
    if not np.isfinite(sigma) or sigma <= 0:
        sigma = float(np.nanstd(finite))
    return max(sigma, 1e-12)


def poly_baseline_with_sigma_clipping(freq, inten, mask, degree=0, n_iter=6, nsigma=3.0):
    """Ajusta una base polinomial con rechazo robusto bilateral."""
    freq = np.asarray(freq, dtype=float)
    inten = np.asarray(inten, dtype=float)
    mask_fit = np.asarray(mask, dtype=bool).copy() & np.isfinite(freq) & np.isfinite(inten)
    if np.sum(mask_fit) < degree + 2:
        raise ValueError("No hay suficientes canales de base para el grado solicitado.")

    # Centrar el eje evita matrices mal condicionadas cuando nu ~ 10^5 MHz.
    f0 = float(np.nanmedian(freq[mask_fit]))
    scale = max(float(np.nanmax(np.abs(freq[mask_fit] - f0))), 1.0)
    x = (freq - f0) / scale
    base = np.full_like(inten, float(np.nanmedian(inten[mask_fit])))

    for _ in range(max(1, int(n_iter))):
        if np.sum(mask_fit) < degree + 2:
            break
        coeffs = np.polyfit(x[mask_fit], inten[mask_fit], deg=degree)
        base = np.polyval(coeffs, x)
        resid = inten - base
        center = float(np.nanmedian(resid[mask_fit]))
        sigma = _robust_sigma(resid[mask_fit] - center)
        new_mask = mask_fit & (np.abs(resid - center) < float(nsigma) * sigma)
        if np.array_equal(new_mask, mask_fit):
            break
        mask_fit = new_mask

    return base


def automatic_baseline_mask(freq, inten, degree=0, line_sigma=3.0, dilation_kms=3.0):
    """Construye una máscara automática de canales plausiblemente libres de línea.

    La detección de regiones contaminadas se hace sobre una copia suavizada del
    residual. Así no se dilata cada fluctuación de ruido individual, algo crítico
    en espectros con alta densidad de líneas.
    """
    freq = np.asarray(freq, dtype=float)
    inten = np.asarray(inten, dtype=float)
    mask = np.isfinite(freq) & np.isfinite(inten)
    if mask.sum() < degree + 2:
        return mask
    channel_width = max(float(np.nanmedian(np.diff(freq))), 1e-12)
    nu_ref = max(float(np.nanmedian(freq)), 1e-12)
    half_bins = max(2, int(np.ceil((nu_ref * float(dilation_kms) / 299792.458) / channel_width)))
    # Evita que el kernel de dilatación sea más largo que espectros ASCII muy
    # cortos o extremadamente sobremuestreados; ``np.convolve(..., same)``
    # devolvería entonces la longitud del kernel y rompería la máscara booleana.
    half_bins = min(half_bins, max(2, (len(freq) - 1) // 2))

    for _ in range(4):
        base = poly_baseline_with_sigma_clipping(freq, inten, mask, degree=degree, n_iter=4, nsigma=3.2)
        resid = inten - base
        smoothed = gaussian_filter1d(resid, sigma=2.0, mode="nearest")
        center = float(np.nanmedian(smoothed[mask]))
        sigma_s = _robust_sigma(smoothed[mask] - center)
        line_like = np.abs(smoothed - center) >= float(line_sigma) * sigma_s
        if np.any(line_like):
            kernel = np.ones(2 * half_bins + 1, dtype=int)
            dilated = np.convolve(line_like.astype(int), kernel, mode="same") > 0
            candidate = np.isfinite(freq) & np.isfinite(inten) & ~dilated
        else:
            candidate = mask
        minimum = max(degree + 2, int(0.08 * len(freq)))
        if candidate.sum() < minimum:
            break
        if np.array_equal(candidate, mask):
            break
        mask = candidate
    return mask

def mask_from_baseline_windows(freq, windows):
    """Convierte ventanas manuales en máscara y conserva grado local opcional.

    Acepta ``(fmin, fmax)`` o ``(fmin, fmax, degree)``. El tercer valor es
    únicamente una instrucción explícita del usuario; si falta, se usa el grado
    global de M1.
    """
    freq = np.asarray(freq, dtype=float)
    mask = np.zeros_like(freq, dtype=bool)
    clean = []
    for pair in windows or []:
        if pair is None or len(pair) not in {2, 3}:
            continue
        a, b = sorted((float(pair[0]), float(pair[1])))
        if not np.isfinite(a) or not np.isfinite(b) or a == b:
            continue
        degree = None
        if len(pair) == 3 and pair[2] is not None:
            degree = int(pair[2])
            if degree not in (0, 1, 2, 3):
                raise ValueError("El grado local de línea base debe estar entre 0 y 3.")
        mask |= (freq >= a) & (freq <= b)
        clean.append((a, b, degree))
    if not clean:
        raise ValueError("El modo de base por ventanas requiere al menos un intervalo válido.")
    return mask, clean


def local_degree_baseline_from_windows(freq, inten, windows, default_degree=0):
    """Construye una línea base local cuando las ventanas usan grados distintos.

    Cada ventana se ajusta con rechazo robusto y con su grado declarado (o el
    grado global como respaldo). Los modelos locales se combinan por
    interpolación entre los centros de ventanas vecinas. La evaluación de cada
    polinomio se limita a dos semianchos de su propia ventana para evitar
    extrapolaciones polinomiales no controladas lejos de los canales que lo
    determinaron. Esta ruta sólo se activa cuando el usuario declara al menos un
    ``@grado`` explícito.
    """
    freq = np.asarray(freq, dtype=float)
    inten = np.asarray(inten, dtype=float)
    specs = sorted(windows, key=lambda row: 0.5 * (row[0] + row[1]))
    models = []
    used_mask = np.zeros_like(freq, dtype=bool)
    for a, b, local_degree in specs:
        degree = int(default_degree if local_degree is None else local_degree)
        mask = np.isfinite(freq) & np.isfinite(inten) & (freq >= a) & (freq <= b)
        if int(mask.sum()) < max(degree + 2, 4):
            raise ValueError(
                f"La ventana {a:g}-{b:g} MHz contiene muy pocos canales para grado {degree}."
            )
        used_mask |= mask
        center = 0.5 * (a + b)
        half_width = max(0.5 * abs(b - a), np.finfo(float).eps)
        x = (freq - center) / half_width
        fit_mask = mask.copy()
        coeffs = None
        for _ in range(6):
            if int(fit_mask.sum()) < degree + 2:
                break
            coeffs = np.polyfit(x[fit_mask], inten[fit_mask], deg=degree)
            pred = np.polyval(coeffs, x)
            resid = inten - pred
            center_resid = float(np.nanmedian(resid[fit_mask]))
            sigma = _robust_sigma(resid[fit_mask] - center_resid)
            next_mask = mask & (np.abs(resid - center_resid) < 3.0 * sigma)
            if np.array_equal(next_mask, fit_mask):
                break
            fit_mask = next_mask
        if coeffs is None:
            coeffs = np.polyfit(x[mask], inten[mask], deg=degree)
        x_eval = np.clip(x, -2.0, 2.0)
        prediction = np.polyval(coeffs, x_eval)
        models.append({
            "a": float(a), "b": float(b), "degree": degree,
            "center": float(center), "prediction": prediction,
        })

    if len(models) == 1:
        return np.asarray(models[0]["prediction"], dtype=float), used_mask, models

    centers = np.asarray([m["center"] for m in models], dtype=float)
    predictions = np.vstack([np.asarray(m["prediction"], dtype=float) for m in models])
    baseline = np.empty_like(freq, dtype=float)
    for i, f in enumerate(freq):
        if f <= centers[0]:
            baseline[i] = predictions[0, i]
            continue
        if f >= centers[-1]:
            baseline[i] = predictions[-1, i]
            continue
        right = int(np.searchsorted(centers, f, side="right"))
        left = right - 1
        span = max(centers[right] - centers[left], np.finfo(float).eps)
        w = float((f - centers[left]) / span)
        baseline[i] = (1.0 - w) * predictions[left, i] + w * predictions[right, i]
    return baseline, used_mask, models

def _pcov_from_least_squares(res, n_obs):
    jac = res.jac
    n_params = res.x.size
    dof = max(n_obs - n_params, 1)

    try:
        jtj = jac.T @ jac
        inv_jtj = npl.inv(jtj)
    except npl.LinAlgError:
        return np.full((n_params, n_params), np.nan)

    var_res = 2.0 * res.cost / dof
    return inv_jtj * var_res


def _sanitize_params(fit_choice, params):
    p = np.array(params, dtype=float)
    if not np.isfinite(p[0]):
        p[0] = 0.0
    if fit_choice in ("1", "2"):
        p[2] = max(abs(p[2]), 1e-8)
    else:
        p[2] = max(abs(p[2]), 1e-8)
        p[3] = max(abs(p[3]), 1e-8)
    return p


def fwhm_and_area_from_params(fit_choice, params, x_for_area=None):
    if fit_choice == "1":
        amp, mu, sigma = params
        sigma = abs(sigma)
        fwhm = 2 * np.sqrt(2 * np.log(2)) * sigma
        area = amp * sigma * np.sqrt(2 * np.pi)
        nu0 = mu

    elif fit_choice == "2":
        amp, mu, gamma = params
        gamma = abs(gamma)
        fwhm = 2 * gamma
        area = amp * np.pi * gamma
        nu0 = mu

    else:
        amp, mu, sigma, gamma = params
        sigma = abs(sigma)
        gamma = abs(gamma)
        fwhm = 0.5346 * 2 * gamma + np.sqrt(0.2166 * (2 * gamma) ** 2 + (2.3548 * sigma) ** 2)

        if x_for_area is None:
            x_for_area = np.linspace(mu - 5 * fwhm, mu + 5 * fwhm, 800)

        area = trapezoidal_integral(voigt(x_for_area, *params), x_for_area)
        nu0 = mu

    return fwhm, area, nu0


def mhz_to_kms(width_mhz, nu0_mhz):
    c_kms = 2.99792458e5
    return c_kms * (width_mhz / max(nu0_mhz, 1e-12))


def kmhz_to_kkms(area_kmhz, nu0_mhz):
    c_kms = 2.99792458e5
    return area_kmhz * c_kms / max(nu0_mhz, 1e-12)


def _dv_intint_from_params(fit_choice, params, x_for_area):
    fwhm_mhz, area_kmhz, mu = fwhm_and_area_from_params(fit_choice, params, x_for_area=x_for_area)
    dv_kms = mhz_to_kms(fwhm_mhz, mu)
    intint = kmhz_to_kkms(area_kmhz, mu)
    return dv_kms, intint


def _numerical_grad(func, fit_choice, params, x_for_area, eps_rel=1e-6):
    params = np.array(params, dtype=float)
    f0 = func(fit_choice, _sanitize_params(fit_choice, params), x_for_area)
    f0 = np.atleast_1d(f0)

    n_params = params.size
    grad = np.zeros((f0.size, n_params), dtype=float)

    for k in range(n_params):
        step = eps_rel * (abs(params[k]) + 1.0)
        pp = params.copy()
        pm = params.copy()
        pp[k] += step
        pm[k] -= step

        pp = _sanitize_params(fit_choice, pp)
        pm = _sanitize_params(fit_choice, pm)

        fp = func(fit_choice, pp, x_for_area)
        fm = func(fit_choice, pm, x_for_area)

        fp = np.atleast_1d(fp)
        fm = np.atleast_1d(fm)
        grad[:, k] = (fp - fm) / (2.0 * step)

    return grad


def dv_intint_and_errors(fit_choice, params, pcov, x_for_area):
    params = _sanitize_params(fit_choice, params)
    dv_kms, intint_kms = _dv_intint_from_params(fit_choice, params, x_for_area)

    if pcov is None or not np.all(np.isfinite(pcov)):
        return dv_kms, np.nan, intint_kms, np.nan

    g = _numerical_grad(_dv_intint_from_params, fit_choice, params, x_for_area)
    cov_out = g @ pcov @ g.T

    dv_err = float(np.sqrt(max(cov_out[0, 0], 0.0)))
    intint_err = float(np.sqrt(max(cov_out[1, 1], 0.0)))

    return dv_kms, dv_err, intint_kms, intint_err


def local_sigma_mad(y, window_bins=51):
    """Ruido local robusto, priorizando diferencias entre canales.

    En espectros line-confused, el MAD directo de la intensidad puede interpretar
    la emisión real como ruido. Las primeras diferencias reducen ese sesgo porque
    una línea ancha cambia lentamente entre canales. Se mantiene un piso global
    para evitar regiones con sigma artificialmente pequeña.
    """
    y = np.asarray(y, dtype=float)
    w = int(max(51, window_bins // 2 * 2 + 1))
    if y.size < 5:
        return np.full_like(y, np.nanstd(y) + 1e-12)

    dy = np.diff(y)
    dy_series = pd.Series(dy)
    dy_med = dy_series.rolling(w, center=True, min_periods=max(7, w // 3)).median()
    dy_mad = (dy_series - dy_med).abs().rolling(
        w, center=True, min_periods=max(7, w // 3)
    ).median()
    sigma_d = 1.4826 * dy_mad / np.sqrt(2.0)

    global_d = 1.4826 * np.median(np.abs(dy - np.median(dy))) / np.sqrt(2.0)
    global_y = 1.4826 * np.median(np.abs(y - np.median(y)))
    sigma0 = max(float(global_d), min(float(global_y), 3.0 * float(global_d)), 1e-12)

    # Interpola el estimador de N-1 diferencias al eje de N canales.
    sigma_d = sigma_d.fillna(sigma0).to_numpy(dtype=float)
    sigma = np.empty_like(y, dtype=float)
    sigma[0] = sigma_d[0]
    sigma[-1] = sigma_d[-1]
    sigma[1:-1] = 0.5 * (sigma_d[:-1] + sigma_d[1:])

    floor = 0.65 * sigma0
    ceiling = max(4.0 * sigma0, floor)
    return np.clip(sigma, floor, ceiling)


def _deduplicate_peak_indices(indices, y, min_separation=2):
    if not indices:
        return []
    ordered = sorted(set(int(i) for i in indices), key=lambda i: abs(float(y[i])), reverse=True)
    accepted = []
    for idx in ordered:
        if all(abs(idx - other) > min_separation for other in accepted):
            accepted.append(idx)
    return sorted(accepted)


def _detect_one_polarity(
    y,
    sigma,
    *,
    sign=1,
    detection_sigma=DEFAULT_DETECTION_SIGMA,
    prominence_sigma=2.5,
    min_width_channels=2.5,
    min_distance_channels=2,
    multiscale=True,
):
    signal = np.asarray(y, dtype=float) * float(sign)
    sigma = np.maximum(np.asarray(sigma, dtype=float), 1e-12)
    peaks, _ = find_peaks(
        signal,
        height=float(detection_sigma) * sigma,
        prominence=float(prominence_sigma) * sigma,
        width=float(min_width_channels),
        distance=max(1, int(min_distance_channels)),
    )
    candidates = peaks.tolist()

    if multiscale and signal.size >= 25:
        for scale in (1.5, 3.0, 5.0):
            ys = gaussian_filter1d(signal, sigma=scale, mode="nearest")
            sigs = local_sigma_mad(ys, window_bins=max(101, (int(35 * scale) | 1)))
            relaxed = max(2.8, float(detection_sigma) - 0.8)
            p_s, _ = find_peaks(
                ys,
                height=relaxed * sigs,
                prominence=max(1.5, float(prominence_sigma) - 0.8) * sigs,
                width=max(2.0, scale),
                distance=max(2, int(round(scale))),
            )
            radius = max(2, int(np.ceil(2.5 * scale)))
            for pidx in p_s:
                lo = max(0, int(pidx) - radius)
                hi = min(signal.size, int(pidx) + radius + 1)
                idx = lo + int(np.argmax(signal[lo:hi]))
                peak_snr = signal[idx] / sigma[idx]
                seg = slice(lo, hi)
                positive = np.clip(signal[seg], 0.0, None)
                integrated_snr = float(np.sum(positive) / np.sqrt(np.sum(sigma[seg] ** 2)))
                if peak_snr >= max(2.5, float(detection_sigma) - 1.5) and integrated_snr >= 1.25 * float(detection_sigma):
                    candidates.append(idx)

    candidates = _deduplicate_peak_indices(
        candidates, signal, min_separation=max(1, int(min_distance_channels))
    )
    return np.asarray(candidates, dtype=int)


def detect_peaks_by_snr(
    y_corr,
    sigma_loc,
    detection_sigma=DEFAULT_DETECTION_SIGMA,
    prominence_sigma=2.5,
    min_width_channels=2.5,
    min_distance_channels=2,
    multiscale=True,
    polarity="emission",
):
    """Detecta emisión, absorción o ambas sobre el espectro físico.

    La estadística se utiliza como umbral, pero la localización se hace sobre T,
    no sobre T/sigma. El suavizado multiescala sólo propone candidatos; los
    perfiles se ajustan siempre contra los datos originales.
    """
    threshold = float(detection_sigma)
    if not np.isfinite(threshold) or not (0.5 <= threshold <= 20.0):
        raise ValueError("El umbral de detección debe estar entre 0.5 y 20 σ.")
    polarity = str(polarity or "emission").lower()
    if polarity not in {"emission", "absorption", "both"}:
        raise ValueError("polarity debe ser 'emission', 'absorption' o 'both'.")

    y = np.asarray(y_corr, dtype=float)
    sigma = np.maximum(np.asarray(sigma_loc, dtype=float), 1e-12)
    prominence_sigma = float(max(1.0, prominence_sigma))
    items = []

    requested = []
    if polarity in {"emission", "both"}:
        requested.append((1, "emission"))
    if polarity in {"absorption", "both"}:
        requested.append((-1, "absorption"))

    from scipy.signal import peak_prominences
    for sign, kind in requested:
        peaks = _detect_one_polarity(
            y,
            sigma,
            sign=sign,
            detection_sigma=threshold,
            prominence_sigma=prominence_sigma,
            min_width_channels=min_width_channels,
            min_distance_channels=min_distance_channels,
            multiscale=multiscale,
        )
        if not len(peaks):
            continue
        signal = sign * y
        prominences, left_bases, right_bases = peak_prominences(signal, peaks)
        widths, _, _, _ = peak_widths(
            signal,
            peaks,
            rel_height=0.5,
            prominence_data=(prominences, left_bases, right_bases),
        )
        for j, idx in enumerate(peaks):
            items.append({
                "index": int(idx),
                "polarity": kind,
                "sign": int(sign),
                "peak_snr": float(abs(y[idx]) / sigma[idx]),
                "signed_snr": float(y[idx] / sigma[idx]),
                "prominence_snr": float(prominences[j] / sigma[idx]),
                "width_channels": float(widths[j]),
                "prominences": float(prominences[j]),
            })

    # Si ambos modos encuentran candidatos casi coincidentes, conservar el de
    # mayor |S/N|. P-Cygni real queda intacto porque los extremos están separados.
    items.sort(key=lambda it: abs(it["peak_snr"]), reverse=True)
    accepted = []
    for item in items:
        if all(abs(item["index"] - other["index"]) > max(1, int(min_distance_channels)) for other in accepted):
            accepted.append(item)
    accepted.sort(key=lambda it: it["index"])

    peaks = np.asarray([it["index"] for it in accepted], dtype=int)
    metrics = {
        "peak_snr": np.asarray([it["peak_snr"] for it in accepted], dtype=float),
        "signed_snr": np.asarray([it["signed_snr"] for it in accepted], dtype=float),
        "prominence_snr": np.asarray([it["prominence_snr"] for it in accepted], dtype=float),
        "width_channels": np.asarray([it["width_channels"] for it in accepted], dtype=float),
        "prominences": np.asarray([it["prominences"] for it in accepted], dtype=float),
        "polarity": np.asarray([it["polarity"] for it in accepted], dtype=object),
    }
    z = y / sigma
    return peaks, metrics, z, prominence_sigma


# =========================================================
# Ajuste robusto y deblending
# =========================================================
def _profile_param_count(fit_choice):
    return 3 if fit_choice in ("1", "2") else 4


def _width_guess_mhz(fit_choice, mu0, dv_guess_kms=2.5):
    fwhm = max(float(mu0) * float(dv_guess_kms) / 299792.458, 1e-8)
    if fit_choice == "1":
        return (fwhm / 2.354820045,)
    if fit_choice == "2":
        return (fwhm / 2.0,)
    # Voigt: reparto inicial conservador entre parte gaussiana y lorentziana.
    return (fwhm / 3.0, fwhm / 4.0)


def evaluate_profile(fit_choice, x, params):
    if fit_choice == "1":
        return gaussian(x, *params)
    if fit_choice == "2":
        return lorentzian(x, *params)
    return voigt(x, *params)


def _multi_model(fit_choice, x, params):
    ppc = _profile_param_count(fit_choice)
    total = np.zeros_like(np.asarray(x, dtype=float), dtype=float)
    for offset in range(0, len(params), ppc):
        total += evaluate_profile(fit_choice, x, params[offset:offset + ppc])
    return total


def fit_multi_components_robust(
    fit_choice,
    x_data,
    y_data,
    sigma_data,
    seeds,
    channel_width,
    *,
    center_window_kms=4.5,
    max_fwhm_kms=30.0,
):
    """Ajusta N componentes con ``least_squares`` y pérdida ``soft_l1``."""
    x_data = np.asarray(x_data, dtype=float)
    y_data = np.asarray(y_data, dtype=float)
    sigma_data = np.maximum(np.asarray(sigma_data, dtype=float), 1e-12)
    if not seeds:
        raise ValueError("Se necesita al menos una semilla para el ajuste.")

    p0, lower, upper = [], [], []
    min_width = max(float(channel_width) / 2.0, 1e-8)
    data_amp = max(float(np.nanmax(np.abs(y_data))), float(np.nanmedian(sigma_data)) * 5.0, 1e-8)
    amp_limit = max(10.0 * data_amp, 1.0)

    for seed in seeds:
        mu0 = float(seed["mu"])
        sign = int(seed.get("sign", 1))
        locked = bool(seed.get("locked"))
        previous_params = seed.get("previous_params")
        try:
            previous_params = np.asarray(previous_params, dtype=float).ravel()
        except Exception:
            previous_params = np.asarray([], dtype=float)
        expected_params = _profile_param_count(fit_choice)
        has_previous_params = (
            locked and previous_params.size == expected_params and np.all(np.isfinite(previous_params))
        )

        seed_center_window_kms = float(seed.get("center_window_kms", center_window_kms))
        if not np.isfinite(seed_center_window_kms) or seed_center_window_kms <= 0:
            seed_center_window_kms = float(center_window_kms)
        seed_max_fwhm_kms = float(seed.get("max_fwhm_kms", max_fwhm_kms))
        if not np.isfinite(seed_max_fwhm_kms) or seed_max_fwhm_kms <= 0:
            seed_max_fwhm_kms = float(max_fwhm_kms)
        nearest = int(np.argmin(np.abs(x_data - mu0)))
        measured = float(y_data[nearest])
        amp0 = measured
        if sign > 0:
            amp0 = max(abs(amp0), float(sigma_data[nearest]) * 3.0)
            amp_lb, amp_ub = 0.0, amp_limit
        else:
            amp0 = -max(abs(amp0), float(sigma_data[nearest]) * 3.0)
            amp_lb, amp_ub = -amp_limit, 0.0

        if bool(seed.get("manual_anchor")):
            center_half = max(mu0 * seed_center_window_kms / 299792.458, 0.35 * float(channel_width))
        else:
            center_half = max(mu0 * seed_center_window_kms / 299792.458, float(channel_width))

        fwhm_max_mhz = max(mu0 * seed_max_fwhm_kms / 299792.458, 3.0 * float(channel_width))
        widths = _width_guess_mhz(fit_choice, mu0)
        previous_fwhm = seed.get("initial_fwhm_mhz")
        try:
            previous_fwhm = float(previous_fwhm)
        except Exception:
            previous_fwhm = np.nan
        if np.isfinite(previous_fwhm) and previous_fwhm > 0:
            if fit_choice == "1":
                widths = (max(previous_fwhm / 2.354820045, min_width),)
            elif fit_choice == "2":
                widths = (max(previous_fwhm / 2.0, min_width),)
            else:
                half = max(previous_fwhm / 2.0, min_width)
                widths = (half, half)

        if has_previous_params:
            # Local-edit survivor: preserve identity/position, but do NOT freeze
            # the whole profile.  a81-a84 used epsilon-sized bounds for every
            # parameter; deleting one component therefore removed its flux while
            # the neighbours were mathematically unable to absorb any of the
            # remaining profile.  That made a single deletion look as if a large
            # fraction of the fit had vanished.
            #
            # Keep the centre strongly anchored (sub-channel motion only), while
            # allowing amplitude and width to adapt within conservative bounds.
            # This is a local constrained refit, not a new discovery/deblending
            # pass: detection_id and component count remain unchanged.
            amp0 = float(previous_params[0])
            mu0 = float(previous_params[1])
            center_slack = max(0.40 * float(channel_width), abs(mu0) * 0.12 / 299792.458, 1.0e-10)

            # Preserve the sign/polarity, but permit the amplitude to respond to
            # the deletion of a neighbouring component.  The global amp_limit
            # still prevents runaway solutions.
            if sign > 0:
                amp_lo = 0.0
                amp_hi = amp_limit
            else:
                amp_lo = -amp_limit
                amp_hi = 0.0

            if fit_choice in ("1", "2"):
                w0 = max(float(previous_params[2]), min_width)
                # Width can broaden/narrow enough to re-describe the local shape,
                # but cannot explode into a broad pseudo-baseline component.
                w_lo = max(min_width, 0.55 * w0)
                w_hi = max(w_lo * 1.01, min(1.85 * w0, fwhm_max_mhz / (2.354820045 if fit_choice == "1" else 2.0)))
                p0.extend([amp0, mu0, w0])
                lower.extend([amp_lo, mu0 - center_slack, w_lo])
                upper.extend([amp_hi, mu0 + center_slack, w_hi])
            else:
                s0 = max(float(previous_params[2]), min_width)
                g0 = max(float(previous_params[3]), min_width)
                s_lo = max(min_width, 0.55 * s0)
                g_lo = max(min_width, 0.55 * g0)
                width_cap = max(min_width * 1.01, fwhm_max_mhz / 2.0)
                s_hi = max(s_lo * 1.01, min(1.85 * s0, width_cap))
                g_hi = max(g_lo * 1.01, min(1.85 * g0, width_cap))
                p0.extend([amp0, mu0, s0, g0])
                lower.extend([amp_lo, mu0 - center_slack, s_lo, g_lo])
                upper.extend([amp_hi, mu0 + center_slack, s_hi, g_hi])
            continue

        if fit_choice == "1":
            max_w = max(fwhm_max_mhz / 2.354820045, min_width * 2.0)
            p0.extend([amp0, mu0, max(widths[0], min_width)])
            lower.extend([amp_lb, mu0 - center_half, min_width])
            upper.extend([amp_ub, mu0 + center_half, max_w])
        elif fit_choice == "2":
            max_w = max(fwhm_max_mhz / 2.0, min_width * 2.0)
            p0.extend([amp0, mu0, max(widths[0], min_width)])
            lower.extend([amp_lb, mu0 - center_half, min_width])
            upper.extend([amp_ub, mu0 + center_half, max_w])
        else:
            max_w = max(fwhm_max_mhz / 2.0, min_width * 2.0)
            p0.extend([amp0, mu0, max(widths[0], min_width), max(widths[1], min_width)])
            lower.extend([amp_lb, mu0 - center_half, min_width, min_width])
            upper.extend([amp_ub, mu0 + center_half, max_w, max_w])

    p0 = np.asarray(p0, dtype=float)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    p0 = np.minimum(np.maximum(p0, lower + 1e-12), upper - 1e-12)

    def residual_func(params):
        return (_multi_model(fit_choice, x_data, params) - y_data) / sigma_data

    result = least_squares(
        residual_func,
        p0,
        bounds=(lower, upper),
        loss="soft_l1",
        f_scale=1.0,
        max_nfev=20000,
    )
    params = result.x
    model = _multi_model(fit_choice, x_data, params)
    standardized = (y_data - model) / sigma_data
    chi2 = float(np.sum(standardized ** 2))
    n_obs = max(len(x_data), 1)
    n_params = len(params)
    bic = chi2 + n_params * np.log(n_obs)
    aic = chi2 + 2.0 * n_params
    pcov = _pcov_from_least_squares(result, n_obs=len(x_data))
    return {
        "params": params,
        "pcov": pcov,
        "model": model,
        "residual": y_data - model,
        "chi2": chi2,
        "bic": float(bic),
        "aic": float(aic),
        "success": bool(result.success),
        "message": str(result.message),
        "lower": lower,
        "upper": upper,
    }


def _component_params(fit_choice, params, index):
    ppc = _profile_param_count(fit_choice)
    return np.asarray(params[index * ppc:(index + 1) * ppc], dtype=float)


def _component_covariance(fit_choice, pcov, index):
    if pcov is None:
        return None
    ppc = _profile_param_count(fit_choice)
    return np.asarray(pcov[index * ppc:(index + 1) * ppc, index * ppc:(index + 1) * ppc], dtype=float)


def _seed_from_index(freq, y, idx, origin="auto", metric=None):
    metric = dict(metric or {})
    sign = 1 if float(y[idx]) >= 0 else -1
    return {
        "index": int(idx),
        "mu": float(freq[idx]),
        # Stable spectral seed used as the persistent edit anchor.  ``mu`` may
        # move during a local refit, but this value does not.
        "stable_seed_mhz": float(freq[idx]),
        "amp": float(y[idx]),
        "sign": int(sign),
        "polarity": "emission" if sign > 0 else "absorption",
        "origin": str(origin),
        **metric,
    }


def _candidate_addition(fit_choice, x_data, y_data, sigma_data, current_seeds, candidates, channel_width):
    best = None
    for candidate in candidates:
        try:
            trial_seeds = list(current_seeds) + [candidate]
            trial = fit_multi_components_robust(
                fit_choice, x_data, y_data, sigma_data, trial_seeds, channel_width
            )
        except Exception:
            continue
        if best is None or trial["bic"] < best["fit"]["bic"]:
            best = {"seed": candidate, "fit": trial}
    return best


def select_components_with_bic(
    fit_choice,
    x_data,
    y_data,
    sigma_data,
    seeds,
    channel_width,
    *,
    detection_sigma=4.0,
    delta_bic_min=6.0,
    max_components=8,
    residual_polarity="both",
    forbidden_freqs=None,
    allow_residual_search=True,
):
    """Selección hacia delante + búsqueda iterativa en residuales.

    Las semillas manuales son forzadas. Las automáticas se incorporan sólo si
    mejoran BIC al menos ``delta_bic_min``. Después se buscan componentes que
    aparezcan en el residual de la solución actual.
    """
    seeds = list(seeds)
    forbidden_freqs = [float(v) for v in (forbidden_freqs or []) if np.isfinite(float(v))]
    if not seeds:
        return None, [], []
    # User edits must be stable: components that already existed before a local
    # edit are treated as locked seeds.  They are refitted, but BIC cannot
    # silently discard the neighbours of the component the user removed.
    forced = [s for s in seeds if s.get("origin") == "manual" or bool(s.get("locked"))]
    auto = [s for s in seeds if s not in forced]
    selected = list(forced[:max_components])
    history = []

    if selected:
        current = fit_multi_components_robust(
            fit_choice, x_data, y_data, sigma_data, selected, channel_width
        )
        history.append({"n": len(selected), "bic": current["bic"], "aic": current["aic"], "reason": "manual"})
        # An isolated user-created manual detection is one requested component.
        # Do not manufacture a second component solely from residual searching.
        # If an independently detected automatic seed shares the group, normal
        # BIC deblending below remains available.
        if len(selected) == 1 and not auto:
            return current, selected, history
    else:
        best = _candidate_addition(
            fit_choice, x_data, y_data, sigma_data, [], auto, channel_width
        )
        if best is None:
            return None, [], history
        selected = [best["seed"]]
        auto = [s for s in auto if s is not best["seed"]]
        current = best["fit"]
        history.append({"n": 1, "bic": current["bic"], "aic": current["aic"], "reason": "seed"})

    # Agrega candidatos iniciales únicamente cuando el criterio estadístico los justifica.
    while auto and len(selected) < max_components:
        best = _candidate_addition(
            fit_choice, x_data, y_data, sigma_data, selected, auto, channel_width
        )
        if best is None:
            break
        improvement = float(current["bic"] - best["fit"]["bic"])
        if improvement < float(delta_bic_min):
            break
        selected.append(best["seed"])
        auto = [s for s in auto if s is not best["seed"]]
        current = best["fit"]
        history.append({"n": len(selected), "bic": current["bic"], "aic": current["aic"], "delta_bic": improvement, "reason": "seed"})

    # Busca líneas ocultas en los residuales. Se usa umbral algo menor, pero la
    # nueva componente debe superar BIC para sobrevivir.
    residual_iterations = 0
    while allow_residual_search and len(selected) < max_components and residual_iterations < 4:
        residual_iterations += 1
        residual = current["residual"]
        residual_sigma = max(3.0, float(detection_sigma) - 1.0)
        peaks, metrics, _, _ = detect_peaks_by_snr(
            residual,
            sigma_data,
            detection_sigma=residual_sigma,
            prominence_sigma=1.8,
            min_width_channels=2.0,
            min_distance_channels=2,
            multiscale=True,
            polarity=residual_polarity,
        )
        residual_candidates = []
        for j, idx in enumerate(peaks.tolist()):
            mu = float(x_data[idx])
            # A component explicitly removed by the user must not immediately
            # reappear through residual-search deblending in the same edit.
            if forbidden_freqs:
                block_tol = max(1.5 * float(channel_width), 1e-7)
                if any(abs(mu - fr) <= block_tol for fr in forbidden_freqs):
                    continue
            # No proponer un duplicado sobre un centro ya ajustado.  En
            # versiones anteriores se comparaba contra la semilla original
            # (seed["mu"]); una componente puede desplazarse durante el fit y
            # dejar que el buscador de residuales proponga una segunda semilla
            # casi encima de su centro FINAL.  Para M1, dos componentes cuya
            # separación cae por debajo de la resolución de un canal no son
            # detecciones independientes.
            current_centers = []
            try:
                for current_index in range(len(selected)):
                    current_centers.append(
                        float(_component_params(fit_choice, current["params"], current_index)[1])
                    )
            except Exception:
                current_centers = [float(seed["mu"]) for seed in selected]
            min_sep_mhz = max(
                float(channel_width),
                abs(mu) * 0.7 / 299792.458,
                1.0e-7,
            )
            if any(abs(mu - center) < min_sep_mhz for center in current_centers):
                continue
            metric = {
                key: (metrics[key][j].item() if hasattr(metrics[key][j], "item") else metrics[key][j])
                for key in metrics
            }
            residual_candidates.append(_seed_from_index(x_data, residual, idx, "residual", metric))
        if not residual_candidates:
            break
        best = _candidate_addition(
            fit_choice, x_data, y_data, sigma_data, selected, residual_candidates, channel_width
        )
        if best is None:
            break
        improvement = float(current["bic"] - best["fit"]["bic"])
        if improvement < float(delta_bic_min):
            break
        selected.append(best["seed"])
        current = best["fit"]
        history.append({"n": len(selected), "bic": current["bic"], "aic": current["aic"], "delta_bic": improvement, "reason": "residual"})

    return current, selected, history


def fit_single_component_robust(fit_choice, x_data, y_data, amp0, mu0, sigma0, channel_width, dv_max_kms=30.0):
    """Compatibilidad con llamadas antiguas; usa el nuevo motor multicomponente."""
    sigma_data = np.full_like(np.asarray(y_data, dtype=float), max(_robust_sigma(y_data), 1e-6))
    seed = {"mu": float(mu0), "amp": float(amp0), "sign": 1 if amp0 >= 0 else -1, "origin": "auto"}
    fit = fit_multi_components_robust(
        fit_choice, x_data, y_data, sigma_data, [seed], channel_width, max_fwhm_kms=dv_max_kms
    )
    return fit["params"], fit["pcov"]

def _velocity_axis_spec(metadata: dict | None = None):
    """Serializable M1 frequency->velocity transform.

    CLASS uses its native spectral calibration. Generic spectra require an
    explicit reference_frequency metadata field; VLSR/rest_frequency never
    define the generic M1 display axis.
    """
    meta = dict(metadata or {})
    def finite_float(value):
        try:
            value = float(value)
            return value if np.isfinite(value) else None
        except Exception:
            return None
    f0=finite_float(meta.get("class_reference_frequency_mhz"))
    v0=finite_float(meta.get("class_reference_velocity_kms"))
    df=finite_float(meta.get("class_frequency_step_mhz"))
    dv=finite_float(meta.get("class_velocity_step_kms"))
    if f0 is not None and v0 is not None and df not in (None,0.0) and dv is not None:
        return {"mode":"linear","f0_mhz":f0,"v0_kms":v0,"slope_kms_per_mhz":dv/df,"source":"class_header"}
    ref=finite_float(meta.get("spectral_axis_reference_frequency_mhz"))
    if ref is not None and ref>0:
        return {"mode":"radio","f0_mhz":ref,"c_kms":299792.458,"source":"explicit_reference"}
    return None


def _intensity_axis_title(metadata: dict | None = None, language: str = "es") -> str:
    """Build a scientifically explicit intensity-axis label.

    ``bunit`` is preserved from FITS/ASCII/CLASS metadata whenever available.
    ASCII readers assign K as the explicit CZSpec working default when the file
    does not declare an intensity unit; the provenance is retained in metadata.
    """
    meta = dict(metadata or {})
    unit = str(
        meta.get("bunit")
        or meta.get("intensity_unit")
        or meta.get("input_intensity_unit")
        or ""
    ).strip()
    if unit:
        return ("Intensidad" if language == "es" else "Intensity") + f" [{unit}]"
    return "Intensidad [K]" if language == "es" else "Intensity [K]"


def _intensity_unit_text(metadata: dict | None = None) -> str:
    meta = dict(metadata or {})
    return str(meta.get("bunit") or meta.get("intensity_unit") or meta.get("input_intensity_unit") or "").strip()


def _add_velocity_axis(fig, freq, metadata: dict | None = None):
    """Añade un eje superior de velocidad sin dibujar referencias VLSR.

    El eje superior usa la relación espectral del encabezado CLASS cuando están
    disponibles FREQUENCY/FREQ_STEP/VELOCITY/VELO_STEP; en otros formatos usa
    la convención Doppler de radio respecto a la frecuencia de referencia.

    A partir de alpha.56 la transformación también se guarda en ``layout.meta``.
    El visor local recalcula los ticks de velocidad sobre el rango de frecuencia
    *visible*, por lo que los valores no desaparecen al hacer zoom profundo.
    """
    meta = dict(metadata or {})
    freq = np.asarray(freq, dtype=float)
    finite = freq[np.isfinite(freq)]
    if finite.size < 2:
        return fig
    lo, hi = float(np.nanmin(finite)), float(np.nanmax(finite))
    spec = _velocity_axis_spec(meta)
    tickvals = np.linspace(lo, hi, 7)
    try:
        velocities = np.asarray(velocity_axis_from_metadata(tickvals, meta), dtype=float)
    except Exception:
        velocities = None

    if spec is not None and velocities is not None and np.all(np.isfinite(velocities)):
        # Descriptor usado por plotly_runtime.py para refrescar los ticks al zoom.
        current_meta = dict(fig.layout.meta or {}) if fig.layout.meta else {}
        current_meta["czspec_velocity_axis"] = spec
        fig.update_layout(meta=current_meta)

        # Plotly no renderiza de forma fiable un eje overlay sin una traza que lo
        # referencie. Esta traza invisible fuerza la presencia de x2 sin afectar
        # datos, leyenda ni hover.
        fig.add_trace(
            go.Scatter(
                x=tickvals,
                y=np.full_like(tickvals, np.nan, dtype=float),
                xaxis="x2",
                yaxis="y",
                mode="markers",
                marker=dict(opacity=0.0, size=1),
                hoverinfo="skip",
                showlegend=False,
                name="__velocity_axis__",
            )
        )
        fig.update_layout(
            xaxis2=dict(
                title=dict(text="Velocidad [km/s]", standoff=8),
                overlaying="x",
                side="top",
                anchor="y",
                matches="x",
                range=[lo, hi],
                tickmode="array",
                tickvals=tickvals.tolist(),
                ticktext=[f"{v:.1f}" for v in velocities],
                showgrid=False,
                zeroline=False,
                showline=True,
                linecolor="#94A3B8",
                linewidth=1,
                ticks="outside",
                ticklen=4,
                tickcolor="#94A3B8",
                automargin=True,
            )
        )

    # M1 no dibuja VLSR sobre el espectro. El valor puede conservarse en los
    # metadatos para otros módulos, pero no debe modificar el autorange ni
    # confundirse con la transformación frecuencia→velocidad del visor.
    return fig


def build_plotly_figure(
    freq,
    inten,
    base_fit,
    y_corr,
    peaks,
    file_path,
    preserve_ranges=None,
    extra_traces=None,
    plot_styles=None,
    input_metadata=None,
    display_name: str | None = None,
    language: str = "es",
    peak_items=None,
):
    styles = normalize_plot_styles(plot_styles)
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=freq,
            y=inten,
            mode="lines",
            name="Espectro corregido por η",
            line=dict(**styles["spectrum"]),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=freq,
            y=base_fit,
            mode="lines",
            name="Ajuste de base",
            line=dict(**styles["baseline"]),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=freq,
            y=y_corr,
            mode="lines",
            name="Espectro corregido por base",
            line=dict(**styles["corrected"]),
        )
    )

    if len(peaks) > 0:
        intensity_unit = _intensity_unit_text(input_metadata)
        intensity_hover = ("Intensity" if language == "en" else "Intensidad") + "=%{y:.5g}" + (f" {intensity_unit}" if intensity_unit else "")
        # customdata carries the immutable detection_id.  L1/L2/... is only a
        # visual label and may change after sorting or deleting a component.
        aligned_items = list(peak_items or [])
        if len(aligned_items) != len(peaks):
            aligned_items = [{} for _ in range(len(peaks))]
        detection_customdata = []
        marker_x = []
        marker_y = []
        for visual_index, (peak_idx, item) in enumerate(zip(np.asarray(peaks, dtype=int), aligned_items), start=1):
            detection_id = str(item.get("detection_id") or "")
            seed_freq = float(item.get("freq", freq[int(peak_idx)]))
            fit_freq = item.get("fit_freq", freq[int(peak_idx)])
            try:
                fit_freq = float(fit_freq)
            except Exception:
                fit_freq = float(freq[int(peak_idx)])
            if not np.isfinite(fit_freq):
                fit_freq = float(freq[int(peak_idx)])

            # A detection marker is an observed spectral point, not the peak
            # amplitude of one mathematical component inside a deblended sum.
            # alpha.82 placed the marker at params[0], which made markers float
            # below blended profiles (and visually suggested spurious lines).
            # Preserve the precise fitted centre for interaction/ID purposes,
            # but place the marker on the baseline-corrected observed spectrum,
            # reproducing the visual semantics used by the older M1 renderer.
            observed_y = float(np.interp(fit_freq, np.asarray(freq, dtype=float), np.asarray(y_corr, dtype=float)))
            if not np.isfinite(observed_y):
                observed_y = float(y_corr[int(peak_idx)])
            line_number = item.get("line_no", visual_index)
            try:
                line_number = int(line_number)
            except Exception:
                line_number = int(visual_index)
            marker_x.append(fit_freq)
            marker_y.append(observed_y)
            try:
                fit_amp = float(item.get("fit_amp", np.nan))
            except Exception:
                fit_amp = np.nan
            detection_customdata.append([detection_id, line_number, seed_freq, fit_amp])
        marker_x = np.asarray(marker_x, dtype=float)
        marker_y = np.asarray(marker_y, dtype=float)
        fig.add_trace(
            go.Scatter(
                x=marker_x,
                y=marker_y,
                mode="markers",
                name="Detections" if language == "en" else "Detecciones",
                customdata=detection_customdata,
                hovertemplate=(
                    "L%{customdata[1]}<br>ν=%{x:.6f} MHz<br>" + intensity_hover +
                    ("<br>Fitted peak=%{customdata[3]:.5g}" if language == "en" else "<br>Pico ajustado=%{customdata[3]:.5g}") +
                    (f" {intensity_unit}" if intensity_unit else "") + "<extra></extra>"
                ),
                marker=dict(**styles["detections"]),
                meta={"czspec_role": "detection"},
            )
        )
        # Labels remain visible without requiring hover.  A -45 degree angle
        # produces the requested rising '/' visual orientation.
        for visual_index, (mx, my, item) in enumerate(zip(marker_x, marker_y, aligned_items), start=1):
            line_no = item.get("line_no", visual_index)
            try:
                line_no = int(line_no)
            except Exception:
                line_no = int(visual_index)
            fig.add_annotation(
                x=float(mx), y=float(my),
                text=f"L{line_no}", showarrow=False, textangle=-45, captureevents=True,
                xanchor="left", yanchor="bottom", xshift=5,
                yshift=7 + 9 * ((line_no - 1) % 4),
                font=dict(size=10, color=str(styles["detections"].get("color", "#7C3AED"))),
                bgcolor="rgba(255,255,255,0.55)",
            )

    display_title = display_name or os.path.basename(file_path)
    fig.update_layout(
        title=(
            f"Detección y ajuste de líneas espectrales - {display_title}"
            if language == "es" else
            f"Spectral-line detection and fitting - {display_title}"
        ),
        xaxis_title="Frecuencia [MHz]" if language == "es" else "Frequency [MHz]",
        yaxis_title=_intensity_axis_title(input_metadata, language),
        template="plotly_white",
        uirevision="spectral-editor",
        # The legend is intentionally compact and horizontal.  Individual fit
        # traces remain visible/hoverable but are represented by two category
        # entries (components vs final profiles), so dozens of fitted lines do
        # not consume the scientific plotting area.
        margin=dict(l=55, r=55, t=112, b=112),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.17,
            xanchor="left",
            x=0.0,
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor="rgba(0,0,0,0.12)",
            borderwidth=1,
            font=dict(size=10),
            groupclick="togglegroup",
        ),
    )

    has_fit_components = False
    has_final_profiles = False
    for raw_trace in (extra_traces or []):
        tr = dict(raw_trace)
        meta = dict(tr.get("meta") or {})
        role = str(meta.get("czspec_role") or "")
        if role == "fit_component":
            has_fit_components = True
            tr["showlegend"] = False
            tr["legendgroup"] = "czspec_fit_components"
        elif role in {"fit", "fit_sum"}:
            has_final_profiles = True
            tr["showlegend"] = False
            tr["legendgroup"] = "czspec_final_profiles"
        fig.add_trace(go.Scatter(**tr))

    # One legend handle per scientific fit category.  The real L1/L2/... names
    # remain attached to the actual traces for hover/inspection.
    if has_fit_components:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="lines",
            name="Componentes individuales" if language == "es" else "Individual components",
            line=dict(**styles.get("fit_components", styles["fits"])),
            showlegend=True, hoverinfo="skip", legendgroup="czspec_fit_components",
            meta={"czspec_role": "legend_fit_components"},
        ))
    if has_final_profiles:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="lines",
            name="Perfiles finales" if language == "es" else "Final profiles",
            line=dict(**styles["fits"]),
            showlegend=True, hoverinfo="skip", legendgroup="czspec_final_profiles",
            meta={"czspec_role": "legend_final_profiles"},
        ))

    if preserve_ranges:
        xr = preserve_ranges.get("xaxis_range") if isinstance(preserve_ranges, dict) else None
        yr = preserve_ranges.get("yaxis_range") if isinstance(preserve_ranges, dict) else None

        if xr and len(xr) == 2:
            fig.update_xaxes(range=xr)

        if yr and len(yr) == 2:
            fig.update_yaxes(range=yr)

    fig.update_xaxes(showline=True, linecolor="#94A3B8", linewidth=1, ticks="outside", ticklen=4, tickcolor="#94A3B8")
    fig.update_yaxes(showline=True, linecolor="#94A3B8", linewidth=1, ticks="outside", ticklen=4, tickcolor="#94A3B8")
    _add_velocity_axis(fig, freq, input_metadata)
    return fig

def build_plotly_html(
    freq,
    inten,
    base_fit,
    y_corr,
    peaks,
    file_path,
    preserve_ranges=None,
    plot_styles=None,
):
    fig = build_plotly_figure(
        freq,
        inten,
        base_fit,
        y_corr,
        peaks,
        file_path,
        preserve_ranges,
        plot_styles=plot_styles,
    )
    return fig.to_html(include_plotlyjs=True)

def load_raw_spectrum(file_path: str, plot_styles=None, display_name: str | None = None, input_metadata: dict | None = None, language: str = "es"):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")

    freq, inten, read_meta = read_spectrum_file(file_path)
    read_meta = merge_metadata(read_meta, input_metadata)

    styles = normalize_plot_styles(plot_styles)
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=freq,
            y=inten,
            mode="lines",
            name="Espectro original" if language == "es" else "Original spectrum",
            line=dict(**styles["spectrum"]),
        )
    )

    fig.update_layout(
        title=(f"Espectro original - {display_name or os.path.basename(file_path)}"
               if language == "es" else
               f"Original spectrum - {display_name or os.path.basename(file_path)}"),
        xaxis_title="Frecuencia [MHz]" if language == "es" else "Frequency [MHz]",
        yaxis_title=_intensity_axis_title(read_meta, language),
        template="plotly_white",
        margin=dict(l=55, r=25, t=116, b=70),
        uirevision="spectral-editor",
    )
    fig.update_xaxes(showline=True, linecolor="#94A3B8", linewidth=1, ticks="outside", ticklen=4, tickcolor="#94A3B8")
    fig.update_yaxes(showline=True, linecolor="#94A3B8", linewidth=1, ticks="outside", ticklen=4, tickcolor="#94A3B8")
    _add_velocity_axis(fig, freq, read_meta)

    return {
        "freq": freq,
        "inten": inten,
        "plot_json": fig.to_json(),
        "plot_html": fig.to_html(include_plotlyjs=True),
        **read_meta,
    }


def _comparison_ranges_overlap(spectra) -> bool:
    """Indica si las bandas comparten una fracción útil de frecuencia."""

    ranges = []
    for item in spectra:
        values = np.asarray(item["freq"], dtype=float)
        values = values[np.isfinite(values)]
        if values.size < 2:
            return False
        ranges.append((float(values.min()), float(values.max())))
    common_low = max(low for low, _ in ranges)
    common_high = min(high for _, high in ranges)
    common_width = max(0.0, common_high - common_low)
    narrowest_width = min(max(high - low, 0.0) for low, high in ranges)
    return narrowest_width > 0 and common_width / narrowest_width >= 0.35


def build_spectrum_comparison(
    spectra,
    plot_styles=None,
    columns: int = 4,
    layout_mode: str = "auto",
    share_x: bool = False,
    share_y: bool = True,
    show_sum: bool = False,
    sum_styles: list[dict] | None = None,
    axis_config: dict | None = None,
    content_label: str = "crudos",
    language: str = "es",
):
    """Build a scientifically conservative multi-spectrum comparison.

    Frequency in MHz remains the canonical coordinate. Display units/titles are
    applied as tick labels, so multiple subplots can use independent CLASS
    velocity calibrations without altering the underlying spectral samples.
    """
    if not spectra:
        raise ValueError("No hay espectros para comparar.")

    palette = [
        "#1D6EEB", "#E67E22", "#16A085", "#D64550", "#8E5CE6",
        "#2D3436", "#DB2777", "#65A30D", "#0891B2", "#7C3AED",
    ]
    combined_palette = ["#7C3AED", "#059669", "#B45309", "#BE123C", "#0369A1", "#4D7C0F"]
    default_style = normalize_plot_styles(plot_styles)["spectrum"]
    cfg = dict(axis_config or {})
    titles = [str(item.get("name") or f"Espectro {i+1}") for i, item in enumerate(spectra)]
    en = language == "en"
    primary_kind = str(cfg.get("primary_spectral") or "frequency")
    secondary_kind = str(cfg.get("secondary_spectral") or "none")
    if secondary_kind == primary_kind:
        secondary_kind = "none"
    secondary_intensity_requested = str(cfg.get("secondary_intensity_unit") or "none")
    styles_sum = list(sum_styles or [])

    def _source_unit(item):
        meta = dict(item.get("metadata") or {})
        return normalize_intensity_unit(meta.get("bunit") or meta.get("intensity_unit") or meta.get("input_intensity_unit"))

    def _display_intensity(index):
        item = spectra[index]
        yy = np.asarray(item["inten"], dtype=float)
        source = _source_unit(item)
        requested = str(cfg.get("intensity_unit") or "native")
        conversion = intensity_conversion_factor(source, requested)
        if requested == "native":
            return yy, source, 1.0
        if conversion is None and source in {"K","mK","µK"} and requested in {"Jy/sr","MJy/sr","W m⁻² Hz⁻¹ sr⁻¹"}:
            # Rayleigh-Jeans brightness conversion evaluated channel by channel.
            freq=np.asarray(item["freq"],dtype=float); k_b=1.380649e-23; c=299792458.0
            temp_scale={"K":1.0,"mK":1e-3,"µK":1e-6}[source]
            out_scale={"Jy/sr":1e26,"MJy/sr":1e20,"W m⁻² Hz⁻¹ sr⁻¹":1.0}[requested]
            factor=temp_scale*(2.0*k_b*(freq*1e6)**2/(c*c))*out_scale
            return yy*factor, requested, 1.0
        if conversion is None:
            return yy, source, 1.0
        factor, target = conversion
        return yy * float(factor), target, float(factor)

    display_cache = [_display_intensity(i) for i in range(len(spectra))]
    effective_units = {u for _, u, _ in display_cache if u}
    common_unit = next(iter(effective_units)) if len(effective_units) == 1 else ""

    def _append_unit(text: str, unit: str) -> str:
        text = str(text or "").strip()
        if not text:
            return text
        if not unit or "[" in text:
            return text
        return f"{text} [{unit}]"

    def _x_preset_base(kind: str, preset: str) -> str:
        preset = str(preset or "auto")
        symbols = {"nu":"ν", "v":"v", "dv":"Δv", "lambda":"λ"}
        if preset in symbols:
            return symbols[preset]
        if preset == "frequency": return "Frequency" if en else "Frecuencia"
        if preset == "velocity": return "Velocity" if en else "Velocidad"
        if preset == "wavelength": return "Wavelength" if en else "Longitud de onda"
        if kind == "velocity": return "Velocity" if en else "Velocidad"
        if kind == "wavelength": return "Wavelength" if en else "Longitud de onda"
        return "Frequency" if en else "Frecuencia"

    def _y_preset_base(preset: str) -> str:
        table = {
            "intensity": "Intensity" if en else "Intensidad",
            "antenna_temperature": "Antenna temperature" if en else "Temperatura de antena",
            "ta_star": "T<sub>A</sub>*", "tmb": "T<sub>MB</sub>", "tb": "T<sub>B</sub>",
        }
        return table.get(str(preset or "auto"), "Intensity" if en else "Intensidad")

    def _frequency_unit():
        requested = str(cfg.get("frequency_unit") or "auto")
        return requested if requested in {"Hz","kHz","MHz","GHz","THz"} else "MHz"

    def _wavelength_unit_shown():
        unit = str(cfg.get("wavelength_unit") or "mm")
        return "µm" if unit == "um" else ("Å" if unit == "angstrom" else unit)

    def _unit_for_kind(kind: str) -> str:
        if kind == "velocity": return str(cfg.get("velocity_unit") or "km/s")
        if kind == "wavelength": return _wavelength_unit_shown()
        return _frequency_unit()

    def _x_title(kind: str, *, secondary=False) -> str:
        custom_key = "secondary_axis_title" if secondary else "primary_axis_title"
        preset_key = "secondary_axis_title_preset" if secondary else "primary_axis_title_preset"
        custom = str(cfg.get(custom_key) or "").strip()
        base = custom or _x_preset_base(kind, str(cfg.get(preset_key) or "auto"))
        return _append_unit(base, _unit_for_kind(kind))

    y_custom = str(cfg.get("intensity_axis_title") or "").strip()
    y_title = _append_unit(y_custom or _y_preset_base(str(cfg.get("intensity_axis_title_preset") or "auto")), common_unit)

    def _spectral_values(freqs, kind: str, metadata):
        freqs = np.asarray(freqs, dtype=float)
        if kind == "frequency":
            unit = _frequency_unit()
            scale = {"Hz":1e6,"kHz":1e3,"MHz":1.0,"GHz":1e-3,"THz":1e-6}[unit]
            return freqs * scale
        if kind == "velocity":
            try:
                vals = np.asarray(velocity_axis_from_metadata(freqs, dict(metadata or {})), dtype=float)
            except Exception:
                return None
            if str(cfg.get("velocity_unit") or "km/s") == "m/s": vals = vals * 1000.0
            return vals
        if kind == "wavelength":
            unit = str(cfg.get("wavelength_unit") or "mm")
            with np.errstate(divide="ignore", invalid="ignore"):
                factors = {"m":299.792458,"cm":29979.2458,"mm":299792.458,
                           "um":299792458.0,"nm":299792458000.0,"angstrom":2997924580000.0}
                return factors.get(unit,299792.458) / freqs
        return None

    def trace_for(index, *, showlegend):
        item = spectra[index]
        frequency = np.asarray(item["freq"], dtype=float)
        intensity, unit, _ = display_cache[index]
        ylabel = unit or ("input" if en else "entrada")
        return go.Scatter(
            x=frequency, y=intensity, mode="lines", name=titles[index], showlegend=showlegend,
            line={"color":item.get("color") or palette[index % len(palette)],
                  "width":float(item.get("width", default_style.get("width",1.35))),
                  "dash":item.get("dash") or default_style.get("dash","solid")},
            hovertemplate=f"{titles[index]}<br>ν=%{{x:.6f}} MHz<br>Y=%{{y:.5g}} {ylabel}<extra></extra>",
        )

    def fit_traces_for(index):
        item=spectra[index]; traces=[]; scale=display_cache[index][2]
        for fit_index,fit in enumerate(item.get("fit_traces") or []):
            role=str((fit.get("meta") or {}).get("czspec_role") or "")
            if role not in {"fit","fit_sum"}: continue
            xv,yv=fit.get("x"),fit.get("y")
            if xv is None or yv is None: continue
            line=dict(fit.get("line") or {}); line.setdefault("width",1.5); line.setdefault("dash","dash")
            traces.append(go.Scatter(x=np.asarray(xv,dtype=float),y=np.asarray(yv,dtype=float)*scale,
                mode="lines",name=str(fit.get("name") or f"{titles[index]} · ajuste {fit_index+1}"),showlegend=False,
                hovertemplate=f"{titles[index]} · ajuste<br>ν=%{{x:.6f}} MHz<br>Y=%{{y:.5g}}<extra></extra>",line=line))
        return traces

    def detection_trace_for(index):
        points=list(spectra[index].get("detection_points") or [])
        if not points:
            return None
        scale=display_cache[index][2]
        xs=[]; ys=[]; labels=[]
        for point in points:
            try:
                xs.append(float(point.get("x")))
                ys.append(float(point.get("y"))*scale)
                labels.append(f"L{int(point.get('line'))}")
            except Exception:
                continue
        if not xs:
            return None
        det_style=normalize_plot_styles(plot_styles)["detections"]
        return go.Scatter(
            x=xs,y=ys,mode="markers+text",text=labels,textposition="top right",
            textfont={"size":9,"color":det_style.get("color","#7C3AED")},
            marker={"color":det_style.get("color","#7C3AED"),"size":max(4,float(det_style.get("size",7.0))*0.82)},
            name=("Detections" if en else "Detecciones"),showlegend=False,
            hovertemplate=("%{text}<br>ν=%{x:.6f} MHz<br>Y=%{y:.5g}<extra></extra>"),
            meta={"czspec_role":"detection"},
        )

    def _sum_style(style_index: int) -> dict:
        saved = styles_sum[style_index] if style_index < len(styles_sum) and isinstance(styles_sum[style_index],dict) else {}
        return {"color":saved.get("color") or combined_palette[style_index % len(combined_palette)],
                "width":float(saved.get("width",2.2)),"dash":saved.get("dash") or "solid"}

    def _plain_tick(value) -> str:
        """Format axis ticks without scientific e-notation for publication plots."""
        try:
            value=float(value)
        except Exception:
            return str(value)
        if not np.isfinite(value):
            return ""
        # Positional formatting preserves useful decimals while avoiding values
        # such as 1.4277e+05 in MHz/velocity comparison axes.
        return np.format_float_positional(value, precision=7, unique=False, fractional=False, trim="-")

    def combined_trace(indices, name=None, style_index=0):
        """Build one continuous combined spectrum using a mean in overlaps.

        Outside overlap regions the available spectrum is preserved unchanged.
        Where two or more spectra cover the same frequency, their interpolated
        intensities are averaged rather than summed, so the combined product
        never creates artificial line amplitudes merely because bands overlap.
        """
        if not indices:
            return None
        units={display_cache[i][1] for i in indices if display_cache[i][1]}
        if len(units)>1:
            return None
        grids=[]
        native_steps=[]
        prepared=[]
        for i in indices:
            x=np.asarray(spectra[i]["freq"],dtype=float)
            y=np.asarray(display_cache[i][0],dtype=float)
            good=np.isfinite(x)&np.isfinite(y)
            x=x[good]; y=y[good]
            if x.size<2:
                continue
            order=np.argsort(x); x=x[order]; y=y[order]
            # Remove duplicate x samples before np.interp.
            ux, keep=np.unique(x, return_index=True); x=ux; y=y[keep]
            if x.size<2:
                continue
            dx=np.diff(x); dx=dx[np.isfinite(dx)&(dx>0)]
            if dx.size:
                native_steps.append(float(np.nanmedian(dx)))
            prepared.append((x,y))
            grids.append(x)
        if not grids:
            return None
        grid=np.unique(np.concatenate(grids))
        total=np.zeros(grid.size,dtype=float)
        count=np.zeros(grid.size,dtype=int)
        for x,y in prepared:
            inside=(grid>=x[0])&(grid<=x[-1])
            if not np.any(inside):
                continue
            total[inside]+=np.interp(grid[inside],x,y)
            count[inside]+=1
        combined=np.full(grid.size,np.nan,dtype=float)
        valid=count>0
        combined[valid]=total[valid]/count[valid]
        if not np.any(np.isfinite(combined)):
            return None

        # Explicitly break the line across uncovered frequency gaps.  A union
        # grid alone has no sample inside a gap, so Plotly would otherwise draw
        # a misleading straight segment from one band to the next.
        xout=[]; yout=[]
        typical_step=float(np.nanmedian(native_steps)) if native_steps else np.nan
        for k,(xx,yy) in enumerate(zip(grid,combined)):
            if k and np.isfinite(typical_step):
                gap=float(xx-grid[k-1])
                if gap>max(5.0*typical_step,1e-9):
                    xout.append(float(0.5*(grid[k-1]+xx))); yout.append(np.nan)
            xout.append(float(xx)); yout.append(float(yy) if np.isfinite(yy) else np.nan)
        return go.Scatter(
            x=xout,y=yout,mode="lines",
            name=name or ("Combined" if en else "Combinado"),
            line=_sum_style(style_index),showlegend=True,
        )

    def contiguous_groups():
        ranges=[]
        for i,item in enumerate(spectra):
            x=np.asarray(item["freq"],dtype=float);x=x[np.isfinite(x)]
            if x.size:ranges.append((float(x.min()),float(x.max()),i))
        ranges.sort();groups=[]
        for lo,hi,i in ranges:
            if not groups: groups.append({"lo":lo,"hi":hi,"indices":[i]});continue
            g=groups[-1]; width=max(g["hi"]-g["lo"],hi-lo,1e-12); tolerance=max(width*0.002,1e-6)
            if lo<=g["hi"]+tolerance: g["hi"]=max(g["hi"],hi);g["indices"].append(i)
            else: groups.append({"lo":lo,"hi":hi,"indices":[i]})
        return groups

    mode=str(layout_mode or "auto").strip().lower()
    if mode=="overlay": mode="continuous"  # backwards-compatible a87 setting
    if mode=="auto":
        mode="aligned" if len(spectra)<=3 else "grid"
    if mode not in {"continuous","aligned","grid","stitched"}: mode="grid"

    def axis_key(prefix,n): return prefix+"axis"+("" if n==1 else str(n))
    def axis_ref(prefix,n): return prefix+("" if n==1 else str(n))

    def _panel_axis_style():
        return dict(showline=True,linecolor="#94A3B8",linewidth=1,ticks="outside",ticklen=4,tickcolor="#94A3B8",showgrid=True,gridcolor="#E8EEF6",automargin=True)

    def configure_axes(fig, panel_specs):
        base_count=max((p["panel"] for p in panel_specs),default=0)
        max_col=max((int(p.get("col",1)) for p in panel_specs),default=1)
        layout_json=fig.layout.to_plotly_json()
        for spec in panel_specs:
            panel=spec["panel"];lo,hi=spec["range"];rep=spec["rep"];indices=spec["indices"]
            if not(np.isfinite(lo) and np.isfinite(hi) and lo!=hi):continue
            ticks=np.linspace(lo,hi,5 if max_col>1 else 6)
            pvals=_spectral_values(ticks,primary_kind,spectra[rep].get("metadata"))
            actual_primary=primary_kind
            if pvals is None or not np.all(np.isfinite(pvals)):
                actual_primary="frequency";pvals=_spectral_values(ticks,"frequency",spectra[rep].get("metadata"))
            col=int(spec.get("col",1))
            primary_ticktext=[_plain_tick(v) for v in pvals]
            if max_col>1 and primary_ticktext:
                if col>1: primary_ticktext[0]=""
                if col<max_col: primary_ticktext[-1]=""
            pk=axis_key("x",panel); existing=dict(layout_json.get(pk,{}) or {})
            existing.update(_panel_axis_style()); existing.update({"tickmode":"array","tickvals":ticks.tolist(),"ticktext":primary_ticktext,"tickfont":{"size":9},"title":{"text":_x_title(actual_primary)},"range":[lo,hi],"autorange":False})
            fig.layout[pk]=existing
            yk=axis_key("y",panel); yexisting=dict(layout_json.get(yk,{}) or {}); yexisting.update(_panel_axis_style())
            if panel==1 or not share_y: yexisting["title"]={"text":y_title}
            fig.layout[yk]=yexisting

            # secondary spectral coordinate
            if secondary_kind not in {"none",actual_primary}:
                svals=_spectral_values(ticks,secondary_kind,spectra[rep].get("metadata"))
                if svals is not None and np.all(np.isfinite(svals)):
                    sec_no=base_count+panel; sk=axis_key("x",sec_no)
                    secondary_ticktext=[_plain_tick(v) for v in svals]
                    if max_col>1 and secondary_ticktext:
                        if col>1: secondary_ticktext[0]=""
                        if col<max_col: secondary_ticktext[-1]=""
                    fig.layout[sk]=dict(overlaying=axis_ref("x",panel),side="top",anchor=axis_ref("y",panel),tickmode="array",
                        tickvals=ticks.tolist(),ticktext=secondary_ticktext,tickfont={"size":9},title={"text":_x_title(secondary_kind,secondary=True)},
                        showgrid=False,showline=True,linecolor="#94A3B8",linewidth=1,ticks="outside",ticklen=4,tickcolor="#94A3B8",automargin=True,range=[lo,hi],autorange=False)
                    fig.add_trace(go.Scatter(x=[lo,hi],y=[0,0],mode="markers",marker={"opacity":0,"size":1},showlegend=False,hoverinfo="skip",
                        name="__czspec_cmp_secondary__",xaxis=axis_ref("x",sec_no),yaxis=axis_ref("y",panel)))

            # Secondary Y is a display scale. Prefix-family conversions are
            # exact constant factors. Temperature<->radiance needs an explicit
            # reference frequency, so comparisons use the centre of each panel
            # and state that reference in the axis title. In stitched mode only
            # the outermost panel gets Y2; otherwise an interior Y2 collides
            # with the next panel's primary Y axis at the spectral break.
            effective=display_cache[rep][1]
            secondary_target = _source_unit(spectra[rep]) if secondary_intensity_requested == "native" else secondary_intensity_requested
            conv=intensity_conversion_factor(effective,secondary_target)
            reference_frequency_mhz=None
            if secondary_intensity_requested not in {"","none"} and conv is None:
                reference_frequency_mhz=0.5*(float(lo)+float(hi))
                conv=intensity_conversion_factor_at_frequency(effective,secondary_target,reference_frequency_mhz)
            allow_secondary_y = bool(spec.get("secondary_y_allowed", True))
            if allow_secondary_y and secondary_intensity_requested not in {"","none"} and conv is not None and conv[1]!=effective:
                factor,target=conv; local=[]
                for j in indices:
                    arr=np.asarray(display_cache[j][0],dtype=float);local.extend(arr[np.isfinite(arr)].tolist())
                if local:
                    yl,yh=float(np.nanmin(local)),float(np.nanmax(local))
                    if yl==yh: yh=yl+1.0
                    yt=np.linspace(yl,yh,6); sec_no=base_count+panel; sk=axis_key("y",sec_no)
                    ycustom=str(cfg.get("secondary_intensity_title") or "").strip()
                    ybase=ycustom or _y_preset_base(str(cfg.get("secondary_intensity_title_preset") or "auto"))
                    title2=_append_unit(ybase,str(target))
                    if reference_frequency_mhz is not None:
                        ref_label=(f"{reference_frequency_mhz/1000.0:.3f} GHz" if reference_frequency_mhz>=1000 else f"{reference_frequency_mhz:.3f} MHz")
                        title2 += f" @ ν={ref_label}"
                    fig.layout[sk]=dict(overlaying=axis_ref("y",panel),side="right",anchor=axis_ref("x",panel),tickmode="array",tickvals=yt.tolist(),
                        ticktext=[_plain_tick(v*factor) for v in yt],title={"text":title2},showgrid=False,showline=True,linecolor="#94A3B8",linewidth=1,
                        ticks="outside",ticklen=4,tickcolor="#94A3B8",automargin=True,range=[yl,yh],autorange=False)
                    x_helper=0.5*(float(lo)+float(hi))
                    fig.add_trace(go.Scatter(x=[x_helper,x_helper],y=[yl,yh],mode="markers",marker={"opacity":0,"size":1},showlegend=False,hoverinfo="skip",
                        name="__czspec_cmp_secondary_y__",xaxis=axis_ref("x",panel),yaxis=axis_ref("y",sec_no)))

    def tidy_titles(fig):
        # Keep subplot titles inside their own panel; this avoids collisions with
        # the top secondary velocity/wavelength coordinate.
        title_set=set(titles)
        for ann in list(fig.layout.annotations or []):
            if str(getattr(ann,"text","") or "") in title_set:
                ann.update(font={"size":11,"color":"#334155"},yshift=-14,bgcolor="rgba(255,255,255,0.78)",borderpad=2)

    panel_specs=[]
    if mode=="continuous":
        figure=go.Figure()
        for i in range(len(spectra)):
            figure.add_trace(trace_for(i,showlegend=True))
            for ft in fit_traces_for(i): figure.add_trace(ft)
            dt=detection_trace_for(i)
            if dt is not None: figure.add_trace(dt)
        if show_sum:
            st=combined_trace(list(range(len(spectra))),style_index=0)
            if st is not None:figure.add_trace(st)
        allf=np.concatenate([np.asarray(it["freq"],dtype=float) for it in spectra]);allf=allf[np.isfinite(allf)]
        fr=(float(allf.min()),float(allf.max())) if allf.size else (0.0,1.0)
        figure.update_layout(showlegend=True,legend={"orientation":"h","yanchor":"bottom","y":1.08,"xanchor":"left","x":0.0},height=570,margin={"l":82,"r":115,"t":135,"b":80})
        panel_specs=[{"panel":1,"range":fr,"rep":0,"indices":list(range(len(spectra))),"secondary_y_allowed":True,"row":1,"col":1}]
    elif mode=="stitched":
        groups=contiguous_groups(); cols=max(1,len(groups))
        figure=make_subplots(rows=1,cols=cols,shared_yaxes=bool(share_y),horizontal_spacing=0.055)
        for gi,g in enumerate(groups,1):
            for idx in g["indices"]:
                figure.add_trace(trace_for(idx,showlegend=True),row=1,col=gi)
                for ft in fit_traces_for(idx): figure.add_trace(ft,row=1,col=gi)
                dt=detection_trace_for(idx)
                if dt is not None: figure.add_trace(dt,row=1,col=gi)
            if show_sum:
                st=combined_trace(g["indices"],name=(f"Combined {gi}" if en else f"Combinado {gi}"),style_index=gi-1)
                if st is not None:figure.add_trace(st,row=1,col=gi)
            panel_specs.append({"panel":gi,"range":(g["lo"],g["hi"]),"rep":g["indices"][0],"indices":list(g["indices"]),"secondary_y_allowed":bool(gi==cols),"row":1,"col":gi})
        # small diagonal break marks at panel boundaries, never text through data.
        if len(groups)>1:
            for gi in range(1,len(groups)):
                x=gi/len(groups)
                for off in (-0.005,0.005):
                    figure.add_shape(type="line",xref="paper",yref="paper",x0=x+off-0.004,x1=x+off+0.004,y0=-0.018,y1=0.018,
                                     line={"color":"#64748B","width":1.4})
        figure.update_layout(showlegend=True,legend={"orientation":"h","yanchor":"bottom","y":1.10,"xanchor":"left","x":0.0},height=570,margin={"l":82,"r":115,"t":140,"b":90})
    else:
        if mode=="aligned":
            panel_columns=len(spectra);rows=1;horizontal_spacing=min(0.055,0.16/max(panel_columns,1));vertical_spacing=0.08
        else:
            panel_columns=min(2,len(spectra)) if len(spectra)<=4 else (min(3,len(spectra)) if len(spectra)<=9 else max(1,min(int(columns),4,len(spectra))))
            rows=int(np.ceil(len(spectra)/panel_columns));horizontal_spacing=0.080;vertical_spacing=0.24 if rows>1 else 0.08
        figure=make_subplots(rows=rows,cols=panel_columns,subplot_titles=titles,shared_xaxes=bool(share_x),shared_yaxes=bool(share_y),
                             horizontal_spacing=horizontal_spacing,vertical_spacing=vertical_spacing)
        global_freq=[]
        for item in spectra:
            x=np.asarray(item["freq"],dtype=float);global_freq.extend(x[np.isfinite(x)].tolist())
        global_range=[min(global_freq),max(global_freq)] if global_freq else None
        for i in range(len(spectra)):
            row=i//panel_columns+1;col=i%panel_columns+1
            figure.add_trace(trace_for(i,showlegend=False),row=row,col=col)
            for ft in fit_traces_for(i): figure.add_trace(ft,row=row,col=col)
            dt=detection_trace_for(i)
            if dt is not None: figure.add_trace(dt,row=row,col=col)
            freq=np.asarray(spectra[i]["freq"],dtype=float);freq=freq[np.isfinite(freq)]
            fr=(float(freq.min()),float(freq.max())) if freq.size else (0.0,1.0); xr=global_range if share_x and global_range else list(fr)
            panel_specs.append({"panel":i+1,"range":(xr[0],xr[1]),"rep":i,"indices":[i],
                                "secondary_y_allowed": bool(col==panel_columns), "row":row, "col":col})
        figure.update_layout(showlegend=False,height=max(540,365*rows),margin={"l":82,"r":115,"t":120,"b":85})
        tidy_titles(figure)

    configure_axes(figure,panel_specs)

    # Plotly exposes one global modebar per figure.  CZSpec adds one miniature
    # reset control per subplot so an accidental zoom/pan in one spectrum does
    # not force the user to reset every panel.
    if len(panel_specs) > 1:
        menus=[]
        layout_json=figure.layout.to_plotly_json()
        for spec in panel_specs:
            panel=int(spec["panel"]); lo,hi=spec["range"]
            xkey=axis_key("x",panel); ykey=axis_key("y",panel)
            domain=(layout_json.get(xkey,{}) or {}).get("domain", [0.0,1.0])
            ydomain=(layout_json.get(ykey,{}) or {}).get("domain", [0.0,1.0])
            suffix="" if panel==1 else str(panel)
            relayout={
                f"xaxis{suffix}.range":[float(lo),float(hi)],
                f"xaxis{suffix}.autorange":False,
                f"yaxis{suffix}.autorange":True,
            }
            menus.append(dict(
                type="buttons", direction="right", showactive=False,
                x=float(domain[1])-0.004, y=min(1.0,float(ydomain[1])+0.035),
                xanchor="right", yanchor="bottom", pad={"r":0,"t":0},
                bgcolor="rgba(255,255,255,0.88)", bordercolor="#CBD5E1", borderwidth=1,
                font={"size":10},
                buttons=[dict(label="↺", method="relayout", args=[relayout])],
            ))
        figure.update_layout(updatemenus=menus)

    # Automatic comparison mode deliberately stays title-free (a89 removed the
    # redundant session heading). Users can still request one global title from
    # Plot style without reintroducing clutter by default.
    graph_title_mode=str(cfg.get("graph_title_mode") or "auto")
    graph_title=str(cfg.get("graph_title") or "").strip()
    if graph_title_mode=="custom" and graph_title:
        current_margin=figure.layout.margin.to_plotly_json() if figure.layout.margin else {}
        figure.update_layout(title={"text":graph_title,"x":0.5,"xanchor":"center"},
                             margin={**current_margin,"t":max(int(current_margin.get("t") or 0),155)})
    else:
        figure.update_layout(title=None)
    # Comparison panels are self-explanatory in automatic/no-title mode; a
    # user-supplied global title is preserved when explicitly requested.
    figure.update_layout(template="plotly_white",hovermode="closest",autosize=True,
                         meta={"czspec_comparison":True,"share_x":bool(share_x),"share_y":bool(share_y),"layout_mode":mode})
    return figure.to_json()

def save_plot_json_to_png(plot_json: str, output_path: str):
    fig = pio.from_json(plot_json)
    fig.write_image(output_path, scale=2)


def save_plot_json_to_file(plot_json: str, output_path: str, *, scale: float = 2.0):
    """Save a Plotly figure to PNG/JPG/PDF according to the extension."""
    fig = pio.from_json(plot_json)
    suffix = str(Path(output_path).suffix).lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".pdf", ".svg", ".webp"}:
        raise ValueError(f"Unsupported static plot format: {suffix}")
    fig.write_image(output_path, scale=scale)

# =========================================================
# Función principal adaptada para GUI
# =========================================================
def run_peak_detection(
    file_path: str,
    baseline_degree: int = 0,
    fit_choice: str = "1",
    beam_efficiency: float = 0.81,
    detection_sigma: float = DEFAULT_DETECTION_SIGMA,
    fit_color: str = DEFAULT_FIT_COLOR,
    plot_styles: dict | None = None,
    output_dir: str = str(PEAK_DETECTION_OUTPUT_DIR),
    export_csv: bool = True,
    export_html: bool = True,
    manual_peak_freqs=None,
    removed_peak_freqs=None,
    retained_peak_items=None,
    local_edit: bool = False,
    preserve_ranges=None,
    progress_callback=None,
    *,
    baseline_mode: str = "auto",
    baseline_windows=None,
    detection_polarity: str = "emission",
    deblend: bool = True,
    delta_bic_min: float = 6.0,
    max_components_per_group: int = 8,
    input_metadata: dict | None = None,
    calibration_factor: float | None = None,
    display_name: str | None = None,
    language: str = "es",
):
    """Detecta y ajusta perfiles espectrales para M1.

    alpha.48 conserva: base automática o por ventanas, emisión/absorción, ajuste
    robusto multicomponente, selección BIC y búsqueda iterativa en residuales.
    """
    def report(value, message):
        if progress_callback is not None:
            progress_callback(value, message)

    report(3, "Validando el espectro")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")
    if baseline_degree not in (0, 1, 2, 3):
        raise ValueError("baseline_degree debe estar entre 0 y 3")
    if fit_choice not in {"1", "2", "3"}:
        raise ValueError("fit_choice debe ser '1', '2' o '3'")
    detection_sigma = float(detection_sigma)
    if not np.isfinite(detection_sigma) or not (0.5 <= detection_sigma <= 20.0):
        raise ValueError("El umbral de detección debe estar entre 0.5 y 20 σ.")
    baseline_mode = str(baseline_mode or "auto").lower()
    if baseline_mode not in {"auto", "windows"}:
        raise ValueError("baseline_mode debe ser 'auto' o 'windows'.")
    detection_polarity = str(detection_polarity or "emission").lower()
    if detection_polarity not in {"emission", "absorption", "both"}:
        raise ValueError("detection_polarity debe ser emission, absorption o both.")
    delta_bic_min = float(delta_bic_min)
    if not 0.0 <= delta_bic_min <= 100.0:
        raise ValueError("delta_bic_min debe estar entre 0 y 100.")
    max_components_per_group = int(max_components_per_group)
    if not 1 <= max_components_per_group <= 12:
        raise ValueError("max_components_per_group debe estar entre 1 y 12.")

    fit_color = str(fit_color).strip().upper()
    if not re.fullmatch(r"#[0-9A-F]{6}", fit_color):
        raise ValueError("El color de los ajustes debe tener formato hexadecimal #RRGGBB.")
    style_source = dict(plot_styles or {})
    fit_style_source = dict(style_source.get("fits", {}) or {})
    fit_style_source.setdefault("color", fit_color)
    style_source["fits"] = fit_style_source
    plot_styles = normalize_plot_styles(style_source)
    fit_color = plot_styles["fits"]["color"]
    # ``fits`` is the final scientific profile: an isolated fit or the sum of
    # a blended group. ``fit_components`` are the individual mathematical
    # components inside a blended group and intentionally use a separate style.
    fit_line_style = dict(plot_styles["fits"])
    component_line_style = dict(plot_styles.get("fit_components", plot_styles["fits"]))
    os.makedirs(output_dir, exist_ok=True)

    manual_peak_freqs = list(manual_peak_freqs or [])
    removed_peak_freqs = list(removed_peak_freqs or [])
    retained_peak_items = list(retained_peak_items or [])
    report(8, "Leyendo los canales del espectro")
    freq, inten, read_meta = read_spectrum_file(file_path)
    effective_metadata = merge_metadata(read_meta, input_metadata)
    if calibration_factor is None:
        if not (0 < beam_efficiency <= 1):
            raise ValueError("La eficiencia del haz debe estar en el rango 0 < eta <= 1.")
        calibration_factor = 1.0 / float(beam_efficiency)
    calibration_factor = float(calibration_factor)
    if not np.isfinite(calibration_factor) or calibration_factor <= 0:
        raise ValueError("El factor de calibración debe ser positivo.")
    inten = inten * calibration_factor
    channel_width = float(np.median(np.diff(freq)))
    if not np.isfinite(channel_width) or channel_width <= 0:
        raise ValueError("No se pudo determinar un ancho de canal positivo.")
    channel_dv_kms = 299792.458 * channel_width / max(float(np.nanmedian(freq)), 1e-12)

    report(15, "Definiendo canales de línea base")
    clean_baseline_windows = []
    if baseline_mode == "windows":
        baseline_mask, clean_baseline_windows = mask_from_baseline_windows(freq, baseline_windows)
        if baseline_mask.sum() < max(baseline_degree + 2, 8):
            raise ValueError("Las ventanas de base contienen muy pocos canales para el ajuste.")
    else:
        baseline_mask = automatic_baseline_mask(freq, inten, degree=baseline_degree)
        if baseline_mask.sum() < max(baseline_degree + 2, int(0.03 * len(freq))):
            baseline_mask = np.ones_like(freq, dtype=bool)

    report(27, "Ajustando la línea base")
    local_baseline_models = []
    use_local_degrees = (
        baseline_mode == "windows"
        and any(spec[2] is not None for spec in clean_baseline_windows)
    )
    if use_local_degrees:
        base_fit, baseline_mask, local_baseline_models = local_degree_baseline_from_windows(
            freq, inten, clean_baseline_windows, default_degree=baseline_degree
        )
    else:
        base_fit = poly_baseline_with_sigma_clipping(
            freq, inten, baseline_mask, degree=baseline_degree, n_iter=6, nsigma=3.0
        )
    y_corr = inten - base_fit
    # El cero se fija con los canales usados realmente para la base, no con todo
    # el espectro (importante en espectros dominados por emisión).
    offset = float(np.nanmedian(y_corr[baseline_mask])) if np.any(baseline_mask) else float(np.nanmedian(y_corr))
    y_corr -= offset
    base_fit += offset

    report(38, "Calculando el ruido local robusto")
    dv_win_kms = 20.0
    bins_noise = int(np.ceil((np.mean(freq) * dv_win_kms / 299792.458) / max(channel_width, 1e-12)))
    window_bins = max(151, bins_noise | 1)
    sigma_loc = local_sigma_mad(y_corr, window_bins=window_bins)

    report(47, "Detectando candidatos espectrales")
    peaks, peak_metrics, z, prominence_sigma = detect_peaks_by_snr(
        y_corr,
        sigma_loc,
        detection_sigma=detection_sigma,
        prominence_sigma=2.5,
        min_width_channels=2.5,
        min_distance_channels=2,
        multiscale=True,
        polarity=detection_polarity,
    )
    metric_map = {}
    for j, idx in enumerate(peaks.tolist()):
        metric = {}
        for key, values in peak_metrics.items():
            if len(values) <= j:
                continue
            value = values[j]
            metric[key] = value.item() if hasattr(value, "item") else value
        metric_map[int(idx)] = metric

    seeds_by_index = {}
    # A manual edit is not a new discovery pass.  Start from the components
    # already accepted in the current state and only apply the requested edit.
    # This prevents deleting one member of a blend from causing BIC/peak search
    # to rebuild (or erase) unrelated components.
    if not local_edit:
        for idx in peaks.tolist():
            seeds_by_index[int(idx)] = _seed_from_index(
                freq, y_corr, int(idx), "auto", metric_map.get(int(idx), {})
            )

    # During an interactive edit, preserve every previously accepted component
    # except the one(s) explicitly removed.  This is the critical distinction
    # between a local edit and a fresh Analyze operation: neighbouring members
    # of a multi-component fit remain present and are refitted rather than
    # rediscovered from scratch.
    for previous in retained_peak_items:
        try:
            seed_freq = float(previous.get("freq"))
        except Exception:
            continue
        if not np.isfinite(seed_freq):
            continue
        # ``retained_peak_items`` has already been filtered by immutable ID in
        # the GUI during a local edit.  Do not discard a neighbouring survivor
        # merely because its seed is within a sub-channel frequency tolerance of
        # the removed component.
        if (not local_edit) and any(abs(seed_freq - float(fr)) <= max(channel_width * 0.35, 1e-7) for fr in removed_peak_freqs):
            continue
        fit_center = previous.get("fit_freq", seed_freq)
        try:
            fit_center = float(fit_center)
        except Exception:
            fit_center = seed_freq
        if not np.isfinite(fit_center):
            fit_center = seed_freq
        idx = int(np.argmin(np.abs(freq - fit_center)))
        origin = str(previous.get("origin") or "auto")
        seed = _seed_from_index(freq, y_corr, idx, origin, metric_map.get(idx, {}))
        # Refit from the previous fitted center, not from the original channel.
        # The original channel is retained separately as an immutable edit anchor.
        seed["mu"] = fit_center
        seed["stable_seed_mhz"] = seed_freq
        seed["locked"] = True
        seed["detection_id"] = str(previous.get("detection_id") or "")
        previous_params = previous.get("fit_params")
        if isinstance(previous_params, (list, tuple, np.ndarray)):
            try:
                previous_params = [float(v) for v in previous_params]
            except Exception:
                previous_params = None
        else:
            previous_params = None
        if previous_params:
            seed["previous_params"] = previous_params
            try:
                seed["sign"] = 1 if float(previous_params[0]) >= 0 else -1
                seed["polarity"] = "emission" if seed["sign"] > 0 else "absorption"
            except Exception:
                pass
        else:
            polarity = str(previous.get("polarity") or "").lower()
            if "absor" in polarity:
                seed["sign"] = -1
                seed["polarity"] = "absorption"
            elif polarity:
                seed["sign"] = 1
                seed["polarity"] = "emission"
        try:
            previous_fwhm_mhz = float(previous.get("fwhm_mhz", np.nan))
        except Exception:
            previous_fwhm_mhz = np.nan
        if np.isfinite(previous_fwhm_mhz) and previous_fwhm_mhz > 0:
            previous_fwhm_kms = 299792.458 * previous_fwhm_mhz / max(abs(fit_center), 1e-12)
            seed["initial_fwhm_mhz"] = previous_fwhm_mhz
            seed["center_window_kms"] = max(3.0 * channel_dv_kms, min(1.2, 0.60 * previous_fwhm_kms))
            seed["max_fwhm_kms"] = min(30.0, max(4.0 * channel_dv_kms, 1.8 * previous_fwhm_kms))
        else:
            seed["center_window_kms"] = max(3.0 * channel_dv_kms, 0.8)
        # Multiple fitted components may legitimately fall in the same nearest
        # spectral channel after deblending.  The old dict key was the channel
        # index itself, so the later survivor silently overwrote the earlier one
        # during a local edit.  Keep a unique sortable key while preserving the
        # actual channel index inside the seed.  This is essential when deleting
        # one member of a close blend: every other immutable detection_id must
        # survive even if two centres round to the same channel.
        seed_key = float(idx)
        while seed_key in seeds_by_index:
            seed_key += 1.0e-6
        seeds_by_index[seed_key] = seed

    # Las detecciones manuales anulan la polaridad automática y usan el signo
    # local del dato. Durante una edición local, ``manual_peak_freqs`` contiene
    # el historial de clicks del usuario, por lo que una manual ya aceptada NO
    # debe reinyectarse como una segunda componente en cada edición posterior.
    retained_anchors = []
    if local_edit:
        for previous in retained_peak_items:
            try:
                # La proximidad visual/observacional se decide respecto al centro
                # ajustado actual, no sólo respecto a la semilla histórica.
                anchor = previous.get("fit_freq", previous.get("freq"))
                retained_anchors.append(float(anchor))
            except Exception:
                continue
    # Una segunda detección manual dentro del mismo canal espectral no puede
    # considerarse una característica observacional independiente en M1.  Las
    # posibles múltiples identificaciones moleculares de una característica
    # no resuelta pertenecen a M2.
    duplicate_tol = max(channel_width, 1.0e-7)
    for value in manual_peak_freqs:
        f_user = float(value)
        if local_edit and any(abs(f_user - anchor) <= duplicate_tol for anchor in retained_anchors):
            continue
        idx = int(np.argmin(np.abs(freq - f_user)))
        seed = _seed_from_index(freq, y_corr, idx, "manual", metric_map.get(idx, {}))
        # A manual detection is an explicit positional request in every mode,
        # not only after an existing analysis.  Keep the exact entered/clicked
        # frequency as the anchor and allow only a small local refinement.
        seed["mu"] = f_user
        seed["stable_seed_mhz"] = f_user
        seed["manual_anchor"] = True
        seed["center_window_kms"] = min(0.35, max(1.5 * channel_dv_kms, 0.12))
        seed["max_fwhm_kms"] = 15.0
        if local_edit:
            seed_key = float(idx)
            while seed_key in seeds_by_index:
                seed_key += 1.0e-6
            seeds_by_index[seed_key] = seed
        else:
            seeds_by_index[idx] = seed

    # El borrado conserva la frecuencia-semilla para que siga funcionando aunque
    # el centro ajustado se desplace ligeramente durante el deblending.
    # Las marcas de borrado se almacenan ahora en la frecuencia-semilla exacta.
    # Una tolerancia menor a medio canal evita borrar componentes adyacentes de
    # un grupo múltiple al retirar sólo Li desde la gráfica.
    remove_tol = max(channel_width * 0.35, 1e-7)
    filtered_seeds = []
    for idx, seed in sorted(seeds_by_index.items()):
        # Una adición manual es una orden explícita del usuario y tiene prioridad
        # sobre una marca de borrado antigua. Esto es esencial al eliminar una
        # detección automática (guardada por su frecuencia-semilla) y re-agregarla
        # después usando el centro ajustado mostrado en la lista.
        if (not bool(seed.get("locked"))) and seed.get("origin") != "manual" and any(
            abs(float(seed.get("stable_seed_mhz", seed["mu"])) - float(fr)) <= remove_tol for fr in removed_peak_freqs
        ):
            continue
        filtered_seeds.append(seed)
    initial_candidate_count = len(filtered_seeds)

    fit_name = {"1": "Gaussiano", "2": "Lorentziano", "3": "Voigt"}[fit_choice]
    report(54, "Agrupando candidatos cercanos")
    max_gap_kms = 8.0
    max_span_kms = 28.0
    max_initial_seeds_per_group = 12
    groups = []
    if filtered_seeds:
        current = [filtered_seeds[0]]
        for seed in filtered_seeds[1:]:
            prev = current[-1]
            first = current[0]
            nu_ref = max(float(seed["mu"]), 1e-12)
            gap = 299792.458 * abs(float(seed["mu"]) - float(prev["mu"])) / nu_ref
            span = 299792.458 * abs(float(seed["mu"]) - float(first["mu"])) / nu_ref
            if gap <= max_gap_kms and span <= max_span_kms and len(current) < max_initial_seeds_per_group:
                current.append(seed)
            else:
                groups.append(current)
                current = [seed]
        groups.append(current)

    resultados = []
    detected_peak_items = []
    fit_plot_traces = []
    diagnostics = []
    all_component_specs = []
    line_id = 1

    def validate_fit(fit, selected, x_data):
        accepted = []
        for comp_index, seed in enumerate(selected):
            sub = _component_params(fit_choice, fit["params"], comp_index)
            subcov = _component_covariance(fit_choice, fit.get("pcov"), comp_index)
            try:
                dv_kms, dv_err, intint, intint_err = dv_intint_and_errors(
                    fit_choice, sub, subcov, x_for_area=x_data
                )
            except Exception:
                continue
            mu = float(sub[1])
            amp = float(sub[0])
            local_noise = float(np.interp(mu, freq, sigma_loc))
            amp_snr = abs(amp) / max(local_noise, 1e-12)
            local_channel_dv = 299792.458 * channel_width / max(mu, 1e-12)
            center_shift = 299792.458 * abs(mu - float(seed["mu"])) / max(float(seed["mu"]), 1e-12)
            is_manual = seed.get("origin") == "manual"
            is_locked = bool(seed.get("locked"))
            if is_manual or is_locked:
                # Manual detections and components already accepted before a
                # local edit are explicit state.  A neighbouring deletion must
                # not make a survivor disappear simply because the refit nudges
                # its S/N below the discovery threshold.  We still reject
                # non-finite, degenerate-width or wrong-sign solutions.
                valid = (
                    np.isfinite(dv_kms)
                    and np.isfinite(amp_snr)
                    and 0.75 * local_channel_dv <= abs(dv_kms) <= 30.0
                    and center_shift <= 4.6
                    and (amp >= 0 if int(seed.get("sign", 1)) > 0 else amp <= 0)
                )
            else:
                min_snr = max(3.0, detection_sigma - 1.0)
                valid = (
                    np.isfinite(dv_kms)
                    and np.isfinite(amp_snr)
                    and amp_snr >= min_snr
                    and 1.5 * local_channel_dv <= abs(dv_kms) <= 30.0
                    and center_shift <= 4.6
                    and (amp >= 0 if int(seed.get("sign", 1)) > 0 else amp <= 0)
                )
            if valid:
                accepted.append({
                    "seed": seed,
                    "params": sub,
                    "pcov": subcov,
                    "dv_kms": float(dv_kms),
                    "dv_err": float(dv_err),
                    "intint": float(intint),
                    "intint_err": float(intint_err),
                    "snr": float(amp_snr),
                    "center_shift_kms": float(center_shift),
                })
        return accepted

    group_count = max(1, len(groups))
    for group_index, group in enumerate(groups):
        report(58 + int(28 * group_index / group_count), f"Deblending del grupo {group_index + 1} de {len(groups)}")
        try:
            group_min = float(group[0]["mu"])
            group_max = float(group[-1]["mu"])
            nu_mid = max(0.5 * (group_min + group_max), 1e-12)
            extension = nu_mid * 14.0 / 299792.458
            left = max(float(freq[0]), group_min - extension)
            right = min(float(freq[-1]), group_max + extension)
            if group_index > 0:
                previous_max = float(groups[group_index - 1][-1]["mu"])
                left = max(left, 0.5 * (previous_max + group_min))
            if group_index + 1 < len(groups):
                next_min = float(groups[group_index + 1][0]["mu"])
                right = min(right, 0.5 * (group_max + next_min))
            mask_loc = (freq >= left) & (freq <= right)
            x_data = freq[mask_loc]
            y_data = y_corr[mask_loc]
            sigma_data = sigma_loc[mask_loc]
            if len(x_data) < 8:
                continue

            if local_edit:
                # Every component in a local edit is explicit user/session state:
                # retained detections are frozen and newly-added manual seeds are
                # intentional.  BIC is a discovery tool and must not silently
                # remove one of these components during an edit.
                selected = group[:max_components_per_group]
                fit = fit_multi_components_robust(
                    fit_choice, x_data, y_data, sigma_data, selected, channel_width
                )
                history = [{
                    "n": len(selected), "bic": fit["bic"], "aic": fit["aic"],
                    "reason": "local_edit_explicit",
                }]
            elif deblend:
                fit, selected, history = select_components_with_bic(
                    fit_choice,
                    x_data,
                    y_data,
                    sigma_data,
                    group,
                    channel_width,
                    detection_sigma=detection_sigma,
                    delta_bic_min=delta_bic_min,
                    max_components=max_components_per_group,
                    residual_polarity=(
                        "both"
                        if len({int(seed.get("sign", 1)) for seed in group}) > 1
                        else ("emission" if int(group[0].get("sign", 1)) > 0 else "absorption")
                    ),
                    forbidden_freqs=removed_peak_freqs,
                    allow_residual_search=True,
                )
            else:
                selected = group[:max_components_per_group]
                fit = fit_multi_components_robust(
                    fit_choice, x_data, y_data, sigma_data, selected, channel_width
                )
                history = [{"n": len(selected), "bic": fit["bic"], "aic": fit["aic"], "reason": "fixed"}]
            if fit is None or not selected:
                continue

            accepted = validate_fit(fit, selected, x_data)
            # Si un componente falla la validación física, se retira y se reajusta
            # una vez para que no distorsione parámetros de los vecinos válidos.
            if 0 < len(accepted) < len(selected):
                selected2 = [entry["seed"] for entry in accepted]
                fit2 = fit_multi_components_robust(
                    fit_choice, x_data, y_data, sigma_data, selected2, channel_width
                )
                accepted2 = validate_fit(fit2, selected2, x_data)
                if accepted2:
                    selected, fit, accepted = selected2, fit2, accepted2
            if not accepted:
                continue

            # Resolubilidad post-fit
            # ----------------------
            # Las semillas iniciales están separadas por canales, pero un ajuste
            # multicomponente puede hacer converger dos centros hacia la misma
            # característica. Sin esta segunda validación, dos detecciones
            # distintas podían terminar separadas por una fracción de canal
            # aunque individualmente ambas pasaran S/N, FWHM y signo.
            #
            # En un Analyze fresco, si dos centros finales quedan a menos de un
            # canal, se prueba retirar cada una por separado y se conserva el
            # modelo resoluble con menor BIC. No se aplica durante una edición
            # local para no modificar silenciosamente componentes que el usuario
            # no está editando.
            unresolved_collapses = []
            if (not local_edit) and len(accepted) > 1:
                max_resolution_passes = len(accepted) + 2
                for _resolution_pass in range(max_resolution_passes):
                    accepted.sort(key=lambda entry: float(entry["params"][1]))
                    unresolved_pair = None
                    for pair_index in range(len(accepted) - 1):
                        mu_left = float(accepted[pair_index]["params"][1])
                        mu_right = float(accepted[pair_index + 1]["params"][1])
                        separation_mhz = abs(mu_right - mu_left)
                        if separation_mhz < max(float(channel_width), 1.0e-7):
                            unresolved_pair = (pair_index, pair_index + 1, separation_mhz)
                            break
                    if unresolved_pair is None:
                        break

                    left_i, right_i, separation_mhz = unresolved_pair
                    trial_solutions = []
                    for drop_i in (left_i, right_i):
                        trial_seeds = [
                            entry["seed"] for k, entry in enumerate(accepted)
                            if k != drop_i
                        ]
                        if not trial_seeds:
                            continue
                        try:
                            trial_fit = fit_multi_components_robust(
                                fit_choice, x_data, y_data, sigma_data,
                                trial_seeds, channel_width
                            )
                            trial_accepted = validate_fit(trial_fit, trial_seeds, x_data)
                            if len(trial_accepted) != len(trial_seeds):
                                continue
                            trial_solutions.append((
                                float(trial_fit["bic"]),
                                drop_i,
                                trial_fit,
                                trial_seeds,
                                trial_accepted,
                            ))
                        except Exception:
                            continue

                    if trial_solutions:
                        trial_solutions.sort(key=lambda item: item[0])
                        _bic, dropped_index, fit, selected, accepted = trial_solutions[0]
                    else:
                        snr_left = float(accepted[left_i].get("snr", 0.0))
                        snr_right = float(accepted[right_i].get("snr", 0.0))
                        dropped_index = left_i if snr_left <= snr_right else right_i
                        selected = [
                            entry["seed"] for k, entry in enumerate(accepted)
                            if k != dropped_index
                        ]
                        if not selected:
                            break
                        fit = fit_multi_components_robust(
                            fit_choice, x_data, y_data, sigma_data,
                            selected, channel_width
                        )
                        accepted = validate_fit(fit, selected, x_data)
                        if not accepted:
                            break

                    collapse_event = {
                        "separation_mhz": float(separation_mhz),
                        "channel_width_mhz": float(channel_width),
                        "dropped_pair_index": int(dropped_index),
                        "reason": "postfit_unresolved_below_one_channel",
                    }
                    unresolved_collapses.append(collapse_event)
                    history.append({
                        "n": len(selected),
                        "bic": float(fit["bic"]),
                        "aic": float(fit["aic"]),
                        "reason": "unresolved_collapse",
                        "separation_mhz": float(separation_mhz),
                        "channel_width_mhz": float(channel_width),
                    })

            if not accepted:
                continue
            accepted.sort(key=lambda entry: float(entry["params"][1]))

            diagnostics.append({
                "group": group_index + 1,
                "candidate_count": len(group),
                "selected_count": len(selected),
                "accepted_count": len(accepted),
                "bic": float(fit["bic"]),
                "aic": float(fit["aic"]),
                "history": history,
                "unresolved_collapses": unresolved_collapses,
                "frequency_min_mhz": float(left),
                "frequency_max_mhz": float(right),
            })

            # Traza total del grupo construida sólo con componentes aceptadas.
            xs_group = np.linspace(float(x_data.min()), float(x_data.max()), 700)
            total_group = np.zeros_like(xs_group)
            start_line_id = line_id
            group_detection_ids = []
            for entry in accepted:
                params = entry["params"]
                seed = entry["seed"]
                ys = evaluate_profile(fit_choice, xs_group, params)
                total_group += ys
                origin = str(seed.get("origin", "auto"))
                if origin == "manual":
                    confidence = "manual"
                elif entry["snr"] >= 6.0:
                    confidence = "segura"
                elif entry["snr"] >= max(4.0, detection_sigma):
                    confidence = "probable"
                else:
                    confidence = "tentativa"
                polarity_label = "Emisión" if float(params[0]) >= 0 else "Absorción"
                delta_last = np.nan
                if history and "delta_bic" in history[-1]:
                    delta_last = float(history[-1]["delta_bic"])

                source_name = str(effective_metadata.get("canonical_name") or effective_metadata.get("raw_source_name") or os.path.basename(file_path))
                line_velocity = np.nan
                source_delta_velocity = np.nan
                if bool(effective_metadata.get("m1_reference_line_active", False)):
                    try:
                        rest_mhz = float(effective_metadata.get("rest_frequency_mhz"))
                        if np.isfinite(rest_mhz) and rest_mhz > 0:
                            line_velocity = float(velocity_axis_from_metadata(np.asarray([float(params[1])]), effective_metadata)[0])
                            source_vlsr = float(effective_metadata.get("vlsr_kms"))
                            if np.isfinite(source_vlsr):
                                source_delta_velocity = line_velocity - source_vlsr
                    except Exception:
                        pass
                resultados.append({
                    "Line": line_id,
                    "Source": source_name,
                    "ν[MHz]": float(params[1]),
                    "v_LSR[km/s]": float(line_velocity),
                    "Δv_fuente[km/s]": float(source_delta_velocity),
                    "T_A [K]": float(params[0]),
                    "Δv [Km/s]": float(entry["dv_kms"]),
                    "σ_Δv [Km/s]": float(entry["dv_err"]),
                    "IntInt [K*Km/s]": float(entry["intint"]),
                    "σ_IntInt [K*Km/s]": float(entry["intint_err"]),
                    "GOI": "Individual" if len(accepted) == 1 else "Grupo",
                    "Ajuste": fit_name,
                    "SNR": float(entry["snr"]),
                    "Confianza": confidence,
                    "Tipo": polarity_label,
                    "Origen": origin,
                    "Semilla_ν[MHz]": float(seed["mu"]),
                    "Desplazamiento_centro[km/s]": float(entry["center_shift_kms"]),
                    "BIC_grupo": float(fit["bic"]),
                    "AIC_grupo": float(fit["aic"]),
                    "ΔBIC_última": delta_last,
                })
                stable_seed = float(seed.get("stable_seed_mhz", seed["mu"]))
                detection_id = str(seed.get("detection_id") or uuid.uuid5(uuid.NAMESPACE_URL, f"czspec:m1:{Path(file_path).resolve()}:{stable_seed:.12f}:{origin}"))
                resultados[-1]["detection_id"] = detection_id
                resultados[-1]["Semilla_ν[MHz]"] = stable_seed
                group_detection_ids.append(detection_id)
                detected_peak_items.append({
                    "detection_id": detection_id,
                    # ``freq`` is the immutable channel seed.  The fitted center
                    # may change without changing the identity of the detection.
                    "freq": stable_seed,
                    "fit_freq": float(params[1]),
                    # Marker/interaction coordinates must describe the fitted
                    # component itself, not the nearest raw spectral channel.
                    # This is especially important for unresolved/close blends,
                    # where two fitted centres can round to the same channel.
                    "fit_amp": float(params[0]),
                    "origin": origin,
                    "deleted": False,
                    "snr": float(entry["snr"]),
                    "prominence_snr": float(seed.get("prominence_snr", np.nan)),
                    "width_channels": float(seed.get("width_channels", np.nan)),
                    "fwhm_mhz": float(abs(entry.get("dv_kms", np.nan)) * abs(float(params[1])) / 299792.458)
                    if np.isfinite(float(entry.get("dv_kms", np.nan))) else np.nan,
                    # Persist the accepted profile itself so a later manual edit
                    # can preserve component identity/position while performing
                    # only a constrained local amplitude/width refit.
                    "fit_params": [float(v) for v in np.asarray(params, dtype=float).ravel()],
                    "fit_choice": str(fit_choice),
                    "group_size": int(len(accepted)),
                    "confidence": confidence,
                    "polarity": polarity_label,
                })
                all_component_specs.append((params.copy(), line_id))
                if len(accepted) > 1:
                    fit_plot_traces.append({
                        "x": xs_group,
                        "y": ys,
                        "mode": "lines",
                        "name": f"Componente L{line_id}",
                        "line": dict(component_line_style),
                        "opacity": 0.82,
                        # Components are scientific fit products and should be
                        # visible by default; the compact legend controls them
                        # as one category instead of hiding them at startup.
                        "visible": True,
                        "meta": {"czspec_role": "fit_component", "detection_id": detection_id},
                    })
                line_id += 1

            if len(accepted) == 1:
                fit_plot_traces.append({
                    "x": xs_group,
                    "y": total_group,
                    "mode": "lines",
                    "name": f"Ajuste L{start_line_id}",
                    "line": dict(fit_line_style),
                    "meta": {
                        "czspec_role": "fit",
                        "detection_id": group_detection_ids[0] if group_detection_ids else "",
                    },
                })
            else:
                fit_plot_traces.append({
                    "x": xs_group,
                    "y": total_group,
                    "mode": "lines",
                    "name": f"Suma grupo L{start_line_id}–L{line_id - 1}",
                    "line": dict(fit_line_style),
                    "meta": {"czspec_role": "fit_sum", "detection_ids": list(group_detection_ids)},
                })
        except Exception as exc:
            diagnostics.append({"group": group_index + 1, "error": str(exc)})
            continue

    report(88, "Construyendo residuales y tabla final")
    df_results = pd.DataFrame(resultados)
    if not df_results.empty:
        # One canonical ordering drives the table, plot labels, hover IDs and
        # fit-trace names.  Independent sorts can disagree for nearly identical
        # fitted centres, which was visible in close blends after alpha.82.
        sort_columns = ["ν[MHz]"]
        if "detection_id" in df_results.columns:
            sort_columns.append("detection_id")
        df_results = df_results.sort_values(sort_columns, kind="mergesort").reset_index(drop=True)
        df_results["Line"] = np.arange(1, len(df_results) + 1)

        item_by_id = {
            str(item.get("detection_id") or ""): item
            for item in detected_peak_items
            if str(item.get("detection_id") or "")
        }
        ordered_items = []
        line_by_id = {}
        for _, row in df_results.iterrows():
            detection_id = str(row.get("detection_id") or "")
            if detection_id:
                line_by_id[detection_id] = int(row["Line"])
                item = item_by_id.get(detection_id)
                if item is not None:
                    item["line_no"] = int(row["Line"])
                    ordered_items.append(item)
        if len(ordered_items) == len(detected_peak_items):
            detected_peak_items = ordered_items
        else:
            # Defensive fallback for legacy/non-ID entries.
            detected_peak_items = sorted(
                detected_peak_items,
                key=lambda item: (float(item.get("fit_freq", np.inf)), str(item.get("detection_id") or "")),
            )
            for line_no, item in enumerate(detected_peak_items, start=1):
                item["line_no"] = line_no
                did = str(item.get("detection_id") or "")
                if did:
                    line_by_id[did] = line_no

        # Fit traces are created while groups are processed.  Rename them only
        # after the final canonical ordering is known so "Componente/Ajuste Li"
        # cannot drift away from the corresponding detection/table row.
        for trace in fit_plot_traces:
            meta = trace.get("meta") or {}
            role = str(meta.get("czspec_role") or "")
            if role in {"fit", "fit_component"}:
                did = str(meta.get("detection_id") or "")
                line_no = line_by_id.get(did)
                if line_no is not None:
                    prefix = "Ajuste" if role == "fit" else "Componente"
                    trace["name"] = f"{prefix} L{line_no}"
            elif role == "fit_sum":
                nums = sorted({line_by_id.get(str(did)) for did in (meta.get("detection_ids") or []) if line_by_id.get(str(did)) is not None})
                if nums:
                    if nums == list(range(nums[0], nums[-1] + 1)):
                        suffix = f"L{nums[0]}–L{nums[-1]}" if len(nums) > 1 else f"L{nums[0]}"
                    else:
                        suffix = "+".join(f"L{n}" for n in nums)
                    trace["name"] = f"Suma grupo {suffix}"

    # Diagnostic final residual: baseline-corrected spectrum minus only the
    # final scientific profiles (isolated fits and group sums).  Individual
    # mathematical components are intentionally not subtracted a second time.
    final_model = np.zeros_like(np.asarray(y_corr, dtype=float), dtype=float)
    for trace in fit_plot_traces:
        meta = trace.get("meta") or {}
        if str(meta.get("czspec_role") or "") not in {"fit", "fit_sum"}:
            continue
        try:
            tx = np.asarray(trace.get("x"), dtype=float)
            ty = np.asarray(trace.get("y"), dtype=float)
            good = np.isfinite(tx) & np.isfinite(ty)
            tx = tx[good]; ty = ty[good]
            if tx.size < 2:
                continue
            order = np.argsort(tx); tx = tx[order]; ty = ty[order]
            mask = (freq >= tx[0]) & (freq <= tx[-1])
            if mask.any():
                final_model[mask] += np.interp(freq[mask], tx, ty)
        except Exception:
            continue
    residual_final = np.asarray(y_corr, dtype=float) - final_model
    fit_plot_traces.append({
        "x": np.asarray(freq, dtype=float),
        "y": residual_final,
        "mode": "lines",
        "name": "Residual final" if language == "es" else "Final residual",
        "line": dict(plot_styles.get("residual", {"color":"#94A3B8","width":1.0,"dash":"dot"})),
        "meta": {"czspec_role": "residual"},
    })

    report(92, "Construyendo la visualización interactiva")
    final_peak_indices = []
    for item in detected_peak_items:
        final_peak_indices.append(int(np.argmin(np.abs(freq - float(item["fit_freq"])))))
    fig = build_plotly_figure(
        freq,
        inten,
        base_fit,
        y_corr,
        np.asarray(final_peak_indices, dtype=int),
        file_path,
        preserve_ranges=preserve_ranges,
        extra_traces=fit_plot_traces,
        plot_styles=plot_styles,
        input_metadata=effective_metadata,
        display_name=display_name,
        language=language,
        peak_items=detected_peak_items,
    )
    if baseline_mode == "windows":
        for a, b, _degree in clean_baseline_windows:
            fig.add_vrect(
                x0=a, x1=b, fillcolor="rgba(100,116,139,0.08)", line_width=0,
                layer="below",
            )

    report(96, "Serializando la gráfica")
    plot_html = fig.to_html(include_plotlyjs=True)
    plot_json = fig.to_json()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_csv = None
    output_html = None
    if export_csv and not df_results.empty:
        output_csv = os.path.join(output_dir, f"{base_name}_peak_detection_{timestamp}.csv")
        df_results.to_csv(output_csv, index=False)
    if export_html:
        output_html = os.path.join(output_dir, f"{base_name}_plot_{timestamp}.html")
        with open(output_html, "w", encoding="utf-8") as handle:
            handle.write(plot_html)

    residual_added = sum(1 for item in detected_peak_items if item.get("origin") == "residual")
    report(99, "Finalizando el análisis")
    return {
        "results_df": df_results,
        "output_csv": output_csv,
        "output_html": output_html,
        "n_detected_lines": len(df_results),
        "n_initial_candidates": int(initial_candidate_count),
        "n_residual_components": int(residual_added),
        "n_groups": int(len(groups)),
        "baseline_degree": baseline_degree,
        "baseline_mode": baseline_mode,
        "baseline_windows_mhz": clean_baseline_windows,
        "baseline_local_models": [
            {"fmin_mhz": m["a"], "fmax_mhz": m["b"], "degree": m["degree"]}
            for m in local_baseline_models
        ],
        "fit_choice": fit_choice,
        "fit_name": fit_name,
        "detection_sigma": detection_sigma,
        "detection_polarity": detection_polarity,
        "prominence_sigma": prominence_sigma,
        "deblend": bool(deblend),
        "delta_bic_min": float(delta_bic_min),
        "max_components_per_group": int(max_components_per_group),
        "fit_color": fit_color,
        "plot_styles": plot_styles,
        "fit_plot_traces": fit_plot_traces,
        "fit_diagnostics": diagnostics,
        "file_path": file_path,
        "plot_html": plot_html,
        "detected_peak_items": detected_peak_items,
        "plot_json": plot_json,
        "frequency_mhz": freq.copy(),
        "beam_corrected_intensity_k": inten.copy(),
        "baseline_k": base_fit.copy(),
        "baseline_corrected_intensity_k": y_corr.copy(),
        "local_noise_sigma_k": sigma_loc.copy(),
        "baseline_mask": baseline_mask.copy(),
        "channel_width_mhz": float(channel_width),
        "channel_spacing_kms": float(channel_dv_kms),
        "beam_efficiency": float(beam_efficiency),
        "input_metadata": effective_metadata,
        "calibration_factor": float(calibration_factor),
        **read_meta,
    }

