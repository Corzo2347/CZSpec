"""Transferencia radiativa no-LTE reproducible para CZSpec.

El motor usa archivos en formato LAMDA y ``pythonradex`` como solucionador de
poblaciones.  La capa de este módulo mantiene explícitas las unidades que usa
CZSpec (MHz, km/s, cm-2, cm-3 y K), descuenta el fondo continuo para comparar
con espectros con línea base sustraída y evalúa las mismas componentes sobre
una o varias bandas observadas.

``pythonradex`` se importa de forma diferida: CZSpec puede abrir y seguir
usando M1--M3 aunque el backend no-LTE no esté instalado correctamente.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import numpy as np
import pandas as pd
from scipy import constants
from scipy.ndimage import gaussian_filter1d

from czspec.logic.lte_model import (
    LIGHT_SPEED_KMS,
    gaussian_beam_filling_factor,
    iram_30m_hpbw_arcsec,
    lte_fit_metrics,
)


SUPPORTED_GEOMETRIES = {
    "static sphere RADEX": "Esfera estática (convención RADEX)",
    "static sphere": "Esfera estática",
    "static slab": "Lámina estática",
}
COLLIDER_LABELS = {
    "H2": "H₂",
    "para-H2": "para-H₂",
    "ortho-H2": "orto-H₂",
    "e": "e⁻",
    "H": "H",
    "He": "He",
    "H+": "H⁺",
}


@dataclass(frozen=True)
class NonLTEComponentSpec:
    """Condiciones de una componente homogénea no-LTE."""

    label: str
    lamda_file: str | Path
    column_density_cm2: float
    kinetic_temperature_k: float
    linewidth_kms: float
    h2_density_cm3: float
    h2_ortho_para_ratio: float = 3.0
    additional_colliders_cm3: Mapping[str, float] | None = None
    geometry: str = "static sphere RADEX"
    velocity_offset_kms: float = 0.0
    source_size_arcsec: float | None = None
    beam_size_arcsec: float | None = None
    beam_model: str = "manual"
    background_temperature_k: float = 2.725
    channel_response_fwhm_mhz: float | None = None
    treat_line_overlap: bool = False
    method: str = ""
    solution_key: str = ""

    def validate(self) -> None:
        path = Path(self.lamda_file).expanduser()
        if not path.is_file():
            raise ValueError(f"No se encontró el archivo LAMDA: {path}")
        if self.geometry not in SUPPORTED_GEOMETRIES:
            raise ValueError("Selecciona una geometría no-LTE compatible.")
        for value, label in (
            (self.column_density_cm2, "N total"),
            (self.kinetic_temperature_k, "T cinética"),
            (self.linewidth_kms, "FWHM"),
            (self.h2_density_cm3, "n(H₂)"),
        ):
            if not np.isfinite(value) or value <= 0:
                raise ValueError(f"{label} debe ser positiva y finita.")
        if (
            not np.isfinite(self.h2_ortho_para_ratio)
            or self.h2_ortho_para_ratio < 0
        ):
            raise ValueError("La razón orto/para de H₂ no puede ser negativa.")
        if self.beam_model not in {"manual", "iram30m"}:
            raise ValueError("El modelo de haz debe ser manual o iram30m.")
        if self.background_temperature_k < 0:
            raise ValueError("La temperatura de fondo no puede ser negativa.")


@dataclass
class NonLTEComponentResult:
    frequency_mhz: np.ndarray
    brightness_temperature_k: np.ndarray
    optical_depth: np.ndarray
    line_diagnostics: pd.DataFrame
    available_colliders: tuple[str, ...]
    collider_densities_cm3: dict[str, float]
    temperature_limits_k: dict[str, tuple[float, float]]
    convergence_iterations: int
    lamda_sha256: str
    backend_version: str


@dataclass
class NonLTEBandResult:
    frequency_mhz: np.ndarray
    brightness_temperature_k: np.ndarray
    optical_depth: np.ndarray
    component_spectra_k: dict[str, np.ndarray]
    component_results: dict[str, NonLTEComponentResult]
    line_diagnostics: pd.DataFrame


@dataclass
class NonLTESessionResult:
    band_results: dict[str, NonLTEBandResult]
    line_diagnostics: pd.DataFrame
    metrics_by_band: dict[str, dict[str, Any]]
    metrics: dict[str, Any]
    omitted_components: list[dict[str, str]]


@dataclass
class _SolvedBackendComponent:
    source: Any
    spec: NonLTEComponentSpec
    available_colliders: tuple[str, ...]
    collider_densities_cm3: dict[str, float]
    temperature_limits_k: dict[str, tuple[float, float]]
    backend_version: str
    lamda_sha256: str


def lamda_molecule_name(path: str | Path) -> str:
    """Lee el nombre declarado en un archivo LAMDA sin cargar el backend."""

    for raw_line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        text = raw_line.strip()
        if text and not text.startswith("!"):
            return text
    raise ValueError("El archivo LAMDA no contiene un nombre molecular legible.")


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_pythonradex():
    try:
        import pythonradex
        from pythonradex.radiative_transfer import Source
    except Exception as exc:  # pragma: no cover - depende de instalación externa
        raise RuntimeError(
            "El backend pythonradex no está disponible. Reinstala CZSpec con sus "
            "dependencias científicas o ejecuta la actualización desde el instalador."
        ) from exc
    return Source, str(getattr(pythonradex, "__version__", "desconocida"))


def planck_specific_intensity(frequency_hz: Any, temperature_k: float) -> np.ndarray:
    frequency = np.asarray(frequency_hz, dtype=float)
    if temperature_k <= 0:
        return np.zeros_like(frequency)
    x = constants.h * frequency / (constants.k * float(temperature_k))
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        value = (
            2.0
            * constants.h
            * frequency**3
            / constants.c**2
            / np.expm1(x)
        )
    return np.where(np.isfinite(value), value, 0.0)


def rj_brightness_temperature(specific_intensity: Any, frequency_hz: Any) -> np.ndarray:
    intensity = np.asarray(specific_intensity, dtype=float)
    frequency = np.asarray(frequency_hz, dtype=float)
    return intensity * constants.c**2 / (2.0 * frequency**2 * constants.k)


def collider_densities_for_file(
    available_colliders: Iterable[str],
    *,
    h2_density_cm3: float,
    h2_ortho_para_ratio: float,
    additional_colliders_cm3: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Adapta n(H2) total a los colisionadores realmente tabulados.

    Si LAMDA separa para/orto-H2, la densidad total se reparte según la razón
    indicada. Si sólo ofrece una de las dos formas, se conserva únicamente la
    fracción correspondiente. Los colisionadores adicionales sólo se usan si
    están presentes en el archivo.
    """

    available = {str(value) for value in available_colliders}
    result: dict[str, float] = {}
    h2_total = float(h2_density_cm3)
    ratio = float(h2_ortho_para_ratio)
    if "H2" in available:
        result["H2"] = h2_total
    else:
        para = h2_total / (1.0 + ratio)
        ortho = h2_total - para
        if "para-H2" in available and para > 0:
            result["para-H2"] = para
        if "ortho-H2" in available and ortho > 0:
            result["ortho-H2"] = ortho
    for collider, density in dict(additional_colliders_cm3 or {}).items():
        value = float(density)
        if collider in available and np.isfinite(value) and value > 0:
            result[collider] = value
    if not result:
        labels = ", ".join(sorted(available)) or "ninguno"
        raise ValueError(
            "No hay una densidad positiva para los colisionadores del archivo "
            f"LAMDA ({labels})."
        )
    return result


def _validate_temperature_ranges(
    kinetic_temperature_k: float,
    densities_cm3: Mapping[str, float],
    limits: Mapping[str, tuple[float, float]],
) -> None:
    invalid = []
    for collider in densities_cm3:
        if collider not in limits:
            continue
        lower, upper = limits[collider]
        if not lower <= kinetic_temperature_k <= upper:
            invalid.append(f"{collider}: {lower:g}--{upper:g} K")
    if invalid:
        raise ValueError(
            f"Tkin={kinetic_temperature_k:g} K queda fuera de los datos colisionales "
            "de LAMDA (" + "; ".join(invalid) + "). CZSpec no extrapola silenciosamente."
        )


def _beam_filling_axis(spec: NonLTEComponentSpec, frequency_mhz: np.ndarray) -> np.ndarray:
    if not spec.source_size_arcsec or spec.source_size_arcsec <= 0:
        return np.ones_like(frequency_mhz, dtype=float)
    if spec.beam_model == "iram30m":
        beam = 2_460_000.0 / np.asarray(frequency_mhz, dtype=float)
        source2 = float(spec.source_size_arcsec) ** 2
        return source2 / (source2 + beam**2)
    value = gaussian_beam_filling_factor(
        spec.source_size_arcsec,
        spec.beam_size_arcsec,
    )
    return np.full_like(frequency_mhz, float(value), dtype=float)


def _convolve(values: np.ndarray, axis_mhz: np.ndarray, fwhm_mhz: float | None):
    if not fwhm_mhz or fwhm_mhz <= 0 or values.size < 3:
        return values
    spacing = float(np.nanmedian(np.abs(np.diff(axis_mhz))))
    if not np.isfinite(spacing) or spacing <= 0:
        return values
    sigma_bins = float(fwhm_mhz) / (2.0 * np.sqrt(2.0 * np.log(2.0))) / spacing
    if sigma_bins < 0.05:
        return values
    return gaussian_filter1d(values, sigma=sigma_bins, mode="nearest")


def _background_subtracted_rj(
    source,
    frequency_hz: np.ndarray,
    background_temperature_k: float,
) -> tuple[np.ndarray, np.ndarray]:
    tau = np.asarray(source.tau(frequency_hz), dtype=float)
    emitted = np.asarray(
        source.spectrum(frequency_hz, output_type="specific intensity"),
        dtype=float,
    )
    background_blocked = planck_specific_intensity(
        frequency_hz, background_temperature_k
    ) * (1.0 - np.exp(-tau))
    return rj_brightness_temperature(emitted - background_blocked, frequency_hz), tau


def _solve_backend_component(
    spec: NonLTEComponentSpec,
    source_factory: Callable[..., Any] | None,
    backend_version: str | None,
) -> _SolvedBackendComponent:
    spec.validate()
    if source_factory is None:
        source_factory, detected_version = _load_pythonradex()
        backend_version = backend_version or detected_version
    backend_version = str(backend_version or "prueba")
    source = source_factory(
        datafilepath=str(Path(spec.lamda_file).expanduser()),
        geometry=spec.geometry,
        line_profile_type="Gaussian",
        width_v=float(spec.linewidth_kms) * 1000.0,
        treat_line_overlap=bool(spec.treat_line_overlap),
        warn_negative_tau=True,
    )
    molecule = source.emitting_molecule
    available = tuple(str(value) for value in molecule.coll_transitions.keys())
    limits = {
        str(key): (float(value[0]), float(value[1]))
        for key, value in molecule.Tkin_data_limits.items()
    }
    densities_cm3 = collider_densities_for_file(
        available,
        h2_density_cm3=spec.h2_density_cm3,
        h2_ortho_para_ratio=spec.h2_ortho_para_ratio,
        additional_colliders_cm3=spec.additional_colliders_cm3,
    )
    _validate_temperature_ranges(spec.kinetic_temperature_k, densities_cm3, limits)
    background = lambda nu: planck_specific_intensity(  # noqa: E731
        nu, spec.background_temperature_k
    )
    source.update_parameters(
        N=float(spec.column_density_cm2) * 1.0e4,
        Tkin=float(spec.kinetic_temperature_k),
        collider_densities={key: value * 1.0e6 for key, value in densities_cm3.items()},
        ext_background=background,
        T_dust=0.0,
        tau_dust=0.0,
    )
    source.solve_radiative_transfer()
    return _SolvedBackendComponent(
        source=source,
        spec=spec,
        available_colliders=available,
        collider_densities_cm3=densities_cm3,
        temperature_limits_k=limits,
        backend_version=backend_version,
        lamda_sha256=file_sha256(spec.lamda_file),
    )


def _evaluate_solved_component(
    frequency_mhz: Any,
    solved: _SolvedBackendComponent,
) -> NonLTEComponentResult:
    spec = solved.spec
    source = solved.source
    molecule = source.emitting_molecule
    axis = np.asarray(frequency_mhz, dtype=float)
    if axis.ndim != 1 or axis.size < 2 or not np.all(np.isfinite(axis)):
        raise ValueError("La cuadrícula espectral no es válida.")

    order = np.argsort(axis)
    inverse = np.argsort(order)
    observed_sorted = axis[order]
    shift = 1.0 - float(spec.velocity_offset_kms) / LIGHT_SPEED_KMS
    if shift <= 0:
        raise ValueError("El desplazamiento de velocidad no es físicamente válido.")
    source_frequency_hz = observed_sorted * 1.0e6 / shift
    brightness, tau = _background_subtracted_rj(
        source,
        source_frequency_hz,
        spec.background_temperature_k,
    )
    filling = _beam_filling_axis(spec, observed_sorted)
    brightness = _convolve(
        brightness * filling,
        observed_sorted,
        spec.channel_response_fwhm_mhz,
    )

    transition_frequencies = np.asarray(molecule.nu0, dtype=float) / 1.0e6 * shift
    fmin = float(np.nanmin(observed_sorted))
    fmax = float(np.nanmax(observed_sorted))
    padding = max((fmax - fmin) * 0.01, 0.5)
    selected = np.where(
        (transition_frequencies >= fmin - padding)
        & (transition_frequencies <= fmax + padding)
    )[0]
    rows: list[dict[str, Any]] = []
    for index in selected:
        transition = molecule.rad_transitions[int(index)]
        observed_frequency = float(transition_frequencies[index])
        beam_size = (
            iram_30m_hpbw_arcsec(observed_frequency)
            if spec.beam_model == "iram30m"
            else spec.beam_size_arcsec
        )
        rows.append(
            {
                "componente": spec.label,
                "método_M3": spec.method,
                "archivo_LAMDA": Path(spec.lamda_file).name,
                "índice_LAMDA": int(index) + 1,
                "transición": str(getattr(transition, "name", f"L{index + 1}")),
                "ν_reposo_MHz": float(molecule.nu0[index] / 1.0e6),
                "ν_modelo_MHz": observed_frequency,
                "E_u_K": float(transition.up.E / constants.k),
                "g_u": float(transition.up.g),
                "A_ul_s-1": float(transition.A21),
                "T_ex_noLTE_K": float(source.Tex[index]),
                "tau_pico": float(source.tau_nu0_individual_transitions[index]),
                "población_inferior": float(source.lower_level_population[index]),
                "población_superior": float(source.upper_level_population[index]),
                "HPBW_arcsec": beam_size,
                "eta_bf": float(
                    gaussian_beam_filling_factor(spec.source_size_arcsec, beam_size)
                ),
                "Tkin_K": float(spec.kinetic_temperature_k),
                "N_total_cm-2": float(spec.column_density_cm2),
                "FWHM_km_s": float(spec.linewidth_kms),
                "Delta_v_km_s": float(spec.velocity_offset_kms),
                "geometría": spec.geometry,
            }
        )
    return NonLTEComponentResult(
        frequency_mhz=axis.copy(),
        brightness_temperature_k=np.asarray(brightness, dtype=float)[inverse],
        optical_depth=np.asarray(tau, dtype=float)[inverse],
        line_diagnostics=pd.DataFrame(rows),
        available_colliders=solved.available_colliders,
        collider_densities_cm3=solved.collider_densities_cm3,
        temperature_limits_k=solved.temperature_limits_k,
        convergence_iterations=int(getattr(source, "n_iter_convergence", 0)),
        lamda_sha256=solved.lamda_sha256,
        backend_version=solved.backend_version,
    )


def simulate_nonlte_component(
    frequency_mhz: Any,
    spec: NonLTEComponentSpec,
    *,
    source_factory: Callable[..., Any] | None = None,
    backend_version: str | None = None,
) -> NonLTEComponentResult:
    """Resuelve una componente y genera su espectro continuo por canales."""

    solved = _solve_backend_component(spec, source_factory, backend_version)
    return _evaluate_solved_component(frequency_mhz, solved)


def simulate_nonlte_session(
    frequency_axes_mhz: Mapping[str, Any],
    observed_by_band_k: Mapping[str, Any],
    components: Iterable[NonLTEComponentSpec],
    *,
    source_factory: Callable[..., Any] | None = None,
    backend_version: str | None = None,
    progress: Callable[[int, str], None] | None = None,
) -> NonLTESessionResult:
    """Evalúa todas las componentes en todas las bandas de la sesión."""

    specs = list(components)
    if not specs:
        raise ValueError("Asigna al menos una componente a un archivo LAMDA.")
    axes = {
        str(name): np.asarray(values, dtype=float)
        for name, values in frequency_axes_mhz.items()
    }
    totals = {name: np.zeros_like(axis) for name, axis in axes.items()}
    tau_totals = {name: np.zeros_like(axis) for name, axis in axes.items()}
    spectra_by_band: dict[str, dict[str, np.ndarray]] = {
        name: {} for name in axes
    }
    results_by_band: dict[str, dict[str, NonLTEComponentResult]] = {
        name: {} for name in axes
    }
    diagnostics_by_band: dict[str, list[pd.DataFrame]] = {
        name: [] for name in axes
    }
    band_results: dict[str, NonLTEBandResult] = {}
    diagnostics: list[pd.DataFrame] = []
    omitted: list[dict[str, str]] = []
    all_observed: list[np.ndarray] = []
    all_model: list[np.ndarray] = []
    metrics_by_band: dict[str, dict[str, Any]] = {}
    total_jobs = max(len(axes) * len(specs), 1)
    completed = 0
    for spec in specs:
        if progress:
            progress(
                5 + int(82 * completed / total_jobs),
                f"Resolviendo poblaciones: {spec.label}",
            )
        try:
            solved = _solve_backend_component(spec, source_factory, backend_version)
        except Exception as exc:
            omitted.append(
                {
                    "espectro": "sesión",
                    "componente": spec.label,
                    "motivo": str(exc),
                }
            )
            completed += len(axes)
            continue
        for band_name, axis in axes.items():
            completed += 1
            if progress:
                progress(
                    5 + int(82 * completed / total_jobs),
                    f"No-LTE: {spec.label} · {Path(str(band_name)).name}",
                )
            try:
                result = _evaluate_solved_component(axis, solved)
            except Exception as exc:
                omitted.append(
                    {
                        "espectro": str(band_name),
                        "componente": spec.label,
                        "motivo": str(exc),
                    }
                )
                continue
            spectrum = np.asarray(result.brightness_temperature_k, dtype=float)
            totals[band_name] += spectrum
            tau_totals[band_name] += np.asarray(result.optical_depth, dtype=float)
            spectra_by_band[band_name][spec.label] = spectrum
            results_by_band[band_name][spec.label] = result
            if not result.line_diagnostics.empty:
                frame = result.line_diagnostics.copy()
                frame.insert(0, "espectro", str(band_name))
                diagnostics.append(frame)
                diagnostics_by_band[band_name].append(frame)
    for band_name, axis in axes.items():
        band_result = NonLTEBandResult(
            frequency_mhz=axis.copy(),
            brightness_temperature_k=totals[band_name],
            optical_depth=tau_totals[band_name],
            component_spectra_k=spectra_by_band[band_name],
            component_results=results_by_band[band_name],
            line_diagnostics=(
                pd.concat(diagnostics_by_band[band_name], ignore_index=True)
                if diagnostics_by_band[band_name]
                else pd.DataFrame()
            ),
        )
        band_results[str(band_name)] = band_result
        observed = np.asarray(observed_by_band_k[str(band_name)], dtype=float)
        metrics_by_band[str(band_name)] = lte_fit_metrics(
            observed, totals[band_name]
        )
        all_observed.append(observed)
        all_model.append(totals[band_name])
    if not any(result.component_results for result in band_results.values()):
        details = "; ".join(item["motivo"] for item in omitted[:3])
        raise ValueError(
            "Ninguna componente no-LTE pudo resolverse. " + details
        )
    metrics = lte_fit_metrics(np.concatenate(all_observed), np.concatenate(all_model))
    metrics["n_spectra"] = len(band_results)
    metrics["n_components_requested"] = len(specs)
    metrics["n_component_band_failures"] = len(omitted)
    return NonLTESessionResult(
        band_results=band_results,
        line_diagnostics=(
            pd.concat(diagnostics, ignore_index=True) if diagnostics else pd.DataFrame()
        ),
        metrics_by_band=metrics_by_band,
        metrics=metrics,
        omitted_components=omitted,
    )
