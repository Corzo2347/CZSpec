"""Puente seguro entre CZSpec y archivos CLASS ``.30m``.

CZSpec no reimplementa el contenedor binario CLASS. Cuando GILDAS/CLASS está
instalado, usa el propio motor CLASS en modo ``-nw`` únicamente como puente de
importación: indexa el contenedor, selecciona observaciones, verifica su
consistencia, promedia las observaciones compatibles y exporta el buffer R a un
archivo ASCII ``.dat`` normalizado en MHz. Desde ese momento CLASS deja de
participar y todo el procesamiento científico pertenece a CZSpec.

En Linux/macOS se usa CLASS nativo cuando está disponible. En Windows, CZSpec
puede usar CLASS de forma transparente dentro de WSL: el usuario permanece en
la interfaz de CZSpec y CLASS actúa sólo como backend de procesamiento.
"""
from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np

from czspec.paths import TEMP_DIR, CLASS_IMPORT_OUTPUT_DIR


def _iram30m_average_group(telescope: str) -> tuple[str, str]:
    """Devuelve una clave/etiqueta segura para promediar datos IRAM-30m.

    En EMIR, nombres como ``30ME1HLI-F03`` y ``30ME1VLI-F04`` describen
    polarizaciones H/V del mismo subrango LI y del mismo tipo de backend F.
    Esas polarizaciones pueden entrar juntas en ``CONSISTENCY -> AVERAGE``;
    CLASS conserva la decisión final de compatibilidad.  No se mezclan LI con
    LO/UI/UO ni familias de backend diferentes.  Para nombres que no sigan la
    convención de EMIR se conserva el TELESCOPE exacto (fallback conservador).
    """
    raw = str(telescope or "").strip()
    match = re.match(
        r"^(30ME\d)([HV])([LU][IO])-([A-Za-z]+)\d+$",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        receiver, _polar, subband, backend_family = match.groups()
        label = f"{receiver.upper()}-{subband.upper()}-{backend_family.upper()}"
        return label, label
    return raw, raw


@dataclass(frozen=True)
class ClassObservation:
    number: int
    version: int
    source: str
    line: str
    telescope: str

    @property
    def setup_key(self) -> tuple[str, str, str]:
        return self.source, self.line, self.telescope

    @property
    def average_group(self) -> str:
        return _iram30m_average_group(self.telescope)[1]

    @property
    def average_key(self) -> tuple[str, str, str]:
        return self.source, self.line, _iram30m_average_group(self.telescope)[0]


@dataclass(frozen=True)
class ClassSetup:
    source: str
    line: str
    telescopes: tuple[str, ...]
    observations: tuple[ClassObservation, ...]
    average_group: str = ""

    @property
    def count(self) -> int:
        return len(self.observations)

    @property
    def telescope(self) -> str:
        return ", ".join(self.telescopes)

    @property
    def average_label(self) -> str:
        return self.average_group or (self.telescopes[0] if len(self.telescopes) == 1 else self.telescope)

    @property
    def key(self) -> tuple[str, str, str, tuple[str, ...]]:
        return self.source, self.line, self.average_label, self.telescopes


@dataclass(frozen=True)
class ClassBackend:
    """Descripción reproducible del motor CLASS usado por CZSpec."""

    kind: str  # ``native`` o ``wsl``
    executable: str
    display_name: str
    wsl_executable: str | None = None
    wsl_distribution: str | None = None

    @property
    def provenance(self) -> dict:
        return {
            "kind": self.kind,
            "executable": self.executable,
            "display_name": self.display_name,
            "wsl_executable": self.wsl_executable,
            "wsl_distribution": self.wsl_distribution,
        }


class ClassBackendError(RuntimeError):
    pass


def _quote_class(value: str) -> str:
    # SIC acepta cadenas entre comillas dobles. Escape conservador de comillas.
    return '"' + str(value).replace('"', '\\"') + '"'


def _clean_subprocess_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        # ``wsl -l -q`` ha devuelto históricamente UTF-16 en algunas versiones.
        for encoding in ("utf-8", "utf-16-le", "utf-16", "cp1252"):
            try:
                text = value.decode(encoding)
                break
            except Exception:
                text = ""
        if not text:
            text = value.decode(errors="replace")
    else:
        text = str(value)
    return text.replace("\x00", "").replace("\ufeff", "").strip()


def _platform_is_windows() -> bool:
    return sys.platform.startswith("win") or os.name == "nt"


def _hidden_subprocess_kwargs() -> dict:
    """Opciones de subprocess que evitan ventanas de consola fugaces en Windows.

    PySide6 es una aplicación gráfica; los procesos auxiliares (WSL, bash y CLASS)
    deben actuar como backend silencioso. En POSIX no se añaden opciones especiales.
    """
    if not _platform_is_windows():
        return {}

    options: dict = {}
    create_no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if create_no_window:
        options["creationflags"] = create_no_window

    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
        startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        options["startupinfo"] = startupinfo
    except Exception:
        # CREATE_NO_WINDOW suele ser suficiente; este fallback mantiene
        # compatibilidad con runtimes donde STARTUPINFO no esté expuesto.
        pass
    return options


def _run_hidden(args, **kwargs):
    """Ejecuta un proceso auxiliar sin mostrar consola en aplicaciones Windows."""
    for key, value in _hidden_subprocess_kwargs().items():
        kwargs.setdefault(key, value)
    return subprocess.run(args, **kwargs)


def _valid_native_class(candidate: str | Path | None) -> str | None:
    """Normaliza y valida una ruta candidata al ejecutable CLASS."""
    if not candidate:
        return None
    try:
        path = Path(str(candidate)).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path.resolve())
    except Exception:
        pass
    return None


def _find_native_class(explicit_path: str | None = None) -> str | None:
    """Localiza CLASS en el sistema anfitrión.

    La aplicación gráfica puede iniciarse desde GNOME/KDE sin heredar el PATH
    de una terminal. Además, una instalación estándar de GILDAS coloca CLASS
    bajo ``gildas-exe-*/<GAG_EXEC_SYSTEM>/bin/class``; por eso no basta con
    ``shutil.which('class')`` ni con buscar ``gildas-exe-*/bin/class``.
    """
    # 1) Ruta explícita de CZSpec / variable compatible con alpha anteriores.
    override = str(explicit_path or os.environ.get("GILDAS_CLASS", "")).strip()
    found = _valid_native_class(override)
    if found:
        return found

    # 2) Entorno GILDAS ya heredado por el proceso Qt.
    gag_root = str(os.environ.get("GAG_ROOT_DIR", "")).strip()
    gag_exec = str(os.environ.get("GAG_EXEC_SYSTEM", "")).strip()
    env_candidates = []
    if gag_root and gag_exec:
        env_candidates.append(Path(gag_root) / gag_exec / "bin" / "class")
    if gag_root:
        env_candidates.extend([
            Path(gag_root) / "bin" / "class",
            Path(gag_root) / "class",
        ])
    for candidate in env_candidates:
        found = _valid_native_class(candidate)
        if found:
            return found

    # 3) PATH actual del proceso.
    direct = shutil.which("class")
    found = _valid_native_class(direct)
    if found:
        return found

    # En Windows no se lanza Git-Bash/Cygwin como sonda: además de no ser el
    # backend soportado para .30m, puede producir ventanas de consola fugaces.
    if _platform_is_windows():
        return None

    # 4) Login shell. La guía oficial de GILDAS recomienda cargar el entorno
    # desde ~/.bash_profile, que bash -lc sí procesa. Pedimos también las
    # variables GAG_* para poder reconstruir la ruta aunque `class` no esté en
    # PATH por alguna personalización del perfil.
    shell = shutil.which("bash")
    if shell:
        try:
            script = (
                'printf "%s\n%s\n%s\n" "$(command -v class 2>/dev/null)" '
                '"${GAG_ROOT_DIR:-}" "${GAG_EXEC_SYSTEM:-}"'
            )
            proc = _run_hidden(
                [shell, "-lc", script],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            lines = _clean_subprocess_text(proc.stdout).splitlines()
            class_value = lines[0].strip() if len(lines) > 0 else ""
            root_value = lines[1].strip() if len(lines) > 1 else ""
            exec_value = lines[2].strip() if len(lines) > 2 else ""
            found = _valid_native_class(class_value)
            if found:
                return found
            if root_value and exec_value:
                found = _valid_native_class(Path(root_value) / exec_value / "bin" / "class")
                if found:
                    return found
            if root_value:
                found = _valid_native_class(Path(root_value) / "bin" / "class")
                if found:
                    return found
        except Exception:
            pass

    # 5) Búsqueda acotada de instalaciones estándar. Esta es la corrección
    # principal de a52: GILDAS normalmente instala el binario un nivel por
    # debajo del directorio gildas-exe-*, p.ej.
    # ~/gildas-exe-sep26/x86_64-ubuntu24.04-gfortran/bin/class.
    home = Path.home()
    home_patterns = (
        "gildas-exe-*/bin/class",                    # instalaciones antiguas/atípicas
        "gildas-exe-*/*/bin/class",                  # instalación mensual estándar
        "gildas-exe-*/**/bin/class",                 # variantes con un nivel extra
        "gildas*/bin/class",
        "gildas*/*/bin/class",
        ".local/gildas*/bin/class",
        ".local/gildas*/*/bin/class",
        "opt/gildas*/bin/class",
        "opt/gildas*/*/bin/class",
    )
    for pattern in home_patterns:
        try:
            for candidate in home.glob(pattern):
                found = _valid_native_class(candidate)
                if found:
                    return found
        except Exception:
            continue

    # 6) Instalaciones compartidas del sistema. No hacemos un rglob de / para
    # evitar bloquear la GUI; sólo se inspeccionan prefijos habituales.
    system_patterns = (
        "/opt/gildas-exe-*/*/bin/class",
        "/opt/gildas*/*/bin/class",
        "/usr/local/gildas-exe-*/*/bin/class",
        "/usr/local/gildas*/*/bin/class",
    )
    import glob
    for pattern in system_patterns:
        try:
            for value in glob.glob(pattern):
                found = _valid_native_class(value)
                if found:
                    return found
        except Exception:
            continue
    return None


def find_wsl_executable() -> str | None:
    """Localiza ``wsl.exe`` sin asumir que el PATH de Qt coincide con cmd.exe."""
    direct = shutil.which("wsl.exe") or shutil.which("wsl")
    if direct:
        return str(Path(direct))
    if _platform_is_windows():
        system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        # Sysnative permite a procesos de 32 bits llegar al System32 real.
        for folder in ("System32", "Sysnative"):
            candidate = system_root / folder / "wsl.exe"
            if candidate.is_file():
                return str(candidate)
    return None


def _normalise_wsl_distro_names(values) -> list[str]:
    """Filtra nombres de distro y evita interpretar la ayuda de wsl.exe como datos."""
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        name = str(raw or "").replace("\x00", "").strip().lstrip("*").strip()
        if not name or len(name) > 128:
            continue
        low = name.lower()
        if low.startswith("docker-desktop"):
            continue
        # Nombres WSL válidos son compactos; estas señales pertenecen a ayuda/error.
        if any(token in low for token in (
            "microsoft corporation", "copyright", "usage:", "uso:",
            "arguments:", "argumentos:", "options:", "opciones:",
            "windows subsystem", "subsistema de windows", "wsl.exe [",
            "--install", "--list", "--help",
        )):
            continue
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+() -]{0,127}", name):
            continue
        if name not in seen:
            seen.add(name)
            result.append(name)
    return result


def _list_wsl_distributions_registry() -> list[str]:
    """Lee las distribuciones registradas sin iniciar wsl.exe.

    Es la vía preferida en Windows porque evita procesos auxiliares, funciona con
    versiones antiguas del frontend WSL y no depende del idioma de su salida.
    """
    if not _platform_is_windows():
        return []
    try:
        import winreg  # type: ignore

        root_path = r"Software\Microsoft\Windows\CurrentVersion\Lxss"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, root_path) as root:
            values: list[str] = []
            index = 0
            while True:
                try:
                    key_name = winreg.EnumKey(root, index)
                except OSError:
                    break
                index += 1
                try:
                    with winreg.OpenKey(root, key_name) as distro_key:
                        distro_name, _ = winreg.QueryValueEx(distro_key, "DistributionName")
                    values.append(str(distro_name))
                except OSError:
                    continue
        return _normalise_wsl_distro_names(values)
    except Exception:
        return []


def list_wsl_distributions(wsl_executable: str | None = None) -> list[str]:
    """Devuelve distribuciones WSL instaladas sin mostrar ventanas de consola."""
    # Evita invocar wsl.exe siempre que Windows ya tenga el dato en el registro.
    registered = _list_wsl_distributions_registry()
    if registered:
        return registered

    wsl = wsl_executable or find_wsl_executable()
    if not wsl:
        return []

    # ``-l -q`` es más compatible con versiones antiguas que las opciones largas.
    # Se prueba una segunda sintaxis sólo como fallback y jamás se interpreta la
    # pantalla de ayuda como si fueran nombres de distribuciones.
    for args in ([wsl, "-l", "-q"], [wsl, "--list", "--quiet"]):
        try:
            proc = _run_hidden(
                args,
                capture_output=True,
                timeout=8,
                check=False,
            )
        except Exception:
            continue
        stdout = _clean_subprocess_text(proc.stdout)
        stderr = _clean_subprocess_text(proc.stderr)
        names = _normalise_wsl_distro_names(stdout.splitlines())
        if proc.returncode == 0 and names:
            return names
        # Si el comando respondió correctamente pero no hay salida, no hay distros.
        if proc.returncode == 0 and not stdout.strip() and not stderr.strip():
            return []
    return []




def _wsl_service_health(wsl: str, distro: str | None = None, retries: int = 2) -> dict:
    """Probe WSL without confusing a transient Windows service failure with missing CLASS."""
    if not wsl:
        return {"ok": False, "transient": False, "message": "WSL executable not found."}
    args = [wsl, "-d", distro, "--", "true"] if distro else [wsl, "--status"]
    last = ""
    transient_tokens = ("wsl/service/e_unexpected", "e_unexpected", "unexpected failure", "error catastrófico",
                        "catastrophic failure", "the service cannot be started", "service unavailable")
    for attempt in range(max(1, int(retries) + 1)):
        try:
            proc = _run_hidden(args, capture_output=True, timeout=10, check=False)
            stdout = _clean_subprocess_text(proc.stdout); stderr = _clean_subprocess_text(proc.stderr)
            combined = (stdout + "\n" + stderr).strip(); last = combined
            low = combined.lower()
            if proc.returncode == 0:
                return {"ok": True, "transient": False, "message": combined}
            transient = any(token in low for token in transient_tokens)
            if transient and attempt < retries:
                time.sleep(0.7 * (attempt + 1)); continue
            return {"ok": False, "transient": transient, "message": combined or f"WSL returned code {proc.returncode}."}
        except (subprocess.TimeoutExpired, OSError) as exc:
            last = str(exc)
            if attempt < retries:
                time.sleep(0.7 * (attempt + 1)); continue
            return {"ok": False, "transient": True, "message": last}
        except Exception as exc:
            return {"ok": False, "transient": False, "message": str(exc)}
    return {"ok": False, "transient": True, "message": last}

def _wsl_test_executable(wsl: str, distro: str, path: str) -> bool:
    try:
        proc = _run_hidden(
            [wsl, "-d", distro, "--", "test", "-x", path],
            capture_output=True,
            timeout=6,
            check=False,
        )
        return proc.returncode == 0
    except Exception:
        return False


def _find_class_in_wsl(
    wsl: str,
    distro: str,
    explicit_path: str | None = None,
) -> str | None:
    override = str(explicit_path or "").strip()
    if override and _wsl_test_executable(wsl, distro, override):
        return override

    probe = r'''
command -v class 2>/dev/null || {
  for p in "$HOME"/gildas-exe-*/bin/class "$HOME"/gildas-exe-*/*/bin/class "$HOME"/gildas*/bin/class "$HOME"/gildas*/*/bin/class "$HOME"/.local/gildas*/bin/class "$HOME"/.local/gildas*/*/bin/class /opt/gildas*/bin/class /opt/gildas*/*/bin/class /opt/czspec-gildas/*/bin/class /opt/czspec-gildas/*/*/bin/class; do
    if [ -x "$p" ]; then printf '%s\n' "$p"; break; fi
  done
}
'''.strip()
    try:
        # ``-lic`` permite encontrar CLASS cuando GILDAS se carga desde el perfil
        # de la distro; stderr puede contener mensajes del shell y se ignora aquí.
        proc = _run_hidden(
            [wsl, "-d", distro, "--", "bash", "-lic", probe],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except Exception:
        return None
    text = _clean_subprocess_text(proc.stdout)
    candidates = [line.strip() for line in text.splitlines() if line.strip().startswith("/")]
    for candidate in reversed(candidates):
        if _wsl_test_executable(wsl, distro, candidate):
            return candidate
    return None


def find_class_backend(
    *,
    preference: str | None = None,
    native_class_path: str | None = None,
    wsl_distribution: str | None = None,
    wsl_class_path: str | None = None,
) -> ClassBackend | None:
    """Localiza el backend CLASS respetando la preferencia de CZSpec.

    Las variables de entorno sirven como interfaz entre la configuración Qt y
    esta capa científica, manteniendo ``class30m.py`` libre de dependencias GUI.
    """
    pref = str(preference or os.environ.get("CZSPEC_CLASS_BACKEND", "auto")).strip().lower()
    if pref not in {"auto", "native", "wsl"}:
        pref = "auto"

    if pref in {"auto", "native"}:
        native = _find_native_class(native_class_path or os.environ.get("CZSPEC_NATIVE_CLASS", ""))
        if native:
            return ClassBackend(
                kind="native",
                executable=native,
                display_name=f"CLASS nativo · {native}",
            )
        if pref == "native":
            return None

    # WSL es el camino oficial de CZSpec para acceder a CLASS desde Windows.
    if pref in {"auto", "wsl"} and (_platform_is_windows() or pref == "wsl"):
        wsl = find_wsl_executable()
        if not wsl:
            return None
        requested_distro = str(
            wsl_distribution or os.environ.get("CZSPEC_WSL_DISTRO", "")
        ).strip()
        distros = list_wsl_distributions(wsl)
        if requested_distro:
            ordered = [requested_distro] + [d for d in distros if d != requested_distro]
        else:
            ordered = distros
        explicit = str(
            wsl_class_path or os.environ.get("CZSPEC_WSL_CLASS", "")
        ).strip() or None
        for distro in ordered:
            class_path = None
            for attempt in range(3):
                class_path = _find_class_in_wsl(wsl, distro, explicit if distro == requested_distro else None)
                if class_path:
                    break
                health = _wsl_service_health(wsl, distro, retries=0)
                if not health.get("transient"):
                    break
                time.sleep(0.6 * (attempt + 1))
            if class_path:
                return ClassBackend(
                    kind="wsl",
                    executable=class_path,
                    display_name=f"CLASS vía WSL · {distro} · {class_path}",
                    wsl_executable=wsl,
                    wsl_distribution=distro,
                )
        return None
    return None


def find_class_executable() -> str | None:
    """Compatibilidad con alpha previas: devuelve la ruta del CLASS resuelto."""
    backend = find_class_backend()
    return backend.executable if backend else None


def class_backend_status() -> tuple[bool, str]:
    backend = find_class_backend()
    if backend:
        return True, backend.display_name

    pref = os.environ.get("CZSPEC_CLASS_BACKEND", "auto").strip().lower() or "auto"
    if _platform_is_windows():
        wsl = find_wsl_executable()
        if pref == "native":
            return False, (
                "No se encontró CLASS nativo en Windows. Cambia el backend a Automático/WSL "
                "o configura una ruta nativa explícita si dispones de una instalación compatible."
            )
        if not wsl:
            return False, (
                "No se encontró WSL. Para leer archivos .30m en Windows, CZSpec usa "
                "GILDAS/CLASS dentro de una distribución WSL sin abrir CLASS al usuario. "
                "Instala WSL + una distribución Linux y después GILDAS/CLASS dentro de ella."
            )
        distros = list_wsl_distributions(wsl)
        if not distros:
            return False, (
                "WSL está disponible, pero no se encontró ninguna distribución Linux utilizable. "
                "Instala Ubuntu (u otra distribución) y GILDAS/CLASS dentro de ella."
            )
        requested = os.environ.get("CZSPEC_WSL_DISTRO", "").strip()
        detail = f" Distribuciones detectadas: {', '.join(distros)}."
        if requested:
            detail += f" Distribución configurada: {requested}."
        return False, (
            "WSL está disponible, pero CZSpec no encontró el ejecutable 'class' dentro de sus "
            "distribuciones. Carga GILDAS en el perfil de WSL o configura la ruta Linux de CLASS "
            "desde 'Configurar GILDAS/CLASS'." + detail
        )

    return False, (
        "No se encontró el ejecutable 'class'. La lectura .30m utiliza el motor oficial "
        "GILDAS/CLASS; instala/carga GILDAS o define GILDAS_CLASS con la ruta al ejecutable."
    )



def install_or_repair_class_backend(
    *,
    wsl_distribution: str | None = None,
    progress=None,
) -> dict:
    """Best-effort guided installation/repair of the CLASS backend."""
    import datetime as _datetime

    def report(value, message):
        if callable(progress):
            try:
                progress(value, message)
            except Exception:
                pass

    report(2, "Comprobando GILDAS/CLASS...")
    existing = find_class_backend(preference="auto", wsl_distribution=wsl_distribution)
    if existing:
        report(100, "CLASS ya está disponible.")
        return {"status": "available", "backend": existing.provenance}

    if not _platform_is_windows():
        return {
            "status": "manual_required",
            "message": ("La instalación automática integrada está disponible por ahora en Windows/WSL. "
                        "En Linux/macOS usa la instalación oficial de GILDAS y vuelve a pulsar Diagnosticar."),
            "url": "https://www.iram.fr/IRAMFR/GILDAS/install.html",
        }

    wsl = find_wsl_executable()
    if not wsl:
        return {
            "status": "wsl_missing",
            "message": ("WSL no está instalado. Windows puede requerir permisos de administrador y un reinicio "
                        "antes de que CZSpec pueda instalar CLASS."),
        }

    distros = list_wsl_distributions(wsl)
    requested = str(wsl_distribution or "").strip()
    distro = requested if requested in distros else (distros[0] if distros else "")
    if not distro:
        return {
            "status": "distro_missing",
            "message": ("WSL está instalado pero no hay una distribución Linux. Instala Ubuntu y vuelve a usar "
                        "este botón; CZSpec podrá instalar CLASS dentro de ella."),
        }

    health = _wsl_service_health(wsl, distro, retries=2)
    if health.get("transient"):
        return {
            "status": "wsl_transient",
            "message": ("WSL respondió con un error temporal del servicio de Windows. CLASS no se ha desinstalado y CZSpec no iniciará una compilación por este fallo. "
                        "Espera unos segundos y pulsa Diagnosticar de nuevo. Si persiste, reinicia WSL o Windows."),
            "detail": str(health.get("message") or ""),
        }
    if not health.get("ok"):
        return {
            "status": "wsl_unavailable",
            "message": "WSL no pudo iniciar la distribución seleccionada. Corrige WSL antes de instalar CLASS.",
            "detail": str(health.get("message") or ""),
        }

    report(8, f"Buscando instalaciones existentes en {distro}...")
    discovery = r'''set -e
for root in "$HOME" /opt /usr/local; do
  [ -d "$root" ] || continue
  find "$root" -maxdepth 6 -type f -name class -path '*/bin/class' -perm -111 2>/dev/null | head -n 1 && exit 0
done
exit 0'''
    try:
        proc = _run_hidden([wsl, "-d", distro, "--", "bash", "-lc", discovery],
                           capture_output=True, timeout=30, check=False)
        found = _clean_subprocess_text(proc.stdout).splitlines()
        if found:
            candidate = found[0].strip()
            if candidate and _wsl_test_executable(wsl, distro, candidate):
                report(100, "CLASS existente localizado.")
                backend = ClassBackend(kind="wsl", executable=candidate,
                                       display_name=f"CLASS vía WSL · {distro} · {candidate}",
                                       wsl_executable=wsl, wsl_distribution=distro)
                return {"status": "available", "backend": backend.provenance}
    except Exception:
        pass

    now = _datetime.datetime.now(_datetime.timezone.utc)
    branch = f"r{now:%y}-{now:%b}".lower()
    release = f"{now:%b}{now:%y}".lower()
    report(12, f"Preparando GILDAS {release} en {distro}...")
    script = f'''set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y git make gcc g++ gfortran libgtk-3-dev groff perl python3-dev python3-numpy python3-setuptools libcfitsio-dev libssl-dev libfftw3-dev
ROOT=/opt/czspec-gildas
SRC="$ROOT/gildas-src-{release}"
mkdir -p "$ROOT"
if [ -d "$SRC/.git" ]; then
  cd "$SRC"
  git fetch --all --tags
  git checkout {branch}
  git pull --ff-only || true
  make distclean || true
else
  rm -rf "$SRC"
  git clone --depth 1 -b {branch} https://git.iram.fr/gildas/gildas.git "$SRC"
  cd "$SRC"
fi
source admin/gildas-env.sh -c gfortran
make -j2
make install
CLASS_PATH="$(find "$ROOT" /root -maxdepth 7 -type f -name class -path '*/bin/class' -perm -111 2>/dev/null | head -n 1 || true)"
if [ -z "$CLASS_PATH" ]; then
  echo 'CZSPEC_ERROR=CLASS executable not found after GILDAS build' >&2
  exit 17
fi
echo "CZSPEC_CLASS_PATH=$CLASS_PATH"
'''
    report(18, "Instalando dependencias y compilando GILDAS/CLASS. Esto puede tardar varios minutos...")
    try:
        proc = _run_hidden([wsl, "-d", distro, "-u", "root", "--", "bash", "-lc", script],
                           capture_output=True, timeout=3600, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ClassBackendError("La instalación de GILDAS/CLASS excedió 60 minutos.") from exc
    stdout = _clean_subprocess_text(proc.stdout)
    stderr = _clean_subprocess_text(proc.stderr)
    if proc.returncode != 0:
        detail = (stderr or stdout)[-4000:]
        raise ClassBackendError(f"No se pudo instalar GILDAS/CLASS en WSL.\n{detail}")
    match = re.search(r"CZSPEC_CLASS_PATH=(/[^\r\n]+)", stdout)
    class_path = match.group(1).strip() if match else _find_class_in_wsl(wsl, distro)
    if not class_path or not _wsl_test_executable(wsl, distro, class_path):
        raise ClassBackendError("GILDAS terminó de compilar, pero CZSpec no pudo localizar el ejecutable CLASS.")
    report(100, "GILDAS/CLASS instalado correctamente.")
    backend = ClassBackend(kind="wsl", executable=class_path,
                           display_name=f"CLASS vía WSL · {distro} · {class_path}",
                           wsl_executable=wsl, wsl_distribution=distro)
    return {"status": "installed", "backend": backend.provenance}


def class_backend_diagnostics(
    *,
    preference: str | None = None,
    native_class_path: str | None = None,
    wsl_distribution: str | None = None,
    wsl_class_path: str | None = None,
) -> dict:
    """Diagnóstico compacto para la ventana de configuración de M1."""
    backend = find_class_backend(
        preference=preference,
        native_class_path=native_class_path,
        wsl_distribution=wsl_distribution,
        wsl_class_path=wsl_class_path,
    )
    wsl = find_wsl_executable() if _platform_is_windows() else None
    distros = list_wsl_distributions(wsl) if wsl else []
    wsl_health = None
    if _platform_is_windows() and wsl and distros and backend is None:
        requested = str(wsl_distribution or "").strip()
        distro = requested if requested in distros else distros[0]
        wsl_health = _wsl_service_health(wsl, distro, retries=2)
    return {
        "platform": sys.platform,
        "is_windows": _platform_is_windows(),
        "preference": str(preference or os.environ.get("CZSPEC_CLASS_BACKEND", "auto")),
        "wsl_executable": wsl,
        "wsl_distributions": distros,
        "wsl_health": wsl_health,
        "backend": backend.provenance if backend else None,
        "ok": backend is not None,
    }


def _manual_windows_to_wsl_path(value: str, distro: str | None = None) -> str | None:
    text = str(value).replace("/", "\\")
    # C:\Users\... -> /mnt/c/Users/...
    match = re.match(r"^([A-Za-z]):\\(.*)$", text)
    if match:
        drive = match.group(1).lower()
        tail = match.group(2).replace("\\", "/")
        return f"/mnt/{drive}/{tail}"

    # \\wsl$\Ubuntu\home\user -> /home/user (si coincide la distro).
    unc = re.match(r"^\\\\(?:wsl\$|wsl\.localhost)\\([^\\]+)\\(.*)$", text, re.I)
    if unc:
        found_distro = unc.group(1)
        if distro and found_distro.lower() != distro.lower():
            return None
        return "/" + unc.group(2).replace("\\", "/")
    return None


def host_path_for_class(path: str | Path, backend: ClassBackend | None = None) -> str:
    """Convierte una ruta del host a la ruta visible por el backend CLASS."""
    backend = backend or find_class_backend()
    if backend is None:
        raise ClassBackendError(class_backend_status()[1])

    raw = str(Path(path).expanduser().resolve())
    if backend.kind == "native":
        return raw

    if backend.kind != "wsl" or not backend.wsl_executable or not backend.wsl_distribution:
        raise ClassBackendError("Configuración WSL de CLASS incompleta.")

    # En pruebas POSIX puede instanciarse manualmente un backend WSL; una ruta POSIX
    # ya es válida y no necesita wslpath.
    if not _platform_is_windows() and raw.startswith("/"):
        return raw

    try:
        proc = _run_hidden(
            [
                backend.wsl_executable,
                "-d",
                backend.wsl_distribution,
                "--",
                "wslpath",
                "-a",
                "-u",
                raw,
            ],
            capture_output=True,
            timeout=8,
            check=False,
        )
        converted = _clean_subprocess_text(proc.stdout)
        converted = converted.splitlines()[-1].strip() if converted else ""
        if proc.returncode == 0 and converted.startswith("/"):
            return converted
    except Exception:
        pass

    fallback = _manual_windows_to_wsl_path(raw, backend.wsl_distribution)
    if fallback:
        return fallback
    raise ClassBackendError(
        f"No se pudo convertir la ruta de Windows para WSL: {raw}. "
        "Mueve el archivo a una unidad montada por WSL o revisa la configuración."
    )




def _run_wsl_backend_command(
    backend: ClassBackend,
    args: list[str],
    *,
    input_text: str | None = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    """Ejecuta una utilidad Linux dentro de la distro WSL configurada.

    Se usa sólo para operaciones auxiliares de ficheros (mktemp, ln, cat, rm).
    CLASS sigue ejecutándose por separado mediante :func:`_run_class`.
    """
    if backend.kind != "wsl" or not backend.wsl_executable or not backend.wsl_distribution:
        raise ClassBackendError("La operación auxiliar requiere un backend WSL válido.")
    try:
        return _run_hidden(
            [backend.wsl_executable, "-d", backend.wsl_distribution, "--", *args],
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ClassBackendError("WSL excedió el tiempo máximo en una operación auxiliar.") from exc
    except OSError as exc:
        raise ClassBackendError(f"No se pudo ejecutar una operación auxiliar en WSL: {exc}") from exc


@contextmanager
def _class_scratch_dir(backend: ClassBackend, prefix: str = "czs"):
    """Crea un directorio temporal con una ruta *muy corta* visible por CLASS.

    SIC/CLASS conserva varios argumentos de fichero en buffers de longitud fija.
    Una ruta típica de Windows convertida a ``/mnt/c/Users/...`` puede superar
    esos buffers, especialmente para los temporales internos de CZSpec. En WSL
    usamos por ello ``/tmp/czs.XXXXXX`` y leemos los resultados de vuelta con
    ``wsl.exe``. Esto también evita que ``LIST`` caiga a la salida paginada cuando
    ``/OUTPUT`` no puede decodificar un nombre demasiado largo.
    """
    if backend.kind != "wsl":
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=f"{prefix}_", dir=str(TEMP_DIR)) as td:
            yield {"host_dir": Path(td), "class_dir": str(Path(td))}
        return

    proc = _run_wsl_backend_command(
        backend,
        ["mktemp", "-d", f"/tmp/{prefix}.XXXXXX"],
        timeout=10,
    )
    scratch = _clean_subprocess_text(proc.stdout)
    scratch = scratch.splitlines()[-1].strip() if scratch else ""
    if proc.returncode != 0 or not scratch.startswith("/tmp/"):
        detail = _clean_subprocess_text(proc.stderr) or scratch or "mktemp no devolvió una ruta"
        raise ClassBackendError(f"No se pudo crear el temporal de CLASS dentro de WSL: {detail}")
    try:
        yield {"host_dir": None, "class_dir": scratch}
    finally:
        _run_wsl_backend_command(backend, ["rm", "-rf", "--", scratch], timeout=10)


def _stage_input_for_class(path: Path, backend: ClassBackend, class_dir: str) -> str:
    """Devuelve una ruta corta del archivo de entrada para CLASS.

    En WSL se crea primero un enlace simbólico corto en ``/tmp``. No se copia el
    fichero de datos; por tanto, incluso archivos .30m grandes no duplican espacio.
    Si el enlace no fuese posible, se usa una copia como último recurso.
    """
    if backend.kind != "wsl":
        return host_path_for_class(path, backend)

    source = host_path_for_class(path, backend)
    suffix = path.suffix if path.suffix else ".30m"
    target = f"{class_dir}/i{suffix}"
    proc = _run_wsl_backend_command(backend, ["ln", "-s", "--", source, target], timeout=15)
    if proc.returncode == 0:
        return target
    proc = _run_wsl_backend_command(backend, ["cp", "--", source, target], timeout=120)
    if proc.returncode != 0:
        detail = _clean_subprocess_text(proc.stderr) or "no se pudo preparar el archivo"
        raise ClassBackendError(f"No se pudo preparar el .30m para CLASS dentro de WSL: {detail}")
    return target


def _read_class_file(class_path: str, backend: ClassBackend, *, timeout: int = 30) -> str:
    """Lee un archivo generado por CLASS, incluso si vive en ``/tmp`` de WSL."""
    if backend.kind != "wsl":
        return Path(class_path).read_text(errors="replace")
    proc = _run_wsl_backend_command(backend, ["cat", "--", class_path], timeout=timeout)
    if proc.returncode != 0:
        detail = _clean_subprocess_text(proc.stderr) or "archivo no disponible"
        raise ClassBackendError(f"CLASS generó una salida que CZSpec no pudo recuperar: {detail}")
    return proc.stdout or ""

def _run_class(
    commands: list[str],
    timeout: int = 90,
    *,
    backend: ClassBackend | None = None,
) -> str:
    backend = backend or find_class_backend()
    if not backend:
        raise ClassBackendError(class_backend_status()[1])

    script = "\n".join(commands + ["exit", ""])
    run_env = os.environ.copy()
    if backend.kind == "native":
        # CZSpec puede arrancarse desde GNOME/KDE sin heredar el entorno de
        # una terminal. En una instalación estándar de GILDAS, ``class``
        # depende de librerías compartidas (p. ej. libclass.so) que el perfil
        # de GILDAS añade a LD_LIBRARY_PATH. Encontrar el binario no basta:
        # reconstruimos/cargamos su entorno antes de ejecutarlo.
        class_path = Path(backend.executable).expanduser().resolve()
        invocation = [str(class_path), "-nw"]

        try:
            # Estructura mensual habitual:
            #   <GAG_ROOT_DIR>/<GAG_EXEC_SYSTEM>/bin/class
            bin_dir = class_path.parent
            exec_dir = bin_dir.parent
            gag_root = exec_dir.parent
            gag_exec_system = exec_dir.name

            # Fallback explícito para que el cargador dinámico encuentre las
            # bibliotecas incluso si el perfil del usuario no está cargado.
            lib_candidates = [
                exec_dir / "lib",
                gag_root / "lib",
            ]
            existing_libs = [str(x) for x in lib_candidates if x.is_dir()]
            if existing_libs:
                current = str(run_env.get("LD_LIBRARY_PATH", "")).strip()
                parts = existing_libs + ([current] if current else [])
                run_env["LD_LIBRARY_PATH"] = os.pathsep.join(parts)

            profile = gag_root / "etc" / "bash_profile"
            shell = shutil.which("bash")
            if profile.is_file() and shell:
                # No dependemos de que CZSpec haya heredado ~/.bash_profile.
                # Cargamos el perfil concreto de la instalación detectada y
                # definimos GAG_* a partir de la propia ruta del ejecutable.
                shell_command = (
                    f"export GAG_ROOT_DIR={shlex.quote(str(gag_root))}; "
                    f"export GAG_EXEC_SYSTEM={shlex.quote(gag_exec_system)}; "
                    f"source {shlex.quote(str(profile))} >/dev/null 2>&1; "
                    f"exec {shlex.quote(str(class_path))} -nw"
                )
                invocation = [shell, "-lc", shell_command]
        except Exception:
            # Si la instalación tiene una disposición no estándar, se conserva
            # la ejecución directa con el entorno heredado/fallback disponible.
            pass
    elif backend.kind == "wsl":
        if not backend.wsl_executable or not backend.wsl_distribution:
            raise ClassBackendError("El backend WSL no contiene distribución o wsl.exe.")
        # Un shell de login no interactivo carga ~/.bash_profile y, por tanto,
        # el entorno de GILDAS. Evitamos ``-i``: CZSpec nunca necesita una shell
        # interactiva y así no se generan prompts ni efectos laterales.
        shell_command = f"exec {shlex.quote(backend.executable)} -nw"
        invocation = [
            backend.wsl_executable,
            "-d",
            backend.wsl_distribution,
            "--",
            "bash",
            "-lc",
            shell_command,
        ]
    else:
        raise ClassBackendError(f"Backend CLASS no reconocido: {backend.kind}")

    try:
        proc = _run_hidden(
            invocation,
            input=script,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=run_env,
        )
    except subprocess.TimeoutExpired as exc:
        raise ClassBackendError("CLASS excedió el tiempo máximo de procesamiento.") from exc
    except OSError as exc:
        raise ClassBackendError(f"No se pudo iniciar CLASS: {exc}") from exc

    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    error_lines = [
        line.strip() for line in output.splitlines()
        if re.match(r"^\s*(?:E-|F-|ERROR|FATAL)", line, flags=re.IGNORECASE)
    ]
    if proc.returncode != 0 or error_lines:
        detail = "\n".join(error_lines[-8:]) or output[-1800:]
        if any("SIC_CHAR" in line.upper() and "TOO LONG" in line.upper() for line in error_lines):
            detail += "\nCZSpec detectó un límite de longitud de argumento de SIC/CLASS; revise que está usando alpha.45 o posterior."
        raise ClassBackendError(f"CLASS no pudo completar la operación.\n{detail.strip()}")
    return output


def _parse_class_list(text: str) -> list[ClassObservation]:
    observations: list[ClassObservation] = []
    # Formato habitual: N;V Source Line Telescope Lambda Beta Sys Sca Sub
    pattern = re.compile(
        r"^\s*(\d+)\s*;\s*(\d+)\s+(\S+)\s+(\S+)\s+(\S+)(?:\s+|$)"
    )
    for line in text.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        number, version = int(match.group(1)), int(match.group(2))
        source, spectral_line, telescope = match.group(3), match.group(4), match.group(5)
        observations.append(
            ClassObservation(number, version, source, spectral_line, telescope)
        )
    return observations


def inspect_30m_file(file_path: str) -> list[ClassSetup]:
    """Devuelve grupos SOURCE/LINE/rango compatibles para importar un .30m."""
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"No se encontró el archivo: {path}")

    backend = find_class_backend()
    if not backend:
        raise ClassBackendError(class_backend_status()[1])

    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    with _class_scratch_dir(backend, "czsi") as scratch:
        class_dir = scratch["class_dir"]
        class_input = _stage_input_for_class(path, backend, class_dir)
        if backend.kind == "wsl":
            class_listing = f"{class_dir}/l.lis"
        else:
            listing = Path(scratch["host_dir"]) / "index.lis"
            class_listing = str(listing)
        output = _run_class([
            f"file in {_quote_class(class_input)}",
            "find",
            f"list /output {_quote_class(class_listing)}",
        ], backend=backend)
        try:
            text = _read_class_file(class_listing, backend)
        except Exception:
            # Sólo como respaldo: si LIST no produjo fichero pero sí salida corta,
            # intentamos interpretar stdout. Nunca activamos paginación a propósito.
            text = output

    observations = _parse_class_list(text)
    if not observations:
        raise ClassBackendError(
            "CLASS abrió el archivo, pero CZSpec no pudo interpretar su índice. "
            "Guarda el resultado de LIST en CLASS y repórtalo para ampliar el parser."
        )

    # En EMIR, H/V son dos polarizaciones del mismo subrango espectral.  Por
    # ejemplo, 30ME1HLI-F03 y 30ME1VLI-F04 comparten el rango LI, mientras que
    # HLO/VLO pertenecen al rango LO y deben quedar separados.  Agrupamos esas
    # polarizaciones antes del AVERAGE, pero CLASS conserva la última palabra con
    # CONSISTENCY.  Para cualquier TELESCOPE no reconocido usamos la cadena exacta.
    grouped: dict[tuple[str, str, str], list[ClassObservation]] = {}
    labels: dict[tuple[str, str, str], str] = {}
    for obs in observations:
        key = obs.average_key
        grouped.setdefault(key, []).append(obs)
        labels[key] = obs.average_group
    setups = []
    for key, items in grouped.items():
        exact_telescopes = tuple(sorted({obs.telescope for obs in items}))
        setups.append(
            ClassSetup(
                key[0], key[1], exact_telescopes, tuple(items), labels.get(key, key[2])
            )
        )
    return sorted(
        setups,
        key=lambda item: (item.source, item.line, item.average_label, item.telescope),
    )


def _read_greg_formatted_text(text: str) -> tuple[np.ndarray, np.ndarray]:
    """Interpreta la salida de ``GREG /FORMATTED`` tras ``SET UNIT F``."""
    rows = []
    for line in str(text).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("!", "#")):
            continue
        try:
            values = [float(token.replace("D", "E").replace("d", "e")) for token in stripped.split()]
        except ValueError:
            continue
        if len(values) >= 2:
            rows.append(values[:2])
    if len(rows) < 3:
        raise ClassBackendError("La exportación GREG de CLASS no contiene suficientes canales.")
    data = np.asarray(rows, dtype=float)
    frequency_mhz = data[:, 0]
    intensity = data[:, 1]
    finite = np.isfinite(frequency_mhz) & np.isfinite(intensity)
    frequency_mhz = frequency_mhz[finite]
    intensity = intensity[finite]
    if frequency_mhz.size < 3:
        raise ClassBackendError("CLASS no exportó canales finitos suficientes.")
    median_frequency = float(np.nanmedian(np.abs(frequency_mhz)))
    if median_frequency < 1.0e3:
        raise ClassBackendError(
            "CLASS devolvió un eje que no parece una frecuencia absoluta en MHz. "
            "Revisa SET UNIT F en tu versión de GILDAS antes de continuar."
        )
    order = np.argsort(frequency_mhz)
    return frequency_mhz[order], intensity[order]


def _read_greg_formatted(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Compatibilidad interna para salidas locales de GREG."""
    return _read_greg_formatted_text(Path(path).read_text(errors="replace"))


def _import_name(file_path: str, setup: ClassSetup, suffix: str) -> Path:
    """Ruta persistente del ``.dat`` que CLASS entrega a CZSpec.

    El archivo queda en ``outputs/class_imports`` para que el producto intermedio
    de la importación sea visible y reproducible, en lugar de vivir sólo en caché.
    """
    source = re.sub(r"[^A-Za-z0-9_.+-]+", "_", setup.source).strip("_") or "source"
    line = re.sub(r"[^A-Za-z0-9_.()+-]+", "_", setup.line).strip("_") or "line"
    telescope = re.sub(
        r"[^A-Za-z0-9_.()+-]+", "_", setup.average_label or "telescope"
    ).strip("_") or "telescope"
    digest = hashlib.sha1(
        (str(Path(file_path).resolve()) + repr(setup.key) + suffix).encode("utf-8")
    ).hexdigest()[:10]
    CLASS_IMPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return CLASS_IMPORT_OUTPUT_DIR / f"{source}_{line}_{telescope}_{suffix}_{digest}.dat"


def _selection_commands(setup: ClassSetup) -> list[str]:
    """Construye el índice CLASS con las observaciones exactas elegidas.

    Además del número de observación se especifican SOURCE, LINE y TELESCOPE.
    Esto hace que la selección sea explícita y evita que una observación con el
    mismo número pero perteneciente a otra configuración pueda entrar en el
    índice por accidente.
    """
    observations = tuple(setup.observations)
    if not observations:
        raise ValueError("No se seleccionó ninguna observación CLASS.")
    commands: list[str] = []
    for index, obs in enumerate(observations):
        prefix = "find" if index == 0 else "find append"
        commands.append(
            f"{prefix} /number {int(obs.number)} {int(obs.number)} "
            f"/source {obs.source} /line {obs.line} /telescope {obs.telescope}"
        )
    return commands



def _metadata_say_commands() -> list[str]:
    """Imprime variables de header CLASS con marcadores fáciles de parsear."""
    return [
        "say \"CZSPEC_META_SOURCE=\" 'SOURCE'",
        "say \"CZSPEC_META_TELESCOPE=\" 'TELESCOPE'",
        "say \"CZSPEC_META_LAMBDA=\" 'LAMBDA'",
        "say \"CZSPEC_META_BETA=\" 'BETA'",
        "say \"CZSPEC_META_EQUINOX=\" 'EQUINOX'",
        "say \"CZSPEC_META_REFERENCE=\" 'REFERENCE'",
        "say \"CZSPEC_META_FREQ_STEP=\" 'FREQ_STEP'",
        "say \"CZSPEC_META_VELO_STEP=\" 'VELO_STEP'",
        "say \"CZSPEC_META_VELOCITY=\" 'VELOCITY'",
        "say \"CZSPEC_META_FREQUENCY=\" 'FREQUENCY'",
        "say \"CZSPEC_META_BEAM_EFF=\" 'BEAM_EFF'",
        "say \"CZSPEC_META_FORWARD_EFF=\" 'FORWARD_EFF'",
    ]


def _parse_class_metadata(output: str) -> dict:
    values: dict[str, str] = {}
    pattern = re.compile(r"CZSPEC_META_([A-Z_]+)=\s*(.*?)\s*$", re.IGNORECASE)
    for line in str(output).splitlines():
        match = pattern.search(line)
        if match:
            values[match.group(1).upper()] = match.group(2).strip().strip('"')
    def number(name):
        try:
            value = float(values.get(name, '').replace('D','E').replace('d','e'))
            return value if math.isfinite(value) else None
        except Exception:
            return None
    meta = {}
    if values.get('SOURCE'):
        meta['raw_source_name'] = values['SOURCE']
    if values.get('TELESCOPE'):
        meta['telescope_header'] = values['TELESCOPE']
    lam, beta = number('LAMBDA'), number('BETA')
    if lam is not None:
        meta['ra_deg'] = math.degrees(lam) % 360.0
    if beta is not None:
        meta['dec_deg'] = math.degrees(beta)
    mappings = {
        'EQUINOX':'equinox', 'REFERENCE':'velocity_reference_channel',
        'FREQ_STEP':'frequency_step_mhz', 'VELO_STEP':'velocity_step_kms',
        # Legacy aliases are kept for backward compatibility with older CZSpec
        # sessions.  They must NOT be interpreted as a user-supplied VLSR/rest
        # transition when drawing the M1 display axes; the explicit CLASS axis
        # keys below are the authoritative spectral calibration.
        'VELOCITY':'vlsr_kms', 'FREQUENCY':'rest_frequency_mhz',
        'BEAM_EFF':'beam_eff', 'FORWARD_EFF':'forward_eff',
    }
    for src, dst in mappings.items():
        value = number(src)
        if value is not None:
            meta[dst] = value

    # Explicit native CLASS spectral-axis calibration.  These keys separate
    # the display conversion FREQUENCY <-> VELOCITY from the physical source
    # metadata used elsewhere in CZSpec (VLSR, transition rest frequency).
    class_axis = {
        'REFERENCE': 'class_reference_channel',
        'FREQUENCY': 'class_reference_frequency_mhz',
        'VELOCITY': 'class_reference_velocity_kms',
        'FREQ_STEP': 'class_frequency_step_mhz',
        'VELO_STEP': 'class_velocity_step_kms',
    }
    for src, dst in class_axis.items():
        value = number(src)
        if value is not None:
            meta[dst] = value
    meta['spectral_axis_calibration'] = 'CLASS native frequency/velocity header'
    meta['spectral_reference_frame'] = 'LSR (CLASS header)'
    meta['coordinate_system'] = 'ICRS/equatorial-like J2000 (CLASS SET SYSTEM EQUATORIAL 2000)'
    meta['coordinate_equinox'] = 2000.0
    if meta:
        meta['provenance'] = {'class_header': 'GILDAS/CLASS SIC header variables'}
    return meta


def _dat_header_lines(base: dict, extra: dict | None = None) -> str:
    data = dict(base)
    data.update(dict(extra or {}))
    lines = ['CZSpec CLASS import', 'columns: frequency_MHz intensity']
    for key, value in data.items():
        if key == 'provenance' or value in (None, '', []):
            continue
        if isinstance(value, (list, tuple, dict)):
            try:
                value = json.dumps(value, ensure_ascii=False)
            except Exception:
                value = str(value)
        lines.append(f'{key}={value}')
    return '\n'.join(lines)

def _spectral_sampling_metadata(frequency_mhz):
    frequency_mhz = np.asarray(frequency_mhz, dtype=float)
    spacing_mhz = float(np.nanmedian(np.diff(frequency_mhz)))
    center_mhz = max(float(np.nanmedian(np.abs(frequency_mhz))), 1e-12)
    spacing_kms = 2.99792458e5 * abs(spacing_mhz) / center_mhz
    return {
        "channel_spacing_mhz": abs(spacing_mhz),
        "channel_spacing_kms": float(spacing_kms),
        "effective_resolution_kms_approx": float(spacing_kms),
        "resolution_note": (
            "Muestreo del .dat exportado por CLASS. La resolución instrumental "
            "nativa puede diferir del espaciamiento entre canales."
        ),
    }


def export_setup(
    file_path: str,
    setup: ClassSetup,
    *,
    average: bool = True,
) -> list[dict]:
    """Convierte una selección del contenedor ``.30m`` en ``.dat`` de CZSpec.

    CLASS sólo interviene en esta frontera de importación:

    ``.30m -> selección -> CONSISTENCY -> AVERAGE -> GREG /FORMATTED -> .dat``.

    Si hay una sola observación, se carga directamente con ``GET`` y se exporta
    sin ejecutar un promedio innecesario. Para dos o más observaciones, CZSpec
    construye el índice exacto, ejecuta ``CONSISTENCY`` y sólo entonces
    ``AVERAGE``. No se usa ``/NOCHECK`` ni ``/RESAMPLE``.
    """
    path = Path(file_path).expanduser().resolve()
    observations = tuple(setup.observations)
    if not observations:
        raise ValueError("La configuración CLASS no contiene observaciones seleccionadas.")

    backend = find_class_backend()
    if not backend:
        raise ClassBackendError(class_backend_status()[1])

    # Una sola observación siempre se importa directamente. Con más de una,
    # ``average=False`` conserva la opción avanzada de importarlas por separado.
    if len(observations) == 1 or not average:
        exports: list[dict] = []
        for obs in observations:
            single_setup = ClassSetup(
                setup.source, setup.line, (obs.telescope,), (obs,), obs.telescope
            )
            suffix = f"obs{obs.number}v{obs.version}"
            final_path = _import_name(str(path), single_setup, suffix)
            with _class_scratch_dir(backend, "czso") as scratch:
                class_dir = scratch["class_dir"]
                class_input = _stage_input_for_class(path, backend, class_dir)
                if backend.kind == "wsl":
                    class_greg = f"{class_dir}/g.dat"
                else:
                    class_greg = str(Path(scratch["host_dir"]) / "spectrum.dat")
                commands = [
                    f"file in {_quote_class(class_input)}",
                    f"get {int(obs.number)} {int(obs.version)}",
                    # M1 normaliza las coordenadas de fuente a RA/DEC J2000 para
                    # que LAMBDA/BETA sean comparables entre archivos y útiles en M6.
                    "set system equatorial 2000",
                    *_metadata_say_commands(),
                    "set unit f",
                    f"greg {_quote_class(class_greg)} /formatted",
                ]
                class_output = _run_class(commands, timeout=180, backend=backend)
                class_meta = _parse_class_metadata(class_output)
                greg_text = _read_class_file(class_greg, backend, timeout=60)
                freq, inten = _read_greg_formatted_text(greg_text)
            base_meta = {
                "raw_source_name": setup.source, "line": setup.line, "telescope": obs.telescope,
                "observation": f"{obs.number};{obs.version}", "bunit": "K",
            }
            np.savetxt(
                final_path, np.column_stack([freq, inten]), fmt="%.9f %.10g",
                header=_dat_header_lines(base_meta, class_meta),
            )
            exports.append({
                "path": str(final_path),
                "source": setup.source,
                "raw_source_name": setup.source,
                "line": setup.line,
                "bunit": "K",
                **class_meta,
                "telescope": obs.telescope,
                "backends": [obs.telescope],
                "observation": obs.number,
                "version": obs.version,
                "n_averaged": 1,
                "average": False,
                "weighting": None,
                "allow_resample": False,
                "input_30m": str(path),
                "class_executable": backend.executable,
                "class_backend": backend.provenance,
                "selected_observations": [
                    {"number": obs.number, "version": obs.version, "telescope": obs.telescope}
                ],
                "class_commands": list(commands),
                "class_role": "import-only",
                "class_pipeline": "GET -> GREG /FORMATTED -> .dat",
                **_spectral_sampling_metadata(freq),
            })
        return exports

    suffix = f"avg{len(observations)}"
    final_path = _import_name(str(path), setup, suffix)
    with _class_scratch_dir(backend, "czsa") as scratch:
        class_dir = scratch["class_dir"]
        class_input = _stage_input_for_class(path, backend, class_dir)
        if backend.kind == "wsl":
            class_greg = f"{class_dir}/g.dat"
        else:
            class_greg = str(Path(scratch["host_dir"]) / "spectrum.dat")
        commands = [
            f"file in {_quote_class(class_input)}",
            *_selection_commands(setup),
            "consistency",
            "average",
            # La conversión se hace sólo después de CONSISTENCY/AVERAGE; no altera
            # qué observaciones son compatibles ni los datos espectrales.
            "set system equatorial 2000",
            *_metadata_say_commands(),
            "set unit f",
            f"greg {_quote_class(class_greg)} /formatted",
        ]
        class_output = _run_class(commands, timeout=180, backend=backend)
        class_meta = _parse_class_metadata(class_output)
        greg_text = _read_class_file(class_greg, backend, timeout=60)
        freq, inten = _read_greg_formatted_text(greg_text)

    base_meta = {
        "raw_source_name": setup.source, "line": setup.line,
        "average_group": setup.average_label, "telescopes": setup.telescope,
        "averaged": len(observations), "weight": "TIME(default)", "bunit": "K",
    }
    np.savetxt(final_path, np.column_stack([freq, inten]), fmt="%.9f %.10g",
               header=_dat_header_lines(base_meta, class_meta))
    return [{
        "path": str(final_path),
        "source": setup.source,
        "raw_source_name": setup.source,
        "line": setup.line,
        "bunit": "K",
        **class_meta,
        "telescope": setup.average_label,
        "average_group": setup.average_label,
        "backends": list(setup.telescopes),
        "n_averaged": len(observations),
        "average": True,
        "weighting": "TIME (CLASS default)",
        "allow_resample": False,
        "input_30m": str(path),
        "class_executable": backend.executable,
        "class_backend": backend.provenance,
        "selected_observations": [
            {"number": obs.number, "version": obs.version, "telescope": obs.telescope}
            for obs in observations
        ],
        "class_commands": list(commands),
        "class_role": "import-only",
        "class_pipeline": "CONSISTENCY -> AVERAGE -> GREG /FORMATTED -> .dat",
        **_spectral_sampling_metadata(freq),
    }]


def reprocess_export_from_metadata(
    metadata: dict,
    *,
    smooth_method: str = "none",
    smooth_value: float | int | None = None,
) -> dict:
    """Compatibilidad con sesiones alfa anteriores.

    Desde alpha.48 CLASS ya no realiza SMOOTH. La función regenera únicamente el
    ``.dat`` base de la importación y rechaza una petición de suavizado para que
    ninguna ruta de código vuelva a delegar análisis posterior en CLASS.
    """
    if str(smooth_method or "none").lower() != "none":
        raise ClassBackendError(
            "Desde CZSpec alpha.48 el suavizado pertenece a CZSpec y no se ejecuta en CLASS."
        )
    meta = dict(metadata or {})
    input_30m = str(meta.get("input_30m") or "").strip()
    if not input_30m:
        raise ValueError("La sesión no conserva el archivo .30m original.")
    source = str(meta.get("source") or "").strip()
    line = str(meta.get("line") or "").strip()
    selected = list(meta.get("selected_observations") or [])
    if not source or not line or not selected:
        raise ValueError("La sesión .30m no conserva SOURCE/LINE/observaciones suficientes.")
    observations = tuple(
        ClassObservation(
            int(row.get("number")),
            int(row.get("version", 1)),
            source,
            line,
            str(row.get("telescope") or meta.get("telescope") or "").strip(),
        )
        for row in selected
    )
    telescopes = tuple(sorted({obs.telescope for obs in observations if obs.telescope}))
    setup = ClassSetup(source, line, telescopes, observations)
    exports = export_setup(input_30m, setup, average=bool(meta.get("average", False)))
    if len(exports) != 1:
        raise ClassBackendError(
            f"CLASS devolvió {len(exports)} espectros al regenerar una importación; se esperaba 1."
        )
    return exports[0]

