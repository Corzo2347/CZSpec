"""Estilos de gráficas sin dependencias científicas pesadas."""

from __future__ import annotations

import re


DEFAULT_FIT_COLOR = "#E67E22"

DEFAULT_PLOT_STYLES = {
    "spectrum": {"color": "#111827", "width": 1.4, "dash": "solid"},
    "baseline": {"color": "#DC2626", "width": 2.0, "dash": "solid"},
    "corrected": {"color": "#2563EB", "width": 1.6, "dash": "solid"},
    # Final fitted profile: isolated line or summed profile of a blended group.
    "fits": {"color": DEFAULT_FIT_COLOR, "width": 2.2, "dash": "solid"},
    # Individual mathematical components inside a multi-line blended group.
    "fit_components": {"color": "#93C5FD", "width": 1.5, "dash": "dash"},
    # Diagnostic residual after subtracting the final fitted profiles.
    "residual": {"color": "#94A3B8", "width": 1.0, "dash": "dot"},
    "detections": {"color": "#8B5CF6", "size": 7.0},
}

VALID_DASH_STYLES = {
    "solid",
    "dot",
    "dash",
    "longdash",
    "dashdot",
    "longdashdot",
}


def normalize_plot_styles(plot_styles=None) -> dict:
    """Combina estilos del usuario con valores seguros para Plotly."""

    source = plot_styles if isinstance(plot_styles, dict) else {}
    normalized = {}

    for role, defaults in DEFAULT_PLOT_STYLES.items():
        candidate = source.get(role, {})
        if not isinstance(candidate, dict):
            candidate = {}

        color = str(candidate.get("color", defaults["color"])).strip().upper()
        if not re.fullmatch(r"#[0-9A-F]{6}", color):
            color = defaults["color"]

        values = {"color": color}
        if role == "detections":
            try:
                size = float(candidate.get("size", defaults["size"]))
            except (TypeError, ValueError):
                size = float(defaults["size"])
            values["size"] = min(18.0, max(3.0, size))
        else:
            try:
                width = float(candidate.get("width", defaults["width"]))
            except (TypeError, ValueError):
                width = float(defaults["width"])
            dash = str(candidate.get("dash", defaults["dash"])).strip().lower()
            values["width"] = min(8.0, max(0.5, width))
            values["dash"] = dash if dash in VALID_DASH_STYLES else defaults["dash"]

        normalized[role] = values

    return normalized
