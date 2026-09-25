"""Ensamblaje reproducible de una sesión LTE global.

Este módulo no depende de Qt.  Convierte las soluciones físicas del módulo 3
en una componente por especie, conserva su procedencia y permite simular esas
componentes sobre todas las bandas observadas en el módulo 1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from czspec.logic.lte_model import (
    LTEComponentSpec,
    LTEMultiComponentResult,
    simulate_lte_components,
    transition_frequency_mhz,
)


@dataclass
class LTESessionResult:
    """Modelo LTE evaluado sobre una o varias bandas observadas."""

    band_results: dict[str, LTEMultiComponentResult]
    omitted_components: dict[str, list[str]]
    line_diagnostics: pd.DataFrame
    skipped_lines: pd.DataFrame


def available_tex_values(
    solutions: Mapping[str, Mapping[str, Any]],
    method: str,
) -> list[float]:
    """Temperaturas finitas disponibles para MOD o MTH."""

    target = str(method).strip().upper()
    values: set[float] = set()
    for solution in solutions.values():
        if str(solution.get("method", "")).strip().upper() != target:
            continue
        try:
            value = float(solution.get("tex_k", np.nan))
        except (TypeError, ValueError):
            continue
        if np.isfinite(value) and value > 0:
            values.add(value)
    return sorted(values)


def _geometric_median(values: Iterable[float]) -> float:
    finite = np.asarray(
        [float(value) for value in values if np.isfinite(value) and float(value) > 0],
        dtype=float,
    )
    if finite.size == 0:
        raise ValueError("No hay densidades de columna positivas para agrupar.")
    return float(10.0 ** np.median(np.log10(finite)))


def aggregate_global_solutions(
    solutions: Mapping[str, Mapping[str, Any]],
    method: str,
    tex_k: float,
    *,
    atol_k: float = 1.0e-6,
) -> list[dict[str, Any]]:
    """Agrupa soluciones de M3 en una componente inicial por especie.

    Para una misma identidad molecular pueden existir varias estimaciones de
    N procedentes de transiciones diferentes. Sumarlas produciría componentes
    físicos duplicados. Por eso se usa la mediana geométrica de N y medianas
    ordinarias para FWHM y desplazamiento. Las soluciones originales quedan en
    ``member_solution_keys`` para auditoría y edición posterior.
    """

    target_method = str(method).strip().upper()
    target_tex = float(tex_k)
    grouped: dict[str, list[tuple[str, Mapping[str, Any]]]] = {}
    for key, solution in solutions.items():
        if str(solution.get("method", "")).strip().upper() != target_method:
            continue
        value = float(solution.get("tex_k", np.nan))
        if not np.isfinite(value) or not np.isclose(value, target_tex, atol=atol_k, rtol=0):
            continue
        species_key = str(solution.get("species_key", "")).strip()
        if not species_key:
            continue
        grouped.setdefault(species_key, []).append((str(key), solution))

    seeds: list[dict[str, Any]] = []
    for species_key, candidates in grouped.items():
        columns = [float(item[1]["column_density_cm2"]) for item in candidates]
        widths = [
            float(item[1].get("linewidth_kms", np.nan))
            for item in candidates
            if np.isfinite(float(item[1].get("linewidth_kms", np.nan)))
            and float(item[1].get("linewidth_kms", 0.0)) > 0
        ]
        velocities = [
            float(item[1].get("velocity_offset_kms", np.nan))
            for item in candidates
            if np.isfinite(float(item[1].get("velocity_offset_kms", np.nan)))
        ]
        representative_key, representative = min(
            candidates,
            key=lambda item: abs(
                np.log10(float(item[1]["column_density_cm2"]))
                - np.median(np.log10(np.asarray(columns, dtype=float)))
            ),
        )
        seed = dict(representative)
        seed.update(
            {
                "method": target_method,
                "species_key": species_key,
                "tex_k": target_tex,
                "column_density_cm2": _geometric_median(columns),
                "linewidth_kms": float(np.median(widths)) if widths else np.nan,
                "velocity_offset_kms": float(np.median(velocities)) if velocities else np.nan,
                "representative_solution_key": representative_key,
                "member_solution_keys": [item[0] for item in candidates],
                "n_input_solutions": len(candidates),
                "column_density_min_cm2": float(np.min(columns)),
                "column_density_max_cm2": float(np.max(columns)),
            }
        )
        seeds.append(seed)

    return sorted(
        seeds,
        key=lambda seed: (
            str(seed.get("target_name", "")).casefold(),
            str(seed.get("species_key", "")),
        ),
    )


def transitions_for_species(
    frame: pd.DataFrame | None,
    source_row: pd.Series,
) -> pd.DataFrame:
    """Selecciona todas las transiciones de M2 que comparten identidad molecular."""

    if frame is None or frame.empty:
        return pd.DataFrame()
    result = frame.copy()
    masks: list[pd.Series] = []
    for column in ("moleculeTag", "species_id"):
        if column not in result.columns or column not in source_row.index:
            continue
        target = pd.to_numeric(pd.Series([source_row.get(column)]), errors="coerce").iloc[0]
        if pd.notna(target):
            values = pd.to_numeric(result[column], errors="coerce")
            masks.append(values.notna() & np.isclose(values.abs(), abs(float(target))))
    linelist = str(source_row.get("linelist", "") or "").strip().casefold()
    if masks:
        mask = masks[0].copy()
        for candidate in masks[1:]:
            mask |= candidate
        if linelist and "linelist" in result.columns:
            mask &= (
                result["linelist"].fillna("").astype(str).str.strip().str.casefold()
                == linelist
            )
        matched = result.loc[mask]
        if not matched.empty:
            return _deduplicate_transitions(matched)

    name = str(source_row.get("name", "") or "").strip().casefold()
    if name and "name" in result.columns:
        mask = result["name"].fillna("").astype(str).str.strip().str.casefold() == name
        matched = result.loc[mask]
        if not matched.empty:
            return _deduplicate_transitions(matched)
    return pd.DataFrame()


def _deduplicate_transitions(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    candidates = [
        column
        for column in ("orderedfreq", "orderedFreq", "frequency_mhz", "ν_obs_MHz")
        if column in result.columns
    ]
    identity = [
        column
        for column in ("moleculeTag", "species_id", "linelist", "name")
        if column in result.columns
    ]
    subset = identity + candidates[:1]
    if subset:
        result = result.drop_duplicates(subset=subset, keep="first")
    return result.reset_index(drop=True)


def transitions_in_band(
    transitions: pd.DataFrame,
    frequency_axis_mhz: Iterable[float],
    *,
    padding_fraction: float = 0.01,
) -> pd.DataFrame:
    """Recorta transiciones a la banda de una cuadrícula observada."""

    axis = np.asarray(frequency_axis_mhz, dtype=float)
    if axis.size < 2 or transitions is None or transitions.empty:
        return pd.DataFrame()
    fmin = float(np.nanmin(axis))
    fmax = float(np.nanmax(axis))
    padding = max((fmax - fmin) * float(padding_fraction), 0.5)
    keep = []
    for _, row in transitions.iterrows():
        value = transition_frequency_mhz(row, axis)
        keep.append(bool(np.isfinite(value) and fmin - padding <= value <= fmax + padding))
    return transitions.loc[keep].reset_index(drop=True)


def simulate_lte_session(
    frequency_axes_mhz: Mapping[str, Iterable[float]],
    components: Iterable[LTEComponentSpec],
) -> LTESessionResult:
    """Evalúa las mismas componentes sobre todas las bandas de la sesión."""

    specs = list(components)
    if not specs:
        raise ValueError("Añade al menos una componente LTE.")
    results: dict[str, LTEMultiComponentResult] = {}
    omitted: dict[str, list[str]] = {}
    diagnostics: list[pd.DataFrame] = []
    skipped: list[pd.DataFrame] = []
    for band_name, axis_values in frequency_axes_mhz.items():
        axis = np.asarray(axis_values, dtype=float)
        band_specs: list[LTEComponentSpec] = []
        omitted_labels: list[str] = []
        for spec in specs:
            selected = transitions_in_band(spec.transitions, axis)
            if selected.empty:
                omitted_labels.append(spec.label)
                continue
            band_specs.append(
                LTEComponentSpec(
                    label=spec.label,
                    transitions=selected,
                    config=spec.config,
                    partition_function=spec.partition_function,
                    partition_source=spec.partition_source,
                    method=spec.method,
                    solution_key=spec.solution_key,
                )
            )
        omitted[str(band_name)] = omitted_labels
        if not band_specs:
            results[str(band_name)] = LTEMultiComponentResult(
                frequency_mhz=axis.copy(),
                brightness_temperature_k=np.zeros_like(axis),
                optical_depth=np.zeros_like(axis),
                component_spectra_k={},
                component_results={},
                line_diagnostics=pd.DataFrame(
                    columns=["componente", "método_M3", "transición"]
                ),
                skipped_lines=pd.DataFrame(
                    columns=["componente", "fila", "motivo"]
                ),
            )
            continue
        result = simulate_lte_components(axis, band_specs)
        results[str(band_name)] = result
        line_frame = result.line_diagnostics.copy()
        line_frame.insert(0, "espectro", str(band_name))
        diagnostics.append(line_frame)
        if not result.skipped_lines.empty:
            skipped_frame = result.skipped_lines.copy()
            skipped_frame.insert(0, "espectro", str(band_name))
            skipped.append(skipped_frame)

    if not results or not diagnostics:
        raise ValueError(
            "Ninguna transición seleccionada cae dentro de las bandas observadas."
        )
    return LTESessionResult(
        band_results=results,
        omitted_components=omitted,
        line_diagnostics=pd.concat(diagnostics, ignore_index=True),
        skipped_lines=(
            pd.concat(skipped, ignore_index=True)
            if skipped
            else pd.DataFrame(columns=["espectro", "componente", "fila", "motivo"])
        ),
    )
