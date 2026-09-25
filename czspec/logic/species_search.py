from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import html
import math
import os
import re
import traceback

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from astropy import units as u
from astroquery.splatalogue import Splatalogue

from czspec.network import require_online

from czspec.paths import (
    CDMS_ABC_PATH,
    CDMS_PARTITION_PATH,
    JPL_ABC_PATH,
    JPL_PARTITION_PATH,
    SPECIES_SEARCH_OUTPUT_DIR,
)


@dataclass
class SpeciesSearchPolicy:
    """Transparent, user-editable priors for candidate selection in M2.

    The default profile is deliberately conservative for generic star-forming
    regions: it is preferable to report no plausible candidate than to force an
    exotic molecule through the emergency branch. Hot-core/COM studies can
    explicitly relax these switches from the M2 filter dialog.
    """

    profile: str = "star_forming"
    eu_max_k: float = 120.0
    emergency_eu_max_k: float = 180.0
    strict_family_mode: bool = True
    forbid_halogens: bool = True
    disallow_vib_excited: bool = True
    allow_complex_organics: bool = False
    allow_emergency_outside_family: bool = False
    heavy_atoms_strict_max: int = 4
    soft_heavy_max: int = 5
    rescue_widen_factor: float = 1.8
    emergency_widen_factor: float = 4.0
    query_workers: int = 3
    weight_frequency: float = 0.75
    weight_eu: float = 0.15
    weight_loga: float = 0.10
    complexity_weight: float = 1.0

    @classmethod
    def from_mapping(cls, values: dict[str, Any] | None):
        if not values:
            return cls()
        allowed = cls.__dataclass_fields__
        clean = {key: value for key, value in dict(values).items() if key in allowed}
        policy = cls(**clean)
        policy.profile = str(policy.profile or "star_forming").strip().lower()
        if policy.profile not in {"star_forming", "balanced", "open"}:
            policy.profile = "star_forming"
        policy.eu_max_k = max(1.0, float(policy.eu_max_k))
        policy.emergency_eu_max_k = max(policy.eu_max_k, float(policy.emergency_eu_max_k))
        policy.heavy_atoms_strict_max = max(1, int(policy.heavy_atoms_strict_max))
        policy.soft_heavy_max = max(policy.heavy_atoms_strict_max, int(policy.soft_heavy_max))
        policy.rescue_widen_factor = max(1.0, float(policy.rescue_widen_factor))
        policy.emergency_widen_factor = max(policy.rescue_widen_factor, float(policy.emergency_widen_factor))
        policy.query_workers = max(1, min(6, int(policy.query_workers)))
        return policy

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass
class SpeciesSearchConfig:
    csv_input: str
    output_name: str
    target_temperatures: list[float] = field(default_factory=list)
    topk: int = 5
    compute_q_values: bool = True
    generate_qt_plots: bool = False
    generate_plotly: bool = False
    search_policy: dict[str, Any] | None = None


@dataclass
class SpeciesSearchResult:
    success: bool
    message: str
    logs: list[str] = field(default_factory=list)

    # Resultados principales
    main_dataframe: Any = None
    topk_dataframe: Any = None

    # Archivos generados
    main_csv_path: str | None = None
    main_html_path: str | None = None
    topk_csv_path: str | None = None
    topk_html_path: str | None = None

    # Carpetas / recursos extra
    plotly_dir: str | None = None
    qt_dir: str | None = None

    # Extras por si luego los ocupamos
    extra: dict[str, Any] = field(default_factory=dict)


# ================== CONFIGURACIÓN BASE ==================
CDMS_T_GRID = [1000.0, 500.0, 300.0, 225.0, 150.0, 75.0, 37.5, 18.75, 9.375, 5.0, 2.725]
CDMS_PATH = CDMS_PARTITION_PATH
JPL_TABLE_PATH = JPL_PARTITION_PATH

BACKEND = "FTS_narrow"
CHAN_WIDTH = {"FTS_narrow": 0.05, "FTS_wide": 0.20, "WILMA": 2.00, "VESPA": 0.078}
CAT_MARGIN_MHZ = 0.05
FALLBACK_DELTA_V_KMS = 4.0
EU_MAX_K = 50

EMERGENCY_WIDEN_FACTOR = 10.0
EMERGENCY_EU_MAX_K = 120
EMERGENCY_TOPN = 1

REGION_PRIOR = "SIMPLE"
STRICT_FAMILY_MODE = True
FORBID_HALOGENS = True
DISALLOW_VIB_EXCITED = True

ALLOWED_ELEMENTS = {"H", "C", "N", "O", "S", "Si"}
HEAVY_ELEMENTS = {"Cl", "Br", "F", "I", "P", "Na", "K", "Mg", "Fe", "Al", "Ca", "Cu", "Zn", "Ti", "V", "Cr", "Mn"}

HEAVY_ATOMS_STRICT_MAX = 4
SOFT_HEAVY_MAX = 5

W_FREQ = 0.75
W_EU = 0.15
W_LOGA = 0.10
COMPLEXITY_PENALTY_WEIGHT = 1.0

HALOGEN_PENALTY = 10.0
VIB_EXCITED_PENALTY = 12.0
ORGANIC_COMPLEX_PENALTY = 6.0
FAMILY_MISMATCH_PENALTY = 5.0
AROMATIC_EXTRA_PENALTY = 8.0
MULTI_CN_EXTRA_PENALTY = 6.0

WHITELIST_BONUS = 4.0
BLACKLIST_PENALTY = 12.0

BASE_WHITELIST_GOOD = {
    # Dense-gas and classical tracers
    "NH3", "NH2D", "HCN", "HC15N", "H13CN", "HNC", "HN13C",
    "CN", "CCH", "C2H", "N2H+", "HCO+", "H13CO+", "HC18O+",
    "HCO", "HNCO", "H2CO", "H213CO", "H2CS", "HCS+",
    # Carbon monoxide and sulphur-bearing gas
    "CO", "13CO", "C18O", "C17O", "CS", "13CS", "C34S", "C33S",
    "CCS", "CCCS", "C3S", "SO", "SO2", "34SO", "34SO2", "OCS", "H2S",
    # Shocks / silicon and common warm-gas species
    "SiO", "29SiO", "30SiO", "SiS", "NO", "NS", "CH3OH",
    # Small carbon-chain / hot-core tracers that remain chemically plausible
    "HC3N", "HCCCN", "CH3CN", "CH3CCH", "cC3H2", "CCCH2",
}


BLACKLIST_BAD = {
    "CH2(OH)CDO", "gG'a-CH3CHOHCH2OH", "Z-HNCHCN", "C3H6O2",
    "OC(CN)2", "Carbonyl cyanide",
    "ANISOLE", "c-C6H5COCH3",
    "Glycerol", "Hydroxyacetone", "2-Cyanobutane",
    "Vinyl Cyanide", "Propyl Cyanide", "Butyl Cyanide",
    "3-Methylbutyronitrile", "cyclo-Propyl cyanide", "Acetone", "Glycolaldehyde"
}

RESCUE_BASE_FAMILIES = {
    "HCN", "H13CN", "HC15N", "HNC", "HN13C", "HCO+", "H13CO+", "HC18O+",
    "HCO", "HNCO", "H2CO", "H2CS", "CO", "13CO", "C18O", "C17O",
    "CN", "CCH", "C2H", "N2H+", "SO", "SO2", "OCS", "H2S", "SiO", "NO", "NS",
    "CS", "C34S", "C33S", "CCS", "CCCS", "C3S", "NH2D", "CH3OH", "HC3N", "CH3CN"
}

RESCUE_WIDEN_FACTOR = 1.8
TOPK_DEFAULT = 5
COL_FREQ = "ν[MHz]"

TAG_RE = re.compile(r"<[^>]+>")
AROMATIC_PAT = re.compile(r"(?:\bc-?C6H5|\bphenyl|\bbenz|anisole)", re.I)

def ensure_dir(path: Path | str) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_name(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"[^\w.-]+", "_", value)
    value = value.strip("._-")
    return value or "resultados"

def qcol_name(T: float) -> str:
    s = f"{float(T)}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return f"Q_{s.replace('.', '_')}K"


def strip_html(s):
    return TAG_RE.sub("", str(s)) if s is not None else s


def delta_nu_MHz(nu_MHz: float, dv_kms: float | None) -> float:
    dv = dv_kms if (dv_kms is not None and dv_kms > 0) else FALLBACK_DELTA_V_KMS
    doppler = nu_MHz * dv / 299_792.458
    return math.sqrt(CHAN_WIDTH[BACKEND] ** 2 + doppler ** 2) + CAT_MARGIN_MHZ


def strip_isotope_prefixes(formula: str) -> str:
    if not isinstance(formula, str):
        return ""
    s = html.unescape(strip_html(formula)).strip()
    s = re.sub(r"\bv\d*\s*=\s*\d+\b", "", s, flags=re.I)
    s = re.sub(r"([A-Za-z])\d+(?=[ΣΔΠΛ])", r"\1", s)
    s = re.sub(r"[ΣΔΠΛ]", "", s)
    s = re.sub(r"^(?:[lcgt]-|\b(?:cis|trans)\b-?)", "", s, flags=re.I)
    s = s.replace(" ", "").replace("–", "").replace("—", "").replace("-", "")
    s = re.sub(r"(?<![A-Za-z])\d+(?=[A-Z])", "", s)
    s = s.replace("+", "")
    return s


def parse_formula_atoms(formula: str):
    if not formula:
        return {}

    s = strip_isotope_prefixes(formula)
    i, n = 0, len(s)
    stack = [dict()]

    def read_int(j):
        k = j
        while k < n and s[k].isdigit():
            k += 1
        return (int(s[j:k]) if k > j else 1, k)

    while i < n:
        ch = s[i]
        if ch == "(":
            stack.append(dict())
            i += 1
        elif ch == ")":
            i += 1
            mult, i = read_int(i)
            grp = stack.pop() if len(stack) > 1 else {}
            for el, cnt in grp.items():
                stack[-1][el] = stack[-1].get(el, 0) + cnt * mult
        elif ch.isupper():
            el = ch
            i += 1
            if i < n and s[i].islower():
                el += s[i]
                i += 1
            num, i = read_int(i)
            stack[-1][el] = stack[-1].get(el, 0) + num
        else:
            i += 1

    atoms = {}
    for level in stack:
        for el, cnt in level.items():
            atoms[el] = atoms.get(el, 0) + cnt
    return atoms


def base_species_key(chem_name: str, formula: str) -> str:
    form = strip_isotope_prefixes(formula or "")
    if parse_formula_atoms(form):
        return form
    name = strip_html(chem_name or "")
    name = re.sub(r"\bv\d*\s*=\s*\d+\b", "", name, flags=re.I)
    return re.sub(r"\s+", " ", name).strip()


def has_halogen(name_or_formula: str) -> bool:
    s = (name_or_formula or "").lower()
    if re.search(r"\b(chloro|chlorine|fluoro|fluorine|bromo|bromine|iodo|iodine)\b", s):
        return True
    if re.search(r"\bcl\b|\bbr\b|\bf\b|\bi\b", s):
        return True
    atoms = parse_formula_atoms(name_or_formula)
    return any(e in atoms for e in ("Cl", "Br", "F", "I"))


def is_vibrationally_excited(name_or_formula: str) -> bool:
    s = (name_or_formula or "").lower()
    m = re.search(r"\bv\d*\s*=\s*([0-9]+)", s)
    return bool(m and m.group(1) != "0")


def count_CN_groups(text: str) -> int:
    s = strip_isotope_prefixes(text or "")
    return len(re.findall(r"CN", s))


def is_blacklisted(name: str, formula: str) -> bool:
    nm = strip_html(name or "").strip().upper()
    fm = strip_html(formula or "").strip().upper()
    return any(nm == bad.upper() or fm == bad.upper() for bad in BLACKLIST_BAD)


def is_base_whitelisted(chem_name: str, formula: str) -> bool:
    base = base_species_key(chem_name, formula)
    base = re.sub(r"\s+", "", base).upper().replace("V=0", "")
    return any(base == ref.upper() for ref in BASE_WHITELIST_GOOD)


def in_rescue_family(chem_name: str, formula: str) -> bool:
    base = base_species_key(chem_name, formula)
    base = re.sub(r"\s+", "", base).upper().replace("V=0", "")
    if base in RESCUE_BASE_FAMILIES:
        return True
    if base.replace("+", "") in {b.replace("+", "") for b in RESCUE_BASE_FAMILIES}:
        return True
    return False


_COMPLEX_ORGANIC_NAME_PAT = re.compile(
    r"acetic|acid|glycol|glycer|butatrien|butyl|propyl|anisole|aldehyde|ketone|"
    r"acetone|acetate|formate|ether|ethanol|methoxy|carbamate|peroxide|amide",
    re.I,
)


def is_complex_organic_candidate(chem_name: str, formula: str) -> bool:
    """Conservative COM flag used only by the default M2 prior.

    It does not claim that a species is astrophysically impossible.  It marks
    candidates that should not be *forced* into a generic star-forming-region
    identification unless the user explicitly enables complex organics.
    """
    name = strip_html(chem_name or "")
    form = strip_isotope_prefixes(formula or "")
    if _COMPLEX_ORGANIC_NAME_PAT.search(name) or _COMPLEX_ORGANIC_NAME_PAT.search(form):
        return True
    atoms = parse_formula_atoms(form)
    carbon = int(atoms.get("C", 0))
    oxygen = int(atoms.get("O", 0))
    nitrogen = int(atoms.get("N", 0))
    heavy = sum(v for k, v in atoms.items() if k != "H")
    # Typical COM-like composition.  Known compact tracers are rescued by the
    # whitelist before this flag becomes a hard rejection.
    if carbon >= 2 and oxygen >= 2 and heavy >= 4:
        return True
    if carbon >= 4 and heavy >= 4:
        return True
    if carbon >= 3 and nitrogen >= 2 and heavy >= 5:
        return True
    return False


def allowed_by_family(chem_name: str, formula: str, policy: SpeciesSearchPolicy | None = None) -> bool:
    policy = policy or SpeciesSearchPolicy()
    if policy.profile == "open" or not policy.strict_family_mode:
        return True

    base = base_species_key(chem_name, formula)
    base = re.sub(r"\s+", "", base).upper().replace("V=0", "")
    base_no_plus = base.replace("+", "")
    fam = {re.sub(r"[- ]", "", b.upper()).replace("+", "") for b in BASE_WHITELIST_GOOD}
    normalized = re.sub(r"[- ]", "", base_no_plus)
    if normalized in fam:
        return True

    atoms = parse_formula_atoms(formula or base)
    if not atoms:
        return policy.profile == "balanced"
    if any(element not in ALLOWED_ELEMENTS for element in atoms):
        return False
    heavy = sum(v for k, v in atoms.items() if k != "H")
    carbon = int(atoms.get("C", 0))

    if is_complex_organic_candidate(chem_name, formula) and not policy.allow_complex_organics:
        return False

    if policy.profile == "balanced":
        return heavy <= policy.soft_heavy_max

    # Generic star-forming regions: admit small simple molecules even if they
    # are absent from the explicit tracer list, but require C4+ candidates to
    # be explicitly whitelisted.
    if carbon >= 4:
        return False
    return heavy <= policy.heavy_atoms_strict_max


def molecular_complexity(chem_name: str, formula: str):
    base_form = strip_isotope_prefixes(formula or "")
    atoms = parse_formula_atoms(base_form)
    Hc = int(atoms.get("H", 0))
    heavy = {k: v for k, v in atoms.items() if k != "H"}
    heavy_n = sum(heavy.values())

    score = float(heavy_n)

    for e in heavy:
        if e not in ALLOWED_ELEMENTS:
            score += 2.0
        if e in HEAVY_ELEMENTS:
            score += 6.0

    nm = (chem_name or "").strip()
    if re.search(
        r"methoxy|amide|peroxide|carbamate|acetate|acetic|acid|formate|glycol|glycer|butatrien|butyl|propyl|anisole|aldehyde|ketone|acetone|ether|ethanol",
        nm,
        flags=re.I
    ):
        score += ORGANIC_COMPLEX_PENALTY

    if AROMATIC_PAT.search(nm) or AROMATIC_PAT.search(base_form):
        score += 12.0

    if max(count_CN_groups(nm), count_CN_groups(base_form)) >= 2:
        score += 10.0

    if has_halogen(nm) or has_halogen(base_form):
        score += HALOGEN_PENALTY

    if is_vibrationally_excited(nm) or is_vibrationally_excited(base_form):
        score += VIB_EXCITED_PENALTY

    return score, heavy_n, Hc, base_form


def round_dataframe_for_gui(df: pd.DataFrame, ndigits: int = 4) -> pd.DataFrame:
    """Return an independent frame without altering scientific precision.

    Older alphas rounded every numeric column to four decimals here.  That was
    destructive: values transferred from M1 (for example peak temperature and
    fitted frequency) no longer matched their source values.  Formatting now
    belongs to the GUI/export layer only.
    """
    if df is None:
        return df
    return df.copy()

def normalize_splatalogue_table(tab, obs_id: int, nu_MHz: float, delta_nu_mhz: float, source_row: pd.Series, *, policy: SpeciesSearchPolicy | None = None, energy_max_k: float | None = None) -> pd.DataFrame:
    """
    Convierte la tabla de Splatalogue a DataFrame de pandas y agrega
    metadatos de la observación original.
    """
    if tab is None or len(tab) == 0:
        return pd.DataFrame()

    policy = policy or SpeciesSearchPolicy()
    df_tab = tab.to_pandas()

    for col in ("name", "chemical_name", "species"):
        if col in df_tab.columns:
            df_tab[col] = df_tab[col].astype(str).map(strip_html)

    if "eu_k" in df_tab.columns:
        df_tab["eu_k"] = pd.to_numeric(df_tab["eu_k"], errors="coerce")
        eu_limit = float(energy_max_k if energy_max_k is not None else policy.eu_max_k)
        df_tab = df_tab[df_tab["eu_k"].isna() | (df_tab["eu_k"] <= eu_limit)].copy()

    if df_tab.empty:
        return pd.DataFrame()

    df_tab["obs_id"] = obs_id
    df_tab["ν_obs_MHz"] = float(nu_MHz)
    df_tab["Δν_MHz"] = float(delta_nu_mhz)

    if "orderedfreq" in df_tab.columns:
        df_tab["orderedfreq"] = pd.to_numeric(df_tab["orderedfreq"], errors="coerce")
        df_tab["freq_diff_MHz"] = (df_tab["orderedfreq"] - float(nu_MHz)).abs()
    else:
        df_tab["freq_diff_MHz"] = np.nan

        # Copiar metadatos y columnas observacionales desde el CSV original
    passthrough_cols = [
        "Line",
        "Source",
        "Grupo",
        "T_A [K]",
        "T_obs_at_fit [K]",
        "Δv [Km/s]",
        "σ_Δv [Km/s]",
        "IntInt [K*Km/s]",
        "σ_IntInt [K*Km/s]",
        "Ajuste",
        "GOI",
        "VLSR [km/s]",
        "source_vlsr_kms",
        "source_path",
        "detection_id",
        "Semilla_ν[MHz]",
    ]

    for col in passthrough_cols:
        if col in source_row.index:
            df_tab[col] = source_row[col]


    form_col = "name" if "name" in df_tab.columns else None
    chem_col = "chemical_name" if "chemical_name" in df_tab.columns else form_col

    complexity_score_vals = []
    heavy_atoms_vals = []
    h_count_vals = []
    base_formula_vals = []
    whitelisted_vals = []
    blacklisted_vals = []
    vib_vals = []
    halogen_vals = []
    family_vals = []
    complex_organic_vals = []

    for _, r in df_tab.iterrows():
        nm = str(r.get(chem_col, "") if chem_col else "")
        fm = str(r.get(form_col, "") if form_col else "")

        comp, heavy_n, h_count, base_formula = molecular_complexity(nm, fm)

        complexity_score_vals.append(comp)
        heavy_atoms_vals.append(heavy_n)
        h_count_vals.append(h_count)
        base_formula_vals.append(base_formula)
        whitelisted_vals.append(is_base_whitelisted(nm, fm))
        blacklisted_vals.append(is_blacklisted(nm, fm))
        vib_vals.append(is_vibrationally_excited(nm) or is_vibrationally_excited(fm))
        halogen_vals.append(has_halogen(nm) or has_halogen(fm))
        family_vals.append(allowed_by_family(nm, fm, policy))
        complex_organic_vals.append(is_complex_organic_candidate(nm, fm))

    df_tab["complexity_score"] = complexity_score_vals
    df_tab["heavy_atoms_count"] = heavy_atoms_vals
    df_tab["H_count"] = h_count_vals
    df_tab["base_formula"] = base_formula_vals
    df_tab["whitelisted"] = whitelisted_vals
    df_tab["blacklisted"] = blacklisted_vals
    df_tab["vib_excited"] = vib_vals
    df_tab["has_halogen"] = halogen_vals
    df_tab["allowed_family"] = family_vals
    df_tab["complex_organic"] = complex_organic_vals

    # Normalize source VLSR to one internal column when the input table carries
    # it under any of the common M1/user-header spellings.
    if "source_vlsr_kms" not in df_tab.columns:
        for alias in ("VLSR [km/s]", "VLSR[km/s]", "vlsr_kms", "VLSR", "v_lsr_kms"):
            if alias in source_row.index:
                value = pd.to_numeric(source_row.get(alias), errors="coerce")
                if pd.notna(value):
                    df_tab["source_vlsr_kms"] = float(value)
                    break

    return df_tab

def _score_common(row: pd.Series, policy: SpeciesSearchPolicy | None = None) -> tuple[float, float, float]:
    policy = policy or SpeciesSearchPolicy()
    freq_diff = abs(float(row.get("orderedfreq", np.nan) - row.get("ν_obs_MHz", np.nan)))
    denom = max(float(row.get("Δν_MHz", 0.0)), 1e-6)
    fpart = min(1.0, freq_diff / denom)

    eu_val = pd.to_numeric(row.get("eu_k", np.nan), errors="coerce")
    eupart = min(1.0, float(eu_val) / max(policy.eu_max_k, 1e-6)) if pd.notna(eu_val) else 0.0

    logapart = 0.5
    for a_col in ("loga", "logaij", "log10_Aij", "aij"):
        if a_col in row.index and pd.notna(row.get(a_col)):
            try:
                lg = float(row.get(a_col))
                logapart = 1.0 - np.clip((lg + 10.0) / 12.0, 0.0, 1.0)
                break
            except Exception:
                pass

    base = policy.weight_frequency * fpart + policy.weight_eu * eupart + policy.weight_loga * logapart
    bonus = WHITELIST_BONUS if bool(row.get("whitelisted", False)) else 0.0
    penalty = BLACKLIST_PENALTY if bool(row.get("blacklisted", False)) else 0.0
    return base, bonus, penalty


def candidate_score_strict(row: pd.Series, policy: SpeciesSearchPolicy | None = None) -> float:
    policy = policy or SpeciesSearchPolicy()
    base, bonus, penalty = _score_common(row, policy)

    if policy.forbid_halogens and bool(row.get("has_halogen", False)):
        return np.inf
    if policy.disallow_vib_excited and bool(row.get("vib_excited", False)) and not bool(row.get("whitelisted", False)):
        return np.inf
    if bool(row.get("complex_organic", False)) and not policy.allow_complex_organics and not bool(row.get("whitelisted", False)):
        return np.inf

    heavy_n = int(row.get("heavy_atoms_count", 0)) if pd.notna(row.get("heavy_atoms_count", np.nan)) else 0
    if heavy_n > policy.heavy_atoms_strict_max and not bool(row.get("whitelisted", False)):
        return np.inf
    if not bool(row.get("allowed_family", True)) and not bool(row.get("whitelisted", False)):
        return np.inf

    cpen = 0.10 * max(0, heavy_n - 2)
    return float(base + policy.complexity_weight * cpen + penalty - bonus)


def candidate_score_soft(row: pd.Series, policy: SpeciesSearchPolicy | None = None) -> float:
    policy = policy or SpeciesSearchPolicy()
    base, bonus, penalty = _score_common(row, policy)

    if policy.forbid_halogens and bool(row.get("has_halogen", False)):
        return np.inf
    if policy.disallow_vib_excited and bool(row.get("vib_excited", False)):
        return np.inf
    if bool(row.get("complex_organic", False)) and not policy.allow_complex_organics and not bool(row.get("whitelisted", False)):
        return np.inf

    heavy_n = int(row.get("heavy_atoms_count", 0)) if pd.notna(row.get("heavy_atoms_count", np.nan)) else 0
    if heavy_n > policy.soft_heavy_max and not bool(row.get("whitelisted", False)):
        return np.inf

    allowed = bool(row.get("allowed_family", True))
    if not allowed:
        if policy.profile == "star_forming" and heavy_n > 3 and not policy.allow_emergency_outside_family:
            return np.inf
        penalty += FAMILY_MISMATCH_PENALTY

    chem_name = str(row.get("chemical_name", "") or "")
    formula = str(row.get("name", "") or row.get("species", "") or "")
    if AROMATIC_PAT.search(chem_name) or AROMATIC_PAT.search(formula):
        penalty += AROMATIC_EXTRA_PENALTY
    if max(count_CN_groups(chem_name), count_CN_groups(formula)) >= 2:
        penalty += MULTI_CN_EXTRA_PENALTY

    cpen = 0.12 * max(0, heavy_n - 2) + 0.8
    return float(base + policy.complexity_weight * cpen + penalty - bonus)


def query_splatalogue_candidates(
    obs_id: int,
    nu_MHz: float,
    dv_obs: float | None,
    source_row: pd.Series,
    widen_factor: float = 1.0,
    energy_max_k: float | None = None,
    policy: SpeciesSearchPolicy | None = None,
) -> pd.DataFrame:
    require_online("Splatalogue molecular identification")
    policy = policy or SpeciesSearchPolicy()
    if energy_max_k is None:
        energy_max_k = policy.eu_max_k
    delta_nu_mhz = delta_nu_MHz(nu_MHz, dv_obs) * widen_factor
    freq_min = (nu_MHz - delta_nu_mhz) * u.MHz
    freq_max = (nu_MHz + delta_nu_mhz) * u.MHz

    tab = Splatalogue.query_lines(
        min_frequency=freq_min.to(u.GHz),
        max_frequency=freq_max.to(u.GHz),
        energy_max=energy_max_k,
        line_lists=["CDMS", "JPL"],
        show_qn_code=True,
        show_upper_degeneracy=True,
    )

    return normalize_splatalogue_table(
        tab=tab,
        obs_id=obs_id,
        nu_MHz=nu_MHz,
        delta_nu_mhz=delta_nu_mhz,
        source_row=source_row,
        policy=policy,
        energy_max_k=energy_max_k,
    )



C_KMS = 299_792.458

def add_kinematic_columns(frame: pd.DataFrame | None) -> pd.DataFrame:
    """Add line-specific radio velocity diagnostics once M2 knows ν_rest.

    A global velocity axis is not physically valid when every row can have a
    different rest frequency.  These columns therefore keep the comparison
    line-by-line: observed line velocity, source VLSR, expected observed
    frequency at that VLSR, and residual offsets.
    """
    if frame is None or frame.empty:
        return frame
    out = frame.copy()
    obs = pd.to_numeric(out.get("ν_obs_MHz"), errors="coerce")
    rest = pd.to_numeric(out.get("orderedfreq"), errors="coerce")
    valid = obs.notna() & rest.notna() & (rest > 0)
    out["v_line_radio_kms"] = np.nan
    out.loc[valid, "v_line_radio_kms"] = C_KMS * (rest[valid] - obs[valid]) / rest[valid]

    if "source_vlsr_kms" not in out.columns:
        for alias in ("VLSR [km/s]", "VLSR[km/s]", "vlsr_kms", "VLSR", "v_lsr_kms"):
            if alias in out.columns:
                out["source_vlsr_kms"] = pd.to_numeric(out[alias], errors="coerce")
                break
    if "source_vlsr_kms" not in out.columns:
        out["source_vlsr_kms"] = np.nan
    else:
        out["source_vlsr_kms"] = pd.to_numeric(out["source_vlsr_kms"], errors="coerce")

    good_v = valid & out["source_vlsr_kms"].notna()
    out["nu_expected_vlsr_mhz"] = np.nan
    out.loc[good_v, "nu_expected_vlsr_mhz"] = rest[good_v] * (1.0 - out.loc[good_v, "source_vlsr_kms"] / C_KMS)
    out["delta_nu_vlsr_mhz"] = np.nan
    out.loc[good_v, "delta_nu_vlsr_mhz"] = obs[good_v] - out.loc[good_v, "nu_expected_vlsr_mhz"]
    out["delta_v_lsr_kms"] = np.nan
    out.loc[good_v, "delta_v_lsr_kms"] = out.loc[good_v, "v_line_radio_kms"] - out.loc[good_v, "source_vlsr_kms"]
    return out



def reattach_observational_metadata(frame: pd.DataFrame | None, source_df: pd.DataFrame) -> pd.DataFrame:
    """Reattach M1/user observational values from one canonical row per obs_id.

    Catalog candidates must never become the authority for measured quantities.
    This function deliberately overwrites observational fields after candidate
    ranking so frequency, fitted peak, source path and line identity are exactly
    those received by M2.  It also prevents accidental cross-row contamination
    when several spectra contain local L1/L2/... labels.
    """
    if frame is None or frame.empty or source_df is None or source_df.empty:
        return frame
    out = frame.copy()
    src = source_df.copy()
    if "obs_id" not in src.columns or "obs_id" not in out.columns:
        return out
    src["obs_id"] = pd.to_numeric(src["obs_id"], errors="coerce")
    src = src[src["obs_id"].notna()].copy()
    if src.empty:
        return out
    src["obs_id"] = src["obs_id"].astype(int)
    # obs_id is synthesized as unique when local M1 Line values repeat.  Keep
    # exactly one canonical source row per identifier as an invariant.
    src = src.drop_duplicates(subset=["obs_id"], keep="first").set_index("obs_id")
    observational = [
        "Line", "Source", "source_path", "source_vlsr_kms", "VLSR [km/s]",
        "T_A [K]", "T_obs_at_fit [K]", "Δv [Km/s]", "σ_Δv [Km/s]",
        "IntInt [K*Km/s]", "σ_IntInt [K*Km/s]", "Ajuste", "GOI",
        "detection_id", "Semilla_ν[MHz]", "ν[MHz]",
    ]
    out_ids = pd.to_numeric(out["obs_id"], errors="coerce")
    for col in observational:
        if col not in src.columns:
            continue
        mapped = out_ids.map(src[col])
        # Source data are authoritative even when a catalog-normalization stage
        # happened to carry a same-named column.
        out[col] = mapped.to_numpy()
    if COL_FREQ in src.columns:
        mapped_freq = out_ids.map(pd.to_numeric(src[COL_FREQ], errors="coerce"))
        out["ν_obs_MHz"] = mapped_freq.to_numpy(dtype=float)
    return out

def build_topk_panel(cands_df: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    if cands_df is None or cands_df.empty:
        return pd.DataFrame()

    c = cands_df[np.isfinite(cands_df["cand_score"].values)].copy()
    if c.empty:
        return pd.DataFrame()

    c = c.sort_values(["obs_id", "cand_score"], ascending=[True, True], kind="mergesort")
    c["rank"] = c.groupby("obs_id")["cand_score"].rank(method="first", ascending=True).astype(int)
    topk_df = c[c["rank"] <= int(k)].copy()

    nice_cols = [
        # control
        "obs_id", "rank",

        # identificación visible primero
        "name",
        "chemical_name",
        "base_formula",
        "linelist",

        # observacionales
        "ν_obs_MHz",
        "orderedfreq",
        "Δν_MHz",
        "Source",
        "source_path",
        "source_vlsr_kms",
        "Line",
        "Grupo",
        "detection_id",

        # claves necesarias para Q(T)
        "species_id",
        "moleculeTag",

        # parámetros físicos / espectroscópicos
        "lower_state_energy",
        "lower_state_energy_K",
        "upper_state_energy",
        "upper_state_energy_K",
        "sijmu2",
        "sij",
        "aij",
        "upperStateDegen",

        # columnas observacionales que necesitan 3.1 y 3.2
        "T_obs_at_fit [K]",
        "T_A [K]",
        "Δv [Km/s]",
        "σ_Δv [Km/s]",
        "IntInt [K*Km/s]",
        "σ_IntInt [K*Km/s]",
        "Ajuste",
        "GOI",

        # Q(T)
        "Q_source",

        # score
        "eu_k",
        "heavy_atoms_count",
        "H_count",
        "complexity_score",
        "whitelisted",
        "blacklisted",
        "has_halogen",
        "vib_excited",
        "allowed_family",
        "score_mode",
        "cand_score",
        "rescue_mode",
    ]

    qt_cols = sorted([c for c in topk_df.columns if c.startswith("Q_") and c != "Q_source"])
    if "Q_source" in topk_df.columns:
        insert_at = nice_cols.index("Q_source")
        nice_cols = nice_cols[:insert_at] + qt_cols + ["Q_source"] + nice_cols[insert_at + 1:]
    else:
        nice_cols.extend(qt_cols)

    nice_cols = [c for c in nice_cols if c in topk_df.columns]
    return topk_df[nice_cols].reset_index(drop=True)

def safe_float(value):
    if value is None:
        return np.nan
    s = str(value).strip()
    if s in {"", "---", "nan", "NaN", "None"}:
        return np.nan
    try:
        return float(s)
    except Exception:
        return np.nan


def load_cdms_partition_table(path: Path) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame()

    rows = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip()
            if not line or line.startswith("=") or line.lower().startswith("tag"):
                continue

            m = re.match(r"^\s*(\d+)\s+(.+?)\s+(\d+)\s+(.+)$", line)
            if not m:
                continue

            tag = m.group(1).strip()
            molecule = m.group(2).strip()
            nlines = m.group(3).strip()
            rest = m.group(4).split()

            if len(rest) < len(CDMS_T_GRID):
                continue

            qvals = [safe_float(x) for x in rest[:len(CDMS_T_GRID)]]
            rows.append({
                "tag": tag,
                "molecule": molecule,
                "nlines": safe_float(nlines),
                **{f"T_{T}": q for T, q in zip(CDMS_T_GRID, qvals)}
            })

    return pd.DataFrame(rows)


def load_jpl_partition_table(path: Path) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame()

    try:
        df = pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

    df.columns = [str(c).strip() for c in df.columns]

    return df


def normalize_species_label(text: str) -> str:
    s = strip_html(text or "")
    s = s.strip().lower()
    s = re.sub(r"\bv\d*\s*=\s*\d+\b", "", s)
    s = re.sub(r"[;,]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def interpolate_partition_loglog(temp_grid, q_grid, target_t: float) -> float:
    temp_grid = np.asarray(temp_grid, dtype=float)
    q_grid = np.asarray(q_grid, dtype=float)

    mask = np.isfinite(temp_grid) & np.isfinite(q_grid) & (temp_grid > 0) & (q_grid > 0)
    temp_grid = temp_grid[mask]
    q_grid = q_grid[mask]

    if len(temp_grid) < 2:
        return np.nan

    order = np.argsort(temp_grid)
    temp_grid = temp_grid[order]
    q_grid = q_grid[order]

    logt = np.log10(temp_grid)
    logq = np.log10(q_grid)
    val = np.interp(np.log10(target_t), logt, logq, left=logq[0], right=logq[-1])
    return float(10 ** val)


def extract_cdms_qrow(cdms_df: pd.DataFrame, candidate_row: pd.Series):
    if cdms_df is None or cdms_df.empty:
        return None

    names_to_try = [
        normalize_species_label(candidate_row.get("chemical_name", "")),
        normalize_species_label(candidate_row.get("name", "")),
        normalize_species_label(candidate_row.get("base_formula", "")),
    ]

    best_idx = None
    for name in names_to_try:
        if not name:
            continue

        hits = cdms_df[
            cdms_df["molecule"].astype(str).map(normalize_species_label).str.contains(re.escape(name), na=False)
        ]
        if not hits.empty:
            best_idx = hits.index[0]
            break

    if best_idx is None:
        return None

    return cdms_df.loc[best_idx]


def extract_jpl_qrow(jpl_df: pd.DataFrame, candidate_row: pd.Series):
    if jpl_df is None or jpl_df.empty:
        return None

    col_candidates = [c for c in jpl_df.columns if "molecule" in c.lower() or "species" in c.lower() or "name" in c.lower()]
    if not col_candidates:
        return None

    mol_col = col_candidates[0]

    names_to_try = [
        normalize_species_label(candidate_row.get("chemical_name", "")),
        normalize_species_label(candidate_row.get("name", "")),
        normalize_species_label(candidate_row.get("base_formula", "")),
    ]

    best_idx = None
    for name in names_to_try:
        if not name:
            continue

        hits = jpl_df[
            jpl_df[mol_col].astype(str).map(normalize_species_label).str.contains(re.escape(name), na=False)
        ]
        if not hits.empty:
            best_idx = hits.index[0]
            break

    if best_idx is None:
        return None

    return jpl_df.loc[best_idx]


def parse_cdms_catalog_for_logic(txt_path: Path) -> pd.DataFrame:
    if not Path(txt_path).is_file():
        return pd.DataFrame()

    data = []
    pat = re.compile(r"^\s*(\d+)\s+(.+?)\s{2,}(\d+)\s+(.+)$")

    with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.rstrip("\n")
            if not s or s.startswith("=") or s.lower().startswith("tag"):
                continue

            m = pat.match(s)
            if not m:
                continue

            tag = int(m.group(1))
            molecule = m.group(2).strip()
            tail = re.split(r"\s+", m.group(4).strip())

            if len(tail) < 11:
                continue

            vals = []
            for x in tail[-11:]:
                if x == "---":
                    vals.append(None)
                else:
                    try:
                        vals.append(float(x))
                    except Exception:
                        vals.append(None)

            data.append((tag, molecule, *vals))

    cols = [
        "tag", "molecule",
        "lgQ1000", "lgQ500", "lgQ300", "lgQ225", "lgQ150",
        "lgQ75", "lgQ37_5", "lgQ18_75", "lgQ9_375", "lgQ5", "lgQ2_725"
    ]
    return pd.DataFrame(data, columns=cols)


def build_cdms_logq_dict(cdms_df: pd.DataFrame) -> dict[int, list[float | None]]:
    if cdms_df is None or cdms_df.empty:
        return {}

    cols_q = [
        "lgQ1000", "lgQ500", "lgQ300", "lgQ225", "lgQ150",
        "lgQ75", "lgQ37_5", "lgQ18_75", "lgQ9_375", "lgQ5", "lgQ2_725"
    ]

    return {
        int(r["tag"]): [r[c] if pd.notna(r[c]) else None for c in cols_q]
        for _, r in cdms_df.iterrows()
    }


def load_jpl_points_table(path_tsv: Path) -> dict[int, tuple[list[float], list[float]]]:
    if not Path(path_tsv).is_file():
        return {}

    try:
        df = pd.read_csv(path_tsv, sep="\t", dtype=str)
    except Exception:
        try:
            df = pd.read_csv(path_tsv, dtype=str)
        except Exception:
            return {}

    tag_col = next((c for c in ["tag", "moleculeTag", "jpl_tag", "Tag"] if c in df.columns), None)
    if tag_col is None:
        return {}

    qcols = []
    tvals = []
    for c in df.columns:
        m = re.match(r"\s*lg\(\s*Q\(([\d\.]+)\)\s*\)\s*$", str(c))
        if m:
            qcols.append(c)
            tvals.append(float(m.group(1)))

    if not qcols:
        return {}

    points = {}
    for _, row in df.iterrows():
        try:
            tag = int(abs(float(row[tag_col])))
        except Exception:
            continue

        Ts = []
        logQs = []
        for T, qc in zip(tvals, qcols):
            try:
                lq = float(row.get(qc, np.nan))
            except Exception:
                lq = np.nan
            if np.isfinite(lq):
                Ts.append(float(T))
                logQs.append(float(lq))

        if Ts:
            points[int(tag)] = (Ts, logQs)

    return points


def interp_logQ_logT_from_cdms_vec(logq_vec, T: float):
    points = []
    for Ti, lQ in zip(CDMS_T_GRID, logq_vec):
        if lQ is not None and np.isfinite(lQ) and Ti > 0:
            points.append((math.log10(Ti), float(lQ)))

    if not points:
        return None

    points.sort(key=lambda item: item[0])
    xs = [item[0] for item in points]
    ys = [item[1] for item in points]

    x = math.log10(T)

    if len(xs) == 1:
        return ys[0]

    if x <= xs[0]:
        return ys[0] + (ys[1] - ys[0]) / (xs[1] - xs[0]) * (x - xs[0])

    if x >= xs[-1]:
        return ys[-1] + (ys[-1] - ys[-2]) / (xs[-1] - xs[-2]) * (x - xs[-1])

    return float(np.interp(x, xs, ys))


def interp_logQ_from_points(Ts, logQs, T: float):
    xs = [math.log10(t) for t in Ts if t > 0]
    ys = [lq for lq, t in zip(logQs, Ts) if t > 0]

    if not xs or len(xs) != len(ys):
        return None

    xs, ys = (list(t) for t in zip(*sorted(zip(xs, ys))))
    x = math.log10(T)

    if x <= xs[0]:
        return ys[0] if len(xs) < 2 else ys[0] + (ys[1] - ys[0]) / (xs[1] - xs[0]) * (x - xs[0])

    if x >= xs[-1]:
        return ys[-1] if len(xs) < 2 else ys[-1] + (ys[-2] - ys[-1]) / (xs[-2] - xs[-1]) * (x - xs[-1])

    return float(np.interp(x, xs, ys))


def get_partition_values_for_row(candidate_row: pd.Series, cdms_logq: dict, jpl_points: dict, target_temperatures: list[float]):
    candidate_tags = []
    molecule_tags = []
    for col in ("moleculeTag", "species_id"):
        if pd.notna(candidate_row.get(col, np.nan)):
            try:
                tag = int(abs(int(float(candidate_row[col]))))
                candidate_tags.append(tag)
                if col == "moleculeTag":
                    molecule_tags.append(tag)
            except Exception:
                pass

    linelist = str(candidate_row.get("linelist", "") or "").strip().upper()
    source_order = ("JPL", "CDMS") if linelist == "JPL" else ("CDMS", "JPL")

    for source in source_order:
        if source == "CDMS":
            for tag in molecule_tags:
                if tag not in cdms_logq:
                    continue
                logq_vec = cdms_logq[tag]
                values = {}
                for T in target_temperatures:
                    lQ = interp_logQ_logT_from_cdms_vec(logq_vec, T)
                    values[qcol_name(T)] = (10.0 ** lQ) if lQ is not None else np.nan
                return (
                    values,
                    "CDMS",
                    CDMS_T_GRID,
                    [10.0 ** x if x is not None else np.nan for x in logq_vec],
                )
        else:
            for tag in candidate_tags:
                if tag not in jpl_points:
                    continue
                Ts, logQs = jpl_points[tag]
                values = {}
                for T in target_temperatures:
                    lQ = interp_logQ_from_points(Ts, logQs, T)
                    values[qcol_name(T)] = (10.0 ** lQ) if lQ is not None else np.nan
                return values, "JPL", Ts, [10.0 ** lq for lq in logQs]

    return {qcol_name(T): np.nan for T in target_temperatures}, "NONE", [], []


def partition_function_for_row(
    candidate_row: pd.Series,
    temperature_k: float,
) -> tuple[float, str]:
    """Obtiene Q(T) para una fila de Splatalogue usando los catálogos incluidos.

    Esta API compacta permite que otros módulos científicos reutilicen la misma
    identificación CDMS/JPL que el buscador, sin depender de widgets ni de las
    temperaturas que estuvieran visibles al ejecutar la búsqueda original.
    """

    temperature_k = float(temperature_k)
    if not np.isfinite(temperature_k) or temperature_k <= 0:
        raise ValueError("La temperatura para Q(T) debe ser mayor que cero.")

    cdms_table = parse_cdms_catalog_for_logic(CDMS_PATH)
    cdms_logq = build_cdms_logq_dict(cdms_table)
    jpl_points = load_jpl_points_table(JPL_TABLE_PATH)
    values, source, _, _ = get_partition_values_for_row(
        candidate_row,
        cdms_logq,
        jpl_points,
        [temperature_k],
    )
    value = float(values.get(qcol_name(temperature_k), np.nan))
    return value, source

def safe_int_tag(value):
    try:
        if pd.isna(value):
            return None
        return int(abs(int(float(value))))
    except Exception:
        return None


def build_qt_unique_key(candidate_row: pd.Series) -> str:
    linelist = str(candidate_row.get("linelist", "") or "").strip().upper()
    molecule_tag = safe_int_tag(candidate_row.get("moleculeTag", np.nan))
    species_id = safe_int_tag(candidate_row.get("species_id", np.nan))
    name = str(candidate_row.get("name", "") or "").strip()
    chemical_name = str(candidate_row.get("chemical_name", "") or "").strip()

    primary_tag = molecule_tag if molecule_tag is not None else species_id
    primary_name = name if name else chemical_name

    return f"{linelist}__{primary_tag}__{primary_name}"


def build_qt_species_label(candidate_row: pd.Series) -> str:
    linelist = str(candidate_row.get("linelist", "") or "").strip().upper()
    molecule_tag = safe_int_tag(candidate_row.get("moleculeTag", np.nan))
    species_id = safe_int_tag(candidate_row.get("species_id", np.nan))

    primary_name = str(candidate_row.get("name", "") or "").strip()
    if not primary_name:
        primary_name = str(candidate_row.get("chemical_name", "") or "").strip()
    if not primary_name:
        primary_name = "unknown"

    if molecule_tag is not None:
        return f"{primary_name} [{linelist}:{molecule_tag}]"
    if species_id is not None:
        return f"{primary_name} [{linelist}:{species_id}]"

    return primary_name

def make_qt_plot(
    output_path: Path,
    species_label: str,
    temp_grid,
    q_grid,
    target_temperatures: list[float],
    q_values: dict[str, float],   # se deja por compatibilidad, pero ya no manda
    q_source: str,
):
    temp_grid = np.asarray(temp_grid, dtype=float)
    q_grid = np.asarray(q_grid, dtype=float)

    mask = np.isfinite(temp_grid) & np.isfinite(q_grid) & (temp_grid > 0) & (q_grid > 0)
    if mask.sum() < 2:
        return

    temp_grid = temp_grid[mask]
    q_grid = q_grid[mask]

    order = np.argsort(temp_grid)
    temp_grid = temp_grid[order]
    q_grid = q_grid[order]

    dense_t = np.geomspace(temp_grid.min(), temp_grid.max(), 300)
    dense_q = [interpolate_partition_loglog(temp_grid, q_grid, t) for t in dense_t]

    plt.figure(figsize=(7, 5))
    plt.loglog(temp_grid, q_grid, "o", label=f"{q_source} catálogo")
    plt.loglog(dense_t, dense_q, "-", label="Interpolación")

    # IMPORTANTE:
    # los puntos de 10 K, 28 K, etc. se calculan desde la MISMA curva
    # para que nunca se desfasen respecto a la interpolación mostrada
    for T in target_temperatures:
        if T <= 0:
            continue

        qv = interpolate_partition_loglog(temp_grid, q_grid, T)
        if np.isfinite(qv) and qv > 0:
            plt.scatter([T], [qv], marker="x", s=70, label=f"{T:g} K")

    plt.xlabel("Temperatura [K]")
    plt.ylabel("Q(T)")
    plt.title(f"Q(T) - {species_label}")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()

def score_candidate_row(row: pd.Series) -> float:
    """
    Score básico:
    - prioriza cercanía en frecuencia
    - favorece menor Eu
    - favorece logA mayor
    - penaliza moléculas complejas / raras
    """
    freq_diff = pd.to_numeric(row.get("freq_diff_MHz", np.nan), errors="coerce")
    eu_k = pd.to_numeric(row.get("eu_k", np.nan), errors="coerce")

    loga_val = np.nan
    for a_col in ("logaij", "log10_Aij", "aij"):
        if a_col in row.index:
            loga_val = pd.to_numeric(row.get(a_col), errors="coerce")
            if pd.notna(loga_val):
                break

    chem_name = str(row.get("chemical_name", "") or "")
    formula = str(row.get("species", "") or row.get("name", "") or "")

    complexity_score, heavy_n, h_count, base_form = molecular_complexity(chem_name, formula)

    score = 0.0

    # 1) Frecuencia: mientras más cerca, mejor
    if pd.notna(freq_diff):
        score += W_FREQ * float(freq_diff)
    else:
        score += W_FREQ * 999.0

    # 2) Eu: mientras más baja, mejor
    if pd.notna(eu_k):
        score += W_EU * (float(eu_k) / 100.0)
    else:
        score += W_EU * 5.0

    # 3) logA: mientras más alta, mejor => restamos algo al score
    if pd.notna(loga_val):
        score -= W_LOGA * float(loga_val)

    # 4) Complejidad química
    score += COMPLEXITY_PENALTY_WEIGHT * float(complexity_score)

    # 5) Penalizaciones extra / bonos
    if is_blacklisted(chem_name, formula):
        score += BLACKLIST_PENALTY

    if is_base_whitelisted(chem_name, formula):
        score -= WHITELIST_BONUS

    if not allowed_by_family(chem_name, formula):
        score += FAMILY_MISMATCH_PENALTY

    if has_halogen(chem_name) or has_halogen(formula):
        score += HALOGEN_PENALTY

    if is_vibrationally_excited(chem_name) or is_vibrationally_excited(formula):
        score += VIB_EXCITED_PENALTY

    if AROMATIC_PAT.search(chem_name) or AROMATIC_PAT.search(formula):
        score += AROMATIC_EXTRA_PENALTY

    if max(count_CN_groups(chem_name), count_CN_groups(formula)) >= 2:
        score += MULTI_CN_EXTRA_PENALTY

    return float(score)

def estimate_peak_height(dv_kms, intint_k_kms, ajuste):
    """
    Estima altura de pico si no se dispone de T_A[K].
    """
    try:
        dv = float(dv_kms) if dv_kms is not None else None
        area = float(intint_k_kms) if intint_k_kms is not None else None
    except Exception:
        dv = None
        area = None

    if (dv is None) or (area is None) or (dv <= 0) or (area <= 0):
        return None

    mode = (str(ajuste).strip().lower() if isinstance(ajuste, str) else "")

    if mode in ("lorentz", "lorentziano"):
        gamma_v = dv / 2.0
        return area / (np.pi * max(gamma_v, 1e-12))

    elif mode == "voigt":
        sigma_v = dv / (2.0 * np.sqrt(2.0 * np.log(2.0)))
        a_g = area / (np.sqrt(2 * np.pi) * sigma_v)
        gamma_v = dv / 2.0
        a_l = area / (np.pi * max(gamma_v, 1e-12))
        return 0.5 * a_l + 0.5 * a_g

    else:  # gaussiano
        sigma_v = dv / (2.0 * np.sqrt(2.0 * np.log(2.0)))
        return area / (np.sqrt(2 * np.pi) * sigma_v)


def find_dat_path(source_name: str, csv_input_path: Path, run_dir: Path) -> Path | None:
    """
    Busca el archivo .dat asociado al Source.
    """
    if not source_name:
        return None

    name = Path(str(source_name)).name
    csv_dir = csv_input_path.resolve().parent if csv_input_path.exists() else Path(".").resolve()

    tries = [
        csv_dir / name,
        run_dir / name,
        Path(name),
    ]

    for p in tries:
        if p.is_file():
            return p

    for root in {csv_dir, run_dir, Path(".").resolve()}:
        try:
            hits = list(root.rglob(name))
            if hits:
                return hits[0]
        except Exception:
            pass

    return None


def parse_dat_file(path: Path):
    xs, ys = [], []

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            s = raw.strip()
            if not s or s.startswith(("#", ";", "!", "//")):
                continue

            s = s.replace(",", " ")
            toks = [t for t in re.split(r"\s+", s) if t]

            nums = []
            for t in toks:
                try:
                    nums.append(float(t))
                except Exception:
                    pass

            if len(nums) >= 3:
                chosen = None
                for i in range(len(nums) - 1):
                    if 1e3 <= nums[i] <= 5e5 and abs(nums[i + 1]) <= 200:
                        chosen = (nums[i], nums[i + 1])
                        break
                if chosen is None:
                    chosen = (nums[0], nums[1])

                xs.append(chosen[0])
                ys.append(chosen[1])

            elif len(nums) >= 2:
                xs.append(nums[0])
                ys.append(nums[1])

    if len(xs) < 5:
        return None, None

    order = np.argsort(xs)
    return np.asarray(xs)[order], np.asarray(ys)[order]


def make_source_plot(df_input: pd.DataFrame, out_df: pd.DataFrame, source_name: str, csv_input_path: Path, run_dir: Path):
    """
    Genera una figura Plotly por Source:
    - espectro .dat
    - líneas detectadas
    - etiquetas de moléculas
    """
    if "Source" not in df_input.columns:
        return None

    sub = df_input[df_input["Source"].astype(str) == str(source_name)].copy()
    if sub.empty:
        return None

    needed_input = ["obs_id", COL_FREQ, "T_A [K]", "Δv [Km/s]", "IntInt [K*Km/s]", "Ajuste"]
    sub = sub[[c for c in needed_input if c in sub.columns]].copy()

    needed_out = ["obs_id", "chemical_name", "name"]
    join = pd.merge(
        sub,
        out_df[[c for c in needed_out if c in out_df.columns]],
        on="obs_id",
        how="left",
    )

    x_lines, y_lines = [], []
    x_peaks, y_peaks, labels = [], [], []

    for _, r in join.iterrows():
        nu0 = float(r[COL_FREQ])

        ta = r.get("T_A [K]", np.nan)
        height = float(ta) if pd.notna(ta) else None

        if (height is None) or not np.isfinite(height):
            height = estimate_peak_height(
                r.get("Δv [Km/s]"),
                r.get("IntInt [K*Km/s]"),
                r.get("Ajuste"),
            )

        if (height is None) or not np.isfinite(height):
            height = 0.05

        label = str(r.get("name") or r.get("chemical_name") or "").strip()
        if label == "— sin candidato —":
            label = ""

        x_lines += [nu0, nu0, None]
        y_lines += [0.0, float(height), None]

        if label:
            x_peaks.append(nu0)
            y_peaks.append(float(height))
            labels.append(label)

    fig = go.Figure()

    dat_path = find_dat_path(source_name, csv_input_path=csv_input_path, run_dir=run_dir)
    if dat_path:
        fx, fy = parse_dat_file(dat_path)
        if fx is not None:
            fig.add_trace(go.Scatter(
                x=fx,
                y=fy,
                mode="lines",
                name="Espectro",
                line=dict(width=1),
                hovertemplate="ν=%{x:.3f} MHz<br>T_A=%{y:.3f} K<extra></extra>",
            ))

    fig.add_trace(go.Scatter(
        x=x_lines,
        y=y_lines,
        mode="lines",
        name="Picos",
        line=dict(width=2, dash="dot"),
        hoverinfo="skip",
    ))

    if x_peaks:
        fig.add_trace(go.Scatter(
            x=x_peaks,
            y=y_peaks,
            mode="markers+text",
            name="Moléculas",
            text=labels,
            textposition="top center",
            textfont=dict(size=11),
            marker=dict(size=7),
            hovertemplate="ν=%{x:.3f} MHz<br>%{text}<extra></extra>",
        ))

    fig.update_layout(
        title=f"Espectro: {source_name}",
        template="plotly_white",
        xaxis_title="ν [MHz]",
        yaxis_title="T_A [K]",
        autosize=True,
        margin=dict(l=30, r=10, t=40, b=30),
        xaxis=dict(automargin=True),
        yaxis=dict(automargin=True),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        updatemenus=[dict(
            type="buttons",
            direction="right",
            x=0.01,
            y=0.99,
            xanchor="left",
            yanchor="top",
            pad=dict(l=6, r=6, t=6, b=6),
            buttons=[
                dict(label="Mostrar todo", method="update", args=[{"visible": [True, True, True]}]),
                dict(label="Sólo datos (.dat)", method="update", args=[{"visible": [True, False, False]}]),
                dict(label="Sólo picos", method="update", args=[{"visible": [False, True, False]}]),
                dict(label="Sólo etiquetas", method="update", args=[{"visible": [False, False, True]}]),
            ],
        )],
    )

    return fig


def save_plotly_html(fig: go.Figure, out_html: Path):
    fig.write_html(
        str(out_html),
        include_plotlyjs=True,
        full_html=True,
        config={"responsive": True, "displaylogo": False},
        default_width="100%",
        default_height="96vh",
    )

def run_species_search(config: SpeciesSearchConfig, progress_callback=None) -> SpeciesSearchResult:
    require_online("M2 molecular identification")
    logs: list[str] = []

    def report(value, message):
        if progress_callback is not None:
            progress_callback(value, message)

    try:
        report(3, "Validando la configuración")
        csv_input = Path(config.csv_input)
        if not csv_input.exists():
            return SpeciesSearchResult(
                success=False,
                message=f"No se encontró el archivo CSV: {csv_input}",
                logs=logs,
            )

        output_name = config.output_name.strip()
        if not output_name:
            return SpeciesSearchResult(
                success=False,
                message="Debes proporcionar un nombre de salida.",
                logs=logs,
            )

        target_temperatures = sorted(set(float(t) for t in config.target_temperatures if float(t) > 0))

        topk = max(1, int(config.topk))
        policy = SpeciesSearchPolicy.from_mapping(config.search_policy)

        compute_q_values = bool(config.compute_q_values)
        generate_qt_plots = bool(config.generate_qt_plots)
        generate_plotly = bool(config.generate_plotly)

        logs.append(f"Archivo de entrada: {csv_input}")
        logs.append(f"Nombre base de salida: {output_name}")
        logs.append(f"Temperaturas objetivo: {target_temperatures if target_temperatures else 'no especificadas'}")
        logs.append(f"TOP-K: {topk}")
        logs.append(f"Perfil de identificación: {policy.profile}")
        logs.append(f"Filtros M2: Eu≤{policy.eu_max_k:g} K; heavy(strict/soft)={policy.heavy_atoms_strict_max}/{policy.soft_heavy_max}; COM={policy.allow_complex_organics}; emergencia abierta={policy.allow_emergency_outside_family}")
        logs.append(f"Generar gráficas Q(T): {generate_qt_plots}")
        logs.append(f"Generar gráficas Plotly: {generate_plotly}")
        logs.append(f"Calcular Q(T): {compute_q_values}")

        requested_name = Path(output_name)
        input_name = sanitize_name(csv_input.stem)
        custom_name = sanitize_name(requested_name.stem or requested_name.name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        run_tag = custom_name if custom_name else input_name

        species_root_dir = ensure_dir(SPECIES_SEARCH_OUTPUT_DIR)
        run_dir = ensure_dir(species_root_dir / f"{run_tag}_{timestamp}")

        plotly_dir = run_dir / "plotly"
        qt_dir = run_dir / "q_t"

        logs.append(f"Directorio raíz de species_search: {species_root_dir}")
        logs.append(f"Directorio de ejecución: {run_dir}")
        logs.append(f"Ruta prevista para Plotly: {plotly_dir}")
        logs.append(f"Ruta prevista para Q(T): {qt_dir}")

        report(7, "Leyendo las líneas detectadas")
        df = pd.read_csv(csv_input)
        logs.append(f"CSV cargado: {len(df)} filas iniciales")

        if COL_FREQ not in df.columns:
            return SpeciesSearchResult(
                success=False,
                message=f"No se encontró la columna requerida '{COL_FREQ}' en el CSV.",
                logs=logs,
            )

        df = df[df[COL_FREQ].astype(str).str.strip().ne(COL_FREQ)].copy()

        df[COL_FREQ] = pd.to_numeric(
            df[COL_FREQ].astype(str).str.replace(",", "", regex=False).str.replace("±", "", regex=False),
            errors="coerce"
        )

        df = df.dropna(subset=[COL_FREQ]).reset_index(drop=True)

        if df.empty:
            return SpeciesSearchResult(
                success=False,
                message="No quedaron frecuencias numéricas válidas en la columna de entrada.",
                logs=logs,
            )

        # Preserve an explicit observation identifier when possible. M1 uses
        # Line=1..N; external tables may already provide obs_id.  Only synthesize
        # a 1-based identifier when neither is usable.
        existing_obs = pd.to_numeric(df.get("obs_id"), errors="coerce") if "obs_id" in df.columns else None
        line_obs = pd.to_numeric(df.get("Line"), errors="coerce") if "Line" in df.columns else None
        if existing_obs is not None and existing_obs.notna().all() and existing_obs.is_unique:
            df["obs_id"] = existing_obs.astype(int)
        elif line_obs is not None and line_obs.notna().all() and line_obs.is_unique:
            df["obs_id"] = line_obs.astype(int)
        else:
            df["obs_id"] = np.arange(1, len(df) + 1, dtype=int)

        if "Grupo" not in df.columns:
            if "GOI" in df.columns:
                df["Grupo"] = (
                    df["GOI"]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .map({"individual": "individual", "grupo": "grupo"})
                    .fillna(df["GOI"].astype(str).str.strip().str.lower())
                )
            else:
                df["Grupo"] = "individual"

        logs.append(f"CSV limpio: {len(df)} filas válidas")

        report(11, "Preparando consultas a Splatalogue")
        candidate_tables: list[pd.DataFrame] = []
        no_match_count = 0

        row_count = max(1, len(df))

        def _base_query(item):
            row_index, row = item
            obs_id = int(row["obs_id"])
            nu_MHz = float(row[COL_FREQ])
            dv_obs = None
            if "Δv [Km/s]" in df.columns and pd.notna(row.get("Δv [Km/s]")):
                try:
                    dv_obs = float(row["Δv [Km/s]"])
                except Exception:
                    dv_obs = None
            result = query_splatalogue_candidates(
                obs_id=obs_id,
                nu_MHz=nu_MHz,
                dv_obs=dv_obs,
                source_row=row,
                widen_factor=1.0,
                energy_max_k=policy.eu_max_k,
                policy=policy,
            )
            return row_index, obs_id, result

        rows_for_query = [(i, row.copy()) for i, (_, row) in enumerate(df.iterrows())]
        completed = 0
        # Splatalogue calls are network-bound; a small pool improves M2 latency
        # without launching an aggressive number of requests against the service.
        with ThreadPoolExecutor(max_workers=policy.query_workers) as executor:
            future_map = {executor.submit(_base_query, item): item[0] for item in rows_for_query}
            for future in as_completed(future_map):
                completed += 1
                report(13 + int(37 * completed / row_count), f"Consultando línea {completed} de {len(df)}")
                try:
                    _row_index, obs_id, df_tab = future.result()
                    if df_tab.empty:
                        no_match_count += 1
                        logs.append(f"[obs_id={obs_id}] Sin candidatos en consulta base.")
                    else:
                        candidate_tables.append(df_tab)
                        logs.append(f"[obs_id={obs_id}] {len(df_tab)} candidatos base.")
                except Exception as query_exc:
                    logs.append(f"[consulta base] Error: {query_exc}")

        if candidate_tables:
            cands = pd.concat(candidate_tables, ignore_index=True)
            logs.append(f"Total de candidatos acumulados: {len(cands)}")
        else:
            cands = pd.DataFrame()

        if not cands.empty:
            cands["cand_score"] = cands.apply(lambda r: candidate_score_strict(r, policy), axis=1)
            cands["score_mode"] = np.where(np.isfinite(cands["cand_score"]), "strict", "discarded")
        else:
            cands["cand_score"] = []
            cands["score_mode"] = []

        need_rescue: list[int] = []
        if not cands.empty:
            for oid, g in cands.groupby("obs_id"):
                good = g[np.isfinite(g["cand_score"].values)]
                if good.empty or not any(
                    in_rescue_family(r.get("chemical_name", ""), r.get("name", ""))
                    for _, r in good.iterrows()
                ):
                    need_rescue.append(int(oid))
        else:
            need_rescue = sorted(df["obs_id"].astype(int).tolist())

        report(53, "Evaluando coincidencias y rescates")
        if need_rescue:
            logs.append(f"[RESCATE] Reintentando {len(need_rescue)} líneas con ventana ampliada.")

            rescue_rows = []
            for oid in need_rescue:
                row = df.loc[df["obs_id"] == oid].iloc[0]
                nu = float(row[COL_FREQ])

                dv = None
                if "Δv [Km/s]" in df.columns and pd.notna(row.get("Δv [Km/s]")):
                    try:
                        dv = float(row["Δv [Km/s]"])
                    except Exception:
                        dv = None

                try:
                    t = query_splatalogue_candidates(
                        obs_id=oid,
                        nu_MHz=nu,
                        dv_obs=dv,
                        source_row=row,
                        widen_factor=policy.rescue_widen_factor,
                        energy_max_k=policy.eu_max_k,
                        policy=policy,
                    )
                    if not t.empty:
                        t = t[
                            [
                                in_rescue_family(r.get("chemical_name", ""), r.get("name", ""))
                                for _, r in t.iterrows()
                            ]
                        ].copy()
                        if not t.empty:
                            t["rescue_mode"] = True
                            rescue_rows.append(t)
                except Exception as exc:
                    logs.append(f"[obs_id={oid}] Error en rescate: {exc}")

            if rescue_rows:
                rescue_df = pd.concat(rescue_rows, ignore_index=True)
                cols_for_dupe = [c for c in rescue_df.columns if c in cands.columns]
                cands = pd.concat([cands, rescue_df], ignore_index=True).drop_duplicates(
                    subset=cols_for_dupe, keep="first"
                )
                cands["cand_score"] = cands.apply(lambda r: candidate_score_strict(r, policy), axis=1)
                cands["score_mode"] = np.where(np.isfinite(cands["cand_score"]), "strict", "discarded")

        no_good = []
        if not cands.empty:
            for oid, g in cands.groupby("obs_id"):
                if not np.isfinite(g["cand_score"]).any():
                    no_good.append(int(oid))

        if no_good:
            logs.append(f"[SOFT] Aplicando modo soft a {len(no_good)} líneas.")
            mask = cands["obs_id"].isin(no_good)
            cands.loc[mask, "cand_score"] = cands.loc[mask].apply(lambda r: candidate_score_soft(r, policy), axis=1)
            fin = mask & np.isfinite(cands["cand_score"])
            cands.loc[fin, "score_mode"] = "soft"

        all_ids = set(df["obs_id"].astype(int).tolist())
        ids_with_finite = set()

        if not cands.empty:
            ids_with_finite = set(
                cands.loc[np.isfinite(cands["cand_score"].values), "obs_id"].astype(int).unique().tolist()
            )

        still_none = sorted(all_ids - ids_with_finite)

        report(62, "Completando identificaciones difíciles")
        if still_none:
            logs.append(f"[EMERGENCIA] Buscando coincidencias cercanas para {len(still_none)} líneas.")
            emer_rows = []

            for oid in still_none:
                row = df.loc[df["obs_id"] == oid].iloc[0]
                nu = float(row[COL_FREQ])

                dv = None
                if "Δv [Km/s]" in df.columns and pd.notna(row.get("Δv [Km/s]")):
                    try:
                        dv = float(row["Δv [Km/s]"])
                    except Exception:
                        dv = None

                try:
                    t = query_splatalogue_candidates(
                        obs_id=oid,
                        nu_MHz=nu,
                        dv_obs=dv,
                        source_row=row,
                        widen_factor=policy.emergency_widen_factor,
                        energy_max_k=policy.emergency_eu_max_k,
                        policy=policy,
                    )
                    if not t.empty:
                        if policy.allow_emergency_outside_family:
                            def emergency_score(r):
                                freq_diff = abs(float(r["orderedfreq"] - r["ν_obs_MHz"]))
                                denom = max(float(r["Δν_MHz"]), 1e-6)
                                fcost = min(1.0, freq_diff / denom)
                                cpen = 0.06 * max(0, int(r.get("heavy_atoms_count", 0)) - 2)
                                bpen = 2.0 if bool(r.get("blacklisted", False)) else 0.0
                                return fcost + cpen + bpen
                            t["cand_score"] = t.apply(emergency_score, axis=1)
                        else:
                            # Conservative emergency: do not force exotic chemistry.
                            # If every candidate fails the user-visible priors, this
                            # observation remains explicitly unidentified.
                            t["cand_score"] = t.apply(lambda r: candidate_score_soft(r, policy), axis=1)
                            t = t[np.isfinite(t["cand_score"].values)].copy()
                        if not t.empty:
                            t["score_mode"] = "emergency"
                            t["rescue_mode"] = True
                            t = t.sort_values(by=["cand_score", "orderedfreq"], ascending=[True, True])
                            emer_rows.append(t.head(EMERGENCY_TOPN))
                except Exception as exc:
                    logs.append(f"[obs_id={oid}] Error en emergencia: {exc}")

            if emer_rows:
                emer_df = pd.concat(emer_rows, ignore_index=True)
                cols_for_dupe = [c for c in emer_df.columns if c in cands.columns]
                cands = pd.concat([cands, emer_df], ignore_index=True).drop_duplicates(
                    subset=cols_for_dupe, keep="first"
                )

        report(70, "Jerarquizando candidatos")
        valid = cands[np.isfinite(cands["cand_score"].values)].copy() if not cands.empty else pd.DataFrame()

        if not valid.empty:
            main_df = valid.loc[
                valid.groupby("obs_id", sort=False)["cand_score"].idxmin()
            ].reset_index(drop=True)
        else:
            main_df = pd.DataFrame()

        missing = sorted(set(df["obs_id"]) - set(main_df["obs_id"])) if not main_df.empty else sorted(df["obs_id"].tolist())

        if missing:
            add = []
            for oid in missing:
                add.append({
                    "obs_id": oid,
                    "ν_obs_MHz": float(df.loc[df["obs_id"] == oid, COL_FREQ].iloc[0]),
                    "chemical_name": "— sin candidato plausible —",
                    "name": "",
                    "base_formula": "",
                    "heavy_atoms_count": np.nan,
                    "cand_score": np.nan,
                    "rescue_mode": False,
                    "score_mode": "none",
                })
            main_df = pd.concat([main_df, pd.DataFrame(add)], ignore_index=True, sort=False)

        extras = ["Line", "Source", "source_path", "source_vlsr_kms", "VLSR [km/s]", "detection_id", "Semilla_ν[MHz]", "T_obs_at_fit [K]", "T_A [K]", "Δv [Km/s]", "σ_Δv [Km/s]", "IntInt [K*Km/s]", "σ_IntInt [K*Km/s]", "Ajuste", "GOI"]
        present_extras = [c for c in extras if c in df.columns]
        df_min = df[["obs_id"] + present_extras].copy()
        rename_input = {c: f"{c}__input" for c in present_extras}
        df_min = df_min.rename(columns=rename_input)
        main_df = main_df.merge(df_min, on="obs_id", how="left")
        # Candidate rows already carry M1 metadata through the Splatalogue
        # normalization step.  Coalesce instead of creating Source_x/Source_y
        # (and, critically, fill those values for explicitly unidentified rows).
        for col in present_extras:
            incoming = f"{col}__input"
            if col not in main_df.columns:
                main_df[col] = main_df[incoming]
            else:
                current = main_df[col]
                if current.dtype == object:
                    empty = current.isna() | current.astype(str).str.strip().isin({"", "nan", "None"})
                else:
                    empty = current.isna()
                main_df.loc[empty, col] = main_df.loc[empty, incoming]
            main_df = main_df.drop(columns=[incoming], errors="ignore")

        for col in main_df.columns:
            if main_df[col].dtype == object:
                main_df[col] = main_df[col].astype(str).map(strip_html)

        main_df["obs_id"] = main_df["obs_id"].astype(int)
        main_df = main_df.sort_values(["obs_id"], ascending=[True], kind="stable").reset_index(drop=True)

        topk_df = build_topk_panel(cands, k=topk)
        # Scientific invariant: observational quantities come only from the M1/user
        # input row, never from a candidate row.  Reattach them after ranking.
        main_df = reattach_observational_metadata(main_df, df)
        topk_df = reattach_observational_metadata(topk_df, df)
        main_df = add_kinematic_columns(main_df)
        topk_df = add_kinematic_columns(topk_df)

        # =========================
        # C) Calcular Q(T) para tablas
        # =========================
        report(76, "Calculando funciones de partición")
        if compute_q_values:
            cdms_q_df = parse_cdms_catalog_for_logic(CDMS_PATH)
            cdms_logq = build_cdms_logq_dict(cdms_q_df)
            jpl_points = load_jpl_points_table(JPL_TABLE_PATH)

            logs.append(
                f"CDMS Q(T): {len(cdms_logq)} tags cargados"
                if cdms_logq else
                "CDMS Q(T): sin datos"
            )
            logs.append(
                f"JPL Q(T): {len(jpl_points)} tags cargados"
                if jpl_points else
                "JPL Q(T): sin datos"
            )

            q_targets = ((main_df, "main"), (topk_df, "topk"))
            total_q_rows = max(1, sum(len(target) for target, _ in q_targets if target is not None))
            completed_q_rows = 0
            for df_target, label in q_targets:
                if df_target is None or df_target.empty:
                    continue

                for idx in df_target.index:
                    report(
                        78 + int(12 * completed_q_rows / total_q_rows),
                        "Interpolando Q(T) de las especies",
                    )
                    row = df_target.loc[idx]
                    qvals, qsource, temp_grid, q_grid = get_partition_values_for_row(
                        candidate_row=row,
                        cdms_logq=cdms_logq,
                        jpl_points=jpl_points,
                        target_temperatures=target_temperatures,
                    )

                    for col_name, qv in qvals.items():
                        df_target.loc[idx, col_name] = qv

                    df_target.loc[idx, "Q_source"] = qsource
                    df_target.loc[idx, "Q_tag_key"] = build_qt_unique_key(row)
                    df_target.loc[idx, "Q_species_label"] = build_qt_species_label(row)
                    completed_q_rows += 1
        else:
            cdms_logq = {}
            jpl_points = {}
            logs.append("[Q(T)] Cálculo de Q(T) desactivado en esta corrida.")

        preferred_order = [
            "obs_id",
            "name",
            "chemical_name",
            "base_formula",
            "ν_obs_MHz",
            "orderedfreq",
            "source_vlsr_kms",
            "v_line_radio_kms",
            "delta_v_lsr_kms",
            "nu_expected_vlsr_mhz",
            "delta_nu_vlsr_mhz",
            "Δν_MHz",
            "Line",
            "T_obs_at_fit [K]",
            "T_A [K]",
            "eu_k",
            "cand_score",
            "score_mode",
            "Q_source",
        ]

        qt_cols = sorted([c for c in main_df.columns if c.startswith("Q_") and c != "Q_source"])
        preferred_order += qt_cols
        if "Q_source" not in preferred_order and "Q_source" in main_df.columns:
            preferred_order.append("Q_source")

        remaining = [c for c in main_df.columns if c not in preferred_order]
        main_df = main_df[[c for c in preferred_order + remaining if c in main_df.columns]]

        # =========================
        # D) Guardar gráficas Q(T)
        # =========================
        report(91, "Preparando productos gráficos")
        if generate_qt_plots:
            ensure_dir(qt_dir)
            qt_plot_written = set()

            if main_df is not None and not main_df.empty:
                tmp = main_df.copy()

                tmp["__qt_key__"] = tmp.apply(build_qt_unique_key, axis=1)
                tmp["__qt_label__"] = tmp.apply(build_qt_species_label, axis=1)

                tmp = tmp[
                    tmp["__qt_key__"].astype(str).str.strip().ne("") &
                    tmp["__qt_label__"].astype(str).str.strip().ne("")
                ].copy()

                for qt_key, g in tmp.groupby("__qt_key__", sort=False):
                    if not qt_key or qt_key in qt_plot_written:
                        continue

                    row0 = g.iloc[0]
                    species_label = str(row0["__qt_label__"]).strip()

                    local_cdms_logq = cdms_logq if compute_q_values else build_cdms_logq_dict(parse_cdms_catalog_for_logic(CDMS_PATH))
                    local_jpl_points = jpl_points if compute_q_values else load_jpl_points_table(JPL_TABLE_PATH)

                    qvals, qsource, temp_grid, q_grid = get_partition_values_for_row(
                        candidate_row=row0,
                        cdms_logq=local_cdms_logq,
                        jpl_points=local_jpl_points,
                        target_temperatures=target_temperatures,
                    )

                    if qsource == "NONE":
                        continue

                    plot_path = qt_dir / f"{sanitize_name(species_label)}.png"
                    make_qt_plot(
                        output_path=plot_path,
                        species_label=species_label,
                        temp_grid=temp_grid,
                        q_grid=q_grid,
                        target_temperatures=target_temperatures,
                        q_values=qvals,
                        q_source=qsource,
                    )
                    qt_plot_written.add(qt_key)

            logs.append(f"Gráficas Q(T) generadas: {len(qt_plot_written)}")
        else:
            logs.append("[Q(T)] Generación de gráficas desactivada en esta corrida.")

        report(96, "Formateando las tablas finales")
        main_df = round_dataframe_for_gui(main_df)
        topk_df = round_dataframe_for_gui(topk_df)

        logs.append(f"Tabla principal final: {len(main_df)} filas")
        logs.append(f"TOP-K final: {len(topk_df)} filas")
        logs.append(f"Observaciones sin coincidencias: {len(missing)} de {len(df)}")

        main_csv_path = None
        main_html_path = None
        topk_csv_path = None
        topk_html_path = None

        if generate_plotly:
            # =========================
            # E) Plotly por Source
            # =========================
            ensure_dir(plotly_dir)

            if "Source" in df.columns and main_df is not None and not main_df.empty:
                sources = sorted(df["Source"].dropna().astype(str).unique().tolist())

                for src in sources:
                    fig = make_source_plot(
                        df_input=df,
                        out_df=main_df,
                        source_name=src,
                        csv_input_path=csv_input,
                        run_dir=run_dir,
                    )

                    if fig is not None:
                        safe_src = re.sub(r"\W+", "_", str(src))
                        out_html = plotly_dir / f"{safe_src}.html"
                        save_plotly_html(fig, out_html)
                        logs.append(f"[PLOTLY] Guardado: {out_html}")
                    else:
                        logs.append(f"[PLOTLY] No se generó figura para Source={src}")
            else:
                logs.append("[PLOTLY] No se generaron gráficas Plotly (faltan Source o resultados principales).")
        else:
            logs.append("[PLOTLY] Generación de gráficas desactivada en esta corrida.")

        report(99, "Finalizando la identificación molecular")
        return SpeciesSearchResult(
            success=True,
            message="Consulta base a Splatalogue y TOP-K completados.",
            logs=logs,
            main_dataframe=main_df,
            topk_dataframe=topk_df,
            main_csv_path=str(main_csv_path) if main_csv_path else None,
            main_html_path=str(main_html_path) if main_html_path else None,
            topk_csv_path=str(topk_csv_path) if topk_csv_path else None,
            topk_html_path=str(topk_html_path) if topk_html_path else None,
            plotly_dir=str(plotly_dir),
            qt_dir=str(qt_dir),
            extra={
                "csv_input": str(csv_input),
                "run_dir": str(run_dir),
                "species_root_dir": str(species_root_dir),
                "output_base_name": run_tag,
                "target_temperatures": target_temperatures,
                "topk": topk,
                "search_policy": policy.to_dict(),
                "row_count": len(df),
                "no_match_count": no_match_count,
                "candidate_count": len(cands) if 'cands' in locals() else 0,
                "main_count": len(main_df),
                "topk_count": len(topk_df),
            },
        )

    except Exception as exc:
        logs.append("Ocurrió un error al ejecutar el buscador de especies.")
        logs.append(str(exc))
        logs.append(traceback.format_exc())

        return SpeciesSearchResult(
            success=False,
            message=f"Error en Buscador de especies: {exc}",
            logs=logs,
        )
