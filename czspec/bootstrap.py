"""Arranque temprano y portable de CZSpec.

En algunas distribuciones Linux, el cargador dinámico selecciona bibliotecas
Qt del sistema antes que las distribuidas con PySide6. Cuando las versiones no
coinciden aparecen errores ``undefined symbol ... Qt_6_PRIVATE_API`` antes de
que QApplication pueda crearse. Este módulo se ejecuta antes de importar Qt,
prioriza las bibliotecas del entorno activo y reinicia el proceso una sola vez.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


_BOOTSTRAP_MARKER = "CZSPEC_QT_BOOTSTRAPPED"


def _pyside_directory() -> Path | None:
    spec = importlib.util.find_spec("PySide6")
    if spec is None:
        return None

    locations = spec.submodule_search_locations or []
    for location in locations:
        candidate = Path(location).resolve()
        if (candidate / "Qt" / "lib").is_dir():
            return candidate
    return None


def _prepend_path(value: str, current: str | None) -> str:
    parts = [part for part in (current or "").split(os.pathsep) if part]
    normalized = os.path.normcase(os.path.abspath(value))
    parts = [part for part in parts if os.path.normcase(os.path.abspath(part)) != normalized]
    return os.pathsep.join([value, *parts])


def _prepare_linux_qt_environment() -> bool:
    """Configura Qt y devuelve True cuando el proceso debe reiniciarse."""
    if not sys.platform.startswith("linux"):
        return False
    if getattr(sys, "frozen", False):
        return False
    if os.environ.get(_BOOTSTRAP_MARKER) == "1":
        return False

    pyside_dir = _pyside_directory()
    if pyside_dir is None:
        return False

    qt_dir = pyside_dir / "Qt"
    qt_lib_dir = qt_dir / "lib"
    qt_plugins_dir = qt_dir / "plugins"
    qt_platforms_dir = qt_plugins_dir / "platforms"

    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = _prepend_path(
        str(qt_lib_dir), environment.get("LD_LIBRARY_PATH")
    )
    environment["QT_PLUGIN_PATH"] = str(qt_plugins_dir)
    environment["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(qt_platforms_dir)
    environment.pop("QT_QPA_PLATFORMTHEME", None)
    environment[_BOOTSTRAP_MARKER] = "1"

    os.execve(
        sys.executable,
        [sys.executable, "-m", "czspec", *sys.argv[1:]],
        environment,
    )
    return True


def main() -> int:
    _prepare_linux_qt_environment()

    from czspec.app import main as application_main

    return application_main()
