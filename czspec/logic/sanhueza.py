from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from itertools import permutations
import math
import os
import re

import numpy as np
import pandas as pd

from czspec.paths import CDMS_ABC_PATH, JPL_ABC_PATH, SANHUEZA_OUTPUT_DIR
from czspec.science_defaults import DEFAULT_ISOTOPIC_ABUNDANCE_RATIOS


# =========================
# Resultado estándar para GUI
# =========================
@dataclass
class SanhuezaResult:
    success: bool
    message: str
    logs: list[str] = field(default_factory=list)
    dataframe: pd.DataFrame | None = None
    csv_path: str | None = None
    html_path: str | None = None


# =========================
# Configuración de salida
# =========================
NDIGITS = 4
SCI_COLS = ["N_cm2", "N_err_cm2"]


# =========================
# Constantes físicas (SI)
# =========================
h = 6.62607015e-34
k_B = 1.380649e-23
c = 299792458.0


# =========================
# Columnas esperadas del input
# =========================
ORIG_COLS = [
    "species_id", "moleculeTag", "linelist", "name", "chemical_name", "orderedfreq",
    "ν_obs_MHz", "Δν_MHz", "lower_state_energy", "lower_state_energy_K",
    "upper_state_energy", "upper_state_energy_K", "sijmu2", "sij", "aij",
    "upperStateDegen", "T_A [K]", "Δv [Km/s]", "σ_Δv [Km/s]",
    "IntInt [K*Km/s]", "σ_IntInt [K*Km/s]", "Q_source"
]

PAIR_COLS_OUT = [
    "species_label", "chemical_name", "Tex_K",
    "pair_kind", "pair_status", "isotope_pair",
    "abundance_ratio_used", "iso_ratio", "r_tau", "R_factor",
    "target_line_id", "target_name", "ref_line_id", "ref_name",
    "Tmb_ref_K", "Tmb_target_K", "nu_target_MHz", "nu_ref_MHz",
    "Ju_target", "Ju_ref", "Jl_target", "Jl_ref",
    "B_target_Hz", "B_ref_Hz", "EJ_target_over_k_K", "EJ_ref_over_k_K",
    "Aul_target_used", "Aul_ref_used", "Aul_source_target", "Aul_source_ref",
    "tau_target", "tau_status", "Delta_v_target_kms", "sigma_Delta_v_target_kms",
    "Q_col_used", "Q_value_used", "N_cm2", "N_err_cm2",
    "N_status", "N_status_detail", "r_mode", "note"
]


# =========================
# Utilidades generales
# =========================
def ensure_dir(path: Path | str) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_name(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"[^\w.-]+", "_", value)
    value = value.strip("._-")
    return value or "resultados_mth"


def _round_numeric(df: pd.DataFrame, ndigits: int = 4, coerce_object: bool = False) -> pd.DataFrame:
    out = df.copy()
    if coerce_object:
        for c in out.select_dtypes(include=["object"]).columns:
            conv = pd.to_numeric(out[c], errors="ignore")
            if pd.api.types.is_numeric_dtype(conv):
                out[c] = conv

    num_cols = out.select_dtypes(include=[np.number]).columns
    if len(num_cols):
        out[num_cols] = out[num_cols].round(ndigits)
        eps = 0.5 * 10 ** (-ndigits)
        mask = out[num_cols].abs() < eps
        out.loc[:, num_cols] = out[num_cols].where(~mask, 0.0)

    return out


def _save_df_both(
    df: pd.DataFrame,
    out_path_without_ext: str,
    *,
    ndigits: int = 4,
    index: bool = False,
    csv_encoding: str = "utf-8",
    html_title: str | None = None,
    html_caption: str | None = None,
    sci_cols: list[str] | None = None,
) -> tuple[str, str]:
    sci_cols = sci_cols or []
    out_dir = os.path.dirname(out_path_without_ext) or "."
    os.makedirs(out_dir, exist_ok=True)

    df_ = _round_numeric(df, ndigits=ndigits)

    df_csv = df_.copy()
    for name in sci_cols:
        if name in df_csv.columns:
            df_csv[name] = (
                df_csv[name].applymap(lambda x: f"{x:.{ndigits}E}" if pd.notnull(x) else "")
                if isinstance(df_csv[name], pd.DataFrame)
                else df_csv[name].apply(lambda x: f"{x:.{ndigits}E}" if pd.notnull(x) else "")
            )

    csv_path = f"{out_path_without_ext}.csv"
    df_csv.to_csv(csv_path, index=index, encoding=csv_encoding)

    formatters = []
    for i, name in enumerate(df_.columns):
        col_series = df_.iloc[:, i]
        if pd.api.types.is_numeric_dtype(col_series):
            if name in sci_cols:
                fmt = (lambda x, nd=ndigits: "" if pd.isna(x) else f"{float(x):.{nd}E}")
            else:
                fmt = (lambda x, nd=ndigits: "" if pd.isna(x) else f"{float(x):.{nd}f}")
        else:
            fmt = (lambda x: "" if pd.isna(x) else str(x))
        formatters.append(fmt)

    table_html = df_.to_html(
        index=index,
        border=0,
        escape=False,
        na_rep="",
        formatters=formatters,
    )

    html_path = f"{out_path_without_ext}.html"
    title = (html_title or os.path.basename(out_path_without_ext)).replace("<", "&lt;").replace(">", "&gt;")
    html_doc = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{title}</title>"
        "<style>"
        "table{border-collapse:collapse;font-family:Inter,Roboto,Arial,sans-serif;font-size:13px}"
        "thead th{position:sticky;top:0;background:#fafafa;border-bottom:1px solid #ddd}"
        "td,th{padding:6px 8px;border-bottom:1px solid #f0f0f0;text-align:right}"
        "tbody tr:nth-child(even){background:#fcfcff}"
        "</style>"
        "</head><body style='margin:16px'>"
    )
    if html_caption:
        html_doc += (
            "<h3 style='margin:0 0 12px 0;font-family:Inter,Roboto,Arial,sans-serif;font-weight:600'>"
            f"{html_caption}</h3>"
        )
    html_doc += table_html
    html_doc += "</body></html>"

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_doc)

    return csv_path, html_path


def safe_float(x):
    try:
        if isinstance(x, str):
            x = x.strip().replace(",", "")
            if x.lower() in ("cdms", "jpl", "none", "nan", ""):
                return np.nan
        return float(x)
    except Exception:
        return np.nan


# =========================
# Parseo cuántico
# =========================
J_PATTERN = re.compile(r"J\s*=\s*(\d+)\s*[-–]\s*(\d+)", re.IGNORECASE)


def parse_J_from_name(name: str):
    if not isinstance(name, str):
        return None, None
    m = J_PATTERN.search(name)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def infer_Jl_from_degeneracy(upperStateDegen, name=None):
    note = None
    Ju = None
    Jl = None
    try:
        if upperStateDegen is not None and pd.notna(upperStateDegen):
            Ju_est = (float(upperStateDegen) - 1.0) / 2.0
            Ju_name, Jl_name = parse_J_from_name(name) if name else (None, None)
            if Ju_name is not None and Jl_name is not None:
                return Ju_name, Jl_name, note
            Jl_est = Ju_est - 1.0
            if Jl_est < 0:
                note = (note or "") + "[Jl<0 from degeneracy fallback]"
                Jl_est = None
            Ju = int(Ju_est) if float(Ju_est).is_integer() else Ju_est
            Jl = int(Jl_est) if (Jl_est is not None and float(Jl_est).is_integer()) else Jl_est
        else:
            note = (note or "") + "[No upperStateDegen to infer Ju/Jl]"
    except Exception as e:
        note = (note or "") + f"[infer_Jl_error:{e}]"
    return Ju, Jl, note


def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _find_col(df: pd.DataFrame, candidates):
    lowmap = {str(c).lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lowmap:
            return lowmap[cand.lower()]
    return None


def _coerce_B_to_Hz(series: pd.Series, is_mhz: bool) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    return s * 1e6 if is_mhz else s


def load_B_catalogs(path_jpl, path_cdms):
    jpl = pd.read_csv(path_jpl)
    cdms = pd.read_csv(path_cdms)

    jpl = _normalize_cols(jpl)
    cdms = _normalize_cols(cdms)

    key_candidates = [
        "moleculeTag",
        "moleculetag",
        "tag",
        "species tag",
        "species_tag",
        "molecule_tag",
    ]

    jpl_key = _find_col(jpl, key_candidates)
    cdms_key = _find_col(cdms, key_candidates)

    if jpl_key is None:
        raise KeyError(f"En {path_jpl} no encontré columna clave. Columnas: {list(jpl.columns)}")
    if cdms_key is None:
        raise KeyError(f"En {path_cdms} no encontré columna clave. Columnas: {list(cdms.columns)}")

    b_hz = ["B", "B_Hz", "B(Hz)", "B[Hz]"]
    b_mhz = ["B_MHz", "B(MHz)", "B[MHz]"]

    jpl_B_hz = _find_col(jpl, b_hz)
    jpl_B_mhz = _find_col(jpl, b_mhz)
    cdms_B_hz = _find_col(cdms, b_hz)
    cdms_B_mhz = _find_col(cdms, b_mhz)

    if jpl_B_hz is None and jpl_B_mhz is None:
        raise KeyError(f"En {path_jpl} no encontré columna B.")
    if cdms_B_hz is None and cdms_B_mhz is None:
        raise KeyError(f"En {path_cdms} no encontré columna B.")

    jpl["B_Hz_unified"] = _coerce_B_to_Hz(
        jpl[jpl_B_hz] if jpl_B_hz else jpl[jpl_B_mhz],
        is_mhz=(jpl_B_hz is None),
    )

    cdms["B_Hz_unified"] = _coerce_B_to_Hz(
        cdms[cdms_B_hz] if cdms_B_hz else cdms[cdms_B_mhz],
        is_mhz=(cdms_B_hz is None),
    )

    return jpl, cdms, jpl_key, cdms_key


def get_B_Hz_for_line(linelist, moleculeTag, jpl_df, cdms_df, jpl_key, cdms_key):
    if pd.isna(moleculeTag):
        raise KeyError("moleculeTag/Tag es NaN")

    linelist_str = str(linelist).strip().upper()

    if linelist_str == "JPL":
        sub = jpl_df[jpl_df[jpl_key] == moleculeTag]
        if sub.empty:
            sub = jpl_df[jpl_df[jpl_key].astype(str) == str(moleculeTag)]
        if sub.empty:
            raise KeyError(f"Tag '{moleculeTag}' no encontrado en JPL ({jpl_key}).")

        B = sub["B_Hz_unified"].iloc[0]
        if pd.isna(B):
            raise KeyError(f"B vacío para tag '{moleculeTag}' en JPL.")
        return float(B)

    if linelist_str == "CDMS":
        sub = cdms_df[cdms_df[cdms_key] == moleculeTag]
        if sub.empty:
            sub = cdms_df[cdms_df[cdms_key].astype(str) == str(moleculeTag)]
        if sub.empty:
            raise KeyError(f"Tag '{moleculeTag}' no encontrado en CDMS ({cdms_key}).")

        B = sub["B_Hz_unified"].iloc[0]
        if pd.isna(B):
            raise KeyError(f"B vacío para tag '{moleculeTag}' en CDMS.")
        return float(B)

    raise KeyError(f"linelist desconocido: '{linelist}' (esperaba 'JPL' o 'CDMS').")

def EJ_over_k_from_B_and_J(B_Hz, J):
    if B_Hz is None or J is None or pd.isna(B_Hz) or pd.isna(J):
        return np.nan
    return (h / k_B) * float(B_Hz) * float(J) * (float(J) + 1.0)


def compute_quantum_block(row, jpl_df, cdms_df, jpl_key, cdms_key, prefix="target_"):
    note_add = ""
    name = row.get("name")
    gu = row.get("upperStateDegen")
    linelist = row.get("linelist")
    moleculeTag = row.get("moleculeTag")

    Ju_name, Jl_name = parse_J_from_name(name)
    if Ju_name is not None and Jl_name is not None:
        Ju, Jl = Ju_name, Jl_name
    else:
        Ju, Jl, n2 = infer_Jl_from_degeneracy(gu, name=name)
        if n2:
            note_add += n2

    B_Hz = np.nan
    try:
        B_Hz = get_B_Hz_for_line(
            linelist,
            moleculeTag,
            jpl_df,
            cdms_df,
            jpl_key,
            cdms_key,
        )
    except Exception as e:
        note_add += f"[B_lookup:{e}]"

    EJ_over_k = EJ_over_k_from_B_and_J(B_Hz, Jl)

    return {
        f"{prefix}Ju": Ju,
        f"{prefix}Jl": Jl,
        f"{prefix}B_Hz": B_Hz,
        f"{prefix}EJ_over_k_K": EJ_over_k,
        "note_add": note_add,
    }


def display_species_label(row):
    lab = row.get("name")
    if isinstance(lab, str) and lab.strip():
        return lab.strip()
    lab = row.get("chemical_name")
    return lab if isinstance(lab, str) and lab.strip() else "unknown"


# =========================
# Física Sanhueza
# =========================
def normalize_Aul(aij_value):
    v = safe_float(aij_value)
    if pd.isna(v):
        return np.nan, "missing"
    if -50.0 < v < 0.0:
        return 10.0 ** v, "log10->linear"
    if v > 0.0:
        return v, "linear"
    return np.nan, "missing"


def pick_Q_from_row(tex, row):
    """
    Selecciona Q(T) de forma dinámica a partir de las columnas disponibles.

    Prioridad:
    1. Usar Q_{Tex}K si existe en el CSV.
    2. Interpolar entre columnas Q_*K si Tex cae entre dos temperaturas disponibles.
    3. Usar Q_source como respaldo.
    4. Usar la Q_*K más cercana como último respaldo.
    5. Si no hay nada útil, devolver NaN.
    """

    tex = safe_float(tex)

    if pd.isna(tex) or tex <= 0:
        return np.nan, "Q=NaN[no Tex]"

    q_points = {}

    # Buscar columnas tipo Q_10K, Q_28K, Q_30K, Q_60K, etc.
    for col in row.index:
        col_str = str(col).strip()

        m = re.fullmatch(r"Q_([0-9]+(?:\.[0-9]+)?)K", col_str)
        if not m:
            continue

        temp_q = safe_float(m.group(1))
        q_val = safe_float(row.get(col))

        if pd.notna(temp_q) and pd.notna(q_val):
            q_points[float(temp_q)] = (float(q_val), col_str)

    temps = sorted(q_points.keys())

    # 1. Coincidencia directa o casi directa
    # Ejemplo: Tex=30 usa Q_30K.
    for t in temps:
        if abs(tex - t) <= 1.0:
            q_val, q_col = q_points[t]
            return q_val, q_col

    # 2. Interpolación lineal entre dos Q disponibles
    # Ejemplo: Tex=40 y existen Q_30K y Q_60K.
    for t1, t2 in zip(temps[:-1], temps[1:]):
        if t1 < tex < t2:
            q1, c1 = q_points[t1]
            q2, c2 = q_points[t2]

            q_interp = q1 + (q2 - q1) * (tex - t1) / (t2 - t1)
            return q_interp, f"Q_interp_{c1}_{c2}"

    # 3. Respaldo con Q_source
    qsrc_val = safe_float(row.get("Q_source"))
    if pd.notna(qsrc_val):
        return qsrc_val, "Q_source_fallback"

    # 4. Último respaldo: Q más cercana
    if temps:
        nearest_t = min(temps, key=lambda t: abs(t - tex))
        q_val, q_col = q_points[nearest_t]
        return q_val, f"{q_col}_nearest_fallback"

    return np.nan, "Q=NaN[no Q available]"


def _norm_species_text(text: str) -> str:
    if text is None or pd.isna(text):
        return ""
    s = str(text).strip().upper()
    s = s.replace(" ", "")
    return s


def _canonical_special_species_name(text: str) -> str:
    """
    Normaliza nombres/fórmulas usados para detectar casos hiperfinos especiales.

    Objetivo:
    - CCH, C2H y Ethynyl deben mapear a C2H.
    - N2H+, N2H y Diazenylium deben mapear a N2H+.
    """
    s = _norm_species_text(text)

    # Limpiar caracteres que pueden venir de catálogos o nombres largos.
    s_clean = re.sub(r"[^A-Z0-9+]", "", s)

    aliases = {
        # C2H / CCH
        "CCH": "C2H",
        "C2H": "C2H",
        "ETHYNYL": "C2H",
        "ETHYNYLRADICAL": "C2H",

        # N2H+
        "N2H+": "N2H+",
        "N2H": "N2H+",
        "DIAZENYLIUM": "N2H+",
        "DIAZENYLIUMION": "N2H+",
    }

    return aliases.get(s_clean, s_clean)


def _is_n2hp(chemical_name: str) -> bool:
    return _canonical_special_species_name(chemical_name) == "N2H+"


def _is_c2h(chemical_name: str) -> bool:
    return _canonical_special_species_name(chemical_name) == "C2H"

# =========================
# Clasificación física de pares Sanhueza
# =========================
# Estos valores son EDITABLES. La clave representa el isotopólogo raro detectado.
# IMPORTANTE:
# - "13C" significa usar 12C/13C
# - "15N" significa usar 14N/15N
# - "18O" significa usar 16O/18O
# - "17O" significa usar 16O/17O
# - "34S" significa usar 32S/34S
# - "33S" significa usar 32S/33S
@dataclass
class PairClassification:
    valid: bool
    pair_kind: str
    pair_status: str
    isotope_pair: str | None = None
    abundance_ratio: float | None = None
    reason: str = ""


def _best_species_label_for_pair(row) -> str:
    """
    Devuelve el texto más útil para detectar isotopólogos.
    Preferimos 'name' porque suele contener cosas como HCN, HC-13-N, HCN-15, etc.
    También agregamos chemical_name por seguridad.
    """
    parts = []
    for col in ("name", "chemical_name"):
        val = row.get(col)
        if val is not None and not pd.isna(val):
            txt = str(val).strip()
            if txt:
                parts.append(txt)
    return " ".join(parts)


def _clean_species_string(text: str) -> str:
    """
    Limpia etiquetas espectroscópicas que estorban:
    - espacios
    - comas
    - estados vibracionales v=0, v2=1, etc.
    - texto tipo recommended, wHFS
    """
    s = str(text or "").upper()
    s = s.replace(" ", "")
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r",?V\d*\s*=\s*\d+", "", s)
    s = re.sub(r",?V\d+\s*", "", s)
    s = re.sub(r",?NU\d+\s*", "", s)
    s = re.sub(r",?VT\s*=\s*\d+(-\d+)?", "", s)
    s = re.sub(r";.*$", "", s)
    s = s.replace("RECOMMENDED", "")
    s = s.replace("WHFS", "")
    return s


def _canonicalize_isotope_notation(text: str) -> str:
    """
    Convierte notaciones comunes de catálogos a una forma uniforme:
    C-13 -> 13C
    N-15 -> 15N
    O-18 -> 18O
    S-34 -> 34S
    HC-13-O+ -> H13CO+
    HCN-15 -> HC15N, de forma aproximada para detección.
    """
    s = _clean_species_string(text)

    # Formas tipo C-13, N-15, O-18, S-34, Si-29
    repl = {
        "C-13": "13C",
        "N-15": "15N",
        "O-18": "18O",
        "O-17": "17O",
        "S-34": "34S",
        "S-33": "33S",
        "SI-29": "29SI",
        "SI-30": "30SI",
    }

    for old, new in repl.items():
        s = s.replace(old, new)

    # Casos frecuentes escritos al final: HCN-15 -> HC15N
    # Solo lo hacemos para patrones muy comunes.
    s = s.replace("HCN15", "HC15N")
    s = s.replace("HCN-15", "HC15N")

    return s


def _detect_isotopes(text: str) -> list[str]:
    """
    Detecta isotopólogos raros relevantes.
    Devuelve claves como: 13C, 15N, 18O, 17O, 34S, 33S.
    """
    s = _canonicalize_isotope_notation(text)

    found = []

    patterns = {
        "13C": [r"13C"],
        "15N": [r"15N"],
        "18O": [r"18O"],
        "17O": [r"17O"],
        "34S": [r"34S"],
        "33S": [r"33S"],
        "29SI": [r"29SI"],
        "30SI": [r"30SI"],
    }

    for isotope_key, pats in patterns.items():
        for pat in pats:
            if re.search(pat, s):
                found.append(isotope_key)
                break

    # Quitar duplicados manteniendo orden
    out = []
    for x in found:
        if x not in out:
            out.append(x)

    return out


def _base_formula_without_isotopes(text: str) -> str:
    """
    Construye una fórmula base aproximada quitando masas isotópicas.
    Ejemplos:
    H13CN  -> HCN
    HC15N  -> HCN
    HC18O+ -> HCO+
    C34S   -> CS
    """
    s = _canonicalize_isotope_notation(text)

    replacements = {
        "13C": "C",
        "15N": "N",
        "18O": "O",
        "17O": "O",
        "34S": "S",
        "33S": "S",
        "29SI": "SI",
        "30SI": "SI",
    }

    for old, new in replacements.items():
        s = s.replace(old, new)

    # Quitar separadores residuales y etiquetas sobrantes
    s = re.sub(r"[^A-Z0-9+]", "", s)

    # Normalizaciones útiles
    s = s.replace("CCH", "C2H")

    return s


def _is_main_species(row) -> bool:
    label = _best_species_label_for_pair(row)
    return len(_detect_isotopes(label)) == 0


def _is_simple_isotopologue(row) -> bool:
    label = _best_species_label_for_pair(row)
    return len(_detect_isotopes(label)) == 1


def classify_sanhueza_pair(
    target_row,
    ref_row,
    chemical_name=None,
    isotopic_ratios: dict[str, float] | None = None,
) -> PairClassification:
    """
    Clasifica si el par target/ref puede entrar al método Sanhueza.

    Convención usada por tu código:
    - target = especie principal cuya tau se quiere obtener.
    - ref    = línea de referencia, isotopólogo o componente hiperfina más débil.
    - solve_tau_ratio usa Tref/Ttarget = (1-exp(-tau/r))/(1-exp(-tau)).

    Reglas:
    1. C2H y N2H+ se aceptan como hiperfinas con r fijo.
    2. Para otros casos:
       - target debe ser especie principal.
       - ref debe ser isotopólogo simple.
       - ambos deben tener la misma fórmula base.
       - pares invertidos se excluyen.
       - pares raro/raro se excluyen.
    """

    ratios = dict(DEFAULT_ISOTOPIC_ABUNDANCE_RATIOS)
    if isotopic_ratios:
        ratios.update(isotopic_ratios)

    chem = _canonical_special_species_name(chemical_name)

    target_label = _best_species_label_for_pair(target_row)
    ref_label = _best_species_label_for_pair(ref_row)

    target_isotopes = _detect_isotopes(target_label)
    ref_isotopes = _detect_isotopes(ref_label)

    target_base = _canonical_special_species_name(
        _base_formula_without_isotopes(target_label)
    )
    ref_base = _canonical_special_species_name(
        _base_formula_without_isotopes(ref_label)
    )

    # Caso especial: hiperfinas de la misma molécula.
    # Aquí NO necesitamos isotopólogo. Deben aceptarse pares CCH/CCH o N2H+/N2H+
    # siempre que is_pair_compatible ya haya confirmado que no son la misma línea exacta.
    if chem == "C2H" or (target_base == "C2H" and ref_base == "C2H"):
        return PairClassification(
            valid=True,
            pair_kind="hyperfine_fixed",
            pair_status="valid_hyperfine_c2h",
            isotope_pair=None,
            abundance_ratio=None,
            reason="C2H/CCH usa r fijo = 2",
        )

    if chem == "N2H+" or (target_base == "N2H+" and ref_base == "N2H+"):
        return PairClassification(
            valid=True,
            pair_kind="hyperfine_fixed",
            pair_status="valid_hyperfine_n2hp",
            isotope_pair=None,
            abundance_ratio=None,
            reason="N2H+ usa r fijo = 5/3",
        )

    # Si el target ya es raro, es par invertido o raro/raro.
    if target_isotopes and not ref_isotopes:
        return PairClassification(
            valid=False,
            pair_kind="reversed_pair",
            pair_status="invalid_isotopologue_to_main",
            isotope_pair=None,
            abundance_ratio=None,
            reason=f"Target parece isotopólogo ({target_isotopes}) y ref parece principal.",
        )

    if target_isotopes and ref_isotopes:
        return PairClassification(
            valid=False,
            pair_kind="rare_to_rare",
            pair_status="invalid_rare_to_rare",
            isotope_pair=None,
            abundance_ratio=None,
            reason=f"Ambas líneas parecen isotopólogos: target={target_isotopes}, ref={ref_isotopes}.",
        )

    # Si ambos son principales y no son C2H/N2H+, no hay razón de profundidades ópticas definida.
    if not target_isotopes and not ref_isotopes:
        return PairClassification(
            valid=False,
            pair_kind="main_to_main",
            pair_status="invalid_no_isotopologue_or_hyperfine_ratio",
            isotope_pair=None,
            abundance_ratio=None,
            reason="Ambas líneas parecen especie principal; no hay isotopólogo ni r hiperfino definido.",
        )

    # Aquí target es principal y ref tiene isotopólogo(s).
    if len(ref_isotopes) != 1:
        return PairClassification(
            valid=False,
            pair_kind="multi_isotopologue",
            pair_status="invalid_multiple_isotopic_substitutions",
            isotope_pair=None,
            abundance_ratio=None,
            reason=f"Ref tiene más de una sustitución isotópica: {ref_isotopes}.",
        )

    isotope_key = ref_isotopes[0]

    # Deben representar la misma molécula base.
    if target_base != ref_base:
        return PairClassification(
            valid=False,
            pair_kind="unrelated_or_mismatched_base",
            pair_status="invalid_different_base_formula",
            isotope_pair=isotope_key,
            abundance_ratio=None,
            reason=f"Fórmulas base distintas: target={target_base}, ref={ref_base}.",
        )

    if isotope_key not in ratios:
        return PairClassification(
            valid=False,
            pair_kind="unknown_isotope_ratio",
            pair_status="invalid_missing_isotopic_ratio",
            isotope_pair=isotope_key,
            abundance_ratio=None,
            reason=f"No hay razón isotópica configurada para {isotope_key}.",
        )

    return PairClassification(
        valid=True,
        pair_kind="main_to_isotopologue",
        pair_status="valid_main_to_simple_isotopologue",
        isotope_pair=isotope_key,
        abundance_ratio=float(ratios[isotope_key]),
        reason=f"Par válido principal/isotopólogo usando razón {isotope_key}.",
    )


def compute_r(
    tex_K,
    iso_ratio,
    B_ref_Hz,
    B_target_Hz,
    EJ_ref_over_k_K,
    EJ_target_over_k_K,
    nu_ref_Hz,
    nu_target_Hz,
    chemical_name=None,
    use_r_fixed=False,
):
    """
    Calcula r = tau_target / tau_ref.

    Convención:
    - target = especie principal o componente fuerte.
    - ref    = isotopólogo o componente débil.
    - iso_ratio = [main]/[iso] correspondiente al isótopo detectado.

    Casos:
    1. C2H y N2H+ usan r fijo hiperfino.
    2. Si use_r_fixed=True, para isotopólogos se usa directamente iso_ratio
       como aproximación de r.
    3. Si use_r_fixed=False, para isotopólogos se calcula r con la ecuación extendida.
    4. Si faltan parámetros para la ecuación extendida, se usa iso_ratio
       del par detectado como aproximación interna.
    """

    chem = _norm_species_text(chemical_name)

    # 1. Casos hiperfinos conocidos: estos SIEMPRE tienen prioridad.
    if _is_n2hp(chem):
        return 5.0 / 3.0

    if _is_c2h(chem):
        return 2.0

    # 2. Aproximación de r:
    # Aquí iso_ratio ya NO debe ser un valor global de la GUI.
    # Debe ser la razón interna correspondiente al isótopo detectado:
    # 13C, 15N, 18O, etc.
    if use_r_fixed:
        return float(iso_ratio)

    # 3. Intentar fórmula isotopóloga extendida
    vals = [
        tex_K,
        iso_ratio,
        B_ref_Hz,
        B_target_Hz,
        EJ_ref_over_k_K,
        EJ_target_over_k_K,
        nu_ref_Hz,
        nu_target_Hz,
    ]

    # Si falta información, usamos la razón isotópica interna del par
    # como aproximación de r, no un valor global arbitrario.
    if any(v is None or pd.isna(v) for v in vals):
        return float(iso_ratio)

    tex_K = float(tex_K)
    iso_ratio = float(iso_ratio)
    B_ref_Hz = float(B_ref_Hz)
    B_target_Hz = float(B_target_Hz)
    EJ_ref_over_k_K = float(EJ_ref_over_k_K)
    EJ_target_over_k_K = float(EJ_target_over_k_K)
    nu_ref_Hz = float(nu_ref_Hz)
    nu_target_Hz = float(nu_target_Hz)

    if (
        tex_K <= 0
        or B_ref_Hz <= 0
        or B_target_Hz <= 0
        or nu_ref_Hz <= 0
        or nu_target_Hz <= 0
        or iso_ratio <= 0
    ):
        return float(iso_ratio)

    try:
        term_rot = (
            ((k_B * tex_K) / (h * B_ref_Hz) + 1.0 / 3.0)
            / ((k_B * tex_K) / (h * B_target_Hz) + 1.0 / 3.0)
        )

        term_E = math.exp(EJ_ref_over_k_K / tex_K) / math.exp(EJ_target_over_k_K / tex_K)

        term_nu = (
            1.0 - math.exp(-(h * nu_target_Hz) / (k_B * tex_K))
        ) / (
            1.0 - math.exp(-(h * nu_ref_Hz) / (k_B * tex_K))
        )

        r = iso_ratio * term_rot * term_E * term_nu

        if not np.isfinite(r) or r <= 0:
            return float(iso_ratio)

        return float(r)

    except Exception:
        return float(iso_ratio)

def describe_r_mode(
    tex_K,
    iso_ratio,
    B_ref_Hz,
    B_target_Hz,
    EJ_ref_over_k_K,
    EJ_target_over_k_K,
    nu_ref_Hz,
    nu_target_Hz,
    chemical_name=None,
    use_r_fixed=False,
):
    chem = _norm_species_text(chemical_name)

    if _is_n2hp(chem):
        return "hyperfine_fixed_n2hp"

    if _is_c2h(chem):
        return "hyperfine_fixed_c2h"

    if use_r_fixed:
        return "approx_r_from_internal_isotopic_ratio"

    vals = [
        tex_K,
        iso_ratio,
        B_ref_Hz,
        B_target_Hz,
        EJ_ref_over_k_K,
        EJ_target_over_k_K,
        nu_ref_Hz,
        nu_target_Hz,
    ]

    if any(v is None or pd.isna(v) for v in vals):
        return "fallback_internal_isotopic_ratio_missing_params"

    if (
        float(tex_K) <= 0
        or float(iso_ratio) <= 0
        or float(B_ref_Hz) <= 0
        or float(B_target_Hz) <= 0
        or float(nu_ref_Hz) <= 0
        or float(nu_target_Hz) <= 0
    ):
        return "fallback_internal_isotopic_ratio_nonphysical_params"

    return "isotopologue_formula"

def solve_tau_ratio(Tref, Ttarget, r, max_iter=200, tol=1e-6):
    if Ttarget is None or Tref is None or pd.isna(Ttarget) or pd.isna(Tref):
        return np.nan, "[Missing Tmb]"
    if Ttarget <= 0 or Tref <= 0:
        return np.nan, "[Non-positive Tmb]"

    ratio = Tref / Ttarget
    low_bound = 1.0 / max(r, 1e-12)
    if not (low_bound < ratio < 1.0):
        return np.nan, f"[No physical root: ratio={ratio:.3g}, requires {low_bound:.3g}<ratio<1]"

    a, b = 1e-9, 100.0

    def f(tau):
        num = 1.0 - math.exp(-tau / float(r))
        den = 1.0 - math.exp(-tau)
        if den <= 0:
            return 1e9
        return (num / den) - ratio

    fa = f(a)
    fb = f(b)
    expand_count = 0
    while fa * fb > 0 and expand_count < 10:
        b *= 2.0
        fb = f(b)
        expand_count += 1

    if fa * fb > 0:
        return np.nan, "[Bisection failed to bracket root]"

    for _ in range(max_iter):
        m = 0.5 * (a + b)
        fm = f(m)
        if abs(fm) < tol:
            return m, ""
        if fa * fm < 0:
            b, fb = m, fm
        else:
            a, fa = m, fm

    return m, "[Max iters reached; approximate root]"


def check_inputs_for_N(tex_K, nu_Hz, gu, Aul_linear, El_over_k, tau, dv_kms, R_factor, Q_val):
    missing = []
    nonphys = []

    def _nan(x):
        return (x is None) or pd.isna(x)

    if _nan(tex_K):
        missing.append("Tex_K")
    if _nan(nu_Hz):
        missing.append("nu_Hz")
    if _nan(gu):
        missing.append("g_u")
    if _nan(Aul_linear):
        missing.append("A_ul")
    if _nan(El_over_k):
        missing.append("El_over_k")
    if _nan(tau):
        missing.append("tau")
    if _nan(dv_kms):
        missing.append("Delta_v")
    if _nan(Q_val):
        missing.append("Q(T)")

    if not missing:
        if tex_K <= 0:
            nonphys.append("Tex_K<=0")
        if nu_Hz <= 0:
            nonphys.append("nu_Hz<=0")
        if gu <= 0:
            nonphys.append("g_u<=0")
        if Aul_linear <= 0:
            nonphys.append("A_ul<=0")
        if R_factor <= 0:
            nonphys.append("R_factor<=0")

    if missing:
        return "missing inputs", ", ".join(missing)
    if nonphys:
        return "non-physical parameter", ", ".join(nonphys)
    return "OK", ""


def compute_N(tex_K, nu_Hz, gu, Aul_linear, El_over_k, tau, dv_kms, R_factor, Q_val):
    N_status, N_detail = check_inputs_for_N(
        tex_K, nu_Hz, gu, Aul_linear, El_over_k, tau, dv_kms, R_factor, Q_val
    )
    if N_status != "OK":
        return np.nan, f"[N: {N_status}]", N_status, N_detail

    try:
        nu = float(nu_Hz)
        c_cms = c * 1e2
        integ_tau_dv = float(tau) * float(dv_kms) * 1.0e5  # km/s -> cm/s
        term1 = (8.0 * math.pi * (nu ** 3)) / (c_cms ** 3)
        term2 = float(Q_val) / (float(gu) * float(Aul_linear))
        expo = math.exp(float(El_over_k) / float(tex_K))
        denom = (1.0 - math.exp(-(h * nu) / (k_B * float(tex_K))))

        if denom <= 0:
            return np.nan, "[N: denom<=0]", "non-physical parameter", "denom<=0"

        N = (term1 / float(R_factor)) * term2 * (expo / denom) * integ_tau_dv
        return N, "", "OK", ""
    except Exception as e:
        return np.nan, f"[N error:{e}]", "non-physical parameter", f"exception:{e}"


def compute_N_err(N, dv_kms, sigma_dv_kms):
    if any(pd.isna(x) for x in [N, dv_kms, sigma_dv_kms]):
        return np.nan
    if dv_kms <= 0:
        return np.nan
    return float(N) * (float(sigma_dv_kms) / float(dv_kms))

def _safe_text(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _sort_ref_rows(g_valid: pd.DataFrame) -> pd.DataFrame:
    if g_valid is None or g_valid.empty:
        return g_valid

    out = g_valid.copy()

    if "ref_line_id" in out.columns:
        out["__ref_line_sort__"] = pd.to_numeric(out["ref_line_id"], errors="coerce")
    else:
        out["__ref_line_sort__"] = np.nan

    out = out.sort_values(
        by=["__ref_line_sort__", "ref_name"],
        kind="mergesort",
        na_position="last"
    ).drop(columns=["__ref_line_sort__"])

    return out.reset_index(drop=True)


def build_sanhueza_wide_table(pair_df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte la tabla interna por pares en una tabla ancha:
    1 fila = 1 línea objetivo + 1 Tex
    con columnas separadas por cada referencia válida.
    """
    if pair_df is None or pair_df.empty:
        return pd.DataFrame()

    df = pair_df.copy()

    # Asegurar tipos numéricos útiles
    for col in [
        "target_line_id",
        "ref_line_id",
        "Tex_K",
        "nu_target_MHz",
        "Tmb_target_K",
        "Delta_v_target_kms",
        "sigma_Delta_v_target_kms",
        "target_IntInt [K*Km/s]",
        "target_σ_IntInt [K*Km/s]",
        "tau_target",
        "N_cm2",
        "N_err_cm2",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Contar pares probados ANTES de filtrar válidos
    pairs_attempted_map = {}
    if {"target_line_id", "Tex_K"}.issubset(df.columns):
        attempted = (
            df.groupby(["target_line_id", "Tex_K"], dropna=False)
              .size()
              .reset_index(name="n_pares_probados")
        )
        for _, row in attempted.iterrows():
            pairs_attempted_map[(row["target_line_id"], row["Tex_K"])] = int(row["n_pares_probados"])

    # Quedarnos solo con pares físicamente válidos
    if "tau_status" in df.columns:
        df = df[df["tau_status"] == "OK"].copy()

    if "N_status" in df.columns:
        df = df[df["N_status"] == "OK"].copy()

    if "tau_target" in df.columns:
        tau_num = pd.to_numeric(df["tau_target"], errors="coerce")
        df = df[tau_num.notna() & (tau_num > 0)].copy()

    if "N_cm2" in df.columns:
        n_num = pd.to_numeric(df["N_cm2"], errors="coerce")
        df = df[n_num.notna()].copy()

    if df.empty:
        return pd.DataFrame()

    group_keys = ["target_line_id", "Tex_K"]
    wide_rows = []

    for (target_line_id, tex_k), g in df.groupby(group_keys, dropna=False):
        g = _sort_ref_rows(g)

        base = g.iloc[0]

        row = {
            "obs_id": base.get("target_obs_id"),
            "Source": base.get("target_Source"),
            "name": base.get("target_name"),
            "chemical_name": base.get("target_chemical_name"),
            "species_id": base.get("target_species_id"),
            "moleculeTag": base.get("target_moleculeTag"),
            "ν_obs_MHz": base.get("nu_target_MHz"),
            "T_A [K]": base.get("Tmb_target_K"),
            "Δv [Km/s]": base.get("Delta_v_target_kms"),
            "σ_Δv [Km/s]": base.get("sigma_Delta_v_target_kms"),
            "IntInt [K*Km/s]": base.get("target_IntInt [K*Km/s]"),
            "σ_IntInt [K*Km/s]": base.get("target_σ_IntInt [K*Km/s]"),
            "Tex [K]": base.get("Tex_K"),
            "n_refs_validas": int(len(g)),
            "n_pares_probados": pairs_attempted_map.get((target_line_id, tex_k), int(len(g))),
        }

        for idx, (_, ref_row) in enumerate(g.iterrows(), start=1):
            row[f"ref_{idx}_line"] = ref_row.get("ref_line_id")
            row[f"ref_{idx}_name"] = ref_row.get("ref_name")
            row[f"tau_{idx}"] = ref_row.get("tau_target")
            row[f"N_{idx}_cm2"] = ref_row.get("N_cm2")
            row[f"sigma_N_{idx}_cm2"] = ref_row.get("N_err_cm2")

        wide_rows.append(row)

    wide_df = pd.DataFrame(wide_rows)

    # Orden base de columnas
    base_cols = [
        "obs_id",
        "Source",
        "name",
        "chemical_name",
        "species_id",
        "moleculeTag",
        "ν_obs_MHz",
        "T_A [K]",
        "Δv [Km/s]",
        "σ_Δv [Km/s]",
        "IntInt [K*Km/s]",
        "σ_IntInt [K*Km/s]",
        "Tex [K]",
        "n_refs_validas",
        "n_pares_probados",
    ]

    dynamic_cols = [c for c in wide_df.columns if c not in base_cols]

    def _dyn_key(col_name: str):
        m = re.match(r"^(ref|tau|N|sigma_N)_(\d+)", col_name)
        if not m:
            return (999, col_name)

        prefix = m.group(1)
        idx = int(m.group(2))

        prefix_order = {
            "ref": 0,
            "tau": 1,
            "N": 2,
            "sigma_N": 3,
        }

        return (idx, prefix_order.get(prefix, 99), col_name)

    dynamic_cols = sorted(dynamic_cols, key=_dyn_key)
    final_cols = [c for c in base_cols if c in wide_df.columns] + dynamic_cols
    wide_df = wide_df[final_cols].copy()

    for int_col in ["obs_id", "species_id", "moleculeTag"]:
        if int_col in wide_df.columns:
            vals = pd.to_numeric(wide_df[int_col], errors="coerce")
            if vals.notna().any():
                wide_df[int_col] = vals.apply(
                    lambda x: "" if pd.isna(x) else str(int(x))
                )

    return wide_df


def _safe_upper_text(x) -> str:
    if x is None or pd.isna(x):
        return ""
    return str(x).strip().upper()


def is_pair_compatible(target_row, ref_row, chemical_name=None):
    """
    Decide si dos filas pueden probarse como par para el método de
    transiciones hiperfinas.

    Criterio corregido:
    - Permite comparar líneas de la misma molécula.
    - Permite que target_name y ref_name sean iguales.
    - Rechaza únicamente pares que parecen ser la misma línea exacta.
    """

    chem = _safe_upper_text(chemical_name)

    if not chem:
        return False

    # Identificadores observacionales
    obs_t = _safe_text(target_row.get("obs_id"))
    obs_r = _safe_text(ref_row.get("obs_id"))

    # Frecuencias
    nu_t = safe_float(target_row.get("ν_obs_MHz"))
    nu_r = safe_float(ref_row.get("ν_obs_MHz"))

    if pd.isna(nu_t) and pd.notna(target_row.get("orderedfreq")):
        nu_t = safe_float(target_row.get("orderedfreq"))

    if pd.isna(nu_r) and pd.notna(ref_row.get("orderedfreq")):
        nu_r = safe_float(ref_row.get("orderedfreq"))

    # Si tienen obs_id distinto, son filas/líneas distintas:
    # se permite comparar aunque tengan el mismo name.
    if obs_t and obs_r and obs_t != obs_r:
        return True

    # Si no hay obs_id confiable, usamos frecuencia:
    # si la frecuencia es distinta, se permite comparar.
    if pd.notna(nu_t) and pd.notna(nu_r):
        if abs(float(nu_t) - float(nu_r)) > 1e-6:
            return True

    # Si tienen mismo obs_id y misma frecuencia, probablemente son la misma línea.
    return False

# =========================
# Ensamblado de salida
# =========================
def assemble_output_row(
    input_file,
    species_label,
    tex_K,
    iso_ratio,
    r_tau,
    pair_id,
    target_row,
    ref_row,
    qb_target,
    qb_ref,
    Aul_t_used,
    Aul_r_used,
    Aul_src_t,
    Aul_src_r,
    tau,
    tau_status,
    tau_note,
    N_val,
    N_err,
    N_status,
    N_detail,
    Q_used_val,
    Q_used_label,
    R_factor=1.0,
    r_mode=None,
    pair_kind=None,
    pair_status=None,
    isotope_pair=None,
    abundance_ratio_used=None,
):
    out = {}
    out["species_label"] = species_label
    out["chemical_name"] = target_row.get("chemical_name")
    out["Tex_K"] = tex_K
    out["pair_kind"] = pair_kind
    out["pair_status"] = pair_status
    out["isotope_pair"] = isotope_pair
    out["abundance_ratio_used"] = abundance_ratio_used
    out["iso_ratio"] = iso_ratio
    out["r_tau"] = r_tau
    out["R_factor"] = R_factor

    # 🔥 IDENTIDAD REAL (NO TOCAR)
    out["target_obs_id"] = target_row.get("obs_id")
    out["ref_obs_id"] = ref_row.get("obs_id")

    out["target_line_id"] = pair_id[0]
    out["target_name"] = target_row.get("name")
    out["ref_line_id"] = pair_id[1]
    out["ref_name"] = ref_row.get("name")

    Tmb_target = target_row.get("T_A [K]")
    Tmb_ref = ref_row.get("T_A [K]")
    out["Tmb_ref_K"] = Tmb_ref
    out["Tmb_target_K"] = Tmb_target

    nu_t_MHz = target_row.get("ν_obs_MHz")
    nu_r_MHz = ref_row.get("ν_obs_MHz")
    if pd.isna(nu_t_MHz) and pd.notna(target_row.get("orderedfreq")):
        nu_t_MHz = target_row.get("orderedfreq")
    if pd.isna(nu_r_MHz) and pd.notna(ref_row.get("orderedfreq")):
        nu_r_MHz = ref_row.get("orderedfreq")

    out["nu_target_MHz"] = nu_t_MHz
    out["nu_ref_MHz"] = nu_r_MHz

    out["Ju_target"] = qb_target.get("target_Ju")
    out["Ju_ref"] = qb_ref.get("ref_Ju")
    out["Jl_target"] = qb_target.get("target_Jl")
    out["Jl_ref"] = qb_ref.get("ref_Jl")

    out["B_target_Hz"] = qb_target.get("target_B_Hz")
    out["B_ref_Hz"] = qb_ref.get("ref_B_Hz")
    out["EJ_target_over_k_K"] = qb_target.get("target_EJ_over_k_K")
    out["EJ_ref_over_k_K"] = qb_ref.get("ref_EJ_over_k_K")

    out["Aul_target_used"] = Aul_t_used
    out["Aul_ref_used"] = Aul_r_used
    out["Aul_source_target"] = Aul_src_t
    out["Aul_source_ref"] = Aul_src_r

    out["tau_target"] = tau
    out["tau_status"] = tau_status

    dv_kms = target_row.get("Δv [Km/s]")
    sdv_kms = target_row.get("σ_Δv [Km/s]")
    out["Delta_v_target_kms"] = dv_kms
    out["sigma_Delta_v_target_kms"] = sdv_kms

    out["Q_col_used"] = Q_used_label
    out["Q_value_used"] = Q_used_val

    out["N_cm2"] = N_val
    out["N_err_cm2"] = N_err
    out["N_status"] = N_status
    out["N_status_detail"] = N_detail
    out["r_mode"] = r_mode

    out["note"] = (tau_note or "") + (qb_target.get("note_add") or "") + (qb_ref.get("note_add") or "")

    # Columnas originales fijas
    dynamic_orig_cols = list(ORIG_COLS)

    # Agregar automáticamente cualquier columna Q_*K que exista en la entrada,
    # por ejemplo Q_15K, Q_30K, Q_45K, Q_60K, etc.
    for source_row in (target_row, ref_row):
        for col in source_row.index:
            col_str = str(col).strip()

            if re.fullmatch(r"Q_([0-9]+(?:\.[0-9]+)?)K", col_str):
                if col_str not in dynamic_orig_cols:
                    dynamic_orig_cols.append(col_str)

    # También asegurar Q_source si existe
    if "Q_source" not in dynamic_orig_cols:
        dynamic_orig_cols.append("Q_source")

    for c in dynamic_orig_cols:
        out[f"target_{c}"] = target_row.get(c)
        out[f"ref_{c}"] = ref_row.get(c)

    return out


# =========================
# Validación de entrada
# =========================
def validate_input_dataframe(df: pd.DataFrame) -> list[str]:
    required_min = [
        "chemical_name",
        "name",
        "aij",
        "upperStateDegen",
        "T_A [K]",
        "Δv [Km/s]",
        "σ_Δv [Km/s]",
        "lower_state_energy_K",
    ]
    missing = [c for c in required_min if c not in df.columns]
    return missing

def _chemical_group_key(value) -> str:
    """
    Clave robusta para agrupar especies químicas.
    Evita que diferencias como espacios finales o mayúsculas/minúsculas
    separen especies que deberían compararse entre sí.

    Ejemplo:
    'Carbon Monosulfide' y 'Carbon Monosulfide  ' -> 'CARBONMONOSULFIDE'
    """
    if value is None or pd.isna(value):
        return ""

    s = str(value).strip().upper()
    s = re.sub(r"\s+", "", s)
    return s

def run_sanhueza_from_dataframe(
    df: pd.DataFrame,
    Tex_values=[10.0],
    iso_ratio=50.0,
    tau_max=None,
    use_r_fixed=False,
    output_name: str = "column_density_mth",
    save_outputs: bool = True,
    isotopic_ratios: dict[str, float] | None = None,
    progress_callback=None,
) -> SanhuezaResult:
    logs: list[str] = []

    def report(value, message):
        if progress_callback is not None:
            progress_callback(value, message)

    report(3, "Validando las líneas de entrada")
    if df is None or df.empty:
        return SanhuezaResult(
            success=False,
            message="DataFrame vacío",
            logs=["[ERROR] El dataframe de entrada está vacío."],
            dataframe=None,
        )

    df = df.copy().reset_index(drop=True)
    report(10, "Preparando pares espectrales")

    # Normalizar tau_max
    tau_max = safe_float(tau_max)
    if pd.isna(tau_max):
        tau_max = None

    missing = validate_input_dataframe(df)
    if missing:
        return SanhuezaResult(
            success=False,
            message=f"Faltan columnas requeridas: {', '.join(missing)}",
            logs=[f"[ERROR] Faltan columnas requeridas: {', '.join(missing)}"],
            dataframe=None,
        )

    if "line_row_index" not in df.columns:
        df.insert(0, "line_row_index", np.arange(1, len(df) + 1))

    logs.append(f"[INFO] Filas de entrada: {len(df)}")
    logs.append(f"[INFO] Tex usados: {Tex_values}")
    logs.append(f"[INFO] Razón isotópica global de respaldo: {iso_ratio}")
    logs.append(f"[INFO] tau_max: {tau_max}")
    logs.append(f"[INFO] use_r_fixed: {use_r_fixed}")

    ratios_used = dict(DEFAULT_ISOTOPIC_ABUNDANCE_RATIOS)
    if isotopic_ratios:
        ratios_used.update(isotopic_ratios)

    logs.append(f"[INFO] Razones isotópicas configuradas: {ratios_used}")

    report(16, "Cargando constantes rotacionales")
    try:
        jpl_df, cdms_df, jpl_key, cdms_key = load_B_catalogs(JPL_ABC_PATH, CDMS_ABC_PATH)
        logs.append(f"[OK] Catálogos B cargados: JPL={JPL_ABC_PATH}, CDMS={CDMS_ABC_PATH}")
    except Exception as e:
        return SanhuezaResult(
            success=False,
            message=f"No se pudieron cargar los catálogos de constantes rotacionales: {e}",
            logs=logs + [f"[ERROR] No se pudieron cargar los catálogos B: {e}"],
            dataframe=None,
        )

    out_rows = []

    df["__chemical_group_key__"] = df["chemical_name"].apply(_chemical_group_key)
    group_items = list(df.groupby("__chemical_group_key__", dropna=False))

    try:
        group_count = max(1, len(group_items))
        total_pairs = max(
            1,
            sum(max(0, len(group) * (len(group) - 1)) for _, group in group_items),
        )
        processed_pairs = 0
        for group_index, (chem_key, g) in enumerate(group_items):
            g = g.reset_index(drop=True)

            chem_name = g["chemical_name"].dropna().astype(str).iloc[0] if "chemical_name" in g.columns else chem_key
            report(
                22 + int(58 * group_index / group_count),
                f"Evaluando pares de {chem_name}",
            )

            if len(g) < 2:
                logs.append(f"[INFO] Especie omitida por tener <2 líneas: {chem_name}")
                continue

            for i, j in permutations(range(len(g)), 2):
                processed_pairs += 1
                report(
                    22 + int(58 * processed_pairs / total_pairs),
                    f"Evaluando pares de {chem_name}: {processed_pairs} de {total_pairs}",
                )
                target_row = g.iloc[i]
                ref_row = g.iloc[j]

                if not is_pair_compatible(target_row, ref_row, chemical_name=chem_name):
                    continue

                pair_id = (int(target_row["line_row_index"]), int(ref_row["line_row_index"]))

                pair_info = classify_sanhueza_pair(
                    target_row,
                    ref_row,
                    chemical_name=chem_name,
                    isotopic_ratios=ratios_used,
                )

                if not pair_info.valid:
                    logs.append(
                        f"[PAIR_SKIP] chem={chem_name} pair={pair_id[0]}->{pair_id[1]} "
                        f"status={pair_info.pair_status} reason={pair_info.reason}"
                    )
                    continue

                logs.append(
                    f"[PAIR_OK] chem={chem_name} pair={pair_id[0]}->{pair_id[1]} "
                    f"kind={pair_info.pair_kind} status={pair_info.pair_status} "
                    f"isotope={pair_info.isotope_pair} abundance_ratio={pair_info.abundance_ratio}"
                )

                nu_t_MHz = target_row.get("ν_obs_MHz")
                nu_r_MHz = ref_row.get("ν_obs_MHz")

                if pd.isna(nu_t_MHz) and pd.notna(target_row.get("orderedfreq")):
                    nu_t_MHz = target_row.get("orderedfreq")
                if pd.isna(nu_r_MHz) and pd.notna(ref_row.get("orderedfreq")):
                    nu_r_MHz = ref_row.get("orderedfreq")

                nu_t_Hz = float(nu_t_MHz) * 1e6 if pd.notna(nu_t_MHz) else np.nan
                nu_r_Hz = float(nu_r_MHz) * 1e6 if pd.notna(nu_r_MHz) else np.nan

                Tmb_target = safe_float(target_row.get("T_A [K]"))
                Tmb_ref = safe_float(ref_row.get("T_A [K]"))
                dv_kms = safe_float(target_row.get("Δv [Km/s]"))
                sdv_kms = safe_float(target_row.get("σ_Δv [Km/s]"))

                gu_t = safe_float(target_row.get("upperStateDegen"))

                Aul_t_used, Aul_src_t = normalize_Aul(target_row.get("aij"))
                Aul_r_used, Aul_src_r = normalize_Aul(ref_row.get("aij"))

                qb_t = compute_quantum_block(
                    target_row,
                    jpl_df,
                    cdms_df,
                    jpl_key,
                    cdms_key,
                    prefix="target_",
                )

                qb_r = compute_quantum_block(
                    ref_row,
                    jpl_df,
                    cdms_df,
                    jpl_key,
                    cdms_key,
                    prefix="ref_",
                )

                

                for tex in Tex_values:
                    tex = safe_float(tex)
                    if pd.isna(tex) or tex <= 0:
                        continue

                    # Para pares isotopológicos válidos, esta es [main]/[iso]
                    # tomada de las razones internas de sesión.
                    abundance_ratio_for_pair = pair_info.abundance_ratio

                    # Para C2H y N2H+ no se necesita razón isotópica.
                    # compute_r devolverá r fijo hiperfino.
                    if abundance_ratio_for_pair is None or pd.isna(abundance_ratio_for_pair):
                        abundance_ratio_for_pair = 1.0

                    chemical_name_for_r = chem_name

                    if pair_info.pair_status == "valid_hyperfine_c2h":
                        chemical_name_for_r = "C2H"
                    elif pair_info.pair_status == "valid_hyperfine_n2hp":
                        chemical_name_for_r = "N2H+"

                    r_val = compute_r(
                       tex,
                        abundance_ratio_for_pair,
                        qb_r.get("ref_B_Hz"),
                        qb_t.get("target_B_Hz"),
                        qb_r.get("ref_EJ_over_k_K"),
                        qb_t.get("target_EJ_over_k_K"),
                        nu_r_Hz,
                        nu_t_Hz,
                        chemical_name=chemical_name_for_r,
                        use_r_fixed=use_r_fixed,
                    )

                    r_mode = describe_r_mode(
                        tex,
                        abundance_ratio_for_pair,
                        qb_r.get("ref_B_Hz"),
                        qb_t.get("target_B_Hz"),
                        qb_r.get("ref_EJ_over_k_K"),
                        qb_t.get("target_EJ_over_k_K"),
                        nu_r_Hz,
                        nu_t_Hz,
                        chemical_name=chemical_name_for_r,
                        use_r_fixed=use_r_fixed,
                    )

                    logs.append(
                        f"[R_MODE] chem={chem_name} pair={pair_id[0]}->{pair_id[1]} "
                        f"Tex={tex} mode={r_mode} "
                        f"pair_kind={pair_info.pair_kind} "
                        f"isotope_pair={pair_info.isotope_pair} "
                        f"abundance_ratio={abundance_ratio_for_pair} "
                        f"r={r_val:.6g}"
                    )

                    tau, tau_note = solve_tau_ratio(Tmb_ref, Tmb_target, r_val)
                    tau = safe_float(tau)
                    tau_status = "OK" if pd.notna(tau) else "NO_ROOT"

                    # Filtro robusto por tau_max
                    if tau_max is not None and pd.notna(tau):
                        if tau > tau_max:
                            continue

                    Q_val, Q_label = pick_Q_from_row(tex, target_row)

                    El_over_k_target = safe_float(target_row.get("lower_state_energy_K"))
                    EJ_over_k_target = qb_t.get("target_EJ_over_k_K")
                    if pd.isna(El_over_k_target):
                        El_over_k_target = EJ_over_k_target

                    R_factor = 1.0

                    N_val, noteN, N_status, N_detail = compute_N(
                        tex_K=tex,
                        nu_Hz=nu_t_Hz,
                        gu=gu_t,
                        Aul_linear=Aul_t_used,
                        El_over_k=El_over_k_target,
                        tau=tau,
                        dv_kms=dv_kms,
                        R_factor=R_factor,
                        Q_val=Q_val,
                    )

                    if noteN:
                        tau_note = (tau_note or "") + noteN

                    N_err = compute_N_err(N_val, dv_kms, sdv_kms)
                    species_label = display_species_label(target_row)

                    out_rows.append(
                        assemble_output_row(
                            input_file="GUI_dataframe",
                            species_label=species_label,
                            tex_K=tex,
                            iso_ratio=abundance_ratio_for_pair,
                            r_tau=r_val,
                            pair_id=pair_id,
                            target_row=target_row,
                            ref_row=ref_row,
                            qb_target=qb_t,
                            qb_ref=qb_r,
                            Aul_t_used=Aul_t_used,
                            Aul_r_used=Aul_r_used,
                            Aul_src_t=Aul_src_t,
                            Aul_src_r=Aul_src_r,
                            tau=tau,
                            tau_status=tau_status,
                            tau_note=tau_note,
                            N_val=N_val,
                            N_err=N_err,
                            N_status=N_status,
                            N_detail=N_detail,
                            Q_used_val=Q_val,
                            Q_used_label=Q_label,
                            R_factor=R_factor,
                            r_mode=r_mode,
                            pair_kind=pair_info.pair_kind,
                            pair_status=pair_info.pair_status,
                            isotope_pair=pair_info.isotope_pair,
                            abundance_ratio_used=abundance_ratio_for_pair,
                        )
                    )

        if not out_rows:
            return SanhuezaResult(
                success=False,
                message="No se generaron pares válidos para MTH.",
                logs=logs + ["[WARN] No se generaron resultados."],
                dataframe=None,
            )

        report(83, "Organizando pares físicamente válidos")
        out_df = pd.DataFrame(out_rows)

        if out_df.empty:
            return SanhuezaResult(
                success=False,
                message="No se generaron resultados internos para MTH.",
                logs=logs + ["[WARN] La tabla interna quedó vacía."],
                dataframe=None,
            )

        report(88, "Construyendo la tabla comparativa MTH")
        wide_df = build_sanhueza_wide_table(out_df)

        if wide_df is None or wide_df.empty:
            return SanhuezaResult(
                success=False,
                message="No quedaron pares físicamente válidos para construir la tabla final de MTH.",
                logs=logs + ["[WARN] La tabla final de MTH quedó vacía."],
                dataframe=None,
            )

        if "N_err_cm2" in out_df.columns:
            nerr_num = pd.to_numeric(out_df["N_err_cm2"], errors="coerce")
            out_df = out_df[nerr_num.notna()].copy()

        out_df = out_df.reset_index(drop=True)

        if out_df.empty:
            return SanhuezaResult(
                success=False,
                message="No quedaron filas válidas con tau y densidad columnar.",
                logs=logs + ["[WARN] Todas las filas fueron descartadas por no cumplir criterios físicos."],
                dataframe=None,
            )

        front_cols = [c for c in PAIR_COLS_OUT if c in out_df.columns]
        target_pref = [f"target_{c}" for c in ORIG_COLS if f"target_{c}" in out_df.columns]
        ref_pref = [f"ref_{c}" for c in ORIG_COLS if f"ref_{c}" in out_df.columns]
        cols_order = front_cols + target_pref + ref_pref
        other_cols = [c for c in out_df.columns if c not in cols_order]
        cols_order += other_cols
        out_df = out_df[cols_order]

        sort_keys = [k for k in ["target_line_id", "ref_line_id", "Tex_K"] if k in out_df.columns]
        if sort_keys:
            out_df = out_df.sort_values(by=sort_keys, kind="mergesort").reset_index(drop=True)

        csv_path = None
        html_path = None

        if save_outputs:
            out_dir = ensure_dir(SANHUEZA_OUTPUT_DIR)
            base_noext = str(out_dir / sanitize_name(output_name))
            csv_path, html_path = _save_df_both(
                out_df,
                base_noext,
                ndigits=NDIGITS,
                index=False,
                html_title="Resultados de densidad de columna — MTH",
                html_caption=f"Redondeo a {NDIGITS} decimales • Notación científica: {', '.join(SCI_COLS)}",
                sci_cols=SCI_COLS,
            )
            logs.append(f"[OK] CSV guardado: {csv_path}")
            logs.append(f"[OK] HTML guardado: {html_path}")

        logs.append(f"[OK] Resultados generados: {len(out_df)}")

        report(94, "Aplicando formato científico")
        df_gui = _round_numeric(out_df, ndigits=NDIGITS)

        for col in ["N_cm2", "N_err_cm2"]:
            if col in df_gui.columns:
                df_gui[col] = df_gui[col].apply(
                    lambda x: f"{x:.{NDIGITS}E}" if pd.notnull(x) else ""
                )

        df_gui = _round_numeric(wide_df, ndigits=NDIGITS)

        sci_cols_wide = [c for c in df_gui.columns if c.startswith("N_") or c.startswith("sigma_N_")]

        if save_outputs:
            out_dir = ensure_dir(SANHUEZA_OUTPUT_DIR)
            base_name = sanitize_name(output_name)
            out_base = out_dir / base_name

            csv_path, html_path = _save_df_both(
                df_gui,
                str(out_base),
                ndigits=NDIGITS,
                index=False,
                html_title="Resultados de densidad de columna — MTH",
                html_caption=f"Tabla final ancha por línea objetivo • Redondeo a {NDIGITS} decimales",
                sci_cols=sci_cols_wide,
            )

            logs.append(f"[OK] CSV generado: {csv_path}")
            logs.append(f"[OK] HTML generado: {html_path}")
        else:
            csv_path = None
            html_path = None

        for col in df_gui.columns:
            if col.startswith("N_") or col.startswith("sigma_N_"):
                df_gui[col] = df_gui[col].apply(
                    lambda x: f"{x:.{NDIGITS}E}" if pd.notnull(x) else ""
                )

        report(99, "Finalizando MTH")
        return SanhuezaResult(
            success=True,
            message="Proceso MTH completado correctamente.",
            logs=logs + [f"[OK] Tabla final MTH: {len(df_gui)} fila(s)."],
            dataframe=df_gui,
            csv_path=csv_path,
            html_path=html_path,
        )

    except Exception as e:
        logs.append(f"[ERROR] {e}")
        return SanhuezaResult(
            success=False,
            message=str(e),
            logs=logs,
            dataframe=None,
        )
