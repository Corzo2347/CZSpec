"""Transformaciones reproducibles para explorar gráficamente tablas M2/M3."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd


def _clean_label_value(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"", "nan", "none", "—"} else text


def with_scientific_series(frame: pd.DataFrame) -> pd.DataFrame:
    """Añade una clave de serie que no mezcle moléculas, métodos ni referencias."""

    prepared = frame.copy()

    def build_label(row: pd.Series) -> str:
        obs = _clean_label_value(row.get("obs_id"))
        if obs.endswith(".0"):
            obs = obs[:-2]
        species = _clean_label_value(row.get("name"))
        chemical = _clean_label_value(row.get("chemical_name"))
        method = _clean_label_value(row.get("Método"))
        reference = _clean_label_value(row.get("Referencia"))
        reference_id = _clean_label_value(row.get("ID de referencia"))

        parts = []
        if obs:
            parts.append(f"obs {obs}")
        if species:
            parts.append(species)
        elif chemical:
            parts.append(chemical)
        if method:
            parts.append(method)
        if reference:
            reference_text = f"ref. {reference}"
            if reference_id:
                reference_text += f" ({reference_id})"
            parts.append(reference_text)
        return " · ".join(parts) or "Serie sin identificar"

    def build_compact_label(row: pd.Series) -> str:
        obs = _clean_label_value(row.get("obs_id"))
        if obs.endswith(".0"):
            obs = obs[:-2]
        species = _clean_label_value(row.get("name"))
        chemical = _clean_label_value(row.get("chemical_name"))
        method = _clean_label_value(row.get("Método"))
        reference_id = _clean_label_value(row.get("ID de referencia"))

        parts = []
        if obs:
            parts.append(obs)
        parts.append(species or chemical or "especie sin nombre")
        if method:
            method_label = method
            if method == "MTH" and reference_id:
                method_label += f" r{reference_id}"
            parts.append(method_label)
        return " · ".join(parts)

    prepared["__czspec_series__"] = prepared.apply(build_label, axis=1)
    prepared["__czspec_series_label__"] = prepared.apply(build_compact_label, axis=1)
    return prepared


def numeric_series(series: pd.Series) -> pd.Series:
    """Convierte valores científicos de tabla a números sin alterar el origen."""

    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace("−", "-", regex=False)
        .str.replace(",", "", regex=False)
        .replace({"": np.nan, "nan": np.nan, "None": np.nan, "—": np.nan})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def numeric_columns(frame: pd.DataFrame) -> list[str]:
    columns = []
    for column in frame.columns:
        values = numeric_series(frame[column])
        if values.notna().any():
            columns.append(str(column))
    return columns


SCIENTIFIC_AXIS_COLUMNS = (
    "ν_obs_MHz", "orderedfreq", "Δν_MHz", "eu_k", "lower_state_energy_K",
    "aij", "upperStateDegen", "T_A [K]", "Δv [Km/s]", "IntInt [K*Km/s]",
    "Tex [K]", "Tex_K", "T_ex [K]", "N_total [cm^-2]", "Q(T)", "τ",
)


def plot_axis_columns(frame: pd.DataFrame, advanced: bool = False) -> list[str]:
    """Devuelve ejes científicos claros; los campos internos quedan bajo demanda."""

    numeric = numeric_columns(frame)
    if advanced:
        return numeric
    return [column for column in SCIENTIFIC_AXIS_COLUMNS if column in numeric]


def uncertainty_column(frame: pd.DataFrame, value_column: str) -> str | None:
    """Localiza la incertidumbre asociada a una magnitud científica."""

    explicit = {
        "Δv [Km/s]": "σ_Δv [Km/s]",
        "IntInt [K*Km/s]": "σ_IntInt [K*Km/s]",
        "N_total [cm^-2]": "σ_N_total [cm^-2]",
    }
    candidates = (
        explicit.get(value_column),
        f"σ_{value_column}",
        f"sigma_{value_column}",
        f"{value_column}_err",
        f"{value_column}_error",
    )
    for candidate in candidates:
        if candidate and candidate in frame.columns:
            values = numeric_series(frame[candidate])
            if values.notna().any():
                return str(candidate)
    return None


def _temperature_from_suffix(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def partition_long(frame: pd.DataFrame) -> pd.DataFrame:
    """Convierte columnas Q_10K, Q_28K… a Q(T) contra T_ex."""

    if frame is None or frame.empty:
        return pd.DataFrame()
    q_columns = []
    for column in frame.columns:
        match = re.fullmatch(r"Q_([0-9]+(?:[._][0-9]+)?)K", str(column))
        if match:
            q_columns.append((column, float(match.group(1).replace("_", "."))))
    rows = []
    identity_columns = [column for column in frame.columns if column not in {item[0] for item in q_columns}]
    for _, source in frame.iterrows():
        identity = {column: source.get(column) for column in identity_columns}
        for column, temperature in q_columns:
            value = numeric_series(pd.Series([source.get(column)])).iloc[0]
            if pd.isna(value):
                continue
            rows.append({**identity, "T_ex [K]": temperature, "Q(T)": float(value)})
    return pd.DataFrame(rows)


def mod_density_long(frame: pd.DataFrame) -> pd.DataFrame:
    """Normaliza el resultado MOD para estudiar N_total(T_ex)."""

    if frame is None or frame.empty:
        return pd.DataFrame()
    density_columns = []
    for column in frame.columns:
        match = re.fullmatch(r"N_tot_([0-9]+(?:\.[0-9]+)?)K_cm2", str(column))
        if match:
            density_columns.append((column, match.group(1)))
    excluded = {
        column
        for column in frame.columns
        if str(column).startswith("N_tot_")
    }
    identity_columns = [column for column in frame.columns if column not in excluded]
    rows = []
    for _, source in frame.iterrows():
        identity = {column: source.get(column) for column in identity_columns}
        for density_column, temperature_text in density_columns:
            density = numeric_series(pd.Series([source.get(density_column)])).iloc[0]
            if pd.isna(density):
                continue
            error_column = f"N_tot_{temperature_text}K_err_cm2"
            error = numeric_series(pd.Series([source.get(error_column)])).iloc[0]
            rows.append(
                {
                    **identity,
                    "Método": "MOD",
                    "T_ex [K]": float(temperature_text),
                    "N_total [cm^-2]": float(density),
                    "σ_N_total [cm^-2]": np.nan if pd.isna(error) else float(error),
                }
            )
    return pd.DataFrame(rows)


def mth_density_long(frame: pd.DataFrame) -> pd.DataFrame:
    """Normaliza la tabla ancha MTH, una fila por solución y referencia."""

    if frame is None or frame.empty:
        return pd.DataFrame()
    density_columns = []
    for column in frame.columns:
        match = re.fullmatch(r"N_(\d+)_cm2", str(column))
        if match:
            density_columns.append((column, match.group(1)))
    excluded = {
        column
        for column in frame.columns
        if re.fullmatch(r"(?:N|sigma_N|tau)_\d+(?:_cm2)?", str(column))
        or re.fullmatch(r"ref_\d+_(?:name|line)", str(column))
    }
    identity_columns = [column for column in frame.columns if column not in excluded]
    tex_column = next(
        (column for column in ("Tex [K]", "Tex_K", "T_ex [K]") if column in frame.columns),
        None,
    )
    rows = []
    for _, source in frame.iterrows():
        identity = {column: source.get(column) for column in identity_columns}
        tex = numeric_series(pd.Series([source.get(tex_column)])).iloc[0] if tex_column else np.nan
        for density_column, suffix in density_columns:
            density = numeric_series(pd.Series([source.get(density_column)])).iloc[0]
            if pd.isna(density):
                continue
            error = numeric_series(pd.Series([source.get(f"sigma_N_{suffix}_cm2")])).iloc[0]
            tau = numeric_series(pd.Series([source.get(f"tau_{suffix}")])).iloc[0]
            rows.append(
                {
                    **identity,
                    "Método": "MTH",
                    "T_ex [K]": np.nan if pd.isna(tex) else float(tex),
                    "N_total [cm^-2]": float(density),
                    "σ_N_total [cm^-2]": np.nan if pd.isna(error) else float(error),
                    "τ": np.nan if pd.isna(tau) else float(tau),
                    "Referencia": source.get(f"ref_{suffix}_name", ""),
                    "ID de referencia": suffix,
                }
            )
    return pd.DataFrame(rows)
