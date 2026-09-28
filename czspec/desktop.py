"""Integración de CZSpec con el escritorio Linux del usuario."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from czspec.paths import CZSPEC_ICON_PATH, CZSPEC_ICON_SIZE_PATHS


APP_ID = "org.czspec.CZSpec"
ICON_NAME = f"{APP_ID}-cz"
DESKTOP_FILENAME = f"{APP_ID}.desktop"


def _xdg_data_home() -> Path:
    configured = os.environ.get("XDG_DATA_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path.home() / ".local" / "share"


def _desktop_exec_argument(path: Path) -> str:
    """Escapa una ruta para el campo Exec de un archivo desktop."""
    text = str(path)
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("`", "\\`")
        .replace("$", "\\$")
    )
    return f'"{escaped}"'


def _refresh_desktop_caches(data_home: Path) -> None:
    desktop_database = shutil.which("update-desktop-database")
    if desktop_database:
        subprocess.run(
            [desktop_database, str(data_home / "applications")],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    icon_cache = shutil.which("gtk-update-icon-cache")
    icon_root = data_home / "icons" / "hicolor"
    if icon_cache and icon_root.is_dir():
        subprocess.run(
            [icon_cache, "-f", "-t", str(icon_root)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def install_desktop_integration(launcher: str | Path | None = None) -> Path:
    """Instala el lanzador y los iconos del usuario; no requiere sudo."""
    if not sys.platform.startswith("linux"):
        raise RuntimeError("La integración .desktop está disponible únicamente en Linux.")

    launcher_path = Path(
        launcher or (Path(sys.executable).resolve().parent / "czspec")
    ).expanduser().resolve()
    if not launcher_path.is_file():
        raise FileNotFoundError(f"No se encontró el lanzador de CZSpec: {launcher_path}")

    data_home = _xdg_data_home()
    applications_dir = data_home / "applications"
    applications_dir.mkdir(parents=True, exist_ok=True)

    icon_targets = {
        512: CZSPEC_ICON_PATH,
        **CZSPEC_ICON_SIZE_PATHS,
    }
    for size, source in icon_targets.items():
        target_dir = data_home / "icons" / "hicolor" / f"{size}x{size}" / "apps"
        target_dir.mkdir(parents=True, exist_ok=True)
        # El nombre versionado evita que GNOME reutilice en memoria el icono
        # anterior después de un rediseño. Se conserva además el nombre
        # histórico para integraciones externas ya existentes.
        shutil.copy2(source, target_dir / f"{ICON_NAME}.png")
        shutil.copy2(source, target_dir / f"{APP_ID}.png")

    desktop_text = f"""[Desktop Entry]
Type=Application
Version=1.0
Name=CZSpec
GenericName=Análisis espectral molecular
Comment=Detección, identificación y densidad de columna de líneas moleculares
Exec={_desktop_exec_argument(launcher_path)}
Icon={ICON_NAME}
Terminal=false
Categories=Science;Education;
Keywords=astronomía;espectroscopía;radioastronomía;líneas moleculares;
StartupNotify=true
StartupWMClass=CZSpec
X-GNOME-WMClass=CZSpec
X-GNOME-UsesNotifications=true
"""

    desktop_path = applications_dir / DESKTOP_FILENAME
    desktop_path.write_text(desktop_text, encoding="utf-8")
    desktop_path.chmod(0o755)
    _refresh_desktop_caches(data_home)
    return desktop_path


def remove_desktop_integration() -> None:
    """Elimina solamente el lanzador y los iconos administrados por CZSpec."""
    if not sys.platform.startswith("linux"):
        return

    data_home = _xdg_data_home()
    desktop_path = data_home / "applications" / DESKTOP_FILENAME
    desktop_path.unlink(missing_ok=True)
    for size in (16, 32, 48, 64, 128, 256, 512):
        icon_dir = (
            data_home / "icons" / "hicolor" / f"{size}x{size}" / "apps"
        )
        for icon_name in (APP_ID, ICON_NAME):
            (icon_dir / f"{icon_name}.png").unlink(missing_ok=True)
    _refresh_desktop_caches(data_home)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Instala o elimina la integración de CZSpec con Linux."
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--install", action="store_true")
    action.add_argument("--uninstall", action="store_true")
    parser.add_argument("--launcher", help="Ruta estable al comando czspec.")
    args = parser.parse_args(argv)

    if args.uninstall:
        remove_desktop_integration()
        print("Integración de escritorio eliminada.")
        return 0

    desktop_path = install_desktop_integration(args.launcher)
    print(f"Lanzador instalado: {desktop_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
