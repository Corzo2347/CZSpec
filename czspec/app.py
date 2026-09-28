"""Punto de entrada de la aplicación de escritorio CZSpec."""

from __future__ import annotations

import os
import sys

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings

from czspec import __public_version__
from czspec.desktop import APP_ID
from czspec.gui.main_window import MainWindow
from czspec.paths import application_icon_path, ensure_workspace_dirs
from czspec.theme import build_app_stylesheet


def _configure_windows_identity() -> None:
    """Asocia la ventana con CZSpec en la barra de tareas de Windows."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except (AttributeError, OSError):
        # El icono de la ventana sigue disponible aunque una edición concreta
        # de Windows no exponga esta llamada.
        pass


def create_application(argv: list[str] | None = None) -> QApplication:
    """Crea y configura una instancia de QApplication consistente."""
    _configure_windows_identity()
    if sys.platform.startswith("linux"):
        os.environ.setdefault("QT_WAYLAND_APP_ID", APP_ID)

    app = QApplication.instance() or QApplication(argv or sys.argv)
    app.setApplicationDisplayName("CZSpec")
    app.setApplicationName("CZSpec")
    app.setApplicationVersion(__public_version__)
    app.setOrganizationName("CZSpec")
    app.setDesktopFileName(APP_ID)
    app.setWindowIcon(QIcon(str(application_icon_path())))
    app.setStyle("Fusion")
    settings = QSettings("CZSpec", "CZSpec")
    try:
        text_scale = int(settings.value("ui/text_scale_percent", 100) or 100)
    except Exception:
        text_scale = 100
    font_family = str(settings.value("ui/font_family", "Inter") or "Inter").strip() or "Inter"
    # Keep point-size changes bounded.  Very large runtime font jumps make Qt
    # relayout every complex table/web view and can feel like a freeze.
    text_scale = max(80, min(150, text_scale))
    app.setFont(QFont(font_family, max(8, round(10 * text_scale / 100))))
    app.setStyleSheet(build_app_stylesheet(text_scale, font_family))
    settings.setValue("ui/text_scale_applied", text_scale)
    settings.setValue("ui/font_family_applied", font_family)
    settings.sync()
    return app


def main() -> int:
    """Inicia CZSpec y devuelve el código de salida de Qt."""
    ensure_workspace_dirs()
    app = create_application()
    window = MainWindow()
    window.show()
    return app.exec()
