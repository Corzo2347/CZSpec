"""Actualización local y segura de una instalación existente de CZSpec."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UpdateResult:
    package_path: Path
    installer_output: str
    desktop_warning: str | None = None


def _absolute_without_resolving(path: str | Path) -> Path:
    """Normaliza una ruta sin seguir enlaces simbólicos de entornos virtuales."""
    expanded = Path(path).expanduser()
    return Path(os.path.abspath(expanded))


def _stable_linux_python() -> Path | None:
    """Localiza el Python de la instalación estable creada por CZSpec."""
    if not sys.platform.startswith("linux"):
        return None
    data_home = Path(
        os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    ).expanduser()
    candidate = data_home / "czspec" / "venv" / "bin" / "python"
    launcher = candidate.parent / "czspec"
    if candidate.is_file() and launcher.is_file():
        return _absolute_without_resolving(candidate)
    return None


def select_update_python(python_executable: str | Path | None = None) -> Path:
    """Selecciona el entorno que debe recibir la actualización."""
    if python_executable is not None:
        return _absolute_without_resolving(python_executable)
    stable_python = _stable_linux_python()
    if stable_python is not None:
        return stable_python
    return _absolute_without_resolving(sys.executable)


def find_desktop_launcher(python: Path) -> Path | None:
    """Encuentra un lanzador existente sin asumir que vive en /usr/bin."""
    candidates = [
        python.parent / "czspec",
        Path.home() / ".local" / "bin" / "czspec",
    ]
    path_launcher = shutil.which("czspec")
    if path_launcher:
        candidates.append(Path(path_launcher))

    for candidate in candidates:
        normalized = _absolute_without_resolving(candidate)
        if normalized.is_file():
            return normalized
    return None


def validate_update_package(package_path: str | Path) -> Path:
    """Acepta únicamente ruedas locales cuyo nombre corresponda a CZSpec."""
    resolved = Path(package_path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"No se encontró el archivo: {resolved}")
    if resolved.suffix.lower() != ".whl" or not resolved.name.lower().startswith(
        "czspec-"
    ):
        raise ValueError("Selecciona un instalador oficial de CZSpec con extensión .whl.")
    return resolved


def install_update_package(
    package_path: str | Path,
    *,
    python_executable: str | Path | None = None,
) -> UpdateResult:
    """Actualiza el entorno activo y vuelve a registrar el lanzador Linux."""
    package = validate_update_package(package_path)
    python = select_update_python(python_executable)

    completed = subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--disable-pip-version-check",
            "--no-input",
            str(package),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    output = "\n".join(
        part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
    )
    if completed.returncode != 0:
        detail = output[-4000:] if output else "pip no devolvió detalles."
        raise RuntimeError(f"No se pudo instalar la actualización.\n\n{detail}")

    desktop_warning = None
    if sys.platform.startswith("linux"):
        launcher = find_desktop_launcher(python)
        if launcher is None:
            desktop_warning = (
                "La actualización quedó instalada, pero no se encontró el "
                "lanzador para refrescar el menú de aplicaciones."
            )
        else:
            desktop_process = subprocess.run(
                [
                    str(python),
                    "-m",
                    "czspec.desktop",
                    "--install",
                    "--launcher",
                    str(launcher),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            if desktop_process.returncode != 0:
                desktop_detail = (desktop_process.stderr or desktop_process.stdout).strip()
                desktop_warning = (
                    "La actualización quedó instalada, pero no se pudo refrescar "
                    f"el menú de aplicaciones.\n\n{desktop_detail}"
                )

    return UpdateResult(
        package_path=package,
        installer_output=output,
        desktop_warning=desktop_warning,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Instala una actualización local .whl de CZSpec."
    )
    parser.add_argument("package", help="Ruta al archivo czspec-*.whl descargado.")
    args = parser.parse_args(argv)

    try:
        result = install_update_package(args.package)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Actualización instalada: {result.package_path.name}")
    if result.desktop_warning:
        print(f"Aviso: {result.desktop_warning}", file=sys.stderr)
    print("Cierra y vuelve a abrir CZSpec para usar la nueva versión.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
