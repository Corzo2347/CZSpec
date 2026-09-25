from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os
import math

import numpy as np
import pandas as pd

from czspec.paths import VASYUNINA_OUTPUT_DIR


@dataclass
class VasyuninaResult:
    success: bool
    message: str
    logs: list[str] = field(default_factory=list)

    dataframe: Any = None
    csv_path: str | None = None
    html_path: str | None = None


# ==== Constantes ====
h = 6.62607015e-27    # erg*s
kB = 1.380649e-16     # erg/K
c = 2.99792458e10     # cm/s
pi = math.pi
T_BG = 2.725          # K

def ensure_dir(path: Path | str) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_name(value: str) -> str:
    value = (value or "").strip()
    value = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)
    value = value.strip("._-")
    return value or "resultados_mod"


def _round_numeric(df: pd.DataFrame, ndigits: int = 4, coerce_object: bool = False) -> pd.DataFrame:
    out = df.copy()

    if coerce_object:
        obj_cols = out.select_dtypes(include=["object"]).columns
        for c in obj_cols:
            converted = pd.to_numeric(out[c], errors="ignore")
            if pd.api.types.is_numeric_dtype(converted):
                out[c] = converted

    num_cols = out.select_dtypes(include=[np.number]).columns
    if len(num_cols):
        out[num_cols] = out[num_cols].round(ndigits)
        eps = 0.5 * 10 ** (-ndigits)
        for col in num_cols:
            arr = out[col].to_numpy(dtype=float, copy=True)
            arr[np.isfinite(arr) & (np.abs(arr) < eps)] = 0.0
            out[col] = arr

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

    df_rounded = _round_numeric(df, ndigits=ndigits)

    # ---------- CSV ----------
    df_csv = df_rounded.copy()
    for col in sci_cols:
        if col in df_csv.columns:
            numeric_col = pd.to_numeric(df_csv[col], errors="coerce")
            df_csv[col] = numeric_col.apply(
                lambda x: f"{x:.{ndigits}E}" if pd.notnull(x) else ""
            )

    csv_path = f"{out_path_without_ext}.csv"
    df_csv.to_csv(csv_path, index=index, encoding=csv_encoding)

    # ---------- HTML ----------
    def fmt_value(x, col_name):
        if pd.isnull(x):
            return ""

        if col_name in sci_cols:
            x_num = pd.to_numeric(pd.Series([x]), errors="coerce").iloc[0]
            return f"{float(x_num):.{ndigits}E}" if pd.notnull(x_num) else str(x)

        if isinstance(x, (int, float, np.floating)):
            return f"{float(x):.{ndigits}f}"

        return str(x)

    headers = df_rounded.columns.tolist()
    thead = "<tr>" + "".join(f"<th>{col}</th>" for col in headers) + "</tr>"

    body_rows = []
    for _, row in df_rounded.iterrows():
        tds = []
        for col in headers:
            tds.append(f"<td>{fmt_value(row[col], col)}</td>")
        body_rows.append("<tr>" + "".join(tds) + "</tr>")

    table_html = f"""
    <table>
        <thead>{thead}</thead>
        <tbody>
            {''.join(body_rows)}
        </tbody>
    </table>
    """

    html_path = f"{out_path_without_ext}.html"
    title = (html_title or os.path.basename(out_path_without_ext))
    html_doc = f"""<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{title}</title>
    <style>
        table {{
            border-collapse: collapse;
            font-family: Inter, Roboto, Arial, sans-serif;
            font-size: 13px;
            width: 100%;
        }}
        thead th {{
            position: sticky;
            top: 0;
            background: #fafafa;
            border-bottom: 1px solid #ddd;
        }}
        td, th {{
            padding: 6px 8px;
            border-bottom: 1px solid #f0f0f0;
        }}
        tbody tr:nth-child(even) {{
            background-color: #fcfcff;
        }}
        td {{
            text-align: right;
        }}
    </style>
</head>
<body style="margin:16px">
"""
    if html_caption:
        html_doc += f"<h3 style='margin:0 0 12px 0;font-family:Inter,Roboto,Arial,sans-serif;font-weight:600'>{html_caption}</h3>"
    html_doc += table_html
    html_doc += "</body></html>"

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_doc)

    return csv_path, html_path


def J_nu(nu_Hz, T):
    x = (h * nu_Hz) / (kB * T)
    ex = np.exp(x)
    return (h * nu_Hz / kB) / (ex - 1.0)


def first_existing_column(df, candidates):
    for name in candidates:
        if name in df.columns:
            return name
    return None


def coerce_float_series(x):
    s = x.astype(str).str.replace(",", ".", regex=False)
    s = s.str.split("±").str[0]
    return pd.to_numeric(s, errors="coerce")


def parse_value_error(df, value_candidates, error_candidates=None):
    val_col = first_existing_column(df, value_candidates)
    err_col = first_existing_column(df, error_candidates or [])

    if val_col and err_col:
        v = coerce_float_series(df[val_col])
        e = coerce_float_series(df[err_col])
        return v, e

    return pd.Series(np.nan, index=df.index), pd.Series(np.nan, index=df.index)


def run_vasyunina_from_dataframe(
    df_input: pd.DataFrame,
    tex_list: list[float],
    output_name: str,
    ndigits: int = 4,
    save_outputs: bool = True,
    progress_callback=None,
) -> VasyuninaResult:
    logs: list[str] = []

    def report(value, message):
        if progress_callback is not None:
            progress_callback(value, message)

    try:
        report(4, "Validando las columnas de entrada")
        if df_input is None or df_input.empty:
            return VasyuninaResult(
                success=False,
                message="No hay datos de entrada para MOD.",
                logs=["[ERROR] El dataframe de entrada está vacío."],
            )

        df = df_input.copy()
        report(12, "Preparando magnitudes espectroscópicas")

        nu_col = first_existing_column(df, ["ν_obs_MHz", "nu_MHz", "freq_MHz"])
        if nu_col is None:
            return VasyuninaResult(
                success=False,
                message="No se encontró una columna de frecuencia compatible.",
                logs=["[ERROR] Falta columna de frecuencia: ν_obs_MHz / nu_MHz / freq_MHz"],
            )

        A_col = first_existing_column(df, ["aij", "A[s^(-1)]"])
        if A_col is None:
            return VasyuninaResult(
                success=False,
                message="No se encontró una columna de A_ul compatible.",
                logs=["[ERROR] Falta columna A_ul: aij / A[s^(-1)]"],
            )

        g_col = first_existing_column(df, ["upperStateDegen", "g_u"])
        if g_col is None:
            return VasyuninaResult(
                success=False,
                message="No se encontró una columna de degeneración superior.",
                logs=["[ERROR] Falta columna: upperStateDegen / g_u"],
            )

        El_col = first_existing_column(df, ["lower_state_energy_K"])
        if El_col is None:
            return VasyuninaResult(
                success=False,
                message="No se encontró lower_state_energy_K.",
                logs=["[ERROR] Falta columna: lower_state_energy_K"],
            )

        nu_Hz = coerce_float_series(df[nu_col]).to_numpy() * 1e6

        if A_col == "aij":
            A_ul = np.power(10.0, coerce_float_series(df[A_col]).to_numpy())
        else:
            A_ul = coerce_float_series(df[A_col]).to_numpy()

        g_u = coerce_float_series(df[g_col]).to_numpy()
        E_over_k = coerce_float_series(df[El_col]).to_numpy()

        I_val, I_err = parse_value_error(
            df,
            ["IntInt [K*Km/s]", "IntInt[K*Km/s]"],
            ["σ_IntInt [K*Km/s]", "sigma_IntInt"],
        )
        I = I_val.to_numpy()
        dI = I_err.to_numpy()

        logs.append(f"[INFO] Filas recibidas: {len(df)}")
        logs.append(f"[INFO] Temperaturas solicitadas: {tex_list}")

        temperature_count = max(1, len(tex_list))
        for temperature_index, Tex in enumerate(tex_list):
            report(
                22 + int(62 * temperature_index / temperature_count),
                f"Calculando N total para T_ex={Tex:g} K",
            )
            q_col = f"Q_{int(Tex)}K"

            if q_col in df.columns:
                Q_series = coerce_float_series(df[q_col])
            else:
                logs.append(f"[WARN] No existe la columna {q_col}; se llenará con NaN.")
                Q_series = pd.Series(np.nan, index=df.index)

            I_cms = I * 1e5
            dI_cms = dI * 1e5

            J_bg = J_nu(nu_Hz, T_BG)
            J_ex = J_nu(nu_Hz, Tex)

            T1 = (8.0 * pi * (nu_Hz ** 3)) / (c ** 3 * A_ul)
            T2 = 1.0 / g_u
            T3 = 1.0 / (J_ex - J_bg)
            T4 = Q_series.to_numpy() * np.exp(E_over_k / Tex)
            T5 = 1.0 / (1.0 - np.exp(-h * nu_Hz / (kB * Tex)))

            N = T1 * T2 * T3 * T4 * T5 * I_cms
            dN = N * (dI_cms / I_cms)

            df[f"N_tot_{int(Tex)}K_cm2"] = N
            df[f"N_tot_{int(Tex)}K_err_cm2"] = dN

        report(88, "Organizando la tabla de densidades")
        csv_path = None
        html_path = None

        sci_cols = [c for c in df.columns if c.startswith("N_tot_")]

        if save_outputs:
            out_dir = ensure_dir(VASYUNINA_OUTPUT_DIR)
            base_name = sanitize_name(output_name)
            out_base = out_dir / base_name

            csv_path, html_path = _save_df_both(
                df,
                str(out_base),
                ndigits=ndigits,
                index=False,
                html_title="Resultados de densidad de columna — MOD",
                html_caption=f"Redondeo a {ndigits} decimales (científica solo en columnas N_tot)",
                sci_cols=sci_cols,
            )

            logs.append(f"[OK] CSV generado: {csv_path}")
            logs.append(f"[OK] HTML generado: {html_path}")

        report(94, "Aplicando formato científico")
        df_gui = _round_numeric(df, ndigits=ndigits)

        for int_col in ["obs_id", "species_id", "moleculeTag"]:
            if int_col in df_gui.columns:
                vals = pd.to_numeric(df_gui[int_col], errors="coerce")
                if vals.notna().any():
                    df_gui[int_col] = vals.apply(
                        lambda x: "" if pd.isna(x) else str(int(x))
                    )

        # Forzar notación científica en columnas de densidad columnar
        for col in df_gui.columns:
            if col.startswith("N_tot_"):
                df_gui[col] = df_gui[col].apply(
                    lambda x: f"{x:.{ndigits}E}" if pd.notnull(x) else ""
                )

        report(99, "Finalizando MOD")
        return VasyuninaResult(
            success=True,
            message="Proceso MOD completado correctamente.",
            logs=logs,
            dataframe=df_gui,
            csv_path=csv_path,
            html_path=html_path,
        )

    except Exception as e:
        logs.append(f"[ERROR] {e}")
        return VasyuninaResult(
            success=False,
            message=f"Error en MOD: {e}",
            logs=logs,
        )
