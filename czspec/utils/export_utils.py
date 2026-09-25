"""Exportación y apertura segura de carpetas en varios sistemas."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from czspec.paths import IMAGES_DIR, TABLES_DIR

__all__ = [
    "IMAGES_DIR",
    "TABLES_DIR",
    "export_dataframe_to_csv",
    "export_html_text",
    "open_folder_in_system",
]


def _safe_name(value: str, fallback: str = "resultado") -> str:
    clean = re.sub(r"[^\w.-]+", "_", (value or "").strip(), flags=re.UNICODE)
    return clean.strip("._-") or fallback


def _timestamped_path(directory: Path, base_name: str, suffix: str, extension: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = _safe_name(base_name)
    suffix = _safe_name(suffix, "export")
    return directory / f"{stem}_{suffix}_{timestamp}.{extension.lstrip('.')}"


def export_dataframe_to_csv(
    dataframe: pd.DataFrame,
    base_name: str,
    *,
    suffix: str = "results",
    output_dir: Path | str = TABLES_DIR,
) -> Path:
    path = _timestamped_path(Path(output_dir), base_name, suffix, "csv")
    dataframe.to_csv(path, index=False, encoding="utf-8")
    return path


def export_html_text(
    html_text: str,
    base_name: str,
    *,
    suffix: str = "interactive",
    output_dir: Path | str = TABLES_DIR,
) -> Path:
    path = _timestamped_path(Path(output_dir), base_name, suffix, "html")
    path.write_text(html_text, encoding="utf-8")
    return path


def open_folder_in_system(path: Path | str) -> None:
    """Abre *path* sin construir un comando de shell vulnerable."""
    folder = Path(path).expanduser().resolve()
    folder.mkdir(parents=True, exist_ok=True)

    if sys.platform.startswith("win"):
        os.startfile(str(folder))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(folder)])
    else:
        subprocess.Popen(["xdg-open", str(folder)])
