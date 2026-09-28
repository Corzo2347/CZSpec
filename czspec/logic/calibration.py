"""Perfiles de calibración/eficiencia para M1.

El objetivo es distinguir una corrección de escala física de una simple
"eficiencia η". Los perfiles automáticos sólo se aplican cuando existe
información suficiente; en caso contrario el factor por defecto es 1.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import math
from typing import Any

from czspec.paths import WORKSPACE_DIR

CUSTOM_PATH = WORKSPACE_DIR / "config" / "calibration_profiles.json"

# Referencia histórica oficial del IRAM 30m. Se conserva como perfil visible,
# NO como verdad universal: archivos .30m modernos pueden aportar BEAM_EFF y
# FORWARD_EFF en su propio header y esos valores tienen prioridad.

# Políticas instrumentales seguras. No todas las instalaciones usan una
# "eficiencia de haz" multiplicativa: para cubos interferométricos calibrados
# en Jy/beam se conserva la escala del producto y se usan BMAJ/BMIN/BPA sólo
# como metadatos del haz sintetizado.
FACILITY_POLICIES = [
    {
        "facility": "IRAM 30m",
        "product_en": "single-dish spectrum",
        "product_es": "espectro de antena única",
        "policy_en": "Prefer header F_eff/B_eff; otherwise use an epoch-appropriate official reference or a documented custom profile.",
        "policy_es": "Priorizar F_eff/B_eff del encabezado; si faltan, usar una referencia oficial apropiada para la época o un perfil personalizado documentado.",
    },
    {
        "facility": "ALMA",
        "product_en": "calibrated FITS cube/image (Jy/beam)",
        "product_es": "cubo/imagen FITS calibrado (Jy/beam)",
        "policy_en": "Do not apply a single-dish beam-efficiency correction; preserve Jy/beam and synthesized-beam metadata.",
        "policy_es": "No aplicar eficiencia de haz de antena única; conservar Jy/beam y los metadatos del haz sintetizado.",
    },
    {
        "facility": "NOEMA",
        "product_en": "calibrated FITS cube/image (Jy/beam)",
        "product_es": "cubo/imagen FITS calibrado (Jy/beam)",
        "policy_en": "Do not apply a single-dish beam-efficiency correction; preserve Jy/beam and synthesized-beam metadata.",
        "policy_es": "No aplicar eficiencia de haz de antena única; conservar Jy/beam y los metadatos del haz sintetizado.",
    },
    {
        "facility": "VLA",
        "product_en": "calibrated FITS cube/image (Jy/beam)",
        "product_es": "cubo/imagen FITS calibrado (Jy/beam)",
        "policy_en": "Do not apply a single-dish beam-efficiency correction; preserve Jy/beam and synthesized-beam metadata.",
        "policy_es": "No aplicar eficiencia de haz de antena única; conservar Jy/beam y los metadatos del haz sintetizado.",
    },
    {
        "facility": "Other / user-defined",
        "product_en": "spectrum or cube",
        "product_es": "espectro o cubo",
        "policy_en": "Use product metadata or a documented user-defined calibration profile.",
        "policy_es": "Usar los metadatos del producto o un perfil de calibración definido por el usuario y documentado.",
    },
]

IRAM30M_REFERENCE = [
    # Historical EMIR/main-beam reference values published by IRAM and used
    # for the pre-2024 30m telescope state. These are deliberately explicit
    # reference points rather than an automatic correction. Values are
    # (frequency GHz, F_eff, B_eff).
    (86.0, 0.95, 0.81),
    (115.0, 0.94, 0.78),
    (145.0, 0.93, 0.74),
    (210.0, 0.94, 0.63),
    (230.0, 0.92, 0.59),
    (280.0, 0.87, 0.49),
    (340.0, 0.81, 0.35),
    (345.0, 0.80, 0.34),
]

@dataclass
class CalibrationProfile:
    name: str
    telescope: str = ""
    instrument: str = ""
    input_scale: str = "native"
    output_scale: str = "native"
    factor: float = 1.0
    beam_eff: float | None = None
    forward_eff: float | None = None
    frequency_min_ghz: float | None = None
    frequency_max_ghz: float | None = None
    notes: str = ""
    provenance: str = ""

    def as_dict(self):
        return asdict(self)


def _finite(value) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except Exception:
        return None


def factor_from_header(metadata: dict[str, Any]) -> dict[str, Any] | None:
    """Deriva T_A* -> T_mb cuando header contiene F_eff y B_eff.

    En la convención de calibración de antena única, T_mb = (F_eff/B_eff) T_A*.
    No se aplica si las unidades sugieren Jy/beam o si faltan eficiencias.
    """
    bunit = str(metadata.get("bunit") or "").lower()
    if "jy" in bunit and "beam" in bunit:
        return {"mode": "none", "factor": 1.0, "name": "Imagen interferométrica calibrada (Jy/beam)",
                "notes": "No se aplica eficiencia de haz de antena única."}
    beam = _finite(metadata.get("beam_eff"))
    forward = _finite(metadata.get("forward_eff"))
    if beam and forward and beam > 0:
        return {
            "mode": "header",
            "factor": forward / beam,
            "name": "Header: T_A* → T_mb (F_eff/B_eff)",
            "beam_eff": beam,
            "forward_eff": forward,
            "notes": "Eficiencias leídas del producto de entrada.",
        }
    return None


def iram30m_reference_profile(freq_mhz: float) -> dict[str, Any]:
    ghz = float(freq_mhz) / 1000.0
    row = min(IRAM30M_REFERENCE, key=lambda item: abs(item[0] - ghz))
    freq_ref, forward, beam = row
    return {
        "mode": "builtin",
        "factor": forward / beam,
        "name": f"IRAM 30m referencia {freq_ref:g} GHz: T_A* → T_mb",
        "beam_eff": beam,
        "forward_eff": forward,
        "frequency_reference_ghz": freq_ref,
        "notes": "Perfil de referencia; priorice eficiencias del header o valores oficiales de la época de observación.",
        "provenance": "IRAM 30m historical EMIR/main-beam efficiency reference table",
    }


def automatic_calibration(metadata: dict[str, Any], median_frequency_mhz: float | None = None) -> dict[str, Any]:
    header = factor_from_header(metadata)
    if header:
        return header
    telescope = (str(metadata.get("telescope") or "") + " " + str(metadata.get("instrument") or "")).upper()
    bunit = str(metadata.get("bunit") or "").upper()
    if "JY/BEAM" in bunit or "JY BEAM" in bunit:
        return {"mode": "none", "factor": 1.0, "name": "Sin corrección de eficiencia (Jy/beam)",
                "notes": "El producto interferométrico ya está calibrado por haz sintetizado."}
    # No se aplica automáticamente la tabla histórica del 30m si faltan valores
    # de header: podría ser incorrecta para la fecha/configuración. La hacemos
    # seleccionable por el usuario en el diálogo.
    return {"mode": "none", "factor": 1.0, "name": "Sin corrección automática", "notes": "Factor = 1.0"}


def load_custom_profiles(path: str | Path = CUSTOM_PATH) -> list[dict[str, Any]]:
    p = Path(path)
    try:
        payload = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else []
        if isinstance(payload, dict):
            payload = payload.get("profiles", [])
        return [dict(x) for x in payload if isinstance(x, dict)]
    except Exception:
        return []


def save_custom_profiles(profiles: list[dict[str, Any]], path: str | Path = CUSTOM_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"profiles": profiles}, ensure_ascii=False, indent=2), encoding="utf-8")
