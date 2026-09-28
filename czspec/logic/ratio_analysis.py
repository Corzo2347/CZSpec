"""Herramientas científicas para el módulo 5 de CZSpec.

El módulo trabaja exclusivamente con densidades columnares ya calculadas en
el módulo 3.  No interpreta una razón de columnas como abundancia absoluta y
no mezcla, de manera silenciosa, resultados MOD y MTH.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import re
from typing import Iterable

import numpy as np
import pandas as pd


_MOD_N_RE = re.compile(r"^N_tot_([0-9]+(?:\.[0-9]+)?)K_cm2$")
_MTH_N_RE = re.compile(r"^N_(\d+)_cm2$")


def _number(value) -> float:
    """Convierte números de tablas/CSV sin confundir coma decimal y millares."""

    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return math.nan
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "--"}:
        return math.nan
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")
    try:
        return float(text)
    except (TypeError, ValueError):
        return math.nan


def _text(value, fallback: str = "") -> str:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return fallback
    text = str(value).strip()
    return text or fallback


def _first(row: pd.Series, *names: str, fallback=""):
    for name in names:
        if name in row.index:
            value = row.get(name)
            if _text(value):
                return value
    return fallback


@dataclass(frozen=True)
class ColumnDensityRecord:
    method: str
    dataset: str
    obs_id: str
    species: str
    chemical_name: str
    tex_k: float
    column_density_cm2: float
    uncertainty_cm2: float = math.nan
    catalog: str = ""
    transition: str = ""
    frequency_mhz: float = math.nan
    reference: str = ""
    tau: float = math.nan

    @property
    def series_key(self) -> str:
        bits = [self.method, self.dataset, self.obs_id, self.species, self.catalog]
        if self.reference:
            bits.append(self.reference)
        return "|".join(str(item).strip() for item in bits)

    @property
    def label(self) -> str:
        obs = f"obs {self.obs_id} · " if self.obs_id else ""
        ref = f" · ref. {self.reference}" if self.reference else ""
        catalog = f" [{self.catalog}]" if self.catalog else ""
        return f"{obs}{self.species}{catalog} · {self.method}{ref}"


@dataclass(frozen=True)
class RatioResult:
    dataset: str
    method: str
    tex_k: float
    numerator_label: str
    denominator_label: str
    numerator_cm2: float
    numerator_uncertainty_cm2: float
    denominator_cm2: float
    denominator_uncertainty_cm2: float
    ratio: float
    uncertainty: float
    status: str = "válida"

    def as_dict(self) -> dict:
        return asdict(self)


def extract_mod_records(
    dataframe: pd.DataFrame | None,
    *,
    dataset: str = "sesión",
) -> list[ColumnDensityRecord]:
    if dataframe is None or dataframe.empty:
        return []

    density_columns: list[tuple[str, float]] = []
    for column in dataframe.columns:
        match = _MOD_N_RE.match(str(column))
        if match:
            density_columns.append((str(column), float(match.group(1))))

    records: list[ColumnDensityRecord] = []
    for _, row in dataframe.iterrows():
        species = _text(_first(row, "name", "species_label"), "Especie sin nombre")
        chemical = _text(_first(row, "chemical_name"))
        obs_id = _text(_first(row, "obs_id", "Line"))
        catalog = _text(_first(row, "linelist", "Source"))
        transition = _text(_first(row, "transition", "orderedfreq"))
        frequency = _number(_first(row, "ν_obs_MHz", "orderedfreq", fallback=math.nan))

        for density_column, tex_k in density_columns:
            density = _number(row.get(density_column))
            if not math.isfinite(density) or density <= 0:
                continue
            error_column = density_column.replace("_cm2", "_err_cm2")
            records.append(
                ColumnDensityRecord(
                    method="MOD",
                    dataset=dataset,
                    obs_id=obs_id,
                    species=species,
                    chemical_name=chemical,
                    tex_k=tex_k,
                    column_density_cm2=density,
                    uncertainty_cm2=_number(row.get(error_column)),
                    catalog=catalog,
                    transition=transition,
                    frequency_mhz=frequency,
                )
            )
    return records


def extract_mth_records(
    dataframe: pd.DataFrame | None,
    *,
    dataset: str = "sesión",
) -> list[ColumnDensityRecord]:
    if dataframe is None or dataframe.empty:
        return []

    records: list[ColumnDensityRecord] = []
    # Formato largo conservado por el motor científico.
    if {"N_cm2", "Tex_K"}.issubset(dataframe.columns):
        for _, row in dataframe.iterrows():
            density = _number(row.get("N_cm2"))
            tex_k = _number(row.get("Tex_K"))
            if not (math.isfinite(density) and density > 0 and math.isfinite(tex_k)):
                continue
            records.append(
                ColumnDensityRecord(
                    method="MTH",
                    dataset=dataset,
                    obs_id=_text(_first(row, "target_obs_id", "obs_id")),
                    species=_text(_first(row, "target_name", "species_label", "name"), "Especie sin nombre"),
                    chemical_name=_text(_first(row, "chemical_name", "target_chemical_name")),
                    tex_k=tex_k,
                    column_density_cm2=density,
                    uncertainty_cm2=_number(row.get("N_err_cm2")),
                    catalog=_text(_first(row, "target_Source", "Source", "target_linelist")),
                    transition=_text(_first(row, "target_line_id")),
                    frequency_mhz=_number(_first(row, "nu_target_MHz", "target_ν_obs_MHz", fallback=math.nan)),
                    reference=_text(_first(row, "ref_name", "ref_line_id")),
                    tau=_number(row.get("tau_target")),
                )
            )
        return records

    # Formato ancho presentado en M3: una solución por referencia válida.
    n_columns: list[tuple[str, int]] = []
    for column in dataframe.columns:
        match = _MTH_N_RE.match(str(column))
        if match:
            n_columns.append((str(column), int(match.group(1))))

    for _, row in dataframe.iterrows():
        tex_k = _number(_first(row, "Tex [K]", "Tex_K", fallback=math.nan))
        if not math.isfinite(tex_k):
            continue
        for density_column, ref_index in n_columns:
            density = _number(row.get(density_column))
            if not math.isfinite(density) or density <= 0:
                continue
            records.append(
                ColumnDensityRecord(
                    method="MTH",
                    dataset=dataset,
                    obs_id=_text(_first(row, "obs_id", "Line")),
                    species=_text(_first(row, "name", "species_label"), "Especie sin nombre"),
                    chemical_name=_text(_first(row, "chemical_name")),
                    tex_k=tex_k,
                    column_density_cm2=density,
                    uncertainty_cm2=_number(row.get(f"sigma_N_{ref_index}_cm2")),
                    catalog=_text(_first(row, "Source", "linelist")),
                    transition=_text(_first(row, "ν_obs_MHz")),
                    frequency_mhz=_number(_first(row, "ν_obs_MHz", fallback=math.nan)),
                    reference=_text(row.get(f"ref_{ref_index}_name"), f"referencia {ref_index}"),
                    tau=_number(row.get(f"tau_{ref_index}")),
                )
            )
    return records


def extract_column_density_records(
    mod_dataframe: pd.DataFrame | None,
    mth_dataframe: pd.DataFrame | None,
    *,
    dataset: str = "sesión",
) -> list[ColumnDensityRecord]:
    return extract_mod_records(mod_dataframe, dataset=dataset) + extract_mth_records(
        mth_dataframe, dataset=dataset
    )


def unique_series(records: Iterable[ColumnDensityRecord]) -> dict[str, ColumnDensityRecord]:
    result: dict[str, ColumnDensityRecord] = {}
    for record in records:
        result.setdefault(record.series_key, record)
    return dict(sorted(result.items(), key=lambda item: item[1].label.casefold()))


def _validate_pair(numerator: ColumnDensityRecord, denominator: ColumnDensityRecord) -> None:
    if numerator.method != denominator.method:
        raise ValueError("No se pueden mezclar densidades MOD y MTH en una misma razón.")
    if numerator.dataset and denominator.dataset and numerator.dataset != denominator.dataset:
        raise ValueError("Las dos densidades deben proceder de la misma fuente o sesión.")
    if not math.isclose(numerator.tex_k, denominator.tex_k, rel_tol=0.0, abs_tol=1e-8):
        raise ValueError("Numerador y denominador deben compartir la misma T_ex.")
    for value in (numerator.column_density_cm2, denominator.column_density_cm2):
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Las densidades columnares deben ser positivas y finitas.")


def calculate_ratio(
    numerator: ColumnDensityRecord,
    denominator: ColumnDensityRecord,
) -> RatioResult:
    _validate_pair(numerator, denominator)
    ratio = numerator.column_density_cm2 / denominator.column_density_cm2
    numerator_error = numerator.uncertainty_cm2
    denominator_error = denominator.uncertainty_cm2
    uncertainty = math.nan
    status = "válida"
    if all(
        math.isfinite(value) and value >= 0
        for value in (numerator_error, denominator_error)
    ):
        uncertainty = ratio * math.sqrt(
            (numerator_error / numerator.column_density_cm2) ** 2
            + (denominator_error / denominator.column_density_cm2) ** 2
        )
    else:
        status = "sin incertidumbre completa"

    frequencies = (numerator.frequency_mhz, denominator.frequency_mhz)
    if all(math.isfinite(value) and value > 0 for value in frequencies):
        # En el contexto IRAM 30 m de la tesis, 3 mm y 2 mm no comparten haz
        # (aprox. 29 y 17 arcsec). La razón sigue siendo calculable, pero debe
        # quedar marcada para que no se interprete como comparación espacial
        # homogénea sin una convolución previa.
        bands = {"3 mm" if value < 110_000.0 else "2 mm" for value in frequencies}
        if len(bands) > 1:
            beam_note = "advertencia: haces 3 mm/2 mm distintos"
            status = f"{status}; {beam_note}" if status != "válida" else beam_note

    return RatioResult(
        dataset=numerator.dataset,
        method=numerator.method,
        tex_k=numerator.tex_k,
        numerator_label=numerator.label,
        denominator_label=denominator.label,
        numerator_cm2=numerator.column_density_cm2,
        numerator_uncertainty_cm2=numerator_error,
        denominator_cm2=denominator.column_density_cm2,
        denominator_uncertainty_cm2=denominator_error,
        ratio=ratio,
        uncertainty=uncertainty,
        status=status,
    )


def calculate_ratio_series(
    records: Iterable[ColumnDensityRecord],
    numerator_key: str,
    denominator_key: str,
) -> list[RatioResult]:
    numerator = {record.tex_k: record for record in records if record.series_key == numerator_key}
    denominator = {record.tex_k: record for record in records if record.series_key == denominator_key}
    common_temperatures = sorted(set(numerator).intersection(denominator))
    if not common_temperatures:
        raise ValueError("Las dos series no comparten temperaturas de excitación.")
    return [calculate_ratio(numerator[tex], denominator[tex]) for tex in common_temperatures]


def results_dataframe(results: Iterable[RatioResult]) -> pd.DataFrame:
    rows = [result.as_dict() for result in results]
    return pd.DataFrame(
        rows,
        columns=[
            "dataset",
            "method",
            "tex_k",
            "numerator_label",
            "denominator_label",
            "numerator_cm2",
            "numerator_uncertainty_cm2",
            "denominator_cm2",
            "denominator_uncertainty_cm2",
            "ratio",
            "uncertainty",
            "status",
        ],
    )
