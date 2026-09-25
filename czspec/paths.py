"""Rutas de recursos de solo lectura y datos escribibles de CZSpec.

Los catálogos viajan dentro del paquete. Los resultados nunca se escriben en
la carpeta de instalación, porque en Windows y macOS normalmente es de solo
lectura. La variable ``CZSPEC_HOME`` permite elegir otra ubicación.
"""

from __future__ import annotations

import os
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
RESOURCES_DIR = PACKAGE_DIR / "resources"
CZSPEC_ICON_PATH = RESOURCES_DIR / "icons" / "czspec.png"
CZSPEC_WINDOWS_ICON_PATH = RESOURCES_DIR / "icons" / "czspec.ico"
CZSPEC_ICON_SIZE_PATHS = {
    size: RESOURCES_DIR / "icons" / f"czspec-{size}.png"
    for size in (16, 32, 48, 64, 128, 256)
}
CATALOGS_DIR = RESOURCES_DIR / "catalogs"
PARTITION_DIR = CATALOGS_DIR / "partition_functions"
ROTCONST_DIR = CATALOGS_DIR / "rotational_constants"

CDMS_PARTITION_PATH = PARTITION_DIR / "cdms_partition_functions.txt"
JPL_PARTITION_PATH = PARTITION_DIR / "jpl_partition_functions.csv"
CDMS_ABC_PATH = ROTCONST_DIR / "cdms_abc_constants.csv"
JPL_ABC_PATH = ROTCONST_DIR / "jpl_abc_constants.csv"


def application_icon_path() -> Path:
    """Devuelve el recurso más apropiado para el sistema operativo actual."""
    if os.name == "nt":
        return CZSPEC_WINDOWS_ICON_PATH
    return CZSPEC_ICON_PATH


def _default_workspace_dir() -> Path:
    configured = os.environ.get("CZSPEC_HOME")
    if configured:
        return Path(configured).expanduser().resolve()

    # Preferencia persistente escrita desde Configuración de CZSpec. Se lee al
    # arrancar para que todos los módulos compartan exactamente la misma raíz.
    preference_file = Path.home() / ".czspec" / "preferences.json"
    try:
        if preference_file.is_file():
            import json
            data = json.loads(preference_file.read_text(encoding="utf-8"))
            configured = str(data.get("workspace_dir") or "").strip()
            if configured:
                return Path(configured).expanduser().resolve()
    except Exception:
        pass

    documents = Path.home() / "Documents"
    base = documents if documents.is_dir() else Path.home()
    return base / "CZSpec"


WORKSPACE_DIR = _default_workspace_dir()
OUTPUTS_DIR = WORKSPACE_DIR / "outputs"
CACHE_DIR = WORKSPACE_DIR / "cache"

PEAK_DETECTION_OUTPUT_DIR = OUTPUTS_DIR / "peak_detection"
SPECIES_SEARCH_OUTPUT_DIR = OUTPUTS_DIR / "species_search"
COLUMN_DENSITY_OUTPUT_DIR = OUTPUTS_DIR / "column_density"
LTE_MODEL_OUTPUT_DIR = OUTPUTS_DIR / "lte_model"
MOLECULAR_RATIOS_OUTPUT_DIR = OUTPUTS_DIR / "molecular_ratios"
SPATIAL_REPRESENTATION_OUTPUT_DIR = OUTPUTS_DIR / "spatial_representation"
PEAK_GRAPHICS_DIR = PEAK_DETECTION_OUTPUT_DIR / "graphics"
PEAK_TABLES_DIR = PEAK_DETECTION_OUTPUT_DIR / "tables"
PEAK_IMAGES_DIR = PEAK_DETECTION_OUTPUT_DIR / "images"
CLASS_IMPORT_OUTPUT_DIR = PEAK_DETECTION_OUTPUT_DIR / "class_imports"
FITS_IMPORT_OUTPUT_DIR = PEAK_DETECTION_OUTPUT_DIR / "fits_imports"
SPECIES_GRAPHICS_DIR = SPECIES_SEARCH_OUTPUT_DIR / "graphics"
SPECIES_TABLES_DIR = SPECIES_SEARCH_OUTPUT_DIR / "tables"
SPECIES_IMAGES_DIR = SPECIES_SEARCH_OUTPUT_DIR / "images"
COLUMN_DENSITY_GRAPHICS_DIR = COLUMN_DENSITY_OUTPUT_DIR / "graphics"
COLUMN_DENSITY_TABLES_DIR = COLUMN_DENSITY_OUTPUT_DIR / "tables"
COLUMN_DENSITY_IMAGES_DIR = COLUMN_DENSITY_OUTPUT_DIR / "images"
LTE_GRAPHICS_DIR = LTE_MODEL_OUTPUT_DIR / "graphics"
LTE_TABLES_DIR = LTE_MODEL_OUTPUT_DIR / "tables"
LTE_IMAGES_DIR = LTE_MODEL_OUTPUT_DIR / "images"
NONLTE_OUTPUT_DIR = LTE_MODEL_OUTPUT_DIR / "nonlte"
NONLTE_GRAPHICS_DIR = NONLTE_OUTPUT_DIR / "graphics"
NONLTE_TABLES_DIR = NONLTE_OUTPUT_DIR / "tables"
NONLTE_IMAGES_DIR = NONLTE_OUTPUT_DIR / "images"
MOLECULAR_RATIOS_GRAPHICS_DIR = MOLECULAR_RATIOS_OUTPUT_DIR / "graphics"
MOLECULAR_RATIOS_TABLES_DIR = MOLECULAR_RATIOS_OUTPUT_DIR / "tables"
MOLECULAR_RATIOS_IMAGES_DIR = MOLECULAR_RATIOS_OUTPUT_DIR / "images"
SPATIAL_GRAPHICS_DIR = SPATIAL_REPRESENTATION_OUTPUT_DIR / "graphics"
SPATIAL_TABLES_DIR = SPATIAL_REPRESENTATION_OUTPUT_DIR / "tables"
SPATIAL_IMAGES_DIR = SPATIAL_REPRESENTATION_OUTPUT_DIR / "images"
LAMDA_DATA_DIR = CACHE_DIR / "lamda"
OPTICALLY_THIN_OUTPUT_DIR = COLUMN_DENSITY_TABLES_DIR / "mod"
HYPERFINE_OUTPUT_DIR = COLUMN_DENSITY_TABLES_DIR / "mth"

# Alias internos conservados para no romper importaciones de versiones alfa previas.
VASYUNINA_OUTPUT_DIR = OPTICALLY_THIN_OUTPUT_DIR
SANHUEZA_OUTPUT_DIR = HYPERFINE_OUTPUT_DIR
SPECIES_LATEX_DIR = SPECIES_SEARCH_OUTPUT_DIR / "latex"
COLUMN_DENSITY_LATEX_DIR = COLUMN_DENSITY_TABLES_DIR / "latex"

TABLES_DIR = OUTPUTS_DIR / "tables"
IMAGES_DIR = OUTPUTS_DIR / "images"
TEMP_DIR = CACHE_DIR / "temp"


def ensure_workspace_dirs() -> None:
    """Crea únicamente las carpetas escribibles requeridas al iniciar."""
    for path in (TABLES_DIR, IMAGES_DIR, TEMP_DIR, CLASS_IMPORT_OUTPUT_DIR, FITS_IMPORT_OUTPUT_DIR):
        path.mkdir(parents=True, exist_ok=True)
