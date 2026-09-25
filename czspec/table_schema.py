"""Nombres científicos y ayudas para las columnas mostradas por CZSpec.

Los nombres internos permanecen intactos en los DataFrame y archivos exportados;
esta capa sólo cambia cómo se presentan en la interfaz.
"""

from __future__ import annotations

import re


COLUMN_LABELS = {
    "selected": "Selección",
    "obs_id": "ID de observación",
    "rank": "Posición TOP-K",
    "name": "Especie / transición",
    "chemical_name": "Nombre químico",
    "base_formula": "Fórmula base",
    "linelist": "Catálogo espectroscópico",
    "ν_obs_MHz": "ν observada [MHz]",
    "orderedfreq": "ν de reposo [MHz]",
    "source_vlsr_kms": "VLSR de la fuente [km s⁻¹]",
    "v_line_radio_kms": "Velocidad de la línea [km s⁻¹]",
    "delta_v_lsr_kms": "Δv respecto a VLSR [km s⁻¹]",
    "nu_expected_vlsr_mhz": "ν esperada a VLSR [MHz]",
    "delta_nu_vlsr_mhz": "Δν respecto a VLSR [MHz]",
    "Δν_MHz": "Ventana Δν [MHz]",
    "eu_k": "Eᵤ/k [K]",
    "lower_state_energy_K": "Eₗ/k [K]",
    "aij": "log₁₀(Aᵢⱼ / s⁻¹)",
    "upperStateDegen": "Degeneración superior gᵤ",
    "T_obs_at_fit [K]": "Temperatura pico observada [K]",
    "T_A [K]": "Amplitud pico ajustada [K]",
    "Δv [Km/s]": "FWHM [km s⁻¹]",
    "σ_Δv [Km/s]": "σ(FWHM) [km s⁻¹]",
    "IntInt [K*Km/s]": "∫T dv [K km s⁻¹]",
    "σ_IntInt [K*Km/s]": "σ(∫T dv) [K km s⁻¹]",
    "Line": "ID de línea",
    "Source": "Archivo fuente",
    "Grupo": "Tipo de ajuste",
    "GOI": "Tipo de ajuste",
    "Ajuste": "Perfil ajustado",
    "species_id": "ID de especie (Splatalogue)",
    "moleculeTag": "Etiqueta molecular",
    "Q_source": "Fuente de Q(T)",
    "Q_species_label": "Especie usada para Q(T)",
    "Q_tag_key": "Clave interna de Q(T)",
    "cand_score": "Puntuación del candidato",
    "score_mode": "Modo de identificación",
    "rescue_mode": "Identificación ampliada",
    "Tex [K]": "Tₑₓ [K]",
    "Tex_K": "Tₑₓ [K]",
    "T_ex [K]": "Tₑₓ [K]",
    "N_total [cm^-2]": "N total [cm⁻²]",
    "σ_N_total [cm^-2]": "σ(N total) [cm⁻²]",
    "Q(T)": "Función de partición Q(T)",
    "τ": "Profundidad óptica τ",
    "Método": "Método",
    "Referencia": "Transición de referencia",
    "n_refs_validas": "Referencias válidas",
    "n_pares_probados": "Pares evaluados",
    "Q_species_label__": "Especie usada para Q(T)",
    "source_index__": "Índice de la fila fuente",
    "__czspec_series__": "Serie científica (observación · molécula · método)",
    "__czspec_series_label__": "Rótulo compacto de serie",
}

COLUMN_DESCRIPTIONS = {
    "obs_id": "Identificador de la línea observada dentro del análisis actual.",
    "rank": "Orden del candidato molecular para una misma línea observada.",
    "ν_obs_MHz": "Frecuencia central medida en el espectro observado.",
    "orderedfreq": "Frecuencia de reposo reportada por el catálogo espectroscópico.",
    "source_vlsr_kms": "Velocidad sistémica LSR asociada a la fuente y conservada desde los metadatos de entrada.",
    "v_line_radio_kms": "Velocidad radial de la línea calculada individualmente con la convención Doppler de radio y su propia frecuencia de reposo.",
    "delta_v_lsr_kms": "Diferencia entre la velocidad de la línea identificada y el VLSR de la fuente.",
    "nu_expected_vlsr_mhz": "Frecuencia observada esperada para la transición si estuviera exactamente al VLSR de la fuente.",
    "delta_nu_vlsr_mhz": "Diferencia entre la frecuencia observada medida y la frecuencia esperada al VLSR.",
    "Δν_MHz": "Semiancho de la ventana usada para buscar candidatos.",
    "aij": "Logaritmo decimal del coeficiente de Einstein Aᵢⱼ, en s⁻¹.",
    "upperStateDegen": "Degeneración estadística del nivel superior de la transición.",
    "T_obs_at_fit [K]": "Valor del espectro corregido por línea base evaluado en el centro ajustado; corresponde al marcador de detección mostrado en M1.",
    "T_A [K]": "Amplitud pico del componente matemático ajustado; puede diferir del valor observado por ruido, mezclas o solapamiento de componentes.",
    "Δv [Km/s]": "Ancho completo a media altura de la línea ajustada.",
    "σ_Δv [Km/s]": "Incertidumbre propagada del ancho FWHM.",
    "IntInt [K*Km/s]": "Intensidad integrada de la línea.",
    "σ_IntInt [K*Km/s]": "Incertidumbre propagada de la intensidad integrada.",
}


def column_display_name(column_name: object) -> str:
    """Devuelve un rótulo legible conservando el nombre interno por separado."""

    name = str(column_name)
    if name in COLUMN_LABELS:
        return COLUMN_LABELS[name]

    match = re.fullmatch(r"Q_([0-9]+(?:[._][0-9]+)?)K", name)
    if match:
        return f"Q({match.group(1).replace('_', '.')} K)"

    match = re.fullmatch(r"N_tot_([0-9]+(?:\.[0-9]+)?)K_cm2", name)
    if match:
        return f"N total ({match.group(1)} K) [cm⁻²]"

    match = re.fullmatch(r"N_tot_([0-9]+(?:\.[0-9]+)?)K_err_cm2", name)
    if match:
        return f"σ[N total ({match.group(1)} K)] [cm⁻²]"

    match = re.fullmatch(r"ref_(\d+)_name", name)
    if match:
        return f"Transición de referencia {match.group(1)}"

    match = re.fullmatch(r"tau_(\d+)", name)
    if match:
        return f"Profundidad óptica τ ({match.group(1)})"

    match = re.fullmatch(r"N_(\d+)_cm2", name)
    if match:
        return f"N total ({match.group(1)}) [cm⁻²]"

    match = re.fullmatch(r"sigma_N_(\d+)_cm2", name)
    if match:
        return f"σ[N total ({match.group(1)})] [cm⁻²]"

    return name.replace("__", "").replace("_", " ")


def column_tooltip(column_name: object) -> str:
    name = str(column_name)
    description = COLUMN_DESCRIPTIONS.get(name)
    if description:
        return f"{description}\nCampo interno: {name}"
    return f"Campo interno: {name}"
