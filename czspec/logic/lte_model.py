"""Espectros sintéticos moleculares bajo la aproximación LTE.

El módulo mantiene la transferencia radiativa separada de Qt y de Plotly para
que las ecuaciones puedan validarse con pruebas numéricas.  Las frecuencias se
expresan en MHz, las velocidades en km/s, las columnas en cm^-2 y las
temperaturas en K.
"""

from __future__ import annotations

from czspec.network import require_online

from dataclasses import dataclass, replace
import re
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import least_squares

from czspec.utils.numerics import trapezoidal_integral


PLANCK_H = 6.62607015e-34  # J s
BOLTZMANN_K = 1.380649e-23  # J K^-1
LIGHT_SPEED_KMS = 299_792.458
LIGHT_SPEED_CMS = 2.99792458e10


def radio_velocity_offset_kms(
    observed_frequency_mhz: float,
    rest_frequency_mhz: float,
) -> float:
    """Corrimiento radial según la convención radio no relativista.

    Un valor positivo desplaza la transición a una frecuencia observada menor,
    la misma convención que usa :class:`LTEModelConfig`.
    """

    observed = float(observed_frequency_mhz)
    rest = float(rest_frequency_mhz)
    if not np.isfinite(observed) or not np.isfinite(rest) or observed <= 0 or rest <= 0:
        raise ValueError("Las frecuencias observada y de reposo deben ser positivas y finitas.")
    return LIGHT_SPEED_KMS * (rest - observed) / rest


def iram_30m_hpbw_arcsec(frequency_mhz: float) -> float:
    """HPBW aproximado del IRAM 30 m: 2460 / frecuencia(GHz)."""

    frequency = float(frequency_mhz)
    if not np.isfinite(frequency) or frequency <= 0:
        raise ValueError("La frecuencia debe ser positiva y finita.")
    return 2_460_000.0 / frequency


@dataclass(frozen=True)
class LTEModelConfig:
    """Parámetros físicos de un componente homogéneo LTE."""

    column_density_cm2: float
    excitation_temperature_k: float
    linewidth_kms: float
    velocity_offset_kms: float = 0.0
    source_size_arcsec: float | None = None
    beam_size_arcsec: float | None = None
    beam_model: str = "manual"
    background_temperature_k: float = 2.725
    channel_response_fwhm_mhz: float | None = None
    component_label: str = "Componente LTE"

    def validate(self) -> None:
        if not np.isfinite(self.column_density_cm2) or self.column_density_cm2 <= 0:
            raise ValueError("N debe ser una densidad de columna positiva en cm⁻².")
        if not np.isfinite(self.excitation_temperature_k) or self.excitation_temperature_k <= 0:
            raise ValueError("T_ex debe ser mayor que cero.")
        if not np.isfinite(self.linewidth_kms) or self.linewidth_kms <= 0:
            raise ValueError("La anchura FWHM debe ser mayor que cero.")
        if not np.isfinite(self.background_temperature_k) or self.background_temperature_k < 0:
            raise ValueError("La temperatura de fondo no puede ser negativa.")
        if self.source_size_arcsec is not None and self.source_size_arcsec < 0:
            raise ValueError("El tamaño de fuente no puede ser negativo.")
        if self.beam_size_arcsec is not None and self.beam_size_arcsec < 0:
            raise ValueError("El tamaño de haz no puede ser negativo.")
        if self.beam_model not in {"manual", "iram30m"}:
            raise ValueError("El modelo de haz debe ser 'manual' o 'iram30m'.")
        if self.channel_response_fwhm_mhz is not None and self.channel_response_fwhm_mhz < 0:
            raise ValueError("La resolución instrumental no puede ser negativa.")


@dataclass
class LTESpectrumResult:
    frequency_mhz: np.ndarray
    brightness_temperature_k: np.ndarray
    optical_depth: np.ndarray
    isolated_components_k: dict[str, np.ndarray]
    line_diagnostics: pd.DataFrame
    skipped_lines: pd.DataFrame
    beam_filling_factor: float
    partition_function: float


@dataclass(frozen=True)
class LTEComponentSpec:
    """Un componente físico y su catálogo de transiciones asociado."""

    label: str
    transitions: pd.DataFrame
    config: LTEModelConfig
    partition_function: float
    partition_source: str = ""
    method: str = ""
    solution_key: str = ""


@dataclass
class LTEMultiComponentResult:
    """Resultado combinado de componentes LTE radiativamente independientes."""

    frequency_mhz: np.ndarray
    brightness_temperature_k: np.ndarray
    optical_depth: np.ndarray
    component_spectra_k: dict[str, np.ndarray]
    component_results: dict[str, LTESpectrumResult]
    line_diagnostics: pd.DataFrame
    skipped_lines: pd.DataFrame


@dataclass
class LTEFitResult:
    """Refinamiento acotado alrededor de soluciones observacionales de M3."""

    model: LTEMultiComponentResult
    initial_components: list[LTEComponentSpec]
    refined_components: list[LTEComponentSpec]
    parameters: pd.DataFrame
    metrics: dict[str, float | int | bool | str]
    lower_envelope_k: np.ndarray | None = None
    upper_envelope_k: np.ndarray | None = None


def radiation_temperature(frequency_hz: Any, temperature_k: float) -> np.ndarray:
    """Devuelve J_nu(T) = (h nu/k)/(exp(h nu/kT)-1), de forma estable."""

    frequency_hz = np.asarray(frequency_hz, dtype=float)
    if temperature_k <= 0:
        return np.zeros_like(frequency_hz)
    x = PLANCK_H * frequency_hz / (BOLTZMANN_K * float(temperature_k))
    # Para x grande el cociente tiende limpiamente a cero; se silencian solo
    # los avisos numéricos de esa asíntota, no valores de entrada inválidos.
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        result = (PLANCK_H * frequency_hz / BOLTZMANN_K) / np.expm1(x)
    return np.where(np.isfinite(result), result, 0.0)


def gaussian_beam_filling_factor(
    source_size_arcsec: float | None,
    beam_size_arcsec: float | None,
) -> float:
    """Factor de llenado para una fuente y un haz gaussianos.

    Un tamaño ausente o igual a cero significa que no se aplicará corrección
    geométrica (fuente extendida o factor ya incorporado por el usuario).
    """

    if not source_size_arcsec or not beam_size_arcsec:
        return 1.0
    source2 = float(source_size_arcsec) ** 2
    beam2 = float(beam_size_arcsec) ** 2
    return source2 / (source2 + beam2)


def beam_size_for_frequency(config: LTEModelConfig, frequency_mhz: float) -> float | None:
    """Devuelve el HPBW aplicable a una transición concreta."""

    if config.beam_model == "iram30m":
        return iram_30m_hpbw_arcsec(frequency_mhz)
    return config.beam_size_arcsec


def _numeric(row: pd.Series, names: tuple[str, ...]) -> float:
    for name in names:
        if name not in row.index:
            continue
        try:
            value = float(row.get(name))
        except (TypeError, ValueError):
            continue
        if np.isfinite(value):
            return value
    return np.nan


def _frequency_mhz(row: pd.Series, frequency_axis_mhz: np.ndarray) -> float:
    explicit_ghz = _numeric(
        row,
        ("frequency_ghz", "orderedfreq_ghz", "Freq-GHz(rest frame,redshifted)"),
    )
    if np.isfinite(explicit_ghz):
        return explicit_ghz * 1000.0

    value = _numeric(
        row,
        (
            "frequency_mhz",
            "orderedfreq",
            "orderedFreq",
            "measfreq",
            "measFreq",
            "ν[MHz]",
            "ν_obs_MHz",
        ),
    )
    if not np.isfinite(value):
        return np.nan

    # Algunas versiones de astroquery devuelven GHz y otras tablas históricas
    # de CZSpec ya contienen MHz. Solo se transforma cuando 1000*valor cae en
    # la banda observada y el valor original no.
    fmin = float(np.nanmin(frequency_axis_mhz))
    fmax = float(np.nanmax(frequency_axis_mhz))
    padding = max((fmax - fmin) * 0.05, 1.0)
    in_band = fmin - padding <= value <= fmax + padding
    ghz_in_band = fmin - padding <= value * 1000.0 <= fmax + padding
    if not in_band and ghz_in_band:
        return value * 1000.0
    return value


def transition_frequency_mhz(row: pd.Series, frequency_axis_mhz: Any) -> float:
    """Frecuencia en MHz de una fila catalogada para una banda concreta.

    Es la interfaz pública de la normalización interna GHz/MHz y permite que el
    ensamblador multibanda recorte las transiciones sin duplicar heurísticas.
    """

    axis = np.asarray(frequency_axis_mhz, dtype=float)
    if axis.ndim != 1 or axis.size < 2:
        raise ValueError("La banda debe contener al menos dos canales.")
    return float(_frequency_mhz(row, axis))


def _einstein_a_s(row: pd.Series) -> float:
    linear = _numeric(row, ("einstein_a_s", "A_ul", "Aij", "a_ul"))
    if np.isfinite(linear) and linear > 0:
        return linear

    log_value = _numeric(
        row,
        (
            "aij",
            "Aij",
            "loga",
            "logaij",
            "log10_Aij",
            "Log<sub>10</sub> (A<sub>ij</sub>)",
        ),
    )
    if np.isfinite(log_value):
        return 10.0 ** log_value
    return np.nan


def _line_label(row: pd.Series, index: int, frequency_mhz: float) -> str:
    quantum = ""
    for name in ("resolved_QNs", "resolved_qns", "transition", "Resolved QNs"):
        value = str(row.get(name, "") or "").strip()
        if value and value.lower() != "nan":
            quantum = re.sub(r"<[^>]+>", "", value)
            break
    return quantum or f"L{index + 1} · {frequency_mhz:.6f} MHz"


def _convolve_channel_response(
    values: np.ndarray,
    frequency_axis_mhz: np.ndarray,
    response_fwhm_mhz: float | None,
) -> np.ndarray:
    if not response_fwhm_mhz or response_fwhm_mhz <= 0 or len(values) < 3:
        return values
    spacing = float(np.nanmedian(np.abs(np.diff(frequency_axis_mhz))))
    if not np.isfinite(spacing) or spacing <= 0:
        return values
    sigma_bins = float(response_fwhm_mhz) / (2.0 * np.sqrt(2.0 * np.log(2.0))) / spacing
    if sigma_bins < 0.05:
        return values
    return gaussian_filter1d(values, sigma=sigma_bins, mode="nearest")


def simulate_lte_spectrum(
    frequency_mhz: Any,
    transitions: pd.DataFrame,
    config: LTEModelConfig,
    partition_function: float,
) -> LTESpectrumResult:
    """Calcula un espectro LTE homogéneo sobre la cuadrícula observada.

    Las opacidades de las transiciones del componente se suman antes de aplicar
    la ecuación de transferencia. Esto mantiene la saturación física dentro del
    componente. Las curvas aisladas se devuelven solo como diagnóstico visual.
    """

    config.validate()
    frequency_mhz = np.asarray(frequency_mhz, dtype=float)
    if frequency_mhz.ndim != 1 or frequency_mhz.size < 2:
        raise ValueError("La cuadrícula espectral debe ser un vector con al menos dos canales.")
    if not np.all(np.isfinite(frequency_mhz)):
        raise ValueError("La cuadrícula espectral contiene frecuencias no finitas.")
    if transitions is None or transitions.empty:
        raise ValueError("No hay transiciones para construir el modelo LTE.")
    if not np.isfinite(partition_function) or partition_function <= 0:
        raise ValueError("Q(T_ex) debe ser positiva y finita.")

    order = np.argsort(frequency_mhz)
    inverse_order = np.argsort(order)
    freq_sorted = frequency_mhz[order]
    tau_total = np.zeros_like(freq_sorted)
    isolated: dict[str, np.ndarray] = {}
    diagnostics: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    weighted_filling_tau = np.zeros_like(freq_sorted)
    line_fillings: list[float] = []

    for line_index, (_, row) in enumerate(transitions.reset_index(drop=True).iterrows()):
        rest_mhz = _frequency_mhz(row, freq_sorted)
        a_ul = _einstein_a_s(row)
        eu_k = _numeric(row, ("upper_state_energy_K", "eu_k", "E_U (K)", "E_u_K"))
        g_u = _numeric(row, ("upperStateDegen", "upper_state_degeneracy", "g_u", "gu"))
        missing = []
        if not np.isfinite(rest_mhz) or rest_mhz <= 0:
            missing.append("frecuencia")
        if not np.isfinite(a_ul) or a_ul <= 0:
            missing.append("A_ul")
        if not np.isfinite(eu_k) or eu_k < 0:
            missing.append("E_u")
        if not np.isfinite(g_u) or g_u <= 0:
            missing.append("g_u")
        if missing:
            skipped.append({"fila": line_index + 1, "motivo": ", ".join(missing)})
            continue

        center_mhz = rest_mhz * (1.0 - config.velocity_offset_kms / LIGHT_SPEED_KMS)
        nu_hz = rest_mhz * 1.0e6
        n_u = (
            config.column_density_cm2
            * g_u
            * np.exp(-eu_k / config.excitation_temperature_k)
            / float(partition_function)
        )
        linewidth_cms = config.linewidth_kms * 1.0e5
        gaussian_norm = np.sqrt(4.0 * np.log(2.0) / np.pi)
        tau_peak = (
            LIGHT_SPEED_CMS**3
            / (8.0 * np.pi * nu_hz**3)
            * a_ul
            * n_u
            * np.expm1(PLANCK_H * nu_hz / (BOLTZMANN_K * config.excitation_temperature_k))
            * gaussian_norm
            / linewidth_cms
        )
        velocity_kms = LIGHT_SPEED_KMS * (center_mhz - freq_sorted) / center_mhz
        tau_line = tau_peak * np.exp(-4.0 * np.log(2.0) * (velocity_kms / config.linewidth_kms) ** 2)
        tau_total += tau_line

        beam_size = beam_size_for_frequency(config, rest_mhz)
        filling = gaussian_beam_filling_factor(config.source_size_arcsec, beam_size)
        line_fillings.append(filling)
        weighted_filling_tau += filling * tau_line

        j_ex = float(radiation_temperature(nu_hz, config.excitation_temperature_k))
        j_bg = float(radiation_temperature(nu_hz, config.background_temperature_k))
        isolated_line = filling * (j_ex - j_bg) * (1.0 - np.exp(-tau_line))
        isolated_line = _convolve_channel_response(
            isolated_line,
            freq_sorted,
            config.channel_response_fwhm_mhz,
        )
        label = _line_label(row, line_index, rest_mhz)
        unique_label = label
        suffix = 2
        while unique_label in isolated:
            unique_label = f"{label} ({suffix})"
            suffix += 1
        isolated[unique_label] = isolated_line[inverse_order]

        velocity_for_integral = LIGHT_SPEED_KMS * (freq_sorted - center_mhz) / center_mhz
        integrated = abs(trapezoidal_integral(isolated_line, velocity_for_integral))
        diagnostics.append(
            {
                "transición": unique_label,
                "ν_reposo_MHz": rest_mhz,
                "ν_modelo_MHz": center_mhz,
                "E_u_K": eu_k,
                "g_u": g_u,
                "A_ul_s-1": a_ul,
                "tau_pico": tau_peak,
                "HPBW_arcsec": beam_size if beam_size is not None else np.nan,
                "eta_bf": filling,
                "T_pico_aislada_K": float(np.nanmax(isolated_line)),
                "IntInt_aislada_K_km_s": integrated,
            }
        )

    if not diagnostics:
        detail = "; ".join(item["motivo"] for item in skipped[:4])
        raise ValueError(
            "Ninguna transición contiene frecuencia, A_ul, E_u y g_u válidos."
            + (f" Campos faltantes: {detail}." if detail else "")
        )

    nu_axis_hz = freq_sorted * 1.0e6
    with np.errstate(divide="ignore", invalid="ignore"):
        filling_axis = np.divide(
            weighted_filling_tau,
            tau_total,
            out=np.ones_like(tau_total),
            where=tau_total > 0,
        )
    source_function = filling_axis * (
        radiation_temperature(nu_axis_hz, config.excitation_temperature_k)
        - radiation_temperature(nu_axis_hz, config.background_temperature_k)
    )
    brightness = source_function * (1.0 - np.exp(-tau_total))
    brightness = _convolve_channel_response(
        brightness,
        freq_sorted,
        config.channel_response_fwhm_mhz,
    )

    return LTESpectrumResult(
        frequency_mhz=frequency_mhz.copy(),
        brightness_temperature_k=brightness[inverse_order],
        optical_depth=tau_total[inverse_order],
        isolated_components_k=isolated,
        line_diagnostics=pd.DataFrame(diagnostics),
        skipped_lines=pd.DataFrame(skipped),
        beam_filling_factor=float(np.nanmedian(line_fillings)) if line_fillings else 1.0,
        partition_function=float(partition_function),
    )


def simulate_lte_components(
    frequency_mhz: Any,
    components: Iterable[LTEComponentSpec],
) -> LTEMultiComponentResult:
    """Suma componentes independientes, conservando saturación dentro de cada uno.

    Esta geometría equivale a componentes que no se absorben mutuamente dentro
    del haz. Es una hipótesis explícita y reproducible; una transferencia en
    capas requerirá además un orden geométrico y queda fuera del motor LTE 1D.
    """

    specs = list(components)
    if not specs:
        raise ValueError("Añade al menos un componente LTE.")
    frequency = np.asarray(frequency_mhz, dtype=float)
    total = np.zeros_like(frequency)
    tau_diagnostic = np.zeros_like(frequency)
    spectra: dict[str, np.ndarray] = {}
    results: dict[str, LTESpectrumResult] = {}
    diagnostic_frames: list[pd.DataFrame] = []
    skipped_frames: list[pd.DataFrame] = []
    used_labels: set[str] = set()

    for index, spec in enumerate(specs, start=1):
        label = spec.label.strip() or f"Componente {index}"
        unique = label
        suffix = 2
        while unique in used_labels:
            unique = f"{label} ({suffix})"
            suffix += 1
        used_labels.add(unique)
        result = simulate_lte_spectrum(
            frequency,
            spec.transitions,
            spec.config,
            spec.partition_function,
        )
        spectrum = np.asarray(result.brightness_temperature_k, dtype=float)
        total += spectrum
        tau_diagnostic += np.asarray(result.optical_depth, dtype=float)
        spectra[unique] = spectrum
        results[unique] = result
        lines = result.line_diagnostics.copy()
        lines.insert(0, "componente", unique)
        lines.insert(1, "método_M3", spec.method)
        diagnostic_frames.append(lines)
        if not result.skipped_lines.empty:
            omitted = result.skipped_lines.copy()
            omitted.insert(0, "componente", unique)
            skipped_frames.append(omitted)

    return LTEMultiComponentResult(
        frequency_mhz=frequency.copy(),
        brightness_temperature_k=total,
        optical_depth=tau_diagnostic,
        component_spectra_k=spectra,
        component_results=results,
        line_diagnostics=pd.concat(diagnostic_frames, ignore_index=True),
        skipped_lines=(
            pd.concat(skipped_frames, ignore_index=True)
            if skipped_frames
            else pd.DataFrame(columns=["componente", "fila", "motivo"])
        ),
    )


def lte_fit_metrics(
    observed_k: Any,
    model_k: Any,
    *,
    parameter_count: int = 0,
    noise_rms_k: float | None = None,
) -> dict[str, float | int | bool | str]:
    """Métricas globales de comparación en los canales finitos."""

    observed = np.asarray(observed_k, dtype=float)
    model = np.asarray(model_k, dtype=float)
    mask = np.isfinite(observed) & np.isfinite(model)
    residual = observed[mask] - model[mask]
    if residual.size == 0:
        raise ValueError("No hay canales finitos para evaluar el modelo LTE.")
    rss = float(np.sum(residual**2))
    count = int(residual.size)
    rms = float(np.sqrt(rss / count))
    mae = float(np.mean(np.abs(residual)))
    dof = max(count - int(parameter_count), 1)
    result: dict[str, float | int | bool | str] = {
        "n_channels": count,
        "n_parameters": int(parameter_count),
        "degrees_of_freedom": dof,
        "rss_K2": rss,
        "rms_K": rms,
        "mae_K": mae,
        "aic": float(count * np.log(max(rss / count, np.finfo(float).tiny)) + 2 * parameter_count),
        "bic": float(
            count * np.log(max(rss / count, np.finfo(float).tiny))
            + parameter_count * np.log(count)
        ),
    }
    if noise_rms_k is not None and np.isfinite(noise_rms_k) and noise_rms_k > 0:
        chi2 = float(np.sum((residual / float(noise_rms_k)) ** 2))
        result.update(
            {
                "noise_rms_K": float(noise_rms_k),
                "chi2": chi2,
                "reduced_chi2": chi2 / dof,
            }
        )
    return result


def refine_lte_components(
    frequency_mhz: Any,
    observed_k: Any,
    components: Iterable[LTEComponentSpec],
    *,
    fit_column_density: bool = True,
    fit_linewidth: bool = True,
    fit_velocity: bool = True,
    noise_rms_k: float | None = None,
    max_nfev: int = 250,
) -> LTEFitResult:
    """Refina N, FWHM y/o Δv con límites físicos alrededor de M3.

    T_ex y Q(T_ex) permanecen fijadas por la solución MOD/MTH. Esto evita que
    una sola transición intente resolver simultáneamente N y T_ex, una
    degeneración que los datos no necesariamente constriñen.
    """

    initial = list(components)
    if not initial:
        raise ValueError("No hay componentes para refinar.")
    if not any((fit_column_density, fit_linewidth, fit_velocity)):
        raise ValueError("Selecciona al menos un parámetro para refinar.")
    frequency = np.asarray(frequency_mhz, dtype=float)
    observed = np.asarray(observed_k, dtype=float)
    finite = np.isfinite(frequency) & np.isfinite(observed)
    initial_model = simulate_lte_components(frequency, initial)
    fit_window = np.zeros_like(finite, dtype=bool)
    for spec, result in zip(initial, initial_model.component_results.values()):
        for center in pd.to_numeric(
            result.line_diagnostics.get("ν_modelo_MHz", pd.Series(dtype=float)),
            errors="coerce",
        ).dropna():
            half_width_mhz = (
                float(center) * max(5.0 * spec.config.linewidth_kms, 1.0)
                / LIGHT_SPEED_KMS
            )
            fit_window |= np.abs(frequency - float(center)) <= half_width_mhz
    if fit_window.any():
        finite &= fit_window
    if finite.sum() < 5:
        raise ValueError("Se necesitan al menos cinco canales finitos para refinar.")

    x0: list[float] = []
    lower: list[float] = []
    upper: list[float] = []
    descriptors: list[tuple[int, str]] = []
    for index, spec in enumerate(initial):
        cfg = spec.config
        if fit_column_density:
            logn = float(np.log10(cfg.column_density_cm2))
            x0.append(logn)
            lower.append(logn - 2.0)
            upper.append(logn + 2.0)
            descriptors.append((index, "log10_N"))
        if fit_linewidth:
            x0.append(float(cfg.linewidth_kms))
            lower.append(max(0.05, cfg.linewidth_kms * 0.2))
            upper.append(max(cfg.linewidth_kms * 5.0, cfg.linewidth_kms + 0.1))
            descriptors.append((index, "FWHM"))
        if fit_velocity:
            x0.append(float(cfg.velocity_offset_kms))
            lower.append(float(cfg.velocity_offset_kms - 3.0 * cfg.linewidth_kms))
            upper.append(float(cfg.velocity_offset_kms + 3.0 * cfg.linewidth_kms))
            descriptors.append((index, "Delta_v"))

    def unpack(values: np.ndarray) -> list[LTEComponentSpec]:
        configs = [spec.config for spec in initial]
        for value, (index, field) in zip(values, descriptors):
            cfg = configs[index]
            if field == "log10_N":
                cfg = replace(cfg, column_density_cm2=10.0 ** float(value))
            elif field == "FWHM":
                cfg = replace(cfg, linewidth_kms=float(value))
            else:
                cfg = replace(cfg, velocity_offset_kms=float(value))
            configs[index] = cfg
        return [replace(spec, config=configs[index]) for index, spec in enumerate(initial)]

    scale = float(noise_rms_k) if noise_rms_k and noise_rms_k > 0 else 1.0

    def residuals(values: np.ndarray) -> np.ndarray:
        model = simulate_lte_components(frequency, unpack(values))
        return (observed[finite] - model.brightness_temperature_k[finite]) / scale

    optimization = least_squares(
        residuals,
        np.asarray(x0, dtype=float),
        bounds=(np.asarray(lower, dtype=float), np.asarray(upper, dtype=float)),
        loss="soft_l1",
        f_scale=1.0,
        max_nfev=int(max_nfev),
    )
    refined = unpack(optimization.x)
    model = simulate_lte_components(frequency, refined)
    metrics = lte_fit_metrics(
        observed[finite],
        model.brightness_temperature_k[finite],
        parameter_count=len(descriptors),
        noise_rms_k=noise_rms_k,
    )
    metrics.update(
        {
            "fit_window_channels": int(finite.sum()),
            "success": bool(optimization.success),
            "optimizer_status": int(optimization.status),
            "optimizer_message": str(optimization.message),
            "n_function_evaluations": int(optimization.nfev),
        }
    )

    standard_errors = np.full(len(descriptors), np.nan)
    lower_envelope = None
    upper_envelope = None
    if optimization.jac.size and optimization.jac.shape[0] > optimization.jac.shape[1]:
        try:
            jac = np.asarray(optimization.jac, dtype=float)
            covariance = np.linalg.pinv(jac.T @ jac)
            variance = 2.0 * float(optimization.cost) / max(jac.shape[0] - jac.shape[1], 1)
            covariance *= variance
            standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0.0))
            rng = np.random.default_rng(36)
            draws = rng.multivariate_normal(optimization.x, covariance, size=120)
            draws = np.clip(draws, np.asarray(lower), np.asarray(upper))
            model_draws = np.asarray(
                [
                    simulate_lte_components(frequency, unpack(draw)).brightness_temperature_k
                    for draw in draws
                ]
            )
            lower_envelope = np.nanpercentile(model_draws, 16.0, axis=0)
            upper_envelope = np.nanpercentile(model_draws, 84.0, axis=0)
        except (ValueError, np.linalg.LinAlgError):
            standard_errors[:] = np.nan

    rows: list[dict[str, Any]] = []
    for position, ((component_index, field), value, error) in enumerate(
        zip(descriptors, optimization.x, standard_errors)
    ):
        initial_value = x0[position]
        if field == "log10_N":
            display_field = "N_total_cm-2"
            fitted_value = 10.0 ** float(value)
            start_value = 10.0 ** float(initial_value)
            uncertainty = (
                fitted_value * np.log(10.0) * float(error)
                if np.isfinite(error)
                else np.nan
            )
        else:
            display_field = "FWHM_km_s-1" if field == "FWHM" else "Delta_v_km_s-1"
            fitted_value = float(value)
            start_value = float(initial_value)
            uncertainty = float(error) if np.isfinite(error) else np.nan
        rows.append(
            {
                "componente": initial[component_index].label,
                "parámetro": display_field,
                "valor_M3": start_value,
                "valor_refinado": fitted_value,
                "incertidumbre_aprox_1sigma": uncertainty,
                "en_límite": bool(
                    np.isclose(value, lower[position], rtol=0, atol=1e-7)
                    or np.isclose(value, upper[position], rtol=0, atol=1e-7)
                ),
            }
        )

    return LTEFitResult(
        model=model,
        initial_components=initial,
        refined_components=refined,
        parameters=pd.DataFrame(rows),
        metrics=metrics,
        lower_envelope_k=lower_envelope,
        upper_envelope_k=upper_envelope,
    )


def query_splatalogue_transitions(
    species_name: str,
    min_frequency_mhz: float,
    max_frequency_mhz: float,
    *,
    line_lists: tuple[str, ...] = ("CDMS", "JPL"),
    molecule_tag: int | None = None,
    species_id: int | None = None,
) -> pd.DataFrame:
    """Consulta las transiciones de una especie dentro de una banda.

    Astroquery se importa dentro de la función para mantener disponible el
    motor LTE y sus pruebas aun cuando no haya conexión o cliente de catálogos.
    """

    require_online("Splatalogue LTE catalog query")
    if not species_name or not species_name.strip():
        raise ValueError("Selecciona una especie molecular.")
    if not np.isfinite(min_frequency_mhz) or not np.isfinite(max_frequency_mhz):
        raise ValueError("El rango de frecuencias no es válido.")
    if max_frequency_mhz <= min_frequency_mhz:
        raise ValueError("La frecuencia máxima debe ser mayor que la mínima.")

    from astropy import units as u
    from astroquery.splatalogue import Splatalogue

    species_expression = rf" {re.escape(species_name.strip())} "
    table = Splatalogue.query_lines(
        min_frequency=float(min_frequency_mhz) * u.MHz,
        max_frequency=float(max_frequency_mhz) * u.MHz,
        chemical_name=species_expression,
        line_lists=list(line_lists),
        line_strengths=["Aij"],
        energy_levels=["Four"],
        show_upper_degeneracy=True,
        show_molecule_tag=True,
        show_qn_code=True,
        export_limit=1000,
    )
    if table is None or len(table) == 0:
        return pd.DataFrame()
    result = table.to_pandas()

    def filter_numeric_identifier(frame: pd.DataFrame, columns: tuple[str, ...], target: int | None):
        if target is None:
            return frame
        for column in columns:
            if column not in frame.columns:
                continue
            numeric = pd.to_numeric(frame[column], errors="coerce").abs()
            matches = frame[numeric == abs(int(target))]
            if not matches.empty:
                return matches
        return frame

    result = filter_numeric_identifier(result, ("moleculeTag", "molecule_tag"), molecule_tag)
    result = filter_numeric_identifier(result, ("species_id", "speciesId"), species_id)
    return result.reset_index(drop=True)
