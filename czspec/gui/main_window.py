import json
import importlib
import importlib.util
import sys
import re
import os
import inspect
import hashlib
import base64
import subprocess
import traceback
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import pandas as pd

from PySide6.QtCore import (
    Qt,
    QUrl,
    QObject,
    QRunnable,
    QThreadPool,
    QTimer,
    QSettings,
    QProcess,
    Signal,
    Slot,
)
from PySide6.QtGui import QColor, QIcon, QPixmap, QFont, QDesktopServices
from PySide6.QtWebChannel import QWebChannel
import numpy as np
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QPushButton,
    QLabel,
    QTextEdit,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QMessageBox,
    QSplitter,
    QGroupBox,
    QFormLayout,
    QDoubleSpinBox,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QLineEdit,
    QDialog,
    QTabWidget,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSpinBox,
    QCheckBox,
    QScrollArea,
    QDialogButtonBox,
    QLayout,
    QColorDialog,
    QSizeGrip,
    QFrame,
    QProgressBar,
    QButtonGroup,
    QSizePolicy,
    QInputDialog,
    QFontComboBox,
    QStyle,
)
from czspec import __public_version__, __version__
from czspec.network import PROJECT_URL
from czspec.plot_styles import DEFAULT_PLOT_STYLES
from czspec.science_defaults import (
    DEFAULT_DETECTION_SIGMA,
    DEFAULT_ISOTOPIC_ABUNDANCE_RATIOS,
)
from czspec.table_schema import column_display_name, column_tooltip
from czspec.utils.export_utils import (
    TABLES_DIR,
    IMAGES_DIR,
    export_dataframe_to_csv,
    export_html_text,
    open_folder_in_system,
)

from czspec.paths import (
    CDMS_ABC_PATH,
    COLUMN_DENSITY_LATEX_DIR,
    COLUMN_DENSITY_OUTPUT_DIR,
    COLUMN_DENSITY_GRAPHICS_DIR,
    COLUMN_DENSITY_TABLES_DIR,
    COLUMN_DENSITY_IMAGES_DIR,
    JPL_ABC_PATH,
    LTE_MODEL_OUTPUT_DIR,
    LTE_GRAPHICS_DIR,
    LTE_TABLES_DIR,
    LTE_IMAGES_DIR,
    NONLTE_OUTPUT_DIR,
    NONLTE_GRAPHICS_DIR,
    NONLTE_TABLES_DIR,
    NONLTE_IMAGES_DIR,
    PEAK_DETECTION_OUTPUT_DIR,
    PEAK_GRAPHICS_DIR,
    PEAK_TABLES_DIR,
    PEAK_IMAGES_DIR,
    SANHUEZA_OUTPUT_DIR,
    SPECIES_LATEX_DIR,
    SPECIES_SEARCH_OUTPUT_DIR,
    SPECIES_GRAPHICS_DIR,
    SPECIES_TABLES_DIR,
    SPECIES_IMAGES_DIR,
    TEMP_DIR,
    VASYUNINA_OUTPUT_DIR,
    WORKSPACE_DIR,
    CZSPEC_ICON_PATH,
    application_icon_path,
)
from czspec.updater import install_update_package
from czspec.theme import build_app_stylesheet


# Los motores científicos se importan solo cuando se usan. En Windows esto
# evita cargar SciPy, Matplotlib, Astropy, Astroquery y Plotly durante el
# arranque inicial de la ventana.
def load_raw_spectrum(*args, **kwargs):
    from czspec.logic.peak_detection import load_raw_spectrum as implementation
    return implementation(*args, **kwargs)


def build_spectrum_comparison(*args, **kwargs):
    from czspec.logic.peak_detection import build_spectrum_comparison as implementation
    return implementation(*args, **kwargs)


def run_peak_detection(*args, **kwargs):
    from czspec.logic.peak_detection import run_peak_detection as implementation
    return implementation(*args, **kwargs)


def save_plot_json_to_png(*args, **kwargs):
    from czspec.logic.peak_detection import save_plot_json_to_png as implementation
    return implementation(*args, **kwargs)

def save_plot_json_to_file(*args, **kwargs):
    from czspec.logic.peak_detection import save_plot_json_to_file as implementation
    return implementation(*args, **kwargs)


def intensity_conversion_factor(*args, **kwargs):
    from czspec.logic.peak_detection import intensity_conversion_factor as implementation
    return implementation(*args, **kwargs)


def intensity_conversion_factor_at_frequency(*args, **kwargs):
    from czspec.logic.peak_detection import intensity_conversion_factor_at_frequency as implementation
    return implementation(*args, **kwargs)


def normalize_intensity_unit(*args, **kwargs):
    from czspec.logic.peak_detection import normalize_intensity_unit as implementation
    return implementation(*args, **kwargs)


def class_backend_status(*args, **kwargs):
    from czspec.logic.class30m import class_backend_status as implementation
    return implementation(*args, **kwargs)


def class_backend_diagnostics(*args, **kwargs):
    from czspec.logic.class30m import class_backend_diagnostics as implementation
    return implementation(*args, **kwargs)


def install_or_repair_class_backend(*args, **kwargs):
    from czspec.logic.class30m import install_or_repair_class_backend as implementation
    return implementation(*args, **kwargs)


def list_wsl_distributions(*args, **kwargs):
    from czspec.logic.class30m import list_wsl_distributions as implementation
    return implementation(*args, **kwargs)


def inspect_30m_file(*args, **kwargs):
    from czspec.logic.class30m import inspect_30m_file as implementation
    return implementation(*args, **kwargs)


def export_class_setup(*args, **kwargs):
    from czspec.logic.class30m import export_setup as implementation
    return implementation(*args, **kwargs)





def source_registry():
    from czspec.logic.source_metadata import SourceRegistry
    return SourceRegistry()

def merge_source_metadata(*args):
    from czspec.logic.source_metadata import merge_metadata
    return merge_metadata(*args)

def resolve_source_simbad(**kwargs):
    from czspec.logic.source_metadata import resolve_simbad
    return resolve_simbad(**kwargs)

def resolve_source_simbad_candidates(**kwargs):
    from czspec.logic.source_metadata import resolve_simbad_candidates
    return resolve_simbad_candidates(**kwargs)

def format_source_ra(*args, **kwargs):
    from czspec.logic.source_metadata import format_ra_hms
    return format_ra_hms(*args, **kwargs)

def format_source_dec(*args, **kwargs):
    from czspec.logic.source_metadata import format_dec_dms
    return format_dec_dms(*args, **kwargs)

def parse_source_ra(*args, **kwargs):
    from czspec.logic.source_metadata import parse_ra_hms
    return parse_ra_hms(*args, **kwargs)

def parse_source_dec(*args, **kwargs):
    from czspec.logic.source_metadata import parse_dec_dms
    return parse_dec_dms(*args, **kwargs)


def inspect_fits_file(*args, **kwargs):
    from czspec.logic.fits_io import inspect_fits_file as implementation
    return implementation(*args, **kwargs)

def extract_fits_spectrum(*args, **kwargs):
    from czspec.logic.fits_io import extract_fits_spectrum as implementation
    return implementation(*args, **kwargs)

def automatic_calibration(*args, **kwargs):
    from czspec.logic.calibration import automatic_calibration as implementation
    return implementation(*args, **kwargs)

def iram30m_reference_profile(*args, **kwargs):
    from czspec.logic.calibration import iram30m_reference_profile as implementation
    return implementation(*args, **kwargs)

def load_custom_calibration_profiles(*args, **kwargs):
    from czspec.logic.calibration import load_custom_profiles as implementation
    return implementation(*args, **kwargs)

def save_custom_calibration_profiles(*args, **kwargs):
    from czspec.logic.calibration import save_custom_profiles as implementation
    return implementation(*args, **kwargs)

def smooth_ascii_spectrum(*args, **kwargs):
    from czspec.logic.smoothing import smooth_ascii_file as implementation
    return implementation(*args, **kwargs)


def SpeciesSearchConfig(*args, **kwargs):
    from czspec.logic.species_search import SpeciesSearchConfig as implementation
    return implementation(*args, **kwargs)


def run_species_search(*args, **kwargs):
    from czspec.logic.species_search import run_species_search as implementation
    return implementation(*args, **kwargs)


def partition_function_for_row(*args, **kwargs):
    from czspec.logic.species_search import partition_function_for_row as implementation
    return implementation(*args, **kwargs)


def LTEModelConfig(*args, **kwargs):
    from czspec.logic.lte_model import LTEModelConfig as implementation
    return implementation(*args, **kwargs)


def LTEComponentSpec(*args, **kwargs):
    from czspec.logic.lte_model import LTEComponentSpec as implementation
    return implementation(*args, **kwargs)


def iram_30m_hpbw_arcsec(*args, **kwargs):
    from czspec.logic.lte_model import iram_30m_hpbw_arcsec as implementation
    return implementation(*args, **kwargs)


def query_splatalogue_transitions(*args, **kwargs):
    from czspec.logic.lte_model import query_splatalogue_transitions as implementation
    return implementation(*args, **kwargs)


def radio_velocity_offset_kms(*args, **kwargs):
    from czspec.logic.lte_model import radio_velocity_offset_kms as implementation
    return implementation(*args, **kwargs)


def simulate_lte_spectrum(*args, **kwargs):
    from czspec.logic.lte_model import simulate_lte_spectrum as implementation
    return implementation(*args, **kwargs)


def simulate_lte_components(*args, **kwargs):
    from czspec.logic.lte_model import simulate_lte_components as implementation
    return implementation(*args, **kwargs)


def lte_fit_metrics(*args, **kwargs):
    from czspec.logic.lte_model import lte_fit_metrics as implementation
    return implementation(*args, **kwargs)


def refine_lte_components(*args, **kwargs):
    from czspec.logic.lte_model import refine_lte_components as implementation
    return implementation(*args, **kwargs)


def available_lte_tex_values(*args, **kwargs):
    from czspec.logic.lte_session import available_tex_values as implementation
    return implementation(*args, **kwargs)


def aggregate_global_lte_solutions(*args, **kwargs):
    from czspec.logic.lte_session import aggregate_global_solutions as implementation
    return implementation(*args, **kwargs)


def lte_transitions_for_species(*args, **kwargs):
    from czspec.logic.lte_session import transitions_for_species as implementation
    return implementation(*args, **kwargs)


def simulate_lte_session(*args, **kwargs):
    from czspec.logic.lte_session import simulate_lte_session as implementation
    return implementation(*args, **kwargs)


def NonLTEComponentSpec(*args, **kwargs):
    from czspec.logic.nonlte_model import NonLTEComponentSpec as implementation
    return implementation(*args, **kwargs)


def simulate_nonlte_session(*args, **kwargs):
    from czspec.logic.nonlte_model import simulate_nonlte_session as implementation
    return implementation(*args, **kwargs)


def run_vasyunina_from_dataframe(*args, **kwargs):
    from czspec.logic.vasyunina import run_vasyunina_from_dataframe as implementation
    return implementation(*args, **kwargs)


def run_sanhueza_from_dataframe(*args, **kwargs):
    from czspec.logic.sanhueza import run_sanhueza_from_dataframe as implementation
    return implementation(*args, **kwargs)


def prepare_plotly_view_file(*args, **kwargs):
    from czspec.utils.plotly_runtime import prepare_plotly_view_file as implementation
    return implementation(*args, **kwargs)


LINE_STYLE_OPTIONS = (
    ("Continua", "solid"),
    ("Guiones", "dash"),
    ("Punteada", "dot"),
    ("Guion y punto", "dashdot"),
    ("Guiones largos", "longdash"),
)

PLOT_STYLE_LABELS = {
    "spectrum": "Espectro cargado / corregido por η",
    "baseline": "Ajuste de línea base",
    "corrected": "Espectro corregido por base",
    "fits": "Perfiles ajustados",
    "detections": "Detecciones",
}


def _column_visible_by_default(table_widget: QTableWidget, column_name: str) -> bool:
    """Devuelve la vista científica inicial sin retirar datos de la tabla."""

    profile = str(table_widget.property("czspecColumnProfile") or "")
    name = str(column_name)

    common_identification = {
        "obs_id",
        "Source",
        "name",
        "chemical_name",
        "linelist",
        "ν_obs_MHz",
        "orderedfreq",
        "source_vlsr_kms",
        "v_line_radio_kms",
        "delta_v_lsr_kms",
        "Δν_MHz",
        "aij",
        "upperStateDegen",
        "T_A [K]",
        "Δv [Km/s]",
        "σ_Δv [Km/s]",
        "IntInt [K*Km/s]",
        "σ_IntInt [K*Km/s]",
    }

    is_partition_value = re.fullmatch(r"Q_[0-9]+(?:\.[0-9]+)?K", name) is not None

    if profile == "species_main":
        return name in common_identification or is_partition_value

    if profile == "species_topk":
        return name in common_identification or name in {
            "selected",
            "rank",
        } or is_partition_value

    if profile == "column_density_source":
        return name in common_identification or is_partition_value

    if profile == "column_density_mod":
        return (
            name in common_identification
            or is_partition_value
            or name.startswith("N_tot_")
        )

    if profile == "column_density_mth":
        return (
            name in common_identification
            or name in {"Tex [K]", "n_refs_validas"}
            or re.fullmatch(r"ref_\d+_name", name) is not None
            or re.fullmatch(r"tau_\d+", name) is not None
            or re.fullmatch(r"N_\d+_cm2", name) is not None
            or re.fullmatch(r"sigma_N_\d+_cm2", name) is not None
        )

    return True


def _table_header_internal_name(header_item, fallback: str = "") -> str:
    if header_item is None:
        return fallback
    internal_name = header_item.data(Qt.UserRole)
    return str(internal_name) if internal_name not in (None, "") else str(header_item.text())


def _set_scientific_table_headers(table_widget: QTableWidget, columns) -> None:
    owner = table_widget.window() if table_widget is not None else None
    language = str(getattr(owner, "ui_language", getattr(owner, "language", "es")) or "es")
    for column_index, column_name in enumerate(columns):
        internal_name = str(column_name)
        item = QTableWidgetItem(_scientific_column_ui_label(internal_name, language))
        item.setData(Qt.UserRole, internal_name)
        item.setToolTip(column_tooltip(internal_name))
        table_widget.setHorizontalHeaderItem(column_index, item)


class TaskSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(object)
    progress = Signal(int, str)
    finished = Signal()


class BackgroundTask(QRunnable):
    """Ejecuta una función sin bloquear el ciclo de eventos de Qt."""

    def __init__(self, function):
        super().__init__()
        self.setAutoDelete(False)
        self.function = function
        self.signals = TaskSignals()

    @Slot()
    def run(self):
        try:
            self.signals.progress.emit(0, "Preparando tarea")
            parameters = inspect.signature(self.function).parameters
            if parameters:
                result = self.function(self.report_progress)
            else:
                result = self.function()
            self.signals.progress.emit(100, "Completado")
        except Exception as exc:
            self.signals.failed.emit((str(exc), traceback.format_exc()))
        else:
            self.signals.succeeded.emit(result)
        finally:
            self.signals.finished.emit()

    def report_progress(self, value: int | float, message: str = ""):
        value = max(0, min(100, int(round(float(value)))))
        self.signals.progress.emit(value, str(message or ""))


class ToastNotification(QFrame):
    """Aviso legible, temporal y no modal."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("toastNotification")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(380)
        self.setMaximumWidth(480)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 11, 10, 11)
        layout.setSpacing(10)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        self.title_label = QLabel()
        self.title_label.setObjectName("toastTitle")
        self.message_label = QLabel()
        self.message_label.setObjectName("toastMessage")
        self.message_label.setWordWrap(True)
        self.message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.message_label)

        close_button = QPushButton("×")
        close_button.setObjectName("toastCloseButton")
        close_button.setFixedSize(26, 26)
        close_button.setToolTip("Cerrar notificación")
        close_button.clicked.connect(self.hide)

        layout.addLayout(text_layout, stretch=1)
        layout.addWidget(close_button, alignment=Qt.AlignTop)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)
        self.hide()

    def show_message(self, title: str, message: str, duration_ms: int = 6500):
        self.title_label.setText(title)
        self.message_label.setText(message)
        self.adjustSize()
        self.show()
        self.raise_()
        self.timer.start(duration_ms)


class FilterCheckBox(QCheckBox):
    """Filtro textual compacto sin cuadrados persistentes en la etiqueta.

    El estado se comunica mediante el color/realce del propio texto. Ocultamos
    el indicador nativo para evitar que distintos temas de Qt dejen un cuadro
    blanco residual al deseleccionar.
    """

    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        self._label = label
        self.setObjectName("filterCheckBox")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "QCheckBox#filterCheckBox::indicator { width: 0px; height: 0px; }"
            "QCheckBox#filterCheckBox { padding: 4px 7px; border-radius: 5px; }"
            "QCheckBox#filterCheckBox:checked { color: #2563EB; font-weight: 700; background: rgba(37,99,235,0.10); }"
        )

    def setText(self, text: str):
        self._label = str(text)
        super().setText(self._label)



def _scientific_column_ui_label(column_name: object, language: str = "es") -> str:
    """Scientific, compact UI label for selectable table columns.

    DataFrame/internal field names are deliberately left untouched.  This
    function is presentation-only so exports remain fully reproducible.
    """
    name = str(column_name)
    es = language != "en"
    m1 = {
        "Line": "Línea" if es else "Line",
        "Source": "Fuente" if es else "Source",
        "ν[MHz]": "νₒᵦₛ [MHz]",
        "v_LSR[km/s]": "vₗₛᵣ [km s⁻¹]",
        "Δv_fuente[km/s]": "Δv(fuente) [km s⁻¹]" if es else "Δv(source) [km s⁻¹]",
        "T_A [K]": "Tₐ* [K]",
        "Δv [Km/s]": "FWHM [km s⁻¹]",
        "σ_Δv [Km/s]": "σ(FWHM) [km s⁻¹]",
        "IntInt [K*Km/s]": "∫ Tₐ* dv [K km s⁻¹]",
        "σ_IntInt [K*Km/s]": "σ(∫ Tₐ* dv) [K km s⁻¹]",
        "GOI": "Grupo de ajuste" if es else "Fit group",
        "Ajuste": "Perfil ajustado" if es else "Fit profile",
        "SNR": "S/N",
        "Confianza": "Confianza" if es else "Confidence",
        "Tipo": "Tipo" if es else "Type",
        "Origen": "Origen" if es else "Origin",
    }
    if name in m1:
        return m1[name]
    label = column_display_name(name)
    # Keep the user-facing source name concise; the internal path remains in source_path.
    if name == "Source":
        return "Source" if language == "en" else "Fuente"
    if language == "en":
        translations = {
            "Selección": "Selection", "ID de observación": "Observation ID",
            "Posición TOP-K": "TOP-K rank", "Especie / transición": "Species / transition",
            "Nombre químico": "Chemical name", "Fórmula base": "Base formula",
            "Catálogo espectroscópico": "Spectroscopic catalog",
            "ν observada [MHz]": "Observed ν [MHz]", "ν de reposo [MHz]": "Rest ν [MHz]",
            "Archivo fuente": "Source file", "ID de línea": "Line ID",
            "Tipo de ajuste": "Fit type", "Perfil ajustado": "Fit profile",
            "Temperatura pico observada [K]": "Observed peak temperature [K]",
            "Amplitud pico ajustada [K]": "Fitted peak amplitude [K]",
            "Puntuación del candidato": "Candidate score", "Modo de identificación": "Identification mode",
            "Identificación ampliada": "Expanded identification",
            "Fuente de Q(T)": "Q(T) source", "Especie usada para Q(T)": "Species used for Q(T)",
            "Clave interna de Q(T)": "Internal Q(T) key",
            "Tₑₓ [K]": "Tₑₓ [K]", "N total [cm⁻²]": "Total N [cm⁻²]",
            "σ(N total) [cm⁻²]": "σ(Total N) [cm⁻²]",
            "Función de partición Q(T)": "Partition function Q(T)",
            "Profundidad óptica τ": "Optical depth τ", "Método": "Method",
            "Transición de referencia": "Reference transition",
            "Referencias válidas": "Valid references", "Pares evaluados": "Pairs evaluated",
            "Tipo de ajuste": "Fit type", "Perfil ajustado": "Fit profile",
            "Velocidad de la línea [km s⁻¹]": "Line velocity [km s⁻¹]",
            "VLSR de la fuente [km s⁻¹]": "Source VLSR [km s⁻¹]",
            "ν esperada a VLSR [MHz]": "Expected ν at VLSR [MHz]",
            "Δν respecto a VLSR [MHz]": "Δν from VLSR [MHz]",
            "Δv respecto a VLSR [km s⁻¹]": "Δv from VLSR [km s⁻¹]",
            "Eᵤ/k [K]": "Eᵤ/k [K]", "Eₗ/k [K]": "Eₗ/k [K]",
            "Degeneración superior gᵤ": "Upper-state degeneracy gᵤ",
        }
        label = translations.get(label, label)
        m = re.fullmatch(r"Transición de referencia (\d+)", label)
        if m: label = f"Reference transition {m.group(1)}"
        m = re.fullmatch(r"Profundidad óptica τ \((\d+)\)", label)
        if m: label = f"Optical depth τ ({m.group(1)})"
        m = re.fullmatch(r"N total \(([^)]+)\) \[cm⁻²\]", label)
        if m: label = f"Total N ({m.group(1)}) [cm⁻²]"
        m = re.fullmatch(r"σ\[N total \(([^)]+)\)\] \[cm⁻²\]", label)
        if m: label = f"σ[Total N ({m.group(1)})] [cm⁻²]"
    return label


def _apply_action_role(widget: QWidget, role: str) -> None:
    """Assign a semantic visual role without changing widget behavior."""
    if widget is None:
        return
    widget.setProperty("actionRole", str(role))
    try:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
    except Exception:
        pass


def _unique_output_path(path: Path) -> Path:
    """Avoid silent overwrites using a stable, human-readable counter.

    Reusing the same save label never destroys a previous product.  The first
    collision becomes ``_001``, then ``_002`` and so on.  A timestamp is only
    used as a defensive fallback after an unrealistically large number of
    collisions.
    """
    path = Path(path)
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for index in range(1, 10000):
        candidate = path.with_name(f"{stem}_{index:03d}{suffix}")
        if not candidate.exists():
            return candidate
    return path.with_name(f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}")


def _localize_plot_trace_names(figure: dict, language: str) -> dict:
    """Localize common M1/M2 legend labels at display time.

    This is intentionally non-destructive: scientific data and saved DataFrames
    are not changed.  It also fixes figures created before a language switch.
    """
    if not isinstance(figure, dict):
        return figure
    en = language == "en"
    fixed = {
        "Espectro corregido por η": "Efficiency-corrected spectrum",
        "Ajuste de base": "Baseline fit",
        "Espectro corregido por base": "Baseline-corrected spectrum",
        "Detecciones": "Detections",
        "Residual final": "Final residual",
        "Componentes individuales": "Individual components",
        "Perfiles finales": "Final profiles",
        "Referencias VLSR": "VLSR references",
    }
    reverse = {v: k for k, v in fixed.items()}
    for trace in figure.get("data", []) or []:
        name = str(trace.get("name") or "")
        if en:
            if name in fixed:
                trace["name"] = fixed[name]
            elif name.startswith("Componente L"):
                trace["name"] = name.replace("Componente L", "Component L", 1)
            elif name.startswith("Suma grupo "):
                trace["name"] = name.replace("Suma grupo ", "Group sum ", 1)
            elif name.startswith("Ajuste L"):
                trace["name"] = name.replace("Ajuste L", "Fit L", 1)
        else:
            if name in reverse:
                trace["name"] = reverse[name]
            elif name.startswith("Component L"):
                trace["name"] = name.replace("Component L", "Componente L", 1)
            elif name.startswith("Group sum "):
                trace["name"] = name.replace("Group sum ", "Suma grupo ", 1)
            elif name.startswith("Fit L"):
                trace["name"] = name.replace("Fit L", "Ajuste L", 1)
    return figure


class AppHeader(QWidget):
    """Barra de título compacta con movimiento nativo y respaldo manual."""

    def __init__(self, window: QMainWindow):
        super().__init__(window)
        self._window = window
        self._drag_offset = None
        self.setObjectName("appHeader")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            window_handle = self._window.windowHandle()
            if window_handle is not None and window_handle.startSystemMove():
                event.accept()
                return

            self._drag_offset = (
                event.globalPosition().toPoint()
                - self._window.frameGeometry().topLeft()
            )
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self._drag_offset is not None
            and event.buttons() & Qt.MouseButton.LeftButton
            and not self._window.isMaximized()
        ):
            self._window.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._window.toggle_window_size()
            event.accept()
            return

        super().mouseDoubleClickEvent(event)


class FullScreenPlotDialog(QDialog):
    def __init__(self, plot_json: str, mode: str = "interactive", parent=None):
        # Debe ser una ventana de nivel superior. En Windows, un QDialog hijo de
        # la ventana principal sin bordes puede quedar reducido a una franja.
        super().__init__(parent, Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("Visualización en pantalla completa")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setStyleSheet("QDialog { background: #FFFFFF; }")

        self.plot_json = plot_json
        self.mode = mode

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        from PySide6.QtWebEngineCore import QWebEngineSettings
        from PySide6.QtWebEngineWidgets import QWebEngineView

        toolbar = QHBoxLayout()
        toolbar.addStretch()
        self.close_button = QPushButton("Salir de pantalla completa")
        self.close_button.clicked.connect(self.close)
        toolbar.addWidget(self.close_button)

        self.plot_view = QWebEngineView(self)
        self.plot_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addLayout(toolbar)
        layout.addWidget(self.plot_view, stretch=1)

        self.plot_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
            True,
        )
        self.plot_view.loadFinished.connect(self._on_page_loaded)
        self._initialize_plotly_container()

    def open_fullscreen(self):
        """Muestra la ventana después de construir el WebEngine y su layout."""

        self.show()
        QTimer.singleShot(0, self.showFullScreen)

    def _initialize_plotly_container(self):
        page_path = prepare_plotly_view_file()
        self.plot_view.load(QUrl.fromLocalFile(str(page_path)))

    def _on_page_loaded(self, ok: bool):
        if not ok:
            return

        payload = json.dumps(self.plot_json)
        mode = json.dumps(self.mode)
        js = (
            f"window.czspecRender({payload}, {mode}, false);"
            "setTimeout(function(){"
            "const gd=document.getElementById('plot');"
            "if(gd && window.Plotly){Plotly.Plots.resize(gd);}}, 60);"
        )
        self.plot_view.page().runJavaScript(js)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


class PlotStyleDialog(QDialog):
    """Editor visual de trazas y configuración de ejes de M1.

    a88 presents the four display axes directly (X1/X2/Y1/Y2).  Internally the
    canonical spectrum remains frequency in MHz, so this is a presentation
    layer only and older settings stay compatible.
    """

    DEFAULT_AXIS_CONFIG = {
        "orientation": "horizontal",
        "primary_spectral": "frequency",
        "secondary_spectral": "velocity",
        "frequency_unit": "auto",
        "velocity_unit": "km/s",
        "wavelength_unit": "mm",
        "intensity_unit": "native",
        "secondary_intensity_unit": "none",
        "primary_axis_title": "",
        "secondary_axis_title": "",
        "intensity_axis_title": "",
        "secondary_intensity_title": "",
        "primary_axis_title_preset": "auto",
        "secondary_axis_title_preset": "auto",
        "intensity_axis_title_preset": "auto",
        "secondary_intensity_title_preset": "auto",
        "graph_title_mode": "auto",
        "graph_title": "",
        "show_detection_labels": True,
    }

    def __init__(self, current_styles: dict, axis_config: dict | None = None, language: str = "es", native_intensity_unit: str | None = None, parent=None):
        super().__init__(parent)
        self.language = language
        self.native_intensity_unit = normalize_intensity_unit(native_intensity_unit)
        self.setWindowTitle("Estilos y ejes de la gráfica" if language == "es" else "Plot styles and axes")
        self.resize(780, 700)
        self.setMinimumSize(600, 500)
        self.styles = deepcopy(DEFAULT_PLOT_STYLES)
        for role, values in (current_styles or {}).items():
            if role in self.styles and isinstance(values, dict):
                self.styles[role].update(values)
        self.axis_config = deepcopy(self.DEFAULT_AXIS_CONFIG)
        if isinstance(axis_config, dict):
            self.axis_config.update(axis_config)

        self.color_buttons = {}; self.width_inputs = {}; self.dash_combos = {}

        # Laptop-safe layout: all long style/axis controls live in a scroll area
        # while Restore/OK/Cancel remain permanently reachable at the bottom.
        outer_layout = QVBoxLayout(self)
        self._style_scroll = QScrollArea(self)
        self._style_scroll.setWidgetResizable(True)
        self._style_scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(self._style_scroll)
        root_layout = QVBoxLayout(content)
        self.content_layout = root_layout
        self._style_scroll.setWidget(content)
        outer_layout.addWidget(self._style_scroll, stretch=1)

        intro = QLabel(
            "Personaliza trazas y los cuatro ejes de presentación. Los datos científicos no se modifican."
            if language == "es" else
            "Customize traces and the four display axes. Scientific data are not modified."
        )
        intro.setWordWrap(True); root_layout.addWidget(intro)

        traces_box = QGroupBox("Trazas" if language == "es" else "Traces")
        grid = QFormLayout(traces_box); grid.setHorizontalSpacing(18); grid.setVerticalSpacing(9)
        role_labels_es = {
            "spectrum":"Espectro", "baseline":"Línea base", "corrected":"Corregido",
            "fit_components":"Componentes de grupo", "fits":"Perfil final / ajuste único",
            "residual":"Residual final", "detections":"Detecciones",
        }
        role_labels_en = {
            "spectrum":"Spectrum", "baseline":"Baseline", "corrected":"Corrected",
            "fit_components":"Group components", "fits":"Final profile / isolated fit",
            "residual":"Final residual", "detections":"Detections",
        }
        labels = role_labels_es if language == "es" else role_labels_en
        for role in ("spectrum", "baseline", "corrected", "fit_components", "fits", "residual"):
            row = QWidget(); row_layout = QHBoxLayout(row); row_layout.setContentsMargins(0,0,0,0); row_layout.setSpacing(8)
            color_button = QPushButton(); color_button.setMinimumWidth(122)
            color_button.clicked.connect(lambda _checked=False, selected_role=role: self._choose_color(selected_role))
            self.color_buttons[role] = color_button
            width_input = QDoubleSpinBox(); width_input.setRange(0.5,8.0); width_input.setDecimals(1); width_input.setSingleStep(0.2); width_input.setSuffix(" px")
            width_input.setValue(float(self.styles[role]["width"])); self.width_inputs[role] = width_input
            dash_combo = QComboBox()
            for label, value in LINE_STYLE_OPTIONS: dash_combo.addItem(label, value)
            dash_combo.setCurrentIndex(max(0, dash_combo.findData(str(self.styles[role].get("dash","solid")))))
            self.dash_combos[role] = dash_combo
            row_layout.addWidget(color_button); row_layout.addWidget(width_input); row_layout.addWidget(dash_combo, stretch=1)
            grid.addRow(f"{labels[role]}:", row)

        detection_row = QWidget(); detection_layout = QHBoxLayout(detection_row); detection_layout.setContentsMargins(0,0,0,0); detection_layout.setSpacing(8)
        detection_color = QPushButton(); detection_color.setMinimumWidth(122); detection_color.clicked.connect(lambda _checked=False: self._choose_color("detections"))
        self.color_buttons["detections"] = detection_color
        detection_size = QDoubleSpinBox(); detection_size.setRange(3.0,18.0); detection_size.setDecimals(1); detection_size.setSingleStep(0.5); detection_size.setSuffix(" px")
        detection_size.setValue(float(self.styles["detections"]["size"])); self.width_inputs["detections"] = detection_size
        detection_layout.addWidget(detection_color); detection_layout.addWidget(QLabel("Tamaño:" if language=="es" else "Size:")); detection_layout.addWidget(detection_size)
        self.show_detection_labels = QCheckBox("Mostrar L1, L2, …" if language=="es" else "Show L1, L2, …")
        self.show_detection_labels.setChecked(bool(self.axis_config.get("show_detection_labels", True)))
        detection_layout.addWidget(self.show_detection_labels); detection_layout.addStretch()
        grid.addRow(f"{labels['detections']}:", detection_row)
        root_layout.addWidget(traces_box)

        axes_box = QGroupBox("Ejes" if language == "es" else "Axes")
        axes = QFormLayout(axes_box)
        axes.setHorizontalSpacing(12); axes.setVerticalSpacing(7)
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItem("Espectral horizontal · intensidad vertical" if language=="es" else "Spectral horizontal · intensity vertical", "horizontal")
        self.orientation_combo.addItem("Intensidad horizontal · espectral vertical" if language=="es" else "Intensity horizontal · spectral vertical", "vertical")
        self.orientation_combo.setCurrentIndex(max(0, self.orientation_combo.findData(self.axis_config.get("orientation","horizontal"))))

        def add_x_options(combo: QComboBox, include_none: bool = False):
            if include_none:
                combo.addItem("Ninguno" if language=="es" else "None", "none|none")
            group = "Frecuencia" if language=="es" else "Frequency"
            for unit in ("auto","Hz","kHz","MHz","GHz","THz"):
                shown = "Automática" if unit=="auto" and language=="es" else ("Automatic" if unit=="auto" else unit)
                combo.addItem(f"{group} · {shown}", f"frequency|{unit}")
            group = "Velocidad" if language=="es" else "Velocity"
            combo.addItem(f"{group} · km/s", "velocity|km/s")
            combo.addItem(f"{group} · m/s", "velocity|m/s")
            group = "Longitud de onda" if language=="es" else "Wavelength"
            for label, unit in (("m","m"),("cm","cm"),("mm","mm"),("µm","um"),("nm","nm"),("Å","angstrom")):
                combo.addItem(f"{group} · {label}", f"wavelength|{unit}")

        def selected_x_value(kind: str, *, secondary=False) -> str:
            if secondary and kind == "none": return "none|none"
            if kind == "frequency": return f"frequency|{self.axis_config.get('frequency_unit','auto')}"
            if kind == "velocity": return f"velocity|{self.axis_config.get('velocity_unit','km/s')}"
            if kind == "wavelength": return f"wavelength|{self.axis_config.get('wavelength_unit','mm')}"
            return "none|none" if secondary else "frequency|auto"

        self.primary_axis_combo = QComboBox(); add_x_options(self.primary_axis_combo, False)
        self.secondary_axis_combo = QComboBox(); add_x_options(self.secondary_axis_combo, True)
        pval = selected_x_value(str(self.axis_config.get("primary_spectral","frequency")))
        sval = selected_x_value(str(self.axis_config.get("secondary_spectral","velocity")), secondary=True)
        self.primary_axis_combo.setCurrentIndex(max(0,self.primary_axis_combo.findData(pval)))
        self.secondary_axis_combo.setCurrentIndex(max(0,self.secondary_axis_combo.findData(sval)))

        unit = self.native_intensity_unit
        native_label = (("Unidad de entrada" if language=="es" else "Input unit") + (f" ({unit})" if unit else ""))
        self.intensity_unit_combo = QComboBox(); self.intensity_unit_combo.addItem(native_label, "native")
        if unit in {"K", "mK", "µK"}:
            compatible = (("K","K"),("mK","mK"),("µK","µK"),("Jy/sr","Jy/sr"),("MJy/sr","MJy/sr"),("W m⁻² Hz⁻¹ sr⁻¹","W m⁻² Hz⁻¹ sr⁻¹"))
        elif unit in {"Jy", "mJy", "µJy", "W m⁻² Hz⁻¹"}:
            compatible = (("Jy","Jy"),("mJy","mJy"),("µJy","µJy"),("W m⁻² Hz⁻¹","W m⁻² Hz⁻¹"))
        elif unit in {"Jy/beam", "mJy/beam", "µJy/beam"}:
            compatible = (("Jy/beam","Jy/beam"),("mJy/beam","mJy/beam"),("µJy/beam","µJy/beam"))
        else:
            compatible = ()
        for label,value in compatible: self.intensity_unit_combo.addItem(label,value)
        idx=self.intensity_unit_combo.findData(self.axis_config.get("intensity_unit","native")); self.intensity_unit_combo.setCurrentIndex(idx if idx>=0 else 0)

        # Keep Y1/Y2 symmetric at the UI level.  Frequency-dependent
        # temperature<->radiance conversions are represented on Y2 at the
        # explicit centre frequency of the displayed panel (recorded in the
        # axis title), while prefix conversions remain exact constant factors.
        self.secondary_intensity_unit_combo = QComboBox(); self.secondary_intensity_unit_combo.addItem("Ninguno" if language=="es" else "None","none")
        self.secondary_intensity_unit_combo.addItem(native_label, "native")
        for label,value in compatible: self.secondary_intensity_unit_combo.addItem(label,value)
        idx=self.secondary_intensity_unit_combo.findData(self.axis_config.get("secondary_intensity_unit","none")); self.secondary_intensity_unit_combo.setCurrentIndex(idx if idx>=0 else 0)

        def title_preset_combo(axis: str):
            combo=QComboBox(); combo.addItem("Automático" if language=="es" else "Automatic","auto")
            if axis == "x":
                values = [
                    (("Frecuencia" if language=="es" else "Frequency"),"frequency"),("ν","nu"),
                    (("Velocidad" if language=="es" else "Velocity"),"velocity"),("v","v"),("Δv","dv"),
                    (("Longitud de onda" if language=="es" else "Wavelength"),"wavelength"),("λ","lambda"),
                ]
            else:
                values = [
                    (("Intensidad" if language=="es" else "Intensity"),"intensity"),
                    (("Temperatura de antena" if language=="es" else "Antenna temperature"),"antenna_temperature"),
                    ("T_A*","ta_star"),("T_MB","tmb"),("T_B","tb"),
                ]
            for label,value in values: combo.addItem(label,value)
            return combo

        def title_editor(preset_key: str, text_key: str, axis: str, placeholder: str):
            holder=QWidget(); lay=QHBoxLayout(holder); lay.setContentsMargins(0,0,0,0); lay.setSpacing(6)
            preset=title_preset_combo(axis); idx=preset.findData(str(self.axis_config.get(preset_key,"auto"))); preset.setCurrentIndex(idx if idx>=0 else 0)
            edit=QLineEdit(str(self.axis_config.get(text_key) or "")); edit.setPlaceholderText(placeholder)
            lay.addWidget(preset,0); lay.addWidget(edit,1)
            return holder,preset,edit

        pxt,self.primary_axis_title_preset_combo,self.primary_axis_title_input=title_editor("primary_axis_title_preset","primary_axis_title","x","Texto personalizado (opcional)" if language=="es" else "Custom text (optional)")
        sxt,self.secondary_axis_title_preset_combo,self.secondary_axis_title_input=title_editor("secondary_axis_title_preset","secondary_axis_title","x","Texto personalizado (opcional)" if language=="es" else "Custom text (optional)")
        pyt,self.intensity_axis_title_preset_combo,self.intensity_axis_title_input=title_editor("intensity_axis_title_preset","intensity_axis_title","y","Texto personalizado (opcional)" if language=="es" else "Custom text (optional)")
        syt,self.secondary_intensity_title_preset_combo,self.secondary_intensity_title_input=title_editor("secondary_intensity_title_preset","secondary_intensity_title","y","Texto personalizado (opcional)" if language=="es" else "Custom text (optional)")

        graph_title_holder = QWidget(); graph_title_layout = QHBoxLayout(graph_title_holder); graph_title_layout.setContentsMargins(0,0,0,0); graph_title_layout.setSpacing(6)
        self.graph_title_mode_combo = QComboBox()
        self.graph_title_mode_combo.addItem("Automático" if language=="es" else "Automatic", "auto")
        self.graph_title_mode_combo.addItem("Sin título" if language=="es" else "No title", "none")
        self.graph_title_mode_combo.addItem("Personalizado" if language=="es" else "Custom", "custom")
        gidx=self.graph_title_mode_combo.findData(str(self.axis_config.get("graph_title_mode") or "auto")); self.graph_title_mode_combo.setCurrentIndex(gidx if gidx>=0 else 0)
        self.graph_title_input = QLineEdit(str(self.axis_config.get("graph_title") or "")); self.graph_title_input.setPlaceholderText("Título personalizado (opcional)" if language=="es" else "Custom graph title (optional)")
        graph_title_layout.addWidget(self.graph_title_mode_combo,0); graph_title_layout.addWidget(self.graph_title_input,1)
        self.graph_title_input.textEdited.connect(lambda _text: self.graph_title_mode_combo.setCurrentIndex(max(0,self.graph_title_mode_combo.findData("custom"))))

        axes.addRow("Orientación:" if language=="es" else "Orientation:", self.orientation_combo)
        axes.addRow("Eje X principal:" if language=="es" else "Primary X axis:", self.primary_axis_combo)
        axes.addRow("Eje X secundario:" if language=="es" else "Secondary X axis:", self.secondary_axis_combo)
        axes.addRow("Eje Y principal:" if language=="es" else "Primary Y axis:", self.intensity_unit_combo)
        axes.addRow("Eje Y secundario:" if language=="es" else "Secondary Y axis:", self.secondary_intensity_unit_combo)
        axes.addRow("Título eje X principal:" if language=="es" else "Primary X title:", pxt)
        axes.addRow("Título eje X secundario:" if language=="es" else "Secondary X title:", sxt)
        axes.addRow("Título eje Y principal:" if language=="es" else "Primary Y title:", pyt)
        axes.addRow("Título eje Y secundario:" if language=="es" else "Secondary Y title:", syt)
        axes.addRow("Título general:" if language=="es" else "Graph title:", graph_title_holder)
        self.primary_axis_combo.currentIndexChanged.connect(self._axis_selection_changed)
        self.secondary_axis_combo.currentIndexChanged.connect(self._axis_selection_changed)
        self._axis_selection_changed()

        axes_note = QLabel(
            "Las unidades del eje X se eligen directamente en X principal/secundario. Å está disponible para longitud de onda. "
            "La velocidad de .30m usa la calibración nativa de CLASS; un ASCII genérico necesita una frecuencia de referencia M1 explícita. "
            "Y1 y Y2 muestran las mismas unidades disponibles. Las conversiones por prefijo son exactas; un eje secundario temperatura/radiancia usa la frecuencia central del panel y etiqueta explícitamente esa referencia. Un título personalizado sin unidad recibe automáticamente la unidad entre corchetes; si ya escribes [unidad], CZSpec no la duplica."
            if language=="es" else
            "X-axis units are selected directly in Primary/Secondary X. Å is available for wavelength. "
            ".30m velocity uses the native CLASS calibration; generic ASCII requires an explicit M1 reference frequency. "
            "Y1 and Y2 expose the same available unit choices. Prefix conversions are exact; a temperature/radiance secondary scale uses the displayed panel centre frequency and labels that reference explicitly. A custom title without a unit receives the unit automatically; if you already type [unit], CZSpec does not duplicate it."
        )
        axes_note.setWordWrap(True); axes_note.setStyleSheet("color:#64748B;font-size:11px;")
        axes.addRow(axes_note); root_layout.addWidget(axes_box)

        buttons_row = QHBoxLayout(); reset_button = QPushButton("Restaurar" if language=="es" else "Restore defaults")
        reset_button.clicked.connect(self._restore_defaults); buttons_row.addWidget(reset_button); buttons_row.addStretch()
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._accept_styles); button_box.rejected.connect(self.reject); buttons_row.addWidget(button_box); outer_layout.addLayout(buttons_row)
        self._refresh_all_color_buttons()

        # Never open taller/wider than the usable screen.  The controls scroll
        # instead of escaping below a laptop panel/taskbar.
        screen = self.screen() or QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.resize(min(780, max(600, geo.width() - 80)), min(700, max(500, geo.height() - 80)))

    @staticmethod
    def _split_x_choice(value: str) -> tuple[str,str]:
        text=str(value or "frequency|auto")
        if "|" not in text: return text,"auto"
        return tuple(text.split("|",1))

    def _refresh_color_button(self, role: str):
        color_value = str(self.styles[role]["color"]).upper(); color = QColor(color_value)
        luminance = 0.2126*color.redF()+0.7152*color.greenF()+0.0722*color.blueF(); text_color = "#111827" if luminance > 0.58 else "#FFFFFF"
        button = self.color_buttons[role]; button.setText(f"●  {color_value}")
        button.setStyleSheet("QPushButton {"+f"background-color: {color_value}; color: {text_color};"+"border: 1px solid #A8B4C6; font-weight: 700;}")

    def _refresh_all_color_buttons(self):
        for role in self.color_buttons: self._refresh_color_button(role)

    def _choose_color(self, role: str):
        selected = QColorDialog.getColor(QColor(self.styles[role]["color"]), self,
            ("Seleccionar color: " if self.language=="es" else "Select color: ") + role)
        if selected.isValid(): self.styles[role]["color"] = selected.name().upper(); self._refresh_color_button(role)

    def _axis_selection_changed(self, *_):
        primary_kind,_ = self._split_x_choice(self.primary_axis_combo.currentData())
        secondary_kind,_ = self._split_x_choice(self.secondary_axis_combo.currentData())
        if secondary_kind == primary_kind:
            idx=self.secondary_axis_combo.findData("none|none")
            if idx>=0:
                blocked=self.secondary_axis_combo.blockSignals(True); self.secondary_axis_combo.setCurrentIndex(idx); self.secondary_axis_combo.blockSignals(blocked)

    def _restore_defaults(self):
        self.styles=deepcopy(DEFAULT_PLOT_STYLES); self.axis_config=deepcopy(self.DEFAULT_AXIS_CONFIG)
        for role,input_widget in self.width_inputs.items():
            input_widget.setValue(float(self.styles[role]["size" if role=="detections" else "width"]))
        for role,combo in self.dash_combos.items(): combo.setCurrentIndex(max(0,combo.findData(self.styles[role]["dash"])))
        self.orientation_combo.setCurrentIndex(max(0,self.orientation_combo.findData("horizontal")))
        self.primary_axis_combo.setCurrentIndex(max(0,self.primary_axis_combo.findData("frequency|auto")))
        self.secondary_axis_combo.setCurrentIndex(max(0,self.secondary_axis_combo.findData("velocity|km/s")))
        self.intensity_unit_combo.setCurrentIndex(max(0,self.intensity_unit_combo.findData("native")))
        self.secondary_intensity_unit_combo.setCurrentIndex(max(0,self.secondary_intensity_unit_combo.findData("none")))
        for combo in (self.primary_axis_title_preset_combo,self.secondary_axis_title_preset_combo,self.intensity_axis_title_preset_combo,self.secondary_intensity_title_preset_combo):
            combo.setCurrentIndex(max(0,combo.findData("auto")))
        self.primary_axis_title_input.clear(); self.secondary_axis_title_input.clear(); self.intensity_axis_title_input.clear(); self.secondary_intensity_title_input.clear()
        self.graph_title_mode_combo.setCurrentIndex(max(0,self.graph_title_mode_combo.findData("auto"))); self.graph_title_input.clear()
        self.show_detection_labels.setChecked(True); self._refresh_all_color_buttons()

    def _accept_styles(self):
        for role,input_widget in self.width_inputs.items(): self.styles[role]["size" if role=="detections" else "width"] = float(input_widget.value())
        for role,combo in self.dash_combos.items(): self.styles[role]["dash"] = str(combo.currentData())
        primary_kind,primary_unit=self._split_x_choice(self.primary_axis_combo.currentData())
        secondary_kind,secondary_unit=self._split_x_choice(self.secondary_axis_combo.currentData())
        if secondary_kind==primary_kind: secondary_kind,secondary_unit="none","none"
        cfg=deepcopy(self.axis_config)
        cfg.update({
            "orientation":str(self.orientation_combo.currentData() or "horizontal"),
            "primary_spectral":primary_kind,
            "secondary_spectral":secondary_kind,
            "intensity_unit":str(self.intensity_unit_combo.currentData() or "native"),
            "secondary_intensity_unit":str(self.secondary_intensity_unit_combo.currentData() or "none"),
            "primary_axis_title":self.primary_axis_title_input.text().strip(),
            "secondary_axis_title":self.secondary_axis_title_input.text().strip(),
            "intensity_axis_title":self.intensity_axis_title_input.text().strip(),
            "secondary_intensity_title":self.secondary_intensity_title_input.text().strip(),
            "primary_axis_title_preset":str(self.primary_axis_title_preset_combo.currentData() or "auto"),
            "secondary_axis_title_preset":str(self.secondary_axis_title_preset_combo.currentData() or "auto"),
            "intensity_axis_title_preset":str(self.intensity_axis_title_preset_combo.currentData() or "auto"),
            "secondary_intensity_title_preset":str(self.secondary_intensity_title_preset_combo.currentData() or "auto"),
            "graph_title_mode":str(self.graph_title_mode_combo.currentData() or "auto"),
            "graph_title":self.graph_title_input.text().strip(),
            "show_detection_labels":bool(self.show_detection_labels.isChecked()),
        })
        for kind,unit in ((primary_kind,primary_unit),(secondary_kind,secondary_unit)):
            if kind=="frequency": cfg["frequency_unit"]=unit
            elif kind=="velocity": cfg["velocity_unit"]=unit
            elif kind=="wavelength": cfg["wavelength_unit"]=unit
        self.axis_config=cfg; self.accept()

    def axis_configuration(self) -> dict:
        return deepcopy(self.axis_config)

class ClassBackendConfigDialog(QDialog):
    """Configuración y diagnóstico del backend GILDAS/CLASS usado por M1."""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar GILDAS/CLASS")
        self.resize(720, 520)

        root = QVBoxLayout(self)
        intro = QLabel(
            "CLASS funciona como motor interno de CZSpec para archivos .30m. "
            "En Windows puede ejecutarse de forma transparente dentro de WSL; "
            "no se abre la interfaz de CLASS ni necesitas escribir comandos."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form_box = QGroupBox("Backend")
        form = QFormLayout(form_box)

        self.backend_combo = QComboBox()
        self.backend_combo.addItem("Automático (recomendado)", "auto")
        self.backend_combo.addItem("CLASS nativo", "native")
        self.backend_combo.addItem("CLASS vía WSL", "wsl")
        current = str(config.get("backend") or "auto")
        idx = self.backend_combo.findData(current)
        self.backend_combo.setCurrentIndex(max(0, idx))

        self.native_path_input = QLineEdit(str(config.get("native_class") or ""))
        self.native_path_input.setPlaceholderText("/ruta/a/class  (opcional)")
        self.native_path_input.setToolTip(
            "Ruta explícita a CLASS en el sistema anfitrión. En Linux normalmente "
            "puede dejarse vacía si 'class' está en PATH."
        )

        self.wsl_distro_combo = QComboBox()
        self.wsl_distro_combo.setEditable(True)
        configured_distro = str(config.get("wsl_distro") or "")
        for distro in list_wsl_distributions():
            self.wsl_distro_combo.addItem(distro)
        if configured_distro:
            idx = self.wsl_distro_combo.findText(configured_distro)
            if idx < 0:
                self.wsl_distro_combo.addItem(configured_distro)
                idx = self.wsl_distro_combo.count() - 1
            self.wsl_distro_combo.setCurrentIndex(idx)
        elif self.wsl_distro_combo.count() == 0:
            self.wsl_distro_combo.setEditText("")

        self.wsl_class_input = QLineEdit(str(config.get("wsl_class") or ""))
        self.wsl_class_input.setPlaceholderText("/home/usuario/.../bin/class  (opcional)")
        self.wsl_class_input.setToolTip(
            "Ruta Linux del ejecutable CLASS dentro de WSL. Déjala vacía para "
            "detección automática desde el perfil de la distribución."
        )

        form.addRow("Modo:", self.backend_combo)
        form.addRow("Ruta CLASS nativo:", self.native_path_input)
        form.addRow("Distribución WSL:", self.wsl_distro_combo)
        form.addRow("Ruta CLASS en WSL:", self.wsl_class_input)
        root.addWidget(form_box)

        self.diagnostic_text = QTextEdit()
        self.diagnostic_text.setReadOnly(True)
        self.diagnostic_text.setMinimumHeight(190)
        root.addWidget(self.diagnostic_text, stretch=1)

        bottom = QHBoxLayout()
        self.diagnose_button = QPushButton("Diagnosticar")
        self.diagnose_button.clicked.connect(self._diagnose)
        bottom.addWidget(self.diagnose_button)
        self.install_class_button = QPushButton("Instalar/Corregir CLASS")
        self.install_class_button.setEnabled(False)
        self.install_class_button.setToolTip(
            "Se habilita cuando el diagnóstico no encuentra CLASS. En Windows usa WSL y la distribución Linux seleccionada."
        )
        self.install_class_button.clicked.connect(self._install_or_repair)
        bottom.addWidget(self.install_class_button)
        bottom.addStretch()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        bottom.addWidget(buttons)
        root.addLayout(bottom)

        self.diagnostic_text.setPlainText(
            "Pulsa ‘Diagnosticar’ para comprobar WSL y GILDAS/CLASS.\n"
            "La comprobación se ejecutará en segundo plano sin abrir terminales."
        )

    def configuration(self) -> dict:
        return {
            "backend": str(self.backend_combo.currentData() or "auto"),
            "native_class": self.native_path_input.text().strip(),
            "wsl_distro": self.wsl_distro_combo.currentText().strip(),
            "wsl_class": self.wsl_class_input.text().strip(),
        }

    def _diagnose(self):
        config = self.configuration()
        self.diagnostic_text.setPlainText("Diagnosticando GILDAS/CLASS...")
        QApplication.processEvents()
        try:
            result = class_backend_diagnostics(
                preference=config["backend"],
                native_class_path=config["native_class"] or None,
                wsl_distribution=config["wsl_distro"] or None,
                wsl_class_path=config["wsl_class"] or None,
            )
        except Exception as exc:
            self.diagnostic_text.setPlainText(f"✗ Error durante el diagnóstico:\n{exc}")
            self.install_class_button.setEnabled(True)
            return

        lines = [f"Sistema: {result.get('platform', '?')}"]
        if result.get("is_windows"):
            wsl = result.get("wsl_executable")
            lines.append(f"WSL: {'✓ ' + str(wsl) if wsl else '✗ No detectado'}")
            distros = result.get("wsl_distributions") or []
            lines.append(
                "Distribuciones WSL: " + (", ".join(distros) if distros else "ninguna")
            )
        backend = result.get("backend")
        wsl_health = result.get("wsl_health") or {}
        transient_wsl = bool(wsl_health.get("transient"))
        if backend:
            lines.append("")
            lines.append("✓ Soporte .30m disponible")
            lines.append(f"Backend: {backend.get('display_name', '?')}")
            self.install_class_button.setEnabled(False)
        elif transient_wsl:
            lines.append("")
            lines.append("⚠ WSL no respondió temporalmente; esto NO significa que CLASS se haya desinstalado.")
            lines.append("Espera unos segundos y pulsa Diagnosticar otra vez. CZSpec evita iniciar una reinstalación ante este tipo de fallo.")
            detail = str(wsl_health.get("message") or "").strip()
            if detail:
                lines.append("Detalle WSL: " + detail.splitlines()[-1][:400])
            self.install_class_button.setEnabled(False)
        else:
            lines.append("")
            lines.append("✗ CLASS no está disponible con esta configuración")
            if result.get("is_windows"):
                lines.append(
                    "CZSpec necesita WSL + GILDAS/CLASS para procesar .30m en Windows. "
                    "CLASS seguirá ejecutándose en segundo plano."
                )
            else:
                lines.append(
                    "Instala/carga GILDAS o indica explícitamente la ruta al ejecutable CLASS."
                )
            self.install_class_button.setEnabled(True)
        self.diagnostic_text.setPlainText("\n".join(lines))

    def _install_or_repair(self):
        config = self.configuration()
        answer = QMessageBox.question(
            self,
            "Instalar/Corregir GILDAS/CLASS",
            "CZSpec intentará localizar una instalación existente y, si es necesario, instalar/compilar GILDAS/CLASS. "
            "En Windows se hará dentro de WSL y puede tardar varios minutos. ¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.install_class_button.setEnabled(False)
        self.diagnose_button.setEnabled(False)
        self.diagnostic_text.setPlainText("Preparando instalación/reparación de GILDAS/CLASS...")

        def work(progress):
            return install_or_repair_class_backend(
                wsl_distribution=config.get("wsl_distro") or None,
                progress=progress,
            )

        task = BackgroundTask(work)
        self._class_install_task = task
        task.signals.progress.connect(lambda value, message: self.diagnostic_text.setPlainText(
            f"{message}\n\nProgreso aproximado: {value}%"
        ))
        task.signals.succeeded.connect(self._class_install_succeeded)
        task.signals.failed.connect(self._class_install_failed)
        task.signals.finished.connect(lambda: self.diagnose_button.setEnabled(True))
        QThreadPool.globalInstance().start(task)

    def _class_install_succeeded(self, result):
        result = dict(result or {})
        backend = result.get("backend") or {}
        status = str(result.get("status") or "")
        if backend:
            kind = str(backend.get("kind") or "")
            if kind == "wsl":
                self.backend_combo.setCurrentIndex(max(0, self.backend_combo.findData("wsl")))
                distro = str(backend.get("wsl_distribution") or "")
                if distro:
                    self.wsl_distro_combo.setEditText(distro)
                self.wsl_class_input.setText(str(backend.get("executable") or ""))
            elif kind == "native":
                self.backend_combo.setCurrentIndex(max(0, self.backend_combo.findData("native")))
                self.native_path_input.setText(str(backend.get("executable") or ""))
            self.diagnostic_text.setPlainText("✓ CLASS está disponible. Pulsa Guardar para conservar esta configuración.")
            self.install_class_button.setEnabled(False)
            return
        message = str(result.get("message") or "No fue posible completar la instalación automática.")
        url = str(result.get("url") or "")
        if url:
            message += f"\n\nGuía oficial: {url}"
        self.diagnostic_text.setPlainText(message)
        self.install_class_button.setEnabled(status not in {"wsl_transient", "wsl_unavailable"})

    def _class_install_failed(self, payload):
        message, details = payload if isinstance(payload, tuple) and len(payload) == 2 else (str(payload), "")
        # Do not dump a Python traceback into the public UI. Keep the actionable
        # error and let a new diagnosis determine whether repair is appropriate.
        detail_line = ""
        if details:
            clean = [line.strip() for line in str(details).splitlines() if line.strip()]
            if clean:
                detail_line = "\n\nDetalle técnico: " + clean[-1][:600]
        self.diagnostic_text.setPlainText(f"✗ No se pudo instalar/corregir CLASS:\n{message}{detail_line}\n\nPulsa Diagnosticar antes de volver a intentar una reparación.")
        self.install_class_button.setEnabled(False)


class Class30mImportDialog(QDialog):
    """Selecciona observaciones CLASS con filtros por metadatos observacionales."""

    def __init__(self, file_path: str, setups: list, backend_path: str, language: str = "es", parent=None):
        super().__init__(parent)
        self.language = language
        self.file_path = str(file_path)
        self.setups = list(setups)
        self.rows = []
        for setup in self.setups:
            for obs in setup.observations:
                self.rows.append((setup, obs))
        self.setWindowTitle("Importar archivo CLASS .30m" if language == "es" else "Import CLASS .30m file")
        self.resize(1180, 760)

        root = QVBoxLayout(self)
        intro = QLabel(
            "CZSpec usará GILDAS/CLASS para leer el contenedor .30m. Filtra y selecciona exactamente "
            "qué observaciones quieres importar o promediar. Los filtros no modifican el archivo original."
            if language == "es" else
            "CZSpec uses GILDAS/CLASS to read the .30m container. Filter and select exactly which "
            "observations to import or average. Filters never modify the original file."
        )
        intro.setWordWrap(True); root.addWidget(intro)
        file_label = QLabel(("Archivo: " if language == "es" else "File: ") + Path(self.file_path).name)
        file_label.setToolTip(self.file_path); root.addWidget(file_label)
        backend_label = QLabel(("Motor CLASS: " if language == "es" else "CLASS engine: ") + backend_path)
        backend_label.setToolTip(backend_path); root.addWidget(backend_label)

        filters_box = QGroupBox("Filtros de selección" if language == "es" else "Selection filters")
        filters = QGridLayout(filters_box)
        self.filter_source = QComboBox(); self.filter_line = QComboBox()
        self.filter_group = QComboBox(); self.filter_backend = QComboBox()
        self.filter_text = QLineEdit(); self.filter_text.setPlaceholderText(
            "Buscar fuente, línea, backend u observación" if language == "es" else
            "Search source, line, backend or observation"
        )
        all_text = "Todos" if language == "es" else "All"
        for combo in (self.filter_source, self.filter_line, self.filter_group, self.filter_backend):
            combo.addItem(all_text, None)
        def add_unique(combo, values):
            for value in sorted({str(v) for v in values if str(v).strip()}, key=str.lower):
                combo.addItem(value, value)
        add_unique(self.filter_source, [setup.source for setup, _ in self.rows])
        add_unique(self.filter_line, [setup.line for setup, _ in self.rows])
        add_unique(self.filter_group, [setup.average_label for setup, _ in self.rows])
        add_unique(self.filter_backend, [obs.telescope for _, obs in self.rows])
        filters.addWidget(QLabel("Fuente:" if language == "es" else "Source:"), 0, 0)
        filters.addWidget(self.filter_source, 0, 1)
        filters.addWidget(QLabel("Línea:" if language == "es" else "Line:"), 0, 2)
        filters.addWidget(self.filter_line, 0, 3)
        filters.addWidget(QLabel("Grupo promedio:" if language == "es" else "Average group:"), 1, 0)
        filters.addWidget(self.filter_group, 1, 1)
        filters.addWidget(QLabel("Backend:"), 1, 2); filters.addWidget(self.filter_backend, 1, 3)
        filters.addWidget(self.filter_text, 2, 0, 1, 4)
        root.addWidget(filters_box)

        self.table = QTableWidget(len(self.rows), 7)
        self.table.setHorizontalHeaderLabels([
            "☑ Usar" if language == "es" else "☑ Use",
            "Fuente" if language == "es" else "Source",
            "Línea" if language == "es" else "Line",
            "Grupo de promedio" if language == "es" else "Average group",
            "Telescopio/backend" if language == "es" else "Telescope/backend",
            "Obs.", "Versión" if language == "es" else "Version",
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        header = self.table.horizontalHeader()
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._header_section_clicked)
        self.table.horizontalHeaderItem(0).setToolTip(
            "Seleccionar exactamente las observaciones visibles tras aplicar los filtros" if language == "es" else
            "Select exactly the observations visible after applying the filters"
        )
        for col in (0, 1, 2, 3, 5, 6): header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        for row, (setup, obs) in enumerate(self.rows):
            check = QTableWidgetItem(); check.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            check.setCheckState(Qt.CheckState.Unchecked); self.table.setItem(row, 0, check)
            values = (setup.source, setup.line, setup.average_label, obs.telescope, obs.number, obs.version)
            for col, value in enumerate(values, start=1):
                item = QTableWidgetItem(str(value)); item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(row, col, item)
        root.addWidget(self.table, stretch=1)

        self.products_label = QLabel(""); self.products_label.setWordWrap(True); root.addWidget(self.products_label)
        preprocessing = QGroupBox("Conversión CLASS → CZSpec" if language == "es" else "CLASS → CZSpec conversion")
        form = QGridLayout(preprocessing)
        self.average_checkbox = QCheckBox(
            "Promediar observaciones seleccionadas cuando haya más de una compatible"
            if language == "es" else "Average selected observations when more than one is compatible"
        )
        self.average_checkbox.setChecked(True)
        self.average_checkbox.setToolTip(
            "Para EMIR, CZSpec agrupa H/V del mismo subrango y familia de backend. "
            "Cada grupo compatible pasa por CONSISTENCY → AVERAGE; subrangos distintos nunca se mezclan."
            if language == "es" else
            "For EMIR, CZSpec groups H/V from the same sub-band and backend family. "
            "Each compatible group uses CONSISTENCY → AVERAGE; distinct sub-bands are never mixed."
        )
        form.addWidget(self.average_checkbox, 0, 0, 1, 4)
        note = QLabel(
            "CLASS sólo abre el .30m, comprueba CONSISTENCY, promedia cuando corresponde y exporta .dat. "
            "Suavizado, línea base, detección y ajustes pertenecen a CZSpec."
            if language == "es" else
            "CLASS only opens the .30m file, checks CONSISTENCY, averages when appropriate and exports .dat. "
            "Smoothing, baseline, detection and fitting belong to CZSpec."
        )
        note.setWordWrap(True); form.addWidget(note, 1, 0, 1, 4); root.addWidget(preprocessing)

        for widget in (self.filter_source, self.filter_line, self.filter_group, self.filter_backend):
            widget.currentIndexChanged.connect(self._apply_filters)
        self.filter_text.textChanged.connect(self._apply_filters)
        self.table.itemChanged.connect(self._refresh_product_count)
        self.average_checkbox.toggled.connect(self._refresh_product_count)
        self._apply_filters(); self._refresh_product_count()

        footer = QHBoxLayout()
        select_all = QPushButton("Seleccionar todos" if language == "es" else "Select all")
        select_none = QPushButton("Quitar todos" if language == "es" else "Clear all")
        select_all.clicked.connect(lambda: self._set_all(True, visible_only=False))
        select_none.clicked.connect(lambda: self._set_all(False, visible_only=False))
        footer.addWidget(select_all); footer.addWidget(select_none); footer.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._validate_and_accept); buttons.rejected.connect(self.reject)
        footer.addWidget(buttons); root.addLayout(footer)

    def _header_section_clicked(self, section: int):
        """The Use header acts as a filter-aware master selector.

        A click selects *exactly* the rows currently visible after filtering.
        Clicking again when the visible rows are already the exclusive
        selection clears them. This keeps filtering and selection predictable.
        """
        if int(section) != 0:
            return
        visible_rows = [r for r in range(self.table.rowCount()) if not self.table.isRowHidden(r)]
        if not visible_rows:
            return
        visible_checked = all(
            self.table.item(r, 0) is not None and self.table.item(r, 0).checkState() == Qt.CheckState.Checked
            for r in visible_rows
        )
        hidden_checked = any(
            self.table.isRowHidden(r) and self.table.item(r, 0) is not None
            and self.table.item(r, 0).checkState() == Qt.CheckState.Checked
            for r in range(self.table.rowCount())
        )
        # If this filtered set is already the exclusive selection, toggle it off.
        if visible_checked and not hidden_checked:
            self._set_all(False, visible_only=True)
        else:
            self._set_all(False, visible_only=False)
            self._set_all(True, visible_only=True)
        self._refresh_use_header()

    def _refresh_use_header(self):
        item = self.table.horizontalHeaderItem(0)
        if item is None:
            return
        visible = [r for r in range(self.table.rowCount()) if not self.table.isRowHidden(r)]
        checked = sum(
            1 for r in visible
            if self.table.item(r, 0) is not None and self.table.item(r, 0).checkState() == Qt.CheckState.Checked
        )
        base = "Usar" if self.language == "es" else "Use"
        if visible and checked == len(visible): symbol = "☑"
        elif checked: symbol = "◩"
        else: symbol = "☐"
        item.setText(f"{symbol} {base}")

    def _apply_filters(self, *_args):
        source = self.filter_source.currentData(); line = self.filter_line.currentData()
        group = self.filter_group.currentData(); backend = self.filter_backend.currentData()
        text = self.filter_text.text().strip().lower()
        for row, (setup, obs) in enumerate(self.rows):
            fields = [str(setup.source), str(setup.line), str(setup.average_label), str(obs.telescope), str(obs.number), str(obs.version)]
            visible = (
                (source is None or str(setup.source) == str(source))
                and (line is None or str(setup.line) == str(line))
                and (group is None or str(setup.average_label) == str(group))
                and (backend is None or str(obs.telescope) == str(backend))
                and (not text or any(text in value.lower() for value in fields))
            )
            self.table.setRowHidden(row, not visible)
        self._refresh_product_count()
        self._refresh_use_header()

    def _set_all(self, checked: bool, *, visible_only: bool = False):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self.table.blockSignals(True)
        try:
            for row in range(self.table.rowCount()):
                if visible_only and self.table.isRowHidden(row): continue
                item = self.table.item(row, 0)
                if item is not None: item.setCheckState(state)
        finally:
            self.table.blockSignals(False)
        self._refresh_product_count()
        self._refresh_use_header()

    def _refresh_product_count(self, *_args):
        try: selected = self.selected_setups()
        except Exception: selected = []
        n_obs = sum(setup.count for setup in selected)
        visible = sum(0 if self.table.isRowHidden(r) else 1 for r in range(self.table.rowCount()))
        if self.average_checkbox.isChecked():
            n_products = len(selected); detail = "un .dat por grupo compatible" if self.language == "es" else "one .dat per compatible group"
        else:
            n_products = n_obs; detail = "un .dat por observación" if self.language == "es" else "one .dat per observation"
        self.products_label.setText(
            (f"Visibles: {visible}/{len(self.rows)} · selección: {n_obs} observación(es) en {len(selected)} grupo(s) · productos previstos: {n_products} ({detail})."
             if self.language == "es" else
             f"Visible: {visible}/{len(self.rows)} · selected: {n_obs} observation(s) in {len(selected)} group(s) · expected products: {n_products} ({detail}).")
        )

    def selected_setups(self) -> list:
        selected_by_setup = {}
        for row, (setup, obs) in enumerate(self.rows):
            item = self.table.item(row, 0)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                selected_by_setup.setdefault(id(setup), [setup, []])[1].append(obs)
        selected = []
        for setup, observations in selected_by_setup.values():
            if not observations: continue
            telescopes = tuple(sorted({obs.telescope for obs in observations}))
            selected.append(type(setup)(setup.source, setup.line, telescopes, tuple(observations), setup.average_label))
        return selected

    def configuration(self) -> dict:
        return {"average": bool(self.average_checkbox.isChecked())}

    def _validate_and_accept(self):
        setups = self.selected_setups()
        if not setups:
            QMessageBox.information(self, "Sin observaciones" if self.language == "es" else "No observations",
                                    "Selecciona al menos una observación CLASS." if self.language == "es" else "Select at least one CLASS observation.")
            return
        self.accept()


class InitialSpectrumViewDialog(QDialog):
    """Elige qué espectros se muestran justo después de una carga masiva."""

    def __init__(self, entries: list[dict], language: str = "es", parent=None):
        super().__init__(parent)
        self.entries = list(entries)
        self.language = "en" if language == "en" else "es"
        language = self.language
        self.setWindowTitle("Initial session view" if language == "en" else "Visualización inicial de la sesión")
        self.resize(720, 520)

        root = QVBoxLayout(self)
        intro = QLabel(
            (f"Loaded {len(self.entries)} spectra. All remain in the session; select only "
             "which ones to display now. One spectrum opens an individual view and several open a comparison.")
            if language == "en" else
            (f"Se cargaron {len(self.entries)} espectros. Todos permanecerán en la "
             "sesión; selecciona únicamente cuáles quieres mostrar ahora. Un solo "
             "espectro abre vista individual y varios abren una comparación.")
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        filters = QGridLayout()
        self.initial_source_filter = QComboBox()
        self.initial_line_filter = QComboBox()
        self.initial_source_filter.addItem("All sources" if language == "en" else "Todas las fuentes", "")
        self.initial_line_filter.addItem("All lines" if language == "en" else "Todas las líneas", "")
        sources, lines = set(), set()
        for entry in self.entries:
            name = str(entry.get("name") or Path(entry.get("path", "")).name)
            parts = [x.strip() for x in name.split("·") if x.strip()]
            if entry.get("source"): sources.add(str(entry.get("source")))
            elif parts: sources.add(parts[0])
            if entry.get("line"): lines.add(str(entry.get("line")))
            elif len(parts) > 1: lines.add(parts[1])
        for value in sorted(sources): self.initial_source_filter.addItem(value, value)
        for value in sorted(lines): self.initial_line_filter.addItem(value, value)
        self.initial_search = QLineEdit()
        self.initial_search.setPlaceholderText("Search spectrum, source or line" if language == "en" else "Buscar espectro, fuente o línea")
        filters.addWidget(QLabel("Source:" if language == "en" else "Fuente:"), 0, 0)
        filters.addWidget(self.initial_source_filter, 0, 1)
        filters.addWidget(QLabel("Line:" if language == "en" else "Línea:"), 0, 2)
        filters.addWidget(self.initial_line_filter, 0, 3)
        filters.addWidget(self.initial_search, 1, 0, 1, 4)
        root.addLayout(filters)

        # Initial preview configuration.  This is deliberately separate from
        # the full Compare dialog: it only decides what the user wants to see
        # immediately after loading a multi-spectrum session.
        preview_box = QGroupBox("Initial preview" if language == "en" else "Previsualización inicial")
        preview_grid = QGridLayout(preview_box)
        self.initial_layout_combo = QComboBox()
        self.initial_layout_combo.addItem("Automatic" if language == "en" else "Automática", "auto")
        self.initial_layout_combo.addItem("Grid" if language == "en" else "Cuadrícula", "grid")
        self.initial_layout_combo.addItem("Aligned bands" if language == "en" else "Bandas alineadas", "aligned")
        self.initial_layout_combo.addItem("Continuous bands" if language == "en" else "Bandas continuas", "continuous")
        self.initial_layout_combo.addItem("Continuous bands with break" if language == "en" else "Bandas continuas con brecha", "stitched")
        self.initial_share_x_checkbox = FilterCheckBox("Share X scale" if language == "en" else "Compartir escala X")
        self.initial_share_y_checkbox = FilterCheckBox("Share Y scale" if language == "en" else "Compartir escala Y")
        self.initial_share_x_checkbox.setChecked(False)
        self.initial_share_y_checkbox.setChecked(False)
        preview_grid.addWidget(QLabel("Layout:" if language == "en" else "Disposición:"), 0, 0)
        preview_grid.addWidget(self.initial_layout_combo, 0, 1)
        preview_grid.addWidget(self.initial_share_x_checkbox, 1, 0)
        preview_grid.addWidget(self.initial_share_y_checkbox, 1, 1)
        root.addWidget(preview_box)

        self.table = QTableWidget(len(self.entries), 3)
        self.table.setHorizontalHeaderLabels(["Show" if language == "en" else "Mostrar", "Spectrum" if language == "en" else "Espectro", "Range [MHz]" if language == "en" else "Rango [MHz]"])
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        for row, entry in enumerate(self.entries):
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            check.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, check)
            name = QTableWidgetItem(str(entry.get("name") or Path(entry["path"]).name))
            name.setToolTip(str(entry["path"]))
            name.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 1, name)
            freq_value = entry.get("freq")
            freq = np.asarray([] if freq_value is None else freq_value, dtype=float)
            finite = freq[np.isfinite(freq)]
            range_text = "—"
            if finite.size:
                range_text = f"{finite.min():.1f}–{finite.max():.1f}"
            item = QTableWidgetItem(range_text)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 2, item)
        root.addWidget(self.table, stretch=1)
        self.initial_source_filter.currentIndexChanged.connect(self._apply_initial_filters)
        self.initial_line_filter.currentIndexChanged.connect(self._apply_initial_filters)
        self.initial_search.textChanged.connect(self._apply_initial_filters)

        note = QLabel(
            ("Tip: for a readable comparison it is usually best to display 2–6 spectra at once. "
             "You can change the selection later with Compare.")
            if language == "en" else
            ("Consejo: para una comparación legible suele ser mejor mostrar 2–6 "
             "espectros a la vez. Puedes cambiar la selección después con ‘Comparar’.")
        )
        note.setWordWrap(True)
        root.addWidget(note)

        footer = QHBoxLayout()
        all_button = QPushButton("Show all" if language == "en" else "Mostrar todos")
        none_button = QPushButton("Quitar todos" if language == "es" else "Clear all")
        all_button.clicked.connect(lambda: self._set_all(True))
        none_button.clicked.connect(lambda: self._set_all(False))
        footer.addWidget(all_button)
        footer.addWidget(none_button)
        footer.addStretch()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Show selection" if language == "en" else "Mostrar selección")
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        footer.addWidget(buttons)
        root.addLayout(footer)


    def _apply_initial_filters(self):
        source = str(self.initial_source_filter.currentData() or "").lower()
        line = str(self.initial_line_filter.currentData() or "").lower()
        query = self.initial_search.text().strip().lower()
        for row, entry in enumerate(self.entries):
            name = str(entry.get("name") or Path(entry.get("path", "")).name)
            parts = [x.strip() for x in name.split("·") if x.strip()]
            src = str(entry.get("source") or (parts[0] if parts else ""))
            lin = str(entry.get("line") or (parts[1] if len(parts) > 1 else ""))
            hay = " | ".join((name, src, lin, str(entry.get("path", "")))).lower()
            visible = (not source or src.lower() == source) and (not line or lin.lower() == line) and (not query or query in hay)
            self.table.setRowHidden(row, not visible)

    def _set_all(self, checked: bool):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(state)

    def selected_paths(self) -> list[str]:
        selected = []
        for row, entry in enumerate(self.entries):
            if self.table.item(row, 0).checkState() == Qt.CheckState.Checked:
                selected.append(str(entry["path"]))
        return selected

    def comparison_config(self) -> dict:
        return {
            "layout": str(self.initial_layout_combo.currentData() or "auto"),
            "share_x": bool(self.initial_share_x_checkbox.isChecked()),
            "share_y": bool(self.initial_share_y_checkbox.isChecked()),
        }

    def _validate_and_accept(self):
        if not self.selected_paths():
            QMessageBox.information(
                self, "Initial view" if self.language == "en" else "Visualización inicial",
                "Select at least one spectrum." if self.language == "en" else "Selecciona al menos un espectro."
            )
            return
        self.accept()


class ApplicationSettingsDialog(QDialog):
    """Preferencias generales de CZSpec visibles desde la barra superior."""

    classBackendRequested = Signal()

    TABLE_FORMATS = (
        ("csv", "CSV"), ("tsv", "TSV"), ("dsv", "DSV (;)") ,
        ("txt", "TXT"), ("xlsx", "XLSX"), ("xml", "XML"),
        ("ods", "ODS"), ("json", "JSON"), ("html", "HTML"),
        ("latex", "LaTeX"),
    )
    PLOT_FORMATS = (("html", "HTML interactivo"), ("png", "PNG"), ("jpg", "JPG"), ("pdf", "PDF"))

    def __init__(
        self,
        input_dir: str,
        workspace_dir: str,
        language: str = "es",
        text_scale_percent: int = 100,
        font_family: str = "Inter",
        table_decimal_places: int = 3,
        table_formats: list[str] | None = None,
        plot_formats: list[str] | None = None,
        m2_table_formats: list[str] | None = None,
        m2_plot_formats: list[str] | None = None,
        m3_table_formats: list[str] | None = None,
        m3_plot_formats: list[str] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Configuración de CZSpec" if language == "es" else "CZSpec settings")
        self.resize(720, 650)
        self.setMinimumSize(560, 440)
        self.language = language
        table_formats = list(table_formats or ["csv", "html", "latex"])
        plot_formats = list(plot_formats or ["html", "png", "jpg", "pdf"])
        m2_table_formats = list(m2_table_formats or ["csv", "html", "latex"])
        m2_plot_formats = list(m2_plot_formats or ["html", "png", "jpg", "pdf"])
        m3_table_formats = list(m3_table_formats or ["csv", "html", "latex"])
        m3_plot_formats = list(m3_plot_formats or ["html", "png", "jpg", "pdf"])

        outer = QVBoxLayout(self)
        self._settings_scroll = QScrollArea(self)
        self._settings_scroll.setWidgetResizable(True)
        self._settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(self._settings_scroll)
        root = QVBoxLayout(content)
        self._settings_scroll.setWidget(content)
        outer.addWidget(self._settings_scroll, stretch=1)
        intro = QLabel(
            "Personaliza rutas, apariencia, exportaciones e integraciones externas. "
            "Los cambios de espacio de trabajo y apariencia se aplican al reiniciar CZSpec."
            if language == "es" else
            "Customize paths, appearance, exports and external integrations. "
            "Workspace and appearance changes are applied after restarting CZSpec."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        paths_box = QGroupBox("Rutas" if language == "es" else "Paths")
        paths_layout = QFormLayout(paths_box)
        self.input_dir_input = QLineEdit(str(input_dir or ""))
        input_row = QWidget(); input_row_layout = QHBoxLayout(input_row)
        input_row_layout.setContentsMargins(0, 0, 0, 0)
        input_row_layout.addWidget(self.input_dir_input, stretch=1)
        input_browse = QPushButton("Examinar..." if language == "es" else "Browse...")
        input_browse.clicked.connect(self._browse_input); input_row_layout.addWidget(input_browse)

        self.workspace_dir_input = QLineEdit(str(workspace_dir or ""))
        workspace_row = QWidget(); workspace_row_layout = QHBoxLayout(workspace_row)
        workspace_row_layout.setContentsMargins(0, 0, 0, 0)
        workspace_row_layout.addWidget(self.workspace_dir_input, stretch=1)
        workspace_browse = QPushButton("Examinar..." if language == "es" else "Browse...")
        workspace_browse.clicked.connect(self._browse_workspace); workspace_row_layout.addWidget(workspace_browse)
        paths_layout.addRow("Carpeta inicial de entrada:" if language == "es" else "Default input folder:", input_row)
        paths_layout.addRow("Espacio de trabajo / salida:" if language == "es" else "Workspace / output folder:", workspace_row)
        root.addWidget(paths_box)

        appearance_box = QGroupBox("Apariencia" if language == "es" else "Appearance")
        appearance_layout = QFormLayout(appearance_box)
        self.text_scale_input = QSpinBox(); self.text_scale_input.setRange(80, 150)
        self.text_scale_input.setSingleStep(5); self.text_scale_input.setSuffix(" %")
        self.text_scale_input.setValue(max(80, min(150, int(text_scale_percent or 100))))
        self.text_scale_input.setToolTip(
            "Escala global del texto. Se aplica al guardar sin perder la sesión actual."
            if language == "es" else
            "Global text scale. It is applied when settings are saved without losing the current session."
        )
        appearance_layout.addRow("Tamaño del texto:" if language == "es" else "Text size:", self.text_scale_input)
        self.font_family_input = QFontComboBox()
        # QFontComboBox always exposes fonts actually available on the machine.
        try:
            from PySide6.QtGui import QFont
            self.font_family_input.setCurrentFont(QFont(str(font_family or "Inter")))
        except Exception:
            pass
        self.font_family_input.setToolTip(
            "Familia tipográfica usada por la interfaz de CZSpec." if language == "es" else
            "Font family used by the CZSpec interface."
        )
        appearance_layout.addRow("Tipografía:" if language == "es" else "Font family:", self.font_family_input)
        self.table_decimal_places_input = QSpinBox()
        self.table_decimal_places_input.setRange(0, 10)
        self.table_decimal_places_input.setValue(max(0, min(10, int(table_decimal_places))))
        self.table_decimal_places_input.setToolTip(
            "Número de decimales usado por las exportaciones de tablas de M1 y M2."
            if language == "es" else
            "Number of decimal places used by M1 and M2 table exports."
        )
        appearance_layout.addRow("Decimales en tablas:" if language == "es" else "Table decimals:", self.table_decimal_places_input)
        root.addWidget(appearance_box)

        exports_box = QGroupBox("Exportaciones de M1" if language == "es" else "M1 exports")
        exports_layout = QVBoxLayout(exports_box)
        table_label = QLabel(
            "Formatos que genera Exportar tablas:" if language == "es" else
            "Formats generated by Export tables:"
        )
        exports_layout.addWidget(table_label)
        table_grid = QGridLayout()
        self.table_format_checks = {}
        for i, (key, label) in enumerate(self.TABLE_FORMATS):
            cb = QCheckBox(label); cb.setChecked(key in table_formats)
            self.table_format_checks[key] = cb
            table_grid.addWidget(cb, i // 5, i % 5)
        exports_layout.addLayout(table_grid)
        plot_label = QLabel(
            "Formatos que genera Exportar gráficas:" if language == "es" else
            "Formats generated by Export plots:"
        )
        exports_layout.addWidget(plot_label)
        plot_grid = QGridLayout(); self.plot_format_checks = {}
        for i, (key, label) in enumerate(self.PLOT_FORMATS):
            cb = QCheckBox(label if language == "es" else label.replace("interactivo", "interactive"))
            cb.setChecked(key in plot_formats); self.plot_format_checks[key] = cb
            plot_grid.addWidget(cb, 0, i)
        exports_layout.addLayout(plot_grid)
        export_note = QLabel(
            "CSV/TSV/DSV/TXT/JSON/XML no requieren software externo. XLSX y ODS se generan cuando "
            "el motor correspondiente está disponible. HTML y LaTeX incluyen documentación de columnas."
            if language == "es" else
            "CSV/TSV/DSV/TXT/JSON/XML do not require external software. XLSX and ODS are generated when "
            "their writer engines are available. HTML and LaTeX include column documentation."
        )
        export_note.setWordWrap(True); export_note.setStyleSheet("color:#64748B;font-size:11px;")
        exports_layout.addWidget(export_note)
        root.addWidget(exports_box)

        m2_exports_box = QGroupBox("Exportaciones de M2" if language == "es" else "M2 exports")
        m2_exports_layout = QVBoxLayout(m2_exports_box)
        m2_table_label = QLabel(
            "Formatos para Exportar tablas de Identificación molecular:" if language == "es" else
            "Formats for Molecular identification table export:"
        )
        m2_exports_layout.addWidget(m2_table_label)
        m2_table_grid = QGridLayout()
        self.m2_table_format_checks = {}
        for i, (key, label) in enumerate(self.TABLE_FORMATS):
            cb = QCheckBox(label); cb.setChecked(key in m2_table_formats)
            self.m2_table_format_checks[key] = cb
            m2_table_grid.addWidget(cb, i // 5, i % 5)
        m2_exports_layout.addLayout(m2_table_grid)
        m2_plot_label = QLabel(
            "Formatos para Q(T) y espectros finales:" if language == "es" else
            "Formats for Q(T) and final spectra:"
        )
        m2_exports_layout.addWidget(m2_plot_label)
        m2_plot_grid = QGridLayout(); self.m2_plot_format_checks = {}
        for i, (key, label) in enumerate(self.PLOT_FORMATS):
            cb = QCheckBox(label if language == "es" else label.replace("interactivo", "interactive"))
            cb.setChecked(key in m2_plot_formats); self.m2_plot_format_checks[key] = cb
            m2_plot_grid.addWidget(cb, 0, i)
        m2_exports_layout.addLayout(m2_plot_grid)
        m2_note = QLabel(
            "M2 usa estos formatos para las tablas visibles/filtradas y para los productos Q(T) y espectros por fuente."
            if language == "es" else
            "M2 uses these formats for the current visible/filtered tables and for Q(T) and per-source spectra."
        )
        m2_note.setWordWrap(True); m2_note.setStyleSheet("color:#64748B;font-size:11px;")
        m2_exports_layout.addWidget(m2_note)
        root.addWidget(m2_exports_box)

        m3_exports_box = QGroupBox("Exportaciones de M3" if language == "es" else "M3 exports")
        m3_exports_layout = QVBoxLayout(m3_exports_box)
        m3_table_label = QLabel(
            "Formatos para exportar resultados MOD/MTH:" if language == "es" else
            "Formats for OTM/HTM result tables:"
        )
        m3_exports_layout.addWidget(m3_table_label)
        m3_table_grid = QGridLayout(); self.m3_table_format_checks = {}
        for i, (key, label) in enumerate(self.TABLE_FORMATS):
            cb = QCheckBox(label); cb.setChecked(key in m3_table_formats)
            self.m3_table_format_checks[key] = cb
            m3_table_grid.addWidget(cb, i // 5, i % 5)
        m3_exports_layout.addLayout(m3_table_grid)
        m3_plot_label = QLabel(
            "Formatos para espectros finales de M3:" if language == "es" else
            "Formats for M3 final spectra:"
        )
        m3_exports_layout.addWidget(m3_plot_label)
        m3_plot_grid = QGridLayout(); self.m3_plot_format_checks = {}
        for i, (key, label) in enumerate(self.PLOT_FORMATS):
            cb = QCheckBox(label if language == "es" else label.replace("interactivo", "interactive"))
            cb.setChecked(key in m3_plot_formats); self.m3_plot_format_checks[key] = cb
            m3_plot_grid.addWidget(cb, 0, i)
        m3_exports_layout.addLayout(m3_plot_grid)
        m3_note = QLabel(
            "M3 mantiene sus tablas, espectros generados y figuras guardadas en carpetas propias del módulo."
            if language == "es" else
            "M3 keeps exported tables, generated spectra and saved figures in module-specific folders."
        )
        m3_note.setWordWrap(True); m3_note.setStyleSheet("color:#64748B;font-size:11px;")
        m3_exports_layout.addWidget(m3_note)
        root.addWidget(m3_exports_box)

        integrations_box = QGroupBox("Integraciones" if language == "es" else "Integrations")
        integrations_layout = QVBoxLayout(integrations_box)
        class_button = QPushButton("Configurar GILDAS/CLASS..." if language == "es" else "Configure GILDAS/CLASS...")
        class_button.setToolTip(
            "Configura CLASS únicamente para importar archivos .30m."
            if language == "es" else "Configure CLASS only for importing .30m files."
        )
        class_button.clicked.connect(self.classBackendRequested.emit)
        integrations_layout.addWidget(class_button); root.addWidget(integrations_box)

        note = QLabel(
            "Nota: cambiar la carpeta de salida no mueve resultados existentes. CZSpec usará la nueva ruta después de reiniciar."
            if language == "es" else
            "Note: changing the output folder does not move existing results. CZSpec will use the new path after restart."
        )
        note.setWordWrap(True); root.addWidget(note)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Guardar" if language == "es" else "Save")
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); outer.addWidget(buttons)

        screen = self.screen() or QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.resize(min(720, max(560, geo.width() - 100)), min(700, max(440, geo.height() - 100)))

    def _browse_input(self):
        title = "Seleccionar carpeta de entrada" if self.language == "es" else "Select input folder"
        selected = QFileDialog.getExistingDirectory(self, title, self.input_dir_input.text().strip())
        if selected: self.input_dir_input.setText(selected)

    def _browse_workspace(self):
        title = "Seleccionar espacio de trabajo" if self.language == "es" else "Select workspace folder"
        selected = QFileDialog.getExistingDirectory(self, title, self.workspace_dir_input.text().strip())
        if selected: self.workspace_dir_input.setText(selected)

    def configuration(self) -> dict:
        return {
            "input_dir": self.input_dir_input.text().strip(),
            "workspace_dir": self.workspace_dir_input.text().strip(),
            "text_scale_percent": int(self.text_scale_input.value()),
            "font_family": str(self.font_family_input.currentFont().family() or "Inter"),
            "table_decimal_places": int(self.table_decimal_places_input.value()),
            "table_formats": [key for key, cb in self.table_format_checks.items() if cb.isChecked()],
            "plot_formats": [key for key, cb in self.plot_format_checks.items() if cb.isChecked()],
            "m2_table_formats": [key for key, cb in self.m2_table_format_checks.items() if cb.isChecked()],
            "m2_plot_formats": [key for key, cb in self.m2_plot_format_checks.items() if cb.isChecked()],
            "m3_table_formats": [key for key, cb in self.m3_table_format_checks.items() if cb.isChecked()],
            "m3_plot_formats": [key for key, cb in self.m3_plot_format_checks.items() if cb.isChecked()],
        }


class SourceMetadataDialog(QDialog):
    """Editor y bitácora de perfiles físicos de una fuente.

    Las coordenadas se muestran en el formato astronómico habitual (RA h:m:s,
    DEC d:m:s) pero se conservan internamente en grados ICRS. Una misma fuente
    puede tener múltiples perfiles térmicos (global, hot core, envolvente, etc.).
    """

    def __init__(self, metadata: dict | None = None, language: str = "es", online_enabled: bool = True, parent=None):
        super().__init__(parent)
        self.language = language
        self.online_enabled = bool(online_enabled)
        self.meta = dict(metadata or {})
        self.registry = source_registry()
        self.setWindowTitle("Fuente y metadatos" if language == "es" else "Source and metadata")
        # Keep the dialog usable on 1366x768 laptops and at large text scales.
        self.resize(600, 520)
        self.setMinimumSize(520, 420)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(2, 2, 2, 2)
        body_layout.setSpacing(6)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)
        info = QLabel(
            "Los metadatos se conservan con el espectro. La bitácora admite varios perfiles "
            "para una misma fuente (global, hot core, envolvente, outflow, etc.). SIMBAD es "
            "sólo una ayuda de identificación: nunca sustituye VLSR ni temperaturas."
            if language == "es" else
            "Metadata are stored with the spectrum. The registry supports multiple profiles "
            "for the same source (global, hot core, envelope, outflow, etc.). SIMBAD is only "
            "an identification aid: it never replaces VLSR or temperatures."
        )
        info.setWordWrap(True)
        body_layout.addWidget(info)

        form = QFormLayout()
        self.raw_name = QLineEdit(str(self.meta.get("raw_source_name") or self.meta.get("source") or ""))
        self.canonical = QLineEdit(str(self.meta.get("canonical_name") or ""))
        self.profile_name = QLineEdit(str(self.meta.get("profile_name") or "Global"))
        self.profile_name.setPlaceholderText("Global / Hot core / Envolvente / ..." if language == "es" else "Global / Hot core / Envelope / ...")
        self.component = QLineEdit(str(self.meta.get("component") or ""))
        self.component.setPlaceholderText("HW2, hot core, outflow..." if language == "es" else "HW2, hot core, outflow...")
        self.ra = QLineEdit(format_source_ra(self.meta.get("ra_deg")))
        self.dec = QLineEdit(format_source_dec(self.meta.get("dec_deg")))
        self.ra.setPlaceholderText("22:56:17.98")
        self.dec.setPlaceholderText("+62:01:49.6")
        self.coord_decimal = QLabel("")
        self.coord_decimal.setStyleSheet("color:#64748B; font-size:11px;")
        self.vlsr = QLineEdit("" if self.meta.get("vlsr_kms") is None else f"{float(self.meta['vlsr_kms']):.6g}")
        self.reference_frequency = QLineEdit(
            "" if self.meta.get("spectral_axis_reference_frequency_mhz") is None
            else f"{float(self.meta['spectral_axis_reference_frequency_mhz']):.9g}"
        )
        self.reference_frequency.setPlaceholderText("p. ej. 146969.0")
        self.velocity_convention = QComboBox()
        self.velocity_convention.addItem("Radio", "radio")
        self.velocity_convention.setCurrentIndex(0)
        self.rest = QLineEdit("" if self.meta.get("rest_frequency_mhz") is None else f"{float(self.meta['rest_frequency_mhz']):.9g}")
        self.m1_reference_line = QCheckBox(
            "Usar ν₀ + VLSR como referencia Doppler en M1" if language == "es"
            else "Use ν₀ + VLSR as the M1 Doppler reference"
        )
        self.m1_reference_line.setChecked(bool(self.meta.get("m1_reference_line_active", False)))
        self.m1_reference_line.setToolTip(
            "Actívalo sólo cuando este espectro o recorte corresponde a una transición concreta. M2 puede trabajar después con una ν₀ diferente para cada identificación."
            if language == "es" else
            "Enable only when this spectrum or extraction corresponds to a specific transition. M2 can later use a different ν₀ for each identification."
        )
        self.tex = QLineEdit(", ".join(f"{float(v):g}" for v in (self.meta.get("excitation_temperatures_k") or [])))
        self.tkin = QLineEdit("" if self.meta.get("kinetic_temperature_k") is None else f"{float(self.meta['kinetic_temperature_k']):g}")
        self.trot = QLineEdit("" if self.meta.get("rotational_temperature_k") is None else f"{float(self.meta['rotational_temperature_k']):g}")
        self.notes = QLineEdit(str(self.meta.get("notes") or ""))

        form.addRow("Alias/encabezado:" if language == "es" else "Header alias:", self.raw_name)
        form.addRow("Nombre canónico:" if language == "es" else "Canonical name:", self.canonical)
        form.addRow("Perfil:" if language == "es" else "Profile:", self.profile_name)
        form.addRow("Componente/región:" if language == "es" else "Component/region:", self.component)
        form.addRow("RA [hh:mm:ss]:", self.ra)
        form.addRow("DEC [±dd:mm:ss]:", self.dec)
        form.addRow("Coordenadas [deg]:" if language == "es" else "Coordinates [deg]:", self.coord_decimal)
        form.addRow("VLSR [km/s]:", self.vlsr)
        form.addRow("Frecuencia de referencia M1 [MHz]:" if language == "es" else "M1 reference frequency [MHz]:", self.reference_frequency)
        form.addRow("Convención de velocidad:" if language == "es" else "Velocity convention:", self.velocity_convention)
        ref_note = QLabel(
            "Para .dat/.txt/.csv sin calibración de velocidad, esta frecuencia permite mostrar velocidad relativa (ν_ref → 0 km/s). No es VLSR ni una frecuencia molecular de reposo."
            if language == "es" else
            "For .dat/.txt/.csv without a native velocity calibration, this frequency enables a relative velocity axis (ν_ref → 0 km/s). It is neither VLSR nor a molecular rest frequency."
        )
        ref_note.setWordWrap(True); ref_note.setStyleSheet("color:#64748B;font-size:11px;")
        form.addRow(ref_note)
        form.addRow("Frecuencia de reposo ν₀ [MHz]:" if language == "es" else "Rest frequency ν₀ [MHz]:", self.rest)
        form.addRow("Referencia Doppler M1:" if language == "es" else "M1 Doppler reference:", self.m1_reference_line)
        form.addRow("Tex [K] (lista):" if language == "es" else "Tex [K] (list):", self.tex)
        form.addRow("Tkin [K]:", self.tkin)
        form.addRow("Trot [K]:", self.trot)
        form.addRow("Notas:" if language == "es" else "Notes:", self.notes)
        body_layout.addLayout(form)
        self.ra.textChanged.connect(self._update_decimal_coordinates)
        self.dec.textChanged.connect(self._update_decimal_coordinates)
        self._update_decimal_coordinates()

        actions1 = QGridLayout()
        resolve = QPushButton("Resolver con SIMBAD" if language == "es" else "Resolve with SIMBAD")
        self.simbad_button = resolve
        resolve.setEnabled(self.online_enabled)
        if not self.online_enabled:
            resolve.setToolTip("Disponible en modo Online" if language == "es" else "Available in Online mode")
        resolve.clicked.connect(self._resolve_simbad)
        load_registry = QPushButton("Cargar de bitácora" if language == "es" else "Load from registry")
        load_registry.clicked.connect(self._load_registry)
        delete_registry = QPushButton("Eliminar perfil..." if language == "es" else "Delete profile...")
        delete_registry.clicked.connect(self._delete_registry)
        actions1.addWidget(resolve, 0, 0)
        actions1.addWidget(load_registry, 0, 1)
        actions1.addWidget(delete_registry, 1, 0, 1, 2)
        body_layout.addLayout(actions1)

        actions2 = QGridLayout()
        save_registry = QPushButton("Guardar/actualizar perfil" if language == "es" else "Save/update profile")
        save_registry.clicked.connect(lambda: self._save_registry(False))
        duplicate = QPushButton("Guardar como nuevo perfil" if language == "es" else "Save as new profile")
        duplicate.clicked.connect(lambda: self._save_registry(True))
        export_profile = QPushButton("Exportar perfil..." if language == "es" else "Export profile...")
        export_profile.clicked.connect(self._export_profile)
        actions2.addWidget(save_registry, 0, 0)
        actions2.addWidget(duplicate, 0, 1)
        actions2.addWidget(export_profile, 1, 0, 1, 2)
        body_layout.addLayout(actions2)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        body_layout.addWidget(self.status)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Guardar" if language == "es" else "Save")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar" if language == "es" else "Cancel")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons, 0)

    @staticmethod
    def _number(text):
        try:
            value = float(str(text).strip())
            return value if np.isfinite(value) else None
        except Exception:
            return None

    def _coordinates(self):
        return parse_source_ra(self.ra.text()), parse_source_dec(self.dec.text())

    def _update_decimal_coordinates(self):
        ra_deg, dec_deg = self._coordinates()
        if ra_deg is None or dec_deg is None:
            self.coord_decimal.setText("—")
        else:
            self.coord_decimal.setText(f"RA={ra_deg:.8f}°, DEC={dec_deg:+.8f}°")

    def configuration(self) -> dict:
        out = dict(self.meta)
        out["raw_source_name"] = self.raw_name.text().strip()
        out["canonical_name"] = self.canonical.text().strip()
        out["profile_name"] = self.profile_name.text().strip() or "Global"
        out["component"] = self.component.text().strip()
        out["ra_deg"], out["dec_deg"] = self._coordinates()
        out["vlsr_kms"] = self._number(self.vlsr.text())
        out["spectral_axis_reference_frequency_mhz"] = self._number(self.reference_frequency.text())
        out["velocity_convention"] = str(self.velocity_convention.currentData() or "radio")
        out["rest_frequency_mhz"] = self._number(self.rest.text())
        out["m1_reference_line_active"] = bool(self.m1_reference_line.isChecked())
        if out["m1_reference_line_active"] and out["rest_frequency_mhz"] is None:
            raise ValueError(
                "La referencia Doppler de M1 necesita una frecuencia de reposo ν₀ válida."
                if self.language == "es" else
                "The M1 Doppler reference requires a valid rest frequency ν₀."
            )
        vals = []
        for tok in re.split(r"[,;/\s]+", self.tex.text().strip()):
            num = self._number(tok)
            if num is not None and num > 0:
                vals.append(num)
        out["excitation_temperatures_k"] = sorted(set(vals))
        out["kinetic_temperature_k"] = self._number(self.tkin.text())
        out["rotational_temperature_k"] = self._number(self.trot.text())
        out["notes"] = self.notes.text().strip()
        return out

    def _apply_profile(self, profile: dict):
        self.meta = dict(profile)
        self.raw_name.setText(str(profile.get("raw_source_name") or (profile.get("aliases") or [""])[0] or ""))
        self.canonical.setText(str(profile.get("canonical_name") or ""))
        self.profile_name.setText(str(profile.get("profile_name") or "Global"))
        self.component.setText(str(profile.get("component") or ""))
        self.ra.setText(format_source_ra(profile.get("ra_deg")))
        self.dec.setText(format_source_dec(profile.get("dec_deg")))
        self.vlsr.setText("" if profile.get("vlsr_kms") is None else f"{float(profile['vlsr_kms']):g}")
        self.reference_frequency.setText(
            "" if profile.get("spectral_axis_reference_frequency_mhz") is None
            else f"{float(profile['spectral_axis_reference_frequency_mhz']):.9g}"
        )
        self.velocity_convention.setCurrentIndex(max(0, self.velocity_convention.findData(str(profile.get("velocity_convention") or "radio"))))
        self.rest.setText("" if profile.get("rest_frequency_mhz") is None else f"{float(profile['rest_frequency_mhz']):.9g}")
        self.m1_reference_line.setChecked(bool(profile.get("m1_reference_line_active", False)))
        self.tex.setText(", ".join(f"{float(v):g}" for v in (profile.get("excitation_temperatures_k") or [])))
        self.tkin.setText("" if profile.get("kinetic_temperature_k") is None else f"{float(profile['kinetic_temperature_k']):g}")
        self.trot.setText("" if profile.get("rotational_temperature_k") is None else f"{float(profile['rotational_temperature_k']):g}")
        self.notes.setText(str(profile.get("notes") or ""))
        self._update_decimal_coordinates()

    def _resolve_simbad(self):
        if not self.online_enabled:
            self.status.setText(
                "SIMBAD se omite en modo sin Internet." if self.language == "es" else
                "SIMBAD is skipped in Offline mode."
            )
            return
        cfg = self.configuration()
        try:
            candidates = resolve_source_simbad_candidates(
                raw_name=cfg.get("raw_source_name", ""),
                canonical_name=cfg.get("canonical_name", ""),
                ra_deg=cfg.get("ra_deg"), dec_deg=cfg.get("dec_deg"),
                radius_arcsec=90.0, limit=12,
            )
            if not candidates:
                self.status.setText("SIMBAD no encontró una coincidencia." if self.language == "es" else "No SIMBAD match found.")
                return
            labels = []
            for row in candidates:
                name = str(row.get("canonical_name") or "(sin nombre)")
                ra_text = format_source_ra(row.get("ra_deg")) or "—"
                dec_text = format_source_dec(row.get("dec_deg")) or "—"
                sep = row.get("separation_arcsec")
                sep_text = "" if sep is None else (f" · {float(sep):.1f} arcsec" if self.language == "es" else f" · {float(sep):.1f} arcsec")
                otype = str(row.get("object_type") or "").strip()
                type_text = f" · {otype}" if otype else ""
                labels.append(f"{name}{type_text} · {ra_text} {dec_text}{sep_text}")
            if len(candidates) == 1:
                chosen = candidates[0]
            else:
                selected, ok = QInputDialog.getItem(
                    self, "SIMBAD",
                    "Coincidencia:" if self.language == "es" else "Match:",
                    labels, 0, False,
                )
                if not ok or selected not in labels:
                    self.status.setText("Sugerencia de SIMBAD ignorada." if self.language == "es" else "SIMBAD suggestion ignored.")
                    return
                chosen = candidates[labels.index(selected)]
            name = str(chosen.get("canonical_name") or "")
            ra_text = format_source_ra(chosen.get("ra_deg"))
            dec_text = format_source_dec(chosen.get("dec_deg"))
            sep = chosen.get("separation_arcsec")
            extra = "" if sep is None else f"\nSeparación = {float(sep):.2f} arcsec"
            message = (
                f"SIMBAD propone:\n{name}\nRA={ra_text}\nDEC={dec_text}{extra}\n\n¿Aplicar esta identidad/posición?"
                if self.language == "es" else
                f"SIMBAD proposes:\n{name}\nRA={ra_text}\nDEC={dec_text}{extra}\n\nApply this identity/position?"
            )
            answer = QMessageBox.question(self, "SIMBAD", message, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                self.status.setText("Sugerencia de SIMBAD ignorada." if self.language == "es" else "SIMBAD suggestion ignored.")
                return
            if name:
                self.canonical.setText(name)
            if chosen.get("ra_deg") is not None:
                self.ra.setText(format_source_ra(chosen["ra_deg"]))
            if chosen.get("dec_deg") is not None:
                self.dec.setText(format_source_dec(chosen["dec_deg"]))
            self.status.setText(
                "Nombre/posición aplicados. VLSR y temperaturas permanecen bajo control del usuario."
                if self.language == "es" else
                "Name/position applied. VLSR and temperatures remain user-controlled."
            )
        except Exception as exc:
            self.status.setText(str(exc))

    def _load_registry(self):
        cfg = self.configuration()
        profiles = self.registry.list_profiles(
            raw_name=cfg.get("raw_source_name", ""), canonical_name=cfg.get("canonical_name", ""),
            ra_deg=cfg.get("ra_deg"), dec_deg=cfg.get("dec_deg"), radius_arcsec=90.0,
        )
        if not profiles:
            profiles = list(self.registry.user_entries)
        if not profiles:
            self.status.setText("La bitácora todavía no contiene perfiles." if self.language == "es" else "The registry does not contain profiles yet.")
            return
        labels=[]
        for row in profiles:
            source=str(row.get("canonical_name") or row.get("raw_source_name") or "Fuente")
            profile=str(row.get("profile_name") or "Global")
            component=str(row.get("component") or "")
            temps=[]
            if row.get("excitation_temperatures_k"):
                temps.append("Tex="+",".join(f"{float(v):g}" for v in row["excitation_temperatures_k"]))
            if row.get("kinetic_temperature_k") is not None:
                temps.append(f"Tkin={float(row['kinetic_temperature_k']):g}")
            suffix=(" · "+", ".join(temps)) if temps else ""
            labels.append(f"{source} · {profile}" + (f" · {component}" if component else "") + suffix)
        selected, ok = QInputDialog.getItem(
            self, "Bitácora de fuentes" if self.language == "es" else "Source registry",
            "Perfil:" if self.language == "es" else "Profile:", labels, 0, False,
        )
        if ok and selected in labels:
            self._apply_profile(profiles[labels.index(selected)])
            self.status.setText("Perfil cargado desde la bitácora." if self.language == "es" else "Profile loaded from registry.")

    def _delete_registry(self):
        cfg = self.configuration()
        profiles = self.registry.list_profiles(
            raw_name=cfg.get("raw_source_name", ""), canonical_name=cfg.get("canonical_name", ""),
            ra_deg=cfg.get("ra_deg"), dec_deg=cfg.get("dec_deg"), radius_arcsec=90.0,
        )
        if not profiles:
            profiles = list(self.registry.user_entries)
        if not profiles:
            self.status.setText("La bitácora no contiene perfiles eliminables." if self.language == "es" else "The registry contains no deletable profiles.")
            return
        labels=[]
        for row in profiles:
            source=str(row.get("canonical_name") or row.get("raw_source_name") or "Fuente")
            profile=str(row.get("profile_name") or "Global")
            component=str(row.get("component") or "")
            labels.append(f"{source} · {profile}" + (f" · {component}" if component else ""))
        selected, ok = QInputDialog.getItem(
            self, "Eliminar perfil" if self.language == "es" else "Delete profile",
            "Perfil:" if self.language == "es" else "Profile:", labels, 0, False,
        )
        if not ok or selected not in labels:
            return
        row=profiles[labels.index(selected)]
        pid=str(row.get("profile_id") or "")
        if not pid or pid.startswith("builtin:"):
            self.status.setText("Los perfiles integrados de CZSpec no se pueden eliminar." if self.language == "es" else "Built-in CZSpec profiles cannot be deleted.")
            return
        question=(f"¿Eliminar definitivamente el perfil?\n\n{selected}" if self.language == "es" else f"Permanently delete this profile?\n\n{selected}")
        answer=QMessageBox.question(self, "Bitácora" if self.language == "es" else "Registry", question, QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self.registry.delete_entry(pid):
            self.registry=source_registry()
            self.status.setText("Perfil eliminado de la bitácora." if self.language == "es" else "Profile deleted from registry.")
        else:
            self.status.setText("No se pudo eliminar el perfil." if self.language == "es" else "Could not delete profile.")

    def _save_registry(self, duplicate: bool = False):
        try:
            entry = self.registry.save_entry(self.configuration(), duplicate=duplicate)
            self.meta.update(entry)
            self.status.setText(
                f"Perfil '{entry.get('profile_name','Global')}' guardado en la bitácora local."
                if self.language == "es" else
                f"Profile '{entry.get('profile_name','Global')}' saved to the local registry."
            )
        except Exception as exc:
            self.status.setText(str(exc))

    def _export_profile(self):
        cfg = self.configuration()
        source = re.sub(r"[^A-Za-z0-9_.+-]+", "_", str(cfg.get("canonical_name") or cfg.get("raw_source_name") or "source"))
        profile = re.sub(r"[^A-Za-z0-9_.+-]+", "_", str(cfg.get("profile_name") or "global"))
        default = str(WORKSPACE_DIR / "outputs" / f"{source}_{profile}_metadata.json")
        path, _ = QFileDialog.getSaveFileName(self, "Exportar perfil" if self.language == "es" else "Export profile", default, "JSON (*.json)")
        if not path:
            return
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        self.status.setText(f"Perfil exportado: {path}" if self.language == "es" else f"Profile exported: {path}")


class CalibrationDialog(QDialog):
    """Selector inequívoco de escala/calibración de intensidad.

    Cada modo es mutuamente excluyente. En particular, ``eta`` (divisor legado)
    y ``F_eff/B_eff`` nunca se aplican simultáneamente.
    """
    def __init__(self, metadata: dict, current: dict | None = None, median_frequency_mhz: float | None = None,
                 language: str = "es", parent=None):
        super().__init__(parent)
        self.language=language; self.meta=dict(metadata or {}); self.median_frequency_mhz=median_frequency_mhz
        current=dict(current or {})
        self.setWindowTitle("Calibración de intensidad" if language=="es" else "Intensity calibration")
        self.resize(760, 610)
        root=QVBoxLayout(self)
        intro=QLabel((
            "Elige UNA transformación de escala. Bₑff es la eficiencia del haz principal y Fₑff la eficiencia "
            "hacia el hemisferio delantero. Para datos IRAM 30m en T_A*, la conversión a T_mb usa Fₑff/Bₑff. "
            "El modo manual conserva el comportamiento T_out=T_in/Bₑff."
            if language=="es" else
            "Choose ONE scale transformation. Bₑff is the main-beam efficiency and Fₑff is the forward "
            "efficiency. For IRAM 30m T_A* data, T_mb uses Fₑff/Bₑff. Manual mode preserves T_out=T_in/Bₑff."
        )); intro.setWordWrap(True); root.addWidget(intro)

        self.mode=QComboBox()
        self.mode.addItem("Bₑff manual (T/Bₑff)" if language=="es" else "Manual Bₑff (T/Bₑff)", "eta")
        self.mode.addItem("IRAM 30m · Fₑff/Bₑff del encabezado" if language=="es" else "IRAM 30m · header Fₑff/Bₑff", "auto")
        self.mode.addItem("IRAM 30m · tabla de referencia" if language=="es" else "IRAM 30m · reference table", "iram")
        self.mode.addItem("Sin corrección" if language=="es" else "No correction", "none")
        self.mode.addItem("Factor multiplicativo personalizado" if language=="es" else "Custom multiplicative factor", "custom")
        self.saved_profiles=load_custom_calibration_profiles()
        for i, profile in enumerate(self.saved_profiles):
            self.mode.addItem(("Perfil: " if language=="es" else "Profile: ")+str(profile.get("name") or f"{i+1}"), f"profile:{i}")

        form=QFormLayout()
        form.addRow("Modo:" if language=="es" else "Mode:", self.mode)
        self.eta_value=QDoubleSpinBox(); self.eta_value.setDecimals(5); self.eta_value.setRange(0.00001,1.5); self.eta_value.setSingleStep(0.01)
        self.eta_value.setValue(float(current.get("eta",0.81) or 0.81))
        form.addRow("Bₑff:", self.eta_value)
        self.eta_label=form.labelForField(self.eta_value)
        self.custom_factor=QDoubleSpinBox(); self.custom_factor.setDecimals(6); self.custom_factor.setRange(0.000001,1000); self.custom_factor.setValue(float(current.get("factor",1.0) or 1.0))
        form.addRow("Factor multiplicativo:" if language=="es" else "Multiplicative factor:", self.custom_factor)
        self.custom_factor_label=form.labelForField(self.custom_factor)
        self.custom_name=QLineEdit(); self.custom_name.setPlaceholderText("Mi perfil" if language=="es" else "My profile")
        form.addRow("Nombre del perfil:" if language=="es" else "Profile name:", self.custom_name)
        self.custom_name_label=form.labelForField(self.custom_name)
        root.addLayout(form)
        self.save_custom_button=QPushButton("Guardar perfil personalizado" if language=="es" else "Save custom profile")
        self.save_custom_button.clicked.connect(self._save_custom); root.addWidget(self.save_custom_button)

        table_box=QGroupBox("Tabla de referencia IRAM 30m" if language=="es" else "IRAM 30m reference table")
        tl=QVBoxLayout(table_box); self.table=QTableWidget(8,4); self.table.setHorizontalHeaderLabels(["ν [GHz]","Fₑff","Bₑff","Fₑff/Bₑff"])
        from czspec.logic.calibration import IRAM30M_REFERENCE
        for r,(nu,fwd,beam) in enumerate(IRAM30M_REFERENCE):
            for c,val in enumerate((nu,fwd,beam,fwd/beam)):
                item=QTableWidgetItem(f"{val:.4g}"); item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable); self.table.setItem(r,c,item)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); tl.addWidget(self.table); root.addWidget(table_box)

        explanation=QLabel((
            "Definiciones: Bₑff es la eficiencia del haz principal; Fₑff describe el acoplamiento al hemisferio "
            "delantero; Fₑff/Bₑff transforma T_A* a T_mb en la convención IRAM 30m. La tabla sólo se usa si "
            "seleccionas explícitamente ese modo."
            if language=="es" else
            "Definitions: Bₑff is the main-beam efficiency; Fₑff describes forward-hemisphere coupling; "
            "Fₑff/Bₑff is the IRAM 30m T_A* to T_mb factor. The table is used only when explicitly selected."
        )); explanation.setWordWrap(True); root.addWidget(explanation)

        policy_box=QGroupBox("Política por instalación/producto" if language=="es" else "Facility/product policy")
        pl=QVBoxLayout(policy_box)
        from czspec.logic.calibration import FACILITY_POLICIES
        self.policy_table=QTableWidget(len(FACILITY_POLICIES),3)
        self.policy_table.setHorizontalHeaderLabels(["Instalación" if language=="es" else "Facility", "Producto" if language=="es" else "Product", "Tratamiento" if language=="es" else "Treatment"])
        for r,row in enumerate(FACILITY_POLICIES):
            vals=(
                row.get("facility",""),
                row.get("product_es","") if language=="es" else row.get("product_en",""),
                row.get("policy_es","") if language=="es" else row.get("policy_en",""),
            )
            for c,val in enumerate(vals):
                item=QTableWidgetItem(str(val)); item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable); self.policy_table.setItem(r,c,item)
        self.policy_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.policy_table.setWordWrap(True); self.policy_table.resizeRowsToContents(); pl.addWidget(self.policy_table); root.addWidget(policy_box)

        self.summary=QLabel(""); self.summary.setWordWrap(True); self.summary.setStyleSheet("font-weight:600;"); root.addWidget(self.summary)
        self.mode.currentIndexChanged.connect(self._refresh); self.custom_factor.valueChanged.connect(self._refresh); self.eta_value.valueChanged.connect(self._refresh)
        idx=self.mode.findData(str(current.get("mode","eta"))); self.mode.setCurrentIndex(max(0,idx)); self._refresh()
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Usar" if language=="es" else "Use")
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def configuration(self):
        mode=str(self.mode.currentData())
        if mode=="eta":
            eta=float(self.eta_value.value()); cfg={"mode":"eta","factor":1.0/eta,"eta":eta,"beam_eff":eta,
                "name":f"Bₑff manual = {eta:g}","notes":"Modo manual: T_out = T_in / B_eff"}
        elif mode=="auto":
            cfg=automatic_calibration(self.meta,self.median_frequency_mhz)
            if cfg.get("mode")=="none":
                cfg["name"]="Header sin Fₑff/Bₑff · sin corrección" if self.language=="es" else "Header without Fₑff/Bₑff · no correction"
        elif mode=="iram": cfg=iram30m_reference_profile(self.median_frequency_mhz or self.meta.get("rest_frequency_mhz") or 86000)
        elif mode=="custom": cfg={"mode":"custom","factor":float(self.custom_factor.value()),"name":self.custom_name.text().strip() or ("Factor personalizado" if self.language=="es" else "Custom factor")}
        elif mode.startswith("profile:"):
            try: cfg=dict(self.saved_profiles[int(mode.split(":",1)[1])])
            except Exception: cfg={"mode":"none","factor":1.0,"name":"Perfil inválido"}
        else: cfg={"mode":"none","factor":1.0,"name":"Sin corrección" if self.language=="es" else "No correction"}
        return cfg

    def _save_custom(self):
        profile={"mode":"custom","factor":float(self.custom_factor.value()),"name":self.custom_name.text().strip() or ("Perfil personalizado" if self.language=="es" else "Custom profile")}
        profiles=list(self.saved_profiles); profiles.append(profile); save_custom_calibration_profiles(profiles); self.saved_profiles=profiles
        self.mode.addItem(("Perfil: " if self.language=="es" else "Profile: ")+profile["name"], f"profile:{len(profiles)-1}")
        self.summary.setText(("Perfil guardado: " if self.language=="es" else "Profile saved: ")+profile["name"])

    def _refresh(self,*_):
        mode=str(self.mode.currentData()); cfg=self.configuration()
        self.eta_value.setVisible(mode=="eta"); self.eta_label.setVisible(mode=="eta")
        self.custom_factor.setVisible(mode=="custom"); self.custom_factor_label.setVisible(mode=="custom")
        self.custom_name.setVisible(mode=="custom"); self.custom_name_label.setVisible(mode=="custom"); self.save_custom_button.setVisible(mode=="custom")
        factor=float(cfg.get("factor",1.0) or 1.0)
        self.summary.setText(("Corrección que se aplicará: " if self.language=="es" else "Correction to be applied: ")+f"{cfg.get('name')} · factor={factor:.6g}")


class FitsImportDialog(QDialog):
    """Selección mínima de HDU y extracción 1-D para FITS/cubos."""
    def __init__(self, path: str, infos: list, language: str="es", parent=None):
        super().__init__(parent); self.language=language; self.path=path; self.infos=list(infos)
        self.setWindowTitle("Importar FITS" if language=="es" else "Import FITS"); self.resize(620,450); root=QVBoxLayout(self)
        text=QLabel("Para un cubo, M1 extrae un espectro 1-D y conserva WCS/coordenadas para módulos posteriores." if language=="es" else "For a cube, M1 extracts a 1-D spectrum and preserves WCS/coordinates for later modules."); text.setWordWrap(True); root.addWidget(text)
        form=QFormLayout(); self.hdu=QComboBox()
        for info in self.infos: self.hdu.addItem(f"HDU {info.index} · {info.name} · {info.shape}", info.index)
        form.addRow("HDU:",self.hdu)
        self.x=QDoubleSpinBox(); self.x.setRange(-1,1e6); self.x.setValue(-1); self.y=QDoubleSpinBox(); self.y.setRange(-1,1e6); self.y.setValue(-1)
        self.radius=QDoubleSpinBox(); self.radius.setRange(0,1e5); self.radius.setValue(0); self.radius.setDecimals(2)
        self.stat=QComboBox(); self.stat.addItem("Media" if language=="es" else "Mean","mean"); self.stat.addItem("Mediana" if language=="es" else "Median","median"); self.stat.addItem("Suma" if language=="es" else "Sum","sum")
        self.ra=QLineEdit(); self.dec=QLineEdit(); self.ra.setPlaceholderText("opcional" if language=="es" else "optional"); self.dec.setPlaceholderText("opcional" if language=="es" else "optional")
        form.addRow("X pixel (-1=centro):" if language=="es" else "X pixel (-1=center):",self.x); form.addRow("Y pixel (-1=centro):" if language=="es" else "Y pixel (-1=center):",self.y); form.addRow("Radio apertura [pix]:" if language=="es" else "Aperture radius [pix]:",self.radius); form.addRow("Estadístico:" if language=="es" else "Statistic:",self.stat); form.addRow("RA [deg] (opcional):" if language=="es" else "RA [deg] (optional):",self.ra); form.addRow("DEC [deg] (opcional):" if language=="es" else "DEC [deg] (optional):",self.dec); root.addLayout(form)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)
    def configuration(self):
        def num(text):
            try:return float(text) if str(text).strip() else None
            except:return None
        return {"hdu_index":int(self.hdu.currentData()),"x":None if self.x.value()<0 else float(self.x.value()),"y":None if self.y.value()<0 else float(self.y.value()),"aperture_radius_px":float(self.radius.value()),"statistic":str(self.stat.currentData()),"ra_deg":num(self.ra.text()),"dec_deg":num(self.dec.text())}



class SpectrumSmoothingDialog(QDialog):
    """Panel no modal para probar suavizados mientras el espectro sigue interactivo."""

    applyRequested = Signal(dict)
    applyAllRequested = Signal(dict)

    def __init__(
        self,
        engine_label: str,
        current: dict | None = None,
        parent=None,
        language: str = "es",
        spectrum_count: int = 1,
    ):
        super().__init__(parent)
        self.language = language
        self.spectrum_count = max(1, int(spectrum_count))
        self.setWindowTitle("Suavizado" if language == "es" else "Smoothing")
        self.resize(500, 245)
        self.setModal(False)
        self.setWindowModality(Qt.WindowModality.NonModal)
        current = dict(current or {})

        root = QVBoxLayout(self)
        intro = QLabel(
            "BOX y Gaussiano se recalculan desde el producto base. Hanning es acumulativo: "
            "cada pulsación de Aplicar vuelve a aplicar Hanning al resultado Hanning actual. "
            "Puedes mantener esta ventana abierta para comparar sucesivos pases."
            if language == "es" else
            "BOX and Gaussian are recalculated from the base product. Hanning is cumulative: "
            "each press of Apply applies Hanning again to the current Hanning result. "
            "Keep this window open to compare successive passes."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        engine = QLabel(
            f"Motor: {engine_label}" if language == "es" else f"Engine: {engine_label}"
        )
        engine.setWordWrap(True)
        root.addWidget(engine)

        form = QFormLayout()
        self.method_combo = QComboBox()
        self.method_combo.addItem(
            "Sin suavizado · restaurar original" if language == "es" else "No smoothing · restore original",
            "none",
        )
        self.method_combo.addItem("Hanning", "hanning")
        self.method_combo.addItem(
            "Box · promedio de N canales" if language == "es" else "Box · average N channels",
            "box",
        )
        self.method_combo.addItem(
            "Gaussiano · ancho en km/s" if language == "es" else "Gaussian · width in km/s",
            "gauss",
        )
        idx = self.method_combo.findData(str(current.get("smooth_method") or "none"))
        self.method_combo.setCurrentIndex(max(0, idx))
        form.addRow("Método:" if language == "es" else "Method:", self.method_combo)

        self.value_row = QWidget()
        value_layout = QHBoxLayout(self.value_row)
        value_layout.setContentsMargins(0, 0, 0, 0)
        self.value_input = QDoubleSpinBox()
        self.value_input.setValue(float(current.get("smooth_value") or 2.0))
        self.units_label = QLabel("")
        value_layout.addWidget(self.value_input)
        value_layout.addWidget(self.units_label)
        value_layout.addStretch()
        self.parameter_label = QLabel("Parámetro:" if language == "es" else "Parameter:")
        form.addRow(self.parameter_label, self.value_row)
        self.form_layout = form
        root.addLayout(form)

        self.note = QLabel("")
        self.note.setWordWrap(True)
        root.addWidget(self.note)

        bottom = QHBoxLayout()
        self.apply_button = QPushButton("Aplicar" if language == "es" else "Apply")
        self.apply_all_button = QPushButton(
            "Aplicar a todos" if language == "es" else "Apply to all"
        )
        self.close_button = QPushButton("Cerrar" if language == "es" else "Close")
        self.apply_button.clicked.connect(self._emit_apply)
        self.apply_all_button.clicked.connect(self._emit_apply_all)
        self.close_button.clicked.connect(self.close)
        self.apply_all_button.setEnabled(self.spectrum_count > 1)
        if self.spectrum_count <= 1:
            self.apply_all_button.setToolTip(
                "La sesión contiene un solo espectro."
                if language == "es" else
                "The session contains only one spectrum."
            )
        else:
            self.apply_all_button.setToolTip(
                f"Aplica este método a los {self.spectrum_count} espectros cargados."
                if language == "es" else
                f"Apply this method to all {self.spectrum_count} loaded spectra."
            )
        bottom.addStretch()
        bottom.addWidget(self.apply_button)
        bottom.addWidget(self.apply_all_button)
        bottom.addWidget(self.close_button)
        root.addLayout(bottom)

        self.method_combo.currentIndexChanged.connect(self._refresh_controls)
        self._refresh_controls()

    def _refresh_controls(self):
        es = self.language == "es"
        method = str(self.method_combo.currentData() or "none")
        show_parameter = method in {"box", "gauss"}
        # Hanning y restaurar original no requieren ningún parámetro. Ocultar
        # completamente la fila evita sugerir al usuario que ese valor interviene.
        try:
            self.form_layout.setRowVisible(self.value_row, show_parameter)
        except Exception:
            self.parameter_label.setVisible(show_parameter)
            self.value_row.setVisible(show_parameter)
        if method == "box":
            self.value_input.setEnabled(True)
            self.value_input.setDecimals(0)
            self.value_input.setRange(2, 50)
            self.value_input.setSingleStep(1)
            if self.value_input.value() < 2:
                self.value_input.setValue(2)
            self.units_label.setText("canales" if es else "channels")
            self.note.setText(
                "BOX promedia N canales adyacentes y reduce el número de canales de salida."
                if es else
                "BOX averages N adjacent channels and reduces the number of output channels."
            )
        elif method == "gauss":
            self.value_input.setEnabled(True)
            self.value_input.setDecimals(2)
            self.value_input.setRange(0.01, 100.0)
            self.value_input.setSingleStep(0.25)
            if self.value_input.value() < 0.01:
                self.value_input.setValue(1.0)
            self.units_label.setText("km/s")
            self.note.setText(
                "Convolución gaussiana con el ancho indicado."
                if es else "Gaussian convolution with the selected width."
            )
        elif method == "hanning":
            self.value_input.setEnabled(False)
            self.units_label.setText("")
            self.note.setText(
                "Hanning de 3 puntos + decimación ×2. Aplicar de nuevo genera Hanning ×2, ×3, … sobre el resultado anterior."
                if es else
                "3-point Hanning + ×2 decimation. Apply again produces Hanning ×2, ×3, … from the previous Hanning result."
            )
        else:
            self.value_input.setEnabled(False)
            self.units_label.setText("")
            self.note.setText(
                "Restaura el espectro que se cargó originalmente."
                if es else "Restores the originally loaded spectrum."
            )

    def configuration(self) -> dict:
        method = str(self.method_combo.currentData() or "none")
        value = None
        if method == "box":
            value = int(round(self.value_input.value()))
        elif method == "gauss":
            value = float(self.value_input.value())
        return {"smooth_method": method, "smooth_value": value}

    def _emit_apply(self):
        self.applyRequested.emit(self.configuration())

    def _emit_apply_all(self):
        self.applyAllRequested.emit(self.configuration())

    def set_busy(self, busy: bool):
        self.apply_button.setEnabled(not busy)
        self.apply_all_button.setEnabled((not busy) and self.spectrum_count > 1)
        self.method_combo.setEnabled(not busy)
        self.value_input.setEnabled((not busy) and str(self.method_combo.currentData() or "none") in {"box", "gauss"})


class SpectrumComparisonDialog(QDialog):
    """Configura qué espectros y qué representación se comparan en M1."""

    PALETTE = [
        "#1D6EEB", "#E67E22", "#16A085", "#D64550", "#8E5CE6",
        "#2D3436", "#DB2777", "#65A30D", "#0891B2", "#7C3AED",
    ]

    def __init__(self, entries: list[dict], current_config: dict | None = None, language: str = "es", parent=None):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle("Configurar comparación espectral" if language == "es" else "Configure spectral comparison")
        self.resize(930, 760)
        self.entries = list(entries)
        self.current_config = deepcopy(current_config or {})
        self.row_widgets = {}

        root = QVBoxLayout(self)
        intro = QLabel(
            ("Elige datos crudos o analizados, la disposición y el estilo de cada archivo. "
             "Puedes compartir escalas, superponer ventanas o agrupar bandas contiguas con una brecha visual.")
            if language == "es" else
            ("Choose raw or analyzed data, layout and style for each file. "
             "You can share scales, overlay windows, or group contiguous bands with a visual spectral break.")
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        options = QGroupBox("Representación" if language == "es" else "Representation")
        options_layout = QGridLayout(options)
        self.content_combo = QComboBox()
        self.content_combo.addItem("Espectros crudos" if language == "es" else "Raw spectra", "raw")
        self.content_combo.addItem("Espectros analizados (corregidos por base)" if language == "es" else "Analyzed spectra (baseline corrected)", "analyzed")
        self.content_combo.addItem("Espectros analizados + perfiles ajustados" if language == "es" else "Analyzed spectra + fitted profiles", "analyzed_fits")
        default_content = "analyzed_fits" if any(bool(e.get("analyzed")) for e in self.entries) else "raw"
        content_index = self.content_combo.findData(self.current_config.get("content", default_content))
        self.content_combo.setCurrentIndex(max(0, content_index))

        self.layout_combo = QComboBox()
        self.layout_combo.addItem("Automática" if language == "es" else "Automatic", "auto")
        self.layout_combo.addItem("Bandas alineadas" if language == "es" else "Aligned bands", "aligned")
        self.layout_combo.addItem("Cuadrícula" if language == "es" else "Grid", "grid")
        self.layout_combo.addItem("Bandas continuas" if language == "es" else "Continuous bands", "continuous")
        self.layout_combo.addItem("Bandas continuas con brecha" if language == "es" else "Continuous bands with break", "stitched")
        saved_layout = str(self.current_config.get("layout", "grid"))
        if saved_layout == "overlay": saved_layout = "continuous"
        layout_index = self.layout_combo.findData(saved_layout)
        self.layout_combo.setCurrentIndex(max(0, layout_index))

        self.share_x_checkbox = QCheckBox("Compartir escala X entre paneles" if language == "es" else "Share X scale across panels")
        self.share_x_checkbox.setChecked(bool(self.current_config.get("share_x", False)))
        self.share_x_checkbox.setToolTip(
            "Úsalo sólo cuando quieras imponer el mismo rango espectral a todos los paneles."
            if language == "es" else "Use only when you want the same spectral range on every panel."
        )
        self.share_y_checkbox = QCheckBox("Compartir escala Y entre paneles" if language == "es" else "Share Y scale across panels")
        self.share_y_checkbox.setChecked(bool(self.current_config.get("share_y", False)))
        self.share_y_checkbox.setToolTip(
            "Úsalo cuando todos los espectros estén expresados en la misma unidad."
        )
        self.show_sum_checkbox = QCheckBox("Mostrar suma/combinado en solapamientos" if language == "es" else "Show summed/combined overlap")
        self.show_sum_checkbox.setChecked(bool(self.current_config.get("show_sum", False)))
        options_layout.addWidget(QLabel("Contenido:" if language == "es" else "Content:"), 0, 0)
        options_layout.addWidget(self.content_combo, 0, 1)
        options_layout.addWidget(QLabel("Disposición:" if language == "es" else "Layout:"), 0, 2)
        options_layout.addWidget(self.layout_combo, 0, 3)
        options_layout.addWidget(self.share_x_checkbox, 1, 0, 1, 2)
        options_layout.addWidget(self.share_y_checkbox, 1, 2, 1, 2)
        options_layout.addWidget(self.show_sum_checkbox, 2, 0, 1, 4)
        root.addWidget(options)

        # Style controls for the optional combined-overlap curves.  One style
        # slot per possible band keeps independent combined curves visually
        # distinguishable instead of forcing the old fixed yellow/green colors.
        self.sum_styles_box = QGroupBox("Estilo de solapamientos combinados" if language == "es" else "Combined-overlap styles")
        self.sum_styles_layout = QFormLayout(self.sum_styles_box)
        self.sum_style_widgets = []
        saved_sum_styles = self.current_config.get("sum_styles", [])
        combined_defaults = ["#7C3AED", "#059669", "#B45309", "#BE123C", "#0369A1", "#4D7C0F"]
        for i in range(max(1, min(len(self.entries), 6))):
            saved_sum = saved_sum_styles[i] if isinstance(saved_sum_styles, list) and i < len(saved_sum_styles) and isinstance(saved_sum_styles[i], dict) else {}
            row = QWidget(); lay = QHBoxLayout(row); lay.setContentsMargins(0,0,0,0); lay.setSpacing(6)
            color = QPushButton(); color.setProperty("czspecColor", str(saved_sum.get("color") or combined_defaults[i % len(combined_defaults)]).upper())
            color.clicked.connect(lambda _checked=False, button=color: self._choose_color(button)); self._refresh_color_button(color)
            width = QDoubleSpinBox(); width.setRange(0.5,8.0); width.setDecimals(2); width.setSingleStep(0.25); width.setSuffix(" px"); width.setValue(float(saved_sum.get("width",2.2)))
            dash = QComboBox(); [dash.addItem(label,value) for label,value in LINE_STYLE_OPTIONS]; dash.setCurrentIndex(max(0,dash.findData(saved_sum.get("dash","solid"))))
            lay.addWidget(color); lay.addWidget(width); lay.addWidget(dash,1)
            self.sum_styles_layout.addRow((f"Combinado {i+1}:" if language=="es" else f"Combined {i+1}:"), row)
            self.sum_style_widgets.append((color,width,dash))
        self.sum_styles_box.setVisible(self.show_sum_checkbox.isChecked())
        self.show_sum_checkbox.toggled.connect(self.sum_styles_box.setVisible)
        root.addWidget(self.sum_styles_box)

        self.table = QTableWidget(len(self.entries), 6)
        self.table.setHorizontalHeaderLabels(
            (["Incluir", "Archivo", "Estado", "Color", "Grosor", "Línea"]
             if language == "es" else
             ["Include", "File", "Status", "Color", "Width", "Line"])
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        root.addWidget(self.table, stretch=1)

        saved_files = self.current_config.get("files", {})
        for row, entry in enumerate(self.entries):
            path = str(entry["path"])
            saved = saved_files.get(path, {}) if isinstance(saved_files, dict) else {}
            include = QCheckBox()
            include.setChecked(bool(saved.get("included", False)))
            include_holder = QWidget()
            include_layout = QHBoxLayout(include_holder)
            include_layout.setContentsMargins(0, 0, 0, 0)
            include_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            include_layout.addWidget(include)
            self.table.setCellWidget(row, 0, include_holder)

            name_item = QTableWidgetItem(str(entry.get("name") or Path(path).name))
            name_item.setToolTip(path)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 1, name_item)

            analyzed = bool(entry.get("analyzed"))
            status_item = QTableWidgetItem(("Analizado" if analyzed else "Solo crudo") if language == "es" else ("Analyzed" if analyzed else "Raw only"))
            status_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 2, status_item)

            color = str(saved.get("color") or self.PALETTE[row % len(self.PALETTE)]).upper()
            color_button = QPushButton()
            color_button.setProperty("czspecColor", color)
            color_button.clicked.connect(
                lambda _checked=False, button=color_button: self._choose_color(button)
            )
            self._refresh_color_button(color_button)
            self.table.setCellWidget(row, 3, color_button)

            width = QDoubleSpinBox()
            width.setRange(0.5, 8.0)
            width.setSingleStep(0.25)
            width.setDecimals(2)
            width.setSuffix(" px")
            width.setValue(float(saved.get("width", 1.4)))
            self.table.setCellWidget(row, 4, width)

            dash = QComboBox()
            for label, value in LINE_STYLE_OPTIONS:
                dash.addItem(label, value)
            dash.setCurrentIndex(max(0, dash.findData(saved.get("dash", "solid"))))
            self.table.setCellWidget(row, 5, dash)
            self.row_widgets[path] = (include, color_button, width, dash)

        footer = QHBoxLayout()
        all_button = QPushButton("Incluir todos" if language == "es" else "Include all")
        none_button = QPushButton("Quitar todos" if language == "es" else "Clear all")
        all_button.clicked.connect(lambda: self._set_all_included(True))
        none_button.clicked.connect(lambda: self._set_all_included(False))
        footer.addWidget(all_button)
        footer.addWidget(none_button)
        footer.addStretch()
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        footer.addWidget(buttons)
        root.addLayout(footer)

    def _set_all_included(self, checked: bool):
        for include, _, _, _ in self.row_widgets.values():
            include.setChecked(checked)

    @staticmethod
    def _refresh_color_button(button: QPushButton):
        color_value = str(button.property("czspecColor") or "#1D6EEB").upper()
        color = QColor(color_value)
        luminance = 0.2126 * color.redF() + 0.7152 * color.greenF() + 0.0722 * color.blueF()
        text_color = "#111827" if luminance > 0.58 else "#FFFFFF"
        button.setText(color_value)
        button.setStyleSheet(
            "QPushButton {"
            f"background-color:{color_value};color:{text_color};"
            "border:1px solid #A8B4C6;font-weight:700;}"
        )

    def _choose_color(self, button: QPushButton):
        current = QColor(str(button.property("czspecColor") or "#1D6EEB"))
        selected = QColorDialog.getColor(current, self, "Color del espectro" if self.language == "es" else "Spectrum color")
        if selected.isValid():
            button.setProperty("czspecColor", selected.name().upper())
            self._refresh_color_button(button)

    def _validate_and_accept(self):
        included = sum(1 for include, _, _, _ in self.row_widgets.values() if include.isChecked())
        if included < 2:
            QMessageBox.warning(self, "Comparación" if self.language == "es" else "Comparison", "Selecciona al menos dos espectros." if self.language == "es" else "Select at least two spectra.")
            return
        self.accept()

    def comparison_config(self) -> dict:
        files = {}
        for path, (include, color_button, width, dash) in self.row_widgets.items():
            files[path] = {
                "included": include.isChecked(),
                "color": str(color_button.property("czspecColor") or "#1D6EEB"),
                "width": float(width.value()),
                "dash": str(dash.currentData() or "solid"),
            }
        sum_styles = []
        for color_button, width, dash in self.sum_style_widgets:
            sum_styles.append({
                "color": str(color_button.property("czspecColor") or "#7C3AED"),
                "width": float(width.value()),
                "dash": str(dash.currentData() or "solid"),
            })
        return {
            "content": str(self.content_combo.currentData() or "raw"),
            "layout": str(self.layout_combo.currentData() or "auto"),
            "share_x": self.share_x_checkbox.isChecked(),
            "share_y": self.share_y_checkbox.isChecked(),
            "show_sum": self.show_sum_checkbox.isChecked(),
            "sum_styles": sum_styles,
            "files": files,
        }


class DataFrameColumnExportDialog(QDialog):
    """Compact scientific column selector used by M1 exports."""

    def __init__(self, columns, language="es", parent=None):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle("Columnas para exportar" if language == "es" else "Export columns")
        self.resize(720, 460)
        root = QVBoxLayout(self)
        note = QLabel(
            "Selecciona las magnitudes que se exportarán. La selección se aplica a todos los formatos tabulares configurados."
            if language == "es" else
            "Select the quantities to export. The same selection is applied to all configured table formats."
        )
        note.setWordWrap(True)
        root.addWidget(note)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        body = QWidget(); grid = QGridLayout(body)
        grid.setHorizontalSpacing(8); grid.setVerticalSpacing(6)
        self.checks = {}
        preferred = {
            "Line", "Source", "ν[MHz]", "v_LSR[km/s]", "T_A [K]",
            "Δv [Km/s]", "σ_Δv [Km/s]", "IntInt [K*Km/s]",
            "σ_IntInt [K*Km/s]", "Ajuste", "SNR", "Confianza", "Tipo"
        }
        for i, col in enumerate(columns):
            cb = FilterCheckBox(_scientific_column_ui_label(col, language))
            cb.setToolTip(column_tooltip(col))
            cb.setChecked(str(col) in preferred)
            self.checks[str(col)] = cb
            grid.addWidget(cb, i // 3, i % 3)
        grid.setRowStretch((max(0, len(columns)-1) // 3) + 1, 1)
        scroll.setWidget(body); root.addWidget(scroll, stretch=1)

        actions = QHBoxLayout()
        allb = QPushButton("Todas" if language == "es" else "All")
        noneb = QPushButton("Ninguna" if language == "es" else "None")
        _apply_action_role(allb, "secondary"); _apply_action_role(noneb, "utility")
        allb.clicked.connect(lambda: [cb.setChecked(True) for cb in self.checks.values()])
        noneb.clicked.connect(lambda: [cb.setChecked(False) for cb in self.checks.values()])
        actions.addWidget(allb); actions.addWidget(noneb); actions.addStretch(); root.addLayout(actions)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept); buttons.rejected.connect(self.reject); root.addWidget(buttons)

    def _accept(self):
        if not self.selected_columns():
            QMessageBox.warning(
                self,
                "Exportar tablas" if self.language == "es" else "Export tables",
                "Selecciona al menos una columna." if self.language == "es" else "Select at least one column.",
            )
            return
        self.accept()

    def selected_columns(self):
        return [col for col, cb in self.checks.items() if cb.isChecked()]


class ColumnSelectorDialog(QDialog):
    """Grid/chip selector for table visibility in M2/M3.

    User-facing scientific columns are shown first.  Calculation/debug fields
    remain available behind an explicit advanced toggle rather than crowding the
    normal selector.
    """

    INTERNAL_COLUMNS = {
        "source_path", "detection_id", "__source_index__", "Grupo",
        "lower_state_energy", "upper_state_energy", "sijmu2", "sij",
        "heavy_atoms_count", "H_count", "complexity_score", "whitelisted",
        "blacklisted", "has_halogen", "vib_excited", "allowed_family",
        "identification_mode", "cand_score", "score_mode", "rescue_mode",
        "expanded_identification", "Semilla_ν[MHz]", "Q_key", "Q_species",
        "resolved_QNs", "LovasASTIntensity", "intintensity", "Lovas_NRAO",
        "orderedFreq", "measFreq", "qnCode", "labref_Lovas_NIST",
        "rel_int_HFS_Lovas", "unres_quantum_numbers", "lineid",
        "transition_in_space", "transition_in_G358", "obsref_Lovas_NIST",
        "source_Lovas_NIST", "telescope_Lovas_NIST", "transitionBandColor",
        "searchErrorMessage", "sqlquery", "requestnumber", "freq_diff_MHz",
        "complex_organic", "allowed_family_reason", "identification_mode",
    }

    def __init__(self, sections: list[tuple[str, QTableWidget]], language="es", parent=None):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle("Seleccionar columnas" if language == "es" else "Select columns")
        self.resize(850, 590)
        self.sections = sections
        self.checkbox_map = {}
        self.advanced_widgets = []
        root_layout = QVBoxLayout(self)

        info = QLabel(
            "Se muestran primero las columnas científicas útiles para el análisis. Los campos internos pueden habilitarse aparte."
            if language == "es" else
            "Scientific analysis columns are shown first. Internal calculation fields can be enabled separately."
        )
        info.setWordWrap(True)
        root_layout.addWidget(info)
        self.advanced_toggle = QCheckBox(
            "Mostrar columnas avanzadas / internas" if language == "es" else "Show advanced / internal columns"
        )
        root_layout.addWidget(self.advanced_toggle)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll_container = QWidget(); scroll_layout = QVBoxLayout(scroll_container)
        self.advanced_groups = []
        for section_title, table_widget in self.sections:
            group = QGroupBox(section_title)
            group_layout = QVBoxLayout(group)
            normal_holder = QWidget(); normal_grid = QGridLayout(normal_holder)
            normal_grid.setContentsMargins(0, 0, 0, 0); normal_grid.setHorizontalSpacing(10); normal_grid.setVerticalSpacing(5)
            advanced_group = QGroupBox("Columnas avanzadas / internas" if language == "es" else "Advanced / internal columns")
            advanced_grid = QGridLayout(advanced_group)
            advanced_grid.setHorizontalSpacing(10); advanced_grid.setVerticalSpacing(5)
            advanced_group.setVisible(False)
            self.advanced_groups.append(advanced_group)
            section_checkboxes = []
            col_count = table_widget.columnCount()
            normal_index = 0; advanced_index = 0
            if col_count == 0:
                normal_grid.addWidget(QLabel("No hay columnas disponibles." if language == "es" else "No columns available."), 0, 0)
            else:
                for col in range(col_count):
                    header_item = table_widget.horizontalHeaderItem(col)
                    col_name = _table_header_internal_name(header_item, f"Columna {col}")
                    if col_name == "selected":
                        continue
                    cb = FilterCheckBox(_scientific_column_ui_label(col_name, language))
                    cb.setToolTip(column_tooltip(col_name))
                    cb.setChecked(not table_widget.isColumnHidden(col))
                    section_checkboxes.append((cb, table_widget, col))
                    advanced = col_name in self.INTERNAL_COLUMNS or str(col_name).startswith(("Lovas", "labref", "obsref", "source_", "transition_"))
                    if advanced:
                        advanced_grid.addWidget(cb, advanced_index // 3, advanced_index % 3)
                        advanced_index += 1
                        self.advanced_widgets.append(cb)
                    else:
                        normal_grid.addWidget(cb, normal_index // 3, normal_index % 3)
                        normal_index += 1
            group_layout.addWidget(normal_holder)
            if advanced_index:
                group_layout.addWidget(advanced_group)
            else:
                advanced_group.setParent(None)
                self.advanced_groups.remove(advanced_group)
            self.checkbox_map[section_title] = section_checkboxes
            scroll_layout.addWidget(group)
        scroll_layout.addStretch(); scroll.setWidget(scroll_container); root_layout.addWidget(scroll, stretch=1)

        actions_row = QHBoxLayout()
        self.show_all_button = QPushButton("Mostrar todo" if language == "es" else "Show all")
        self.hide_all_button = QPushButton("Ocultar todo" if language == "es" else "Hide all")
        self.default_button = QPushButton("Restaurar por defecto" if language == "es" else "Restore defaults")
        _apply_action_role(self.show_all_button, "secondary")
        _apply_action_role(self.hide_all_button, "utility")
        _apply_action_role(self.default_button, "utility")
        actions_row.addWidget(self.show_all_button); actions_row.addWidget(self.hide_all_button); actions_row.addWidget(self.default_button); actions_row.addStretch()
        root_layout.addLayout(actions_row)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        root_layout.addWidget(button_box)
        self.show_all_button.clicked.connect(self.show_all)
        self.hide_all_button.clicked.connect(self.hide_all)
        self.default_button.clicked.connect(self.restore_defaults)
        self.advanced_toggle.toggled.connect(self._toggle_advanced)
        button_box.accepted.connect(self.apply_and_accept); button_box.rejected.connect(self.reject)

    def _toggle_advanced(self, visible: bool):
        for group in getattr(self, "advanced_groups", []):
            group.setVisible(bool(visible))
        # The hidden advanced section is removed from layout geometry entirely,
        # so normal mode has no blank holes between scientific columns.
        self.layout().activate()

    def show_all(self):
        for section_items in self.checkbox_map.values():
            for cb, _, _ in section_items:
                if cb.isVisible(): cb.setChecked(True)

    def hide_all(self):
        for section_items in self.checkbox_map.values():
            for cb, _, _ in section_items:
                if cb.isVisible(): cb.setChecked(False)

    def restore_defaults(self):
        for section_items in self.checkbox_map.values():
            for cb, table_widget, col in section_items:
                header_item = table_widget.horizontalHeaderItem(col)
                col_name = _table_header_internal_name(header_item, f"Columna {col}")
                cb.setChecked(_column_visible_by_default(table_widget, col_name))

    def apply_and_accept(self):
        for section_items in self.checkbox_map.values():
            for cb, table_widget, col in section_items:
                table_widget.setColumnHidden(col, not cb.isChecked())
        self.accept()


class IsotopicRatiosDialog(QDialog):
    def __init__(self, current_ratios: dict[str, float], language: str = "es", parent=None):
        super().__init__(parent)

        self.language = "en" if language == "en" else "es"
        en = self.language == "en"
        self.setWindowTitle("Isotopic ratios" if en else "Razones isotópicas")
        self.resize(460, 300)

        self._default_ratios = dict(DEFAULT_ISOTOPIC_ABUNDANCE_RATIOS)
        self._current_ratios = dict(current_ratios or self._default_ratios)

        layout = QVBoxLayout(self)

        info = QLabel(
            ("Edit values directly in the table. Built-in isotope keys stay fixed; custom rows can be added or removed. "
             "The physical-ratio/note column is descriptive and helps document why a value is being used."
             if en else
             "Edita los valores directamente en la tabla. Las claves isotópicas internas permanecen fijas; puedes agregar o eliminar filas personalizadas. "
             "La columna Razón física / nota sirve para documentar por qué se usa cada valor.")
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(
            (["Rare isotope / key", "Value", "Physical ratio / note"] if en else ["Isótopo raro / clave", "Valor", "Razón física / nota"])
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)

        self._populate_table()

        buttons_row = QHBoxLayout()

        self.btn_add = QPushButton("Add ratio" if en else "Agregar razón")
        self.btn_add.clicked.connect(self.add_custom_ratio)
        self.btn_remove = QPushButton("Remove selected" if en else "Eliminar seleccionada")
        self.btn_remove.clicked.connect(self.remove_selected_ratio)
        self.btn_reset = QPushButton("Restore defaults" if en else "Restaurar valores por defecto")
        self.btn_reset.clicked.connect(self.reset_defaults)

        self.btn_cancel = QPushButton("Cancel" if en else "Cancelar")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_ok = QPushButton("Save for session" if en else "Guardar en sesión")
        self.btn_ok.clicked.connect(self.accept)

        buttons_row.addWidget(self.btn_add)
        buttons_row.addWidget(self.btn_remove)
        buttons_row.addWidget(self.btn_reset)
        buttons_row.addStretch()
        buttons_row.addWidget(self.btn_cancel)
        buttons_row.addWidget(self.btn_ok)

        layout.addLayout(buttons_row)

    def _meaning_for_key(self, key: str) -> str:
        meanings = {
            "13C": "12C / 13C",
            "15N": "14N / 15N",
            "18O": "16O / 18O",
            "17O": "16O / 17O",
            "34S": "32S / 34S",
            "33S": "32S / 33S",
            "29SI": "28Si / 29Si",
            "30SI": "28Si / 30Si",
        }
        return meanings.get(key, key)

    def _populate_table(self):
        order = ["13C", "15N", "18O", "17O", "34S", "33S", "29SI", "30SI"]
        custom = [k for k in self._current_ratios if k not in order]
        keys = order + custom
        self.table.setRowCount(len(keys))

        for row, key in enumerate(keys):
            key_item = QTableWidgetItem(key)
            if key in order:
                key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            value = self._current_ratios.get(key, self._default_ratios.get(key, ""))
            value_item = QTableWidgetItem(str(value))
            meaning_item = QTableWidgetItem(self._meaning_for_key(key) if key in order else "")
            # Notes are intentionally editable so the session documents the
            # physical convention behind both built-in and custom ratios.
            self.table.setItem(row, 0, key_item)
            self.table.setItem(row, 1, value_item)
            self.table.setItem(row, 2, meaning_item)

        self.table.resizeColumnsToContents()

    def add_custom_ratio(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        key = QTableWidgetItem("new_isotope" if self.language == "en" else "nuevo_isotopo")
        value = QTableWidgetItem("1")
        note = QTableWidgetItem("Describe the physical abundance ratio" if self.language == "en" else "Describe aquí la razón física")
        self.table.setItem(row, 0, key); self.table.setItem(row, 1, value); self.table.setItem(row, 2, note)
        self.table.setCurrentCell(row, 0); self.table.editItem(key)

    def remove_selected_ratio(self):
        row = self.table.currentRow()
        if row < 0:
            return
        key_item = self.table.item(row, 0)
        key = key_item.text().strip().upper() if key_item else ""
        protected = {"13C", "15N", "18O", "17O", "34S", "33S", "29SI", "30SI"}
        if key in protected:
            QMessageBox.information(
                self,
                "Isotopic ratios" if self.language == "en" else "Razones isotópicas",
                "Built-in isotope keys cannot be removed; edit their value instead." if self.language == "en" else
                "Las claves isotópicas internas no se eliminan; puedes editar su valor."
            )
            return
        self.table.removeRow(row)

    def reset_defaults(self):
        self._current_ratios = dict(self._default_ratios)
        self._populate_table()

    def get_ratios(self) -> dict[str, float]:
        ratios = {}

        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)

            if key_item is None or value_item is None:
                continue

            key = key_item.text().strip()
            raw_value = value_item.text().strip().replace(",", ".")

            try:
                value = float(raw_value)
            except ValueError:
                value = self._default_ratios.get(key, np.nan)

            if not np.isfinite(value) or value <= 0:
                value = self._default_ratios.get(key, np.nan)
            if not np.isfinite(value) or value <= 0:
                # Invalid custom rows are ignored rather than injecting NaN into
                # the scientific session configuration.
                continue

            ratios[key] = float(value)

        return ratios


class LTEComponentWorkbench(QDialog):
    """Mesa no modal para revisar y editar componentes sin cerrar M4."""

    componentsApplied = Signal(object)

    PALETTE = (
        "#E67E22", "#246BDE", "#16A085", "#D64550", "#8E5CE6",
        "#2D3436", "#DB2777", "#65A30D", "#0891B2", "#7C3AED",
    )

    def __init__(self, components: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mesa de componentes LTE — CZSpec")
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.resize(1180, 520)
        self._components = deepcopy(components)
        self._row_widgets = []

        root = QVBoxLayout(self)
        intro = QLabel(
            "Esta ventana puede permanecer abierta junto a M4. Activa o desactiva "
            "especies y refina sus valores iniciales; «Aplicar a M4» no modifica "
            "las tablas originales de MOD/MTH."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            [
                "Usar", "Componente / especie", "Método", "Tₑₓ [K]",
                "N total [cm⁻²]", "FWHM [km s⁻¹]", "Δv [km s⁻¹]",
                "Tamaño [″]", "Color", "Procedencia M3",
            ]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.Stretch)
        root.addWidget(self.table, stretch=1)

        footer = QHBoxLayout()
        reset = QPushButton("Restaurar valores iniciales")
        apply_button = QPushButton("Aplicar a M4")
        close_button = QPushButton("Cerrar")
        reset.clicked.connect(self._restore_initial)
        apply_button.clicked.connect(self._apply)
        close_button.clicked.connect(self.hide)
        footer.addWidget(reset)
        footer.addStretch()
        footer.addWidget(apply_button)
        footer.addWidget(close_button)
        root.addLayout(footer)
        self.set_components(components)

    def set_components(self, components: list[dict]):
        self._components = deepcopy(components)
        self.table.setRowCount(len(self._components))
        self._row_widgets = []
        for row, component in enumerate(self._components):
            enabled = QCheckBox()
            enabled.setChecked(bool(component.get("enabled", True)))
            holder = QWidget()
            holder_layout = QHBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            holder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            holder_layout.addWidget(enabled)
            self.table.setCellWidget(row, 0, holder)

            label_item = QTableWidgetItem(str(component.get("label", "Componente LTE")))
            method_item = QTableWidgetItem(str(component.get("solution", {}).get("method", "")))
            tex_item = QTableWidgetItem(
                f"{float(component.get('solution', {}).get('tex_k', 0.0)):g}"
            )
            for column, item in ((1, label_item), (2, method_item), (3, tex_item)):
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(row, column, item)

            solution = component.get("solution", {})
            n_input = QLineEdit(f"{float(solution.get('column_density_cm2', 0.0)):.8g}")
            width = QDoubleSpinBox()
            width.setRange(0.001, 500.0)
            width.setDecimals(4)
            width.setValue(max(float(solution.get("linewidth_kms", 0.0)), 0.001))
            velocity = QDoubleSpinBox()
            velocity.setRange(-1000.0, 1000.0)
            velocity.setDecimals(4)
            velocity.setValue(float(solution.get("velocity_offset_kms", 0.0) or 0.0))
            source_size = QDoubleSpinBox()
            source_size.setRange(0.0, 100000.0)
            source_size.setDecimals(2)
            source_size.setSpecialValueText("Extendida")
            source_size.setValue(float(component.get("source_size_arcsec") or 0.0))
            self.table.setCellWidget(row, 4, n_input)
            self.table.setCellWidget(row, 5, width)
            self.table.setCellWidget(row, 6, velocity)
            self.table.setCellWidget(row, 7, source_size)

            color = str(component.get("color") or self.PALETTE[row % len(self.PALETTE)]).upper()
            color_button = QPushButton(color)
            color_button.setProperty("czspecColor", color)
            color_button.clicked.connect(
                lambda _checked=False, button=color_button: self._choose_color(button)
            )
            self._refresh_color_button(color_button)
            self.table.setCellWidget(row, 8, color_button)

            count = int(solution.get("n_input_solutions", 1) or 1)
            provenance = (
                f"{count} solución(es); "
                f"{len(component.get('transitions', []))} transición(es) seleccionadas"
            )
            provenance_item = QTableWidgetItem(provenance)
            provenance_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            provenance_item.setToolTip(
                ", ".join(solution.get("member_solution_keys", [])) or
                str(component.get("solution_key", ""))
            )
            self.table.setItem(row, 9, provenance_item)
            self._row_widgets.append(
                (enabled, n_input, width, velocity, source_size, color_button)
            )

    @staticmethod
    def _refresh_color_button(button: QPushButton):
        value = str(button.property("czspecColor") or "#E67E22").upper()
        color = QColor(value)
        light = 0.2126 * color.redF() + 0.7152 * color.greenF() + 0.0722 * color.blueF()
        button.setText(value)
        button.setStyleSheet(
            "QPushButton {"
            f"background:{value};color:{'#111827' if light > 0.58 else '#FFFFFF'};"
            "border:1px solid #A8B4C6;font-weight:700;}"
        )

    def _choose_color(self, button: QPushButton):
        selected = QColorDialog.getColor(
            QColor(str(button.property("czspecColor") or "#E67E22")),
            self,
            "Color de la componente LTE",
        )
        if selected.isValid():
            button.setProperty("czspecColor", selected.name().upper())
            self._refresh_color_button(button)

    def _restore_initial(self):
        for component in self._components:
            initial = component.get("initial_solution")
            if isinstance(initial, dict):
                component["solution"] = deepcopy(initial)
            component["enabled"] = True
        self.set_components(self._components)

    def _apply(self):
        updated = deepcopy(self._components)
        try:
            for row, widgets in enumerate(self._row_widgets):
                enabled, n_input, width, velocity, source_size, color_button = widgets
                density = float(n_input.text().strip().replace(",", "."))
                if not np.isfinite(density) or density <= 0:
                    raise ValueError(f"La densidad de la fila {row + 1} no es válida.")
                solution = updated[row].setdefault("solution", {})
                solution["column_density_cm2"] = density
                solution["linewidth_kms"] = float(width.value())
                solution["velocity_offset_kms"] = float(velocity.value())
                updated[row]["source_size_arcsec"] = (
                    float(source_size.value()) if source_size.value() > 0 else None
                )
                updated[row]["enabled"] = enabled.isChecked()
                updated[row]["color"] = str(
                    color_button.property("czspecColor") or "#E67E22"
                ).upper()
        except ValueError as exc:
            QMessageBox.warning(self, "Componentes LTE", str(exc))
            return
        self._components = deepcopy(updated)
        self.componentsApplied.emit(updated)


class LTEDiagnosticsDialog(QDialog):
    """Diagnóstico LTE no modal que no reduce el área principal de la gráfica."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Diagnóstico por transición — CZSpec")
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.resize(1220, 620)

        layout = QVBoxLayout(self)
        self.summary = QLabel(
            "Genera un modelo LTE para consultar las transiciones utilizadas."
        )
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, stretch=1)

        footer = QHBoxLayout()
        footer.addStretch()
        close_button = QPushButton("Cerrar")
        close_button.clicked.connect(self.hide)
        footer.addWidget(close_button)
        layout.addLayout(footer)


class PlotInteractionBridge(QObject):
    """Puente mínimo entre el visor Plotly y M1.

    JavaScript nunca modifica estado científico directamente. Sólo envía la
    selección/clic a Qt y MainWindow decide qué operación reproducible aplicar.
    """

    selectionReceived = Signal(float, float)
    detectionRemoveRequested = Signal(int, float)
    detectionRemoveByIdRequested = Signal(str, float)
    detectionAddRequested = Signal(float, float)

    @Slot(float, float)
    def selectedRange(self, a: float, b: float):
        self.selectionReceived.emit(float(a), float(b))

    @Slot(int, float)
    def removeDetection(self, line_number: int, frequency_mhz: float):
        # Backward-compatible visual-index route. New M1 plots use the immutable
        # detection_id route below.
        self.detectionRemoveRequested.emit(int(line_number), float(frequency_mhz))

    @Slot(str, float)
    def removeDetectionById(self, detection_id: str, frequency_mhz: float):
        self.detectionRemoveByIdRequested.emit(str(detection_id), float(frequency_mhz))

    @Slot(float, float)
    def addDetection(self, frequency_mhz: float, intensity: float):
        self.detectionAddRequested.emit(float(frequency_mhz), float(intensity))



class SpeciesSearchFilterDialog(QDialog):
    """Editor transparente de los priors/filtros científicos del buscador M2."""

    PROFILE_PRESETS = {
        "star_forming": {
            "eu_max_k": 120.0, "emergency_eu_max_k": 180.0,
            "strict_family_mode": True, "forbid_halogens": True,
            "disallow_vib_excited": True, "allow_complex_organics": False,
            "allow_emergency_outside_family": False, "heavy_atoms_strict_max": 4,
            "soft_heavy_max": 5, "rescue_widen_factor": 1.8,
            "emergency_widen_factor": 4.0, "weight_frequency": 0.75,
            "weight_eu": 0.15, "weight_loga": 0.10, "complexity_weight": 1.0,
        },
        "balanced": {
            "eu_max_k": 250.0, "emergency_eu_max_k": 450.0,
            "strict_family_mode": True, "forbid_halogens": True,
            "disallow_vib_excited": False, "allow_complex_organics": True,
            "allow_emergency_outside_family": False, "heavy_atoms_strict_max": 6,
            "soft_heavy_max": 8, "rescue_widen_factor": 2.2,
            "emergency_widen_factor": 5.0, "weight_frequency": 0.78,
            "weight_eu": 0.12, "weight_loga": 0.10, "complexity_weight": 0.55,
        },
        "open": {
            "eu_max_k": 800.0, "emergency_eu_max_k": 1500.0,
            "strict_family_mode": False, "forbid_halogens": False,
            "disallow_vib_excited": False, "allow_complex_organics": True,
            "allow_emergency_outside_family": True, "heavy_atoms_strict_max": 12,
            "soft_heavy_max": 18, "rescue_widen_factor": 3.0,
            "emergency_widen_factor": 8.0, "weight_frequency": 0.86,
            "weight_eu": 0.07, "weight_loga": 0.07, "complexity_weight": 0.15,
        },
    }

    PROFILE_NOTES_ES = {
        "star_forming": "Perfil recomendado para regiones de formación estelar: prior químico fuerte, sin COMs por defecto y emergencia conservadora.",
        "balanced": "Amplía la química plausible para gas cálido/hot cores: permite COMs y estados vibracionales, pero conserva filtros de familia y halógenos.",
        "open": "Exploración de catálogo: prior químico mínimo, ventanas más amplias y mayor complejidad permitida. Úsalo cuando quieras inspeccionar candidatos poco comunes.",
    }
    PROFILE_NOTES_EN = {
        "star_forming": "Recommended for star-forming regions: strong chemical prior, COMs disabled by default, conservative emergency search.",
        "balanced": "Broader warm-gas/hot-core chemistry: COMs and vibrational states are allowed while family/halogen safeguards remain.",
        "open": "Catalog exploration: minimal chemical prior, wider windows and greater complexity. Use it to inspect unusual candidates.",
    }

    def __init__(self, policy: dict | None = None, language: str = "es", parent=None):
        super().__init__(parent)
        self.language = language
        self.policy = dict(policy or {})
        self.setWindowTitle(
            "Filtros de identificación molecular" if language == "es"
            else "Molecular-identification filters"
        )
        self.resize(620, 560)
        self.setMinimumSize(520, 420)
        outer = QVBoxLayout(self)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget(scroll)
        root = QVBoxLayout(body)
        scroll.setWidget(body)
        outer.addWidget(scroll, stretch=1)

        intro = QLabel(
            "Estos controles determinan qué candidatos de Splatalogue son plausibles y cómo se ordenan. "
            "El perfil conservador prefiere dejar una línea sin identificar antes que forzar una molécula exótica."
            if language == "es" else
            "These controls determine which Splatalogue candidates are plausible and how they are ranked. "
            "The conservative profile prefers an unidentified line over forcing an exotic molecule."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        profile_box = QGroupBox("Perfil científico" if language == "es" else "Scientific profile")
        profile_form = QFormLayout(profile_box)
        self.profile_combo = QComboBox()
        self.profile_combo.addItem(
            "Región de formación estelar · conservador" if language == "es" else "Star-forming region · conservative",
            "star_forming",
        )
        self.profile_combo.addItem(
            "Balanceado · química más amplia" if language == "es" else "Balanced · broader chemistry",
            "balanced",
        )
        self.profile_combo.addItem(
            "Catálogo abierto · mínimo prior químico" if language == "es" else "Open catalog · minimal chemical prior",
            "open",
        )
        idx = self.profile_combo.findData(str(self.policy.get("profile", "star_forming")))
        self.profile_combo.setCurrentIndex(max(0, idx))
        profile_form.addRow("Perfil:" if language == "es" else "Profile:", self.profile_combo)
        self.profile_note = QLabel()
        self.profile_note.setWordWrap(True)
        self.profile_note.setStyleSheet("color:#52627A;font-size:11px;padding-top:3px;")
        profile_form.addRow("Bitácora:" if language == "es" else "Profile notes:", self.profile_note)
        root.addWidget(profile_box)

        limits_box = QGroupBox("Límites de selección" if language == "es" else "Selection limits")
        limits = QFormLayout(limits_box)
        self.eu_max = QDoubleSpinBox(); self.eu_max.setRange(1.0, 3000.0); self.eu_max.setDecimals(1); self.eu_max.setSuffix(" K")
        self.eu_max.setValue(float(self.policy.get("eu_max_k", 120.0)))
        self.emergency_eu = QDoubleSpinBox(); self.emergency_eu.setRange(1.0, 5000.0); self.emergency_eu.setDecimals(1); self.emergency_eu.setSuffix(" K")
        self.emergency_eu.setValue(float(self.policy.get("emergency_eu_max_k", 180.0)))
        self.heavy_strict = QSpinBox(); self.heavy_strict.setRange(1, 20); self.heavy_strict.setValue(int(self.policy.get("heavy_atoms_strict_max", 4)))
        self.heavy_soft = QSpinBox(); self.heavy_soft.setRange(1, 30); self.heavy_soft.setValue(int(self.policy.get("soft_heavy_max", 5)))
        self.rescue_factor = QDoubleSpinBox(); self.rescue_factor.setRange(1.0, 20.0); self.rescue_factor.setDecimals(2); self.rescue_factor.setValue(float(self.policy.get("rescue_widen_factor", 1.8)))
        self.emergency_factor = QDoubleSpinBox(); self.emergency_factor.setRange(1.0, 50.0); self.emergency_factor.setDecimals(2); self.emergency_factor.setValue(float(self.policy.get("emergency_widen_factor", 4.0)))
        self.query_workers = QSpinBox(); self.query_workers.setRange(1, 6); self.query_workers.setValue(int(self.policy.get("query_workers", 3)))
        limits.addRow("Eᵤ/k máximo:" if language == "es" else "Maximum Eᵤ/k:", self.eu_max)
        limits.addRow("Eᵤ/k de emergencia:" if language == "es" else "Emergency Eᵤ/k:", self.emergency_eu)
        limits.addRow("Átomos pesados · estricto:" if language == "es" else "Heavy atoms · strict:", self.heavy_strict)
        limits.addRow("Átomos pesados · flexible:" if language == "es" else "Heavy atoms · soft:", self.heavy_soft)
        limits.addRow("Ampliación de rescate:" if language == "es" else "Rescue window factor:", self.rescue_factor)
        limits.addRow("Ampliación de emergencia:" if language == "es" else "Emergency window factor:", self.emergency_factor)
        limits.addRow("Consultas simultáneas:" if language == "es" else "Concurrent queries:", self.query_workers)
        root.addWidget(limits_box)

        rules_box = QGroupBox("Reglas químicas" if language == "es" else "Chemical rules")
        rules = QVBoxLayout(rules_box)
        self.strict_family = QCheckBox("Priorizar familias plausibles para formación estelar" if language == "es" else "Prioritize plausible star-forming-region families")
        self.forbid_halogens = QCheckBox("Descartar especies con halógenos" if language == "es" else "Reject halogen-bearing species")
        self.disallow_vib = QCheckBox("Descartar estados vibracionalmente excitados por defecto" if language == "es" else "Reject vibrationally excited states by default")
        self.allow_com = QCheckBox("Permitir moléculas orgánicas complejas (COMs)" if language == "es" else "Allow complex organic molecules (COMs)")
        self.allow_emergency = QCheckBox("Permitir que emergencia salga de las familias plausibles" if language == "es" else "Allow emergency mode outside plausible families")
        self.strict_family.setChecked(bool(self.policy.get("strict_family_mode", True)))
        self.forbid_halogens.setChecked(bool(self.policy.get("forbid_halogens", True)))
        self.disallow_vib.setChecked(bool(self.policy.get("disallow_vib_excited", True)))
        self.allow_com.setChecked(bool(self.policy.get("allow_complex_organics", False)))
        self.allow_emergency.setChecked(bool(self.policy.get("allow_emergency_outside_family", False)))
        for cb in (self.strict_family, self.forbid_halogens, self.disallow_vib, self.allow_com, self.allow_emergency):
            rules.addWidget(cb)
        warning = QLabel(
            "Activar COMs o emergencia abierta es útil para hot cores o búsquedas exploratorias, pero puede aumentar falsos candidatos."
            if language == "es" else
            "Allowing COMs or open emergency mode is useful for hot cores/exploratory work, but can increase false candidates."
        )
        warning.setWordWrap(True); warning.setStyleSheet("color:#8A5A00;font-size:11px;")
        rules.addWidget(warning)
        root.addWidget(rules_box)

        scoring_box = QGroupBox("Ponderación del ranking" if language == "es" else "Ranking weights")
        scoring = QFormLayout(scoring_box)
        self.weight_frequency = QDoubleSpinBox(); self.weight_frequency.setRange(0.0, 5.0); self.weight_frequency.setDecimals(3); self.weight_frequency.setValue(float(self.policy.get("weight_frequency", 0.75)))
        self.weight_eu = QDoubleSpinBox(); self.weight_eu.setRange(0.0, 5.0); self.weight_eu.setDecimals(3); self.weight_eu.setValue(float(self.policy.get("weight_eu", 0.15)))
        self.weight_loga = QDoubleSpinBox(); self.weight_loga.setRange(0.0, 5.0); self.weight_loga.setDecimals(3); self.weight_loga.setValue(float(self.policy.get("weight_loga", 0.10)))
        self.complexity_weight = QDoubleSpinBox(); self.complexity_weight.setRange(0.0, 10.0); self.complexity_weight.setDecimals(3); self.complexity_weight.setValue(float(self.policy.get("complexity_weight", 1.0)))
        scoring.addRow("Frecuencia:" if language == "es" else "Frequency:", self.weight_frequency)
        scoring.addRow("Energía Eᵤ:" if language == "es" else "Eᵤ energy:", self.weight_eu)
        scoring.addRow("Einstein A:" if language == "es" else "Einstein A:", self.weight_loga)
        scoring.addRow("Complejidad química:" if language == "es" else "Chemical complexity:", self.complexity_weight)
        root.addWidget(scoring_box)

        footer = QHBoxLayout()
        reset = QPushButton("Restaurar valores recomendados" if language == "es" else "Restore recommended defaults")
        reset.clicked.connect(self._restore_defaults)
        footer.addWidget(reset); footer.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Aplicar" if language == "es" else "Apply")
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        footer.addWidget(buttons)
        root.addLayout(footer)
        self.profile_combo.currentIndexChanged.connect(self._profile_changed)
        self._update_profile_note()
        screen = self.screen() or QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.resize(min(620, max(520, geo.width() - 100)), min(640, max(420, geo.height() - 100)))

    def _update_profile_note(self):
        key = str(self.profile_combo.currentData() or "star_forming")
        notes = self.PROFILE_NOTES_ES if self.language == "es" else self.PROFILE_NOTES_EN
        self.profile_note.setText(notes.get(key, ""))

    def _profile_changed(self, *_):
        key = str(self.profile_combo.currentData() or "star_forming")
        preset = dict(self.PROFILE_PRESETS.get(key) or {})
        if not preset:
            self._update_profile_note(); return
        self.eu_max.setValue(float(preset["eu_max_k"]))
        self.emergency_eu.setValue(float(preset["emergency_eu_max_k"]))
        self.heavy_strict.setValue(int(preset["heavy_atoms_strict_max"]))
        self.heavy_soft.setValue(int(preset["soft_heavy_max"]))
        self.rescue_factor.setValue(float(preset["rescue_widen_factor"]))
        self.emergency_factor.setValue(float(preset["emergency_widen_factor"]))
        self.strict_family.setChecked(bool(preset["strict_family_mode"]))
        self.forbid_halogens.setChecked(bool(preset["forbid_halogens"]))
        self.disallow_vib.setChecked(bool(preset["disallow_vib_excited"]))
        self.allow_com.setChecked(bool(preset["allow_complex_organics"]))
        self.allow_emergency.setChecked(bool(preset["allow_emergency_outside_family"]))
        self.weight_frequency.setValue(float(preset["weight_frequency"]))
        self.weight_eu.setValue(float(preset["weight_eu"]))
        self.weight_loga.setValue(float(preset["weight_loga"]))
        self.complexity_weight.setValue(float(preset["complexity_weight"]))
        self._update_profile_note()

    def _restore_defaults(self):
        self.profile_combo.setCurrentIndex(max(0, self.profile_combo.findData("star_forming")))
        self.eu_max.setValue(120.0); self.emergency_eu.setValue(180.0)
        self.heavy_strict.setValue(4); self.heavy_soft.setValue(5)
        self.rescue_factor.setValue(1.8); self.emergency_factor.setValue(4.0); self.query_workers.setValue(3)
        self.strict_family.setChecked(True); self.forbid_halogens.setChecked(True); self.disallow_vib.setChecked(True)
        self.allow_com.setChecked(False); self.allow_emergency.setChecked(False)
        self.weight_frequency.setValue(0.75); self.weight_eu.setValue(0.15); self.weight_loga.setValue(0.10); self.complexity_weight.setValue(1.0)

    def configuration(self) -> dict:
        return {
            "profile": str(self.profile_combo.currentData() or "star_forming"),
            "eu_max_k": float(self.eu_max.value()),
            "emergency_eu_max_k": max(float(self.eu_max.value()), float(self.emergency_eu.value())),
            "strict_family_mode": bool(self.strict_family.isChecked()),
            "forbid_halogens": bool(self.forbid_halogens.isChecked()),
            "disallow_vib_excited": bool(self.disallow_vib.isChecked()),
            "allow_complex_organics": bool(self.allow_com.isChecked()),
            "allow_emergency_outside_family": bool(self.allow_emergency.isChecked()),
            "heavy_atoms_strict_max": int(self.heavy_strict.value()),
            "soft_heavy_max": max(int(self.heavy_strict.value()), int(self.heavy_soft.value())),
            "rescue_widen_factor": float(self.rescue_factor.value()),
            "emergency_widen_factor": max(float(self.rescue_factor.value()), float(self.emergency_factor.value())),
            "query_workers": int(self.query_workers.value()),
            "weight_frequency": float(self.weight_frequency.value()),
            "weight_eu": float(self.weight_eu.value()),
            "weight_loga": float(self.weight_loga.value()),
            "complexity_weight": float(self.complexity_weight.value()),
        }


class SpeciesPlotStyleDialog(PlotStyleDialog):
    """M2 plot-style editor: M1 controls plus the line-specific VLSR trace."""

    def __init__(self, current_styles: dict, axis_config: dict | None = None, vlsr_style: dict | None = None,
                 language: str = "es", native_intensity_unit: str | None = None, parent=None):
        self._m2_vlsr_style = {"color": "#D97706", "width": 1.5, "dash": "dot"}
        if isinstance(vlsr_style, dict):
            self._m2_vlsr_style.update(vlsr_style)
        super().__init__(current_styles, axis_config=axis_config, language=language,
                         native_intensity_unit=native_intensity_unit, parent=parent)
        self.setWindowTitle("Estilos y ejes del espectro final — M2" if language == "es" else "Final-spectrum styles and axes — M2")

        box = QGroupBox("Referencia VLSR por línea" if language == "es" else "Per-line VLSR reference")
        row = QHBoxLayout(box)
        self.vlsr_color_button = QPushButton()
        self.vlsr_color_button.setMinimumWidth(122)
        self.vlsr_color_button.clicked.connect(self._choose_vlsr_color)
        self.vlsr_width_input = QDoubleSpinBox(); self.vlsr_width_input.setRange(0.5, 8.0); self.vlsr_width_input.setDecimals(1); self.vlsr_width_input.setSingleStep(0.2); self.vlsr_width_input.setSuffix(" px")
        self.vlsr_width_input.setValue(float(self._m2_vlsr_style.get("width", 1.5)))
        self.vlsr_dash_combo = QComboBox()
        for label, value in LINE_STYLE_OPTIONS:
            self.vlsr_dash_combo.addItem(label, value)
        self.vlsr_dash_combo.setCurrentIndex(max(0, self.vlsr_dash_combo.findData(str(self._m2_vlsr_style.get("dash", "dot")))))
        row.addWidget(self.vlsr_color_button)
        row.addWidget(self.vlsr_width_input)
        row.addWidget(self.vlsr_dash_combo, stretch=1)
        self.content_layout.addWidget(box)
        self._refresh_vlsr_color_button()

    def _refresh_vlsr_color_button(self):
        value = str(self._m2_vlsr_style.get("color", "#D97706")).upper()
        color = QColor(value)
        lum = 0.2126*color.redF()+0.7152*color.greenF()+0.0722*color.blueF()
        fg = "#111827" if lum > 0.58 else "#FFFFFF"
        self.vlsr_color_button.setText(f"●  {value}")
        self.vlsr_color_button.setStyleSheet(
            "QPushButton {"+f"background-color:{value};color:{fg};border:1px solid #A8B4C6;font-weight:700;"+"}"
        )

    def _choose_vlsr_color(self):
        selected = QColorDialog.getColor(QColor(str(self._m2_vlsr_style.get("color", "#D97706"))), self,
                                         "Seleccionar color VLSR" if self.language == "es" else "Select VLSR color")
        if selected.isValid():
            self._m2_vlsr_style["color"] = selected.name().upper()
            self._refresh_vlsr_color_button()

    def _restore_defaults(self):
        super()._restore_defaults()
        self._m2_vlsr_style = {"color": "#D97706", "width": 1.5, "dash": "dot"}
        if hasattr(self, "vlsr_width_input"):
            self.vlsr_width_input.setValue(1.5)
            self.vlsr_dash_combo.setCurrentIndex(max(0, self.vlsr_dash_combo.findData("dot")))
            self._refresh_vlsr_color_button()

    def _accept_styles(self):
        self._m2_vlsr_style["width"] = float(self.vlsr_width_input.value())
        self._m2_vlsr_style["dash"] = str(self.vlsr_dash_combo.currentData() or "dot")
        super()._accept_styles()

    def vlsr_style(self) -> dict:
        return deepcopy(self._m2_vlsr_style)


class SpeciesSpectrumDialog(QDialog):
    """Fast, reusable M2 viewer backed by the same local Plotly runtime as M1."""

    def __init__(self, source_names, figure_provider, style_callback=None, language: str = "es",
                 label_mode: str = "name", output_directory: Path | None = None,
                 module_label: str = "M2", window_title: str | None = None,
                 filename_prefix: str = "", parent=None):
        super().__init__(parent)
        self.language = language
        self.figure_provider = figure_provider
        self.style_callback = style_callback
        self.output_directory = Path(output_directory or SPECIES_IMAGES_DIR)
        self.module_label = str(module_label or "M2")
        self.filename_prefix = re.sub(r"[^A-Za-z0-9._-]+", "_", str(filename_prefix or "")).strip("._-")
        self._page_ready = False
        self._pending_json = None
        self.setWindowTitle(window_title or ((f"Espectro final — {self.module_label}") if language == "es" else (f"Final spectrum — {self.module_label}")))
        self.resize(1280, 720)
        root = QVBoxLayout(self)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Fuente:" if language == "es" else "Source:"))
        self.source_combo = QComboBox(); self.source_combo.addItems(list(source_names or [])); controls.addWidget(self.source_combo, stretch=1)

        controls.addWidget(QLabel("Identificadores:" if language == "es" else "Identifiers:"))
        self.label_combo = QComboBox()
        self.label_combo.addItem("L# + especie / transición" if language == "es" else "L# + species / transition", "name")
        self.label_combo.addItem("L# + nombre químico" if language == "es" else "L# + chemical name", "chemical_name")
        self.label_combo.addItem("Ocultar identificadores" if language == "es" else "Hide identifiers", "none")
        idx = self.label_combo.findData(label_mode); self.label_combo.setCurrentIndex(idx if idx >= 0 else 0)
        controls.addWidget(self.label_combo)

        controls.addWidget(QLabel("Vista:" if language == "es" else "View:"))
        self.legend_combo = QComboBox()
        self.legend_combo.addItem("Sin leyenda" if language == "es" else "Without legend", "no_legend")
        self.legend_combo.addItem("Con leyenda" if language == "es" else "With legend", "with_legend")
        self.legend_combo.addItem("Con leyenda extendida" if language == "es" else "With legend extended", "with_legend_extended")
        self.legend_combo.setCurrentIndex(max(0, self.legend_combo.findData("with_legend")))
        controls.addWidget(self.legend_combo)

        self.style_button = QPushButton("Estilo de gráfica…" if language == "es" else "Plot style…")
        self.style_button.setToolTip("Editar trazas, referencia VLSR y ejes" if language == "es" else "Edit traces, VLSR reference and axes")
        controls.addWidget(self.style_button)
        self.image_name_input = QLineEdit()
        self.image_name_input.setPlaceholderText("Nombre de imagen (opcional)" if language == "es" else "Image name (optional)")
        self.image_name_input.setToolTip("Nombre opcional para el archivo guardado." if language == "es" else "Optional filename for the saved image.")
        self.image_name_input.setMaximumWidth(205)
        controls.addWidget(self.image_name_input)
        self.save_button = QPushButton("Guardar imagen..." if language == "es" else "Save image...")
        _apply_action_role(self.style_button, "secondary")
        _apply_action_role(self.save_button, "export")
        controls.addWidget(self.save_button)
        root.addLayout(controls)

        from PySide6.QtWebEngineCore import QWebEngineSettings
        from PySide6.QtWebEngineWidgets import QWebEngineView
        self.plot_view = QWebEngineView(self)
        self.plot_view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        self.plot_view.loadFinished.connect(self._page_loaded)
        root.addWidget(self.plot_view, stretch=1)

        close = QPushButton("Cerrar" if language == "es" else "Close")
        close.clicked.connect(self.accept)
        row = QHBoxLayout(); row.addStretch(); row.addWidget(close); root.addLayout(row)

        self.source_combo.currentIndexChanged.connect(self._render)
        self.legend_combo.currentIndexChanged.connect(self._render)
        self.label_combo.currentIndexChanged.connect(self._render)
        self.style_button.clicked.connect(self._open_style)
        self.save_button.clicked.connect(self._save)
        self.plot_view.load(QUrl.fromLocalFile(str(prepare_plotly_view_file())))
        QTimer.singleShot(0, self._fit_to_available_screen)

    def _fit_to_available_screen(self):
        screen = self.screen()
        if screen is None:
            return
        available = screen.availableGeometry()
        width = min(1320, max(900, int(available.width() * 0.86)))
        height = min(800, max(600, int(available.height() * 0.78)))
        self.resize(width, height)
        self.move(available.x() + max(0, (available.width() - width) // 2),
                  available.y() + max(0, (available.height() - height) // 2))

    def current_label_mode(self) -> str:
        return str(self.label_combo.currentData() or "name")

    def _page_loaded(self, ok: bool):
        self._page_ready = bool(ok)
        if self._page_ready:
            self._render()

    def _current_json(self):
        key = self.source_combo.currentText()
        if not key:
            return None
        try:
            raw = self.figure_provider(key, self.current_label_mode())
        except Exception as exc:
            QMessageBox.critical(self, "M2", str(exc)); return None
        if not raw:
            return None
        try:
            figure = json.loads(raw) if isinstance(raw, str) else deepcopy(raw)
        except Exception:
            return raw
        figure = _localize_plot_trace_names(figure, self.language)
        layout = figure.setdefault("layout", {})
        view_mode = str(self.legend_combo.currentData() or "with_legend")
        show = view_mode != "no_legend"
        extended = view_mode == "with_legend_extended"
        layout["showlegend"] = show
        margin = dict(layout.get("margin") or {})
        category_roles = {"legend_fit_components", "legend_final_profiles", "legend_m2_vlsr"}
        individual_roles = {"fit_component", "fit", "fit_sum", "m2_vlsr_reference"}
        for tr in figure.get("data", []) or []:
            meta = tr.get("meta") if isinstance(tr.get("meta"), dict) else {}
            role = str(meta.get("czspec_role") or "")
            if role in category_roles:
                tr["showlegend"] = bool(show and not extended)
            elif role in individual_roles:
                tr["showlegend"] = bool(show and extended)
            elif str(tr.get("name") or "").startswith("__czspec_"):
                tr["showlegend"] = False
        if show:
            legend = dict(layout.get("legend") or {})
            if extended:
                legend.update({
                    "x": 1.09, "xanchor": "left", "y": 1.0, "yanchor": "top",
                    "orientation": "v", "bgcolor": "rgba(255,255,255,0.96)",
                    "bordercolor": "rgba(120,130,150,0.28)", "borderwidth": 1,
                    "tracegroupgap": 2, "font": {"size": 10},
                    "groupclick": "toggleitem",
                })
                margin["r"] = max(int(margin.get("r", 45) or 45), 440)
                margin["b"] = max(70, min(int(margin.get("b", 70) or 70), 110))
            else:
                legend.update({
                    "x": 0.0, "xanchor": "left", "y": -0.16, "yanchor": "top",
                    "orientation": "h", "bgcolor": "rgba(255,255,255,0.94)",
                    "bordercolor": "rgba(120,130,150,0.24)", "borderwidth": 1,
                    "tracegroupgap": 3, "font": {"size": 10},
                    "groupclick": "togglegroup",
                })
                margin["b"] = max(int(margin.get("b", 60) or 60), 112)
                margin["r"] = max(int(margin.get("r", 30) or 30), 45)
            layout["legend"] = legend
        else:
            margin["r"] = min(int(margin.get("r", 30) or 30), 40)
            margin["b"] = min(int(margin.get("b", 60) or 60), 80)
        layout["margin"] = margin
        return json.dumps(figure, ensure_ascii=False)

    def _render(self):
        raw = self._current_json()
        if not raw:
            return
        if not self._page_ready:
            self._pending_json = raw
            return
        self._pending_json = None
        payload = json.dumps(raw)
        self.plot_view.page().runJavaScript(
            f"window.czspecRender({payload}, 'interactive', true);"
            "setTimeout(function(){const gd=document.getElementById('plot');if(gd&&window.Plotly){Plotly.Plots.resize(gd);}},30);"
        )

    def _open_style(self):
        if callable(self.style_callback):
            self.style_callback()
            self._render()

    def _save(self):
        raw = self._current_json()
        if not raw:
            return
        from plotly import io as pio
        fig = pio.from_json(raw)
        key = re.sub(r"\W+", "_", self.source_combo.currentText()).strip("_") or "spectrum"
        custom_raw = self.image_name_input.text().strip()
        custom = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(custom_raw).stem if custom_raw else "").strip("._-")
        suggested = custom or f"{key}_{self.module_label}"
        if self.filename_prefix and not suggested.casefold().startswith(self.filename_prefix.casefold()):
            suggested = f"{self.filename_prefix}_{suggested}"
        self.output_directory.mkdir(parents=True, exist_ok=True)
        suggested_path = _unique_output_path(self.output_directory / f"{suggested}.png")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar espectro" if self.language == "es" else "Save spectrum",
            str(suggested_path),
            "PNG (*.png);;JPG (*.jpg);;PDF (*.pdf);;HTML (*.html)",
        )
        if not file_path:
            return
        path = Path(file_path); path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if path.suffix.lower() == ".html":
                fig.write_html(str(path), include_plotlyjs=True, full_html=True)
            else:
                fig.write_image(str(path), scale=2)
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.fullscreen_dialog = None

        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        )
        self.setWindowTitle("CZSpec — Análisis espectral molecular")
        self.setWindowIcon(QIcon(str(application_icon_path())))
        self.resize(1280, 820)
        self.setMinimumSize(1080, 700)

        self.selected_file = None
        self.selected_files = []
        self.spectrum_session = {}
        self._switching_spectrum = False
        self.comparison_plot_json = None
        self.last_result = None
        self.current_view_ranges = None

        self.raw_plot_json = None
        self.analyzed_plot_json = None
        self.analyzed_clean_plot_json = None
        self.current_plot_json = None
        self.current_view_mode = None

        self.manual_peak_freqs = []
        self.removed_peak_freqs = []
        self.removed_detection_ids = []
        self.settings = QSettings("CZSpec", "CZSpec")
        _network_value = str(self.settings.value("network/online", "true") or "true").strip().lower()
        self.network_online = _network_value not in {"0", "false", "off", "no"}
        os.environ["CZSPEC_ONLINE"] = "1" if self.network_online else "0"
        self.ui_language = str(self.settings.value("ui/language", "es") or "es").lower()
        if self.ui_language not in {"es", "en"}:
            self.ui_language = "es"
        self.smoothing_dialog = None
        self._restore_class_backend_settings()
        self.plot_styles = self._load_plot_styles()
        self.axis_config = self._load_json_setting(
            "m1/axis_config", deepcopy(PlotStyleDialog.DEFAULT_AXIS_CONFIG)
        )
        self.table_export_formats = self._load_json_setting(
            "m1/table_export_formats", ["csv", "html", "latex"]
        )
        self.table_decimal_places = int(self.settings.value("m1/table_decimal_places", 3) or 3)
        self.plot_export_formats = self._load_json_setting(
            "m1/plot_export_formats", ["html", "png", "jpg", "pdf"]
        )
        self.m2_table_export_formats = self._load_json_setting(
            "m2/table_export_formats", ["csv", "html", "latex"]
        )
        self.m2_plot_export_formats = self._load_json_setting(
            "m2/plot_export_formats", ["html", "png", "jpg", "pdf"]
        )
        self.m3_table_export_formats = self._load_json_setting(
            "m3/table_export_formats", ["csv", "html", "latex"]
        )
        self.m3_plot_export_formats = self._load_json_setting(
            "m3/plot_export_formats", ["html", "png", "jpg", "pdf"]
        )
        self.m2_plot_styles = self._load_json_setting(
            "m2/plot_styles", deepcopy(self.plot_styles)
        )
        for _role, _defaults in DEFAULT_PLOT_STYLES.items():
            if _role not in self.m2_plot_styles or not isinstance(self.m2_plot_styles.get(_role), dict):
                self.m2_plot_styles[_role] = deepcopy(_defaults)
            else:
                merged = deepcopy(_defaults); merged.update(self.m2_plot_styles[_role]); self.m2_plot_styles[_role] = merged
        self.m2_axis_config = self._load_json_setting(
            "m2/axis_config", deepcopy(self.axis_config)
        )
        self.m2_vlsr_style = self._load_json_setting(
            "m2/vlsr_style", {"color": "#D97706", "width": 1.5, "dash": "dot"}
        )
        self.species_final_label_mode = str(self.settings.value("m2/final_label_mode", "name") or "name")
        if self.species_final_label_mode not in {"name", "chemical_name", "none"}:
            self.species_final_label_mode = "name"
        self.comparison_config = self._load_comparison_config()
        self.fit_color = self.plot_styles["fits"]["color"]
        self._m1_log_history = []
        self._species_log_history = []
        self._column_density_log_history = []
        self._extracted_original_path = None

        self.species_selected_file = None
        self.species_last_result = None

        self.species_last_main_df = None
        self.species_last_topk_df = None
        self.species_last_output_name = None
        self.species_last_target_temperatures = None
        self.species_original_input_file = None
        self.species_external_spectrum_files = []
        self.species_qt_products = {}
        self.species_spectrum_products = {}
        self._species_final_sources_cache = {}
        self.species_search_policy = self._load_json_setting(
            "m2/search_policy",
            {
                "profile": "star_forming",
                "eu_max_k": 120.0,
                "emergency_eu_max_k": 180.0,
                "strict_family_mode": True,
                "forbid_halogens": True,
                "disallow_vib_excited": True,
                "allow_complex_organics": False,
                "allow_emergency_outside_family": False,
                "heavy_atoms_strict_max": 4,
                "soft_heavy_max": 5,
                "rescue_widen_factor": 1.8,
                "emergency_widen_factor": 4.0,
                "query_workers": 3,
                "weight_frequency": 0.75,
                "weight_eu": 0.15,
                "weight_loga": 0.10,
                "complexity_weight": 1.0,
            },
        )

        self.auto_species_csv_path = None

        self.species_topk_df = None
        self._species_topk_updating = False
        self.species_filter_active = False

        self.species_filter_text = ""
        self.species_filter_fields = []

        self.species_topk_filtered_df = None
        self.species_main_filtered_df = None

        self.column_density_vasyunina_df = None
        self.column_density_sanhueza_df = None
        self.column_density_source_df = None

        self.column_density_manual_file = None
        self.column_density_manual_df = None

        self.column_density_filter_active = False
        self.column_density_filter_text = ""
        self.column_density_filter_fields = []

        self.column_density_source_filtered_df = None
        self.column_density_vasyunina_filtered_df = None
        self.column_density_sanhueza_filtered_df = None

        self.lte_catalog_df = None
        self.lte_catalog_species_key = None
        self.lte_last_result = None
        self.nonlte_last_result = None
        self.nonlte_dialog = None
        self.nonlte_assignments = self._load_json_setting(
            "nonlte/lamda_assignments", {}
        )
        self.nonlte_defaults = self._load_json_setting(
            "nonlte/model_defaults",
            {
                "tkin_k": 20.0,
                "h2_density_cm3": 1.0e4,
                "h2_opr": 3.0,
                "geometry": "static sphere RADEX",
                "background_temperature_k": 2.725,
                "additional_colliders_cm3": {},
                "treat_line_overlap": False,
            },
        )
        self.lte_observed_frequency_mhz = None
        self.lte_observed_intensity_k = None
        self.lte_observed_source_file = None
        self.lte_species_rows = {}
        self.lte_physical_solutions = {}
        self.lte_solution_groups = {}
        self.lte_selected_method = None
        self.lte_applied_solution_key = None
        self.lte_reference_tau = None
        self.lte_components = []
        self.lte_observed_spectra = {}
        self.lte_active_band_path = None
        self.lte_component_workbench = None
        self.lte_diagnostics_dialog = None
        self.lte_setup_dialog = None
        self.lte_channel_spacing_mhz = None
        self.lte_plot_json = None
        self.lte_current_view_mode = None
        self.lte_fullscreen_dialog = None
        self._lte_plot_ready = False
        self._pending_lte_plot_json = None

        self.sanhueza_isotopic_ratios = dict(DEFAULT_ISOTOPIC_ABUNDANCE_RATIOS)
        self._plot_page_ready = False
        self._pending_plot_request = None
        self.thread_pool = QThreadPool(self)
        self.thread_pool.setMaxThreadCount(3)
        self._active_tasks = {}
        self._task_progress_values = {}
        self._table_plot_dialogs = []

        self._build_ui()
        self._apply_semantic_button_colors()
        self.toast = ToastNotification(self)
        self._refresh_network_mode_ui()

        self.task_progress_label = QLabel("Proceso")
        self.task_progress_label.setObjectName("taskProgressLabel")
        self.task_progress_label.setStyleSheet("font-weight:700; padding-left:8px;")
        self.task_progress_label.hide()
        self.task_progress = QProgressBar()
        self.task_progress.setObjectName("taskProgress")
        self.task_progress.setRange(0, 100)
        self.task_progress.setValue(0)
        self.task_progress.setFormat("%p%")
        self.task_progress.setTextVisible(True)
        self.task_progress.setMinimumWidth(330)
        self.task_progress.setMaximumWidth(460)
        self.task_progress.setMinimumHeight(22)
        self.task_progress.hide()
        self.statusBar().addPermanentWidget(self.task_progress_label)
        self.statusBar().addPermanentWidget(self.task_progress)
        self.statusBar().addPermanentWidget(QSizeGrip(self))
        self.statusBar().showMessage(self._ready_status_text())

    def _apply_semantic_button_colors(self):
        """Apply a small, consistent action-color vocabulary to M1/M2."""
        groups = {
            "primary": (
                "load_button", "species_load_button", "species_refresh_from_m1_button",
                "species_load_spectrum_button", "species_final_spectrum_button",
                "species_search_button", "save_image_button",
            ),
            "success": (
                "run_button", "analyze_all_button", "species_run_button", "add_manual_button",
            ),
            "export": (
                "export_csv_button", "export_html_button", "species_export_tables_button",
                "species_export_spectra_button", "species_export_qt_button",
            ),
            "folder": (
                "open_general_button", "open_graphics_button", "open_tables_button", "open_images_button",
                "species_open_general_button", "species_open_tables_button", "species_open_plotly_button",
                "species_open_qt_button", "species_open_figures_button",
            ),
            "secondary": (
                "calibration_button", "source_metadata_button", "compare_spectra_button", "smooth_button",
                "plot_style_button", "advanced_detection_button", "species_filters_button",
                "species_plot_table_button", "species_columns_button", "fullscreen_button",
            ),
            "danger": ("remove_selected_button",),
            "utility": (
                "refresh_button", "clear_baseline_windows_button", "species_clear_search_button",
            ),
        }
        for role, names in groups.items():
            for name in names:
                widget = getattr(self, name, None)
                if widget is not None:
                    _apply_action_role(widget, role)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(14, 10, 14, 10)
        root_layout.setSpacing(8)

        header = AppHeader(self)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 6, 10, 6)
        header_layout.setSpacing(5)

        brand_mark = QLabel()
        brand_mark.setObjectName("brandMark")
        brand_mark.setAlignment(Qt.AlignCenter)
        brand_mark.setFixedSize(38, 38)
        brand_mark.setPixmap(
            QPixmap(str(CZSPEC_ICON_PATH)).scaled(
                38,
                38,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        title = QLabel("CZSpec")
        title.setObjectName("appTitle")
        brand_text.addWidget(title)

        header_action_size = (82, 28)

        self.language_button = QPushButton("ES" if self.ui_language == "es" else "EN")
        self.language_button.setObjectName("appUpdateButton")
        self.language_button.setToolTip(
            "Cambiar a English" if self.ui_language == "es" else "Switch to Español"
        )
        self.language_button.clicked.connect(self.toggle_ui_language)

        self.network_mode_button = QPushButton()
        self.network_mode_button.setObjectName("networkModeButton")
        self.network_mode_button.setCheckable(True)
        self.network_mode_button.setChecked(bool(self.network_online))
        self.network_mode_button.toggled.connect(self.set_network_mode)

        self.app_settings_button = QPushButton("⚙")
        self.app_settings_button.setObjectName("appUpdateButton")
        self.app_settings_button.setToolTip(
            "Configuración de CZSpec" if self.ui_language == "es" else "CZSpec settings"
        )
        self.app_settings_button.clicked.connect(self.open_application_settings)

        self.app_restart_button = QPushButton()
        self.app_restart_button.setObjectName("appUpdateButton")
        self.app_restart_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        )
        self.app_restart_button.setToolTip(
            "Reiniciar CZSpec" if self.ui_language == "es" else "Restart CZSpec"
        )
        self.app_restart_button.clicked.connect(self.restart_application)

        self.app_version_button = QPushButton(__public_version__)
        self.app_version_button.setObjectName("appUpdateButton")
        self.app_version_button.clicked.connect(self.open_project_github)

        self.app_update_button = QPushButton("Actualizar")
        self.app_update_button.setObjectName("appUpdateButton")
        self.app_update_button.setToolTip(
            "Instalar una actualización oficial de CZSpec (.whl)"
        )
        self.app_update_button.clicked.connect(self.select_update_package)

        for _header_button in (
            self.language_button, self.network_mode_button, self.app_settings_button,
            self.app_restart_button, self.app_version_button, self.app_update_button,
        ):
            _header_button.setFixedSize(*header_action_size)

        self.window_minimize_button = QPushButton("—")
        self.window_minimize_button.setObjectName("windowControlButton")
        self.window_minimize_button.setToolTip("Minimizar")
        self.window_minimize_button.setFixedSize(30, 26)

        self.window_maximize_button = QPushButton("□")
        self.window_maximize_button.setObjectName("windowControlButton")
        self.window_maximize_button.setToolTip("Maximizar o restaurar")
        self.window_maximize_button.setFixedSize(30, 26)

        self.window_close_button = QPushButton("×")
        self.window_close_button.setObjectName("windowCloseButton")
        self.window_close_button.setToolTip("Cerrar CZSpec")
        self.window_close_button.setFixedSize(30, 26)

        self.window_minimize_button.clicked.connect(self.showMinimized)
        self.window_maximize_button.clicked.connect(self.toggle_window_size)
        self.window_close_button.clicked.connect(self.close)

        header_layout.addWidget(brand_mark)
        header_layout.addSpacing(4)
        header_layout.addLayout(brand_text)
        header_layout.addStretch()
        header_layout.addWidget(self.language_button)
        header_layout.addWidget(self.network_mode_button)
        header_layout.addWidget(self.app_settings_button)
        header_layout.addWidget(self.app_restart_button)
        header_layout.addSpacing(3)
        header_layout.addWidget(self.app_version_button)
        header_layout.addWidget(self.app_update_button)
        header_layout.addSpacing(3)
        header_layout.addWidget(self.window_minimize_button)
        header_layout.addWidget(self.window_maximize_button)
        header_layout.addWidget(self.window_close_button)
        root_layout.addWidget(header)

        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs, stretch=1)

        # =========================
        # TAB 1: Detección y ajuste de líneas espectrales
        # =========================
        self.peaks_tab = QWidget()
        self.tabs.addTab(self.peaks_tab, "1  Detección y ajuste")

        peaks_layout = QVBoxLayout(self.peaks_tab)

        self.file_label = QLabel("Ningún archivo seleccionado")
        self.file_label.setStyleSheet("font-size: 13px;")
        peaks_layout.addWidget(self.file_label)

        splitter = QSplitter(Qt.Horizontal)
        self.m1_splitter = splitter
        splitter.setChildrenCollapsible(False)
        peaks_layout.addWidget(splitter, stretch=1)

        left_panel = QWidget()
        left_panel.setObjectName("m1ControlsPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(6)
        left_panel.setMinimumWidth(0)
        left_panel.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        # M1 is frequently used on laptops. Keep the control column dense so the
        # scientific plot remains the dominant element instead of relying on a
        # hidden side panel. This local stylesheet deliberately affects only M1.
        left_panel.setStyleSheet(r"""
            QWidget#m1ControlsPanel { font-size: 9pt; }
            QWidget#m1ControlsPanel QGroupBox {
                margin-top: 10px; padding: 9px 6px 6px 6px; border-radius: 9px;
            }
            QWidget#m1ControlsPanel QGroupBox::title { left: 8px; padding: 0 4px; }
            QWidget#m1ControlsPanel QPushButton {
                min-height: 20px; padding: 3px 6px; border-radius: 7px;
            }
            QWidget#m1ControlsPanel QLineEdit,
            QWidget#m1ControlsPanel QDoubleSpinBox,
            QWidget#m1ControlsPanel QSpinBox,
            QWidget#m1ControlsPanel QComboBox {
                min-height: 22px; padding: 2px 5px; border-radius: 7px;
            }
            QWidget#m1ControlsPanel QHeaderView::section { padding: 4px 5px; }
        """)

        # El trabajo en M1 comienza por cargar/seleccionar el espectro y revisar
        # su identidad. Por eso la sesión se muestra antes del procesamiento.
        self.session_box = QGroupBox("Sesión espectral")
        session_box = self.session_box
        session_layout = QVBoxLayout(session_box)
        session_layout.setContentsMargins(7, 7, 7, 7)
        session_layout.setSpacing(5)

        self.load_button = QPushButton("Cargar espectro(s)")
        self.load_button.setToolTip(
            "Carga uno o varios espectros. Los archivos .30m se convierten mediante CLASS antes de entrar a M1."
        )
        session_layout.addWidget(self.load_button)

        self.spectrum_selector = QComboBox()
        self.spectrum_selector.addItem("Sin espectros cargados", None)
        self.spectrum_selector.setEnabled(False)
        self.spectrum_selector.setToolTip(
            "Elige el espectro activo; cada archivo conserva su análisis y edición manual."
        )
        session_layout.addWidget(self.spectrum_selector)

        self.source_metadata_button = QPushButton("Fuente y metadatos")
        self.source_metadata_button.setEnabled(False)
        self.source_metadata_button.setToolTip(
            "Edita nombre canónico, coordenadas, VLSR, frecuencia de reposo y temperaturas físicas asociadas a la fuente."
        )
        session_layout.addWidget(self.source_metadata_button)
        left_layout.addWidget(session_box)

        self.params_box = QGroupBox("Procesamiento y análisis")
        params_box = self.params_box
        self.params_layout = QFormLayout(params_box)
        params_layout = self.params_layout
        params_layout.setContentsMargins(7, 7, 7, 7)
        params_layout.setHorizontalSpacing(5)
        params_layout.setVerticalSpacing(5)
        params_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        params_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        params_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # La eficiencia sigue siendo un control científico explícito. Nunca se
        # aplica una receta instrumental de forma silenciosa.
        self.eta_input = QDoubleSpinBox()
        self.eta_input.setDecimals(4)
        self.eta_input.setRange(0.0001, 10.0)
        self.eta_input.setSingleStep(0.01)
        self.eta_input.setValue(0.81)
        self.eta_input.setToolTip(
            "Eficiencia usada como T_corr = T/η. Usa η=1 si el espectro ya está en la escala de intensidad deseada."
        )
        self.calibration_button = QPushButton("Configurar calibración")
        self.calibration_button.setEnabled(False)
        self.calibration_summary = QLabel("Bₑff=0.81 · f=1.23457")
        self.calibration_summary.setWordWrap(True)
        self.calibration_summary.setStyleSheet("color:#52627A; font-size:8pt;")
        calibration_widget = QWidget()
        self.calibration_widget = calibration_widget
        calibration_layout = QVBoxLayout(calibration_widget)
        calibration_layout.setContentsMargins(0, 0, 0, 0)
        calibration_layout.addWidget(self.calibration_button)
        calibration_layout.addWidget(self.calibration_summary)

        self.detection_sigma_input = QDoubleSpinBox()
        self.detection_sigma_input.setRange(0.5, 20.0)
        self.detection_sigma_input.setDecimals(1)
        self.detection_sigma_input.setSingleStep(0.5)
        self.detection_sigma_input.setValue(DEFAULT_DETECTION_SIGMA)
        self.detection_sigma_input.setSuffix(" σ")
        self.detection_sigma_input.setToolTip(
            "Altura mínima para una detección automática, expresada como múltiplo del ruido local robusto."
        )

        self.baseline_mode_combo = QComboBox()
        self.baseline_mode_combo.addItem("Automática", "auto")
        self.baseline_mode_combo.addItem("Manual", "windows")
        self.baseline_mode_combo.setToolTip(
            "Automática: CZSpec excluye señales antes del ajuste. Manual: sólo las ventanas indicadas se usan como referencia de línea base."
        )

        self.baseline_combo = QComboBox()
        self.baseline_combo.addItems(["0", "1", "2", "3"])

        self.baseline_windows_input = QLineEdit()
        self.baseline_windows_input.setPlaceholderText("143450-143470@0, 143900-143930@2 MHz")
        self.baseline_windows_input.setToolTip(
            "Ventanas de línea base en MHz. Puedes añadir @grado por ventana, por ejemplo 143450-143470@0, 143900-143930@2."
        )
        baseline_window_tools = QWidget()
        baseline_window_layout = QVBoxLayout(baseline_window_tools)
        baseline_window_layout.setContentsMargins(0, 0, 0, 0)
        baseline_window_layout.setSpacing(4)
        baseline_window_layout.addWidget(self.baseline_windows_input)
        baseline_window_buttons = QHBoxLayout()
        self.clear_baseline_windows_button = QPushButton("Limpiar ventanas")
        self.clear_baseline_windows_button.setToolTip("Elimina todas las ventanas manuales de línea base.")
        baseline_window_buttons.addWidget(self.clear_baseline_windows_button)
        baseline_window_layout.addLayout(baseline_window_buttons)
        self.baseline_windows_widget = baseline_window_tools

        self.polarity_combo = QComboBox()
        self.polarity_combo.addItem("Emisión", "emission")
        self.polarity_combo.addItem("Absorción", "absorption")
        self.polarity_combo.addItem("Emisión + absorción", "both")

        self.fit_combo = QComboBox()
        self.fit_combo.addItem("Gaussiano", "1")
        self.fit_combo.addItem("Lorentziano", "2")
        self.fit_combo.addItem("Voigt", "3")

        self.deblend_checkbox = QCheckBox("Iterativo + BIC")
        self.deblend_checkbox.setChecked(True)
        self.delta_bic_input = QDoubleSpinBox()
        self.delta_bic_input.setDecimals(1)
        self.delta_bic_input.setRange(0.0, 30.0)
        self.delta_bic_input.setSingleStep(1.0)
        self.delta_bic_input.setValue(6.0)
        self.max_components_input = QSpinBox()
        self.max_components_input.setRange(1, 12)
        self.max_components_input.setValue(8)

        self.plot_style_button = QPushButton("Estilo de gráfica")
        self.fit_color_button = self.plot_style_button

        params_layout.addRow("Calibración de intensidad:", calibration_widget)
        params_layout.addRow("Umbral de detección:", self.detection_sigma_input)
        params_layout.addRow("Línea base:", self.baseline_mode_combo)
        params_layout.addRow("Grado de línea base:", self.baseline_combo)
        params_layout.addRow("Ventanas de línea base:", baseline_window_tools)
        params_layout.addRow("Buscar:", self.polarity_combo)
        params_layout.addRow("Perfil de ajuste:", self.fit_combo)

        self.advanced_detection_button = QPushButton("Opciones avanzadas")
        self.advanced_detection_button.setCheckable(True)
        self.advanced_detection_button.setChecked(False)
        params_layout.addRow(self.advanced_detection_button)
        self.advanced_detection_widget = QWidget()
        advanced_layout = QFormLayout(self.advanced_detection_widget)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setHorizontalSpacing(5)
        advanced_layout.setVerticalSpacing(4)
        advanced_layout.addRow("Deblending:", self.deblend_checkbox)
        advanced_layout.addRow("ΔBIC mínimo:", self.delta_bic_input)
        advanced_layout.addRow("Máx. componentes/grupo:", self.max_components_input)
        self.advanced_detection_widget.setVisible(False)
        params_layout.addRow(self.advanced_detection_widget)
        self.advanced_detection_button.toggled.connect(self.advanced_detection_widget.setVisible)
        params_layout.addRow("Estilo de gráfica:", self.plot_style_button)

        # Herramientas de selección directa sobre Plotly. Box/Lasso pueden
        # convertirse en ventanas de baseline o en un recorte no destructivo.
        selection_widget = QWidget()
        selection_layout = QVBoxLayout(selection_widget)
        selection_layout.setContentsMargins(0, 0, 0, 0)
        selection_row = QHBoxLayout()
        self.selection_action_combo = QComboBox()
        self.selection_action_combo.addItem("Ventana de línea base", "baseline")
        self.selection_action_combo.addItem("Extraer región", "extract")
        selection_row.addWidget(self.selection_action_combo, stretch=1)
        self.selection_back_button = QPushButton("←")
        self.selection_forward_button = QPushButton("→")
        self.restore_extracted_button = QPushButton("↺")
        for button in (self.selection_back_button, self.selection_forward_button):
            button.setFixedSize(28, 28)
            button.setEnabled(False)
        self.restore_extracted_button.setFixedSize(28, 28)
        self.restore_extracted_button.setToolTip("Volver directamente al espectro completo.")
        self.restore_extracted_button.setEnabled(False)
        selection_row.addWidget(self.selection_back_button)
        selection_row.addWidget(self.selection_forward_button)
        selection_row.addWidget(self.restore_extracted_button)
        selection_layout.addLayout(selection_row)
        selection_note = QLabel("Usa Box Select o Lasso Select en la barra de la gráfica.")
        selection_note.setWordWrap(True)
        selection_note.setStyleSheet("color:#64748B;font-size:11px;")
        self.selection_note = selection_note
        selection_layout.addWidget(selection_note)
        params_layout.addRow("Selección interactiva:", selection_widget)

        # Keep every M1 control genuinely shrinkable on laptop screens.  The
        # scroll area should constrain the content, not clip a minimum-size
        # child that happens to be wider than the viewport.
        compact_fields = (
            self.calibration_button, self.detection_sigma_input,
            self.baseline_mode_combo, self.baseline_combo,
            self.baseline_windows_input, self.clear_baseline_windows_button,
            self.polarity_combo, self.fit_combo, self.advanced_detection_button,
            self.delta_bic_input, self.max_components_input, self.plot_style_button,
            self.selection_action_combo, self.load_button, self.spectrum_selector,
            self.source_metadata_button,
        )
        for widget in compact_fields:
            widget.setMinimumWidth(0)
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, widget.sizePolicy().verticalPolicy())
        for box in (session_box, params_box):
            box.setMinimumWidth(0)

        action_grid = QGridLayout()
        self.compare_spectra_button = QPushButton("Comparar")
        self.smooth_button = QPushButton("Suavizado")
        self.run_button = QPushButton("Ejecutar análisis")
        self.analyze_all_button = QPushButton("Analizar todos")
        self.refresh_button = QPushButton("Reiniciar espectro")
        self.compare_spectra_button.setEnabled(False)
        self.smooth_button.setEnabled(False)
        self.analyze_all_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        action_grid.addWidget(self.compare_spectra_button, 0, 0)
        action_grid.addWidget(self.smooth_button, 0, 1)
        action_grid.addWidget(self.run_button, 1, 0)
        action_grid.addWidget(self.analyze_all_button, 1, 1)
        action_grid.addWidget(self.refresh_button, 2, 0, 1, 2)
        params_layout.addRow(action_grid)

        self._update_baseline_window_visibility()
        self.baseline_mode_combo.currentIndexChanged.connect(self._update_baseline_window_visibility)
        self.clear_baseline_windows_button.clicked.connect(self.baseline_windows_input.clear)
        left_layout.addWidget(params_box)

        # La configuración de CLASS se gestiona desde la configuración global.
        self.class_config_button = QPushButton("Configurar GILDAS/CLASS")
        self.class_config_button.setVisible(False)

        self.export_csv_button = QPushButton("Exportar tablas")
        self.export_html_button = QPushButton("Exportar gráficas")
        self.open_general_button = QPushButton("Salida principal")
        self.open_graphics_button = QPushButton("Gráficas")
        self.open_tables_button = QPushButton("Tablas")
        self.open_images_button = QPushButton("Imágenes")
        self.export_csv_button.setEnabled(False)
        self.export_html_button.setEnabled(False)

        self.folders_box = QGroupBox("Guardado y carpetas")
        folders_box = self.folders_box
        folders_layout = QGridLayout(folders_box)
        self.save_label_input = QLineEdit()
        self.save_label_input.setPlaceholderText("Nombre de guardado (opcional)")
        self.save_label_input.setToolTip("Etiqueta opcional para crear una carpeta de sesión independiente sin sobrescribir exportaciones previas.")
        folders_layout.addWidget(self.save_label_input, 0, 0, 1, 2)
        folders_layout.setContentsMargins(7, 7, 7, 7)
        folders_layout.setHorizontalSpacing(5)
        folders_layout.setVerticalSpacing(5)
        # Orden 2×3 solicitado: exportaciones, carpetas especializadas, salida.
        folders_layout.addWidget(self.export_csv_button, 1, 0)
        folders_layout.addWidget(self.export_html_button, 1, 1)
        folders_layout.addWidget(self.open_tables_button, 2, 0)
        folders_layout.addWidget(self.open_graphics_button, 2, 1)
        folders_layout.addWidget(self.open_images_button, 3, 0)
        folders_layout.addWidget(self.open_general_button, 3, 1)
        for button in (self.export_csv_button, self.export_html_button, self.open_tables_button,
                       self.open_graphics_button, self.open_images_button, self.open_general_button):
            button.setMinimumWidth(0)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        folders_box.setMinimumWidth(0)
        left_layout.addWidget(folders_box)

        self.manual_box = QGroupBox("Edición manual de detecciones")
        manual_box = self.manual_box
        manual_layout = QVBoxLayout(manual_box)
        manual_layout.setContentsMargins(7, 7, 7, 7)
        manual_layout.setSpacing(5)
        self.manual_freq_input = QLineEdit()
        self.manual_freq_input.setPlaceholderText(
            "Frecuencia(s) MHz o índices/rangos para eliminar"
        )
        self.manual_freq_input.setMinimumWidth(0)
        self.manual_freq_input.setToolTip("Frecuencias en MHz o índices/rangos; el texto puede desplazarse horizontalmente dentro del campo.")
        manual_layout.addWidget(self.manual_freq_input)
        manual_buttons = QHBoxLayout()
        self.add_manual_button = QPushButton("Agregar")
        self.remove_selected_button = QPushButton("Eliminar")
        self.add_manual_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.remove_selected_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        manual_buttons.addWidget(self.add_manual_button)
        manual_buttons.addWidget(self.remove_selected_button)
        manual_layout.addLayout(manual_buttons)
        left_layout.addWidget(manual_box)

        self.detections_box = QGroupBox("Líneas espectrales detectadas")
        detections_box = self.detections_box
        detections_layout = QVBoxLayout(detections_box)
        detections_header = QHBoxLayout()
        detections_header.addStretch()
        self.detach_detections_button = QPushButton("↗")
        self.detach_detections_button.setFixedSize(28, 26)
        self.detach_detections_button.setToolTip("Open the detected-lines table in a floating window" if self.ui_language == "en" else "Abrir la tabla de líneas detectadas en una ventana flotante")
        detections_header.addWidget(self.detach_detections_button)
        detections_layout.addLayout(detections_header)
        self.detections_list = QTableWidget(0, 5)
        self.detections_list.setMinimumHeight(150)
        self.detections_list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.detections_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.detections_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.detections_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.detections_list.horizontalHeader().setStretchLastSection(True)
        self.detections_list.verticalHeader().setVisible(False)
        detections_layout.addWidget(self.detections_list)
        left_layout.addWidget(detections_box, stretch=1)

        # Keep the system log available without sacrificing the main plot area.
        # It lives below the detected-lines table and can be expanded on demand.
        self.logs_box = QGroupBox("Logs de M1")
        logs_box = self.logs_box
        logs_layout = QVBoxLayout(logs_box)
        logs_header = QHBoxLayout(); logs_header.addStretch()
        self.toggle_logs_button = QPushButton("↕"); self.toggle_logs_button.setFixedSize(28,26)
        self.toggle_logs_button.setToolTip("Expandir/reducir el log" if self.ui_language=="es" else "Expand/collapse system log")
        logs_header.addWidget(self.toggle_logs_button); logs_layout.addLayout(logs_header)
        self.log_area = QTextEdit(); self.log_area.setReadOnly(True); self.log_area.setMinimumHeight(86); self.log_area.setMaximumHeight(125)
        logs_layout.addWidget(self.log_area)
        left_layout.addWidget(logs_box)

        left_layout.addStretch()
        left_scroll = QScrollArea()
        left_scroll.setObjectName("sidePanelScroll")
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setMinimumWidth(270)
        left_scroll.setMaximumWidth(360)
        left_scroll.setWidget(left_panel)
        self.m1_left_scroll = left_scroll
        splitter.addWidget(left_scroll)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.plot_box = QGroupBox("Visualización")
        plot_box = self.plot_box
        plot_layout = QVBoxLayout(plot_box)

        plot_toolbar = QHBoxLayout()
        # Unified M1 view selector.  Legacy buttons remain as hidden aliases for
        # internal/backward compatibility, but the user-facing control matches M2.
        self.m1_view_label = QLabel("Vista:")
        self.m1_view_combo = QComboBox()
        self.m1_view_combo.addItem("Crudo", "raw")
        self.m1_view_combo.addItem("Sin leyenda", "no_legend")
        self.m1_view_combo.addItem("Con leyenda", "with_legend")
        self.m1_view_combo.addItem("Con leyenda extendida", "with_legend_extended")
        self.m1_view_combo.setMinimumWidth(175)
        self.view_raw_button = QPushButton("Ver crudo"); self.view_raw_button.setVisible(False)
        self.view_clean_button = QPushButton("Ver sin leyenda"); self.view_clean_button.setVisible(False)
        self.view_interactive_button = QPushButton("Ver con leyenda"); self.view_interactive_button.setVisible(False)
        self.m1_image_name_input = QLineEdit()
        self.m1_image_name_input.setPlaceholderText("Nombre de imagen (opcional)")
        self.m1_image_name_input.setToolTip("Nombre opcional para la captura. Si se deja vacío, CZSpec genera un nombre automático.")
        self.m1_image_name_input.setMaximumWidth(220)
        self.save_image_button = QPushButton("Guardar imagen")
        self.toggle_m1_panel_button = QPushButton("◀")
        self.toggle_m1_panel_button.setFixedSize(32, 30)
        self.toggle_m1_panel_button.setToolTip("Oculta o recupera el panel de controles para ampliar la gráfica.")
        self.fullscreen_button = QPushButton("Pantalla completa")

        plot_toolbar.addWidget(self.m1_view_label)
        plot_toolbar.addWidget(self.m1_view_combo)
        plot_toolbar.addWidget(self.m1_image_name_input)
        plot_toolbar.addWidget(self.save_image_button)
        plot_toolbar.addStretch()
        plot_toolbar.addWidget(self.toggle_m1_panel_button)
        plot_toolbar.addWidget(self.fullscreen_button)

        self.plot_stack = QStackedWidget()
        self.plot_stack.setMinimumHeight(300)
        self.plot_placeholder = QLabel(
            "Carga un espectro para iniciar la visualización."
        )
        self.plot_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.plot_placeholder.setStyleSheet(
            "color: #52627A; font-size: 17px; background: #FFFFFF;"
        )
        self.plot_stack.addWidget(self.plot_placeholder)
        self.plot_view = None

        plot_layout.addLayout(plot_toolbar)
        plot_layout.addWidget(self.plot_stack)
        right_layout.addWidget(plot_box, stretch=3)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([290, 1110])

        self.load_button.clicked.connect(self.load_file)
        self.calibration_button.clicked.connect(self.open_calibration_dialog)
        self.source_metadata_button.clicked.connect(self.open_source_metadata_dialog)
        self.class_config_button.clicked.connect(self.open_class_backend_dialog)
        self.smooth_button.clicked.connect(self.open_smoothing_dialog)
        self.spectrum_selector.currentIndexChanged.connect(self._spectrum_selection_changed)
        self.compare_spectra_button.clicked.connect(
            lambda: self.show_spectrum_comparison(configure=True)
        )
        self.analyze_all_button.clicked.connect(self.analyze_all_spectra)
        self.run_button.clicked.connect(self.run_process)
        self.refresh_button.clicked.connect(self.reset_active_spectrum)
        self.fullscreen_button.clicked.connect(self.open_fullscreen_plot)

        self.view_raw_button.clicked.connect(self.show_raw_view)
        self.view_clean_button.clicked.connect(self.show_analyzed_clean_view)
        self.view_interactive_button.clicked.connect(self.show_analyzed_interactive_view)
        self.m1_view_combo.currentIndexChanged.connect(self._m1_view_changed)
        self.save_image_button.clicked.connect(self.save_current_plot_image)

        self.add_manual_button.clicked.connect(self.add_manual_detection)
        self.remove_selected_button.clicked.connect(self.remove_selected_detections)
        self.detections_list.cellClicked.connect(self._focus_detection_row)
        self.detach_detections_button.clicked.connect(self.open_detected_lines_window)
        self.selection_action_combo.currentIndexChanged.connect(self._selection_mode_changed)
        self.selection_back_button.clicked.connect(lambda: self._navigate_extraction_history(-1))
        self.selection_forward_button.clicked.connect(lambda: self._navigate_extraction_history(1))
        self.restore_extracted_button.clicked.connect(self.restore_full_spectrum)
        self.toggle_m1_panel_button.clicked.connect(self.toggle_m1_side_panel)
        self.toggle_logs_button.clicked.connect(self.toggle_system_log_size)

        self.export_csv_button.clicked.connect(self.export_table_results)
        self.export_html_button.clicked.connect(self.export_plots_results)
        self.open_general_button.clicked.connect(
            lambda: self._open_folder(PEAK_DETECTION_OUTPUT_DIR)
        )
        self.open_graphics_button.clicked.connect(
            lambda: self._open_folder(PEAK_GRAPHICS_DIR)
        )
        self.open_tables_button.clicked.connect(
            lambda: self._open_folder(PEAK_TABLES_DIR)
        )
        self.open_images_button.clicked.connect(
            lambda: self._open_folder(PEAK_IMAGES_DIR)
        )
        self.plot_style_button.clicked.connect(self.open_plot_style_dialog)

        # =========================
        # TAB 2: Buscador de especies
        # =========================
        self._build_species_tab()

        # =========================
        # TAB 3: Densidad de columna
        # =========================
        self._build_column_density_tab()

        # =========================
        # TAB 4: Modelado espectral LTE / no-LTE
        # =========================
        self._build_lte_tab()

        # =========================
        # TAB 5: Razones de densidad columnar
        # =========================
        from czspec.gui.molecular_ratios import MolecularRatioWidget

        self.molecular_ratios_tab = MolecularRatioWidget(
            self._m5_m6_data_provider,
            self,
        )
        self.tabs.addTab(self.molecular_ratios_tab, "5  Razones moleculares")

        # =========================
        # TAB 6: Representación espacial paramétrica
        # =========================
        from czspec.gui.spatial_environment import SpatialEnvironmentWidget

        self.spatial_environment_tab = SpatialEnvironmentWidget(
            self._m5_m6_data_provider,
            self,
        )
        self.tabs.addTab(self.spatial_environment_tab, "6  Representación espacial")
        self.tabs.currentChanged.connect(self._advanced_tab_changed)
        self._apply_public_module_visibility()
        self._apply_visual_roles()
        self._apply_ui_language()

    def _apply_public_module_visibility(self):
        """Oculta M4--M6 en la interfaz pública sin retirarlos del paquete.

        Los widgets y su lógica siguen construidos y disponibles internamente,
        pero no forman parte de la navegación pública de CZSpec v1.0.0.
        """
        for widget_name in (
            "lte_tab",
            "molecular_ratios_tab",
            "spatial_environment_tab",
        ):
            widget = getattr(self, widget_name, None)
            if widget is None:
                continue
            index = self.tabs.indexOf(widget)
            if index < 0:
                continue
            try:
                self.tabs.setTabVisible(index, False)
            except AttributeError:
                self.tabs.tabBar().setTabVisible(index, False)
            self.tabs.setTabEnabled(index, False)

    def _refresh_network_mode_ui(self):
        """Refreshes the global Online/Offline policy without restarting CZSpec."""
        online = bool(getattr(self, "network_online", True))
        en = getattr(self, "ui_language", "es") == "en"
        os.environ["CZSPEC_ONLINE"] = "1" if online else "0"
        button = getattr(self, "network_mode_button", None)
        if button is not None:
            button.blockSignals(True)
            button.setChecked(online)
            button.setText("Online" if online else "Offline")
            button.setProperty("online", "true" if online else "false")
            button.setToolTip(
                ("Online mode: external catalog/services are enabled. Click for Offline mode." if en else
                 "Modo online: catálogos y servicios externos habilitados. Pulsa para usar modo sin Internet.")
                if online else
                ("Offline mode: Internet-dependent stages are skipped. Click to enable Online mode." if en else
                 "Modo sin Internet: las etapas que dependen de Internet se omiten. Pulsa para activar Online.")
            )
            button.style().unpolish(button); button.style().polish(button)
            button.blockSignals(False)
        version_button = getattr(self, "app_version_button", None)
        if version_button is not None:
            version_button.setEnabled(online)
        species_button = getattr(self, "species_run_button", None)
        if species_button is not None:
            species_button.setEnabled(online)
            species_button.setToolTip(
                ("Uses Splatalogue; available in Online mode." if en else "Usa Splatalogue; disponible en modo Online.")
                if not online else ""
            )

    def set_network_mode(self, online: bool):
        self.network_online = bool(online)
        self.settings.setValue("network/online", self.network_online)
        self.settings.sync()
        self._refresh_network_mode_ui()
        text = (
            "Online mode enabled. External services may be used when requested." if self.ui_language == "en" else
            "Modo Online activado. Los servicios externos podrán usarse cuando se soliciten."
        ) if self.network_online else (
            "Offline mode enabled. Internet-dependent stages will be skipped." if self.ui_language == "en" else
            "Modo sin Internet activado. Las etapas dependientes de Internet se omitirán."
        )
        try:
            self.statusBar().showMessage(text, 6000)
            self.log("[INFO] " + text)
        except Exception:
            pass

    def open_project_github(self):
        if not bool(getattr(self, "network_online", True)):
            self.notify_info(
                "Enable Online mode to open GitHub." if self.ui_language == "en" else
                "Activa el modo Online para abrir GitHub."
            )
            return
        QDesktopServices.openUrl(QUrl(PROJECT_URL))

    def toggle_ui_language(self):
        self.ui_language = "en" if self.ui_language == "es" else "es"
        self.settings.setValue("ui/language", self.ui_language)
        self.settings.sync()
        self._apply_ui_language()

    def _update_baseline_window_visibility(self, *_):
        manual = str(self.baseline_mode_combo.currentData()) == "windows"
        self.baseline_windows_widget.setVisible(manual)
        try:
            self.params_layout.setRowVisible(self.baseline_windows_widget, manual)
        except Exception:
            pass

    def _save_axis_config(self):
        self.settings.setValue(
            "m1/axis_config", json.dumps(self.axis_config, ensure_ascii=False)
        )
        self.settings.sync()

    def _ready_status_text(self) -> str:
        return (
            ("Ready · Workspace: " if self.ui_language == "en" else "Listo · Espacio de trabajo: ")
            + str(WORKSPACE_DIR)
        )

    def _apply_ui_language(self):
        """Traduce la navegación global y M1; los módulos se amplían al cerrarlos."""
        en = self.ui_language == "en"
        self.setWindowTitle("CZSpec — Molecular spectral analysis" if en else "CZSpec — Análisis espectral molecular")
        if hasattr(self, "language_button"):
            self.language_button.setText("EN" if en else "ES")
            self.language_button.setToolTip("Switch to Español" if en else "Cambiar a English")
        if hasattr(self, "app_settings_button"):
            self.app_settings_button.setToolTip("CZSpec settings" if en else "Configuración de CZSpec")
        if hasattr(self, "app_restart_button"):
            self.app_restart_button.setToolTip("Restart CZSpec" if en else "Reiniciar CZSpec")
        if hasattr(self, "app_version_button"):
            self.app_version_button.setToolTip(
                "Open the CZSpec GitHub repository" if en else "Abrir el repositorio de CZSpec en GitHub"
            )
        if hasattr(self, "app_update_button"):
            self.app_update_button.setText("Update" if en else "Actualizar")
            self.app_update_button.setToolTip(
                "Install an official CZSpec update (.whl)" if en else "Instalar una actualización oficial de CZSpec (.whl)"
            )
        self._refresh_network_mode_ui()
        if hasattr(self, "window_minimize_button"):
            self.window_minimize_button.setToolTip("Minimize" if en else "Minimizar")
            self.window_maximize_button.setToolTip("Maximize or restore" if en else "Maximizar o restaurar")
            self.window_close_button.setToolTip("Close CZSpec" if en else "Cerrar CZSpec")

        tab_names = (
            "1  Detection and fitting" if en else "1  Detección y ajuste",
            "2  Molecular identification" if en else "2  Identificación molecular",
            "3  Column density" if en else "3  Densidad de columna",
            "4  Spectral modeling" if en else "4  Modelado espectral",
            "5  Molecular ratios" if en else "5  Razones moleculares",
            "6  Spatial representation" if en else "6  Representación espacial",
        )
        for i, name in enumerate(tab_names):
            if i < self.tabs.count():
                self.tabs.setTabText(i, name)
        self._apply_public_module_visibility()

        # M2 · identificación molecular
        if hasattr(self, "species_source_box"):
            self.species_source_box.setTitle("Analyzed input" if en else "Información analizada")
            self.species_config_box.setTitle("Configuration" if en else "Configuración")
            self.species_actions_box.setTitle("Identification process" if en else "Proceso de identificación")
            self.species_exports_box.setTitle("Save and folders" if en else "Guardado y carpetas")
            self.species_logs_box.setTitle("M2 Logs" if en else "Logs de M2")
            self.species_search_box.setTitle("Search / filter" if en else "Búsqueda / filtro")
            self.species_results_box.setTitle("Main results" if en else "Resultados principales")
            self.species_topk_box.setTitle("TOP-K")
            self.species_tables_label.setText("Tables" if en else "Tablas")

            self.species_load_button.setText("Load table…" if en else "Cargar tabla…")
            self.species_refresh_from_m1_button.setText("Refresh from M1" if en else "Actualizar desde M1")
            self.species_m1_scope_label.setText("M1 data:" if en else "Datos M1:")
            for data, es_text, en_text in (
                ("active", "Espectro activo", "Active spectrum"),
                ("session", "Toda la sesión analizada", "Entire analyzed session"),
            ):
                idx = self.species_m1_scope_combo.findData(data)
                if idx >= 0:
                    self.species_m1_scope_combo.setItemText(idx, en_text if en else es_text)

            self.species_spectrum_label.setText("Spectrum:" if en else "Espectro:")
            for data, es_text, en_text in (
                ("active", "Espectro activo de M1", "Active M1 spectrum"),
                ("session", "Toda la sesión de M1", "Entire M1 session"),
                ("external", "Archivo(s) externo(s)", "External file(s)"),
            ):
                idx = self.species_spectrum_mode_combo.findData(data)
                if idx >= 0:
                    self.species_spectrum_mode_combo.setItemText(idx, en_text if en else es_text)
            self.species_load_spectrum_button.setText("Load…" if en else "Cargar…")
            self.species_spectrum_label_mode_label.setText("Label:" if en else "Etiqueta:")
            idx = self.species_spectrum_label_mode_combo.findData("name")
            if idx >= 0: self.species_spectrum_label_mode_combo.setItemText(idx, "Species / transition" if en else "Especie / transición")
            idx = self.species_spectrum_label_mode_combo.findData("chemical_name")
            if idx >= 0: self.species_spectrum_label_mode_combo.setItemText(idx, "Chemical name" if en else "Nombre químico")
            self._species_spectrum_mode_changed()

            for widget, label_text in (
                (self.species_output_input, "Output:" if en else "Salida:"),
                (self.species_temperatures_input, "Q(T) [K]:"),
                (self.species_topk_input, "TOP-K:"),
            ):
                label = self.species_config_layout.labelForField(widget)
                if label is not None:
                    label.setText(label_text)
            self.species_output_input.setPlaceholderText("Automatic name from source" if en else "Nombre automático desde la fuente")
            self.species_filters_button.setText("Identification filters…" if en else "Filtros de identificación…")
            self.species_run_button.setText("Run molecular identification" if en else "Ejecutar identificación molecular")
            self.species_generate_qt_button.setText("Generate Q(T)" if en else "Generar Q(T)")
            self.species_generate_spectra_button.setText("Generate spectra" if en else "Generar espectros")
            self.species_save_label_input.setPlaceholderText("Save label (optional)" if en else "Nombre de guardado (opcional)")
            self.species_save_label_input.setToolTip(
                "Optional prefix for M2 products. If the name already exists, CZSpec appends _001, _002, etc. without overwriting." if en else
                "Prefijo opcional para los productos de M2. Si el nombre ya existe, CZSpec agrega _001, _002, etc., sin sobrescribir."
            )
            self.species_export_tables_button.setText("Export tables" if en else "Exportar tablas")
            self.species_export_qt_button.setText("Export Q(T)" if en else "Exportar Q(T)")
            self.species_export_spectra_button.setText("Export spectra" if en else "Exportar espectros")
            self.species_open_general_button.setText("Main output" if en else "Salida principal")
            self.species_open_tables_button.setText("Tables" if en else "Tablas")
            self.species_open_qt_button.setText("Q(T)")
            self.species_open_plotly_button.setText("Spectra" if en else "Espectros")
            self.species_open_figures_button.setText("Figures" if en else "Figuras")
            self.species_load_spectrum_button.setToolTip("Enabled only for External file(s)." if en else "Sólo se habilita al elegir Archivo(s) externo(s).")

            self.species_search_input.setPlaceholderText("e.g. 1-5; HCN; SO2" if en else "Ej.: 1-5; HCN; SO2")
            self.species_search_button.setText("Search" if en else "Buscar")
            self.species_clear_search_button.setText("Clear" if en else "Limpiar")
            self.species_search_obs_id_cb.setText("Observation ID" if en else "ID de observación")
            self.species_search_name_cb.setText("Species / transition" if en else "Especie / transición")
            self.species_search_chemical_name_cb.setText("Chemical name" if en else "Nombre químico")
            self.species_search_species_id_cb.setText("Species ID" if en else "ID de especie")
            self.species_search_moleculeTag_cb.setText("Molecular tag" if en else "Etiqueta molecular")
            self.species_columns_button.setText("Columns…" if en else "Columnas…")
            self.species_plot_table_button.setText("Plot tables…" if en else "Graficar tablas…")
            self.species_final_spectrum_button.setText("Final spectrum…" if en else "Espectro final…")
            idx = self.species_plot_view_combo.findData("with_legend")
            if idx >= 0: self.species_plot_view_combo.setItemText(idx, "With legend" if en else "Con leyenda")
            idx = self.species_plot_view_combo.findData("no_legend")
            if idx >= 0: self.species_plot_view_combo.setItemText(idx, "Without legend" if en else "Sin leyenda")

            for table in (self.species_table, self.species_topk_table):
                cols=[]
                for c in range(table.columnCount()):
                    hi=table.horizontalHeaderItem(c)
                    cols.append(_table_header_internal_name(hi, hi.text() if hi else f"col{c}"))
                if cols: _set_scientific_table_headers(table, cols)
            if not getattr(self, "species_selected_file", None):
                self.species_file_label.setText("No line table loaded" if en else "Sin tabla de líneas cargada")

        # M3 · column density
        if hasattr(self, "column_density_source_box"):
            self.column_density_info_label.setText(
                "This tab uses the final selection from Molecular identification."
                if en else "Esta pestaña usa la selección final de Identificación molecular."
            )
            self.column_density_source_box.setTitle("Data source" if en else "Fuente de datos")
            self.column_density_refresh_button.setText("Refresh from M2" if en else "Actualizar desde M2")
            self.column_density_load_button.setText("Load data" if en else "Cargar datos")
            self.vasy_box.setTitle("Optically thin method (OTM)" if en else "Método ópticamente delgado (MOD)")
            self.vasyunina_temp_label.setText("Excitation temperatures [K]:" if en else "Temperaturas de excitación [K]:")
            self.vasyunina_run_button.setText("Run OTM" if en else "Ejecutar MOD")
            self.sanh_box.setTitle("Hyperfine-transition method (HTM)" if en else "Método de transiciones hiperfinas (MTH)")
            self.sanhueza_tex_label.setText("Excitation temperatures [K]:" if en else "Temperaturas de excitación [K]:")
            self.sanhueza_ratios_label.setText("Isotopic ratios:" if en else "Razones isotópicas:")
            self.sanhueza_ratios_button.setText("Isotopic ratios" if en else "Razones isotópicas")
            self.sanhueza_r_mode_checkbox.setText("Use r approximation" if en else "Usar aproximación de r")
            self.sanhueza_r_mode_checkbox.setToolTip(
                "Click to enable/disable the r approximation. Blue = enabled." if en else
                "Haz clic para activar/desactivar la aproximación de r. Azul = activa."
            )
            self.sanhueza_tau_label.setText("Maximum τ (optional):" if en else "τ máximo (opcional):")
            self.sanhueza_run_button.setText("Run HTM" if en else "Ejecutar MTH")
            self.column_density_folders_box.setTitle("Save and folders" if en else "Guardado y carpetas")
            self.column_density_save_label_input.setPlaceholderText("Save label (optional)" if en else "Nombre de guardado (opcional)")
            self.column_density_save_label_input.setToolTip(
                "Optional prefix for M3 products. If the name already exists, CZSpec appends _001, _002, etc. without overwriting." if en else
                "Prefijo opcional para los productos de M3. Si el nombre ya existe, CZSpec agrega _001, _002, etc., sin sobrescribir."
            )
            self.column_density_export_tables_button.setText("Export Tables" if en else "Exportar tablas")
            self.column_open_tables_button.setText("Tables" if en else "Tablas")
            self.column_density_export_spectra_button.setText("Export spectra" if en else "Exportar espectros")
            self.column_open_spectra_button.setText("Spectra" if en else "Espectros")
            self.column_open_images_button.setText("Figures" if en else "Figuras")
            self.column_open_general_button.setText("Main output" if en else "Salida principal")
            self.column_density_logs_box.setTitle("M3 Logs" if en else "Logs de M3")
            self.sanhueza_ratios_summary_label.setText(self._format_sanhueza_isotopic_ratios_summary())
            self._rebuild_column_density_log_display()
            self.column_density_search_box.setTitle("Search / filter" if en else "Búsqueda / filtro")
            self.cd_search_obs_id_cb.setText("Observation ID" if en else "ID de observación")
            self.cd_search_name_cb.setText("Species / transition" if en else "Especie / transición")
            self.cd_search_chemical_name_cb.setText("Chemical name" if en else "Nombre químico")
            self.cd_search_species_id_cb.setText("Species ID" if en else "ID de especie")
            self.cd_search_moleculeTag_cb.setText("Molecular tag" if en else "Etiqueta molecular")
            self.cd_search_input.setPlaceholderText("What are you looking for?" if en else "¿Qué buscas?")
            self.cd_search_button.setText("Search" if en else "Buscar")
            self.cd_clear_search_button.setText("Clear search" if en else "Limpiar búsqueda")
            self.column_density_tables_label.setText("Tables" if en else "Tablas")
            self.column_density_plot_table_button.setText("Plot tables…" if en else "Graficar tablas…")
            self.column_density_final_spectrum_button.setText("Final spectrum…" if en else "Espectro final…")
            self.column_density_columns_button.setText("Columns…" if en else "Columnas…")
            tab_labels = (
                "1  Input" if en else "1  Entrada",
                "2  OTM" if en else "2  MOD",
                "3  HTM" if en else "3  MTH",
                "4  OTM vs HTM" if en else "4  MOD vs MTH",
            )
            for i, label in enumerate(tab_labels):
                if i < self.column_density_tables_tabs.count():
                    self.column_density_tables_tabs.setTabText(i, label)
            self.vasyunina_comparison_box.setTitle("Optically thin method (OTM)" if en else "Método ópticamente delgado (MOD)")
            self.sanhueza_comparison_box.setTitle("Hyperfine-transition method (HTM)" if en else "Método de transiciones hiperfinas (MTH)")
            # Table headers are presentation-only and must follow the UI language
            # even when the underlying DataFrame was created in the other language.
            for table in (self.column_density_source_table, self.vasyunina_results_table, self.sanhueza_results_table,
                          self.vasyunina_comparison_table, self.sanhueza_comparison_table):
                cols=[]
                for c in range(table.columnCount()):
                    hi=table.horizontalHeaderItem(c)
                    cols.append(_table_header_internal_name(hi, hi.text() if hi else f"col{c}"))
                if cols: _set_scientific_table_headers(table, cols)

        if not hasattr(self, "params_box"):
            return
        self.params_box.setTitle("Processing and analysis" if en else "Procesamiento y análisis")
        self.session_box.setTitle("Spectral session" if en else "Sesión espectral")
        self.folders_box.setTitle("Save and folders" if en else "Guardado y carpetas")
        self.manual_box.setTitle("Manual detection editing" if en else "Edición manual de detecciones")
        self.detections_box.setTitle("Detected spectral lines" if en else "Líneas espectrales detectadas")
        self.logs_box.setTitle("M1 Logs" if en else "Logs de M1")

        field_labels = (
            (self.calibration_widget, "Calibration:" if en else "Calibración:"),
            (self.detection_sigma_input, "Threshold:" if en else "Umbral:"),
            (self.baseline_mode_combo, "Baseline:" if en else "Línea base:"),
            (self.baseline_combo, "Degree:" if en else "Grado:"),
            (self.baseline_windows_widget, "Windows:" if en else "Ventanas:"),
            (self.polarity_combo, "Search:" if en else "Buscar:"),
            (self.fit_combo, "Profile:" if en else "Perfil:"),
            (self.plot_style_button, "Plot style:" if en else "Estilo:"),
            (self.selection_action_combo.parentWidget(), "Selection:" if en else "Selección:"),
        )
        for widget, label_text in field_labels:
            label = self.params_layout.labelForField(widget)
            if label is not None:
                label.setText(label_text)

        auto_idx = self.baseline_mode_combo.findData("auto")
        manual_idx = self.baseline_mode_combo.findData("windows")
        if auto_idx >= 0:
            self.baseline_mode_combo.setItemText(auto_idx, "Automatic" if en else "Automática")
        if manual_idx >= 0:
            self.baseline_mode_combo.setItemText(manual_idx, "Manual" if en else "Manual")
        labels = {
            "emission": "Emission" if en else "Emisión",
            "absorption": "Absorption" if en else "Absorción",
            "both": "Emission + absorption" if en else "Emisión + absorción",
        }
        for key, label_text in labels.items():
            idx = self.polarity_combo.findData(key)
            if idx >= 0:
                self.polarity_combo.setItemText(idx, label_text)
        fit_labels = {"1": "Gaussian" if en else "Gaussiano", "2": "Lorentzian" if en else "Lorentziano", "3": "Voigt"}
        for key, label_text in fit_labels.items():
            idx = self.fit_combo.findData(key)
            if idx >= 0:
                self.fit_combo.setItemText(idx, label_text)

        self.advanced_detection_button.setText("Advanced options" if en else "Opciones avanzadas")
        advanced_layout = self.advanced_detection_widget.layout()
        if isinstance(advanced_layout, QFormLayout):
            mapping = (
                (self.deblend_checkbox, "Deblending:"),
                (self.delta_bic_input, "Minimum ΔBIC:" if en else "ΔBIC mínimo:"),
                (self.max_components_input, "Max. components/group:" if en else "Máx. componentes/grupo:"),
            )
            for widget, label_text in mapping:
                label = advanced_layout.labelForField(widget)
                if label is not None:
                    label.setText(label_text)
        self.deblend_checkbox.setText("Iterative + BIC" if en else "Iterativo + BIC")
        self.plot_style_button.setText("Plot style" if en else "Estilo de gráfica")

        self.load_button.setText("Load spectrum(s)" if en else "Cargar espectro(s)")
        self.calibration_button.setText("Configure calibration" if en else "Configurar calibración")
        self.source_metadata_button.setText("Source and metadata" if en else "Fuente y metadatos")
        self.compare_spectra_button.setText("Compare" if en else "Comparar")
        self.smooth_button.setText("Smoothing" if en else "Suavizado")
        self.run_button.setText("Run analysis" if en else "Ejecutar análisis")
        self.analyze_all_button.setText("Analyze all" if en else "Analizar todos")
        self.refresh_button.setText("Reset spectrum" if en else "Reiniciar espectro")
        self.export_csv_button.setText("Export Tables" if en else "Exportar tablas")
        if hasattr(self, "save_label_input"):
            self.save_label_input.setPlaceholderText("Save label (optional)" if en else "Nombre de guardado (opcional)")
        self.export_html_button.setText("Export Plots" if en else "Exportar gráficas")
        self.open_general_button.setText("Main output" if en else "Salida principal")
        self.open_graphics_button.setText("Plots" if en else "Gráficas")
        self.open_tables_button.setText("Tables" if en else "Tablas")
        self.open_images_button.setText("Images" if en else "Imágenes")
        self.view_raw_button.setText("Raw" if en else "Ver crudo")
        self.view_clean_button.setText("No legend" if en else "Ver sin leyenda")
        self.view_interactive_button.setText("With legend" if en else "Ver con leyenda")
        if hasattr(self, "m1_view_label"):
            self.m1_view_label.setText("View:" if en else "Vista:")
        if hasattr(self, "m1_view_combo"):
            labels = {
                "raw": "Raw" if en else "Crudo",
                "no_legend": "Without legend" if en else "Sin leyenda",
                "with_legend": "With legend" if en else "Con leyenda",
                "with_legend_extended": "With legend extended" if en else "Con leyenda extendida",
            }
            for data, label in labels.items():
                idx = self.m1_view_combo.findData(data)
                if idx >= 0:
                    self.m1_view_combo.setItemText(idx, label)
        if hasattr(self, "m1_image_name_input"):
            self.m1_image_name_input.setPlaceholderText("Image name (optional)" if en else "Nombre de imagen (opcional)")
            self.m1_image_name_input.setToolTip("Optional filename for the screenshot. Leave blank for an automatic name." if en else "Nombre opcional para la captura. Si se deja vacío, CZSpec genera un nombre automático.")
        self.save_image_button.setText("Save image" if en else "Guardar imagen")
        self.fullscreen_button.setText("Fullscreen" if en else "Pantalla completa")
        if hasattr(self, "toggle_m1_panel_button"):
            visible = self.m1_left_scroll.isVisible() if hasattr(self, "m1_left_scroll") else True
            self.toggle_m1_panel_button.setText("◀" if visible else "▶")
        self.plot_box.setTitle("Visualization" if en else "Visualización")
        self.plot_placeholder.setText(
            "Load a spectrum to start visualization." if en else "Carga un espectro para iniciar la visualización."
        )
        self.clear_baseline_windows_button.setText("Clear windows" if en else "Limpiar ventanas")
        self.restore_extracted_button.setText("↺")
        self.selection_back_button.setToolTip("Previous extraction" if en else "Recorte anterior")
        self.selection_forward_button.setToolTip("Next extraction" if en else "Recorte siguiente")
        if hasattr(self, "toggle_m1_panel_button"):
            visible = self.m1_left_scroll.isVisible() if hasattr(self, "m1_left_scroll") else True
            self.toggle_m1_panel_button.setText("◀" if visible else "▶")
            self.toggle_m1_panel_button.setToolTip("Hide/show the control panel to enlarge the plot." if en else "Oculta/muestra el panel de controles para ampliar la gráfica.")
        self.selection_note.setText(
            "Use Box Select or Lasso Select in the plot toolbar." if en else
            "Usa Box Select o Lasso Select en la barra de la gráfica."
        )
        for data, es_text, en_text in (
            ("baseline", "Ventana de línea base", "Baseline window"),
            ("extract", "Extraer región", "Extract region"),
        ):
            idx = self.selection_action_combo.findData(data)
            if idx >= 0:
                self.selection_action_combo.setItemText(idx, en_text if en else es_text)

        self.add_manual_button.setText("Add" if en else "Agregar")
        self.remove_selected_button.setText("Remove" if en else "Eliminar")
        self.manual_freq_input.setPlaceholderText(
            "Frequency/frequencies in MHz or indices/ranges to remove" if en else
            "Frecuencia(s) MHz o índices/rangos para eliminar"
        )
        self._set_detection_table_headers()
        self._update_baseline_window_visibility()

        if not self.selected_file:
            self.file_label.setText("No file selected" if en else "Ningún archivo seleccionado")
        if not self.selected_files and self.spectrum_selector.count() > 0:
            self.spectrum_selector.setItemText(0, "No spectra loaded" if en else "Sin espectros cargados")
        if not self._active_tasks:
            self.statusBar().showMessage(self._ready_status_text())
        if hasattr(self, "task_progress_label"):
            self.task_progress_label.setText("Progress" if en else "Proceso")

        # Rebuild only the M1 log text that has a known translation and redraw
        # the current plot so labels change with the interface language too.
        self._rebuild_m1_log_display()
        self._rebuild_species_log_display()
        # Re-label visible M2 table headers and selection chips without touching data.
        try:
            if getattr(self, "species_topk_df", None) is not None:
                self.populate_species_topk_table()
                self.refresh_species_main_table_from_selection()
        except Exception:
            pass
        self._refresh_current_plot_language()

    def restart_application(self):
        """Reinicia CZSpec usando el mismo intérprete y entorno activo."""
        en = self.ui_language == "en"
        answer = QMessageBox.question(
            self,
            "Restart CZSpec" if en else "Reiniciar CZSpec",
            (
                "CZSpec will close and reopen now. Continue?"
                if en
                else "CZSpec se cerrará y volverá a abrir ahora. ¿Continuar?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            program = sys.executable
            arguments = ["-m", "czspec", *sys.argv[1:]]
            started, _pid = QProcess.startDetached(program, arguments, str(Path.cwd()))
        except Exception as exc:
            self.notify(
                "Restart failed" if en else "No se pudo reiniciar",
                str(exc),
            )
            return

        if not started:
            self.notify(
                "Restart failed" if en else "No se pudo reiniciar",
                (
                    "CZSpec could not start a new process."
                    if en
                    else "CZSpec no pudo iniciar el nuevo proceso."
                ),
            )
            return

        app = QApplication.instance()
        if app is not None:
            app.quit()
        else:
            self.close()

    def open_application_settings(self):
        input_dir = str(self.settings.value("paths/input_dir", "") or "")
        dialog = ApplicationSettingsDialog(
            input_dir=input_dir,
            workspace_dir=str(WORKSPACE_DIR),
            language=self.ui_language,
            text_scale_percent=int(self.settings.value("ui/text_scale_percent", 100) or 100),
            font_family=str(self.settings.value("ui/font_family", "Inter") or "Inter"),
            table_decimal_places=int(self.settings.value("m1/table_decimal_places", 3) or 3),
            table_formats=list(self.table_export_formats),
            plot_formats=list(self.plot_export_formats),
            m2_table_formats=list(self.m2_table_export_formats),
            m2_plot_formats=list(self.m2_plot_export_formats),
            m3_table_formats=list(self.m3_table_export_formats),
            m3_plot_formats=list(self.m3_plot_export_formats),
            parent=self,
        )
        dialog.classBackendRequested.connect(self.open_class_backend_dialog)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        config = dialog.configuration()
        self.settings.setValue("paths/input_dir", config.get("input_dir", ""))
        text_scale = max(80, min(150, int(config.get("text_scale_percent", 100) or 100)))
        font_family = str(config.get("font_family", "Inter") or "Inter").strip() or "Inter"
        self.settings.setValue("ui/text_scale_percent", text_scale)
        self.settings.setValue("ui/font_family", font_family)
        self.table_decimal_places = int(config.get("table_decimal_places", 3) or 0)
        self.settings.setValue("m1/table_decimal_places", self.table_decimal_places)
        self.table_export_formats = list(config.get("table_formats") or ["csv", "html", "latex"])
        self.plot_export_formats = list(config.get("plot_formats") or ["html", "png", "jpg", "pdf"])
        self.settings.setValue("m1/table_export_formats", json.dumps(self.table_export_formats, ensure_ascii=False))
        self.settings.setValue("m1/plot_export_formats", json.dumps(self.plot_export_formats, ensure_ascii=False))
        self.m2_table_export_formats = list(config.get("m2_table_formats") or ["csv", "html", "latex"])
        self.m2_plot_export_formats = list(config.get("m2_plot_formats") or ["html", "png", "jpg", "pdf"])
        self.settings.setValue("m2/table_export_formats", json.dumps(self.m2_table_export_formats, ensure_ascii=False))
        self.settings.setValue("m2/plot_export_formats", json.dumps(self.m2_plot_export_formats, ensure_ascii=False))
        self.m3_table_export_formats = list(config.get("m3_table_formats") or ["csv", "html", "latex"])
        self.m3_plot_export_formats = list(config.get("m3_plot_formats") or ["html", "png", "jpg", "pdf"])
        self.settings.setValue("m3/table_export_formats", json.dumps(self.m3_table_export_formats, ensure_ascii=False))
        self.settings.setValue("m3/plot_export_formats", json.dumps(self.m3_plot_export_formats, ensure_ascii=False))
        self.settings.sync()
        # Apply typography live without discarding the current scientific session.
        # Updates are temporarily suspended so Qt performs one consolidated
        # relayout instead of repeatedly reflowing every table and panel.
        previous_scale = int(self.settings.value("ui/text_scale_applied", 100) or 100)
        previous_family = str(self.settings.value("ui/font_family_applied", "Inter") or "Inter")
        if text_scale != previous_scale or font_family != previous_family:
            app = QApplication.instance()
            if app is not None:
                self.setUpdatesEnabled(False)
                try:
                    app.setFont(QFont(font_family, max(8, round(10 * text_scale / 100))))
                    app.setStyleSheet(build_app_stylesheet(text_scale, font_family))
                    self.settings.setValue("ui/text_scale_applied", text_scale)
                    self.settings.setValue("ui/font_family_applied", font_family)
                    self.settings.sync()
                finally:
                    self.setUpdatesEnabled(True)
                    self.updateGeometry()
                    self.update()
                QTimer.singleShot(0, lambda: QApplication.processEvents())
            self.notify_success(
                "Appearance updated without restarting the session."
                if self.ui_language == "en" else
                "La apariencia se actualizó sin reiniciar la sesión."
            )
        workspace = str(config.get("workspace_dir") or "").strip()
        if workspace:
            try:
                config_dir = Path.home() / ".czspec"
                config_dir.mkdir(parents=True, exist_ok=True)
                (config_dir / "preferences.json").write_text(
                    json.dumps({"workspace_dir": workspace}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception as exc:
                self.notify("Configuración" if self.ui_language == "es" else "Settings", str(exc))
                return
            if Path(workspace).expanduser().resolve() != Path(WORKSPACE_DIR).resolve():
                self.notify_info(
                    "La nueva carpeta de salida se aplicará al reiniciar CZSpec."
                    if self.ui_language == "es" else
                    "The new output folder will be used after restarting CZSpec."
                )

    def _m5_m6_data_provider(self):
        """Entrega a M5/M6 una instantánea trazable de los resultados de M3."""

        source = self.column_density_manual_file or self.species_selected_file or self.selected_file
        if source:
            dataset = Path(source).stem
        elif len(self.selected_files) > 1:
            dataset = f"sesion_{len(self.selected_files)}_espectros"
        else:
            dataset = "sesión actual"
        return (
            self.column_density_vasyunina_df,
            self.column_density_sanhueza_df,
            dataset,
        )

    def _advanced_tab_changed(self, index: int):
        widget = self.tabs.widget(index)
        if hasattr(self, "species_tab") and widget is self.species_tab:
            # Seamless M1 -> M2 hand-off: if the user has already analyzed the
            # active spectrum and M2 has no explicit input yet, recover it once.
            if not getattr(self, "species_selected_file", None) and self.selected_file:
                state = self.spectrum_session.get(self.selected_file, {})
                result = state.get("last_result") or {}
                if result.get("results_df") is not None and not result.get("results_df").empty:
                    self.refresh_species_input_from_m1()
            self._species_spectrum_mode_changed()
        elif widget is self.molecular_ratios_tab:
            self.molecular_ratios_tab.refresh()
        elif widget is self.spatial_environment_tab:
            self.spatial_environment_tab.refresh()
            # El WebEngine se inicializa aquí, no al arrancar CZSpec.
            self.spatial_environment_tab.activate_viewer()

    def _refresh_advanced_modules(self):
        if hasattr(self, "molecular_ratios_tab"):
            self.molecular_ratios_tab.refresh()
        if hasattr(self, "spatial_environment_tab"):
            self.spatial_environment_tab.refresh()

    def _apply_visual_roles(self):
        """Aplica jerarquía visual sin mezclar estilos con la lógica."""
        primary_buttons = (
            self.run_button,
            self.species_run_button,
            self.vasyunina_run_button,
            self.sanhueza_run_button,
            self.lte_run_button,
        )
        accent_buttons = (
            self.save_image_button,
            self.species_save_results_button,
            self.save_vasyunina_button,
            self.save_sanhueza_button,
            self.lte_export_button,
        )

        for button in primary_buttons:
            button.setProperty("role", "primary")
        for button in accent_buttons:
            button.setProperty("role", "accent")

        for table in self.findChildren(QTableWidget):
            table.setAlternatingRowColors(True)
            table.verticalHeader().setVisible(False)

    def toggle_window_size(self):
        if self.isMaximized():
            self.showNormal()
            self.window_maximize_button.setText("□")
            self.window_maximize_button.setToolTip("Maximizar")
        else:
            self.showMaximized()
            self.window_maximize_button.setText("❐")
            self.window_maximize_button.setToolTip("Restaurar tamaño")

    def _class_backend_config(self) -> dict:
        return {
            "backend": str(self.settings.value("class30m/backend", "auto") or "auto"),
            "native_class": str(self.settings.value("class30m/native_class", "") or ""),
            "wsl_distro": str(self.settings.value("class30m/wsl_distro", "") or ""),
            "wsl_class": str(self.settings.value("class30m/wsl_class", "") or ""),
        }

    def _restore_class_backend_settings(self):
        config = self._class_backend_config()
        os.environ["CZSPEC_CLASS_BACKEND"] = config["backend"]
        os.environ["CZSPEC_NATIVE_CLASS"] = config["native_class"]
        os.environ["CZSPEC_WSL_DISTRO"] = config["wsl_distro"]
        os.environ["CZSPEC_WSL_CLASS"] = config["wsl_class"]

    def open_class_backend_dialog(self):
        dialog = ClassBackendConfigDialog(self._class_backend_config(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        config = dialog.configuration()
        self.settings.setValue("class30m/backend", config["backend"])
        self.settings.setValue("class30m/native_class", config["native_class"])
        self.settings.setValue("class30m/wsl_distro", config["wsl_distro"])
        self.settings.setValue("class30m/wsl_class", config["wsl_class"])
        self.settings.sync()
        self._restore_class_backend_settings()
        ok, status = class_backend_status()
        if ok:
            self.log(f"[OK] Backend .30m configurado: {status}")
            self.notify_success("GILDAS/CLASS quedó disponible para archivos .30m.")
        else:
            self.log(f"[WARN] Backend .30m aún no disponible: {status}")
            self.notify("GILDAS/CLASS no disponible", status, duration_ms=12000)

    def select_update_package(self):
        start_directory = Path.home()
        for candidate_name in ("Downloads", "Descargas"):
            candidate = Path.home() / candidate_name
            if candidate.is_dir():
                start_directory = candidate
                break

        package_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar actualización de CZSpec",
            str(start_directory),
            "Actualización de CZSpec (czspec-*.whl);;Python Wheel (*.whl)",
        )
        if not package_path:
            return

        self.notify_info(
            "Instalando la actualización. Puedes continuar usando esta ventana; "
            "los cambios se aplicarán al reiniciar CZSpec."
        )

        def work(progress):
            progress(10, "Validando el paquete de actualización")
            progress(30, "Instalando la nueva versión")
            result = install_update_package(package_path)
            progress(95, "Verificando la instalación")
            return result

        def on_success(result):
            message = (
                f"{result.package_path.name} quedó instalado. Cierra y vuelve a "
                "abrir CZSpec para usar la nueva versión."
            )
            if result.desktop_warning:
                message += f"\n\nAviso: {result.desktop_warning}"
            self.notify(
                "Actualización instalada",
                message,
                duration_ms=12000,
            )

        def on_error(message, details):
            self.notify(
                "No se pudo actualizar",
                message[-900:],
                duration_ms=12000,
            )

        self._start_background_task(
            "czspec_update",
            work,
            on_success,
            on_error=on_error,
            busy_widgets=(self.app_update_button,),
            status_message="Instalando actualización de CZSpec...",
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "toast") and self.toast.isVisible():
            self._position_toast()

    def _position_toast(self):
        margin = 22
        status_height = self.statusBar().height() if self.statusBar() else 0
        available_width = max(320, self.width() - 2 * margin)
        toast_width = min(460, available_width)
        self.toast.resize(toast_width, self.toast.sizeHint().height())
        self.toast.move(
            max(margin, self.width() - self.toast.width() - margin),
            max(margin, self.height() - self.toast.height() - status_height - margin),
        )

    def notify(self, title: str, message: str, duration_ms: int = 6500):
        self.toast.show_message(title, message, duration_ms)
        self._position_toast()

    def notify_success(self, message: str):
        self.notify("Proceso completado", message)

    def notify_info(self, message: str):
        self.notify("Información", message, duration_ms=5000)

    def _start_background_task(
        self,
        key: str,
        function,
        on_success,
        *,
        on_error=None,
        busy_widgets=(),
        status_message: str,
    ):
        if key in self._active_tasks:
            self.notify_info("Esta operación ya se encuentra en ejecución.")
            return False

        worker = BackgroundTask(function)
        widgets = tuple(busy_widgets)
        self._active_tasks[key] = (worker, widgets)
        self._task_progress_values[key] = 0

        for widget in widgets:
            widget.setEnabled(False)

        self.task_progress_label.setText("Progress" if self.ui_language == "en" else "Proceso")
        self.task_progress_label.show()
        self.task_progress.show()
        self.task_progress.setValue(
            int(sum(self._task_progress_values.values()) / len(self._task_progress_values))
        )
        self.statusBar().showMessage(status_message)

        worker.signals.succeeded.connect(
            lambda result, callback=on_success: self._dispatch_task_success(
                callback, result
            )
        )
        worker.signals.failed.connect(
            lambda failure, callback=on_error: self._dispatch_task_failure(
                callback, failure
            )
        )
        worker.signals.progress.connect(
            lambda value, message, task_key=key: self._update_task_progress(
                task_key, value, message
            )
        )
        worker.signals.finished.connect(
            lambda task_key=key: self._finish_background_task(task_key)
        )
        self.thread_pool.start(worker)
        return True

    def _update_task_progress(self, key: str, value: int, message: str = ""):
        if key not in self._active_tasks:
            return
        self._task_progress_values[key] = max(0, min(100, int(value)))
        values = list(self._task_progress_values.values())
        self.task_progress.setValue(int(round(sum(values) / len(values))))
        if message:
            self.statusBar().showMessage(f"{message} · {int(value)}%")

    def _dispatch_task_success(self, callback, result):
        try:
            callback(result)
        except Exception as exc:
            self._dispatch_task_failure(
                None,
                (str(exc), traceback.format_exc()),
            )

    def _dispatch_task_failure(self, callback, failure):
        message, details = failure
        if callback is not None:
            callback(message, details)
            return
        QMessageBox.critical(self, "Error", message)

    def _finish_background_task(self, key: str):
        task_data = self._active_tasks.pop(key, None)
        self._task_progress_values.pop(key, None)
        if task_data is not None:
            _, widgets = task_data
            for widget in widgets:
                widget.setEnabled(True)

        if key in {
            "lte_catalog",
            "lte_model",
            "lte_refinement",
            "nonlte_backend",
            "nonlte_model",
        }:
            self.lte_run_button.setEnabled(self._lte_model_inputs_ready())
            self.lte_refine_button.setEnabled(
                bool(self.lte_last_result)
                and self.lte_last_result.get("model_kind", "LTE") == "LTE"
            )
            if hasattr(self, "nonlte_run_button"):
                self._refresh_nonlte_controls()

        if hasattr(self, "spectrum_selector"):
            has_spectra = bool(self.selected_files)
            has_multiple = len(self.selected_files) > 1
            self.spectrum_selector.setEnabled(has_spectra)
            self.compare_spectra_button.setEnabled(has_multiple)
            self.analyze_all_button.setEnabled(has_multiple)

        if not self._active_tasks:
            self.task_progress.hide()
            self.task_progress_label.hide()
            self.statusBar().showMessage(self._ready_status_text())
        else:
            values = list(self._task_progress_values.values())
            self.task_progress.setValue(int(round(sum(values) / len(values))))

    def _load_json_setting(self, key: str, default):
        raw_value = self.settings.value(key, "")
        if not raw_value:
            return deepcopy(default)
        try:
            value = json.loads(str(raw_value))
        except (TypeError, ValueError, json.JSONDecodeError):
            return deepcopy(default)
        if not isinstance(value, type(default)):
            return deepcopy(default)
        return value

    def _load_plot_styles(self) -> dict:
        styles = deepcopy(DEFAULT_PLOT_STYLES)
        raw_value = self.settings.value("plot_styles", "")
        if not raw_value:
            return styles

        try:
            saved = json.loads(str(raw_value))
        except (TypeError, ValueError, json.JSONDecodeError):
            return styles

        if not isinstance(saved, dict):
            return styles

        for role, values in saved.items():
            if role in styles and isinstance(values, dict):
                styles[role].update(values)
        return styles

    def _save_plot_styles(self):
        self.settings.setValue(
            "plot_styles",
            json.dumps(self.plot_styles, ensure_ascii=False),
        )

    def _load_comparison_config(self) -> dict:
        defaults = {
            "content": "raw",
            "layout": "grid",
            "share_x": False,
            "share_y": False,
            "show_sum": False,
            "sum_styles": [],
            "files": {},
        }
        raw_value = self.settings.value("spectrum_comparison", "")
        if not raw_value:
            return defaults
        try:
            saved = json.loads(str(raw_value))
        except (TypeError, ValueError, json.JSONDecodeError):
            return defaults
        if not isinstance(saved, dict):
            return defaults
        defaults.update({
            key: saved[key]
            for key in ("content", "layout", "share_x", "share_y", "show_sum", "sum_styles", "files")
            if key in saved
        })
        return defaults

    def _save_comparison_config(self):
        self.settings.setValue(
            "spectrum_comparison",
            json.dumps(self.comparison_config, ensure_ascii=False),
        )

    def open_plot_style_dialog(self):
        dialog = PlotStyleDialog(
            self.plot_styles,
            axis_config=self.axis_config,
            language=self.ui_language,
            native_intensity_unit=self._current_plot_metadata().get("bunit") or self._current_plot_metadata().get("intensity_unit"),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        old_axis_config = deepcopy(self.axis_config)
        self.plot_styles = deepcopy(dialog.styles)
        self.axis_config = deepcopy(dialog.axis_configuration())
        axis_layout_changed = old_axis_config != self.axis_config
        self.fit_color = self.plot_styles["fits"]["color"]
        self.comparison_plot_json = None
        self._save_plot_styles()
        self._save_axis_config()
        self.log("[INFO] Plot styles and axes updated." if self.ui_language == "en" else "[INFO] Estilos y ejes de la gráfica actualizados.")

        if self.last_result is not None and self.selected_file:
            self.log("[INFO] Recalculando la visualización con los nuevos estilos...")
            if axis_layout_changed:
                # A change of orientation/primary/secondary axis must not inherit
                # the old Plotly x/y ranges, otherwise intensity and frequency can
                # appear swapped until the user toggles views.
                mode = self.current_view_mode or "interactive"
                canonical = self.analyzed_plot_json if mode in {"interactive", "interactive_extended"} else self.analyzed_clean_plot_json if mode == "clean" else self.raw_plot_json
                if canonical:
                    self.render_plot_full(canonical, mode=mode)
                    self.current_plot_json = canonical
            else:
                self.update_detections_preserving_view()
            return

        if self.selected_file:
            try:
                state = self.spectrum_session.get(self.selected_file, {})
                raw_result = load_raw_spectrum(
                    str(state.get("analysis_path") or self.selected_file),
                    plot_styles=self.plot_styles,
                    display_name=str(state.get("display_name") or Path(self.selected_file).name),
                    input_metadata=self._active_analysis_metadata(state),
                    language=self.ui_language,
                )
                self.raw_plot_json = raw_result["plot_json"]
                self.current_plot_json = self.raw_plot_json
                self.current_view_mode = "raw"
                if self.selected_file in self.spectrum_session:
                    self.spectrum_session[self.selected_file].update({
                        "raw_result": raw_result,
                        "raw_plot_json": self.raw_plot_json,
                        "current_plot_json": self.raw_plot_json,
                        "current_view_mode": "raw",
                    })
                self.render_plot_full(self.raw_plot_json, mode="raw")
            except Exception as exc:
                self.log(f"[ERROR] No se pudieron aplicar los estilos: {exc}")

    # Compatibilidad con integraciones que invocaban el selector anterior.
    def choose_fit_color(self):
        self.open_plot_style_dialog()

    def _build_species_tab(self):
        self.species_tab = QWidget()
        self.tabs.addTab(self.species_tab, "2  Identificación molecular")

        layout = QVBoxLayout(self.species_tab)
        layout.setContentsMargins(7, 7, 7, 7)
        layout.setSpacing(5)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(9)
        layout.addWidget(splitter, stretch=1)

        # ================================================================
        # Panel izquierdo · M2
        # ================================================================
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setSpacing(5)
        left_panel.setMinimumWidth(315)

        self.species_source_box = QGroupBox("Información analizada")
        source_layout = QVBoxLayout(self.species_source_box)
        source_layout.setContentsMargins(7, 8, 7, 7)
        source_layout.setSpacing(4)

        input_buttons = QHBoxLayout(); input_buttons.setSpacing(5)
        self.species_load_button = QPushButton("Cargar tabla…")
        self.species_refresh_from_m1_button = QPushButton("Actualizar desde M1")
        input_buttons.addWidget(self.species_load_button)
        input_buttons.addWidget(self.species_refresh_from_m1_button)
        source_layout.addLayout(input_buttons)

        # El alcance sólo controla qué tabla analizada se recupera de M1.  El
        # selector de espectro de abajo es independiente y se usa para la
        # visualización cinemática final de M2.
        refresh_scope_row = QHBoxLayout(); refresh_scope_row.setSpacing(5)
        self.species_m1_scope_label = QLabel("Datos M1:")
        self.species_m1_scope_combo = QComboBox()
        self.species_m1_scope_combo.addItem("Espectro activo", "active")
        self.species_m1_scope_combo.addItem("Toda la sesión analizada", "session")
        refresh_scope_row.addWidget(self.species_m1_scope_label)
        refresh_scope_row.addWidget(self.species_m1_scope_combo, stretch=1)
        source_layout.addLayout(refresh_scope_row)

        self.species_file_label = QLabel("Sin tabla de líneas cargada")
        self.species_file_label.setWordWrap(True)
        self.species_file_label.setStyleSheet("font-size:11px;color:#52627A;")
        self.species_file_label.setMaximumHeight(48)
        source_layout.addWidget(self.species_file_label)

        spectrum_row = QHBoxLayout(); spectrum_row.setSpacing(5)
        self.species_spectrum_label = QLabel("Espectro:")
        self.species_spectrum_mode_combo = QComboBox()
        self.species_spectrum_mode_combo.addItem("Espectro activo de M1", "active")
        self.species_spectrum_mode_combo.addItem("Toda la sesión de M1", "session")
        self.species_spectrum_mode_combo.addItem("Archivo(s) externo(s)", "external")
        self.species_load_spectrum_button = QPushButton("Cargar…")
        self.species_load_spectrum_button.setMaximumWidth(80)
        self.species_load_spectrum_button.setToolTip("Sólo se habilita al elegir Archivo(s) externo(s)." if self.ui_language == "es" else "Enabled only for External file(s).")
        spectrum_row.addWidget(self.species_spectrum_label)
        spectrum_row.addWidget(self.species_spectrum_mode_combo, stretch=1)
        spectrum_row.addWidget(self.species_load_spectrum_button)
        source_layout.addLayout(spectrum_row)

        # El tipo de identificador pertenece al visor final, no a la entrada de análisis.
        # Conservamos estos objetos ocultos como alias de compatibilidad para rutas alfa previas.
        self.species_spectrum_label_mode_label = QLabel("Etiqueta:")
        self.species_spectrum_label_mode_combo = QComboBox()
        self.species_spectrum_label_mode_combo.addItem("Especie / transición", "name")
        self.species_spectrum_label_mode_combo.addItem("Nombre químico", "chemical_name")
        idx = self.species_spectrum_label_mode_combo.findData(self.species_final_label_mode)
        self.species_spectrum_label_mode_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.species_spectrum_label_mode_label.setVisible(False)
        self.species_spectrum_label_mode_combo.setVisible(False)

        self.species_spectrum_file_label = QLabel("Se usarán los espectros cargados en M1.")
        self.species_spectrum_file_label.setWordWrap(True)
        self.species_spectrum_file_label.setStyleSheet("font-size:11px;color:#52627A;")
        self.species_spectrum_file_label.setMaximumHeight(44)
        source_layout.addWidget(self.species_spectrum_file_label)
        left_layout.addWidget(self.species_source_box)

        self.species_config_box = QGroupBox("Configuración")
        self.species_config_layout = QFormLayout(self.species_config_box)
        self.species_config_layout.setContentsMargins(7, 8, 7, 7)
        self.species_config_layout.setHorizontalSpacing(6)
        self.species_config_layout.setVerticalSpacing(4)
        self.species_output_input = QLineEdit(); self.species_output_input.setPlaceholderText("Nombre automático desde la fuente")
        self.species_temperatures_input = QLineEdit(); self.species_temperatures_input.setPlaceholderText("e.g. 10, 28" if self.ui_language == "en" else "Ej. 10, 28")
        self.species_topk_input = QSpinBox(); self.species_topk_input.setRange(1, 100); self.species_topk_input.setValue(5)
        self.species_filters_button = QPushButton("Filtros de identificación…")
        self.species_config_layout.addRow("Salida:", self.species_output_input)
        self.species_config_layout.addRow("Q(T) [K]:", self.species_temperatures_input)
        self.species_config_layout.addRow("TOP-K:", self.species_topk_input)
        self.species_config_layout.addRow(self.species_filters_button)
        left_layout.addWidget(self.species_config_box)

        self.species_actions_box = QGroupBox("Proceso de identificación")
        actions_layout = QVBoxLayout(self.species_actions_box)
        actions_layout.setContentsMargins(7, 8, 7, 7); actions_layout.setSpacing(4)
        self.species_run_button = QPushButton("Ejecutar identificación molecular")
        actions_layout.addWidget(self.species_run_button)
        # Aliases internos: la generación ahora se dispara desde Export Q(T)/Spectra.
        self.species_generate_qt_button = QPushButton("Generar Q(T)"); self.species_generate_qt_button.setVisible(False)
        self.species_generate_spectra_button = QPushButton("Generar espectros"); self.species_generate_spectra_button.setVisible(False)
        left_layout.addWidget(self.species_actions_box)

        self.species_exports_box = QGroupBox("Guardado y carpetas")
        exports_layout = QGridLayout(self.species_exports_box)
        exports_layout.setContentsMargins(7, 8, 7, 7); exports_layout.setHorizontalSpacing(5); exports_layout.setVerticalSpacing(4)
        self.species_save_label_input = QLineEdit()
        self.species_save_label_input.setPlaceholderText("Nombre de guardado (opcional)")
        self.species_save_label_input.setToolTip(
            "Prefijo opcional para los productos de M2. Si el nombre ya existe, CZSpec agrega _001, _002, etc., sin sobrescribir."
        )
        exports_layout.addWidget(self.species_save_label_input, 0, 0, 1, 2)
        self.species_export_tables_button = QPushButton("Exportar tablas")
        self.species_export_spectra_button = QPushButton("Exportar espectros")
        self.species_export_qt_button = QPushButton("Exportar Q(T)")
        self.species_open_tables_button = QPushButton("Tablas")
        self.species_open_plotly_button = QPushButton("Espectros")
        self.species_open_qt_button = QPushButton("Q(T)")
        self.species_open_figures_button = QPushButton("Figuras")
        self.species_open_general_button = QPushButton("Salida principal")
        exports_layout.addWidget(self.species_export_tables_button, 1, 0)
        exports_layout.addWidget(self.species_open_tables_button, 1, 1)
        exports_layout.addWidget(self.species_export_spectra_button, 2, 0)
        exports_layout.addWidget(self.species_open_plotly_button, 2, 1)
        exports_layout.addWidget(self.species_export_qt_button, 3, 0)
        exports_layout.addWidget(self.species_open_qt_button, 3, 1)
        exports_layout.addWidget(self.species_open_figures_button, 4, 0)
        exports_layout.addWidget(self.species_open_general_button, 4, 1)
        for _button in (self.species_export_tables_button, self.species_export_spectra_button, self.species_export_qt_button,
                        self.species_open_tables_button, self.species_open_plotly_button, self.species_open_qt_button,
                        self.species_open_figures_button, self.species_open_general_button):
            _button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        left_layout.addWidget(self.species_exports_box)

        # Compatibility aliases for code paths retained from older alpha builds.
        self.species_save_results_button = self.species_export_tables_button
        self.species_generate_plots_button = self.species_generate_spectra_button
        self.species_open_results_button = self.species_open_general_button

        self.species_generate_qt_button.setEnabled(False)
        self.species_generate_spectra_button.setEnabled(False)
        self.species_export_tables_button.setEnabled(False)
        self.species_export_qt_button.setEnabled(False)
        self.species_export_spectra_button.setEnabled(False)
        # Folder buttons stay available even before the first export.
        self.species_open_qt_button.setEnabled(True)
        self.species_open_plotly_button.setEnabled(True)

        self.species_logs_box = QGroupBox("Logs de M2")
        logs_layout = QVBoxLayout(self.species_logs_box)
        logs_layout.setContentsMargins(7, 8, 7, 7)
        self.species_log_area = QTextEdit(); self.species_log_area.setReadOnly(True)
        self.species_log_area.setMinimumHeight(75); self.species_log_area.setMaximumHeight(125)
        logs_layout.addWidget(self.species_log_area)
        left_layout.addWidget(self.species_logs_box)
        left_layout.addStretch(1)

        self.species_left_scroll = QScrollArea()
        self.species_left_scroll.setObjectName("sidePanelScroll")
        self.species_left_scroll.setWidgetResizable(True)
        self.species_left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.species_left_scroll.setMinimumWidth(325)
        self.species_left_scroll.setWidget(left_panel)
        splitter.addWidget(self.species_left_scroll)

        # ================================================================
        # Panel derecho · filtros, tablas y visualización
        # ================================================================
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 5, 5, 5); right_layout.setSpacing(5)

        self.species_search_box = QGroupBox("Búsqueda / filtro")
        search_layout = QVBoxLayout(self.species_search_box)
        search_layout.setContentsMargins(7, 8, 7, 7); search_layout.setSpacing(4)
        fields_row = QHBoxLayout(); fields_row.setSpacing(9)
        self.species_search_obs_id_cb = FilterCheckBox("ID de observación")
        self.species_search_name_cb = FilterCheckBox("Especie / transición")
        self.species_search_chemical_name_cb = FilterCheckBox("Nombre químico")
        self.species_search_species_id_cb = FilterCheckBox("ID de especie")
        self.species_search_moleculeTag_cb = FilterCheckBox("Etiqueta molecular")
        for widget in (self.species_search_obs_id_cb, self.species_search_name_cb, self.species_search_chemical_name_cb, self.species_search_species_id_cb, self.species_search_moleculeTag_cb):
            fields_row.addWidget(widget)
        fields_row.addStretch()
        controls_row = QHBoxLayout(); controls_row.setSpacing(5)
        self.species_search_input = QLineEdit(); self.species_search_input.setPlaceholderText("Ej.: 1-5; HCN; SO2")
        self.species_search_button = QPushButton("Buscar")
        self.species_clear_search_button = QPushButton("Limpiar")
        controls_row.addWidget(self.species_search_input, stretch=1); controls_row.addWidget(self.species_search_button); controls_row.addWidget(self.species_clear_search_button)
        search_layout.addLayout(fields_row); search_layout.addLayout(controls_row)
        right_layout.addWidget(self.species_search_box)

        species_header_row = QHBoxLayout(); species_header_row.setSpacing(5)
        self.species_tables_label = QLabel("Tablas")
        species_header_row.addWidget(self.species_tables_label); species_header_row.addStretch()
        # La vista con/sin leyenda pertenece a los visores, no al encabezado principal de M2.
        self.species_plot_view_combo = QComboBox()
        self.species_plot_view_combo.addItem("Con leyenda", "with_legend")
        self.species_plot_view_combo.addItem("Sin leyenda", "no_legend")
        self.species_plot_view_combo.setVisible(False)
        self.species_plot_table_button = QPushButton("Graficar tablas…")
        self.species_final_spectrum_button = QPushButton("Espectro final…")
        self.species_columns_button = QPushButton("Columnas…")
        self.species_plot_table_button.setMaximumWidth(145); self.species_final_spectrum_button.setMaximumWidth(135); self.species_columns_button.setMaximumWidth(105)
        self.species_final_spectrum_button.setEnabled(False)
        species_header_row.addWidget(self.species_plot_table_button)
        species_header_row.addWidget(self.species_final_spectrum_button)
        species_header_row.addWidget(self.species_columns_button)
        right_layout.addLayout(species_header_row)

        self.species_tables_splitter = QSplitter(Qt.Vertical)
        self.species_tables_splitter.setChildrenCollapsible(False)

        self.species_results_box = QGroupBox("Resultados principales")
        self.species_results_box.setProperty("role", "tablePanel")
        species_results_layout = QVBoxLayout(self.species_results_box); species_results_layout.setContentsMargins(4, 4, 4, 4)
        self.species_table = QTableWidget(); self.species_table.setProperty("czspecColumnProfile", "species_main")
        self.species_table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.species_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.species_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.species_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); self.species_table.horizontalHeader().setStretchLastSection(True)
        self.species_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        species_results_layout.addWidget(self.species_table, stretch=1)
        self.species_tables_splitter.addWidget(self.species_results_box)

        self.species_topk_box = QGroupBox("TOP-K")
        self.species_topk_box.setProperty("role", "tablePanel")
        species_topk_layout = QVBoxLayout(self.species_topk_box); species_topk_layout.setContentsMargins(4, 4, 4, 4)
        self.species_topk_table = QTableWidget(); self.species_topk_table.setProperty("czspecColumnProfile", "species_topk")
        self.species_topk_table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.species_topk_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.species_topk_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.species_topk_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); self.species_topk_table.horizontalHeader().setStretchLastSection(True)
        self.species_topk_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.species_topk_table.cellClicked.connect(self.on_species_topk_cell_clicked)
        species_topk_layout.addWidget(self.species_topk_table, stretch=1)
        self.species_tables_splitter.addWidget(self.species_topk_box)
        self.species_tables_splitter.setStretchFactor(0, 1); self.species_tables_splitter.setStretchFactor(1, 1)
        self.species_tables_splitter.setSizes([400, 400])
        right_layout.addWidget(self.species_tables_splitter, stretch=1)

        # Debounce expensive downstream M3/LTE refreshes when the user browses
        # TOP-K candidates quickly.  The M2 tables update immediately.
        self._species_selection_refresh_timer = QTimer(self)
        self._species_selection_refresh_timer.setSingleShot(True)
        self._species_selection_refresh_timer.setInterval(180)
        self._species_selection_refresh_timer.timeout.connect(self._refresh_species_selection_dependents)

        splitter.addWidget(right_panel)
        splitter.setSizes([345, 935]); splitter.setStretchFactor(0, 0); splitter.setStretchFactor(1, 1)

        # Conexiones M2
        self.species_load_button.clicked.connect(self.load_species_file)
        self.species_refresh_from_m1_button.clicked.connect(self.refresh_species_input_from_m1)
        self.species_spectrum_mode_combo.currentIndexChanged.connect(self._species_spectrum_mode_changed)
        self.species_load_spectrum_button.clicked.connect(self.load_species_spectrum_files)
        self.species_filters_button.clicked.connect(self.open_species_search_filters)
        self.species_run_button.clicked.connect(self.run_species_process)
        self.species_generate_qt_button.clicked.connect(self.generate_species_qt_products)
        self.species_generate_spectra_button.clicked.connect(self.generate_species_spectrum_products)
        self.species_export_tables_button.clicked.connect(self.export_species_tables)
        self.species_export_qt_button.clicked.connect(self.export_species_qt_products)
        self.species_export_spectra_button.clicked.connect(self.export_species_spectrum_products)
        self.species_open_general_button.clicked.connect(self.open_species_results_folder)
        self.species_open_tables_button.clicked.connect(self.open_species_tables_folder)
        self.species_open_plotly_button.clicked.connect(self.open_species_plotly_folder)
        self.species_open_qt_button.clicked.connect(self.open_species_qt_folder)
        self.species_open_figures_button.clicked.connect(self.open_species_figures_folder)
        self.species_search_button.clicked.connect(self.apply_species_filter)
        self.species_clear_search_button.clicked.connect(self.clear_species_filter)
        self.species_search_input.returnPressed.connect(self.apply_species_filter)
        self.species_columns_button.clicked.connect(self.open_species_columns_dialog)
        self.species_plot_table_button.clicked.connect(self.open_species_table_plot_dialog)
        self.species_final_spectrum_button.clicked.connect(self.open_species_final_spectrum)
        self._species_spectrum_mode_changed()

    def _build_lte_tab(self):
        self.lte_tab = QWidget()
        self.tabs.addTab(self.lte_tab, "4  Modelado espectral")

        layout = QVBoxLayout(self.lte_tab)
        intro = QLabel(
            "Construye el espectro sintético LTE global de la sesión: todas las bandas "
            "de M1, todas las transiciones elegidas en M2 y las soluciones físicas "
            "MOD o MTH de M3."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, stretch=1)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        left_layout.setSpacing(10)
        left_panel.setMinimumWidth(0)
        left_panel.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        source_box = QGroupBox("Datos y solución física")
        source_layout = QVBoxLayout(source_box)
        self.lte_source_label = QLabel("Carga y analiza un espectro en el módulo 1.")
        self.lte_source_label.setWordWrap(True)
        self.lte_refresh_button = QPushButton("Actualizar desde módulos 1–3")
        self.lte_refresh_button.setToolTip(
            "M1 aporta uno o varios espectros; M2 las identificaciones y M3 las soluciones MOD/MTH."
        )
        self.lte_species_combo = QComboBox(self.lte_tab)
        self.lte_species_combo.setToolTip(
            "Selector interno sincronizado con la transición elegida del módulo 3."
        )
        self.lte_species_combo.setVisible(False)
        self.lte_catalog_label = QLabel("Sin transiciones cargadas para la banda.")
        self.lte_catalog_label.setWordWrap(True)

        self.lte_method_group = QButtonGroup(self)
        self.lte_method_group.setExclusive(True)
        self.lte_mod_method_button = QPushButton("MOD")
        self.lte_mth_method_button = QPushButton("MTH")
        for method_button in (self.lte_mod_method_button, self.lte_mth_method_button):
            method_button.setCheckable(True)
            method_button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
            self.lte_method_group.addButton(method_button)
        self.lte_solution_species_combo = QComboBox()
        self.lte_solution_species_combo.setToolTip(
            "Transiciones con resultados del método elegido, ordenadas por frecuencia creciente."
        )
        self.lte_solution_combo = QComboBox()
        self.lte_solution_combo.setToolTip(
            "Soluciones de la transición elegida, ordenadas por temperatura de excitación."
        )
        for combo in (
            self.lte_species_combo,
            self.lte_solution_species_combo,
            self.lte_solution_combo,
        ):
            combo.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            combo.setMinimumContentsLength(10)
            combo.setMinimumWidth(0)
            combo.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.lte_global_tex_combo = QComboBox()
        self.lte_global_tex_combo.setToolTip(
            "Temperatura común usada para reunir una componente inicial por especie."
        )
        self.lte_global_tex_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self.lte_build_global_button = QPushButton("Preparar modelo global de la sesión")
        self.lte_build_global_button.setEnabled(False)
        self.lte_build_global_button.setToolTip(
            "Reúne todas las especies y transiciones compatibles con el método y Tₑₓ elegidos."
        )
        self.lte_apply_solution_button = QPushButton("Añadir componente individual")
        self.lte_apply_solution_button.setEnabled(False)
        self.lte_solution_label = QLabel(
            "Ejecuta MOD o MTH en el módulo 3 y aplica una de sus soluciones."
        )
        self.lte_solution_label.setWordWrap(True)
        self.lte_query_button = QPushButton("Consultar transiciones de la banda")
        self.lte_query_button.setEnabled(False)
        source_layout.addWidget(self.lte_source_label)
        source_layout.addWidget(self.lte_refresh_button)
        source_layout.addWidget(QLabel("Solución física de M3:"))
        method_layout = QHBoxLayout()
        method_layout.setSpacing(7)
        method_layout.addWidget(self.lte_mod_method_button)
        method_layout.addWidget(self.lte_mth_method_button)
        source_layout.addLayout(method_layout)
        source_layout.addWidget(QLabel("Temperatura común del modelo:"))
        source_layout.addWidget(self.lte_global_tex_combo)
        source_layout.addWidget(self.lte_build_global_button)
        self.lte_setup_button = QPushButton("Condiciones y componente individual…")
        self.lte_setup_button.setToolTip(
            "Abre los parámetros observacionales comunes y la adición opcional "
            "de una especie concreta, sin ocupar espacio permanente en M4."
        )
        source_layout.addWidget(self.lte_setup_button)
        left_layout.addWidget(source_box)

        components_box = QGroupBox("Componentes del modelo")
        components_layout = QVBoxLayout(components_box)
        self.lte_components_summary_label = QLabel(
            "Sin componentes. Un componente representa una especie con una "
            "solución física; puede producir varias transiciones."
        )
        self.lte_components_summary_label.setWordWrap(True)
        components_layout.addWidget(self.lte_components_summary_label)
        self.lte_components_list = QListWidget()
        self.lte_components_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lte_components_list.setMinimumHeight(92)
        self.lte_components_list.setToolTip(
            "Cada componente conserva su especie, solución MOD/MTH y transiciones. "
            "Los componentes se suman en temperatura, sin absorción mutua."
        )
        self.lte_components_list.setVisible(False)
        self.lte_remove_component_button = QPushButton("Quitar")
        self.lte_clear_components_button = QPushButton("Vaciar")
        self.lte_edit_components_button = QPushButton("Gestionar componentes…")
        self.lte_remove_component_button.setEnabled(False)
        self.lte_clear_components_button.setEnabled(False)
        self.lte_edit_components_button.setEnabled(False)
        self.lte_remove_component_button.setVisible(False)
        components_layout.addWidget(self.lte_edit_components_button)
        components_layout.addWidget(self.lte_clear_components_button)
        left_layout.addWidget(components_box)

        self.lte_column_density_input = QLineEdit()
        self.lte_column_density_input.setPlaceholderText("Pendiente de MOD/MTH")
        self.lte_column_density_input.setReadOnly(True)
        self.lte_column_density_input.setToolTip(
            "Densidad de columna observacional heredada obligatoriamente del módulo 3."
        )

        self.lte_tex_input = QDoubleSpinBox()
        self.lte_tex_input.setRange(0.0, 2000.0)
        self.lte_tex_input.setDecimals(2)
        self.lte_tex_input.setSingleStep(1.0)
        self.lte_tex_input.setValue(0.0)
        self.lte_tex_input.setSuffix(" K")
        self.lte_tex_input.setSpecialValueText("Pendiente de M3")
        self.lte_tex_input.setReadOnly(True)

        self.lte_linewidth_input = QDoubleSpinBox()
        self.lte_linewidth_input.setRange(0.0, 500.0)
        self.lte_linewidth_input.setDecimals(3)
        self.lte_linewidth_input.setSingleStep(0.1)
        self.lte_linewidth_input.setValue(0.0)
        self.lte_linewidth_input.setSuffix(" km/s")
        self.lte_linewidth_input.setSpecialValueText("Pendiente de M3")
        self.lte_linewidth_input.setReadOnly(True)
        self.lte_linewidth_input.setToolTip(
            "FWHM del componente. La heredada de MTH proviene del ajuste observado y ya "
            "incluye la respuesta instrumental del espectro procesado."
        )

        self.lte_velocity_input = QDoubleSpinBox()
        self.lte_velocity_input.setRange(-1000.0, 1000.0)
        self.lte_velocity_input.setDecimals(3)
        self.lte_velocity_input.setSingleStep(0.1)
        self.lte_velocity_input.setValue(0.0)
        self.lte_velocity_input.setSuffix(" km/s")
        self.lte_velocity_input.setReadOnly(True)
        self.lte_velocity_input.setToolTip(
            "Desplazamiento relativo: un valor positivo mueve las líneas a frecuencias menores."
        )

        self.lte_source_size_input = QDoubleSpinBox()
        self.lte_source_size_input.setRange(0.0, 100000.0)
        self.lte_source_size_input.setDecimals(2)
        self.lte_source_size_input.setValue(0.0)
        self.lte_source_size_input.setSuffix(" ″")
        self.lte_source_size_input.setSpecialValueText("Extendida")
        self.lte_source_size_input.setToolTip(
            "Con 'Extendida' se adopta η_bf=1. El HPBW solo produce dilución si se indica "
            "un tamaño angular finito para la fuente."
        )

        self.lte_telescope_combo = QComboBox()
        self.lte_telescope_combo.addItem("IRAM 30 m · automático", "iram30m")
        self.lte_telescope_combo.addItem("Manual / otro telescopio", "manual")
        self.lte_telescope_combo.setToolTip(
            "Para IRAM 30 m se calcula HPBW = 2460 / ν(GHz), no un valor fijo por banda."
        )

        self.lte_beam_size_input = QDoubleSpinBox()
        self.lte_beam_size_input.setRange(0.0, 100000.0)
        self.lte_beam_size_input.setDecimals(2)
        self.lte_beam_size_input.setValue(0.0)
        self.lte_beam_size_input.setSuffix(" ″")
        self.lte_beam_size_input.setSpecialValueText("Sin dilución")
        self.lte_beam_size_input.setEnabled(False)

        self.lte_background_input = QDoubleSpinBox()
        self.lte_background_input.setRange(0.0, 1000.0)
        self.lte_background_input.setDecimals(3)
        self.lte_background_input.setValue(2.725)
        self.lte_background_input.setSuffix(" K")

        self.lte_resolution_input = QDoubleSpinBox()
        self.lte_resolution_input.setRange(0.0, 10000.0)
        self.lte_resolution_input.setDecimals(6)
        self.lte_resolution_input.setValue(0.0)
        self.lte_resolution_input.setSuffix(" MHz")
        self.lte_resolution_input.setSpecialValueText("Sin convolución")
        self.lte_resolution_input.setToolTip(
            "FWHM efectivo de la respuesta instrumental después de SMOOTH. "
            "No se deduce del espaciado del archivo DAT; introdúcelo solo si lo conoces."
        )

        self.lte_channel_spacing_label = QLabel("Pendiente de cargar el espectro")
        self.lte_channel_spacing_label.setWordWrap(True)
        self.lte_channel_spacing_label.setToolTip(
            "Muestreo medido en el archivo. No equivale necesariamente al FWHM efectivo."
        )

        self.lte_q_label = QLabel("Q(T_ex): pendiente")
        self.lte_q_label.setWordWrap(True)

        self.lte_setup_dialog = QDialog(self)
        self.lte_setup_dialog.setWindowTitle("Condiciones del modelo LTE — CZSpec")
        self.lte_setup_dialog.setModal(False)
        self.lte_setup_dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.lte_setup_dialog.resize(620, 610)
        setup_root = QVBoxLayout(self.lte_setup_dialog)
        setup_intro = QLabel(
            "Estos valores se aplican al preparar nuevas componentes. Las componentes "
            "ya creadas se editan desde «Gestionar componentes»."
        )
        setup_intro.setWordWrap(True)
        setup_root.addWidget(setup_intro)
        setup_tabs = QTabWidget()

        conditions_tab = QWidget()
        params_layout = QFormLayout(conditions_tab)
        params_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        params_layout.setRowWrapPolicy(QFormLayout.WrapLongRows)
        params_layout.addRow("Tamaño de fuente:", self.lte_source_size_input)
        params_layout.addRow("Telescopio / haz:", self.lte_telescope_combo)
        params_layout.addRow("HPBW del haz:", self.lte_beam_size_input)
        params_layout.addRow("Temperatura de fondo:", self.lte_background_input)
        params_layout.addRow("Resolución instrumental:", self.lte_resolution_input)
        params_layout.addRow("Espaciado de canales:", self.lte_channel_spacing_label)
        self.lte_q_label.setText(
            "Q(Tₑₓ) se calcula automáticamente para cada especie al generar el modelo."
        )
        params_layout.addRow("Función de partición:", self.lte_q_label)
        setup_tabs.addTab(conditions_tab, "Condiciones comunes")

        individual_tab = QWidget()
        individual_layout = QVBoxLayout(individual_tab)
        individual_help = QLabel(
            "Opcional: añade una sola especie/solución de M3. El modelo global se "
            "prepara directamente desde el panel principal."
        )
        individual_help.setWordWrap(True)
        individual_layout.addWidget(individual_help)
        individual_layout.addWidget(QLabel("Especie / transición de origen:"))
        individual_layout.addWidget(self.lte_solution_species_combo)
        individual_layout.addWidget(QLabel("Solución por Tₑₓ:"))
        individual_layout.addWidget(self.lte_solution_combo)
        inherited_form = QFormLayout()
        inherited_form.addRow("N total heredada:", self.lte_column_density_input)
        inherited_form.addRow("Tₑₓ heredada:", self.lte_tex_input)
        inherited_form.addRow("FWHM heredada:", self.lte_linewidth_input)
        inherited_form.addRow("Δv heredado:", self.lte_velocity_input)
        individual_layout.addLayout(inherited_form)
        individual_layout.addWidget(self.lte_apply_solution_button)
        individual_layout.addWidget(self.lte_solution_label)
        individual_layout.addWidget(self.lte_catalog_label)
        individual_layout.addWidget(self.lte_query_button)
        individual_layout.addStretch()
        setup_tabs.addTab(individual_tab, "Componente individual")
        setup_root.addWidget(setup_tabs, stretch=1)
        setup_footer = QHBoxLayout()
        setup_footer.addStretch()
        setup_close = QPushButton("Cerrar")
        setup_close.clicked.connect(self.lte_setup_dialog.hide)
        setup_footer.addWidget(setup_close)
        setup_root.addLayout(setup_footer)

        actions_box = QGroupBox("Modelo y productos")
        actions_layout = QVBoxLayout(actions_box)
        self.lte_run_button = QPushButton("Generar espectro LTE global")
        self.lte_run_button.setEnabled(False)
        self.lte_export_button = QPushButton("Exportar modelo CSV")
        self.lte_export_button.setEnabled(False)
        actions_layout.addWidget(self.lte_run_button)
        actions_layout.addWidget(self.lte_export_button)
        left_layout.addWidget(actions_box)

        refinement_box = QGroupBox("Ajuste automático del modelo (opcional)")
        refinement_layout = QVBoxLayout(refinement_box)
        refinement_help = QLabel(
            "No añade componentes: optimiza las ya preparadas. Parte de la solución "
            "física de M3 y mantiene Tₑₓ fija. En una sesión "
            "de una sola banda puede minimizar el residual ajustando únicamente "
            "N, FWHM y/o Δv; M3 siempre se conserva como referencia."
        )
        refinement_help.setWordWrap(True)
        refinement_layout.addWidget(refinement_help)
        refinement_checks = QHBoxLayout()
        self.lte_fit_n_checkbox = QCheckBox("N")
        self.lte_fit_width_checkbox = QCheckBox("FWHM")
        self.lte_fit_velocity_checkbox = QCheckBox("Δv")
        self.lte_fit_n_checkbox.setChecked(True)
        self.lte_fit_width_checkbox.setChecked(True)
        self.lte_fit_velocity_checkbox.setChecked(True)
        refinement_checks.addWidget(self.lte_fit_n_checkbox)
        refinement_checks.addWidget(self.lte_fit_width_checkbox)
        refinement_checks.addWidget(self.lte_fit_velocity_checkbox)
        refinement_layout.addLayout(refinement_checks)
        self.lte_noise_input = QDoubleSpinBox()
        self.lte_noise_input.setRange(0.0, 100000.0)
        self.lte_noise_input.setDecimals(6)
        self.lte_noise_input.setSpecialValueText("Sin σ conocida")
        self.lte_noise_input.setSuffix(" K")
        refinement_layout.addWidget(QLabel("RMS de ruido para χ² (opcional):"))
        refinement_layout.addWidget(self.lte_noise_input)
        self.lte_refine_button = QPushButton("Ajustar N, FWHM y Δv (una banda)")
        self.lte_refine_button.setEnabled(False)
        refinement_layout.addWidget(self.lte_refine_button)
        left_layout.addWidget(refinement_box)

        folders_box = QGroupBox("Carpetas de salida")
        folders_layout = QGridLayout(folders_box)
        folders_layout.setHorizontalSpacing(8)
        folders_layout.setVerticalSpacing(8)
        self.lte_open_folder_button = QPushButton("Guardado general")
        self.lte_open_graphics_button = QPushButton("Gráficos")
        self.lte_open_tables_button = QPushButton("Tablas")
        self.lte_open_images_button = QPushButton("Imágenes")
        folders_layout.addWidget(self.lte_open_folder_button, 0, 0)
        folders_layout.addWidget(self.lte_open_graphics_button, 0, 1)
        folders_layout.addWidget(self.lte_open_tables_button, 1, 0)
        folders_layout.addWidget(self.lte_open_images_button, 1, 1)
        left_layout.addWidget(folders_box)

        nonlte_box = QGroupBox("No-LTE · RADEX/LAMDA")
        nonlte_layout = QVBoxLayout(nonlte_box)
        nonlte_text = QLabel(
            "Resuelve las poblaciones colisionales de las componentes de M3. "
            "N, FWHM y Δv se heredan; Tkin, densidades y archivos LAMDA se "
            "documentan explícitamente. Tₑₓ y τ son resultados por transición."
        )
        nonlte_text.setWordWrap(True)
        self.nonlte_config_button = QPushButton("Configurar LAMDA y colisionadores…")
        self.nonlte_backend_label = QLabel()
        self.nonlte_backend_label.setWordWrap(True)
        self.nonlte_backend_button = QPushButton("Instalar backend no-LTE…")
        self.nonlte_backend_button.setToolTip(
            "Instala pythonradex y sus dependencias en el entorno estable de CZSpec."
        )
        self.nonlte_run_button = QPushButton("Generar modelo no-LTE global")
        self.nonlte_export_button = QPushButton("Exportar modelo no-LTE")
        self.nonlte_run_button.setEnabled(False)
        self.nonlte_export_button.setEnabled(False)
        nonlte_layout.addWidget(nonlte_text)
        nonlte_layout.addWidget(self.nonlte_backend_label)
        nonlte_layout.addWidget(self.nonlte_backend_button)
        nonlte_layout.addWidget(self.nonlte_config_button)
        nonlte_layout.addWidget(self.nonlte_run_button)
        nonlte_layout.addWidget(self.nonlte_export_button)
        left_layout.addWidget(nonlte_box)
        left_layout.addStretch()

        left_scroll = QScrollArea()
        left_scroll.setObjectName("sidePanelScroll")
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setMinimumWidth(305)
        left_scroll.setMaximumWidth(365)
        left_scroll.setWidget(left_panel)
        splitter.addWidget(left_scroll)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        plot_box = QGroupBox("Espectro observado, modelo y residuales")
        plot_layout = QVBoxLayout(plot_box)

        plot_toolbar = QHBoxLayout()
        self.lte_band_combo = QComboBox()
        self.lte_band_combo.setMinimumContentsLength(18)
        self.lte_band_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.lte_band_combo.setToolTip(
            "Elige la banda que se muestra. El modelo global sigue usando todas las bandas."
        )
        plot_toolbar.addWidget(QLabel("Banda visible:"))
        plot_toolbar.addWidget(self.lte_band_combo)
        self.lte_view_observed_button = QPushButton("Ver observado")
        self.lte_view_observed_button.setEnabled(False)
        self.lte_view_clean_button = QPushButton("Ver modelo limpio")
        self.lte_view_clean_button.setEnabled(False)
        self.lte_view_comparison_button = QPushButton("Ver comparación")
        self.lte_view_comparison_button.setEnabled(False)
        self.lte_save_image_button = QPushButton("Guardar imagen")
        self.lte_save_image_button.setEnabled(False)
        self.lte_style_button = QPushButton("Estilos de sesión…")
        self.lte_style_button.setToolTip(
            "Reutiliza los colores, grosores y patrones configurables para los espectros de M1."
        )
        self.lte_fullscreen_button = QPushButton("Pantalla completa")
        self.lte_fullscreen_button.setEnabled(False)
        self.lte_diagnostics_button = QPushButton("Diagnóstico…")
        self.lte_diagnostics_button.setEnabled(False)
        self.lte_diagnostics_button.setToolTip(
            "Abre en otra ventana todas las transiciones y sus magnitudes LTE."
        )
        self.lte_view_clean_button.setToolTip(
            "Superpone observado y modelo total, sin residuales ni leyenda lateral."
        )
        self.lte_view_comparison_button.setToolTip(
            "Muestra observado, modelo, residuales y componentes interactivos."
        )
        plot_toolbar.addWidget(self.lte_view_observed_button)
        plot_toolbar.addWidget(self.lte_view_clean_button)
        plot_toolbar.addWidget(self.lte_view_comparison_button)
        plot_toolbar.addWidget(self.lte_save_image_button)
        plot_toolbar.addWidget(self.lte_style_button)
        plot_toolbar.addWidget(self.lte_diagnostics_button)
        plot_toolbar.addStretch()
        plot_toolbar.addWidget(self.lte_fullscreen_button)
        plot_layout.addLayout(plot_toolbar)

        self.lte_interpretation_label = QLabel(
            "Cada banda conserva el estilo de su espectro observado. Naranja: modelo LTE "
            "global de todas las especies activas. Azul punteado: observado − modelo; "
            "las contribuciones individuales pueden activarse desde la leyenda."
        )
        self.lte_interpretation_label.setWordWrap(True)
        plot_layout.addWidget(self.lte_interpretation_label)

        self.lte_metrics_label = QLabel("Métricas: genera un modelo para evaluarlo.")
        self.lte_metrics_label.setWordWrap(True)
        self.lte_metrics_label.setStyleSheet("color: #52627A;")
        plot_layout.addWidget(self.lte_metrics_label)

        self.lte_plot_stack = QStackedWidget()
        self.lte_plot_stack.setMinimumHeight(255)
        self.lte_plot_placeholder = QLabel(
            "Genera o selecciona un espectro para iniciar la visualización LTE."
        )
        self.lte_plot_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lte_plot_placeholder.setStyleSheet(
            "color: #52627A; font-size: 16px; background: #FFFFFF;"
        )
        self.lte_plot_stack.addWidget(self.lte_plot_placeholder)
        self.lte_plot_view = None
        plot_layout.addWidget(self.lte_plot_stack)
        right_layout.addWidget(plot_box, stretch=1)

        self.lte_diagnostics_dialog = LTEDiagnosticsDialog(self)
        self.lte_diagnostics_table = self.lte_diagnostics_dialog.table

        self.lte_log_area = QTextEdit()
        self.lte_log_area.setReadOnly(True)
        self.lte_log_area.setMaximumHeight(78)
        self.lte_log_area.setPlaceholderText("Aquí se documentarán Q(T), dilución y líneas omitidas.")
        right_layout.addWidget(self.lte_log_area)

        splitter.addWidget(right_panel)
        splitter.setSizes([300, 1080])

        self.lte_refresh_button.clicked.connect(self.refresh_lte_inputs)
        self.lte_setup_button.clicked.connect(self.open_lte_setup_dialog)
        self.lte_mod_method_button.clicked.connect(
            lambda _checked=False: self.set_lte_solution_method("MOD")
        )
        self.lte_mth_method_button.clicked.connect(
            lambda _checked=False: self.set_lte_solution_method("MTH")
        )
        self.lte_solution_species_combo.currentIndexChanged.connect(
            self.on_lte_solution_species_changed
        )
        self.lte_solution_combo.currentIndexChanged.connect(
            self.on_lte_solution_choice_changed
        )
        self.lte_global_tex_combo.currentIndexChanged.connect(
            lambda *_: self.lte_build_global_button.setEnabled(
                self.lte_global_tex_combo.currentData() is not None
                and self.lte_selected_method in {"MOD", "MTH"}
            )
        )
        self.lte_build_global_button.clicked.connect(self.build_global_lte_components)
        self.lte_apply_solution_button.clicked.connect(self.apply_lte_physical_solution)
        self.lte_components_list.itemSelectionChanged.connect(
            lambda: self.lte_remove_component_button.setEnabled(
                self.lte_components_list.currentRow() >= 0
            )
        )
        self.lte_remove_component_button.clicked.connect(self.remove_lte_component)
        self.lte_clear_components_button.clicked.connect(self.clear_lte_components)
        self.lte_edit_components_button.clicked.connect(self.open_lte_component_workbench)
        self.lte_telescope_combo.currentIndexChanged.connect(self.update_lte_beam_preset)
        self.lte_query_button.clicked.connect(self.query_lte_catalog)
        self.lte_run_button.clicked.connect(self.run_lte_model)
        self.lte_refine_button.clicked.connect(self.refine_lte_model)
        self.lte_export_button.clicked.connect(self.export_lte_model)
        self.lte_view_observed_button.clicked.connect(self.show_lte_observed_view)
        self.lte_view_clean_button.clicked.connect(self.show_lte_clean_view)
        self.lte_view_comparison_button.clicked.connect(self.show_lte_comparison_view)
        self.lte_save_image_button.clicked.connect(self.save_lte_image)
        self.lte_style_button.clicked.connect(self.configure_lte_session_styles)
        self.lte_band_combo.currentIndexChanged.connect(self.on_lte_band_changed)
        self.lte_diagnostics_button.clicked.connect(self.open_lte_diagnostics)
        self.lte_fullscreen_button.clicked.connect(self.open_lte_fullscreen_plot)
        self.lte_open_folder_button.clicked.connect(
            lambda: self._open_folder(LTE_MODEL_OUTPUT_DIR)
        )
        self.lte_open_graphics_button.clicked.connect(
            lambda: self._open_folder(LTE_GRAPHICS_DIR)
        )
        self.lte_open_tables_button.clicked.connect(
            lambda: self._open_folder(LTE_TABLES_DIR)
        )
        self.lte_open_images_button.clicked.connect(
            lambda: self._open_folder(LTE_IMAGES_DIR)
        )
        self.nonlte_config_button.clicked.connect(self.open_nonlte_dialog)
        self.nonlte_backend_button.clicked.connect(self.install_nonlte_backend)
        self.nonlte_run_button.clicked.connect(
            lambda _checked=False: self.run_nonlte_model()
        )
        self.nonlte_export_button.clicked.connect(self.export_nonlte_model)

    def _build_column_density_tab(self):
        self.sanhueza_tau_max_input = QLineEdit()
        self.sanhueza_tau_max_input.setPlaceholderText("τ máximo (opcional)")
        self.sanhueza_tau_max_input.setMinimumWidth(220)
        self.column_density_tab = QWidget()
        self.tabs.addTab(self.column_density_tab, "3  Densidad de columna")

        layout = QVBoxLayout(self.column_density_tab)
        

        self.column_density_info_label = QLabel(
            "Esta pestaña usará como entrada la selección final del Buscador de especies."
        )
        self.column_density_info_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.column_density_info_label)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, stretch=1)

        # =========================
        # Panel izquierdo
        # =========================
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        left_layout.setSpacing(7)
        left_panel.setMinimumWidth(315)

        self.column_density_source_box = QGroupBox("Fuente de datos")
        source_layout = QVBoxLayout(self.column_density_source_box)
        source_layout.setContentsMargins(8, 8, 8, 8); source_layout.setSpacing(6)

        self.column_density_source_label = QLabel("Sin datos disponibles desde M2")
        self.column_density_source_label.setWordWrap(True)
        self.column_density_source_label.setStyleSheet("font-size:11px;color:#52627A;")

        source_buttons = QHBoxLayout(); source_buttons.setSpacing(6)
        self.column_density_load_button = QPushButton("Cargar datos")
        self.column_density_load_button.clicked.connect(self.load_column_density_file)
        self.column_density_refresh_button = QPushButton("Actualizar desde M2")
        self.column_density_refresh_button.clicked.connect(self.refresh_column_density_source_preview)
        source_buttons.addWidget(self.column_density_load_button)
        source_buttons.addWidget(self.column_density_refresh_button)
        source_layout.addWidget(self.column_density_source_label)
        source_layout.addLayout(source_buttons)

        # Legacy LaTeX actions remain callable from code but no longer occupy
        # permanent space in the scientific input panel.
        self.column_density_save_latex_button = QPushButton(); self.column_density_save_latex_button.setVisible(False)
        self.column_density_open_latex_button = QPushButton(); self.column_density_open_latex_button.setVisible(False)
        self.column_density_save_latex_button.clicked.connect(self.save_column_density_latex_results)
        self.column_density_open_latex_button.clicked.connect(self.open_column_density_latex_folder)
        left_layout.addWidget(self.column_density_source_box)

        self.vasy_box = QGroupBox("Método ópticamente delgado (MOD)")
        vasy_layout = QVBoxLayout(self.vasy_box); vasy_layout.setContentsMargins(8,8,8,8); vasy_layout.setSpacing(5)
        self.vasyunina_temp_label = QLabel("Temperaturas de excitación [K]:")
        self.vasyunina_temperatures_input = QLineEdit()
        self.vasyunina_temperatures_input.setPlaceholderText("Ej. 10, 28")
        self.vasyunina_run_button = QPushButton("Ejecutar MOD")
        self.vasyunina_run_button.setEnabled(False)
        self.vasyunina_run_button.clicked.connect(self.run_vasyunina_process)
        vasy_layout.addWidget(self.vasyunina_temp_label)
        vasy_layout.addWidget(self.vasyunina_temperatures_input)
        vasy_layout.addWidget(self.vasyunina_run_button)
        # Hidden compatibility actions; exporting is centralized in Save and folders.
        self.save_vasyunina_button = QPushButton(); self.save_vasyunina_button.setVisible(False); self.save_vasyunina_button.setEnabled(False)
        self.save_vasyunina_button.clicked.connect(self.save_vasyunina_results)
        self.open_vasyunina_button = QPushButton(); self.open_vasyunina_button.setVisible(False); self.open_vasyunina_button.clicked.connect(self.open_vasyunina_folder)
        left_layout.addWidget(self.vasy_box)

        self.sanh_box = QGroupBox("Método de transiciones hiperfinas (MTH)")
        sanh_layout = QGridLayout(self.sanh_box); sanh_layout.setContentsMargins(8,8,8,8); sanh_layout.setHorizontalSpacing(7); sanh_layout.setVerticalSpacing(5)
        self.sanhueza_tex_label = QLabel("Temperaturas de excitación [K]:")
        self.sanhueza_tex_input = QLineEdit(); self.sanhueza_tex_input.setPlaceholderText("Ej. 10, 28")
        self.sanhueza_ratios_label = QLabel("Razones isotópicas:")
        self.sanhueza_ratios_button = QPushButton("Razones isotópicas")
        self.sanhueza_ratios_button.clicked.connect(self.open_sanhueza_isotopic_ratios_dialog)
        self.sanhueza_ratios_summary_label = QLabel(self._format_sanhueza_isotopic_ratios_summary())
        self.sanhueza_ratios_summary_label.setWordWrap(True); self.sanhueza_ratios_summary_label.setStyleSheet("font-size:10px;color:#64748B;")
        self.sanhueza_r_mode_checkbox = FilterCheckBox("Usar aproximación de r")
        self.sanhueza_r_mode_checkbox.setChecked(False)
        self.sanhueza_r_mode_checkbox.setToolTip(
            "Haz clic para activar/desactivar la aproximación de r. Azul = activa."
        )
        self.sanhueza_tau_label = QLabel("τ máximo (opcional):")
        self.sanhueza_tau_max_input.setMinimumWidth(0); self.sanhueza_tau_max_input.setPlaceholderText("τ máx.")
        self.sanhueza_run_button = QPushButton("Ejecutar MTH"); self.sanhueza_run_button.setEnabled(False); self.sanhueza_run_button.clicked.connect(self.run_sanhueza_process)
        sanh_layout.addWidget(self.sanhueza_tex_label,0,0); sanh_layout.addWidget(self.sanhueza_tex_input,0,1)
        sanh_layout.addWidget(self.sanhueza_ratios_label,1,0); sanh_layout.addWidget(self.sanhueza_ratios_button,1,1)
        sanh_layout.addWidget(self.sanhueza_ratios_summary_label,2,0,1,2)
        sanh_layout.addWidget(self.sanhueza_r_mode_checkbox,3,0,1,2)
        sanh_layout.addWidget(self.sanhueza_tau_label,4,0); sanh_layout.addWidget(self.sanhueza_tau_max_input,4,1)
        sanh_layout.addWidget(self.sanhueza_run_button,5,0,1,2)
        self.save_sanhueza_button = QPushButton(); self.save_sanhueza_button.setVisible(False); self.save_sanhueza_button.setEnabled(False); self.save_sanhueza_button.clicked.connect(self.save_sanhueza_results)
        self.open_sanhueza_button = QPushButton(); self.open_sanhueza_button.setVisible(False); self.open_sanhueza_button.clicked.connect(self.open_sanhueza_folder)
        left_layout.addWidget(self.sanh_box)

        self.column_density_folders_box = QGroupBox("Guardado y carpetas")
        folders_layout = QGridLayout(self.column_density_folders_box); folders_layout.setHorizontalSpacing(7); folders_layout.setVerticalSpacing(6)
        self.column_density_save_label_input = QLineEdit()
        self.column_density_save_label_input.setPlaceholderText("Nombre de guardado (opcional)")
        self.column_density_save_label_input.setToolTip(
            "Prefijo opcional para los productos de M3. Si el nombre ya existe, CZSpec agrega _001, _002, etc., sin sobrescribir."
        )
        folders_layout.addWidget(self.column_density_save_label_input,0,0,1,2)
        self.column_density_export_tables_button = QPushButton("Exportar tablas")
        self.column_open_tables_button = QPushButton("Tablas")
        self.column_density_export_spectra_button = QPushButton("Exportar espectros")
        self.column_open_spectra_button = QPushButton("Espectros")
        self.column_open_images_button = QPushButton("Figuras")
        self.column_open_general_button = QPushButton("Salida principal")
        self.column_open_graphics_button = QPushButton(); self.column_open_graphics_button.setVisible(False)
        folders_layout.addWidget(self.column_density_export_tables_button,1,0)
        folders_layout.addWidget(self.column_open_tables_button,1,1)
        folders_layout.addWidget(self.column_density_export_spectra_button,2,0)
        folders_layout.addWidget(self.column_open_spectra_button,2,1)
        folders_layout.addWidget(self.column_open_images_button,3,0)
        folders_layout.addWidget(self.column_open_general_button,3,1)
        self.column_density_export_tables_button.clicked.connect(self.export_column_density_tables)
        self.column_density_export_spectra_button.clicked.connect(self.export_column_density_spectra)
        self.column_open_general_button.clicked.connect(lambda: self._open_folder(COLUMN_DENSITY_OUTPUT_DIR))
        self.column_open_tables_button.clicked.connect(lambda: self._open_folder(COLUMN_DENSITY_TABLES_DIR))
        self.column_open_spectra_button.clicked.connect(lambda: self._open_folder(COLUMN_DENSITY_GRAPHICS_DIR / "spectra"))
        self.column_open_images_button.clicked.connect(lambda: self._open_folder(COLUMN_DENSITY_IMAGES_DIR))
        left_layout.addWidget(self.column_density_folders_box)

        self.column_density_logs_box = QGroupBox("Logs de M3")
        logs_layout = QVBoxLayout(self.column_density_logs_box); logs_layout.setContentsMargins(6,6,6,6)
        self.column_density_log_area = QTextEdit(); self.column_density_log_area.setReadOnly(True); self.column_density_log_area.setMaximumHeight(125)
        logs_layout.addWidget(self.column_density_log_area)
        left_layout.addWidget(self.column_density_logs_box)

        left_layout.addStretch()

        left_scroll = QScrollArea()
        left_scroll.setObjectName("sidePanelScroll")
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setMinimumWidth(315)
        left_scroll.setWidget(left_panel)
        splitter.addWidget(left_scroll)

        # =========================
        # Panel derecho
        # =========================
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.column_density_search_box = QGroupBox("Búsqueda / filtro")
        search_layout = QVBoxLayout(self.column_density_search_box)

        cd_fields_row = QHBoxLayout()
        cd_fields_row.setSpacing(14)
        self.cd_search_obs_id_cb = FilterCheckBox("ID de observación")
        self.cd_search_name_cb = FilterCheckBox("Especie / transición")
        self.cd_search_chemical_name_cb = FilterCheckBox("Nombre químico")
        self.cd_search_species_id_cb = FilterCheckBox("ID de especie")
        self.cd_search_moleculeTag_cb = FilterCheckBox("Etiqueta molecular")

        cd_fields_row.addWidget(self.cd_search_obs_id_cb)
        cd_fields_row.addWidget(self.cd_search_name_cb)
        cd_fields_row.addWidget(self.cd_search_chemical_name_cb)
        cd_fields_row.addWidget(self.cd_search_species_id_cb)
        cd_fields_row.addWidget(self.cd_search_moleculeTag_cb)
        cd_fields_row.addStretch()

        cd_controls_row = QHBoxLayout()
        cd_controls_row.setSpacing(8)
        self.cd_search_input = QLineEdit()
        self.cd_search_input.setPlaceholderText("¿Qué buscas?")
        self.cd_search_button = QPushButton("Buscar")
        self.cd_clear_search_button = QPushButton("Limpiar búsqueda")

        cd_controls_row.addWidget(self.cd_search_input)
        cd_controls_row.addWidget(self.cd_search_button)
        cd_controls_row.addWidget(self.cd_clear_search_button)

        search_layout.addLayout(cd_fields_row)
        search_layout.addLayout(cd_controls_row)

        right_layout.addWidget(self.column_density_search_box)

        cd_header_row = QHBoxLayout()
        self.column_density_tables_label = QLabel("Tablas")
        cd_header_row.addWidget(self.column_density_tables_label)
        cd_header_row.addStretch()

        self.column_density_final_spectrum_button = QPushButton("Espectro final...")
        self.column_density_final_spectrum_button.setMaximumWidth(140)
        self.column_density_final_spectrum_button.setEnabled(False)
        self.column_density_columns_button = QPushButton("Columnas...")
        self.column_density_columns_button.setMaximumWidth(110)
        self.column_density_plot_table_button = QPushButton("Graficar tablas...")
        self.column_density_plot_table_button.setMaximumWidth(150)
        cd_header_row.addWidget(self.column_density_plot_table_button)
        cd_header_row.addWidget(self.column_density_final_spectrum_button)
        cd_header_row.addWidget(self.column_density_columns_button)

        right_layout.addLayout(cd_header_row)

        self.column_density_source_table_box = QWidget()
        self.column_density_source_table_box.setObjectName("resultsTabPage")
        source_table_layout = QVBoxLayout(self.column_density_source_table_box)
        source_table_layout.setContentsMargins(7, 7, 7, 7)

        self.column_density_source_table = QTableWidget()
        self.column_density_source_table.setProperty(
            "czspecColumnProfile", "column_density_source"
        )
        self.column_density_source_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.column_density_source_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.column_density_source_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.column_density_source_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.column_density_source_table.horizontalHeader().setStretchLastSection(True)

        source_table_layout.addWidget(self.column_density_source_table)

        self.vasyunina_results_box = QWidget()
        self.vasyunina_results_box.setObjectName("resultsTabPage")
        vasy_results_layout = QVBoxLayout(self.vasyunina_results_box)
        vasy_results_layout.setContentsMargins(7, 7, 7, 7)

        self.vasyunina_results_table = QTableWidget()
        self.vasyunina_results_table.setProperty(
            "czspecColumnProfile", "column_density_mod"
        )
        self.vasyunina_results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.vasyunina_results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.vasyunina_results_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.vasyunina_results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.vasyunina_results_table.horizontalHeader().setStretchLastSection(True)

        vasy_results_layout.addWidget(self.vasyunina_results_table)

        self.sanhueza_results_box = QWidget()
        self.sanhueza_results_box.setObjectName("resultsTabPage")
        sanh_results_layout = QVBoxLayout(self.sanhueza_results_box)
        sanh_results_layout.setContentsMargins(7, 7, 7, 7)

        self.sanhueza_results_table = QTableWidget()
        self.sanhueza_results_table.setProperty(
            "czspecColumnProfile", "column_density_mth"
        )
        self.sanhueza_results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sanhueza_results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sanhueza_results_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.sanhueza_results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.sanhueza_results_table.horizontalHeader().setStretchLastSection(True)

        sanh_results_layout.addWidget(self.sanhueza_results_table)

        self.column_density_comparison_box = QWidget()
        self.column_density_comparison_box.setObjectName("resultsTabPage")
        comparison_layout = QVBoxLayout(self.column_density_comparison_box)
        comparison_layout.setContentsMargins(7, 7, 7, 7)

        self.vasyunina_comparison_box = QGroupBox(
            "Método ópticamente delgado (MOD)"
        )
        self.vasyunina_comparison_box.setProperty("role", "comparisonPanel")
        vasy_comparison_layout = QVBoxLayout(self.vasyunina_comparison_box)
        vasy_comparison_layout.setContentsMargins(5, 5, 5, 5)

        self.vasyunina_comparison_table = QTableWidget()
        self.vasyunina_comparison_table.setProperty(
            "czspecColumnProfile", "column_density_mod"
        )
        self.vasyunina_comparison_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        self.vasyunina_comparison_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.vasyunina_comparison_table.setSelectionMode(
            QAbstractItemView.SingleSelection
        )
        self.vasyunina_comparison_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.vasyunina_comparison_table.horizontalHeader().setStretchLastSection(True)
        vasy_comparison_layout.addWidget(self.vasyunina_comparison_table)

        self.sanhueza_comparison_box = QGroupBox(
            "Método de transiciones hiperfinas (MTH)"
        )
        self.sanhueza_comparison_box.setProperty("role", "comparisonPanel")
        sanh_comparison_layout = QVBoxLayout(self.sanhueza_comparison_box)
        sanh_comparison_layout.setContentsMargins(5, 5, 5, 5)

        self.sanhueza_comparison_table = QTableWidget()
        self.sanhueza_comparison_table.setProperty(
            "czspecColumnProfile", "column_density_mth"
        )
        self.sanhueza_comparison_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        self.sanhueza_comparison_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.sanhueza_comparison_table.setSelectionMode(
            QAbstractItemView.SingleSelection
        )
        self.sanhueza_comparison_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.sanhueza_comparison_table.horizontalHeader().setStretchLastSection(True)
        sanh_comparison_layout.addWidget(self.sanhueza_comparison_table)

        self.column_density_comparison_splitter = QSplitter(Qt.Vertical)
        self.column_density_comparison_splitter.setChildrenCollapsible(False)
        self.column_density_comparison_splitter.setHandleWidth(7)
        self.column_density_comparison_splitter.addWidget(
            self.vasyunina_comparison_box
        )
        self.column_density_comparison_splitter.addWidget(
            self.sanhueza_comparison_box
        )
        self.column_density_comparison_splitter.setSizes([260, 260])
        self.column_density_comparison_splitter.handle(1).setToolTip(
            "Arrastra para dar más altura a MOD o MTH."
        )
        comparison_layout.addWidget(self.column_density_comparison_splitter)

        self.column_density_tables_tabs = QTabWidget()
        self.column_density_tables_tabs.setObjectName("resultsTabs")
        self.column_density_tables_tabs.addTab(
            self.column_density_source_table_box,
            "1  Entrada",
        )
        self.column_density_tables_tabs.addTab(
            self.vasyunina_results_box,
            "2  MOD",
        )
        self.column_density_tables_tabs.addTab(
            self.sanhueza_results_box,
            "3  MTH",
        )
        self.column_density_tables_tabs.addTab(
            self.column_density_comparison_box,
            "4  MOD vs MTH",
        )
        self.column_density_tables_tabs.tabBar().setTabToolTip(
            0,
            "Datos seleccionados en identificación molecular o cargados desde CSV.",
        )
        self.column_density_tables_tabs.tabBar().setTabToolTip(
            1,
            "Resultados del método ópticamente delgado.",
        )
        self.column_density_tables_tabs.tabBar().setTabToolTip(
            2,
            "Resultados del método de transiciones hiperfinas.",
        )
        self.column_density_tables_tabs.tabBar().setTabToolTip(
            3,
            "Comparación simultánea de los resultados MOD y MTH.",
        )
        self.column_density_tables_tabs.setCurrentWidget(
            self.column_density_source_table_box
        )
        right_layout.addWidget(self.column_density_tables_tabs, stretch=1)

        splitter.addWidget(right_panel)
        splitter.setSizes([315, 965])
        for _button in (self.column_density_refresh_button, self.column_density_load_button, self.column_density_plot_table_button, self.column_density_final_spectrum_button, self.column_density_columns_button):
            _apply_action_role(_button, "secondary")
        for _button in (self.vasyunina_run_button, self.sanhueza_run_button):
            _apply_action_role(_button, "primary")
        for _button in (self.save_vasyunina_button, self.save_sanhueza_button, self.column_density_save_latex_button, self.column_density_export_tables_button, self.column_density_export_spectra_button):
            _apply_action_role(_button, "export")
        for _button in (self.column_open_tables_button, self.column_open_spectra_button, self.column_open_images_button, self.column_open_general_button):
            _apply_action_role(_button, "utility")

        self.column_density_columns_button.clicked.connect(self.open_column_density_columns_dialog)
        self.column_density_plot_table_button.clicked.connect(self.open_column_density_table_plot_dialog)
        self.column_density_final_spectrum_button.clicked.connect(self.open_column_density_final_spectrum)
        self._m3_temperature_user_edited = False
        self.vasyunina_temperatures_input.textEdited.connect(lambda _t: setattr(self, "_m3_temperature_user_edited", True))
        self.sanhueza_tex_input.textEdited.connect(lambda _t: setattr(self, "_m3_temperature_user_edited", True))

        self.cd_search_button.clicked.connect(self.apply_column_density_filter)
        self.cd_clear_search_button.clicked.connect(self.clear_column_density_filter)
        self.cd_search_input.returnPressed.connect(self.apply_column_density_filter)

    @staticmethod
    def _optional_positive(value: float) -> float | None:
        value = float(value)
        return value if value > 0 else None

    @staticmethod
    def _optional_int_from_row(row: pd.Series, name: str) -> int | None:
        try:
            value = row.get(name, np.nan)
            if pd.isna(value):
                return None
            return int(abs(float(value)))
        except (TypeError, ValueError):
            return None

    def _selected_lte_species_row(self) -> pd.Series | None:
        key = self.lte_species_combo.currentData()
        row = self.lte_species_rows.get(key)
        return row.copy() if row is not None else None

    def _lte_species_key_from_row(self, row: pd.Series) -> str:
        name = str(row.get("name", "") or row.get("chemical_name", "") or "").strip()
        linelist = str(row.get("linelist", "") or "").strip().upper()
        tag = self._optional_int_from_row(row, "moleculeTag")
        species_id = self._optional_int_from_row(row, "species_id")
        return f"{linelist}|{tag}|{species_id}|{name}"

    def _matching_lte_species_key(self, source_row: pd.Series) -> str | None:
        """Relaciona una fila de M3 con la identidad molecular conservada en M2."""

        exact_key = self._lte_species_key_from_row(source_row)
        if exact_key in self.lte_species_rows:
            return exact_key

        target_tag = self._optional_int_from_row(source_row, "moleculeTag")
        target_species_id = self._optional_int_from_row(source_row, "species_id")
        target_linelist = str(source_row.get("linelist", "") or "").strip().upper()
        target_name = str(source_row.get("name", "") or "").strip().casefold()
        for key, candidate in self.lte_species_rows.items():
            candidate_linelist = str(candidate.get("linelist", "") or "").strip().upper()
            candidate_tag = self._optional_int_from_row(candidate, "moleculeTag")
            candidate_species_id = self._optional_int_from_row(candidate, "species_id")
            candidate_name = str(candidate.get("name", "") or "").strip().casefold()
            if (
                target_tag is not None
                and candidate_tag == target_tag
                and (not target_linelist or candidate_linelist == target_linelist)
            ):
                return key
            if (
                target_species_id is not None
                and candidate_species_id == target_species_id
                and (not target_linelist or candidate_linelist == target_linelist)
            ):
                return key
            if target_name and candidate_name == target_name:
                return key
        return None

    @staticmethod
    def _mth_target_source_row(row: pd.Series) -> pd.Series:
        values = {
            str(column)[len("target_") :]: value
            for column, value in row.items()
            if str(column).startswith("target_")
        }
        values["obs_id"] = row.get("target_obs_id", values.get("obs_id"))
        values["name"] = row.get("target_name", values.get("name"))
        values["chemical_name"] = row.get(
            "chemical_name",
            values.get("chemical_name"),
        )
        values["ν_obs_MHz"] = row.get("nu_target_MHz", values.get("ν_obs_MHz"))
        return pd.Series(values)

    def _lte_species_display_label(self, source_row: pd.Series) -> str:
        name = str(
            source_row.get("name", "")
            or source_row.get("chemical_name", "")
            or "Especie sin nombre"
        ).strip()
        linelist = str(source_row.get("linelist", "") or "").strip().upper()
        tag = self._optional_int_from_row(source_row, "moleculeTag")
        if tag is None:
            tag = self._optional_int_from_row(source_row, "species_id")
        catalog = f" [{linelist}:{tag}]" if linelist and tag is not None else ""
        return f"{name}{catalog}"

    def _fallback_lte_transitions(self, selected_row: pd.Series) -> pd.DataFrame:
        selected = self.get_species_selected_dataframe()
        if selected is None or selected.empty:
            return pd.DataFrame()

        target_tag = self._optional_int_from_row(selected_row, "moleculeTag")
        if target_tag is not None and "moleculeTag" in selected.columns:
            tags = pd.to_numeric(selected["moleculeTag"], errors="coerce").abs()
            matching = selected[tags == target_tag]
            if not matching.empty:
                return matching.reset_index(drop=True)

        target_name = str(selected_row.get("name", "") or "").strip().lower()
        if target_name and "name" in selected.columns:
            names = selected["name"].fillna("").astype(str).str.strip().str.lower()
            matching = selected[names == target_name]
            if not matching.empty:
                return matching.reset_index(drop=True)
        return pd.DataFrame([selected_row])

    @staticmethod
    def _finite_row_value(row: pd.Series, *names: str) -> float | None:
        for name in names:
            if name not in row.index:
                continue
            try:
                value = float(row.get(name))
            except (TypeError, ValueError):
                continue
            if np.isfinite(value):
                return value
        return None

    @staticmethod
    def _identifier_mask(frame: pd.DataFrame, column: str, value) -> pd.Series:
        if column not in frame.columns or value is None or pd.isna(value):
            return pd.Series(False, index=frame.index)
        numeric_value = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
        if pd.notna(numeric_value):
            numeric_column = pd.to_numeric(frame[column], errors="coerce")
            return numeric_column.notna() & np.isclose(numeric_column, float(numeric_value))
        target = str(value).strip().casefold()
        return frame[column].fillna("").astype(str).str.strip().str.casefold() == target

    def _rows_for_lte_species(
        self,
        frame: pd.DataFrame | None,
        selected_row: pd.Series,
        *,
        obs_column: str,
        name_column: str,
    ) -> pd.DataFrame:
        if frame is None or frame.empty:
            return pd.DataFrame()
        obs_mask = self._identifier_mask(frame, obs_column, selected_row.get("obs_id"))
        if obs_mask.any():
            return frame.loc[obs_mask].copy()

        selected_name = str(selected_row.get("name", "") or "").strip().casefold()
        if selected_name and name_column in frame.columns:
            name_mask = (
                frame[name_column].fillna("").astype(str).str.strip().str.casefold()
                == selected_name
            )
            if name_mask.any():
                return frame.loc[name_mask].copy()
        return pd.DataFrame()

    def _complete_lte_source_row(self, source_row: pd.Series) -> pd.Series:
        """Restaura metadatos espectroscópicos omitidos por la tabla MTH ancha."""

        selected = self.get_species_selected_dataframe()
        if selected is None or selected.empty:
            return source_row.copy()

        matching = pd.DataFrame()
        obs_mask = self._identifier_mask(selected, "obs_id", source_row.get("obs_id"))
        if obs_mask.any():
            matching = selected.loc[obs_mask]
        if matching.empty:
            name = str(source_row.get("name", "") or "").strip().casefold()
            if name and "name" in selected.columns:
                name_mask = (
                    selected["name"].fillna("").astype(str).str.strip().str.casefold()
                    == name
                )
                matching = selected.loc[name_mask]
        if matching.empty:
            return source_row.copy()

        completed = matching.iloc[0].copy()
        for column, value in source_row.items():
            try:
                missing = pd.isna(value)
            except (TypeError, ValueError):
                missing = False
            if not missing:
                completed[column] = value
        return completed

    def refresh_lte_physical_solutions(self):
        """Construye el selector jerárquico método → transición → T_ex desde M3."""

        previous_method = self.lte_selected_method
        previous_group_key = self.lte_solution_species_combo.currentData()
        previous_solution_key = self.lte_solution_combo.currentData()
        self.lte_physical_solutions = {}
        self.lte_solution_groups = {}

        def register_solution(
            key: str,
            solution: dict,
            source_row: pd.Series,
            frequency_mhz: float | None,
        ):
            species_key = self._matching_lte_species_key(source_row)
            if species_key is None:
                # Las tablas de M3 conservan la identidad espectroscópica de M2.
                # Si la selección TOP-K cambió después del cálculo, se recupera
                # esa identidad directamente de la solución en vez de ocultarla.
                candidate_key = self._lte_species_key_from_row(source_row)
                candidate_name = str(
                    source_row.get("name", "")
                    or source_row.get("chemical_name", "")
                    or ""
                ).strip()
                if not candidate_name:
                    return
                species_key = candidate_key
                if species_key not in self.lte_species_rows:
                    self.lte_species_rows[species_key] = source_row.copy()
                    self.lte_species_combo.addItem(
                        self._lte_species_display_label(source_row),
                        species_key,
                    )
            obs_id = source_row.get("obs_id")
            obs_token = "" if obs_id is None or pd.isna(obs_id) else str(obs_id)
            source_file = str(source_row.get("Source", "") or "").strip()
            frequency_token = (
                f"{float(frequency_mhz):.9f}"
                if frequency_mhz is not None and np.isfinite(frequency_mhz)
                else "sin-frecuencia"
            )
            group_key = (
                f"{solution['method']}|{species_key}|{source_file}|{obs_token}|{frequency_token}"
            )
            display_label = self._lte_species_display_label(source_row)
            if source_file:
                display_label = f"{source_file} · {display_label}"
            if frequency_mhz is not None and np.isfinite(frequency_mhz):
                display_label += f" · {float(frequency_mhz):.6f} MHz"
            group = self.lte_solution_groups.setdefault(
                group_key,
                {
                    "method": solution["method"],
                    "species_key": species_key,
                    "label": display_label,
                    "frequency_mhz": frequency_mhz,
                    "source_file": source_file,
                    "solution_keys": [],
                },
            )
            solution["species_key"] = species_key
            solution["group_key"] = group_key
            solution["source_file"] = source_file
            self.lte_physical_solutions[key] = solution
            group["solution_keys"].append(key)

        def register_mth_solution(
            *,
            key: str,
            row: pd.Series,
            source_row: pd.Series,
            n_value: float | None,
            tex: float | None,
            linewidth: float | None,
            tau: float | None,
            reference_name: str,
        ):
            if not all(
                value is not None and value > 0
                for value in (n_value, tex, linewidth, tau)
            ):
                return
            source_row = self._complete_lte_source_row(source_row)
            rest_frequency = self._finite_row_value(
                source_row,
                "orderedfreq",
                "orderedFreq",
                "frequency_mhz",
            )
            observed_frequency = self._finite_row_value(
                source_row,
                "ν_obs_MHz",
                "nu_MHz",
                "freq_MHz",
            )
            display_frequency = (
                observed_frequency if observed_frequency is not None else rest_frequency
            )
            solution = {
                "method": "MTH",
                "column_density_cm2": n_value,
                "tex_k": tex,
                "linewidth_kms": linewidth,
                "tau_reference": tau,
                "rest_frequency_mhz": rest_frequency,
                "observed_frequency_mhz": observed_frequency,
                "target_name": str(source_row.get("name", "") or "").strip(),
                "reference_name": reference_name,
            }
            register_solution(
                key,
                solution,
                source_row,
                display_frequency,
            )

        if self.column_density_sanhueza_df is not None:
            for source_index, row in self.column_density_sanhueza_df.iterrows():
                is_wide_row = "Tex [K]" in row.index and any(
                    re.fullmatch(r"tau_\d+", str(column))
                    for column in row.index
                )
                if is_wide_row:
                    source_row = row.copy()
                    tex = self._finite_row_value(row, "Tex [K]", "Tex_K")
                    linewidth = self._finite_row_value(
                        row,
                        "Δv [Km/s]",
                        "Delta_v_target_kms",
                    )
                    for column in row.index:
                        match = re.fullmatch(r"tau_(\d+)", str(column))
                        if match is None:
                            continue
                        reference_index = match.group(1)
                        tau = self._finite_row_value(row, str(column))
                        n_value = self._finite_row_value(
                            row,
                            f"N_{reference_index}_cm2",
                        )
                        reference_name = str(
                            row.get(f"ref_{reference_index}_name", "") or ""
                        ).strip()
                        register_mth_solution(
                            key=f"mth-wide:{source_index}:{reference_index}",
                            row=row,
                            source_row=source_row,
                            n_value=n_value,
                            tex=tex,
                            linewidth=linewidth,
                            tau=tau,
                            reference_name=reference_name,
                        )
                    continue

                source_row = self._mth_target_source_row(row)
                n_value = self._finite_row_value(row, "N_cm2")
                tex = self._finite_row_value(row, "Tex_K")
                linewidth = self._finite_row_value(row, "Delta_v_target_kms")
                tau = self._finite_row_value(row, "tau_target")
                if str(row.get("N_status", "OK")).strip().upper() != "OK":
                    continue
                if str(row.get("tau_status", "OK")).strip().upper() != "OK":
                    continue
                register_mth_solution(
                    key=f"mth:{source_index}",
                    row=row,
                    source_row=source_row,
                    n_value=n_value,
                    tex=tex,
                    linewidth=linewidth,
                    tau=tau,
                    reference_name=str(row.get("ref_name", "") or "").strip(),
                )

        if self.column_density_vasyunina_df is not None:
            for source_index, row in self.column_density_vasyunina_df.iterrows():
                source_row = row.copy()
                linewidth = self._finite_row_value(row, "Δv [Km/s]", "Delta_v_target_kms")
                if linewidth is None or linewidth <= 0:
                    continue
                rest_frequency = self._finite_row_value(
                    source_row,
                    "orderedfreq",
                    "orderedFreq",
                    "frequency_mhz",
                )
                observed_frequency = self._finite_row_value(
                    source_row,
                    "ν_obs_MHz",
                    "nu_MHz",
                    "freq_MHz",
                )
                display_frequency = (
                    observed_frequency if observed_frequency is not None else rest_frequency
                )
                for column in row.index:
                    match = re.fullmatch(r"N_tot_([0-9]+(?:\.[0-9]+)?)K_cm2", str(column))
                    if match is None:
                        continue
                    n_value = self._finite_row_value(row, str(column))
                    tex = float(match.group(1))
                    if n_value is None or n_value <= 0:
                        continue
                    key = f"mod:{source_index}:{column}"
                    solution = {
                        "method": "MOD",
                        "column_density_cm2": n_value,
                        "tex_k": tex,
                        "linewidth_kms": linewidth,
                        "tau_reference": None,
                        "rest_frequency_mhz": rest_frequency,
                        "observed_frequency_mhz": observed_frequency,
                        "target_name": str(row.get("name", "") or "").strip(),
                    }
                    register_solution(
                        key,
                        solution,
                        source_row,
                        display_frequency,
                    )

        available_methods = {
            group["method"] for group in self.lte_solution_groups.values()
        }
        # MOD y MTH permanecen seleccionables. Si un método aún no tiene filas
        # válidas, su propia vista lo explica en vez de bloquear el botón.
        self.lte_mod_method_button.setEnabled(True)
        self.lte_mth_method_button.setEnabled(True)
        target_method = previous_method if previous_method in {"MOD", "MTH"} else None

        if not available_methods:
            self.lte_global_tex_combo.clear()
            self.lte_global_tex_combo.addItem("Sin temperaturas disponibles", None)
            self.lte_build_global_button.setEnabled(False)
            self.lte_solution_species_combo.blockSignals(True)
            self.lte_solution_species_combo.clear()
            self.lte_solution_species_combo.addItem("Sin resultados disponibles en M3", None)
            self.lte_solution_species_combo.blockSignals(False)
            self.lte_solution_combo.blockSignals(True)
            self.lte_solution_combo.clear()
            self.lte_solution_combo.addItem("Ejecuta MOD o MTH en el módulo 3", None)
            self.lte_solution_combo.blockSignals(False)
            self.lte_apply_solution_button.setEnabled(False)
            self.lte_query_button.setEnabled(False)
            self.lte_solution_label.setText(
                "No hay soluciones compatibles en M3. Ejecuta MOD o MTH antes de modelar LTE."
            )
            self._clear_lte_model_state()
            return

        if target_method is None:
            self.lte_global_tex_combo.clear()
            self.lte_global_tex_combo.addItem("Elige primero MOD o MTH", None)
            self.lte_build_global_button.setEnabled(False)
            self.lte_solution_species_combo.blockSignals(True)
            self.lte_solution_species_combo.clear()
            self.lte_solution_species_combo.addItem(
                "Elige primero MOD o MTH",
                None,
            )
            self.lte_solution_species_combo.blockSignals(False)
            self.lte_solution_combo.blockSignals(True)
            self.lte_solution_combo.clear()
            self.lte_solution_combo.addItem(
                "Después elige una transición y Tₑₓ",
                None,
            )
            self.lte_solution_combo.blockSignals(False)
            self.lte_apply_solution_button.setEnabled(False)
            self.lte_query_button.setEnabled(False)
            self._clear_lte_model_state()
            self.lte_solution_label.setText(
                "Selecciona MOD o MTH para mostrar sus resultados del módulo 3."
            )
            return

        target_button = (
            self.lte_mod_method_button if target_method == "MOD" else self.lte_mth_method_button
        )
        target_button.setChecked(True)
        self.set_lte_solution_method(
            target_method,
            preferred_group_key=previous_group_key,
            preferred_solution_key=previous_solution_key,
        )

    def set_lte_solution_method(
        self,
        method: str,
        *,
        preferred_group_key: str | None = None,
        preferred_solution_key: str | None = None,
    ):
        method = str(method).strip().upper()
        self.lte_selected_method = method
        target_button = (
            self.lte_mod_method_button if method == "MOD" else self.lte_mth_method_button
        )
        target_button.setChecked(True)
        self._populate_lte_global_tex(method)
        groups = [
            (key, group)
            for key, group in self.lte_solution_groups.items()
            if group.get("method") == method
        ]
        active_source = self.lte_active_band_path or self.selected_file
        active_name = Path(active_source).name if active_source else ""
        groups_for_active = [
            item for item in groups if item[1].get("source_file") == active_name
        ]
        if groups_for_active:
            groups = groups_for_active
        groups.sort(
            key=lambda item: (
                float(item[1]["frequency_mhz"])
                if item[1].get("frequency_mhz") is not None
                and np.isfinite(item[1]["frequency_mhz"])
                else float("inf"),
                str(item[1].get("label", "")).casefold(),
            )
        )

        self.lte_solution_species_combo.blockSignals(True)
        self.lte_solution_species_combo.clear()
        for group_key, group in groups:
            self.lte_solution_species_combo.addItem(group["label"], group_key)
            self.lte_solution_species_combo.setItemData(
                self.lte_solution_species_combo.count() - 1,
                group["label"],
                Qt.ItemDataRole.ToolTipRole,
            )
        if not groups:
            self.lte_solution_species_combo.addItem(
                f"Sin resultados {method} disponibles",
                None,
            )
        elif preferred_group_key in self.lte_solution_groups:
            preferred_index = self.lte_solution_species_combo.findData(
                preferred_group_key
            )
            if preferred_index >= 0:
                self.lte_solution_species_combo.setCurrentIndex(preferred_index)
        self.lte_solution_species_combo.blockSignals(False)
        self._populate_lte_solution_choices(preferred_solution_key)

    def _populate_lte_global_tex(self, method: str):
        previous = self.lte_global_tex_combo.currentData()
        temperatures = available_lte_tex_values(self.lte_physical_solutions, method)
        self.lte_global_tex_combo.blockSignals(True)
        self.lte_global_tex_combo.clear()
        for temperature in temperatures:
            self.lte_global_tex_combo.addItem(f"{temperature:g} K", float(temperature))
        if previous in temperatures:
            index = self.lte_global_tex_combo.findData(previous)
            self.lte_global_tex_combo.setCurrentIndex(max(0, index))
        if not temperatures:
            self.lte_global_tex_combo.addItem(
                f"Sin temperaturas {str(method).upper()} disponibles", None
            )
        self.lte_global_tex_combo.blockSignals(False)
        self.lte_build_global_button.setEnabled(bool(temperatures))

    def _clear_lte_model_state(self):
        self.lte_catalog_df = None
        self.lte_catalog_species_key = None
        self.lte_applied_solution_key = None
        self.lte_reference_tau = None
        self.lte_column_density_input.clear()
        self.lte_tex_input.setValue(0.0)
        self.lte_linewidth_input.setValue(0.0)
        self.lte_velocity_input.setValue(0.0)
        self.lte_run_button.setEnabled(self._lte_model_inputs_ready())

    def _populate_lte_solution_choices(
        self,
        preferred_solution_key: str | None = None,
    ):
        self._clear_lte_model_state()
        group_key = self.lte_solution_species_combo.currentData()
        group = self.lte_solution_groups.get(group_key)

        self.lte_solution_combo.blockSignals(True)
        self.lte_solution_combo.clear()
        if group is None:
            self.lte_solution_combo.addItem("Sin soluciones para esta selección", None)
            self.lte_solution_combo.blockSignals(False)
            self.lte_apply_solution_button.setEnabled(False)
            self.lte_query_button.setEnabled(False)
            self.lte_q_label.setText("Q(T_ex): pendiente")
            return

        species_key = group.get("species_key")
        species_index = self.lte_species_combo.findData(species_key)
        self.lte_species_combo.blockSignals(True)
        if species_index >= 0:
            self.lte_species_combo.setCurrentIndex(species_index)
        self.lte_species_combo.blockSignals(False)

        solutions = [
            (key, self.lte_physical_solutions[key])
            for key in group.get("solution_keys", [])
            if key in self.lte_physical_solutions
        ]
        solutions.sort(
            key=lambda item: (
                float(item[1].get("tex_k", float("inf"))),
                float(item[1].get("column_density_cm2", float("inf"))),
            )
        )
        for key, solution in solutions:
            linewidth = solution.get("linewidth_kms")
            linewidth_text = (
                f" · FWHM={linewidth:g} km/s"
                if linewidth is not None and linewidth > 0
                else ""
            )
            if solution["method"] == "MTH":
                reference = solution.get("reference_name")
                reference_text = f" · ref. {reference}" if reference else ""
                label = (
                    f"Tₑₓ={solution['tex_k']:g} K · N={solution['column_density_cm2']:.3g} "
                    f"· τ={solution['tau_reference']:.3g}{linewidth_text}{reference_text}"
                )
            else:
                label = (
                    f"Tₑₓ={solution['tex_k']:g} K · "
                    f"N={solution['column_density_cm2']:.3g}{linewidth_text}"
                )
            self.lte_solution_combo.addItem(label, key)
            self.lte_solution_combo.setItemData(
                self.lte_solution_combo.count() - 1,
                label,
                Qt.ItemDataRole.ToolTipRole,
            )
        if preferred_solution_key in self.lte_physical_solutions:
            preferred_index = self.lte_solution_combo.findData(preferred_solution_key)
            if preferred_index >= 0:
                self.lte_solution_combo.setCurrentIndex(preferred_index)
        self.lte_solution_combo.blockSignals(False)

        current_solution = self.lte_solution_combo.currentData()
        self.lte_apply_solution_button.setEnabled(
            current_solution in self.lte_physical_solutions
        )
        self.lte_solution_label.setText(
            f"{len(solutions)} solución(es) {group['method']} disponibles. "
            "Elige Tₑₓ y aplica la solución observacional."
        )
        self.update_lte_beam_preset()
        row = self._selected_lte_species_row()
        self.lte_query_button.setEnabled(
            row is not None and self.lte_observed_frequency_mhz is not None
        )
        if row is None:
            self.lte_q_label.setText("Q(T_ex): pendiente")
            return
        fallback = self._fallback_lte_transitions(row)
        self.lte_catalog_label.setText(
            f"{len(fallback)} transición(es) seleccionada(s) disponibles como respaldo. "
            "Consulta la banda para incluir todas las transiciones catalogadas."
        )
        self.lte_q_label.setText("Q(T_ex): se calculará al generar el modelo")

    def on_lte_solution_species_changed(self, *_):
        self._populate_lte_solution_choices()

    def on_lte_solution_choice_changed(self, *_):
        current_key = self.lte_solution_combo.currentData()
        self.lte_apply_solution_button.setEnabled(
            current_key in self.lte_physical_solutions
        )
        if current_key == self.lte_applied_solution_key:
            return
        self.lte_applied_solution_key = None
        self.lte_reference_tau = None
        self.lte_column_density_input.clear()
        self.lte_tex_input.setValue(0.0)
        self.lte_linewidth_input.setValue(0.0)
        self.lte_velocity_input.setValue(0.0)
        self.lte_run_button.setEnabled(False)
        if current_key in self.lte_physical_solutions:
            self.lte_solution_label.setText(
                "La solución cambió. Pulsa «Aplicar solución observacional» para usarla."
            )

    def _lte_model_inputs_ready(self) -> bool:
        return (
            bool(self.lte_observed_spectra)
            and any(item.get("enabled", True) for item in self.lte_components)
        )

    def apply_lte_physical_solution(self):
        solution = self.lte_physical_solutions.get(self.lte_solution_combo.currentData())
        if solution is None:
            self.lte_applied_solution_key = None
            self.lte_reference_tau = None
            self.lte_solution_label.setText(
                "Selecciona y aplica una solución observacional de MOD o MTH."
            )
            self.lte_run_button.setEnabled(False)
            return

        self.lte_applied_solution_key = self.lte_solution_combo.currentData()

        self.lte_column_density_input.setText(f"{solution['column_density_cm2']:.8g}")
        self.lte_tex_input.setValue(float(solution["tex_k"]))
        linewidth = solution.get("linewidth_kms")
        resolution_text = ""
        if linewidth is not None and linewidth > 0:
            self.lte_linewidth_input.setValue(float(linewidth))
            self.lte_resolution_input.setValue(0.0)
            resolution_text = (
                " La convolución instrumental queda desactivada porque la FWHM heredada "
                "ya fue medida en el espectro procesado."
            )

        observed = solution.get("observed_frequency_mhz")
        rest = solution.get("rest_frequency_mhz")
        velocity_text = "Δv de centro no disponible"
        if observed is not None and rest is not None:
            try:
                velocity = radio_velocity_offset_kms(observed, rest)
                self.lte_velocity_input.setValue(velocity)
                velocity_text = f"corrimiento de centro={velocity:.3g} km/s"
            except ValueError:
                pass

        tau = solution.get("tau_reference")
        if tau is not None:
            self.lte_reference_tau = {
                "value": float(tau),
                "rest_frequency_mhz": rest,
                "method": solution["method"],
            }
            tau_text = (
                f"τ MTH={tau:.4g} se conservará como referencia; "
                "el motor LTE recalculará τ para cada transición"
            )
        else:
            self.lte_reference_tau = None
            tau_text = "MOD no aporta una τ independiente"

        self.lte_solution_label.setText(
            f"Aplicada {solution['method']}: N, Tₑₓ"
            f"{', FWHM' if linewidth is not None and linewidth > 0 else ''}; "
            f"{velocity_text}; {tau_text}.{resolution_text}"
        )
        self.update_lte_beam_preset()
        row = self._selected_lte_species_row()
        if row is None:
            self.notify_info("La solución no conserva una identidad molecular utilizable.")
            return
        species_key = solution.get("species_key")
        transitions = None
        if (
            self.lte_catalog_df is not None
            and not self.lte_catalog_df.empty
            and self.lte_catalog_species_key == species_key
        ):
            transitions = self.lte_catalog_df.copy()
        if transitions is None or transitions.empty:
            transitions = self._fallback_lte_transitions(row)
        if transitions is None or transitions.empty:
            self.notify_info(
                "No hay transiciones utilizables. Consulta la banda o vuelve a M2."
            )
            return

        component_label = (
            f"{self.lte_solution_species_combo.currentText()} · "
            f"{solution['method']} · Tₑₓ={solution['tex_k']:g} K"
        )
        component = {
            "label": component_label,
            "solution_key": self.lte_applied_solution_key,
            "solution": deepcopy(solution),
            "initial_solution": deepcopy(solution),
            "row": row.copy(),
            "transitions": transitions.copy(),
            "reference_tau": deepcopy(self.lte_reference_tau),
            "source_size_arcsec": self._optional_positive(
                self.lte_source_size_input.value()
            ),
            "beam_size_arcsec": self._optional_positive(
                self.lte_beam_size_input.value()
            ),
            "beam_model": str(self.lte_telescope_combo.currentData()),
            "background_temperature_k": self.lte_background_input.value(),
            "channel_response_fwhm_mhz": self._optional_positive(
                self.lte_resolution_input.value()
            ),
            "enabled": True,
            "color": LTEComponentWorkbench.PALETTE[
                len(self.lte_components) % len(LTEComponentWorkbench.PALETTE)
            ],
        }
        existing = next(
            (
                index
                for index, item in enumerate(self.lte_components)
                if item.get("solution_key") == self.lte_applied_solution_key
            ),
            None,
        )
        if existing is None:
            self.lte_components.append(component)
        else:
            self.lte_components[existing] = component
        self._refresh_lte_components_list()
        self.lte_log_area.append(
            f"[OK] Componente LTE añadido desde {solution['method']} (módulo 3)."
        )
        self.lte_run_button.setEnabled(self._lte_model_inputs_ready())

    def build_global_lte_components(self):
        """Crea una componente por especie usando toda la selección M1–M3."""

        method = str(self.lte_selected_method or "").upper()
        tex = self.lte_global_tex_combo.currentData()
        if method not in {"MOD", "MTH"} or tex is None:
            self.notify_info("Elige MOD o MTH y una temperatura de excitación.")
            return
        seeds = aggregate_global_lte_solutions(
            self.lte_physical_solutions,
            method,
            float(tex),
        )
        if not seeds:
            self.notify_info(
                f"M3 no contiene soluciones {method} válidas para Tₑₓ={float(tex):g} K."
            )
            return
        selected = self.get_species_selected_dataframe()
        components = []
        palette = LTEComponentWorkbench.PALETTE
        for index, seed in enumerate(seeds):
            species_key = seed.get("species_key")
            row = self.lte_species_rows.get(species_key)
            if row is None:
                continue
            transitions = lte_transitions_for_species(selected, row)
            if transitions.empty:
                transitions = self._fallback_lte_transitions(row)
            if transitions.empty:
                continue
            member_keys = list(seed.get("member_solution_keys", []))
            member_solutions = [
                self.lte_physical_solutions[key]
                for key in member_keys
                if key in self.lte_physical_solutions
            ]
            velocities = [
                self._solution_velocity_offset(solution)
                for solution in member_solutions
            ]
            if velocities:
                seed["velocity_offset_kms"] = float(np.median(velocities))
            reference_taus = [
                {
                    "value": float(solution["tau_reference"]),
                    "rest_frequency_mhz": solution.get("rest_frequency_mhz"),
                    "solution_key": key,
                }
                for key, solution in zip(member_keys, member_solutions)
                if solution.get("tau_reference") is not None
            ]
            label = (
                f"{self._lte_species_display_label(row)} · {method} · "
                f"Tₑₓ={float(tex):g} K"
            )
            solution_key = f"global:{method}:{species_key}:{float(tex):g}"
            component = {
                "label": label,
                "solution_key": solution_key,
                "solution": deepcopy(seed),
                "initial_solution": deepcopy(seed),
                "row": row.copy(),
                "transitions": transitions.copy(),
                "reference_tau": reference_taus[0] if reference_taus else None,
                "reference_taus": reference_taus,
                "source_size_arcsec": self._optional_positive(
                    self.lte_source_size_input.value()
                ),
                "beam_size_arcsec": self._optional_positive(
                    self.lte_beam_size_input.value()
                ),
                "beam_model": str(self.lte_telescope_combo.currentData()),
                "background_temperature_k": self.lte_background_input.value(),
                "channel_response_fwhm_mhz": self._optional_positive(
                    self.lte_resolution_input.value()
                ),
                "enabled": True,
                "color": palette[index % len(palette)],
            }
            components.append(component)
        if not components:
            self.notify_info(
                "Las soluciones de M3 no pudieron relacionarse con transiciones seleccionadas en M2."
            )
            return
        self.lte_components = components
        self._refresh_lte_components_list()
        self.lte_log_area.append(
            f"[OK] Modelo global preparado: {len(components)} especie(s), "
            f"{sum(len(item['transitions']) for item in components)} transición(es), "
            f"método {method}, Tₑₓ={float(tex):g} K y "
            f"{len(self.lte_observed_spectra)} espectro(s)."
        )

    def open_lte_component_workbench(self):
        if not self.lte_components:
            self.notify_info("Prepara el modelo global o añade una componente individual.")
            return
        if self.lte_component_workbench is None:
            self.lte_component_workbench = LTEComponentWorkbench(
                self.lte_components,
                self,
            )
            self.lte_component_workbench.componentsApplied.connect(
                self.apply_lte_component_workbench
            )
        else:
            self.lte_component_workbench.set_components(self.lte_components)
        self.lte_component_workbench.show()
        self.lte_component_workbench.raise_()
        self.lte_component_workbench.activateWindow()

    def open_lte_setup_dialog(self):
        """Muestra las condiciones comunes sin recargar el panel principal."""

        self.lte_setup_dialog.show()
        self.lte_setup_dialog.raise_()
        self.lte_setup_dialog.activateWindow()

    def open_lte_diagnostics(self):
        if self.lte_diagnostics_table.rowCount() == 0:
            self.notify_info("Genera primero un modelo para consultar el diagnóstico.")
            return
        self.lte_diagnostics_dialog.show()
        self.lte_diagnostics_dialog.raise_()
        self.lte_diagnostics_dialog.activateWindow()

    @staticmethod
    def _nonlte_component_key(component: dict) -> str:
        return str(component.get("solution_key") or component.get("label"))

    def _save_nonlte_state(self):
        self.settings.setValue(
            "nonlte/lamda_assignments",
            json.dumps(self.nonlte_assignments, ensure_ascii=False),
        )
        self.settings.setValue(
            "nonlte/model_defaults",
            json.dumps(self.nonlte_defaults, ensure_ascii=False),
        )

    def _update_nonlte_assignments(self, assignments):
        self.nonlte_assignments = dict(assignments or {})
        self._save_nonlte_state()
        self.nonlte_last_result = None
        self.nonlte_export_button.setEnabled(False)
        self._refresh_nonlte_controls()

    @staticmethod
    def _nonlte_backend_available() -> bool:
        """Comprueba el backend sin cargar Numba durante el arranque de CZSpec."""

        return importlib.util.find_spec("pythonradex") is not None

    def _refresh_nonlte_controls(self):
        if not hasattr(self, "nonlte_run_button"):
            return
        component_keys = {
            self._nonlte_component_key(component)
            for component in self.lte_components
            if component.get("enabled", True)
        }
        ready = any(
            key in component_keys
            and bool(assignment.get("enabled", True))
            and Path(str(assignment.get("path", ""))).is_file()
            for key, assignment in self.nonlte_assignments.items()
        )
        backend_ready = self._nonlte_backend_available()
        backend_busy = "nonlte_backend" in self._active_tasks
        self.nonlte_backend_label.setText(
            "Motor no-LTE disponible."
            if backend_ready
            else "Falta instalar una vez el motor pythonradex/Numba."
        )
        self.nonlte_backend_button.setVisible(not backend_ready)
        self.nonlte_backend_button.setEnabled(not backend_busy)
        self.nonlte_run_button.setEnabled(
            backend_ready
            and ready
            and bool(self.lte_observed_spectra)
            and "nonlte_model" not in self._active_tasks
        )

    def install_nonlte_backend(self):
        """Instala el backend añadido en alpha.39 a instalaciones ya existentes."""

        if self._nonlte_backend_available():
            self._refresh_nonlte_controls()
            self.notify_info("El motor no-LTE ya está disponible.")
            return

        def work(progress):
            progress(10, "Preparando la instalación del motor no-LTE")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    "--disable-pip-version-check",
                    "--no-input",
                    "pythonradex>=2.0.2,<3",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            output = "\n".join(
                part.strip()
                for part in (completed.stdout, completed.stderr)
                if part.strip()
            )
            if completed.returncode != 0:
                detail = output[-5000:] if output else "pip no devolvió detalles."
                raise RuntimeError(
                    "No se pudo instalar pythonradex. Comprueba la conexión a "
                    f"Internet y vuelve a intentarlo.\n\n{detail}"
                )
            progress(95, "Verificando el motor no-LTE")
            return output

        def on_success(output):
            importlib.invalidate_caches()
            self._refresh_nonlte_controls()
            self.lte_log_area.append("[OK] Backend no-LTE instalado: pythonradex.")
            self.notify_success(
                "El motor no-LTE quedó instalado. Ya puedes configurar archivos "
                "LAMDA y generar el modelo global."
            )

        def on_error(message, details):
            self.lte_log_area.append(f"[ERROR] Backend no-LTE: {message}")
            self.lte_log_area.append(details)
            self.notify(
                "No se pudo instalar el motor no-LTE",
                message[-1200:],
                duration_ms=14000,
            )

        self._start_background_task(
            "nonlte_backend",
            work,
            on_success,
            on_error=on_error,
            busy_widgets=(
                self.nonlte_backend_button,
                self.nonlte_config_button,
                self.nonlte_run_button,
            ),
            status_message="Instalando el motor no-LTE…",
        )

    def open_nonlte_dialog(self):
        from czspec.gui.nonlte_dialog import NonLTEConfigDialog

        if self.nonlte_dialog is None:
            self.nonlte_dialog = NonLTEConfigDialog(self)
            self.nonlte_dialog.assignments_changed.connect(
                self._update_nonlte_assignments
            )
            self.nonlte_dialog.run_requested.connect(self.run_nonlte_model)
        self.nonlte_dialog.set_state(
            self.lte_components,
            self.nonlte_assignments,
            self.nonlte_defaults,
        )
        self.nonlte_dialog.show()
        self.nonlte_dialog.raise_()
        self.nonlte_dialog.activateWindow()

    def run_nonlte_model(self, configuration=None):
        if not self._nonlte_backend_available():
            self._refresh_nonlte_controls()
            self.notify_info(
                "Instala primero el motor no-LTE desde el botón de esta sección."
            )
            return
        if not self.lte_observed_spectra:
            self.notify_info("Actualiza primero la sesión desde los módulos 1–3.")
            return
        if configuration is None:
            selected = [
                key
                for key, assignment in self.nonlte_assignments.items()
                if assignment.get("enabled", True)
                and Path(str(assignment.get("path", ""))).is_file()
            ]
            if not selected:
                self.open_nonlte_dialog()
                self.notify_info(
                    "Asigna al menos un archivo LAMDA antes de generar el modelo no-LTE."
                )
                return
            configuration = dict(self.nonlte_defaults)
            configuration["selected_component_keys"] = selected
            configuration["assignments"] = deepcopy(self.nonlte_assignments)
        else:
            configuration = deepcopy(dict(configuration))
            self.nonlte_assignments = deepcopy(configuration.get("assignments", {}))
            self.nonlte_defaults = {
                key: deepcopy(configuration[key])
                for key in (
                    "tkin_k",
                    "h2_density_cm3",
                    "h2_opr",
                    "geometry",
                    "background_temperature_k",
                    "additional_colliders_cm3",
                    "treat_line_overlap",
                )
                if key in configuration
            }
            self._save_nonlte_state()

        selected_keys = set(configuration.get("selected_component_keys", []))
        assignments = configuration.get("assignments", self.nonlte_assignments)
        component_inputs = [
            deepcopy(component)
            for component in self.lte_components
            if component.get("enabled", True)
            and self._nonlte_component_key(component) in selected_keys
        ]
        if not component_inputs:
            self.notify_info(
                "Las asignaciones LAMDA ya no corresponden a componentes activas de M3."
            )
            self.open_nonlte_dialog()
            return
        band_entries = deepcopy(self.lte_observed_spectra)

        def work(progress):
            specs = []
            for component in component_inputs:
                key = self._nonlte_component_key(component)
                assignment = assignments.get(key, {})
                solution = component["solution"]
                specs.append(
                    NonLTEComponentSpec(
                        label=component["label"],
                        lamda_file=str(assignment.get("path", "")),
                        column_density_cm2=float(solution["column_density_cm2"]),
                        kinetic_temperature_k=float(configuration["tkin_k"]),
                        linewidth_kms=float(solution["linewidth_kms"]),
                        h2_density_cm3=float(configuration["h2_density_cm3"]),
                        h2_ortho_para_ratio=float(configuration.get("h2_opr", 3.0)),
                        additional_colliders_cm3=configuration.get(
                            "additional_colliders_cm3", {}
                        ),
                        geometry=str(configuration.get("geometry", "static sphere RADEX")),
                        velocity_offset_kms=self._solution_velocity_offset(solution),
                        source_size_arcsec=component.get("source_size_arcsec"),
                        beam_size_arcsec=component.get("beam_size_arcsec"),
                        beam_model=str(component.get("beam_model", "manual")),
                        background_temperature_k=float(
                            configuration.get("background_temperature_k", 2.725)
                        ),
                        channel_response_fwhm_mhz=component.get(
                            "channel_response_fwhm_mhz"
                        ),
                        treat_line_overlap=bool(
                            configuration.get("treat_line_overlap", False)
                        ),
                        method=str(solution.get("method", "")),
                        solution_key=key,
                    )
                )
            axes = {
                file_path: entry["frequency_mhz"]
                for file_path, entry in band_entries.items()
            }
            observed = {
                file_path: entry["intensity_k"]
                for file_path, entry in band_entries.items()
            }
            result = simulate_nonlte_session(
                axes,
                observed,
                specs,
                progress=progress,
            )
            progress(96, "Preparando diagnóstico no-LTE y residuales")
            return result, specs

        def on_success(result_and_specs):
            session_result, specs = result_and_specs
            active_path = self.lte_active_band_path or self.selected_file
            if active_path not in session_result.band_results:
                active_path = next(iter(session_result.band_results))
            active_result = session_result.band_results[active_path]
            payload = {
                "model_kind": "no-LTE",
                "result": active_result,
                "observed": np.asarray(
                    band_entries[active_path]["intensity_k"], dtype=float
                ),
                "active_band": active_path,
                "session_result": session_result,
                "band_entries": band_entries,
                "metrics_by_band": session_result.metrics_by_band,
                "metrics": session_result.metrics,
                "component_specs": specs,
                "component_inputs": component_inputs,
                "nonlte_configuration": deepcopy(configuration),
                "fit_result": None,
            }
            self.nonlte_last_result = payload
            self.lte_last_result = payload
            self._present_nonlte_result()
            self.notify_success(
                f"Modelo no-LTE listo: {len(specs)} componente(s), "
                f"{len(session_result.band_results)} banda(s) y "
                f"{len(session_result.line_diagnostics)} transición(es)."
            )

        def on_error(message, details):
            self.lte_log_area.append(f"[ERROR] Modelo no-LTE: {message}")
            self.lte_log_area.append(details)
            self.notify("No se pudo generar el modelo no-LTE", message, duration_ms=11000)

        self._start_background_task(
            "nonlte_model",
            work,
            on_success,
            on_error=on_error,
            busy_widgets=(
                self.nonlte_run_button,
                self.nonlte_config_button,
                self.lte_run_button,
                self.lte_refresh_button,
            ),
            status_message="Resolviendo poblaciones no-LTE con RADEX/LAMDA...",
        )

    def _present_nonlte_result(self):
        payload = self.nonlte_last_result
        if not payload:
            return
        session_result = payload["session_result"]
        diagnostics = session_result.line_diagnostics.copy()
        display = diagnostics.rename(
            columns={
                "espectro": "Espectro",
                "componente": "Componente",
                "método_M3": "Método M3",
                "archivo_LAMDA": "Archivo LAMDA",
                "índice_LAMDA": "Índice LAMDA",
                "transición": "Transición",
                "ν_reposo_MHz": "ν reposo [MHz]",
                "ν_modelo_MHz": "ν modelo [MHz]",
                "E_u_K": "Eᵤ [K]",
                "g_u": "gᵤ",
                "A_ul_s-1": "Aᵤₗ [s⁻¹]",
                "T_ex_noLTE_K": "Tₑₓ no-LTE [K]",
                "tau_pico": "τ pico",
                "Tkin_K": "Tkin [K]",
                "N_total_cm-2": "N total [cm⁻²]",
                "FWHM_km_s": "FWHM [km s⁻¹]",
                "Delta_v_km_s": "Δv [km s⁻¹]",
                "geometría": "Geometría",
            }
        )
        self.populate_table_widget_from_dataframe(
            self.lte_diagnostics_table, display.round(6)
        )
        omitted = session_result.omitted_components
        omitted_text = (
            f" · {len(omitted)} omisión(es) documentada(s)"
            if omitted
            else " · sin omisiones"
        )
        self.lte_diagnostics_dialog.summary.setText(
            f"{len(display)} transición(es) no-LTE en todas las bandas{omitted_text}. "
            "Tₑₓ y τ son resultados del equilibrio estadístico, no entradas de M3."
        )
        self.lte_diagnostics_button.setText(f"Diagnóstico ({len(display)})…")
        self.lte_diagnostics_button.setEnabled(True)
        self._update_lte_metrics_label(payload)
        active_path = payload.get("active_band")
        active_name = Path(active_path).name if active_path else "banda activa"
        config = payload["nonlte_configuration"]
        self.lte_interpretation_label.setText(
            f"Vista: {active_name}. Modelo no-LTE global con "
            f"Tkin={float(config['tkin_k']):g} K, "
            f"n(H₂)={float(config['h2_density_cm3']):.4g} cm⁻³ y "
            f"geometría «{config['geometry']}». {len(payload['component_specs'])} "
            f"componente(s) resueltas en {len(session_result.band_results)} banda(s)"
            f"{omitted_text}."
        )
        self.lte_q_label.setText(
            "No se impone Q(Tₑₓ): las poblaciones se resuelven con tasas "
            "radiativas y colisionales del archivo LAMDA."
        )
        for item in omitted:
            self.lte_log_area.append(
                f"[WARN] Omitida {item['componente']} ({Path(item['espectro']).name}): "
                f"{item['motivo']}"
            )
        self.lte_log_area.append(
            f"[OK] Modelo no-LTE: {len(payload['component_specs'])} componente(s), "
            f"{len(session_result.band_results)} banda(s), "
            f"RMS global={payload['metrics']['rms_K']:.4g} K."
        )
        self.lte_export_button.setEnabled(False)
        self.nonlte_export_button.setEnabled(True)
        self.lte_save_image_button.setEnabled(True)
        self.lte_fullscreen_button.setEnabled(True)
        self.lte_view_clean_button.setEnabled(True)
        self.lte_view_comparison_button.setEnabled(True)
        self.lte_refine_button.setEnabled(False)
        self.show_lte_comparison_view()

    def _populate_lte_band_combo(self):
        previous = self.lte_active_band_path
        if previous not in self.lte_observed_spectra:
            previous = self.selected_file
        if previous not in self.lte_observed_spectra and self.lte_observed_spectra:
            previous = next(iter(self.lte_observed_spectra))

        self.lte_band_combo.blockSignals(True)
        self.lte_band_combo.clear()
        for index, (file_path, entry) in enumerate(self.lte_observed_spectra.items(), start=1):
            frequency = np.asarray(entry.get("frequency_mhz", []), dtype=float)
            finite = frequency[np.isfinite(frequency)]
            range_text = ""
            if finite.size:
                range_text = f" · {np.nanmin(finite) / 1000:.3f}–{np.nanmax(finite) / 1000:.3f} GHz"
            label = f"{index}. {entry.get('name') or Path(file_path).name}{range_text}"
            self.lte_band_combo.addItem(label, file_path)
            self.lte_band_combo.setItemData(
                self.lte_band_combo.count() - 1,
                file_path,
                Qt.ItemDataRole.ToolTipRole,
            )
        selected_index = self.lte_band_combo.findData(previous)
        if selected_index >= 0:
            self.lte_band_combo.setCurrentIndex(selected_index)
        self.lte_band_combo.setEnabled(self.lte_band_combo.count() > 1)
        self.lte_band_combo.blockSignals(False)
        self._set_lte_active_band(previous, render=False)

    def _set_lte_active_band(self, file_path, *, render: bool = True):
        if file_path not in self.lte_observed_spectra:
            return
        self.lte_active_band_path = file_path
        entry = self.lte_observed_spectra[file_path]
        self.lte_observed_source_file = file_path
        self.lte_observed_frequency_mhz = np.asarray(entry["frequency_mhz"], dtype=float)
        self.lte_observed_intensity_k = np.asarray(entry["intensity_k"], dtype=float)
        self.lte_source_label.setText(
            f"{len(self.lte_observed_spectra)} banda(s) listas. Visible: "
            f"{entry.get('name') or Path(file_path).name} · "
            f"{len(self.lte_observed_frequency_mhz)} canales · {entry.get('scale', '')}. "
            "El modelo global utiliza la sesión completa."
        )
        if len(self.lte_observed_frequency_mhz) > 1:
            spacing = float(np.nanmedian(np.abs(np.diff(self.lte_observed_frequency_mhz))))
            if np.isfinite(spacing) and spacing > 0:
                self.lte_channel_spacing_mhz = spacing
                self.lte_channel_spacing_label.setText(
                    f"{spacing:.6g} MHz · muestreo, no FWHM instrumental"
                )

        payload = self.lte_last_result
        if payload:
            session_result = payload.get("session_result")
            if session_result is not None and file_path in session_result.band_results:
                payload["active_band"] = file_path
                payload["result"] = session_result.band_results[file_path]
                payload["observed"] = np.asarray(entry["intensity_k"], dtype=float)
                self._update_lte_metrics_label(payload)

        if self.lte_selected_method in {"MOD", "MTH"}:
            self.set_lte_solution_method(self.lte_selected_method)

        if not render:
            return
        if self.lte_current_view_mode == "clean" and self.lte_last_result:
            self.show_lte_clean_view()
        elif self.lte_current_view_mode == "comparison" and self.lte_last_result:
            self.show_lte_comparison_view()
        else:
            self.show_lte_observed_view()
        self.lte_log_area.append(
            f"[INFO] Banda visible: {entry.get('name') or Path(file_path).name}."
        )

    def on_lte_band_changed(self, *_):
        self._set_lte_active_band(self.lte_band_combo.currentData())

    def _update_lte_metrics_label(self, payload: dict):
        metrics = payload.get("metrics", {})
        active_path = payload.get("active_band") or self.lte_active_band_path
        band_metrics = payload.get("metrics_by_band", {}).get(active_path, {})
        active_name = Path(active_path).name if active_path else "banda activa"
        if band_metrics:
            self.lte_metrics_label.setText(
                f"{active_name}: RMS={band_metrics.get('rms_K', np.nan):.4g} K · "
                f"MAE={band_metrics.get('mae_K', np.nan):.4g} K.  "
                f"Sesión global: RMS={metrics.get('rms_K', np.nan):.4g} K · "
                f"MAE={metrics.get('mae_K', np.nan):.4g} K."
            )
            return
        chi_text = ""
        if "reduced_chi2" in metrics:
            chi_text = f" · χ²ᵣ={metrics['reduced_chi2']:.4g}"
        self.lte_metrics_label.setText(
            f"Evaluación: RMS={metrics.get('rms_K', np.nan):.4g} K · "
            f"MAE={metrics.get('mae_K', np.nan):.4g} K{chi_text}."
        )

    def apply_lte_component_workbench(self, components):
        self.lte_components = deepcopy(list(components))
        self.lte_last_result = None
        self._refresh_lte_components_list()
        enabled = sum(bool(item.get("enabled", True)) for item in self.lte_components)
        self.lte_log_area.append(
            f"[INFO] Mesa aplicada: {enabled}/{len(self.lte_components)} componente(s) activas."
        )

    def _refresh_lte_components_list(self):
        self.lte_last_result = None
        self.nonlte_last_result = None
        self.lte_export_button.setEnabled(False)
        self.nonlte_export_button.setEnabled(False)
        self.lte_view_clean_button.setEnabled(False)
        self.lte_view_comparison_button.setEnabled(False)
        self.lte_refine_button.setEnabled(False)
        self.lte_diagnostics_button.setEnabled(False)
        self.lte_diagnostics_button.setText("Diagnóstico…")
        self.lte_diagnostics_table.clear()
        self.lte_diagnostics_table.setRowCount(0)
        self.lte_diagnostics_table.setColumnCount(0)
        self.lte_diagnostics_dialog.summary.setText(
            "Genera de nuevo el modelo LTE para actualizar el diagnóstico."
        )
        self.lte_components_list.clear()
        for index, component in enumerate(self.lte_components, start=1):
            marker = "●" if component.get("enabled", True) else "○"
            self.lte_components_list.addItem(
                f"{marker} {index}. {component['label']} · "
                f"{len(component.get('transitions', []))} línea(s)"
            )
        has_components = bool(self.lte_components)
        enabled_count = sum(
            bool(item.get("enabled", True)) for item in self.lte_components
        )
        transition_count = sum(
            len(item.get("transitions", []))
            for item in self.lte_components
            if item.get("enabled", True)
        )
        if has_components:
            self.lte_components_summary_label.setText(
                f"{enabled_count}/{len(self.lte_components)} componentes moleculares activas · "
                f"{transition_count} transiciones. Una componente reúne una especie y "
                "una solución física de M3; puede producir varias líneas y aparecer en "
                "más de una banda."
            )
        else:
            self.lte_components_summary_label.setText(
                "Sin componentes. Una componente representa una especie con una "
                "solución física de M3; puede producir varias transiciones."
            )
        self.lte_clear_components_button.setEnabled(has_components)
        self.lte_edit_components_button.setEnabled(has_components)
        self.lte_remove_component_button.setEnabled(False)
        self.lte_run_button.setEnabled(
            any(item.get("enabled", True) for item in self.lte_components)
            and bool(self.lte_observed_spectra)
        )
        if not has_components:
            self.lte_last_result = None
            self.lte_refine_button.setEnabled(False)
        self._refresh_nonlte_controls()
        if self.nonlte_dialog is not None and self.nonlte_dialog.isVisible():
            self.nonlte_dialog.set_state(
                self.lte_components,
                self.nonlte_assignments,
                self.nonlte_defaults,
            )
        if (
            self.lte_component_workbench is not None
            and self.lte_component_workbench.isVisible()
        ):
            self.lte_component_workbench.set_components(self.lte_components)

    def remove_lte_component(self):
        row = self.lte_components_list.currentRow()
        if 0 <= row < len(self.lte_components):
            removed = self.lte_components.pop(row)
            self.lte_log_area.append(f"[INFO] Componente retirado: {removed['label']}")
        self._refresh_lte_components_list()

    def clear_lte_components(self):
        self.lte_components.clear()
        self._refresh_lte_components_list()
        self.lte_log_area.append("[INFO] Se vació la lista de componentes LTE.")

    def update_lte_beam_preset(self, *_):
        is_iram = self.lte_telescope_combo.currentData() == "iram30m"
        self.lte_beam_size_input.setEnabled(not is_iram)
        if not is_iram:
            return
        frequency = None
        selected_solution = self.lte_physical_solutions.get(
            self.lte_solution_combo.currentData()
        )
        if selected_solution is not None:
            frequency = selected_solution.get("rest_frequency_mhz")
            if frequency is None:
                frequency = selected_solution.get("observed_frequency_mhz")
        selected_group = self.lte_solution_groups.get(
            self.lte_solution_species_combo.currentData()
        )
        if frequency is None and selected_group is not None:
            frequency = selected_group.get("frequency_mhz")
        selected_row = self._selected_lte_species_row()
        if selected_row is not None:
            if frequency is None:
                frequency = self._finite_row_value(
                    selected_row,
                    "orderedfreq",
                    "orderedFreq",
                    "ν_obs_MHz",
                )
        if frequency is None and self.lte_observed_frequency_mhz is not None:
            finite = self.lte_observed_frequency_mhz[np.isfinite(self.lte_observed_frequency_mhz)]
            if finite.size:
                frequency = float(np.nanmedian(finite))
        if frequency is None or frequency <= 0:
            self.lte_beam_size_input.setValue(0.0)
            return
        self.lte_beam_size_input.setValue(iram_30m_hpbw_arcsec(frequency))
        self.lte_beam_size_input.setToolTip(
            f"IRAM 30 m: HPBW=2460/ν(GHz), evaluado en {frequency:.6f} MHz."
        )

    def refresh_lte_inputs(self):
        """Sincroniza espectro (M1), identificación (M2) y soluciones físicas (M3)."""

        observed_spectra = {}
        session_files = list(self.selected_files)
        if not session_files and self.selected_file:
            session_files = [self.selected_file]
        for file_path in session_files:
            try:
                state = self.spectrum_session.get(file_path, {})
                analyzed = state.get("last_result")
                frequency = None
                intensity = None
                scale_text = ""
                if analyzed is not None:
                    frequency = analyzed.get("frequency_mhz")
                    intensity = analyzed.get("baseline_corrected_intensity_k")
                    if frequency is not None and intensity is not None:
                        scale_text = "corregido por eficiencia y línea base"
                if frequency is None or intensity is None:
                    raw = state.get("raw_result") or load_raw_spectrum(file_path)
                    frequency = raw["freq"]
                    intensity = raw["inten"]
                    scale_text = "crudo; conviene analizarlo antes del modelado"
                observed_spectra[file_path] = {
                    "name": Path(file_path).name,
                    "frequency_mhz": np.asarray(frequency, dtype=float),
                    "intensity_k": np.asarray(intensity, dtype=float),
                    "scale": scale_text,
                }
            except Exception as exc:
                self.lte_log_area.append(
                    f"[ERROR] No se pudo leer {Path(file_path).name}: {exc}"
                )
        self.lte_observed_spectra = observed_spectra
        self._populate_lte_band_combo()
        active_path = self.lte_active_band_path
        active_entry = observed_spectra.get(active_path)
        if active_entry is None and observed_spectra:
            active_path, active_entry = next(iter(observed_spectra.items()))
            self.lte_active_band_path = active_path
        frequency = active_entry.get("frequency_mhz") if active_entry else None
        intensity = active_entry.get("intensity_k") if active_entry else None
        scale_text = active_entry.get("scale", "") if active_entry else ""

        if frequency is not None and intensity is not None:
            self.lte_observed_source_file = active_path
            self.lte_observed_frequency_mhz = np.asarray(frequency, dtype=float)
            self.lte_observed_intensity_k = np.asarray(intensity, dtype=float)
            file_name = active_entry.get("name", "espectro")
            self.lte_source_label.setText(
                f"{len(observed_spectra)} banda(s) listas. Visible: {file_name} · "
                f"{len(self.lte_observed_frequency_mhz)} canales · {scale_text}. "
                "El modelo global utiliza la sesión completa."
            )
            if len(self.lte_observed_frequency_mhz) > 1:
                spacing = float(np.nanmedian(np.abs(np.diff(self.lte_observed_frequency_mhz))))
                if np.isfinite(spacing) and spacing > 0:
                    self.lte_channel_spacing_mhz = spacing
                    self.lte_channel_spacing_label.setText(
                        f"{spacing:.6g} MHz · muestreo, no FWHM instrumental"
                    )
            self.lte_view_observed_button.setEnabled(True)
        else:
            self.lte_observed_source_file = None
            self.lte_observed_frequency_mhz = None
            self.lte_observed_intensity_k = None
            self.lte_channel_spacing_mhz = None
            self.lte_channel_spacing_label.setText("Pendiente de cargar el espectro")
            self.lte_source_label.setText("Carga y analiza un espectro en el módulo 1.")
            self.lte_view_observed_button.setEnabled(False)

        selected = self.get_species_selected_dataframe()
        previous_key = self.lte_species_combo.currentData()
        self.lte_species_rows = {}
        self.lte_species_combo.blockSignals(True)
        self.lte_species_combo.clear()
        if selected is not None and not selected.empty:
            for _, row in selected.iterrows():
                name = str(row.get("name", "") or row.get("chemical_name", "") or "").strip()
                if not name:
                    continue
                linelist = str(row.get("linelist", "") or "").strip().upper()
                tag = self._optional_int_from_row(row, "moleculeTag")
                species_id = self._optional_int_from_row(row, "species_id")
                key = self._lte_species_key_from_row(row)
                if key in self.lte_species_rows:
                    continue
                self.lte_species_rows[key] = row.copy()
                tag_text = tag if tag is not None else species_id
                label = f"{name} [{linelist}:{tag_text}]" if linelist else name
                self.lte_species_combo.addItem(label, key)
        if previous_key in self.lte_species_rows:
            self.lte_species_combo.setCurrentIndex(self.lte_species_combo.findData(previous_key))
        self.lte_species_combo.blockSignals(False)

        self.lte_query_button.setEnabled(False)
        self.lte_run_button.setEnabled(self._lte_model_inputs_ready())
        if not self.lte_species_rows:
            self.lte_catalog_label.setText(
                "Selecciona al menos una identificación en el TOP-K del módulo 2."
            )
        self.refresh_lte_physical_solutions()

    def on_lte_species_changed(self, *_):
        """Compatibilidad interna: M4 ahora deriva la especie desde la solución de M3."""

        self.on_lte_solution_species_changed()

    def query_lte_catalog(self):
        row = self._selected_lte_species_row()
        if row is None or self.lte_observed_frequency_mhz is None:
            self.notify_info("Sincroniza primero el espectro y la identificación molecular.")
            return

        species_name = str(row.get("name", "") or row.get("chemical_name", "") or "").strip()
        molecule_tag = self._optional_int_from_row(row, "moleculeTag")
        species_id = self._optional_int_from_row(row, "species_id")
        fmin = float(np.nanmin(self.lte_observed_frequency_mhz))
        fmax = float(np.nanmax(self.lte_observed_frequency_mhz))
        linelist = str(row.get("linelist", "") or "").strip().upper()
        line_lists = (linelist,) if linelist in {"CDMS", "JPL"} else ("CDMS", "JPL")
        self.lte_log_area.append(
            f"[INFO] Consultando {species_name} entre {fmin:.6f} y {fmax:.6f} MHz..."
        )

        def work(progress):
            progress(10, "Preparando la consulta del catálogo")
            progress(25, "Consultando transiciones en Splatalogue")
            frame = query_splatalogue_transitions(
                species_name,
                fmin,
                fmax,
                line_lists=line_lists,
                molecule_tag=molecule_tag,
                species_id=species_id,
            )
            progress(90, "Organizando las transiciones encontradas")
            return frame

        def use_fallback(reason: str):
            fallback = self._fallback_lte_transitions(row)
            if fallback.empty:
                self.lte_catalog_label.setText("No se encontraron transiciones utilizables.")
                self.lte_run_button.setEnabled(False)
                return
            self.lte_catalog_df = fallback
            selected_solution = self.lte_physical_solutions.get(
                self.lte_solution_combo.currentData(), {}
            )
            self.lte_catalog_species_key = selected_solution.get("species_key")
            self.lte_catalog_label.setText(
                f"Usando {len(fallback)} transición(es) seleccionada(s); {reason}."
            )
            self.lte_run_button.setEnabled(self._lte_model_inputs_ready())

        def on_success(frame):
            if frame is None or frame.empty:
                use_fallback("la consulta de banda no devolvió resultados")
                return
            self.lte_catalog_df = frame.copy()
            selected_solution = self.lte_physical_solutions.get(
                self.lte_solution_combo.currentData(), {}
            )
            self.lte_catalog_species_key = selected_solution.get("species_key")
            self.lte_catalog_label.setText(
                f"Catálogo de banda listo: {len(frame)} transición(es) de {species_name}."
            )
            self.lte_run_button.setEnabled(self._lte_model_inputs_ready())
            self.lte_log_area.append(f"[OK] Splatalogue devolvió {len(frame)} transiciones.")

        def on_error(message, details):
            self.lte_log_area.append(f"[WARN] Consulta de catálogo: {message}")
            use_fallback("no fue posible consultar Splatalogue")
            self.notify(
                "Catálogo no disponible",
                "Se usarán las transiciones ya seleccionadas en Identificación molecular.",
            )

        if not bool(getattr(self, "network_online", True)):
            use_fallback("modo sin Internet: se omitió Splatalogue")
            self.lte_log_area.append("[OFFLINE] Splatalogue omitido; se usan las transiciones seleccionadas en M2.")
            return

        self._start_background_task(
            "lte_catalog",
            work,
            on_success,
            on_error=on_error,
            busy_widgets=(
                self.lte_query_button,
                self.lte_run_button,
                self.lte_solution_species_combo,
                self.lte_solution_combo,
                self.lte_mod_method_button,
                self.lte_mth_method_button,
                self.lte_refresh_button,
            ),
            status_message="Consultando transiciones moleculares de la banda...",
        )

    def _build_lte_observed_plot_json(
        self,
        frequency: np.ndarray,
        observed: np.ndarray,
    ) -> str:
        figure = {
            "data": [
                {
                    "x": np.asarray(frequency, dtype=float).tolist(),
                    "y": np.asarray(observed, dtype=float).tolist(),
                    "type": "scatter",
                    "mode": "lines",
                    "name": "Espectro observado",
                    "line": {"color": "#111827", "width": 1.25},
                }
            ],
            "layout": {
                "title": "Espectro observado usado por el modelo LTE",
                "template": "plotly_white",
                "hovermode": "x unified",
                "showlegend": False,
                "margin": {"l": 68, "r": 30, "t": 55, "b": 62},
                "xaxis": {"title": "Frecuencia [MHz]"},
                "yaxis": {"title": "Temperatura [K]"},
            },
        }
        return json.dumps(figure)

    def _build_lte_plot_json(
        self,
        result,
        observed: np.ndarray,
        view_mode: str = "comparison",
        fit_result=None,
    ) -> str:
        frequency = np.asarray(result.frequency_mhz, dtype=float)
        model = np.asarray(result.brightness_temperature_k, dtype=float)
        observed = np.asarray(observed, dtype=float)
        residual = observed - model
        data = [
            {
                "x": frequency.tolist(),
                "y": observed.tolist(),
                "type": "scatter",
                "mode": "lines",
                "name": "Espectro observado",
                "line": {"color": "#111827", "width": 1.25},
                "xaxis": "x",
                "yaxis": "y",
            },
            {
                "x": frequency.tolist(),
                "y": model.tolist(),
                "type": "scatter",
                "mode": "lines",
                "name": "Modelo LTE total",
                "line": {"color": "#E67E22", "width": 2.2},
                "xaxis": "x",
                "yaxis": "y",
            },
        ]
        if fit_result is not None and fit_result.lower_envelope_k is not None:
            lower = np.asarray(fit_result.lower_envelope_k, dtype=float)
            upper = np.asarray(fit_result.upper_envelope_k, dtype=float)
            data.insert(
                1,
                {
                    "x": frequency.tolist(),
                    "y": lower.tolist(),
                    "type": "scatter",
                    "mode": "lines",
                    "name": "Intervalo aproximado 68 %",
                    "line": {"color": "rgba(230,126,34,0)", "width": 0},
                    "hoverinfo": "skip",
                    "showlegend": False,
                    "xaxis": "x",
                    "yaxis": "y",
                },
            )
            data.insert(
                2,
                {
                    "x": frequency.tolist(),
                    "y": upper.tolist(),
                    "type": "scatter",
                    "mode": "lines",
                    "name": "Intervalo aproximado 68 %",
                    "line": {"color": "rgba(230,126,34,0)", "width": 0},
                    "fill": "tonexty",
                    "fillcolor": "rgba(230,126,34,0.18)",
                    "hoverinfo": "skip",
                    "xaxis": "x",
                    "yaxis": "y",
                },
            )
        if view_mode == "comparison":
            components = getattr(result, "component_spectra_k", None)
            if components is None:
                components = result.isolated_components_k
            for label, component in list(components.items())[:30]:
                data.append(
                    {
                        "x": frequency.tolist(),
                        "y": np.asarray(component, dtype=float).tolist(),
                        "type": "scatter",
                        "mode": "lines",
                        "name": label,
                        "visible": "legendonly",
                        "opacity": 0.7,
                        "line": {"width": 1.0, "dash": "dot"},
                        "xaxis": "x",
                        "yaxis": "y",
                    }
                )
            data.append(
                {
                    "x": frequency.tolist(),
                    "y": residual.tolist(),
                    "type": "scatter",
                    "mode": "lines",
                    "name": "Residual observado − LTE",
                    "line": {"color": "#246BDE", "width": 1.1},
                    "xaxis": "x2",
                    "yaxis": "y2",
                }
            )

        if view_mode == "clean":
            layout = {
                "title": "Observado y modelo LTE total",
                "template": "plotly_white",
                "hovermode": "x unified",
                "showlegend": False,
                "margin": {"l": 68, "r": 30, "t": 55, "b": 62},
                "xaxis": {"title": "Frecuencia [MHz]"},
                "yaxis": {"title": "Temperatura [K]"},
            }
            return json.dumps({"data": data, "layout": layout})

        figure = {
            "data": data,
            "layout": {
                "title": "Comparación LTE y residuales",
                "template": "plotly_white",
                "hovermode": "x unified",
                "margin": {"l": 68, "r": 220, "t": 55, "b": 62},
                "xaxis": {"domain": [0.0, 1.0], "anchor": "y", "showticklabels": False},
                "yaxis": {"domain": [0.32, 1.0], "title": "Temperatura [K]"},
                "xaxis2": {
                    "domain": [0.0, 1.0],
                    "anchor": "y2",
                    "matches": "x",
                    "title": "Frecuencia [MHz]",
                },
                "yaxis2": {"domain": [0.0, 0.22], "title": "Residual [K]", "zeroline": True},
                "legend": {"x": 1.02, "y": 1.0, "xanchor": "left", "yanchor": "top"},
            },
        }
        return json.dumps(figure)

    def configure_lte_session_styles(self):
        entries = self._comparison_dialog_entries()
        if len(entries) >= 2:
            dialog = SpectrumComparisonDialog(entries, self.comparison_config, language=self.ui_language, parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            self.comparison_config = dialog.comparison_config()
            self._save_comparison_config()
        else:
            dialog = PlotStyleDialog(self.plot_styles, axis_config=self.axis_config, language=self.ui_language, parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            self.plot_styles = deepcopy(dialog.styles)
            self.fit_color = self.plot_styles["fits"]["color"]
            self._save_plot_styles()
        if self.lte_current_view_mode == "observed":
            self.show_lte_observed_view()
        elif self.lte_current_view_mode == "clean":
            self.show_lte_clean_view()
        elif self.lte_last_result:
            self.show_lte_comparison_view()

    def _build_lte_session_plot_json(self, payload: dict, view_mode: str) -> str:
        model_kind = str(payload.get("model_kind", "LTE"))
        model_label = "Modelo no-LTE global" if model_kind == "no-LTE" else "Modelo LTE global"
        residual_label = (
            "Residual observado − no-LTE"
            if model_kind == "no-LTE"
            else "Residual observado − LTE"
        )
        session_result = payload.get("session_result")
        if session_result is None:
            return self._build_lte_plot_json(
                payload["result"],
                payload["observed"],
                view_mode=view_mode,
                fit_result=payload.get("fit_result"),
            )
        band_results = session_result.band_results
        entries = payload.get("band_entries", {})
        active_path = (
            payload.get("active_band")
            or self.lte_active_band_path
            or next(iter(band_results), None)
        )
        if active_path not in band_results:
            active_path = next(iter(band_results), None)
        if active_path is None:
            return json.dumps({"data": [], "layout": {"template": "plotly_white"}})

        result = band_results[active_path]
        entry = entries[active_path]
        frequency = np.asarray(result.frequency_mhz, dtype=float)
        observed = np.asarray(entry["intensity_k"], dtype=float)
        model = np.asarray(result.brightness_temperature_k, dtype=float)
        residual = observed - model
        band_name = str(entry.get("name") or Path(active_path).name)
        data = []
        component_colors = {
            item["label"]: item.get("color")
            for item in payload.get("component_inputs", [])
        }
        palette = SpectrumComparisonDialog.PALETTE
        file_styles = self.comparison_config.get("files", {})
        style = file_styles.get(active_path, {}) if isinstance(file_styles, dict) else {}
        band_index = max(0, list(band_results).index(active_path))
        observed_color = str(style.get("color") or palette[band_index % len(palette)])
        observed_width = float(style.get("width", self.plot_styles["spectrum"]["width"]))
        observed_dash = str(style.get("dash", self.plot_styles["spectrum"]["dash"]))
        data.append(
            {
                "x": frequency.tolist(),
                "y": observed.tolist(),
                "type": "scatter",
                "mode": "lines",
                "name": "Espectro observado",
                "line": {
                    "color": observed_color,
                    "width": observed_width,
                    "dash": observed_dash,
                },
                "xaxis": "x",
                "yaxis": "y",
            }
        )
        if view_mode != "observed":
            data.append(
                {
                    "x": frequency.tolist(),
                    "y": model.tolist(),
                    "type": "scatter",
                    "mode": "lines",
                    "name": model_label,
                    "line": {"color": "#E67E22", "width": 2.1},
                    "xaxis": "x",
                    "yaxis": "y",
                }
            )

        if view_mode == "clean":
            return json.dumps(
                {
                    "data": data,
                    "layout": {
                        "title": f"{band_name} · observado y modelo {model_kind} global",
                        "template": "plotly_white",
                        "hovermode": "x unified",
                        "showlegend": False,
                        "margin": {"l": 72, "r": 35, "t": 55, "b": 62},
                        "xaxis": {"title": "Frecuencia [MHz]"},
                        "yaxis": {"title": "Temperatura [K]", "zeroline": True},
                    },
                }
            )

        if view_mode == "comparison":
            for label, spectrum in result.component_spectra_k.items():
                data.append(
                    {
                        "x": frequency.tolist(),
                        "y": np.asarray(spectrum, dtype=float).tolist(),
                        "type": "scatter",
                        "mode": "lines",
                        "name": label,
                        "visible": "legendonly",
                        "legendgroup": label,
                        "line": {
                            "color": component_colors.get(label),
                            "width": 1.0,
                            "dash": "dash",
                        },
                        "xaxis": "x",
                        "yaxis": "y",
                    }
                )
            data.append(
                {
                    "x": frequency.tolist(),
                    "y": residual.tolist(),
                    "type": "scatter",
                    "mode": "lines",
                    "name": residual_label,
                    "line": {"color": "#246BDE", "width": 1.0},
                    "xaxis": "x2",
                    "yaxis": "y2",
                }
            )
            layout = {
                "title": f"{band_name} · comparación {model_kind} y residuales",
                "template": "plotly_white",
                "hovermode": "x unified",
                "showlegend": True,
                "margin": {"l": 72, "r": 235, "t": 55, "b": 62},
                "xaxis": {"domain": [0.0, 1.0], "anchor": "y", "showticklabels": False},
                "yaxis": {"domain": [0.32, 1.0], "title": "Temperatura [K]"},
                "xaxis2": {
                    "domain": [0.0, 1.0],
                    "anchor": "y2",
                    "matches": "x",
                    "title": "Frecuencia [MHz]",
                },
                "yaxis2": {"domain": [0.0, 0.22], "title": "Residual [K]", "zeroline": True},
                "legend": {"x": 1.02, "y": 1.0, "xanchor": "left", "yanchor": "top"},
            }
            return json.dumps({"data": data, "layout": layout})

        layout = {
            "title": f"{band_name} · espectro observado",
            "template": "plotly_white",
            "hovermode": "x unified",
            "showlegend": False,
            "margin": {"l": 72, "r": 35, "t": 55, "b": 62},
            "xaxis": {"title": "Frecuencia [MHz]"},
            "yaxis": {"title": "Temperatura [K]", "zeroline": True},
        }
        return json.dumps({"data": data, "layout": layout})

    def show_lte_observed_view(self):
        if not self.lte_observed_spectra:
            self.notify_info("Carga o sincroniza primero un espectro.")
            return
        if len(self.lte_observed_spectra) == 1:
            self.lte_plot_json = self._build_lte_observed_plot_json(
                self.lte_observed_frequency_mhz,
                self.lte_observed_intensity_k,
            )
        else:
            placeholder_results = {}
            for file_path, entry in self.lte_observed_spectra.items():
                frequency = np.asarray(entry["frequency_mhz"], dtype=float)
                observed = np.asarray(entry["intensity_k"], dtype=float)
                placeholder_results[file_path] = type(
                    "ObservedBand",
                    (),
                    {
                        "frequency_mhz": frequency,
                        "brightness_temperature_k": np.zeros_like(observed),
                        "component_spectra_k": {},
                    },
                )()
            session = type("ObservedSession", (), {"band_results": placeholder_results})()
            self.lte_plot_json = self._build_lte_session_plot_json(
                {
                    "session_result": session,
                    "band_entries": self.lte_observed_spectra,
                    "component_inputs": [],
                    "result": next(iter(placeholder_results.values())),
                    "observed": next(iter(self.lte_observed_spectra.values()))["intensity_k"],
                },
                "observed",
            )
        self.lte_current_view_mode = "observed"
        self._render_lte_plot(self.lte_plot_json)
        self.lte_save_image_button.setEnabled(True)
        self.lte_fullscreen_button.setEnabled(True)
        self.lte_log_area.append("[INFO] Mostrando únicamente el espectro observado.")

    def show_lte_clean_view(self):
        if not self.lte_last_result:
            self.notify_info("Primero genera un modelo LTE o no-LTE.")
            return
        payload = self.lte_last_result
        self.lte_plot_json = self._build_lte_session_plot_json(payload, "clean")
        self.lte_current_view_mode = "clean"
        self._render_lte_plot(self.lte_plot_json)
        self.lte_log_area.append(
            f"[INFO] Mostrando observado y modelo {payload.get('model_kind', 'LTE')} "
            "total sin leyenda."
        )

    def show_lte_comparison_view(self):
        if not self.lte_last_result:
            self.notify_info("Primero genera un modelo LTE o no-LTE.")
            return
        payload = self.lte_last_result
        self.lte_plot_json = self._build_lte_session_plot_json(payload, "comparison")
        self.lte_current_view_mode = "comparison"
        self._render_lte_plot(self.lte_plot_json)
        self.lte_log_area.append(
            f"[INFO] Mostrando comparación {payload.get('model_kind', 'LTE')} "
            "con residuales."
        )

    def run_lte_model(self):
        if not self.lte_observed_spectra:
            self.notify_info("Actualiza primero la sesión desde los módulos 1–3.")
            return
        component_inputs = [
            deepcopy(component)
            for component in self.lte_components
            if component.get("enabled", True)
        ]
        if not component_inputs:
            self.notify_info("Activa al menos una componente LTE en la mesa de trabajo.")
            return
        band_entries = deepcopy(self.lte_observed_spectra)

        def work(progress):
            specs = []
            q_sources = {}
            for index, component in enumerate(component_inputs, start=1):
                solution = component["solution"]
                tex = float(solution["tex_k"])
                progress(
                    8 + int(45 * index / max(len(component_inputs), 1)),
                    f"Calculando Q(Tₑₓ) del componente {index}/{len(component_inputs)}",
                )
                q_value, q_source = partition_function_for_row(component["row"], tex)
                config = LTEModelConfig(
                    column_density_cm2=float(solution["column_density_cm2"]),
                    excitation_temperature_k=tex,
                    linewidth_kms=float(solution["linewidth_kms"]),
                    velocity_offset_kms=self._solution_velocity_offset(solution),
                    source_size_arcsec=component.get("source_size_arcsec"),
                    beam_size_arcsec=component.get("beam_size_arcsec"),
                    beam_model=str(component.get("beam_model", "manual")),
                    background_temperature_k=float(
                        component.get("background_temperature_k", 2.725)
                    ),
                    channel_response_fwhm_mhz=component.get(
                        "channel_response_fwhm_mhz"
                    ),
                    component_label=component["label"],
                )
                specs.append(
                    LTEComponentSpec(
                        label=component["label"],
                        transitions=component["transitions"],
                        config=config,
                        partition_function=q_value,
                        partition_source=q_source,
                        method=solution["method"],
                        solution_key=component["solution_key"],
                    )
                )
                q_sources[component["label"]] = {
                    "value": q_value,
                    "source": q_source,
                }
            progress(62, "Distribuyendo las transiciones entre las bandas observadas")
            axes = {
                file_path: entry["frequency_mhz"]
                for file_path, entry in band_entries.items()
            }
            session_result = simulate_lte_session(axes, specs)
            metrics_by_band = {}
            observed_all = []
            model_all = []
            for file_path, result in session_result.band_results.items():
                observed = np.asarray(band_entries[file_path]["intensity_k"], dtype=float)
                metrics_by_band[file_path] = lte_fit_metrics(
                    observed,
                    result.brightness_temperature_k,
                )
                observed_all.append(observed)
                model_all.append(np.asarray(result.brightness_temperature_k, dtype=float))
            metrics = lte_fit_metrics(
                np.concatenate(observed_all),
                np.concatenate(model_all),
            )
            metrics["n_spectra"] = len(session_result.band_results)
            progress(94, "Preparando diagnóstico y residuales")
            return session_result, specs, q_sources, metrics, metrics_by_band

        def on_success(payload):
            session_result, specs, q_sources, metrics, metrics_by_band = payload
            active_path = self.lte_active_band_path or self.selected_file
            if active_path not in session_result.band_results:
                active_path = next(iter(session_result.band_results))
            result = session_result.band_results[active_path]
            observed = np.asarray(band_entries[active_path]["intensity_k"], dtype=float)
            self.lte_last_result = {
                "model_kind": "LTE",
                "result": result,
                "observed": observed,
                "active_band": active_path,
                "session_result": session_result,
                "band_entries": band_entries,
                "metrics_by_band": metrics_by_band,
                "component_specs": specs,
                "m3_component_specs": specs,
                "q_sources": q_sources,
                "metrics": metrics,
                "fit_result": None,
                "component_inputs": component_inputs,
            }
            self.nonlte_last_result = None
            self._present_lte_result()
            self.notify_success(
                f"Modelo LTE global listo: {len(session_result.band_results)} espectro(s) y "
                f"{len(session_result.line_diagnostics)} transición(es) modeladas."
            )

        def on_error(message, details):
            self.lte_log_area.append(f"[ERROR] Modelo LTE: {message}")
            self.lte_log_area.append(details)
            self.notify("No se pudo generar el modelo LTE", message, duration_ms=11000)

        self._start_background_task(
            "lte_model",
            work,
            on_success,
            on_error=on_error,
            busy_widgets=(
                self.lte_run_button,
                self.lte_refine_button,
                self.lte_query_button,
                self.lte_refresh_button,
            ),
            status_message="Calculando el modelo LTE global de la sesión...",
        )

    @staticmethod
    def _solution_velocity_offset(solution: dict) -> float:
        explicit = solution.get("velocity_offset_kms")
        try:
            if explicit is not None and np.isfinite(float(explicit)):
                return float(explicit)
        except (TypeError, ValueError):
            pass
        observed = solution.get("observed_frequency_mhz")
        rest = solution.get("rest_frequency_mhz")
        if observed is None or rest is None:
            return 0.0
        try:
            return float(radio_velocity_offset_kms(observed, rest))
        except ValueError:
            return 0.0

    def _present_lte_result(self):
        payload = self.lte_last_result
        if not payload:
            return
        result = payload["result"]
        observed = np.asarray(payload["observed"], dtype=float)
        session_result = payload.get("session_result")
        diagnostics = (
            session_result.line_diagnostics.copy()
            if session_result is not None
            else result.line_diagnostics.copy()
        )
        diagnostics["tau_MTH_referencia"] = np.nan
        diagnostics["tau_LTE_sobre_MTH"] = np.nan
        for component in payload.get("component_inputs", []):
            references = component.get("reference_taus") or [
                component.get("reference_tau")
            ]
            for reference in references:
                if not reference or diagnostics.empty:
                    continue
                component_mask = diagnostics["componente"] == component["label"]
                rest_values = pd.to_numeric(
                    diagnostics.loc[component_mask, "ν_reposo_MHz"], errors="coerce"
                ).dropna()
                rest_ref = reference.get("rest_frequency_mhz")
                tau_ref = float(reference["value"])
                if rest_ref is None or rest_values.empty or tau_ref <= 0:
                    continue
                nearest = (rest_values - float(rest_ref)).abs().idxmin()
                tolerance = max(0.05, 2.0 * float(self.lte_channel_spacing_mhz or 0.0))
                if abs(float(rest_values.loc[nearest]) - float(rest_ref)) <= tolerance:
                    tau_lte = float(diagnostics.loc[nearest, "tau_pico"])
                    diagnostics.loc[nearest, "tau_MTH_referencia"] = tau_ref
                    diagnostics.loc[nearest, "tau_LTE_sobre_MTH"] = tau_lte / tau_ref

        display = diagnostics.rename(
            columns={
                "componente": "Componente",
                "método_M3": "Método M3",
                "transición": "Transición",
                "ν_reposo_MHz": "ν reposo [MHz]",
                "ν_modelo_MHz": "ν modelo [MHz]",
                "E_u_K": "Eᵤ [K]",
                "g_u": "gᵤ",
                "A_ul_s-1": "Aᵤₗ [s⁻¹]",
                "tau_pico": "τ pico",
                "HPBW_arcsec": "HPBW [″]",
                "eta_bf": "η bf",
                "tau_MTH_referencia": "τ MTH ref.",
                "tau_LTE_sobre_MTH": "τ LTE / τ MTH",
                "T_pico_aislada_K": "T pico [K]",
                "IntInt_aislada_K_km_s": "∫Tdv [K km/s]",
            }
        )
        self.populate_table_widget_from_dataframe(self.lte_diagnostics_table, display.round(6))
        metrics = payload["metrics"]
        self._update_lte_metrics_label(payload)
        q_count = len(payload.get("q_sources", {}))
        self.lte_q_label.setText(
            f"Calculada automáticamente para {q_count} componente(s). "
            "Los valores completos se conservan en la exportación y el diagnóstico."
        )
        self.lte_diagnostics_dialog.summary.setText(
            f"{len(display)} transición(es) del modelo global. La tabla incluye todas "
            "las bandas; la gráfica principal muestra una banda a la vez."
        )
        self.lte_diagnostics_button.setText(f"Diagnóstico ({len(display)})…")
        self.lte_diagnostics_button.setEnabled(True)
        band_results = (
            session_result.band_results
            if session_result is not None
            else {payload.get("active_band", "espectro"): result}
        )
        tau_max = max(float(np.nanmax(item.optical_depth)) for item in band_results.values())
        peak_model = max(
            float(np.nanmax(item.brightness_temperature_k))
            for item in band_results.values()
        )
        residual_max = 0.0
        for file_path, band_result in band_results.items():
            entry = payload.get("band_entries", {}).get(file_path)
            band_observed = (
                np.asarray(entry["intensity_k"], dtype=float)
                if entry is not None
                else observed
            )
            residual_max = max(
                residual_max,
                float(
                    np.nanmax(
                        np.abs(
                            band_observed
                            - np.asarray(band_result.brightness_temperature_k, dtype=float)
                        )
                    )
                ),
            )
        active_path = payload.get("active_band") or self.lte_active_band_path
        active_name = Path(active_path).name if active_path else "banda activa"
        self.lte_interpretation_label.setText(
            f"Vista: {active_name}. Modelo global: {len(payload['component_specs'])} "
            f"componente(s), {len(diagnostics)} transición(es) en {len(band_results)} "
            f"banda(s). τ máxima={tau_max:.3g}; pico del modelo={peak_model:.3g} K; "
            f"máximo |residual|={residual_max:.3g} K."
        )
        for label, component_result in result.component_results.items():
            if not component_result.skipped_lines.empty:
                self.lte_log_area.append(
                    f"[WARN] {label}: {len(component_result.skipped_lines)} línea(s) omitida(s)."
                )
            if np.nanmax(component_result.optical_depth) >= 0.1:
                spec = next(
                    (item for item in payload["component_specs"] if item.label == label),
                    None,
                )
                if spec is not None and spec.method == "MOD":
                    self.lte_log_area.append(
                        f"[WARN] {label}: τ LTE no es claramente delgada aunque procede de MOD."
                    )
        self.lte_log_area.append(
            f"[OK] Modelo LTE global: {len(payload['component_specs'])} componentes, "
            f"{len(band_results)} espectro(s); "
            f"RMS global={metrics['rms_K']:.4g} K."
        )
        self.lte_export_button.setEnabled(True)
        self.nonlte_export_button.setEnabled(False)
        self.lte_save_image_button.setEnabled(True)
        self.lte_fullscreen_button.setEnabled(True)
        self.lte_view_clean_button.setEnabled(True)
        self.lte_view_comparison_button.setEnabled(True)
        self.lte_refine_button.setEnabled(True)
        self.show_lte_comparison_view()

    def refine_lte_model(self):
        if not self.lte_last_result:
            self.notify_info("Genera primero el modelo LTE de referencia.")
            return
        if self.lte_last_result.get("model_kind", "LTE") != "LTE":
            self.notify_info(
                "El refinamiento automático actual corresponde al modelo LTE. "
                "Para no-LTE ajusta primero las condiciones RADEX/LAMDA."
            )
            self.open_nonlte_dialog()
            return
        session_result = self.lte_last_result.get("session_result")
        if session_result is not None and len(session_result.band_results) > 1:
            self.notify_info(
                "El refinamiento automático multibanda queda para la siguiente etapa de M4. "
                "En esta versión usa la mesa no modal para ajustar N, FWHM y Δv mientras "
                "comparas todas las bandas."
            )
            self.open_lte_component_workbench()
            return
        if not any(
            checkbox.isChecked()
            for checkbox in (
                self.lte_fit_n_checkbox,
                self.lte_fit_width_checkbox,
                self.lte_fit_velocity_checkbox,
            )
        ):
            self.notify_info("Marca al menos N, FWHM o Δv para refinar.")
            return
        payload = self.lte_last_result
        frequency = np.asarray(payload["result"].frequency_mhz, dtype=float)
        observed = np.asarray(payload["observed"], dtype=float)
        initial_specs = payload["component_specs"]
        noise = self._optional_positive(self.lte_noise_input.value())
        fit_n = self.lte_fit_n_checkbox.isChecked()
        fit_width = self.lte_fit_width_checkbox.isChecked()
        fit_velocity = self.lte_fit_velocity_checkbox.isChecked()

        def work(progress):
            progress(8, "Definiendo ventanas alrededor de las transiciones")
            progress(20, "Refinando parámetros con límites físicos")
            result = refine_lte_components(
                frequency,
                observed,
                initial_specs,
                fit_column_density=fit_n,
                fit_linewidth=fit_width,
                fit_velocity=fit_velocity,
                noise_rms_k=noise,
            )
            progress(94, "Estimando el intervalo aproximado del modelo")
            return result

        def on_success(fit_result):
            payload.setdefault("m3_component_specs", initial_specs)
            payload["component_specs"] = fit_result.refined_components
            payload["result"] = fit_result.model
            # El optimizador actual opera sobre una sola banda. Evitamos
            # conservar una vista de sesión previa que todavía contenga el
            # modelo sin refinar y dejamos que la presentación/exportación use
            # directamente el resultado optimizado de esa banda.
            payload["session_result"] = None
            payload["fit_result"] = fit_result
            payload["metrics"] = fit_result.metrics
            self.lte_last_result = payload
            self._present_lte_result()
            status = "convergió" if fit_result.metrics.get("success") else "terminó con advertencia"
            self.lte_log_area.append(
                f"[OK] El refinamiento {status}: {fit_result.metrics.get('optimizer_message', '')}"
            )
            self.notify_success("Refinamiento LTE terminado; M3 se conserva como referencia.")

        def on_error(message, details):
            self.lte_log_area.append(f"[ERROR] Refinamiento LTE: {message}")
            self.lte_log_area.append(details)
            self.notify("No se pudo refinar el modelo LTE", message, duration_ms=11000)

        self._start_background_task(
            "lte_refinement",
            work,
            on_success,
            on_error=on_error,
            busy_widgets=(self.lte_run_button, self.lte_refine_button),
            status_message="Refinando el modelo LTE en ventanas espectrales...",
        )

    def _on_lte_plot_page_loaded(self, ok: bool):
        if not ok:
            self._lte_plot_ready = False
            self.lte_log_area.append("[ERROR] No se pudo cargar el visor LTE.")
            return
        self.lte_plot_view.page().runJavaScript(
            "Boolean(window.czspecRuntimeReady)",
            self._on_lte_plot_runtime_checked,
        )

    def _on_lte_plot_runtime_checked(self, ready):
        self._lte_plot_ready = bool(ready)
        if not self._lte_plot_ready:
            self.lte_log_area.append("[ERROR] Plotly no pudo iniciar el visor LTE.")
            return
        if self._pending_lte_plot_json is not None:
            pending = self._pending_lte_plot_json
            self._pending_lte_plot_json = None
            self._render_lte_plot(pending)

    def _ensure_lte_plot_container(self):
        if self.lte_plot_view is not None:
            return
        from PySide6.QtWebEngineCore import QWebEngineSettings
        from PySide6.QtWebEngineWidgets import QWebEngineView

        self._lte_plot_ready = False
        self.lte_plot_view = QWebEngineView()
        self.lte_plot_view.setMinimumHeight(255)
        self.lte_plot_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
            True,
        )
        self.lte_plot_view.loadFinished.connect(self._on_lte_plot_page_loaded)
        self.lte_plot_stack.addWidget(self.lte_plot_view)
        self.lte_plot_stack.setCurrentWidget(self.lte_plot_view)
        self.lte_plot_view.load(
            QUrl.fromLocalFile(str(prepare_plotly_view_file()))
        )

    def _render_lte_plot(self, plot_json: str):
        if self.lte_plot_view is None:
            self._pending_lte_plot_json = plot_json
            self._ensure_lte_plot_container()
            return
        if not self._lte_plot_ready:
            self._pending_lte_plot_json = plot_json
            return
        payload = json.dumps(plot_json)
        js = (
            "(function () {"
            "if (typeof window.czspecRender !== 'function') return {ok:false};"
            f"return window.czspecRender({payload}, 'interactive', true);"
            "})();"
        )
        self.lte_plot_view.page().runJavaScript(js)

    def open_lte_fullscreen_plot(self):
        if not self.lte_plot_json:
            self.notify_info("No hay una visualización de M4 disponible.")
            return
        self.lte_fullscreen_dialog = FullScreenPlotDialog(
            self.lte_plot_json,
            "interactive",
            self,
        )
        self.lte_fullscreen_dialog.open_fullscreen()

    def export_lte_model(self):
        if not self.lte_last_result or self.lte_last_result.get("model_kind", "LTE") != "LTE":
            self.notify_info("Primero genera un modelo LTE.")
            return
        LTE_TABLES_DIR.mkdir(parents=True, exist_ok=True)
        payload = self.lte_last_result
        result = payload["result"]
        session_result = payload.get("session_result")
        output_frames = []
        if session_result is not None:
            for file_path, band_result in session_result.band_results.items():
                observed = np.asarray(
                    payload["band_entries"][file_path]["intensity_k"], dtype=float
                )
                model = np.asarray(band_result.brightness_temperature_k, dtype=float)
                output_frames.append(
                    pd.DataFrame(
                        {
                            "spectrum": Path(file_path).name,
                            "source_path": file_path,
                            "frequency_MHz": band_result.frequency_mhz,
                            "observed_K": observed,
                            "lte_model_K": model,
                            "residual_K": observed - model,
                            "tau_total": band_result.optical_depth,
                        }
                    )
                )
            output = pd.concat(output_frames, ignore_index=True)
        else:
            observed = np.asarray(payload["observed"], dtype=float)
            model = np.asarray(result.brightness_temperature_k, dtype=float)
            output = pd.DataFrame(
                {
                    "frequency_MHz": result.frequency_mhz,
                    "observed_K": observed,
                    "lte_model_K": model,
                    "residual_K": observed - model,
                    "tau_total": result.optical_depth,
                }
            )
        base = (
            f"session_{len(output_frames)}_spectra"
            if len(output_frames) > 1
            else (Path(self.selected_file).stem if self.selected_file else "spectrum")
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = LTE_TABLES_DIR / f"{base}_lte_model_{timestamp}.csv"
        lines_path = LTE_TABLES_DIR / f"{base}_lte_lines_{timestamp}.csv"
        components_path = LTE_TABLES_DIR / f"{base}_lte_components_{timestamp}.csv"
        fit_path = LTE_TABLES_DIR / f"{base}_lte_refinement_{timestamp}.csv"
        metadata_path = LTE_TABLES_DIR / f"{base}_lte_model_{timestamp}.json"
        output.to_csv(model_path, index=False)
        (
            session_result.line_diagnostics
            if session_result is not None
            else result.line_diagnostics
        ).to_csv(lines_path, index=False)
        component_rows = []
        input_by_key = {
            item.get("solution_key"): item
            for item in payload.get("component_inputs", [])
        }
        m3_specs = {
            spec.solution_key: spec
            for spec in payload.get("m3_component_specs", payload["component_specs"])
        }
        for spec in payload["component_specs"]:
            config = spec.config
            m3_config = m3_specs.get(spec.solution_key, spec).config
            component_input = input_by_key.get(spec.solution_key, {})
            initial_solution = component_input.get(
                "initial_solution",
                component_input.get("solution", {}),
            )
            component_rows.append(
                {
                    "component": spec.label,
                    "method_M3": spec.method,
                    "solution_key": spec.solution_key,
                    "partition_function": spec.partition_function,
                    "partition_source": spec.partition_source,
                    "M3_column_density_cm2": initial_solution.get(
                        "column_density_cm2", m3_config.column_density_cm2
                    ),
                    "M3_linewidth_kms": initial_solution.get(
                        "linewidth_kms", m3_config.linewidth_kms
                    ),
                    "M3_velocity_offset_kms": initial_solution.get(
                        "velocity_offset_kms", m3_config.velocity_offset_kms
                    ),
                    "M3_input_solution_count": initial_solution.get(
                        "n_input_solutions", 1
                    ),
                    "M3_member_solution_keys": ";".join(
                        initial_solution.get("member_solution_keys", [])
                    ),
                    "column_density_cm2": config.column_density_cm2,
                    "excitation_temperature_k": config.excitation_temperature_k,
                    "linewidth_kms": config.linewidth_kms,
                    "velocity_offset_kms": config.velocity_offset_kms,
                    "source_size_arcsec": config.source_size_arcsec,
                    "beam_model": config.beam_model,
                    "beam_size_arcsec": config.beam_size_arcsec,
                    "background_temperature_k": config.background_temperature_k,
                    "channel_response_fwhm_mhz": config.channel_response_fwhm_mhz,
                }
            )
        pd.DataFrame(component_rows).to_csv(components_path, index=False)
        fit_result = payload.get("fit_result")
        if fit_result is not None:
            fit_result.parameters.to_csv(fit_path, index=False)
        metadata_path.write_text(
            json.dumps(
                {
                    "czspec_version": __version__,
                    "model_geometry": (
                        "Componentes radiativamente independientes sumados en temperatura; "
                        "saturación interna por componente."
                    ),
                    "scope": "global_multispectrum" if session_result is not None else "single_spectrum",
                    "spectra": (
                        [
                            {
                                "name": Path(file_path).name,
                                "source_path": file_path,
                                "metrics": payload.get("metrics_by_band", {}).get(file_path, {}),
                            }
                            for file_path in session_result.band_results
                        ]
                        if session_result is not None
                        else [
                            {
                                "name": Path(self.selected_file).name
                                if self.selected_file
                                else "spectrum"
                            }
                        ]
                    ),
                    "components": component_rows,
                    "metrics": payload["metrics"],
                    "refinement": (
                        {
                            "performed": True,
                            "metrics": fit_result.metrics,
                            "parameter_table": fit_path.name,
                            "uncertainty_note": (
                                "Errores 1σ e intervalo 68 % aproximados desde la covarianza local "
                                "del Jacobiano; no sustituyen una inferencia posterior."
                            ),
                        }
                        if fit_result is not None
                        else {"performed": False}
                    ),
                    "files": {
                        "spectrum": model_path.name,
                        "lines": lines_path.name,
                        "components": components_path.name,
                    },
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.lte_log_area.append(f"[OK] Modelo exportado: {model_path}")
        self.notify_success(
            f"Modelo, componentes, líneas y metadatos guardados en:\n{LTE_TABLES_DIR}"
        )

    def export_nonlte_model(self):
        payload = self.nonlte_last_result
        if not payload:
            self.notify_info("Primero genera un modelo no-LTE.")
            return
        NONLTE_TABLES_DIR.mkdir(parents=True, exist_ok=True)
        session_result = payload["session_result"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"session_{len(session_result.band_results)}_spectra_nonlte_{timestamp}"
        spectrum_path = NONLTE_TABLES_DIR / f"{base}_model.csv"
        lines_path = NONLTE_TABLES_DIR / f"{base}_transitions.csv"
        components_path = NONLTE_TABLES_DIR / f"{base}_components.csv"
        omissions_path = NONLTE_TABLES_DIR / f"{base}_omissions.csv"
        metadata_path = NONLTE_TABLES_DIR / f"{base}_metadata.json"

        spectra = []
        for file_path, result in session_result.band_results.items():
            observed = np.asarray(
                payload["band_entries"][file_path]["intensity_k"], dtype=float
            )
            model = np.asarray(result.brightness_temperature_k, dtype=float)
            spectra.append(
                pd.DataFrame(
                    {
                        "spectrum": Path(file_path).name,
                        "source_path": file_path,
                        "frequency_MHz": result.frequency_mhz,
                        "observed_K": observed,
                        "nonLTE_model_K": model,
                        "residual_K": observed - model,
                        "tau_sum_independent_components": result.optical_depth,
                    }
                )
            )
        pd.concat(spectra, ignore_index=True).to_csv(spectrum_path, index=False)
        session_result.line_diagnostics.to_csv(lines_path, index=False)
        pd.DataFrame(session_result.omitted_components).to_csv(
            omissions_path, index=False
        )

        backend_by_label = {}
        for band_result in session_result.band_results.values():
            for label, result in band_result.component_results.items():
                backend_by_label.setdefault(label, result)
        component_rows = []
        for spec in payload["component_specs"]:
            backend = backend_by_label.get(spec.label)
            component_rows.append(
                {
                    "component": spec.label,
                    "method_M3": spec.method,
                    "solution_key": spec.solution_key,
                    "lamda_file": str(Path(spec.lamda_file)),
                    "lamda_sha256": backend.lamda_sha256 if backend else "",
                    "backend": "pythonradex",
                    "backend_version": backend.backend_version if backend else "",
                    "column_density_cm2": spec.column_density_cm2,
                    "kinetic_temperature_K": spec.kinetic_temperature_k,
                    "linewidth_FWHM_km_s": spec.linewidth_kms,
                    "velocity_offset_km_s": spec.velocity_offset_kms,
                    "h2_density_cm3": spec.h2_density_cm3,
                    "h2_ortho_para_ratio": spec.h2_ortho_para_ratio,
                    "additional_colliders_cm3": json.dumps(
                        dict(spec.additional_colliders_cm3 or {}), ensure_ascii=False
                    ),
                    "colliders_used_cm3": json.dumps(
                        backend.collider_densities_cm3 if backend else {},
                        ensure_ascii=False,
                    ),
                    "collision_temperature_limits_K": json.dumps(
                        backend.temperature_limits_k if backend else {},
                        ensure_ascii=False,
                    ),
                    "geometry": spec.geometry,
                    "background_temperature_K": spec.background_temperature_k,
                    "source_size_arcsec": spec.source_size_arcsec,
                    "beam_model": spec.beam_model,
                    "beam_size_arcsec": spec.beam_size_arcsec,
                    "channel_response_FWHM_MHz": spec.channel_response_fwhm_mhz,
                    "treat_line_overlap": spec.treat_line_overlap,
                    "convergence_iterations": (
                        backend.convergence_iterations if backend else None
                    ),
                }
            )
        pd.DataFrame(component_rows).to_csv(components_path, index=False)
        metadata = {
            "czspec_version": __version__,
            "model": "non-LTE statistical equilibrium",
            "backend": "pythonradex",
            "radiative_transfer_geometry": payload["nonlte_configuration"].get(
                "geometry"
            ),
            "component_combination": (
                "Emisores independientes sumados en temperatura de brillo; no se "
                "presupone un orden de capas ni absorción mutua entre componentes. "
                "La suma de tau se conserva sólo como indicador diagnóstico."
            ),
            "background_convention": (
                "El fondo externo afecta las poblaciones y se sustrae el continuo "
                "bloqueado para comparar con espectros con línea base removida."
            ),
            "units": {
                "frequency": "MHz",
                "brightness_temperature": "K (Rayleigh-Jeans)",
                "column_density": "cm^-2",
                "collider_density": "cm^-3",
                "velocity": "km s^-1",
            },
            "metrics": payload["metrics"],
            "metrics_by_band": payload["metrics_by_band"],
            "components": component_rows,
            "omissions": session_result.omitted_components,
            "files": {
                "spectra": spectrum_path.name,
                "transitions": lines_path.name,
                "components": components_path.name,
                "omissions": omissions_path.name,
            },
        }
        metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        self.lte_log_area.append(f"[OK] Modelo no-LTE exportado: {spectrum_path}")
        self.notify_success(
            f"Modelo no-LTE, diagnóstico y metadatos guardados en:\n{NONLTE_TABLES_DIR}"
        )

    def save_lte_image(self):
        if not self.lte_plot_json:
            self.notify_info("Primero genera una visualización de M4.")
            return
        try:
            model_kind = (
                self.lte_last_result.get("model_kind", "LTE")
                if self.lte_last_result
                else "observed"
            )
            output_dir = NONLTE_IMAGES_DIR if model_kind == "no-LTE" else LTE_IMAGES_DIR
            output_dir.mkdir(parents=True, exist_ok=True)
            session_result = (
                self.lte_last_result.get("session_result")
                if self.lte_last_result
                else None
            )
            base = (
                f"session_{len(session_result.band_results)}_spectra"
                if session_result is not None and len(session_result.band_results) > 1
                else (Path(self.selected_file).stem if self.selected_file else "spectrum")
            )
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            suffix = "nonlte" if model_kind == "no-LTE" else "lte"
            path = output_dir / f"{base}_{suffix}_{timestamp}.png"
            save_plot_json_to_png(self.lte_plot_json, str(path))
            self.lte_log_area.append(f"[OK] Imagen guardada: {path}")
            self.notify_success(f"Imagen de M4 guardada en:\n{path}")
        except Exception as exc:
            self.notify("No se pudo guardar la imagen", str(exc), duration_ms=10000)

    def open_species_columns_dialog(self):
        en = self.ui_language == "en"
        dialog = ColumnSelectorDialog(
            sections=[
                ("Main results" if en else "Resultados principales", self.species_table),
                ("TOP-K", self.species_topk_table),
            ],
            language=self.ui_language,
            parent=self,
        )
        dialog.exec()

    def open_species_table_plot_dialog(self):
        from czspec.gui.table_plot_dialog import TablePlotDialog
        from czspec.table_plot_data import partition_long

        main_df = (
            self.species_main_filtered_df
            if self.species_main_filtered_df is not None
            else self.species_last_main_df
        )
        topk_df = (
            self.species_topk_filtered_df
            if self.species_topk_filtered_df is not None
            else self.species_topk_df
        )
        datasets = {}
        default_dataset = None
        if main_df is not None and not main_df.empty:
            main_label = "Main results" if self.ui_language == "en" else "Resultados principales"
            datasets[main_label] = main_df.copy()
            q_long = partition_long(main_df)
            if not q_long.empty:
                default_dataset = "Q(T) · partition function" if self.ui_language == "en" else "Q(T) · función de partición"
                datasets[default_dataset] = q_long
        if topk_df is not None and not topk_df.empty:
            datasets["TOP-K"] = topk_df.drop(columns=["__source_index__"], errors="ignore").copy()
        if not datasets:
            self.notify_info("Ejecuta primero la identificación molecular para graficar sus tablas.")
            return
        # User-saved figures from Plot Tables and Final Spectrum share the
        # module-specific M2 figures folder. Generated Q(T)/spectra products
        # remain in the graphics subfolders.
        graph_directory = SPECIES_IMAGES_DIR
        dialog = TablePlotDialog(
            datasets,
            parent=self,
            default_dataset=default_dataset,
            output_directory=graph_directory,
            language=self.ui_language,
            filename_prefix=self._module_save_label("M2"),
        )
        requested_view = str(self.species_plot_view_combo.currentData() or "with_legend")
        if hasattr(dialog, "legend_combo"):
            target = "hidden" if requested_view == "no_legend" else "bottom"
            idx = dialog.legend_combo.findData(target)
            if idx >= 0:
                dialog.legend_combo.setCurrentIndex(idx)
        self._show_table_plot_dialog(dialog)


    def open_column_density_columns_dialog(self):
        en = self.ui_language == "en"
        dialog = ColumnSelectorDialog(
            sections=[
                ("M2 input" if en else "Entrada desde M2", self.column_density_source_table),
                ("OTM results" if en else "Resultados MOD", self.vasyunina_results_table),
                ("HTM results" if en else "Resultados MTH", self.sanhueza_results_table),
            ],
            language=self.ui_language,
            parent=self,
        )
        if dialog.exec() == QDialog.Accepted:
            self._sync_column_density_comparison_visibility()

    def open_column_density_table_plot_dialog(self):
        from czspec.gui.table_plot_dialog import TablePlotDialog
        from czspec.table_plot_data import mod_density_long, mth_density_long

        source_df = (
            self.column_density_source_filtered_df
            if self.column_density_filter_active
            and self.column_density_source_filtered_df is not None
            else self.column_density_source_df
        )
        mod_df = (
            self.column_density_vasyunina_filtered_df
            if self.column_density_filter_active
            and self.column_density_vasyunina_filtered_df is not None
            else self.column_density_vasyunina_df
        )
        mth_df = (
            self.column_density_sanhueza_filtered_df
            if self.column_density_filter_active
            and self.column_density_sanhueza_filtered_df is not None
            else self.column_density_sanhueza_df
        )

        en = self.ui_language == "en"
        input_label = "M2 input" if en else "Entrada desde M2"
        mod_label = "OTM results" if en else "Resultados MOD"
        mth_label = "HTM results" if en else "Resultados MTH"
        mod_n_label = "OTM · total N vs T_ex" if en else "MOD · N total vs T_ex"
        mth_n_label = "HTM · total N vs T_ex" if en else "MTH · N total vs T_ex"
        tau_label = "HTM · τ vs T_ex" if en else "MTH · τ vs T_ex"
        comparison_label = "OTM + HTM · comparison" if en else "MOD + MTH · comparación"
        datasets = {}
        if source_df is not None and not source_df.empty:
            datasets[input_label] = source_df.copy()
        if mod_df is not None and not mod_df.empty:
            datasets[mod_label] = mod_df.copy()
            mod_long = mod_density_long(mod_df)
            if not mod_long.empty:
                datasets[mod_n_label] = mod_long
        else:
            mod_long = pd.DataFrame()
        if mth_df is not None and not mth_df.empty:
            datasets[mth_label] = mth_df.copy()
            mth_long = mth_density_long(mth_df)
            if not mth_long.empty:
                datasets[mth_n_label] = mth_long
                tau_long = mth_long.dropna(subset=["τ"]).drop(
                    columns=["N_total [cm^-2]", "σ_N_total [cm^-2]"],
                    errors="ignore",
                )
                if not tau_long.empty:
                    datasets[tau_label] = tau_long
        else:
            mth_long = pd.DataFrame()
        comparable = [frame for frame in (mod_long, mth_long) if not frame.empty]
        if comparable:
            datasets[comparison_label] = pd.concat(
                comparable,
                ignore_index=True,
                sort=False,
            )
        if not datasets:
            self.notify_info("Run OTM or HTM to explore the results." if en else "Ejecuta MOD o MTH para explorar gráficamente sus resultados.")
            return

        default_dataset = next((name for name in (comparison_label, mod_n_label, mth_n_label) if name in datasets), None)
        self._show_table_plot_dialog(
            TablePlotDialog(
                datasets,
                parent=self,
                default_dataset=default_dataset,
                output_directory=COLUMN_DENSITY_IMAGES_DIR,
                language=self.ui_language,
                filename_prefix=self._module_save_label("M3"),
            )
        )

    def _show_table_plot_dialog(self, dialog):
        """Mantiene abierto el explorador sin bloquear las tablas de CZSpec."""

        dialog.setWindowModality(Qt.NonModal)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._table_plot_dialogs.append(dialog)

        def forget_dialog(*_):
            if dialog in self._table_plot_dialogs:
                self._table_plot_dialogs.remove(dialog)

        dialog.destroyed.connect(forget_dialog)
        dialog.image_saved.connect(
            lambda path: self.notify_success(f"Imagen guardada en:\n{path}")
        )
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def open_column_density_latex_folder(self):
        path = COLUMN_DENSITY_LATEX_DIR
        self._open_folder(path)

    def open_species_latex_folder(self):
        path = SPECIES_LATEX_DIR
        self._open_folder(path)

    def _get_visible_table_columns(self, table_widget: QTableWidget) -> list[str]:
        visible_columns = []

        for col in range(table_widget.columnCount()):
            if table_widget.isColumnHidden(col):
                continue

            header_item = table_widget.horizontalHeaderItem(col)
            if header_item is None:
                continue

            col_name = _table_header_internal_name(header_item).strip()
            if col_name:
                visible_columns.append(col_name)

        return visible_columns

    def _filter_dataframe_by_visible_columns(self, df: pd.DataFrame | None, table_widget: QTableWidget) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        
        df = df.copy()

        # Alias defensivos para mantener el filtro consistente
        if "Line" in df.columns and "obs_id" not in df.columns:
            df["obs_id"] = df["Line"]

        for int_col in ["obs_id", "species_id", "moleculeTag"]:
            if int_col in df.columns:
                df[int_col] = (
                    pd.to_numeric(df[int_col], errors="coerce")
                    .apply(lambda x: "" if pd.isna(x) else str(int(x)))
                )

        visible_columns = self._get_visible_table_columns(table_widget)
        if not visible_columns:
            return pd.DataFrame()

        valid_columns = [c for c in visible_columns if c in df.columns]
        if not valid_columns:
            return pd.DataFrame()

        return df[valid_columns].copy()

    def _parse_multi_search_terms(self, raw_text: str) -> list[str]:
        """
        Convierte una entrada como:
        1,2,3
        HCN;HNC
        CH3OH
        en una lista limpia de términos.
        """
        if not raw_text:
            return []

        parts = re.split(r"[,\n;]+", raw_text)
        terms = [p.strip() for p in parts if p.strip()]
        return terms

    def _field_uses_exact_match(self, field_name: str) -> bool:
        """
        Campos tipo ID deben compararse por igualdad exacta.
        """
        return field_name in {"obs_id", "species_id", "moleculeTag"}

    def _build_multi_term_mask(self, df: pd.DataFrame, field: str, terms: list[str]) -> pd.Series:
        """Máscara OR con IDs exactos/rangos y búsqueda textual parcial.

        Ejemplos válidos para IDs: ``1``, ``1,3,7`` y ``1-5``.  De esta forma
        obs_id=1 nunca captura 10/11/12 por coincidencia de texto.
        """
        if field not in df.columns or not terms:
            return pd.Series(False, index=df.index)

        series = df[field].fillna("").astype(str).str.strip()
        if self._field_uses_exact_match(field):
            numeric = pd.to_numeric(df[field], errors="coerce")
            mask = pd.Series(False, index=df.index)
            exact_terms = []
            for term in terms:
                token = term.strip()
                match = re.fullmatch(r"(-?\d+)\s*(?:-|:|\.\.)\s*(-?\d+)", token)
                if match:
                    a, b = int(match.group(1)), int(match.group(2))
                    lo, hi = sorted((a, b))
                    mask = mask | numeric.between(lo, hi, inclusive="both")
                else:
                    exact_terms.append(token.lower())
            if exact_terms:
                normalized = series.str.lower()
                normalized = normalized.str.replace(r"\.0$", "", regex=True)
                clean_terms = {re.sub(r"\.0$", "", t) for t in exact_terms if t}
                mask = mask | normalized.isin(clean_terms)
            return mask.fillna(False)

        normalized_series = series.str.lower()
        mask = pd.Series(False, index=df.index)
        for term in terms:
            token = term.strip().lower()
            if token:
                mask = mask | normalized_series.str.contains(re.escape(token), na=False)
        return mask

    def _export_dataframe_to_latex(
        self,
        df: pd.DataFrame,
        output_path: Path,
        caption: str | None = None,
        label: str | None = None,
    ) -> Path:
        """
        Exporta un DataFrame a LaTeX.
        Usa longtable para tablas largas.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        df_to_save = df.copy()

        latex_text = df_to_save.to_latex(
            index=False,
            escape=True,
            longtable=True,
            caption=caption,
            label=label,
        )

        output_path.write_text(latex_text, encoding="utf-8")
        return output_path

    def _make_safe_output_name(self, raw_name: str, fallback: str) -> str:
        value = (raw_name or "").strip()
        if not value:
            value = fallback
        value = re.sub(r"[^\w.-]+", "_", value)
        value = value.strip("._-")
        return value or fallback

    def _module_save_label(self, module: str) -> str:
        """Return the independent optional save label for M2 or M3."""
        widget = None
        if str(module).upper() == "M2":
            widget = getattr(self, "species_save_label_input", None)
        elif str(module).upper() == "M3":
            widget = getattr(self, "column_density_save_label_input", None)
        raw = str(widget.text() if widget is not None else "").strip()
        return self._make_safe_output_name(raw, "") if raw else ""

    def _module_output_stem(self, module: str, automatic: str) -> str:
        """Prefer the user's module label, otherwise keep the existing auto name."""
        label = self._module_save_label(module)
        return label or self._make_safe_output_name(automatic, str(module).lower())

    def initialize_plotly_container(self):
        if self.plot_view is None:
            from PySide6.QtWebEngineCore import QWebEngineSettings
            from PySide6.QtWebEngineWidgets import QWebEngineView

            self.plot_view = QWebEngineView()
            self.plot_view.setMinimumHeight(300)
            self.plot_view.settings().setAttribute(
                QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
                True,
            )
            self.plot_interaction_bridge = PlotInteractionBridge(self)
            self.plot_interaction_bridge.selectionReceived.connect(self._handle_plot_selection)
            self.plot_interaction_bridge.detectionRemoveRequested.connect(self._remove_detection_from_plot)
            self.plot_interaction_bridge.detectionRemoveByIdRequested.connect(self._remove_detection_by_id_from_plot)
            self.plot_interaction_bridge.detectionAddRequested.connect(self._add_detection_from_plot)
            self.plot_web_channel = QWebChannel(self.plot_view.page())
            self.plot_web_channel.registerObject("czspecBridge", self.plot_interaction_bridge)
            self.plot_view.page().setWebChannel(self.plot_web_channel)
            self.plot_view.loadFinished.connect(self._on_plot_page_loaded)
            self.plot_stack.addWidget(self.plot_view)
            self.plot_stack.setCurrentWidget(self.plot_view)
        self._plot_page_ready = False
        page_path = prepare_plotly_view_file()
        self.plot_view.load(QUrl.fromLocalFile(str(page_path)))

    def _on_plot_page_loaded(self, ok: bool):
        if not ok:
            self._plot_page_ready = False
            if hasattr(self, "log_area"):
                self.log("[ERROR] Qt WebEngine no pudo cargar el visor local de Plotly.")
            return

        self.plot_view.page().runJavaScript(
            "Boolean(window.czspecRuntimeReady)",
            self._on_plot_runtime_checked,
        )

    def _on_plot_runtime_checked(self, ready):
        self._plot_page_ready = bool(ready)
        if not self._plot_page_ready:
            if hasattr(self, "log_area"):
                self.log("[ERROR] Plotly no pudo inicializarse en el visor local.")
            return

        if hasattr(self, "log_area"):
            self.log("[OK] Visor interactivo preparado.")

        if self._pending_plot_request is not None:
            plot_json, mode, use_react = self._pending_plot_request
            self._pending_plot_request = None
            self._execute_plot_render(plot_json, mode, use_react)

    def _translate_m1_log_line(self, message: str) -> str:
        """Traducción conservadora de mensajes recurrentes del log de M1."""
        if self.ui_language == "es":
            replacements = {
                "Viewer ready.": "Visor interactivo preparado.",
                "Interactive viewer ready.": "Visor interactivo preparado.",
                "Active spectrum": "Espectro activo",
                "Analysis completed.": "Detección completada.",
                "Plot styles and axes updated.": "Estilos y ejes de la gráfica actualizados.",
                "Full spectrum restored.": "Espectro completo restaurado.",
            }
        else:
            replacements = {
                "Visor interactivo preparado.": "Interactive viewer ready.",
                "Espectro activo": "Active spectrum",
                "Detección completada.": "Analysis completed.",
                "Estilos y ejes de la gráfica actualizados.": "Plot styles and axes updated.",
                "Espectro completo restaurado.": "Full spectrum restored.",
                "Iniciando análisis": "Starting analysis",
                "Archivo:": "File:",
                "Umbral de detección": "Detection threshold",
                "Ventanas de base": "Baseline windows",
                "Buscar =": "Search =",
                "Ajuste =": "Fit =",
                "Detecciones manuales agregadas": "Manual detections added",
                "Detecciones marcadas para eliminar": "Detections marked for removal",
                "Candidatos iniciales": "Initial candidates",
                "componentes aceptadas": "accepted components",
                "recuperadas en residuales": "recovered from residuals",
                "Criterio aplicado": "Applied criterion",
                "Primeras filas del resultado": "First result rows",
            }
        result = str(message)
        for source, target in replacements.items():
            result = result.replace(source, target)
        return result

    def log(self, message: str):
        raw = str(message)
        if hasattr(self, "_m1_log_history"):
            self._m1_log_history.append(raw)
            if len(self._m1_log_history) > 2500:
                self._m1_log_history = self._m1_log_history[-2500:]
        self.log_area.append(self._translate_m1_log_line(raw))

    def _rebuild_m1_log_display(self):
        if not hasattr(self, "log_area") or not hasattr(self, "_m1_log_history"):
            return
        self.log_area.clear()
        for raw in self._m1_log_history:
            self.log_area.append(self._translate_m1_log_line(raw))

    def _apply_legend_view_mode(self, plot_json: str, mode: str) -> str:
        """Return a display-only legend variant without altering scientific data."""
        try:
            figure = json.loads(plot_json) if isinstance(plot_json, str) else deepcopy(plot_json)
        except Exception:
            return plot_json
        figure = _localize_plot_trace_names(figure, self.ui_language)
        layout = figure.setdefault("layout", {})
        margin = dict(layout.get("margin") or {})
        if mode in {"raw", "clean"}:
            layout["showlegend"] = False
            margin["r"] = max(35, min(int(margin.get("r", 35) or 35), 85))
            margin["b"] = max(60, min(int(margin.get("b", 60) or 60), 90))
            layout["margin"] = margin
            return json.dumps(figure, ensure_ascii=False)

        extended = mode == "interactive_extended"
        layout["showlegend"] = True
        category_roles = {"legend_fit_components", "legend_final_profiles", "legend_m2_vlsr"}
        individual_roles = {"fit_component", "fit", "fit_sum", "m2_vlsr_reference"}
        helper_roles = {"axis_helper", "m2_identifier"}
        for tr in figure.get("data", []) or []:
            meta = tr.get("meta") if isinstance(tr.get("meta"), dict) else {}
            role = str(meta.get("czspec_role") or "")
            if role in category_roles:
                tr["showlegend"] = not extended
            elif role in individual_roles:
                tr["showlegend"] = bool(extended)
            elif role in helper_roles or str(tr.get("name") or "").startswith("__czspec_"):
                tr["showlegend"] = False

        legend = dict(layout.get("legend") or {})
        if extended:
            legend.update({
                "orientation": "v", "x": 1.09, "xanchor": "left",
                "y": 1.0, "yanchor": "top",
                "bgcolor": "rgba(255,255,255,0.96)",
                "bordercolor": "rgba(120,130,150,0.28)", "borderwidth": 1,
                "font": {"size": 10}, "tracegroupgap": 2,
                "groupclick": "toggleitem",
            })
            margin["r"] = max(int(margin.get("r", 55) or 55), 440)
            margin["b"] = max(70, min(int(margin.get("b", 70) or 70), 110))
        else:
            legend.update({
                "orientation": "h", "x": 0.0, "xanchor": "left",
                "y": -0.16, "yanchor": "top",
                "bgcolor": "rgba(255,255,255,0.94)",
                "bordercolor": "rgba(120,130,150,0.24)", "borderwidth": 1,
                "font": {"size": 10}, "tracegroupgap": 3,
                "groupclick": "togglegroup",
            })
            margin["r"] = max(45, min(int(margin.get("r", 55) or 55), 95))
            margin["b"] = max(int(margin.get("b", 90) or 90), 118)
        layout["legend"] = legend
        layout["margin"] = margin
        return json.dumps(figure, ensure_ascii=False)

    def render_plot_full(self, plot_json: str, mode: str = "interactive"):
        if self.plot_view is None:
            self._pending_plot_request = (plot_json, mode, False)
            self.initialize_plotly_container()
            return
        if not self._plot_page_ready:
            self._pending_plot_request = (plot_json, mode, False)
            return
        self._execute_plot_render(plot_json, mode, False)

    def update_plot_in_place(self, plot_json: str, mode: str = "interactive"):
        if self.plot_view is None:
            self._pending_plot_request = (plot_json, mode, True)
            self.initialize_plotly_container()
            return
        if not self._plot_page_ready:
            self._pending_plot_request = (plot_json, mode, True)
            return
        self._execute_plot_render(plot_json, mode, True)

    def update_plot_preserving_live_view(self, plot_json: str, mode: str = "interactive"):
        """Actualiza los datos conservando el viewport *actual* del navegador.

        Es distinto de guardar rangos en Python antes de un cálculo: un diálogo no
        modal permite que el usuario siga navegando mientras el cálculo está en
        curso. La captura y el Plotly.react ocurren de forma atómica en JavaScript.
        """
        if self.plot_view is None or not self._plot_page_ready:
            self.update_plot_in_place(plot_json, mode)
            return
        # Use exactly the same M1 representation path as full/in-place renders.
        # a80 skipped _configure_m1_plot_json() here, so a local add/remove could
        # temporarily restore stale/raw secondary-axis state until another UI
        # action forced a complete render.
        configured_plot_json = self._configure_m1_plot_json(plot_json)
        configured_plot_json = self._apply_legend_view_mode(configured_plot_json, mode)
        payload = json.dumps(configured_plot_json)
        mode_value = json.dumps(mode)
        js = (
            "(function () {"
            "if (typeof window.czspecRenderPreserveView !== 'function') "
            "return {ok:false,error:'Preserve-view bridge unavailable.'};"
            f"return window.czspecRenderPreserveView({payload}, {mode_value});"
            "})();"
        )
        self.plot_view.page().runJavaScript(js, self._on_preserved_plot_rendered)

    def _on_preserved_plot_rendered(self, result):
        if isinstance(result, dict) and result.get("ok") is False:
            self.log(f"[ERROR] Visor Plotly: {result.get('error', 'error desconocido')}")
            return
        if isinstance(result, dict) and isinstance(result.get("ranges"), dict):
            self.current_view_ranges = result.get("ranges")
            if self.selected_file in self.spectrum_session:
                self.spectrum_session[self.selected_file]["current_view_ranges"] = self.current_view_ranges

    @staticmethod
    def _velocity_spec_from_metadata(metadata: dict | None, fallback_f0_mhz: float | None = None) -> dict | None:
        """Return the frequency->velocity transform used only for M1 display axes.

        This deliberately separates two concepts that had become conflated in
        the alpha.65--alpha.74 work:

        * CLASS spectral-axis calibration (FREQUENCY, VELOCITY, FREQ_STEP,
          VELO_STEP), which defines how the frequency and velocity coordinates
          of the *same channels* correspond; and
        * physical source/transition metadata (VLSR and rest frequency), which
          belong to line interpretation and are not required to draw the axes.

        For CLASS products we reproduce the native linear channel calibration.
        For other spectra, when no native velocity calibration exists, M1 may
        still show a relative radio-velocity coordinate around the available
        spectral reference (or the current band centre as a display fallback).
        """
        meta = dict(metadata or {})

        def finite_value(value):
            try:
                value = float(value)
                return value if np.isfinite(value) else None
            except Exception:
                return None

        # New explicit CLASS axis keys (a75+).
        f0 = finite_value(meta.get("class_reference_frequency_mhz"))
        v0 = finite_value(meta.get("class_reference_velocity_kms"))
        df = finite_value(meta.get("class_frequency_step_mhz"))
        dv = finite_value(meta.get("class_velocity_step_kms"))

        # Backward compatibility for .dat files generated by older alpha
        # versions.  Only use the legacy aliases when the provenance clearly
        # identifies a CLASS import, so ordinary source VLSR/rest-frequency
        # metadata cannot accidentally redefine the display axis.
        provenance = meta.get("provenance") or {}
        is_class = (
            isinstance(provenance, dict) and bool(provenance.get("class_header"))
        ) or "CLASS" in str(meta.get("spectral_reference_frame") or "").upper() \
          or "CLASS" in str(meta.get("spectral_axis_calibration") or "").upper()
        # Older CZSpec CLASS exports may predate the explicit ``class_*`` keys
        # and/or provenance marker. A complete four-value channel calibration is
        # nevertheless unambiguous and is safe to reuse; a lone VLSR or rest
        # frequency is never enough.
        legacy_f0 = finite_value(meta.get("rest_frequency_mhz"))
        legacy_v0 = finite_value(meta.get("vlsr_kms"))
        legacy_df = finite_value(meta.get("frequency_step_mhz"))
        legacy_dv = finite_value(meta.get("velocity_step_kms"))
        if is_class and f0 is None:
            f0 = legacy_f0
        if is_class and v0 is None:
            v0 = legacy_v0
        if is_class and df is None:
            df = legacy_df
        if is_class and dv is None:
            dv = legacy_dv

        if f0 is not None and f0 > 0 and v0 is not None and df not in (None, 0.0) and dv is not None:
            return {
                "mode": "linear",
                "f0_mhz": f0,
                "v0_kms": v0,
                "slope_kms_per_mhz": dv / df,
                "source": str(meta.get("class_axis_source") or "class_header"),
            }

        # Never let an unrelated generic reference frequency replace an
        # incomplete CLASS calibration.  A CLASS product either reproduces the
        # native CLASS F/V geometry or reports velocity as unavailable.
        if is_class:
            return None

        # Generic spectra: use a display-only radio velocity offset.  This is
        # NOT the source VLSR and does not claim identification of a transition.
        axis_f0 = finite_value(meta.get("spectral_axis_reference_frequency_mhz"))
        if axis_f0 is None:
            axis_f0 = finite_value(fallback_f0_mhz)
        if axis_f0 is not None and axis_f0 > 0:
            return {
                "mode": "radio",
                "f0_mhz": axis_f0,
                "c_kms": 299792.458,
                "source": "display_reference",
            }
        return None

    def _current_plot_metadata(self, state: dict | None = None) -> dict:
        if state is not None:
            return self._active_analysis_metadata(state)
        if not self.selected_file or self.selected_file not in self.spectrum_session:
            return {}
        return self._active_analysis_metadata(self.spectrum_session[self.selected_file])

    def _localize_plot_dict(self, figure: dict) -> dict:
        """Traduce textos estructurales de M1 sin tocar valores científicos."""
        en = self.ui_language == "en"
        layout = figure.setdefault("layout", {})
        title = layout.get("title")
        if isinstance(title, dict):
            title_text = str(title.get("text") or "")
        else:
            title_text = str(title or "")
        replacements = (
            ("Espectro original - ", "Original spectrum - "),
            ("Original spectrum - ", "Espectro original - "),
            ("Detección y ajuste de líneas espectrales - ", "Spectral-line detection and fitting - "),
            ("Spectral-line detection and fitting - ", "Detección y ajuste de líneas espectrales - "),
        )
        if en:
            title_text = title_text.replace(replacements[0][0], replacements[0][1]).replace(replacements[2][0], replacements[2][1])
        else:
            title_text = title_text.replace(replacements[1][0], replacements[1][1]).replace(replacements[3][0], replacements[3][1])
        if isinstance(title, dict):
            title["text"] = title_text
        elif title is not None:
            layout["title"] = title_text
        name_map_es_en = {
            "Espectro original":"Original spectrum", "Espectro":"Spectrum",
            "Línea base":"Baseline", "Espectro corregido":"Baseline-corrected spectrum",
            "Detecciones":"Detections", "Ajustes":"Fits",
        }
        reverse = {v:k for k,v in name_map_es_en.items()}
        mapping = name_map_es_en if en else reverse
        for trace in figure.get("data", []) or []:
            name = str(trace.get("name") or "")
            if name in mapping:
                trace["name"] = mapping[name]
        return figure

    @staticmethod
    def _scale_plotly_numeric_payload(value, factor: float):
        """Scale Plotly numeric arrays, including Plotly 6 typed-array JSON."""
        if factor == 1.0 or value is None:
            return value
        if isinstance(value, (int, float, np.integer, np.floating)):
            try:
                return float(value) * factor if np.isfinite(float(value)) else value
            except Exception:
                return value
        if isinstance(value, (list, tuple)):
            return [MainWindow._scale_plotly_numeric_payload(v, factor) for v in value]
        if isinstance(value, dict) and "bdata" in value and "dtype" in value:
            try:
                raw = base64.b64decode(str(value["bdata"]))
                arr = np.frombuffer(raw, dtype=np.dtype(str(value["dtype"])))
                shape = value.get("shape")
                if shape:
                    if isinstance(shape, str):
                        dims = tuple(int(v.strip()) for v in shape.split(",") if v.strip())
                    else:
                        dims = tuple(int(v) for v in shape)
                    if dims:
                        arr = arr.reshape(dims)
                return (arr.astype(float) * factor).tolist()
            except Exception:
                return value
        return value

    @staticmethod
    def _metadata_intensity_unit(metadata: dict | None) -> str:
        meta = dict(metadata or {})
        return normalize_intensity_unit(
            meta.get("bunit") or meta.get("intensity_unit") or meta.get("input_intensity_unit")
        )

    @staticmethod
    def _plot_frequency_values(trace: dict, key: str = "x"):
        """Decode a Plotly numeric payload (including Plotly 6 typed arrays)."""
        values = trace.get(key)
        if isinstance(values, list):
            try:
                arr = np.asarray(values, dtype=float)
                return arr if arr.ndim == 1 else None
            except Exception:
                return None
        if isinstance(values, dict) and "bdata" in values and "dtype" in values:
            try:
                raw = base64.b64decode(str(values["bdata"]))
                arr = np.frombuffer(raw, dtype=np.dtype(str(values["dtype"]))).astype(float)
                return arr
            except Exception:
                return None
        return None

    def _rj_temperature_display(self, figure: dict, source_unit: str, target_unit: str) -> bool:
        """Convert temperature traces to spectral radiance with Rayleigh–Jeans.

        This is a display-only conversion.  It does not pretend that K is an
        integrated flux density in Jy; the output remains explicitly per sr.
        """
        temp_scale = {"K":1.0, "mK":1.0e-3, "µK":1.0e-6}
        if source_unit not in temp_scale or target_unit not in {"Jy/sr","MJy/sr","W m⁻² Hz⁻¹ sr⁻¹"}:
            return False
        k_b = 1.380649e-23; c = 299792458.0
        target_scale = {"Jy/sr":1.0e26, "MJy/sr":1.0e20, "W m⁻² Hz⁻¹ sr⁻¹":1.0}[target_unit]
        any_trace = False
        representative_factor = None
        for trace in figure.get("data", []) or []:
            freq = self._plot_frequency_values(trace)
            y = trace.get("y")
            yy = self._plot_frequency_values({"x": y})
            if freq is None or yy is None:
                continue
            if yy.ndim != 1 or yy.size != freq.size:
                continue
            nu_hz = freq * 1.0e6
            factor = temp_scale[source_unit] * (2.0*k_b*nu_hz*nu_hz/(c*c)) * target_scale
            trace["y"] = (yy * factor).tolist()
            if factor.size:
                representative_factor = float(np.nanmedian(factor))
            any_trace = True
        if any_trace and representative_factor is not None and np.isfinite(representative_factor):
            layout = figure.setdefault("layout", {})
            yaxis = layout.setdefault("yaxis", {})
            if isinstance(yaxis.get("range"), (list, tuple)) and len(yaxis["range"]) == 2:
                yaxis["range"] = self._scale_plotly_numeric_payload(yaxis["range"], representative_factor)
            for ann in layout.get("annotations", []) or []:
                if str(ann.get("yref", "y")) in {"y","y1"}:
                    ann["y"] = self._scale_plotly_numeric_payload(ann.get("y"), representative_factor)
            for shape in layout.get("shapes", []) or []:
                if str(shape.get("yref", "y")) in {"y","y1"}:
                    shape["y0"] = self._scale_plotly_numeric_payload(shape.get("y0"), representative_factor)
                    shape["y1"] = self._scale_plotly_numeric_payload(shape.get("y1"), representative_factor)
        return any_trace

    def _apply_intensity_display_unit(self, figure: dict, state: dict | None, config: dict) -> tuple[dict, dict]:
        """Apply direct intensity-unit conversions to the rendered figure only.

        The underlying spectrum, fitted parameters and exported scientific table
        stay in their analysis unit.  Only the visual representation is scaled.
        """
        metadata = self._current_plot_metadata(state)
        source_unit = self._metadata_intensity_unit(metadata)
        requested = str(config.get("intensity_unit") or "native")
        conversion = intensity_conversion_factor(source_unit, requested)
        used_rj = False
        if requested == "native":
            effective_unit = source_unit
            factor = 1.0
        elif conversion is None and source_unit in {"K","mK","µK"} and requested in {"Jy/sr","MJy/sr","W m⁻² Hz⁻¹ sr⁻¹"}:
            used_rj = self._rj_temperature_display(figure, source_unit, requested)
            effective_unit = requested if used_rj else source_unit
            factor = 1.0
            if not used_rj:
                config = dict(config); config["intensity_unit"] = "native"
        elif conversion is None:
            effective_unit = source_unit
            factor = 1.0
            config = dict(config)
            config["intensity_unit"] = "native"
        else:
            factor, effective_unit = conversion
            factor = float(factor)

        if factor != 1.0 and not used_rj:
            for trace in figure.get("data", []) or []:
                trace["y"] = self._scale_plotly_numeric_payload(trace.get("y"), factor)
                hover = trace.get("hovertemplate")
                if isinstance(hover, str) and effective_unit:
                    # Keep the scientific values and their displayed unit in sync.
                    hover = re.sub(r"(?i)(Intensidad|Intensity|T)=%\{y([^}]*)\}(?:\s*[^<]*)?", r"\1=%{y\2} " + effective_unit, hover)
                    trace["hovertemplate"] = hover
            layout = figure.setdefault("layout", {})
            yaxis = layout.setdefault("yaxis", {})
            if isinstance(yaxis.get("range"), (list, tuple)) and len(yaxis["range"]) == 2:
                yaxis["range"] = self._scale_plotly_numeric_payload(yaxis["range"], factor)
            if yaxis.get("tickvals") is not None:
                yaxis["tickvals"] = self._scale_plotly_numeric_payload(yaxis.get("tickvals"), factor)
            for ann in layout.get("annotations", []) or []:
                if str(ann.get("yref", "y")) in {"y", "y1"}:
                    ann["y"] = self._scale_plotly_numeric_payload(ann.get("y"), factor)
            for shape in layout.get("shapes", []) or []:
                if str(shape.get("yref", "y")) in {"y", "y1"}:
                    shape["y0"] = self._scale_plotly_numeric_payload(shape.get("y0"), factor)
                    shape["y1"] = self._scale_plotly_numeric_payload(shape.get("y1"), factor)

        custom_intensity_title = str(config.get("intensity_axis_title") or "").strip()
        preset = str(config.get("intensity_axis_title_preset") or "auto")
        en = self.ui_language == "en"
        preset_labels = {
            "intensity": "Intensity" if en else "Intensidad",
            "antenna_temperature": "Antenna temperature" if en else "Temperatura de antena",
            "ta_star": "T<sub>A</sub>*",
            "tmb": "T<sub>MB</sub>",
            "tb": "T<sub>B</sub>",
        }
        base_label = custom_intensity_title or preset_labels.get(preset) or ("Intensity" if en else "Intensidad")
        if effective_unit and "[" not in base_label:
            label = f"{base_label} [{effective_unit}]"
        elif base_label:
            label = base_label
        else:
            label = "Intensity [input unit]" if en else "Intensidad [unidad de entrada]"
        yaxis = figure.setdefault("layout", {}).setdefault("yaxis", {})
        title = yaxis.get("title")
        if isinstance(title, dict):
            title["text"] = label
        else:
            yaxis["title"] = {"text": label}
        config = dict(config)
        config["effective_intensity_unit"] = effective_unit or ""
        config["intensity_scale_factor"] = factor
        secondary_requested = str(config.get("secondary_intensity_unit") or "none")
        config["secondary_intensity_factor"] = None
        config["secondary_intensity_effective_unit"] = ""
        config["secondary_intensity_reference_frequency_mhz"] = None
        if secondary_requested not in {"", "none", "None"} and effective_unit:
            secondary_target = source_unit if secondary_requested == "native" else secondary_requested
            secondary_conversion = intensity_conversion_factor(effective_unit, secondary_target)
            reference_frequency_mhz = None
            if secondary_conversion is None:
                freqs=[]
                for tr in figure.get("data", []) or []:
                    if str(tr.get("name") or "").startswith("__czspec_"):
                        continue
                    arr=self._plot_frequency_values(tr,"x")
                    if arr is not None:
                        freqs.extend(arr[np.isfinite(arr)].tolist())
                if freqs:
                    reference_frequency_mhz=float(np.nanmedian(freqs))
                    secondary_conversion = intensity_conversion_factor_at_frequency(effective_unit, secondary_target, reference_frequency_mhz)
            if secondary_conversion is not None:
                secondary_factor, secondary_unit = secondary_conversion
                if secondary_unit != effective_unit:
                    config["secondary_intensity_factor"] = float(secondary_factor)
                    config["secondary_intensity_effective_unit"] = str(secondary_unit or "")
                    if reference_frequency_mhz is not None:
                        config["secondary_intensity_reference_frequency_mhz"] = reference_frequency_mhz
        return figure, config

    def _configure_m1_plot_json(self, plot_json: str, state: dict | None = None, axis_config_override: dict | None = None) -> str:
        """Aplica idioma/orientación/ejes a una copia del JSON Plotly.

        Las trazas conservan frecuencia en MHz como coordenada espectral
        canónica. El visor genera etiquetas de frecuencia/velocidad/longitud de
        onda dinámicamente, por lo que el zoom sigue siendo exacto.
        """
        try:
            figure = json.loads(plot_json) if isinstance(plot_json, str) else deepcopy(plot_json)
        except Exception:
            return plot_json
        figure = self._localize_plot_dict(figure)
        # A comparison figure owns xaxis/xaxis2/... as independent subplot axes.
        # Reusing xaxis2 as the secondary spectral axis destroys the subplot
        # geometry, which was the visual regression seen in a71. Comparisons keep
        # their own frequency/intensity subplot layout.
        if bool((figure.get("layout") or {}).get("meta", {}).get("czspec_comparison")):
            return json.dumps(figure, ensure_ascii=False)
        config = deepcopy(PlotStyleDialog.DEFAULT_AXIS_CONFIG)
        config.update(axis_config_override if isinstance(axis_config_override, dict) else (self.axis_config or {}))
        figure, config = self._apply_intensity_display_unit(figure, state, config)
        layout = figure.setdefault("layout", {})

        graph_title_mode = str(config.get("graph_title_mode") or "auto")
        graph_title = str(config.get("graph_title") or "").strip()
        if graph_title_mode == "none":
            layout.pop("title", None)
        elif graph_title_mode == "custom":
            if graph_title:
                layout["title"] = {"text": graph_title, "x": 0.5, "xanchor": "center"}
            else:
                layout.pop("title", None)
        # In automatic mode retain the canonical plot title already generated
        # by the scientific plot builder.

        # a73: VLSR remains metadata only. Never render the old VLSR label/line
        # because it can distort autorange after Analyze All and is conceptually
        # separate from the frequency↔velocity display transform.
        layout["annotations"] = [
            ann for ann in (layout.get("annotations") or [])
            if "VLSR" not in str(ann.get("text") or "").upper()
        ]
        # Legacy VLSR reference shapes were thin dotted vertical lines. Remove
        # only the explicitly tagged legacy shape when present; newer baseline
        # selection regions and other scientific shapes are preserved.
        layout["shapes"] = [
            sh for sh in (layout.get("shapes") or [])
            if not bool((sh.get("meta") or {}).get("czspec_vlsr_reference"))
        ]

        meta = dict(layout.get("meta") or {})
        fallback_f0 = None
        try:
            for tr in figure.get("data", []) or []:
                arr = self._plot_frequency_values(tr)
                if arr is not None:
                    finite = arr[np.isfinite(arr)]
                    if finite.size:
                        fallback_f0 = float(np.nanmedian(finite)); break
        except Exception:
            fallback_f0 = None
        # The plot itself carries the CLASS/generic frequency<->velocity
        # transform that was active when this exact spectrum was built.  Use
        # that immutable snapshot first.  Falling back to the currently active
        # session metadata can otherwise make the secondary axis change after
        # a local edit, spectrum switch, or background Analyze All render.
        embedded_velocity_spec = meta.get("czspec_velocity_axis")
        if not isinstance(embedded_velocity_spec, dict):
            embedded_velocity_spec = None
        velocity_spec = embedded_velocity_spec or self._velocity_spec_from_metadata(
            self._current_plot_metadata(state), None
        )
        meta["czspec_spectral_axes"] = {
            **config,
            "language": self.ui_language,
            "velocity_spec": velocity_spec,
        }
        layout["meta"] = meta

        # Las etiquetas L1...LN se identifican por su texto, por lo que pueden
        # ocultarse sin afectar otras anotaciones científicas.
        if not bool(config.get("show_detection_labels", True)):
            layout["annotations"] = [
                ann for ann in (layout.get("annotations") or [])
                if not re.fullmatch(r"L\d+", str(ann.get("text") or ""))
            ]

        orientation = str(config.get("orientation") or "horizontal")
        # El eje secundario legacy de velocidad se reconstruye en runtime.
        figure["data"] = [
            tr for tr in (figure.get("data") or [])
            if str(tr.get("name") or "") not in {"__velocity_axis__", "__czspec_secondary_axis__", "__czspec_secondary_intensity_axis__"}
        ]
        layout.pop("xaxis2", None)
        layout.pop("yaxis2", None)
        if orientation == "vertical":
            for tr in figure.get("data", []) or []:
                tr["x"], tr["y"] = tr.get("y"), tr.get("x")
                tr.pop("xaxis", None); tr.pop("yaxis", None)
            old_x = deepcopy(layout.get("xaxis") or {})
            old_y = deepcopy(layout.get("yaxis") or {})
            layout["xaxis"] = old_y
            layout["yaxis"] = old_x
            for shape in layout.get("shapes", []) or []:
                x0, x1, y0, y1 = shape.get("x0"), shape.get("x1"), shape.get("y0"), shape.get("y1")
                xref, yref = shape.get("xref", "x"), shape.get("yref", "y")
                shape["x0"], shape["x1"], shape["y0"], shape["y1"] = y0, y1, x0, x1
                shape["xref"], shape["yref"] = yref, xref
            for ann in layout.get("annotations", []) or []:
                ann["x"], ann["y"] = ann.get("y"), ann.get("x")
                ann["xref"], ann["yref"] = ann.get("yref", "y"), ann.get("xref", "x")
                if re.fullmatch(r"L\d+", str(ann.get("text") or "")):
                    ann["textangle"] = -45

        # Force the secondary Plotly axis with a real in-range helper trace.
        # Plotly 6 serializes large numpy arrays as typed-array objects; the old
        # JavaScript Array.isArray check therefore failed and the requested top/
        # right axis simply did not exist.  Decoding happens here in Python, so
        # the helper always contains ordinary finite lists.
        secondary = str(config.get("secondary_spectral") or "none")
        if secondary != "none" and secondary != str(config.get("primary_spectral") or "frequency"):
            spectral_key = "y" if orientation == "vertical" else "x"
            orth_key = "x" if orientation == "vertical" else "y"
            spectral = None
            orth = None
            for tr in figure.get("data", []) or []:
                if str(tr.get("name") or "").startswith("__czspec_"):
                    continue
                arr = self._plot_frequency_values(tr, spectral_key)
                if arr is not None:
                    finite = arr[np.isfinite(arr)]
                    if finite.size >= 2:
                        spectral = finite
                        oarr = self._plot_frequency_values(tr, orth_key)
                        if oarr is not None:
                            ofinite = oarr[np.isfinite(oarr)]
                            if ofinite.size:
                                orth = float(ofinite[len(ofinite)//2])
                        break
            if spectral is not None:
                lo, hi = float(np.nanmin(spectral)), float(np.nanmax(spectral))
                if np.isfinite(lo) and np.isfinite(hi) and lo != hi:
                    if orth is None or not np.isfinite(orth):
                        orth = 0.0
                    if orientation == "vertical":
                        layout["yaxis2"] = {
                            "overlaying":"y", "side":"right", "anchor":"x",
                            "range":[lo,hi], "autorange":False, "visible":False,
                            "showgrid":False, "showline":True, "linecolor":"#94A3B8",
                            "linewidth":1, "ticks":"outside", "ticklen":4,
                            "tickcolor":"#94A3B8", "automargin":True,
                        }
                        figure["data"].append({
                            "x":[orth,orth], "y":[lo,hi], "type":"scatter",
                            "mode":"markers", "marker":{"opacity":0.0,"size":1},
                            "xaxis":"x", "yaxis":"y2", "showlegend":False,
                            "hoverinfo":"skip", "name":"__czspec_secondary_axis__",
                            "meta":{"czspec_role":"axis_helper"},
                        })
                    else:
                        layout["xaxis2"] = {
                            "overlaying":"x", "side":"top", "anchor":"y",
                            "range":[lo,hi], "autorange":False, "visible":False,
                            "showgrid":False, "showline":True, "linecolor":"#94A3B8",
                            "linewidth":1, "ticks":"outside", "ticklen":4,
                            "tickcolor":"#94A3B8", "automargin":True,
                        }
                        figure["data"].append({
                            "x":[lo,hi], "y":[orth,orth], "type":"scatter",
                            "mode":"markers", "marker":{"opacity":0.0,"size":1},
                            "xaxis":"x2", "yaxis":"y", "showlegend":False,
                            "hoverinfo":"skip", "name":"__czspec_secondary_axis__",
                            "meta":{"czspec_role":"axis_helper"},
                        })

        # A secondary intensity axis is a display-only linear conversion of the
        # already rendered intensity coordinate. It is valid only when the unit
        # conversion has one constant factor (K<->mK<->µK, Jy prefixes, etc.).
        secondary_intensity_factor = config.get("secondary_intensity_factor")
        try:
            secondary_intensity_factor = float(secondary_intensity_factor)
        except Exception:
            secondary_intensity_factor = None
        if secondary_intensity_factor not in (None, 0.0) and np.isfinite(secondary_intensity_factor):
            if orientation == "vertical":
                # intensity is the horizontal coordinate
                xaxis = layout.get("xaxis") or {}
                xrange = xaxis.get("range")
                if not (isinstance(xrange, (list, tuple)) and len(xrange) == 2):
                    vals = []
                    for tr in figure.get("data", []) or []:
                        if str(tr.get("name") or "").startswith("__czspec_"):
                            continue
                        arr = self._plot_frequency_values(tr, "x")
                        if arr is not None: vals.extend(arr[np.isfinite(arr)].tolist())
                    xrange = [min(vals), max(vals)] if vals else None
                if xrange and np.isfinite(xrange[0]) and np.isfinite(xrange[1]) and xrange[0] != xrange[1]:
                    layout["xaxis2"] = {
                        "overlaying":"x", "side":"top", "anchor":"y", "range":[float(xrange[0]),float(xrange[1])],
                        "autorange":False, "visible":False, "showgrid":False, "showline":True,
                        "linecolor":"#94A3B8", "linewidth":1, "ticks":"outside", "ticklen":4,
                        "tickcolor":"#94A3B8", "automargin":True,
                    }
                    # Keep the invisible helper entirely inside the current
                    # scientific spectral range.  Using a synthetic y=0 helper
                    # can expand the orthogonal autorange when the actual
                    # spectral coordinate is far from zero.
                    yvals=[]
                    for tr in figure.get("data", []) or []:
                        if str(tr.get("name") or "").startswith("__czspec_"):
                            continue
                        arr=self._plot_frequency_values(tr,"y")
                        if arr is not None:
                            yvals.extend(arr[np.isfinite(arr)].tolist())
                    y0=float(np.nanmedian(yvals)) if yvals else 0.0
                    figure["data"].append({
                        "x":[float(xrange[0]),float(xrange[1])], "y":[y0,y0], "type":"scatter", "mode":"markers",
                        "marker":{"opacity":0.0,"size":1}, "xaxis":"x2", "yaxis":"y", "showlegend":False,
                        "hoverinfo":"skip", "name":"__czspec_secondary_intensity_axis__", "meta":{"czspec_role":"axis_helper"},
                    })
                    margin=layout.setdefault("margin",{})
                    margin["t"]=max(float(margin.get("t") or 0),95)
            else:
                yaxis = layout.get("yaxis") or {}
                yrange = yaxis.get("range")
                if not (isinstance(yrange, (list, tuple)) and len(yrange) == 2):
                    vals = []
                    for tr in figure.get("data", []) or []:
                        if str(tr.get("name") or "").startswith("__czspec_"):
                            continue
                        arr = self._plot_frequency_values(tr, "y")
                        if arr is not None: vals.extend(arr[np.isfinite(arr)].tolist())
                    yrange = [min(vals), max(vals)] if vals else None
                if yrange and np.isfinite(yrange[0]) and np.isfinite(yrange[1]) and yrange[0] != yrange[1]:
                    layout["yaxis2"] = {
                        "overlaying":"y", "side":"right", "anchor":"x", "range":[float(yrange[0]),float(yrange[1])],
                        "autorange":False, "visible":False, "showgrid":False, "showline":True,
                        "linecolor":"#94A3B8", "linewidth":1, "ticks":"outside", "ticklen":4,
                        "tickcolor":"#94A3B8", "automargin":True,
                    }
                    # The old x=0 helper forced Plotly to include zero in the
                    # primary frequency autorange.  For spectra around tens or
                    # hundreds of GHz this compressed the real data into a thin
                    # strip at the right edge.  Anchor the helper at a real
                    # in-range spectral coordinate instead.
                    xvals=[]
                    for tr in figure.get("data", []) or []:
                        if str(tr.get("name") or "").startswith("__czspec_"):
                            continue
                        arr=self._plot_frequency_values(tr,"x")
                        if arr is not None:
                            xvals.extend(arr[np.isfinite(arr)].tolist())
                    if xvals:
                        x0=float(np.nanmedian(xvals))
                    else:
                        xr=(layout.get("xaxis") or {}).get("range")
                        x0=float(0.5*(xr[0]+xr[1])) if isinstance(xr,(list,tuple)) and len(xr)==2 else 0.0
                    figure["data"].append({
                        "x":[x0,x0], "y":[float(yrange[0]),float(yrange[1])], "type":"scatter", "mode":"markers",
                        "marker":{"opacity":0.0,"size":1}, "xaxis":"x", "yaxis":"y2", "showlegend":False,
                        "hoverinfo":"skip", "name":"__czspec_secondary_intensity_axis__", "meta":{"czspec_role":"axis_helper"},
                    })
                    margin=layout.setdefault("margin",{})
                    margin["r"]=max(float(margin.get("r") or 0),105)
        return json.dumps(figure, ensure_ascii=False)

    def _refresh_current_plot_language(self):
        if not self.current_plot_json:
            return
        # Canonical JSON remains unchanged; render-time localization allows
        # switching language without recomputing fits.
        try:
            self.update_plot_in_place(self.current_plot_json, self.current_view_mode or "interactive")
        except Exception:
            pass

    def _execute_plot_render(self, plot_json: str, mode: str, use_react: bool):
        configured_plot_json = self._configure_m1_plot_json(plot_json)
        configured_plot_json = self._apply_legend_view_mode(configured_plot_json, mode)
        payload = json.dumps(configured_plot_json)
        mode_value = json.dumps(mode)
        use_react_value = "true" if use_react else "false"
        js = (
            "(function () {"
            "if (typeof window.czspecRender !== 'function') "
            "return {ok:false,error:'El puente de visualización no está disponible.'};"
            f"return window.czspecRender({payload}, {mode_value}, {use_react_value});"
            "})();"
        )
        self.plot_view.page().runJavaScript(js, self._on_plot_rendered)

    def _on_plot_rendered(self, result):
        if isinstance(result, dict) and result.get("ok") is False:
            self.log(f"[ERROR] Visor Plotly: {result.get('error', 'error desconocido')}")

    def _set_m1_view_combo(self, data: str):
        if not hasattr(self, "m1_view_combo"):
            return
        idx = self.m1_view_combo.findData(data)
        if idx >= 0 and idx != self.m1_view_combo.currentIndex():
            blocked = self.m1_view_combo.blockSignals(True)
            self.m1_view_combo.setCurrentIndex(idx)
            self.m1_view_combo.blockSignals(blocked)

    def show_raw_view(self):
        if not self.raw_plot_json:
            self.notify_info("No hay espectro crudo cargado.")
            return

        self.render_plot_full(self.raw_plot_json, mode="raw")
        self.current_plot_json = self.raw_plot_json
        self.current_view_mode = "raw"
        self._set_m1_view_combo("raw")
        self.log("[INFO] Mostrando espectro crudo.")

    def show_analyzed_clean_view(self):
        if not self.analyzed_clean_plot_json:
            self.notify_info("Primero ejecuta un análisis.")
            return

        self.render_plot_full(self.analyzed_clean_plot_json, mode="clean")
        self.current_plot_json = self.analyzed_clean_plot_json
        self.current_view_mode = "clean"
        self._set_m1_view_combo("no_legend")
        self.log("[INFO] Mostrando análisis sin leyenda.")

    def show_analyzed_interactive_view(self):
        if not self.analyzed_plot_json:
            self.notify_info("Primero ejecuta un análisis.")
            return

        self.render_plot_full(self.analyzed_plot_json, mode="interactive")
        self.current_plot_json = self.analyzed_plot_json
        self.current_view_mode = "interactive"
        self._set_m1_view_combo("with_legend")
        self.log("[INFO] Mostrando análisis con leyenda compacta.")

    def show_analyzed_extended_view(self):
        if not self.analyzed_plot_json:
            self.notify_info("Primero ejecuta un análisis.")
            return
        self.render_plot_full(self.analyzed_plot_json, mode="interactive_extended")
        self.current_plot_json = self.analyzed_plot_json
        self.current_view_mode = "interactive_extended"
        self._set_m1_view_combo("with_legend_extended")
        self.log("[INFO] Mostrando análisis con leyenda extendida.")

    def _m1_view_changed(self, _index=None):
        mode = str(self.m1_view_combo.currentData() or "raw")
        if mode == "raw":
            self.show_raw_view()
        elif mode == "no_legend":
            self.show_analyzed_clean_view()
        elif mode == "with_legend_extended":
            self.show_analyzed_extended_view()
        else:
            self.show_analyzed_interactive_view()

    def _save_active_spectrum_state(self):
        if not self.selected_file or self.selected_file not in self.spectrum_session:
            return
        state = self.spectrum_session[self.selected_file]
        values = {
            "last_result": self.last_result,
            "raw_plot_json": self.raw_plot_json,
            "analyzed_plot_json": self.analyzed_plot_json,
            "analyzed_clean_plot_json": self.analyzed_clean_plot_json,
            "manual_peak_freqs": list(self.manual_peak_freqs),
            "removed_peak_freqs": list(self.removed_peak_freqs),
            "removed_detection_ids": list(self.removed_detection_ids),
            "current_view_ranges": self.current_view_ranges,
        }
        if self.current_view_mode != "comparison":
            values["current_plot_json"] = self.current_plot_json
            values["current_view_mode"] = self.current_view_mode
        state.update(values)

    def _activate_spectrum(
        self,
        file_path: str,
        *,
        render: bool = True,
        save_current: bool = True,
    ):
        if file_path not in self.spectrum_session:
            return
        if save_current:
            self._save_active_spectrum_state()
        state = self.spectrum_session[file_path]
        self.selected_file = file_path
        self.last_result = state.get("last_result")
        self.raw_plot_json = state.get("raw_plot_json")
        self.analyzed_plot_json = state.get("analyzed_plot_json")
        self.analyzed_clean_plot_json = state.get("analyzed_clean_plot_json")
        self.current_plot_json = state.get("current_plot_json") or self.raw_plot_json
        self.current_view_mode = state.get("current_view_mode") or "raw"
        self.manual_peak_freqs = list(state.get("manual_peak_freqs", []))
        self.removed_peak_freqs = list(state.get("removed_peak_freqs", []))
        self.removed_detection_ids = list(state.get("removed_detection_ids", []))
        self.current_view_ranges = state.get("current_view_ranges")

        position = self.selected_files.index(file_path) + 1
        self.file_label.setText(
            (f"Active spectrum {position}/{len(self.selected_files)}: " if self.ui_language == "en" else f"Espectro activo {position}/{len(self.selected_files)}: ")
            + self._spectrum_display_name(file_path)
        )
        result = self.last_result or {}
        self._populate_detections(result.get("detected_peak_items", []))
        has_df = result.get("results_df") is not None and not result.get("results_df").empty
        self.export_csv_button.setEnabled(bool(has_df))
        self.export_html_button.setEnabled(bool(self.raw_plot_json or result.get("plot_html")))
        self.refresh_button.setEnabled(True)
        self.smooth_button.setEnabled(True)
        self.source_metadata_button.setEnabled(True)
        self.calibration_button.setEnabled(True)
        self._update_calibration_summary()
        self._propagate_source_physics_defaults(state.get("source_metadata") or {})
        self._update_extraction_nav_buttons()

        if render and self.current_plot_json:
            mode = self.current_view_mode
            if mode == "comparison":
                mode = "raw"
            self.render_plot_full(self.current_plot_json, mode=mode)
            view_data = {"raw":"raw", "clean":"no_legend", "interactive":"with_legend", "interactive_extended":"with_legend_extended"}.get(mode, "raw")
            self._set_m1_view_combo(view_data)
        self.refresh_lte_inputs()

    def _spectrum_display_name(self, file_path: str) -> str:
        state = self.spectrum_session.get(str(file_path), {})
        return str(state.get("display_name") or Path(file_path).name)

    def _spectrum_selection_changed(self, index: int):
        if self._switching_spectrum or index < 0:
            return
        file_path = self.spectrum_selector.itemData(index)
        if file_path:
            self._activate_spectrum(str(file_path))
            self.log(f"[INFO] Espectro activo: {self._spectrum_display_name(str(file_path))}")

    def _comparison_dialog_entries(self) -> list[dict]:
        entries = []
        for file_path in self.selected_files:
            state = self.spectrum_session.get(file_path, {})
            entries.append({
                "path": file_path,
                "name": self._spectrum_display_name(file_path),
                "analyzed": bool(state.get("last_result")),
            })
        return entries

    def _comparison_spectra_from_config(self, config: dict) -> tuple[list[dict], list[str]]:
        content = str(config.get("content", "raw"))
        file_styles = config.get("files", {})
        if not isinstance(file_styles, dict):
            file_styles = {}
        spectra = []
        omitted = []
        for index, file_path in enumerate(self.selected_files):
            result = {}
            style = file_styles.get(file_path, {})
            if isinstance(style, dict) and not bool(style.get("included", True)):
                continue
            state = self.spectrum_session.get(file_path, {})
            if content in {"analyzed", "analyzed_fits"}:
                result = state.get("last_result") or {}
                frequency = result.get("frequency_mhz")
                intensity = result.get("baseline_corrected_intensity_k")
                if frequency is None or intensity is None:
                    omitted.append(self._spectrum_display_name(file_path))
                    continue
            else:
                raw = state.get("raw_result") or {}
                frequency = raw.get("freq")
                intensity = raw.get("inten")
                if frequency is None or intensity is None:
                    omitted.append(self._spectrum_display_name(file_path))
                    continue
            detection_points = []
            if content in {"analyzed", "analyzed_fits"} and result:
                freq_arr = np.asarray(result.get("frequency_mhz") if result.get("frequency_mhz") is not None else frequency, dtype=float)
                corr_arr = np.asarray(result.get("baseline_corrected_intensity_k") if result.get("baseline_corrected_intensity_k") is not None else intensity, dtype=float)
                for visual_index, det in enumerate(list(result.get("detected_peak_items") or []), start=1):
                    try:
                        xdet = float(det.get("fit_freq", det.get("freq")))
                        ydet = float(np.interp(xdet, freq_arr, corr_arr))
                        lno = int(det.get("line_no", visual_index))
                        if np.isfinite(xdet) and np.isfinite(ydet):
                            detection_points.append({"x": xdet, "y": ydet, "line": lno})
                    except Exception:
                        continue
            spectra.append({
                "name": self._spectrum_display_name(file_path),
                "freq": frequency,
                "inten": intensity,
                "color": style.get("color") if isinstance(style, dict) else None,
                "width": style.get("width", self.plot_styles["spectrum"]["width"])
                if isinstance(style, dict) else self.plot_styles["spectrum"]["width"],
                "dash": style.get("dash", self.plot_styles["spectrum"]["dash"])
                if isinstance(style, dict) else self.plot_styles["spectrum"]["dash"],
                "order": index,
                "fit_traces": result.get("fit_plot_traces", [])
                if content == "analyzed_fits" else [],
                "detection_points": detection_points,
                "metadata": self._active_analysis_metadata(state),
            })
        return spectra, omitted

    def show_spectrum_comparison(self, configure: bool = True):
        self._save_active_spectrum_state()
        if len(self.selected_files) < 2:
            self.notify_info("Load at least two spectra to compare them." if self.ui_language == "en" else "Carga al menos dos espectros para compararlos.")
            return

        if configure:
            dialog = SpectrumComparisonDialog(
                self._comparison_dialog_entries(),
                self.comparison_config,
                language=self.ui_language,
                parent=self,
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            self.comparison_config = dialog.comparison_config()
            self._save_comparison_config()

        spectra, omitted = self._comparison_spectra_from_config(self.comparison_config)
        if len(spectra) < 2:
            content = self.comparison_config.get("content", "raw")
            if self.ui_language == "en":
                message = (
                    "Analyzed comparison requires at least two already-analyzed files."
                    if content in {"analyzed", "analyzed_fits"}
                    else "Select at least two available spectra."
                )
            else:
                message = (
                    "La comparación analizada requiere al menos dos archivos ya analizados."
                    if content in {"analyzed", "analyzed_fits"}
                    else "Selecciona al menos dos espectros disponibles."
                )
            self.notify_info(message)
            return
        content_labels = ({
            "raw": "raw",
            "analyzed": "analyzed (baseline-corrected)",
            "analyzed_fits": "analyzed with fitted profiles",
        } if self.ui_language == "en" else {
            "raw": "crudos",
            "analyzed": "analizados (corregidos por línea base)",
            "analyzed_fits": "analizados con perfiles ajustados",
        })
        content_label = content_labels.get(
            self.comparison_config.get("content"), "raw" if self.ui_language == "en" else "crudos"
        )
        self.comparison_plot_json = build_spectrum_comparison(
            spectra,
            plot_styles=self.plot_styles,
            layout_mode=self.comparison_config.get("layout", "auto"),
            share_x=bool(self.comparison_config.get("share_x", False)),
            share_y=bool(self.comparison_config.get("share_y", True)),
            show_sum=bool(self.comparison_config.get("show_sum", False)),
            sum_styles=deepcopy(self.comparison_config.get("sum_styles", [])),
            axis_config=deepcopy(self.axis_config),
            content_label=content_label,
            language=self.ui_language,
        )
        self.render_plot_full(self.comparison_plot_json, mode="interactive")
        self.current_plot_json = self.comparison_plot_json
        self.current_view_mode = "comparison"
        self.log(
            (f"[INFO] Comparing {len(spectra)} {content_label} spectra; layout={self.comparison_config.get('layout', 'auto')}."
             if self.ui_language == "en" else
             f"[INFO] Comparando {len(spectra)} espectros {content_label}; disposición={self.comparison_config.get('layout', 'auto')}.")
        )
        if omitted:
            self.log(
                (("[WARN] Files omitted because the requested data are unavailable: " if self.ui_language == "en" else
                  "[WARN] Se omitieron archivos sin los datos solicitados: ") + ", ".join(omitted))
            )

    @staticmethod
    def _smoothing_label(method: str, value=None) -> str:
        method = str(method or "none").lower()
        if method == "hanning":
            return "Smooth Hanning"
        if method == "box":
            return f"Smooth Box {int(value or 2)} ch"
        if method == "gauss":
            return f"Smooth Gauss {float(value or 1.0):g} km/s"
        return "Sin suavizado"

    @staticmethod
    def _invalidate_session_state_after_smoothing(state: dict):
        """Descarta resultados M1 almacenados para un espectro modificado."""
        state.update({
            "last_result": None,
            "analyzed_plot_json": None,
            "analyzed_clean_plot_json": None,
            "manual_peak_freqs": [],
            "removed_peak_freqs": [],
            "removed_detection_ids": [],
            "current_view_ranges": None,
            "current_view_mode": "raw",
            "current_plot_json": state.get("raw_plot_json"),
        })

    def _invalidate_active_analysis_after_smoothing(self, state: dict):
        """Descarta resultados M1 del espectro activo y sincroniza la GUI."""
        self._invalidate_session_state_after_smoothing(state)
        self.last_result = None
        self.analyzed_plot_json = None
        self.analyzed_clean_plot_json = None
        self.manual_peak_freqs = []
        self.removed_peak_freqs = []
        self.removed_detection_ids = []
        self.current_view_ranges = None
        self.current_view_mode = "raw"
        self.current_plot_json = state.get("raw_plot_json")
        self.export_csv_button.setEnabled(False)
        self.export_html_button.setEnabled(bool(state.get("raw_plot_json")))
        self._populate_detections([])

    def open_smoothing_dialog(self):
        """Abre un panel no modal; el usuario puede seguir haciendo zoom en Plotly."""
        if not self.selected_file or self.selected_file not in self.spectrum_session:
            self.notify_info(
                "Primero carga un espectro." if self.ui_language == "es" else "Load a spectrum first."
            )
            return

        state = self.spectrum_session[self.selected_file]
        if self.smoothing_dialog is not None:
            try:
                self.smoothing_dialog.close()
            except Exception:
                pass
        self.smoothing_dialog = SpectrumSmoothingDialog(
            "CZSpec native" if self.ui_language == "en" else "CZSpec nativo",
            state.get("smoothing_meta"),
            self,
            language=self.ui_language,
            spectrum_count=len(self.selected_files),
        )
        self.smoothing_dialog.applyRequested.connect(self._request_smoothing)
        self.smoothing_dialog.applyAllRequested.connect(self._request_smoothing_all)
        self.smoothing_dialog.finished.connect(lambda *_: setattr(self, "smoothing_dialog", None))
        self.smoothing_dialog.show()
        self.smoothing_dialog.raise_()
        self.smoothing_dialog.activateWindow()

    def _request_smoothing(self, config: dict):
        """Solicita el suavizado sin congelar prematuramente el viewport.

        La ventana es no modal, por lo que el usuario puede seguir haciendo zoom o
        paneo mientras se calcula el suavizado. El viewport se captura dentro del
        navegador justo cuando se sustituye la traza, no al pulsar «Aplicar».
        """
        if not self.selected_file or self.selected_file not in self.spectrum_session:
            return
        if self.smoothing_dialog is not None:
            self.smoothing_dialog.set_busy(True)
        self._apply_smoothing_configuration(config)

    def _request_smoothing_all(self, config: dict):
        """Aplica el mismo suavizado, desde cada espectro base, a toda la sesión."""
        targets = [
            str(key) for key in self.selected_files
            if str(key) in self.spectrum_session
        ]
        if not targets:
            return
        if len(targets) == 1:
            self._request_smoothing(config)
            return
        if self.smoothing_dialog is not None:
            self.smoothing_dialog.set_busy(True)
        self._apply_smoothing_configuration_all(config, targets)

    @staticmethod
    def _plot_json_with_ranges(plot_json: str, ranges: dict | None) -> str:
        if not ranges:
            return plot_json
        try:
            figure = json.loads(plot_json)
            layout = figure.setdefault("layout", {})
            layout["uirevision"] = "czspec-m1-spectrum-view"
            xr = ranges.get("xaxis_range") if isinstance(ranges, dict) else None
            yr = ranges.get("yaxis_range") if isinstance(ranges, dict) else None
            if xr and len(xr) == 2:
                axis = layout.setdefault("xaxis", {})
                axis["range"] = [float(xr[0]), float(xr[1])]
                axis["autorange"] = False
            if yr and len(yr) == 2:
                axis = layout.setdefault("yaxis", {})
                axis["range"] = [float(yr[0]), float(yr[1])]
                axis["autorange"] = False
            return json.dumps(figure)
        except Exception:
            return plot_json

    def _apply_smoothing_configuration(self, config: dict):
        """Aplica suavizado nativo. Hanning puede acumularse por pases sucesivos."""
        if not self.selected_file or self.selected_file not in self.spectrum_session:
            if self.smoothing_dialog is not None:
                self.smoothing_dialog.set_busy(False)
            return
        state = self.spectrum_session[self.selected_file]
        method = str(config.get("smooth_method") or "none")
        value = config.get("smooth_value")
        selected_key = str(self.selected_file)
        original_path = str(state.get("original_analysis_path") or selected_key)
        base_display_name = str(state.get("base_display_name") or Path(selected_key).name)
        plot_styles = deepcopy(self.plot_styles)
        prior_meta = dict(state.get("smoothing_meta") or {})
        prior_hanning = int(prior_meta.get("hanning_passes") or 0) if prior_meta.get("smooth_method") == "hanning" else 0
        # Sólo Hanning encadena el producto Hanning anterior. BOX/Gauss y el primer
        # Hanning parten del producto base, tal como se documenta en el diálogo.
        input_path = str(state.get("analysis_path") or original_path) if method == "hanning" and prior_hanning > 0 else original_path
        hanning_passes = prior_hanning + 1 if method == "hanning" else 0
        input_metadata = deepcopy(self._active_analysis_metadata(state))

        def work(progress):
            if method == "none":
                progress(25, "Restaurando espectro sin suavizado" if self.ui_language == "es" else "Restoring unsmoothed spectrum")
                path = original_path
                display_name = base_display_name
                smooth_meta = {"smooth_method":"none","smooth_value":None,"smooth_engine":"czspec-native","hanning_passes":0}
            else:
                label = (f"Hanning ×{hanning_passes}" if method == "hanning" else self._smoothing_label(method, value))
                progress(20, (f"CZSpec: aplicando {label}" if self.ui_language == "es" else f"CZSpec: applying {label}"))
                outdir = TEMP_DIR / "smoothing"; outdir.mkdir(parents=True, exist_ok=True)
                safe = re.sub(r"[^A-Za-z0-9_.+-]+", "_", Path(selected_key).stem).strip("_") or "spectrum"
                value_tag = "" if value is None else "_" + str(value).replace(".", "p")
                pass_tag = f"_x{hanning_passes}" if method == "hanning" else ""
                output_path = outdir / f"{safe}_{method}{pass_tag}{value_tag}.dat"
                native = smooth_ascii_spectrum(input_path, str(output_path), method, value)
                path = str(native["path"])
                display_name = f"{base_display_name} · {label}"
                smooth_meta = {
                    "smooth_method":method,"smooth_value":value,"smooth_engine":native.get("smooth_engine","czspec-native"),
                    "channel_spacing_kms":native.get("channel_spacing_kms"),"smoothing_note":native.get("smoothing_note"),
                    "hanning_passes":hanning_passes,
                }
            progress(75, "Actualizando gráfica" if self.ui_language == "es" else "Updating plot")
            raw = load_raw_spectrum(path, plot_styles=plot_styles, display_name=display_name, input_metadata=input_metadata, language=self.ui_language)
            progress(98, "Preparando sesión" if self.ui_language == "es" else "Preparing session")
            return {"path":path,"raw":raw,"display_name":display_name,"smooth_meta":smooth_meta}

        def on_success(payload):
            target=self.spectrum_session.get(selected_key)
            if target is None:return
            raw=payload["raw"]
            target.update({"analysis_path":str(payload["path"]),"raw_result":raw,"raw_plot_json":raw["plot_json"],
                           "current_plot_json":raw["plot_json"],"display_name":str(payload["display_name"]),
                           "class30m_meta":deepcopy(target.get("base_class30m_meta")),"smoothing_meta":dict(payload.get("smooth_meta") or {})})
            target["extraction_history"]=[{"path":str(payload["path"]),"display_name":str(payload["display_name"])}]
            target["extraction_index"]=0
            if self.selected_file==selected_key:
                self.raw_plot_json=raw["plot_json"]
                self._invalidate_active_analysis_after_smoothing(target)
                self.current_plot_json=self.raw_plot_json; target["current_plot_json"]=self.raw_plot_json
                self.update_plot_preserving_live_view(self.raw_plot_json, mode="raw")
                self._update_extraction_nav_buttons()
                idx=self.spectrum_selector.currentIndex()
                if idx>=0:
                    pos=self.selected_files.index(selected_key)+1; self.spectrum_selector.setItemText(idx,f"{pos}. {target['display_name']}")
                pos=self.selected_files.index(selected_key)+1
                self.file_label.setText((f"Active spectrum {pos}/{len(self.selected_files)}: " if self.ui_language=="en" else f"Espectro activo {pos}/{len(self.selected_files)}: ")+target['display_name'])
                self.refresh_lte_inputs()
            self.comparison_plot_json=None
            passes=int(target.get("smoothing_meta",{}).get("hanning_passes") or 0)
            label=f"Hanning ×{passes}" if method=="hanning" else self._smoothing_label(method,value)
            self.log((f"[OK] {label} aplicado (motor=CZSpec nativo)." if self.ui_language=="es" else f"[OK] {label} applied (engine=CZSpec native)."))
            self.notify_success((f"{label} aplicado; el análisis previo fue invalidado." if self.ui_language=="es" else f"{label} applied; the previous analysis was invalidated."))
            if self.smoothing_dialog is not None:self.smoothing_dialog.set_busy(False)

        def on_error(message,details):
            self.log(f"[ERROR] Smoothing: {message}"); self.log(details); self.notify("Error",message)
            if self.smoothing_dialog is not None:self.smoothing_dialog.set_busy(False)

        self._start_background_task("smooth_spectrum",work,on_success,on_error=on_error,busy_widgets=(self.run_button,),
            status_message="Suavizando espectro con CZSpec..." if self.ui_language=="es" else "Smoothing spectrum with CZSpec...")

    def _apply_smoothing_configuration_all(self, config: dict, target_keys: list[str]):
        """Aplica a la sesión; Hanning avanza un pase por espectro en cada Apply all."""
        method=str(config.get("smooth_method") or "none"); value=config.get("smooth_value")
        plot_styles=deepcopy(self.plot_styles); active_key=str(self.selected_file) if self.selected_file else None
        targets=[k for k in target_keys if k in self.spectrum_session]
        snapshots={}
        for key in targets:
            st=self.spectrum_session[key]; meta=dict(st.get("smoothing_meta") or {})
            prior=int(meta.get("hanning_passes") or 0) if meta.get("smooth_method")=="hanning" else 0
            snapshots[key]={"original":str(st.get("original_analysis_path") or key),"current":str(st.get("analysis_path") or key),
                            "base":str(st.get("base_display_name") or Path(key).name),"prior":prior,
                            "metadata":deepcopy(self._active_analysis_metadata(st))}
        def smooth_one(key):
            snap=snapshots[key]; prior=snap["prior"]
            if method=="none":
                path=snap["original"]; display=snap["base"]; sm={"smooth_method":"none","smooth_value":None,"smooth_engine":"czspec-native","hanning_passes":0}
            else:
                hp=prior+1 if method=="hanning" else 0
                input_path=snap["current"] if method=="hanning" and prior>0 else snap["original"]
                outdir=TEMP_DIR/"smoothing"; outdir.mkdir(parents=True,exist_ok=True)
                safe=re.sub(r"[^A-Za-z0-9_.+-]+","_",Path(key).stem).strip("_") or "spectrum"; digest=hashlib.sha1(key.encode()).hexdigest()[:8]
                tag=f"_x{hp}" if method=="hanning" else ("" if value is None else "_"+str(value).replace(".","p"))
                out=outdir/f"{safe}_{digest}_{method}{tag}.dat"; native=smooth_ascii_spectrum(input_path,str(out),method,value); path=str(native["path"])
                label=f"Hanning ×{hp}" if method=="hanning" else self._smoothing_label(method,value); display=f"{snap['base']} · {label}"
                sm={"smooth_method":method,"smooth_value":value,"smooth_engine":native.get("smooth_engine","czspec-native"),"channel_spacing_kms":native.get("channel_spacing_kms"),"smoothing_note":native.get("smoothing_note"),"hanning_passes":hp}
            raw=load_raw_spectrum(path,plot_styles=plot_styles,display_name=display,input_metadata=snap["metadata"],language=self.ui_language)
            return {"key":key,"path":path,"raw":raw,"display_name":display,"smooth_meta":sm}
        def work(progress):
            results=[];fail=[];total=max(1,len(targets))
            for i,key in enumerate(targets,1):
                progress(5+int(88*(i-1)/total),(f"Suavizando {i}/{total}" if self.ui_language=="es" else f"Smoothing {i}/{total}"))
                try:results.append(smooth_one(key))
                except Exception as exc:fail.append({"key":key,"error":str(exc),"details":traceback.format_exc()})
            progress(98,"Actualizando sesión" if self.ui_language=="es" else "Updating session");return {"results":results,"failures":fail}
        def on_success(payload):
            updated=set()
            for item in payload["results"]:
                key=item["key"]; st=self.spectrum_session.get(key)
                if st is None:continue
                raw=item["raw"]; st.update({"analysis_path":item["path"],"raw_result":raw,"raw_plot_json":raw["plot_json"],"current_plot_json":raw["plot_json"],"display_name":item["display_name"],"smoothing_meta":item["smooth_meta"],"class30m_meta":deepcopy(st.get("base_class30m_meta"))})
                st["extraction_history"]=[{"path":item["path"],"display_name":item["display_name"]}]; st["extraction_index"]=0
                self._invalidate_session_state_after_smoothing(st);updated.add(key)
            for i,key in enumerate(self.selected_files):
                st=self.spectrum_session.get(str(key))
                if st is not None and i<self.spectrum_selector.count():self.spectrum_selector.setItemText(i,f"{i+1}. {st.get('display_name') or Path(str(key)).name}")
            if active_key in updated:
                self._activate_spectrum(active_key,render=True,save_current=False);self._update_extraction_nav_buttons()
            self.comparison_plot_json=None
            for f in payload["failures"]:self.log(f"[ERROR] {f['key']}: {f['error']}");self.log(f["details"])
            self.notify_success((f"Suavizado aplicado a {len(payload['results'])} espectro(s)." if self.ui_language=="es" else f"Smoothing applied to {len(payload['results'])} spectrum/spectra.")) if not payload["failures"] else self.notify_info(f"{len(payload['failures'])} error(es); revisa el log.")
            if self.smoothing_dialog is not None:self.smoothing_dialog.set_busy(False)
        def on_error(message,details):
            self.log(f"[ERROR] {message}");self.log(details)
            if self.smoothing_dialog is not None:self.smoothing_dialog.set_busy(False)
        self._start_background_task("smooth_all_spectra",work,on_success,on_error=on_error,busy_widgets=(self.run_button,self.analyze_all_button),status_message="Suavizando sesión..." if self.ui_language=="es" else "Smoothing session...")

    def _finalize_loaded_spectrum_session(self, loaded, failures, comparison):
        """Instala en la GUI resultados cargados desde ASCII o desde CLASS .30m."""
        normalized = []
        for item in loaded:
            if len(item) >= 3:
                file_path, raw_result, meta = item[0], item[1], item[2] or {}
            else:
                file_path, raw_result = item[0], item[1]
                meta = {}
            normalized.append((str(file_path), raw_result, dict(meta)))

        self.selected_files = [path for path, _, _ in normalized]
        self.spectrum_session = {}
        self.comparison_plot_json = comparison
        for file_path, raw_result, meta in normalized:
            display_name = str(meta.get("display_name") or Path(file_path).name)
            class_meta = deepcopy(meta.get("class30m_meta")) if meta.get("class30m_meta") else None
            raw_meta = {k: deepcopy(v) for k, v in raw_result.items() if k not in {"freq", "inten", "plot_json", "plot_html"}}
            source_meta = merge_source_metadata(raw_meta, class_meta, meta.get("fits_meta"), meta.get("source_metadata"))
            try:
                registry_hit = source_registry().match(
                    str(source_meta.get("raw_source_name") or source_meta.get("source") or ""),
                    source_meta.get("ra_deg"), source_meta.get("dec_deg"),
                )
                source_meta = merge_source_metadata(source_meta, registry_hit)
            except Exception:
                pass
            canonical = str(source_meta.get("canonical_name") or "").strip()
            raw_alias = str(source_meta.get("raw_source_name") or "").strip()
            if canonical:
                if raw_alias and raw_alias.lower() in display_name.lower():
                    display_name = re.sub(re.escape(raw_alias), canonical, display_name, count=1, flags=re.IGNORECASE)
                elif canonical.lower() not in display_name.lower():
                    display_name = f"{canonical} · {display_name}"
            # raw_result ya fue construido en el worker de carga (incluido CLASS/.30m).
            # No se vuelve a leer aquí: hacerlo en el hilo GUI duplicaba el parseo del
            # espectro, provocando pausas largas especialmente con archivos .30m.
            # Conservamos los metadatos fusionados en el estado; el JSON crudo ya
            # contiene la geometría espectral calculada durante la importación.
            self.spectrum_session[file_path] = {
                "raw_result": raw_result,
                "raw_plot_json": raw_result["plot_json"],
                "analyzed_plot_json": None,
                "analyzed_clean_plot_json": None,
                "current_plot_json": raw_result["plot_json"],
                "current_view_mode": "raw",
                "last_result": None,
                "manual_peak_freqs": [],
                "removed_peak_freqs": [],
                "removed_detection_ids": [],
                "current_view_ranges": None,
                "display_name": display_name,
                "base_display_name": display_name,
                "analysis_path": str(file_path),
                "original_analysis_path": str(file_path),
                "class30m_meta": class_meta,
                "fits_meta": deepcopy(meta.get("fits_meta")) if meta.get("fits_meta") else None,
                "base_class30m_meta": deepcopy(class_meta) if class_meta else None,
                "source_metadata": source_meta,
                "input_metadata": source_meta,
                "calibration": None,
                "smoothing_meta": {
                    "smooth_method": "none",
                    "smooth_value": None,
                    "smooth_engine": "czspec-native",
                    "hanning_passes": 0,
                },
                "extraction_history": [{"path": str(file_path), "display_name": display_name}],
                "extraction_index": 0,
            }

        self._switching_spectrum = True
        self.spectrum_selector.clear()
        for index, file_path in enumerate(self.selected_files, start=1):
            self.spectrum_selector.addItem(
                f"{index}. {self._spectrum_display_name(file_path)}",
                file_path,
            )
        self.spectrum_selector.setEnabled(True)
        self.spectrum_selector.setCurrentIndex(0)
        self._switching_spectrum = False
        multiple = len(self.selected_files) > 1
        self.compare_spectra_button.setEnabled(multiple)
        self.analyze_all_button.setEnabled(multiple)
        self._activate_spectrum(
            self.selected_files[0],
            render=(not multiple or not comparison),
            save_current=False,
        )
        if multiple and comparison:
            self.render_plot_full(comparison, mode="interactive")
            self.current_plot_json = comparison
            self.current_view_mode = "comparison"
            self.log(
                f"[INFO] Comparación inicial: {len(self.selected_files)} "
                "espectros crudos con disposición automática."
            )
        self.log(f"[OK] Sesión creada con {len(self.selected_files)} espectro(s).")
        if failures:
            detail = "; ".join(f"{Path(path).name}: {error}" for path, error in failures)
            self.log(f"[WARN] Archivos/configuraciones omitidos: {detail}")
            self.notify("Carga parcial", f"Se omitieron {len(failures)} elemento(s).")
        else:
            self.notify_success(
                f"Se cargaron {len(self.selected_files)} espectro(s) sin bloquear la interfaz."
            )

    def _finalize_with_initial_preview(self, loaded, failures):
        """Install a multi-spectrum session only after the user chooses its first view.

        Nothing is pre-selected.  All spectra remain loaded regardless of the
        preview subset.  The dialog also restores the old initial choice for
        shared X/Y scales without conflating it with the full Compare editor.
        """
        if not loaded:
            return
        if len(loaded) == 1:
            self._finalize_loaded_spectrum_session(loaded, failures, None)
            return

        entries = []
        loaded_map = {}
        for item in loaded:
            if len(item) >= 3:
                path, raw, meta = item[0], item[1], dict(item[2] or {})
            else:
                path, raw, meta = item[0], item[1], {}
            path = str(path)
            loaded_map[path] = (raw, meta)
            entries.append({
                "path": path,
                "name": str(meta.get("display_name") or raw.get("display_name") or Path(path).name),
                "freq": raw.get("freq"),
                "source": meta.get("source") or (meta.get("class30m_meta") or {}).get("source"),
                "line": meta.get("line") or (meta.get("class30m_meta") or {}).get("line"),
            })

        dialog = InitialSpectrumViewDialog(entries, language=self.ui_language, parent=self)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        chosen = dialog.selected_paths() if accepted else []
        preview_cfg = dialog.comparison_config() if accepted else {"layout":"auto","share_x":False,"share_y":False}

        self._finalize_loaded_spectrum_session(loaded, failures, None)
        if not chosen:
            # Cancel/empty cannot discard the imported session: keep the first
            # spectrum visible and all others available in the selector.
            self._activate_spectrum(str(loaded[0][0]), render=True, save_current=False)
            return
        if len(chosen) == 1:
            self._activate_spectrum(chosen[0], render=True, save_current=False)
            self.log((f"[INFO] Initial view: 1 of {len(loaded)} spectra." if self.ui_language=="en" else f"[INFO] Vista inicial: 1 de {len(loaded)} espectros."))
            return

        spectra=[]
        for path in chosen:
            if path not in loaded_map:
                continue
            raw, meta = loaded_map[path]
            state = self.spectrum_session.get(path, {})
            spectra.append({
                "name": str(state.get("display_name") or meta.get("display_name") or Path(path).name),
                "freq": raw.get("freq"),
                "inten": raw.get("inten"),
                "metadata": self._active_analysis_metadata(state) if state else dict(meta),
            })
        if len(spectra) < 2:
            self._activate_spectrum(chosen[0], render=True, save_current=False)
            return
        comparison = build_spectrum_comparison(
            spectra, plot_styles=deepcopy(self.plot_styles),
            layout_mode=str(preview_cfg.get("layout") or "auto"),
            share_x=bool(preview_cfg.get("share_x", False)),
            share_y=bool(preview_cfg.get("share_y", False)),
            axis_config=deepcopy(self.axis_config), language=self.ui_language,
        )
        self.comparison_plot_json = comparison
        self.render_plot_full(comparison, mode="interactive")
        self.current_plot_json = comparison
        self.current_view_mode = "comparison"
        files_cfg={str(path): {"included": str(path) in chosen} for path in self.selected_files}
        self.comparison_config.update({
            "layout": str(preview_cfg.get("layout") or "auto"),
            "share_x": bool(preview_cfg.get("share_x",False)),
            "share_y": bool(preview_cfg.get("share_y",False)),
            "files": files_cfg,
        })
        self._save_comparison_config()
        self.log((f"[INFO] Initial view: comparing {len(spectra)} of {len(loaded)} spectra." if self.ui_language=="en" else f"[INFO] Vista inicial: comparando {len(spectra)} de {len(loaded)} espectros."))

    @staticmethod
    def _class30m_display_name(meta: dict) -> str:
        source = str(meta.get("source") or "SOURCE")
        line = str(meta.get("line") or "LINE")
        telescope = str(meta.get("telescope") or "")
        if meta.get("average"):
            process = f"AVG n={int(meta.get('n_averaged') or 1)}"
        else:
            process = f"obs {meta.get('observation', '?')};{meta.get('version', '?')}"
        middle = f" · {telescope}" if telescope else ""
        return f"{source} · {line}{middle} · {process}"

    def _import_class30m_setups(self, file_path: str, setups: list, config: dict):
        plot_styles = deepcopy(self.plot_styles)
        average = bool(config.get("average", True))

        def work(progress):
            exports = []
            failures = []
            total = len(setups)
            for index, setup in enumerate(setups):
                progress(
                    5 + int(55 * index / max(total, 1)),
                    f"CLASS: procesando {setup.source} / {setup.line} ({index + 1}/{total})",
                )
                try:
                    items = export_class_setup(
                        file_path,
                        setup,
                        average=average,
                    )
                    exports.extend(items)
                except Exception as exc:
                    failures.append((f"{setup.source}/{setup.line}/{setup.telescope}", str(exc)))

            if not exports:
                detail = "\n\n".join(
                    f"• {name}: {error}" for name, error in failures[:8]
                )
                message = (
                    "CLASS no pudo exportar ninguna configuración seleccionada. "
                    "CZSpec separa los promedios por SOURCE + LINE + subrango "
                    "espectral compatible.\n"
                )
                if detail:
                    message += "\nDetalle devuelto por CLASS:\n" + detail
                raise ValueError(message)

            loaded = []
            for index, meta in enumerate(exports):
                progress(
                    62 + int(25 * index / max(len(exports), 1)),
                    f"CZSpec: leyendo espectro CLASS {index + 1}/{len(exports)}",
                )
                try:
                    display_name = self._class30m_display_name(meta)
                    raw_result = load_raw_spectrum(
                        meta["path"], plot_styles=plot_styles, display_name=display_name,
                        input_metadata=dict(meta), language=self.ui_language,
                    )
                    enriched = dict(meta)
                    enriched["class30m_meta"] = dict(meta)
                    enriched["display_name"] = display_name
                    loaded.append((meta["path"], raw_result, enriched))
                except Exception as exc:
                    failures.append((meta.get("path", "exportación CLASS"), str(exc)))

            if not loaded:
                raise ValueError("No se pudo convertir ninguna exportación CLASS en espectro CZSpec.")

            # The initial comparison is created only after the user chooses the
            # preview subset/layout.  Avoiding a throwaway Plotly figure here is
            # particularly important for large .30m sessions.
            progress(99, "Preparando sesión .30m")
            return loaded, failures, None

        def on_success(payload):
            loaded, failures, comparison = payload
            self._finalize_with_initial_preview(loaded, failures)

            self.log(
                "[OK] Archivo .30m convertido mediante GILDAS/CLASS a .dat "
                "(CONSISTENCY → AVERAGE cuando hay varias observaciones). "
                "Desde este punto CLASS deja de intervenir."
            )
            for _path, _raw, enriched in loaded:
                meta = dict(enriched.get("class30m_meta") or {})
                spacing = meta.get("channel_spacing_kms")
                if spacing is not None:
                    self.log(
                        f"[INFO] .dat CLASS {meta.get('source', '?')}/{meta.get('line', '?')}: "
                        f"muestreo={float(spacing):.4g} km/s."
                    )
                if meta.get("path"):
                    self.log(f"[INFO] Producto intermedio .dat: {meta.get('path')}")

        def on_error(message, details):
            self.log(f"[ERROR] Falló la importación .30m: {message}")
            self.log(details)
            self.notify("No se pudo importar el .30m", message)

        self._start_background_task(
            "import_class30m",
            work,
            on_success,
            on_error=on_error,
            busy_widgets=(
                self.load_button,
                self.run_button,
                self.spectrum_selector,
                self.compare_spectra_button,
                self.analyze_all_button,
            ),
            status_message="Procesando archivo .30m con CLASS...",
        )

    def _propagate_source_physics_defaults(self, metadata: dict | None):
        """Propaga metadatos físicos de M1 como valores iniciales, nunca como resultados forzados."""
        meta = dict(metadata or {})
        tex_values = [float(v) for v in (meta.get("excitation_temperatures_k") or []) if v is not None and float(v) > 0]
        if tex_values and hasattr(self, "species_temperatures_input"):
            suggestion = ", ".join(f"{v:g}" for v in sorted(set(tex_values)))
            # M1 metadata are authoritative user/source metadata, so when M2 is
            # explicitly fed from M1 we populate the editable field.  A fresh
            # session without M1 metadata remains empty.
            self.species_temperatures_input.setText(suggestion)
            self.species_temperatures_input.setPlaceholderText(
                "" if suggestion else ("e.g. 10, 28" if self.ui_language == "en" else "Ej. 10, 28")
            )
            try:
                self.species_last_target_temperatures = list(sorted(set(tex_values)))
            except Exception:
                pass
        tkin = meta.get("kinetic_temperature_k")
        try:
            tkin = float(tkin) if tkin is not None else None
        except Exception:
            tkin = None
        if tkin and tkin > 0:
            try:
                defaults = dict(self.nonlte_defaults or {})
                defaults["tkin_k"] = tkin
                self.nonlte_defaults = defaults
            except Exception:
                pass
        if tex_values or tkin:
            self.log(
                "[INFO] Metadatos físicos de la fuente preparados como valores iniciales para módulos posteriores: "
                + (f"Tex={tex_values} K " if tex_values else "")
                + (f"Tkin={tkin:g} K" if tkin else "")
            )

    def _refresh_active_metadata_plot(self):
        if not self.selected_file or self.selected_file not in self.spectrum_session:
            return
        state = self.spectrum_session[self.selected_file]
        try:
            raw = load_raw_spectrum(
                str(state.get("analysis_path") or self.selected_file),
                plot_styles=deepcopy(self.plot_styles),
                display_name=state.get("display_name"),
                input_metadata=self._active_analysis_metadata(state),
                language=self.ui_language,
            )
            state["raw_result"] = raw
            state["raw_plot_json"] = raw["plot_json"]
            if not state.get("last_result"):
                state["current_plot_json"] = raw["plot_json"]
                self.raw_plot_json = raw["plot_json"]
                self.current_plot_json = raw["plot_json"]
                self.update_plot_preserving_live_view(raw["plot_json"], mode="raw")
        except Exception as exc:
            self.log(f"[WARN] No se pudo refrescar la gráfica con metadatos: {exc}")

    def open_source_metadata_dialog(self):
        if not self.selected_file or self.selected_file not in self.spectrum_session:
            self.notify_info("Carga primero un espectro.")
            return
        state = self.spectrum_session[self.selected_file]
        dialog = SourceMetadataDialog(state.get("source_metadata") or {}, language=self.ui_language, online_enabled=self.network_online, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            metadata = dialog.configuration()
        except ValueError as exc:
            self.notify(
                "Metadatos inválidos" if self.ui_language == "es" else "Invalid metadata",
                str(exc),
            )
            return
        state["source_metadata"] = metadata
        state["input_metadata"] = metadata
        canonical = str(metadata.get("canonical_name") or metadata.get("raw_source_name") or "").strip()
        if canonical:
            base = str(state.get("base_display_name") or state.get("display_name") or Path(self.selected_file).name)
            # No borramos información de línea/backend; anteponemos nombre canónico sólo si no estaba.
            if canonical.lower() not in base.lower():
                state["display_name"] = f"{canonical} · {base}"
        # Guardar en la bitácora es una acción explícita del usuario dentro del diálogo.
        self._propagate_source_physics_defaults(metadata)
        self._refresh_active_metadata_plot()
        self._switching_spectrum = True
        index = self.selected_files.index(self.selected_file)
        self.spectrum_selector.setItemText(index, f"{index+1}. {self._spectrum_display_name(self.selected_file)}")
        self._switching_spectrum = False
        self.log("[OK] Metadatos de fuente actualizados y vinculados al espectro.")

    def _active_calibration(self, state: dict) -> dict:
        calibration = dict(state.get("calibration") or {})
        if calibration:
            return calibration
        eta = float(self.eta_input.value())
        if not np.isfinite(eta) or eta <= 0:
            eta = 1.0
        return {
            "mode": "eta",
            "factor": 1.0 / eta,
            "eta": eta,
            "name": f"η manual = {eta:g}",
            "notes": "T_corr = T_input / η",
        }

    def _update_calibration_summary(self):
        if not self.selected_file or self.selected_file not in self.spectrum_session:
            self.calibration_summary.setText("—")
            self.calibration_button.setEnabled(False)
            return
        state = self.spectrum_session[self.selected_file]
        cfg = self._active_calibration(state)
        self.calibration_button.setEnabled(True)
        factor=float(cfg.get("factor",1.0) or 1.0)
        self.calibration_summary.setText(("Activa: " if self.ui_language == "es" else "Active: ") + f"{cfg.get('name','η manual')} · factor={factor:.6g}")

    def open_calibration_dialog(self):
        if not self.selected_file or self.selected_file not in self.spectrum_session:
            self.notify_info("Carga primero un espectro.")
            return
        state = self.spectrum_session[self.selected_file]
        raw = state.get("raw_result") or {}
        freq = np.asarray(raw.get("freq", []), dtype=float)
        median = float(np.nanmedian(freq)) if freq.size else None
        dialog = CalibrationDialog(
            dict(state.get("source_metadata") or {}), current=self._active_calibration(state),
            median_frequency_mhz=median, language=self.ui_language, parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        state["calibration"] = dialog.configuration()
        # Cambiar calibración invalida cualquier ajuste anterior.
        state["last_result"] = None; state["analyzed_plot_json"] = None; state["analyzed_clean_plot_json"] = None
        self.last_result = None; self.analyzed_plot_json = None; self.analyzed_clean_plot_json = None
        self.export_csv_button.setEnabled(False); self.export_html_button.setEnabled(bool(state.get("raw_plot_json")))
        self._update_calibration_summary()
        self.log(f"[INFO] Calibración: {state['calibration'].get('name')} · factor={state['calibration'].get('factor')}")

    def _load_class30m_file(self, file_path: str):
        ok, backend = class_backend_status()
        if not ok:
            self.log(f"[ERROR] Soporte .30m no disponible: {backend}")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle("GILDAS/CLASS no disponible")
            box.setText(backend)
            box.setInformativeText(
                "CZSpec usa CLASS únicamente como motor interno; no abrirá su interfaz. "
                "Puedes revisar la configuración ahora."
            )
            configure = box.addButton("Configurar...", QMessageBox.ButtonRole.ActionRole)
            box.addButton(QMessageBox.StandardButton.Close)
            box.exec()
            if box.clickedButton() is configure:
                self.open_class_backend_dialog()
            return

        def work(progress):
            progress(15, "Leyendo índice del archivo .30m con CLASS")
            setups = inspect_30m_file(file_path)
            progress(95, f"Se encontraron {len(setups)} configuraciones")
            return setups

        def on_success(setups):
            dialog = Class30mImportDialog(file_path, setups, backend, language=self.ui_language, parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                self.log("[INFO] Importación .30m cancelada por el usuario.")
                return
            self._import_class30m_setups(
                file_path,
                dialog.selected_setups(),
                dialog.configuration(),
            )

        def on_error(message, details):
            self.log(f"[ERROR] No se pudo inspeccionar el archivo .30m: {message}")
            self.log(details)
            self.notify("No se pudo abrir el .30m", message)

        self._start_background_task(
            "inspect_class30m",
            work,
            on_success,
            on_error=on_error,
            busy_widgets=(self.load_button,),
            status_message="Inspeccionando archivo CLASS .30m...",
        )

    def _load_fits_file(self, file_path: str):
        """Inspecciona un FITS y extrae un espectro 1-D reproducible."""
        def work_inspect(progress):
            progress(20, "Inspeccionando HDU y WCS FITS")
            infos = inspect_fits_file(file_path)
            if not infos:
                raise ValueError("El FITS no contiene HDU con datos analizables.")
            progress(95, f"{len(infos)} HDU con datos encontrados")
            return infos

        def on_inspect(infos):
            dialog = FitsImportDialog(file_path, infos, language=self.ui_language, parent=self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            cfg = dialog.configuration()
            def work_extract(progress):
                progress(20, "Extrayendo espectro FITS")
                result = extract_fits_spectrum(file_path, **cfg)
                progress(75, "Normalizando espectro a M1")
                meta = dict(result.get("metadata") or {})
                raw = load_raw_spectrum(
                    result["path"], plot_styles=deepcopy(self.plot_styles),
                    display_name=meta.get("display_name"), input_metadata=meta, language=self.ui_language,
                )
                enriched = {"fits_meta": meta, "source_metadata": meta,
                            "display_name": meta.get("display_name") or Path(result["path"]).name}
                progress(99, "Preparando sesión FITS")
                return [(result["path"], raw, enriched)], [], None
            def on_extract(payload):
                loaded, failures, comparison = payload
                self._finalize_loaded_spectrum_session(loaded, failures, comparison)
                meta = dict(loaded[0][2].get("fits_meta") or {})
                self.log(f"[OK] FITS extraído a .dat: {loaded[0][0]}")
                if meta.get("ra_deg") is not None and meta.get("dec_deg") is not None:
                    self.log(f"[INFO] Coordenadas FITS: RA={float(meta['ra_deg']):.6f} deg · DEC={float(meta['dec_deg']):.6f} deg")
            self._start_background_task(
                "extract_fits", work_extract, on_extract,
                on_error=lambda m,d: (self.log(f"[ERROR] FITS: {m}"), self.log(d), self.notify("No se pudo extraer el FITS", m)),
                busy_widgets=(self.load_button,), status_message="Extrayendo espectro FITS...",
            )

        self._start_background_task(
            "inspect_fits", work_inspect, on_inspect,
            on_error=lambda m,d: (self.log(f"[ERROR] FITS: {m}"), self.log(d), self.notify("No se pudo abrir el FITS", m)),
            busy_widgets=(self.load_button,), status_message="Inspeccionando FITS...",
        )

    def load_file(self):
        start_dir = str(self.settings.value("paths/input_dir", "") or "")
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleccionar uno o varios espectros" if self.ui_language == "es" else "Select one or more spectra",
            start_dir,
            "Espectros (*.dat *.csv *.txt *.30m *.fits *.fit *.fts);;FITS (*.fits *.fit *.fts);;CLASS 30m (*.30m);;Archivos ASCII (*.dat *.csv *.txt);;Todos los archivos (*)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )

        self.show()
        self.raise_()
        self.activateWindow()
        if not file_paths:
            self.log("[INFO] No se seleccionaron espectros.")
            return
        unique_paths = list(dict.fromkeys(str(Path(path).resolve()) for path in file_paths))
        class30m_paths = [path for path in unique_paths if Path(path).suffix.lower() == ".30m"]
        if class30m_paths:
            if len(unique_paths) != 1:
                self.notify_info(
                    "Para importar .30m selecciona un archivo CLASS a la vez. "
                    "Dentro del archivo podrás elegir varias configuraciones y compararlas."
                )
                return
            self._load_class30m_file(class30m_paths[0])
            return
        fits_paths = [path for path in unique_paths if Path(path).suffix.lower() in {".fits", ".fit", ".fts"}]
        if fits_paths:
            if len(unique_paths) != 1:
                self.notify_info("Para importar cubos FITS selecciona un archivo a la vez; después puedes añadir más espectros a otra sesión.")
                return
            self._load_fits_file(fits_paths[0])
            return
        plot_styles = deepcopy(self.plot_styles)

        def work(progress):
            loaded = []
            failures = []
            total = len(unique_paths)
            for index, file_path in enumerate(unique_paths):
                progress(
                    5 + int(82 * index / max(total, 1)),
                    f"Leyendo espectro {index + 1} de {total}",
                )
                try:
                    raw_result = load_raw_spectrum(file_path, plot_styles=plot_styles, language=self.ui_language)
                    loaded.append((file_path, raw_result))
                except Exception as exc:
                    failures.append((file_path, str(exc)))
            if not loaded:
                raise ValueError("No se pudo leer ninguno de los archivos seleccionados.")
            # Build the multi-spectrum figure only after the initial-preview
            # dialog tells us which spectra/layout the user actually wants.
            progress(99, "Preparando la sesión espectral")
            return loaded, failures, None

        def on_success(payload):
            loaded, failures, comparison = payload
            self._finalize_with_initial_preview(loaded, failures)

        def on_error(message, details):
            self.log(f"[ERROR] No se pudieron cargar los espectros: {message}")
            self.log(details)
            self.notify("No se pudieron cargar", message)

        self._start_background_task(
            "load_spectra",
            work,
            on_success,
            on_error=on_error,
            busy_widgets=(
                self.load_button,
                self.run_button,
                self.spectrum_selector,
                self.compare_spectra_button,
                self.analyze_all_button,
            ),
            status_message="Cargando espectros...",
        )

    def _set_detection_table_headers(self):
        if not hasattr(self,"detections_list") or not isinstance(self.detections_list,QTableWidget):return
        en=self.ui_language=="en"
        self.detections_list.setHorizontalHeaderLabels(("Line" if en else "Línea","Center [MHz]" if en else "Centro [MHz]","S/N","Confidence" if en else "Confianza","Origin" if en else "Origen"))
        h=self.detections_list.horizontalHeader()
        h.setStretchLastSection(False)
        for col in range(5): h.setSectionResizeMode(col,QHeaderView.ResizeMode.ResizeToContents)
        sn_tip=("Signal-to-noise ratio: fitted peak intensity divided by the robust local noise estimate." if en else "Relación señal-ruido: intensidad pico ajustada dividida por la estimación robusta local del ruido.")
        self.detections_list.horizontalHeaderItem(2).setToolTip(sn_tip)

    def _localized_detection_value(self, field: str, value: str) -> str:
        raw = str(value or "").strip()
        low = raw.lower()
        en = self.ui_language == "en"
        maps = {
            "origin": {
                "auto": ("Automática", "Automatic"),
                "manual": ("Manual", "Manual"),
                "residual": ("Residual", "Residual"),
            },
            "confidence": {
                "high": ("Alta", "High"),
                "medium": ("Media", "Medium"),
                "low": ("Baja", "Low"),
                "alta": ("Alta", "High"),
                "media": ("Media", "Medium"),
                "baja": ("Baja", "Low"),
                "tentativa": ("Tentativa", "Tentative"),
                "tentative": ("Tentativa", "Tentative"),
                "segura": ("Segura", "Secure"),
                "secure": ("Segura", "Secure"),
                "probable": ("Probable", "Probable"),
            },
            "polarity": {
                "emission": ("Emisión", "Emission"),
                "absorption": ("Absorción", "Absorption"),
            },
        }
        pair = maps.get(field, {}).get(low)
        if pair:
            return pair[1] if en else pair[0]
        return raw or "—"

    def open_detected_lines_window(self):
        # This is a viewer, not a configuration dialog: it must remain modeless
        # so the user can inspect a row and keep interacting with the main plot.
        existing = getattr(self, "_detected_lines_dialog", None)
        if existing is not None and existing.isVisible():
            existing.raise_(); existing.activateWindow(); return
        dialog = QDialog(self)
        dialog.setModal(False)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        dialog.setWindowTitle("Detected spectral lines" if self.ui_language == "en" else "Líneas espectrales detectadas")
        dialog.resize(760, 500)
        layout = QVBoxLayout(dialog)
        table = QTableWidget(self.detections_list.rowCount(), self.detections_list.columnCount())
        headers = []
        for c in range(self.detections_list.columnCount()):
            hi = self.detections_list.horizontalHeaderItem(c)
            headers.append(hi.text() if hi else "")
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        for r in range(self.detections_list.rowCount()):
            for c in range(self.detections_list.columnCount()):
                src = self.detections_list.item(r, c)
                if src is not None:
                    clone = QTableWidgetItem(src.text())
                    clone.setToolTip(src.toolTip())
                    clone.setData(Qt.ItemDataRole.UserRole, src.data(Qt.ItemDataRole.UserRole))
                    table.setItem(r, c, clone)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(False)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        # Keep the detached viewer and the embedded table synchronized.  This
        # means a row selected in either table can be removed with the main
        # Manual detection editing -> Remove button.
        def _floating_row_clicked(r, c):
            self.detections_list.clearSelection()
            self.detections_list.setCurrentCell(r, 0)
            self.detections_list.selectRow(r)
            self._focus_detection_row(r, c)
        table.cellClicked.connect(_floating_row_clicked)
        self._detected_lines_floating_table = table
        layout.addWidget(table)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.button(QDialogButtonBox.StandardButton.Close).setText("Close" if self.ui_language == "en" else "Cerrar")
        close.rejected.connect(dialog.close)
        close.clicked.connect(dialog.close)
        layout.addWidget(close)
        def _clear_detached_refs(*_):
            self._detected_lines_dialog = None
            self._detected_lines_floating_table = None
        dialog.destroyed.connect(_clear_detached_refs)
        self._detected_lines_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _populate_detections(self, peak_items):
        self.detections_list.setRowCount(0)
        self._set_detection_table_headers()

        if not peak_items:
            self.detections_list.setRowCount(1)
            item = QTableWidgetItem(
                "No spectral lines detected." if self.ui_language == "en"
                else "No se detectaron líneas espectrales."
            )
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.detections_list.setItem(0, 0, item)
            self.detections_list.setSpan(0, 0, 1, 5)
            self._sync_floating_detection_table()
            return

        self.detections_list.clearSpans()
        self.detections_list.setRowCount(len(peak_items))
        for row, item_data in enumerate(peak_items):
            seed_freq = float(item_data["freq"])
            fit_freq = float(item_data.get("fit_freq", seed_freq))
            origin = str(item_data.get("origin", "auto"))
            confidence = str(item_data.get("confidence", ""))
            snr = item_data.get("snr")
            line_item = QTableWidgetItem(f"L{row + 1}")
            line_item.setData(Qt.ItemDataRole.UserRole, dict(item_data))
            center_item = QTableWidgetItem(f"{fit_freq:.6f}")
            snr_item = QTableWidgetItem(
                "—" if snr is None or not np.isfinite(float(snr)) else f"{float(snr):.2f}"
            )
            conf_item = QTableWidgetItem(self._localized_detection_value("confidence", confidence))
            origin_item = QTableWidgetItem(self._localized_detection_value("origin", origin))
            tooltip_parts = [
                ("Fitted center" if self.ui_language == "en" else "Centro ajustado") + f": {fit_freq:.6f} MHz",
                ("Seed" if self.ui_language == "en" else "Semilla") + f": {seed_freq:.6f} MHz",
            ]
            polarity = str(item_data.get("polarity", ""))
            if polarity:
                tooltip_parts.append(
                    ("Type" if self.ui_language == "en" else "Tipo") + ": "
                    + self._localized_detection_value("polarity", polarity)
                )
            tooltip = "\n".join(tooltip_parts)
            for col_item in (line_item, center_item, snr_item, conf_item, origin_item):
                col_item.setToolTip(tooltip)
            for col, col_item in enumerate((line_item, center_item, snr_item, conf_item, origin_item)):
                self.detections_list.setItem(row, col, col_item)

        self._sync_floating_detection_table()

    def _sync_floating_detection_table(self):
        """Mirror the embedded detection table after every local refit.

        The detached viewer used to keep stale row payloads after a deletion.
        Its visible L-number then referred to a different component than the
        embedded table.  Rebuild it from the canonical table so both surfaces
        always carry the same immutable detection_id.
        """
        table = getattr(self, "_detected_lines_floating_table", None)
        if table is None:
            return
        try:
            table.blockSignals(True)
            table.clearSelection()
            table.setCurrentCell(-1, -1)
            table.setRowCount(self.detections_list.rowCount())
            table.setColumnCount(self.detections_list.columnCount())
            headers=[]
            for c in range(self.detections_list.columnCount()):
                hi=self.detections_list.horizontalHeaderItem(c)
                headers.append(hi.text() if hi else "")
            table.setHorizontalHeaderLabels(headers)
            for r in range(self.detections_list.rowCount()):
                for c in range(self.detections_list.columnCount()):
                    src=self.detections_list.item(r,c)
                    if src is None:
                        table.setItem(r,c,None)
                        continue
                    clone=QTableWidgetItem(src.text())
                    clone.setToolTip(src.toolTip())
                    clone.setFlags(src.flags())
                    clone.setData(Qt.ItemDataRole.UserRole, src.data(Qt.ItemDataRole.UserRole))
                    table.setItem(r,c,clone)
            table.clearSpans()
            if self.detections_list.rowCount()==1 and self.detections_list.columnSpan(0,0)>1:
                table.setSpan(0,0,1,self.detections_list.columnSpan(0,0))
        finally:
            table.blockSignals(False)

    def _get_detection_items(self):
        """Devuelve las detecciones visibles preservando la frecuencia-semilla."""
        items = []
        for row in range(self.detections_list.rowCount()):
            item = self.detections_list.item(row, 0)
            if item is None:
                continue
            data = item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(data, dict) or "freq" not in data:
                continue
            items.append({
                "display_index": len(items) + 1,
                "freq": float(data["freq"]),
                "origin": data.get("origin", "auto"),
                "item": item,
                "row": row,
                "data": data,
            })
        return items

    def _focus_detection_row(self,row:int,_column:int=0):
        item=self.detections_list.item(row,0)
        if item is None:return
        data=item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(data,dict):return
        freq=float(data.get("fit_freq",data.get("freq",np.nan)))
        if not np.isfinite(freq) or self.plot_view is None or not self._plot_page_ready:return
        try:
            state=self.spectrum_session.get(self.selected_file,{}) if self.selected_file else {}
            raw=state.get("raw_result") or {}; arr=np.asarray(raw.get("freq",[]),dtype=float); arr=arr[np.isfinite(arr)]
            full_span=float(np.nanmax(arr)-np.nanmin(arr)) if arr.size>1 else 1.0
            fwhm=float(data.get("fwhm_mhz",np.nan))
            channel=max(self._manual_edit_tolerance_mhz()/1.25,1e-6)
            context_floor=max(8.0*channel, 1.5)
            tol=max(context_floor, 5.0*fwhm if np.isfinite(fwhm) and fwhm>0 else 0.0)
            tol=min(tol, max(12.0, 0.01*full_span))
        except Exception:tol=3.0
        self.plot_view.page().runJavaScript(f"window.czspecFocusSpectral && window.czspecFocusSpectral({freq!r},{tol!r});")

    @staticmethod
    def _parse_baseline_windows(text: str) -> list[tuple[float, float, int | None]]:
        """Parsea ventanas ``fmin-fmax`` y un ``@grado`` local opcional.

        Ejemplos válidos::
            143450-143470
            143450-143470@0, 143900-143930@2
        """
        text = (text or "").strip()
        if not text:
            return []
        windows = []
        chunks = [chunk.strip() for chunk in re.split(r"[,;]+", text) if chunk.strip()]
        for chunk in chunks:
            clean = re.sub(r"(?i)mhz", "", chunk).strip()
            degree = None
            degree_match = re.search(r"@\s*([0-3])\s*$", clean)
            if degree_match:
                degree = int(degree_match.group(1))
                clean = clean[:degree_match.start()].strip()
            elif "@" in clean:
                raise ValueError(
                    f"Grado local inválido en '{chunk}'. Usa @0, @1, @2 o @3."
                )
            match = re.fullmatch(
                r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(?:-|:|\.\.)\s*"
                r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))",
                clean,
            )
            if not match:
                match = re.fullmatch(
                    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s+"
                    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))",
                    clean,
                )
            if not match:
                raise ValueError(
                    f"Ventana de línea base inválida: '{chunk}'. Usa fmin-fmax[@grado] en MHz."
                )
            a, b = float(match.group(1)), float(match.group(2))
            if a == b:
                raise ValueError(f"La ventana '{chunk}' tiene ancho cero.")
            a, b = sorted((a, b))
            windows.append((a, b, degree))
        return windows

    @staticmethod
    def _format_baseline_window(spec) -> str:
        a, b = float(spec[0]), float(spec[1])
        degree = spec[2] if len(spec) > 2 else None
        return f"{a:g}-{b:g}" + (f"@{int(degree)}" if degree is not None else "")

    def capture_current_plot_ranges(self, callback):
        if self.plot_view is None or not self._plot_page_ready:
            callback(None)
            return
        js_code = "window.getCurrentRanges();"
        self.plot_view.page().runJavaScript(js_code, callback)

    def capture_current_plot_json(self, callback):
        if self.plot_view is None or not self._plot_page_ready:
            callback(None)
            return
        js_code = """
        (function() {
            const gd = document.getElementById('plot');
            if (!gd || !gd.data || !gd.layout) {
                return null;
            }

            const fig = {
                data: gd.data,
                layout: gd.layout
            };

            return JSON.stringify(fig);
        })();
        """
        self.plot_view.page().runJavaScript(js_code, callback)

    def execute_analysis(self, preserve_view=False, reset_manual_state=False, preserve_existing_components=False):
        if not self.selected_file:
            QMessageBox.warning(self, "Advertencia", "Primero debes cargar un archivo.")
            self.log("[ERROR] No hay archivo seleccionado.")
            return

        if reset_manual_state:
            self.manual_peak_freqs = []
            self.removed_peak_freqs = []
            self.removed_detection_ids = []
            self.current_view_ranges = None
            self.log("[INFO] Se restableció el análisis al estado base.")

        baseline_degree = int(self.baseline_combo.currentText())
        baseline_mode = str(self.baseline_mode_combo.currentData())
        try:
            baseline_windows = (
                self._parse_baseline_windows(self.baseline_windows_input.text())
                if baseline_mode == "windows" else []
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Ventanas de base inválidas", str(exc))
            return
        if baseline_mode == "windows" and not baseline_windows:
            QMessageBox.warning(
                self, "Ventanas de base",
                "Escribe al menos una ventana de línea base en MHz."
            )
            return
        fit_choice = self.fit_combo.currentData()
        state = self.spectrum_session.get(self.selected_file, {})
        explicit_calibration = dict(state.get("calibration") or {})
        calibration = self._active_calibration(state)
        calibration_factor = float(explicit_calibration.get("factor", 1.0) or 1.0) if explicit_calibration else None
        eta_value = float(self.eta_input.value())
        detection_sigma = self.detection_sigma_input.value()
        detection_polarity = str(self.polarity_combo.currentData())
        deblend = bool(self.deblend_checkbox.isChecked())
        delta_bic_min = float(self.delta_bic_input.value())
        max_components = int(self.max_components_input.value())

        self.log("[INFO] Iniciando análisis...")
        self.log(f"[INFO] Archivo: {self.selected_file}")
        self.log(f"[INFO] Escala = {calibration.get('name')}" + (f" · factor={calibration_factor:.6g}" if calibration_factor is not None else ""))
        self.log(f"[INFO] Umbral de detección = {detection_sigma:.1f} σ")
        self.log(f"[INFO] Base grado = {baseline_degree}; modo = {baseline_mode}")
        if baseline_windows:
            self.log("[INFO] Ventanas de base [MHz] = " + ", ".join(self._format_baseline_window(spec) for spec in baseline_windows))
        self.log(f"[INFO] Buscar = {self.polarity_combo.currentText()}")
        self.log(f"[INFO] Ajuste = {self.fit_combo.currentText()}")
        self.log(
            f"[INFO] Deblending={'sí' if deblend else 'no'}; "
            f"ΔBIC mínimo={delta_bic_min:.1f}; máx. componentes/grupo={max_components}"
        )
        self.log(f"[INFO] Detecciones manuales agregadas: {len(self.manual_peak_freqs)}")
        self.log(f"[INFO] Detecciones marcadas para eliminar: {len(self.removed_detection_ids) or len(self.removed_peak_freqs)}")

        selected_file = self.selected_file
        manual_peak_freqs = list(self.manual_peak_freqs)
        removed_peak_freqs = list(self.removed_peak_freqs)
        removed_detection_ids = {str(v) for v in self.removed_detection_ids if str(v)}
        retained_peak_items = []
        if preserve_existing_components and self.last_result is not None:
            # Interactive editing is identity based.  Frequencies are only kept
            # as a legacy/fallback rediscovery guard; they never decide which
            # accepted component survives a local edit.
            for item in list((self.last_result or {}).get("detected_peak_items") or []):
                detection_id = str(item.get("detection_id") or "")
                if detection_id and detection_id in removed_detection_ids:
                    continue
                retained_peak_items.append(dict(item))
        preserve_ranges = self.current_view_ranges if preserve_view else None
        fit_color = self.fit_color
        plot_styles = deepcopy(self.plot_styles)
        state = self.spectrum_session.get(selected_file, {})
        analysis_file = str(state.get("analysis_path") or selected_file)
        input_metadata = merge_source_metadata(
            state.get("source_metadata"), state.get("class30m_meta"), state.get("fits_meta"), state.get("smoothing_meta")
        )
        if analysis_file != selected_file:
            self.log(f"[INFO] Datos activos procesados: {analysis_file}")

        def work(progress):
            return run_peak_detection(
                file_path=analysis_file,
                baseline_degree=baseline_degree,
                fit_choice=fit_choice,
                beam_efficiency=eta_value,
                calibration_factor=calibration_factor,
                detection_sigma=detection_sigma,
                fit_color=fit_color,
                plot_styles=plot_styles,
                output_dir=str(PEAK_DETECTION_OUTPUT_DIR),
                export_csv=False,
                export_html=False,
                manual_peak_freqs=manual_peak_freqs,
                removed_peak_freqs=removed_peak_freqs,
                retained_peak_items=retained_peak_items,
                local_edit=bool(preserve_existing_components),
                preserve_ranges=preserve_ranges,
                progress_callback=progress,
                baseline_mode=baseline_mode,
                baseline_windows=baseline_windows,
                detection_polarity=detection_polarity,
                deblend=deblend,
                delta_bic_min=delta_bic_min,
                max_components_per_group=max_components,
                input_metadata=input_metadata,
                display_name=str(state.get("display_name") or Path(selected_file).name),
                language=self.ui_language,
            )

        def on_success(result):
            self.last_result = result

            has_df = result.get("results_df") is not None and not result["results_df"].empty
            has_html = bool(result.get("plot_html"))
            self.export_csv_button.setEnabled(has_df)
            self.export_html_button.setEnabled(has_html)

            df = result["results_df"]
            output_csv = result.get("output_csv")
            n_lines = result.get("n_detected_lines", 0)
            peak_items = result.get("detected_peak_items", [])
            plot_json = result.get("plot_json")

            self.analyzed_plot_json = plot_json
            self.analyzed_clean_plot_json = plot_json

            self.log("[OK] Detección completada.")
            self.log(
                f"[OK] Candidatos iniciales: {result.get('n_initial_candidates', 0)}; "
                f"componentes aceptadas: {n_lines}; "
                f"recuperadas en residuales: {result.get('n_residual_components', 0)}."
            )
            self.log(
                f"[OK] Criterio aplicado: altura ≥ {result.get('detection_sigma', detection_sigma):.1f} σ; "
                f"prominencia ≥ {result.get('prominence_sigma', 2.0):.1f} σ; "
                f"ΔBIC ≥ {result.get('delta_bic_min', delta_bic_min):.1f}."
            )

            if output_csv:
                self.log(f"[OK] CSV generado: {output_csv}")

            if not df.empty:
                self.log("[INFO] Primeras filas del resultado:")
                self.log(df.head().to_string(index=False))
                if len(self.selected_files) <= 1:
                    source_meta = self.spectrum_session.get(self.selected_file, {}).get("source_metadata") or {}
                    source_label = str(source_meta.get("canonical_name") or source_meta.get("raw_source_name") or Path(self.selected_file).name)
                    self.sync_peak_results_to_species_tab(
                        df,
                        source_description=source_label,
                    )
                else:
                    self.log(
                        "[INFO] Resultado guardado en la sesión. En M2 elige "
                        "'Espectro activo' o 'Toda la sesión analizada' y pulsa actualizar."
                    )
            else:
                self.log("[INFO] No se detectaron líneas ajustables.")

            self._populate_detections(peak_items)

            if plot_json:
                if preserve_view and self.current_view_mode in {"interactive", "interactive_extended"}:
                    render_mode = self.current_view_mode
                    self.update_plot_in_place(plot_json, mode=render_mode)
                else:
                    render_mode = "interactive"
                    self.render_plot_full(plot_json, mode=render_mode)

                self.current_plot_json = plot_json
                self.current_view_mode = render_mode
                self._set_m1_view_combo("with_legend_extended" if render_mode == "interactive_extended" else "with_legend")
            else:
                self.log("[ERROR] No se recibió plot_json para renderizar.")
            self.refresh_lte_inputs()
            self.notify_success(
                f"El análisis espectral terminó correctamente: {n_lines} "
                "línea(s) detectada(s) o ajustada(s)."
            )
            self._save_active_spectrum_state()
            self.comparison_plot_json = None

        def on_error(message, details):
            self.log(f"[ERROR] Ocurrió un problema: {message}")
            self.log(details)
            QMessageBox.critical(self, "Error en el análisis espectral", message)

        self._start_background_task(
            "spectral_analysis",
            work,
            on_success,
            on_error=on_error,
            busy_widgets=(
                self.load_button,
                self.run_button,
                self.refresh_button,
                self.add_manual_button,
                self.remove_selected_button,
                self.fit_color_button,
                self.view_raw_button,
                self.view_clean_button,
                self.view_interactive_button,
                self.save_image_button,
                self.fullscreen_button,
                self.spectrum_selector,
                self.compare_spectra_button,
                self.analyze_all_button,
            ),
            status_message="Ejecutando análisis espectral...",
        )

    def analyze_all_spectra(self):
        if len(self.selected_files) < 2:
            self.notify_info("Carga al menos dos espectros para usar el análisis por lote.")
            return
        self._save_active_spectrum_state()
        baseline_degree = int(self.baseline_combo.currentText())
        baseline_mode = str(self.baseline_mode_combo.currentData())
        try:
            baseline_windows = (
                self._parse_baseline_windows(self.baseline_windows_input.text())
                if baseline_mode == "windows" else []
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Ventanas de base inválidas", str(exc))
            return
        if baseline_mode == "windows" and not baseline_windows:
            self.notify_info("Escribe al menos una ventana de línea base en MHz.")
            return
        fit_choice = self.fit_combo.currentData()
        detection_sigma = self.detection_sigma_input.value()
        detection_polarity = str(self.polarity_combo.currentData())
        deblend = bool(self.deblend_checkbox.isChecked())
        delta_bic_min = float(self.delta_bic_input.value())
        max_components = int(self.max_components_input.value())
        fit_color = self.fit_color
        plot_styles = deepcopy(self.plot_styles)
        inputs = []
        for file_path in self.selected_files:
            state = self.spectrum_session[file_path]
            inputs.append({
                "file_path": file_path,
                "manual_peak_freqs": list(state.get("manual_peak_freqs", [])),
                "removed_peak_freqs": list(state.get("removed_peak_freqs", [])),
                "input_metadata": merge_source_metadata(state.get("source_metadata"), state.get("class30m_meta"), state.get("fits_meta"), state.get("smoothing_meta")),
                "calibration_factor": (float((state.get("calibration") or {}).get("factor", 1.0)) if state.get("calibration") else None),
                "eta_value": float(self.eta_input.value()),
                "display_name": str(state.get("display_name") or Path(file_path).name),
                "analysis_path": str(state.get("analysis_path") or file_path),
            })

        def work(progress):
            results = []
            total = len(inputs)
            for index, item in enumerate(inputs):
                file_name = Path(item["file_path"]).name

                def local_progress(value, message, i=index, name=file_name):
                    overall = int(((i + max(0, min(100, value)) / 100.0) / total) * 98)
                    progress(
                        overall,
                        f"{name} · {message}",
                    )

                result = run_peak_detection(
                    file_path=item.get("analysis_path") or item["file_path"],
                    baseline_degree=baseline_degree,
                    fit_choice=fit_choice,
                    beam_efficiency=item.get("eta_value", 1.0),
                    calibration_factor=item["calibration_factor"],
                    detection_sigma=detection_sigma,
                    fit_color=fit_color,
                    plot_styles=plot_styles,
                    output_dir=str(PEAK_DETECTION_OUTPUT_DIR),
                    export_csv=False,
                    export_html=False,
                    manual_peak_freqs=item["manual_peak_freqs"],
                    removed_peak_freqs=item["removed_peak_freqs"],
                    progress_callback=local_progress,
                    baseline_mode=baseline_mode,
                    baseline_windows=baseline_windows,
                    detection_polarity=detection_polarity,
                    deblend=deblend,
                    delta_bic_min=delta_bic_min,
                    max_components_per_group=max_components,
                    input_metadata=item["input_metadata"],
                    display_name=item.get("display_name"),
                    language=self.ui_language,
                )
                results.append((item["file_path"], result))
            progress(99, "Consolidando los resultados de la sesión")
            return results

        def on_success(results):
            combined = []
            total_lines = 0
            for file_path, result in results:
                state = self.spectrum_session[file_path]
                state.update({
                    "last_result": result,
                    "analyzed_plot_json": result.get("plot_json"),
                    "analyzed_clean_plot_json": result.get("plot_json"),
                    "current_plot_json": result.get("plot_json") or state["raw_plot_json"],
                    "current_view_mode": "interactive" if result.get("plot_json") else "raw",
                })
                frame = result.get("results_df")
                if frame is not None and not frame.empty:
                    prepared = frame.copy()
                    prepared["Source"] = Path(file_path).name
                    combined.append(prepared)
                    total_lines += len(prepared)

            active_path = self.selected_file if self.selected_file in self.spectrum_session else self.selected_files[0]
            # Cambia el estado activo sin destruir/recrear la vista WebEngine.
            # Esto elimina el parpadeo/desaparición breve observado al finalizar
            # Analyze All y reutiliza el contenedor Plotly ya cargado.
            self._activate_spectrum(active_path, render=False, save_current=False)
            if self.current_plot_json:
                self.update_plot_in_place(self.current_plot_json, mode=self.current_view_mode or "interactive")
            self.comparison_plot_json = None
            if combined:
                combined_frame = pd.concat(combined, ignore_index=True, sort=False)
                if hasattr(self, "species_m1_scope_combo"):
                    session_index = self.species_m1_scope_combo.findData("session")
                    self.species_m1_scope_combo.setCurrentIndex(max(0, session_index))
                self.sync_peak_results_to_species_tab(
                    combined_frame,
                    base_name=f"sesion_{len(results)}_espectros",
                    source_description=f"toda la sesión ({len(results)} espectros)",
                )
            self.log(
                f"[OK] Sesión analizada: {len(results)} espectros y {total_lines} líneas ajustadas."
            )
            self.notify_success(
                f"Se analizaron {len(results)} espectros; M2 recibió {total_lines} línea(s) con su archivo fuente."
            )
            self.refresh_lte_inputs()

        def on_error(message, details):
            self.log(f"[ERROR] Falló el análisis multiespectro: {message}")
            self.log(details)
            self.notify("No se completó el análisis por lote", message)

        self._start_background_task(
            "spectral_batch_analysis",
            work,
            on_success,
            on_error=on_error,
            busy_widgets=(
                self.load_button,
                self.run_button,
                self.refresh_button,
                self.compare_spectra_button,
                self.analyze_all_button,
                self.spectrum_selector,
            ),
            status_message="Analizando todos los espectros...",
        )

    def update_detections_preserving_view(self):
        def _after_capture(ranges):
            self.current_view_ranges = ranges
            self.log(f"[DEBUG] Rangos capturados: {ranges}")
            self.execute_analysis(preserve_view=True, reset_manual_state=False, preserve_existing_components=True)

        self.capture_current_plot_ranges(_after_capture)


    def toggle_system_log_size(self):
        """Expand/collapse the compact M1 system log in the left panel."""
        expanded = self.log_area.maximumHeight() > 180
        if expanded:
            self.log_area.setMaximumHeight(125)
            self.toggle_logs_button.setText("↕")
        else:
            self.log_area.setMaximumHeight(360)
            self.toggle_logs_button.setText("↕")

    def toggle_m1_side_panel(self):
        if not hasattr(self, "m1_left_scroll"):
            return
        show = not self.m1_left_scroll.isVisible()
        self.m1_left_scroll.setVisible(show)
        if show and hasattr(self, "m1_splitter"):
            self.m1_splitter.setSizes([270, max(700, self.m1_splitter.width() - 270)])
        self.toggle_m1_panel_button.setText("◀" if show else "▶")

    def _clear_plot_selection_visual(self):
        if self.plot_view is not None and self._plot_page_ready:
            self.plot_view.page().runJavaScript("window.czspecClearSelection && window.czspecClearSelection();")

    def _selection_mode_changed(self, *_):
        # Una selección pertenece únicamente al modo activo al momento de crearla.
        # Al cambiar baseline/extract se descarta cualquier contorno temporal previo.
        self._clear_plot_selection_visual()

    def _ensure_extraction_history(self, state: dict):
        history = list(state.get("extraction_history") or [])
        if not history:
            history = [{"path": str(state.get("analysis_path") or state.get("original_analysis_path") or self.selected_file),
                        "display_name": str(state.get("display_name") or state.get("base_display_name") or Path(str(self.selected_file)).name)}]
            state["extraction_history"] = history
            state["extraction_index"] = 0
        idx = max(0, min(int(state.get("extraction_index") or 0), len(history)-1))
        state["extraction_index"] = idx
        return history, idx

    def _update_extraction_nav_buttons(self):
        if not hasattr(self, "selection_back_button"):
            return
        if not self.selected_file or self.selected_file not in self.spectrum_session:
            self.selection_back_button.setEnabled(False); self.selection_forward_button.setEnabled(False); self.restore_extracted_button.setEnabled(False); return
        history, idx = self._ensure_extraction_history(self.spectrum_session[self.selected_file])
        self.selection_back_button.setEnabled(idx > 0)
        self.selection_forward_button.setEnabled(idx < len(history)-1)
        self.restore_extracted_button.setEnabled(idx > 0)

    def _capture_current_extraction_snapshot(self, state: dict):
        history, idx = self._ensure_extraction_history(state)
        entry = history[idx]
        entry["snapshot"] = {
            "last_result": state.get("last_result"),
            "analyzed_plot_json": state.get("analyzed_plot_json"),
            "analyzed_clean_plot_json": state.get("analyzed_clean_plot_json"),
            "current_plot_json": state.get("current_plot_json"),
            "current_view_mode": state.get("current_view_mode") or "raw",
            "manual_peak_freqs": list(state.get("manual_peak_freqs") or []),
            "removed_peak_freqs": list(state.get("removed_peak_freqs") or []),
            "removed_detection_ids": list(state.get("removed_detection_ids") or []),
            "current_view_ranges": deepcopy(state.get("current_view_ranges")),
        }
        state["extraction_history"] = history

    def _restore_extraction_snapshot(self, state: dict, entry: dict):
        snap = dict(entry.get("snapshot") or {})
        if not snap:
            self._invalidate_active_analysis_after_smoothing(state)
            return
        for key in ("last_result","analyzed_plot_json","analyzed_clean_plot_json","current_plot_json","current_view_mode","current_view_ranges"):
            state[key] = snap.get(key)
        state["manual_peak_freqs"] = list(snap.get("manual_peak_freqs") or [])
        state["removed_peak_freqs"] = list(snap.get("removed_peak_freqs") or [])
        state["removed_detection_ids"] = list(snap.get("removed_detection_ids") or [])
        self.last_result = state.get("last_result")
        self.analyzed_plot_json = state.get("analyzed_plot_json")
        self.analyzed_clean_plot_json = state.get("analyzed_clean_plot_json")
        self.current_plot_json = state.get("current_plot_json") or state.get("raw_plot_json")
        self.current_view_mode = state.get("current_view_mode") or "raw"
        self.manual_peak_freqs = list(state.get("manual_peak_freqs") or [])
        self.removed_peak_freqs = list(state.get("removed_peak_freqs") or [])
        self.removed_detection_ids = list(state.get("removed_detection_ids") or [])
        self.current_view_ranges = state.get("current_view_ranges")
        self._populate_detections((self.last_result or {}).get("detected_peak_items", []))
        has_df = bool(self.last_result is not None and getattr((self.last_result or {}).get("results_df"), "empty", True) is False)
        self.export_csv_button.setEnabled(has_df)
        self.export_html_button.setEnabled(bool(state.get("raw_plot_json") or self.current_plot_json))

    def _apply_extraction_history_index(self, index: int):
        if not self.selected_file or self.selected_file not in self.spectrum_session:
            return
        state = self.spectrum_session[self.selected_file]
        history, current_idx = self._ensure_extraction_history(state)
        self._capture_current_extraction_snapshot(state)
        index = max(0, min(int(index), len(history)-1)); entry = history[index]
        state["extraction_index"] = index
        state["analysis_path"] = str(entry["path"]); state["display_name"] = str(entry["display_name"])
        # Rebuild only the raw representation for the target extraction, then
        # restore that extraction's own analysis snapshot if it has one.
        self._refresh_active_metadata_plot()
        self.raw_plot_json = state.get("raw_plot_json")
        self._restore_extraction_snapshot(state, entry)
        self.raw_plot_json = state.get("raw_plot_json")
        render_json = self.current_plot_json or self.raw_plot_json
        render_mode = self.current_view_mode or "raw"
        self.render_plot_full(render_json, mode=render_mode)
        self._clear_plot_selection_visual(); self._update_extraction_nav_buttons()
        try:
            pos=self.selected_files.index(self.selected_file)+1; self.file_label.setText((f"Active spectrum {pos}/{len(self.selected_files)}: " if self.ui_language=="en" else f"Espectro activo {pos}/{len(self.selected_files)}: ")+state["display_name"])
        except Exception: pass

    def _navigate_extraction_history(self, delta: int):
        if not self.selected_file or self.selected_file not in self.spectrum_session:return
        state=self.spectrum_session[self.selected_file]; history,idx=self._ensure_extraction_history(state)
        target=idx+int(delta)
        if 0 <= target < len(history): self._apply_extraction_history_index(target)

    def _add_baseline_selection(self, lo: float, hi: float):
        try: windows=self._parse_baseline_windows(self.baseline_windows_input.text())
        except Exception: windows=[]
        degree=int(self.baseline_combo.currentText())
        # El estado actual, no el historial, es lo que se dibuja: las selecciones
        # solapadas se fusionan y el último grado elegido gobierna la unión.
        merged_lo, merged_hi = lo, hi; kept=[]
        for a,b,d in windows:
            if b < merged_lo or a > merged_hi: kept.append((a,b,d))
            else: merged_lo=min(merged_lo,a); merged_hi=max(merged_hi,b)
        kept.append((merged_lo,merged_hi,degree)); kept.sort(key=lambda x:x[0])
        self.baseline_windows_input.setText(", ".join(self._format_baseline_window(x) for x in kept))
        idx=self.baseline_mode_combo.findData("windows")
        if idx>=0:self.baseline_mode_combo.setCurrentIndex(idx)
        self._update_baseline_window_visibility(); self._clear_plot_selection_visual()
        token=self._format_baseline_window((merged_lo,merged_hi,degree))
        self.log((f"[INFO] Baseline window added from plot: {token} MHz" if self.ui_language=="en" else f"[INFO] Ventana de línea base agregada desde la gráfica: {token} MHz"))

    def reset_active_spectrum(self):
        """Vuelve al archivo originalmente cargado y elimina todo el estado derivado de M1."""
        if not self.selected_file or self.selected_file not in self.spectrum_session:return
        state=self.spectrum_session[self.selected_file]; original=str(state.get("original_analysis_path") or self.selected_file); base=str(state.get("base_display_name") or Path(self.selected_file).name)
        try:
            raw=load_raw_spectrum(original,plot_styles=deepcopy(self.plot_styles),display_name=base,input_metadata=merge_source_metadata(state.get("source_metadata"),state.get("base_class30m_meta"),state.get("fits_meta")),language=self.ui_language)
        except Exception as exc:
            self.notify("Error",str(exc));return
        state.update({"analysis_path":original,"display_name":base,"raw_result":raw,"raw_plot_json":raw["plot_json"],"current_plot_json":raw["plot_json"],"current_view_mode":"raw","last_result":None,"analyzed_plot_json":None,"analyzed_clean_plot_json":None,"manual_peak_freqs":[],"removed_peak_freqs":[],"removed_detection_ids":[],"current_view_ranges":None,"smoothing_meta":{"smooth_method":"none","smooth_value":None,"smooth_engine":"czspec-native","hanning_passes":0},"extraction_history":[{"path":original,"display_name":base}],"extraction_index":0,"class30m_meta":deepcopy(state.get("base_class30m_meta"))})
        self.last_result=None;self.raw_plot_json=raw["plot_json"];self.analyzed_plot_json=None;self.analyzed_clean_plot_json=None;self.current_plot_json=self.raw_plot_json;self.current_view_mode="raw";self.manual_peak_freqs=[];self.removed_peak_freqs=[];self.removed_detection_ids=[];self.current_view_ranges=None
        self.baseline_windows_input.clear(); idx=self.baseline_mode_combo.findData("auto");
        if idx>=0:self.baseline_mode_combo.setCurrentIndex(idx)
        self._populate_detections([]); self.export_csv_button.setEnabled(False);self.export_html_button.setEnabled(True);self._update_extraction_nav_buttons();self.render_plot_full(self.raw_plot_json,mode="raw");self._clear_plot_selection_visual()
        self.log("[OK] Spectrum reset to the originally loaded data." if self.ui_language=="en" else "[OK] Espectro reiniciado a los datos cargados originalmente.")

    def _handle_plot_selection(self,a:float,b:float):
        if not self.selected_file or not np.isfinite(a) or not np.isfinite(b):return
        lo,hi=sorted((float(a),float(b)))
        if lo==hi:return
        action=str(self.selection_action_combo.currentData() or "baseline")
        if action=="baseline":self._add_baseline_selection(lo,hi);return
        # Extract usa exclusivamente la selección recién recibida en modo extract.
        self._extract_selected_region(lo,hi)

    def _active_analysis_metadata(self, state: dict | None = None) -> dict:
        state = state or (self.spectrum_session.get(self.selected_file, {}) if self.selected_file else {})
        return merge_source_metadata(
            state.get("source_metadata"), state.get("class30m_meta"),
            state.get("fits_meta"), state.get("smoothing_meta")
        )

    def _extract_selected_region(self,lo:float,hi:float):
        if not self.selected_file or self.selected_file not in self.spectrum_session:return
        state=self.spectrum_session[self.selected_file]; history,idx=self._ensure_extraction_history(state)
        self._capture_current_extraction_snapshot(state)
        history,idx=self._ensure_extraction_history(state)
        source_path=str(history[idx]["path"]); source_name=str(history[idx]["display_name"])
        try:
            raw=load_raw_spectrum(source_path,plot_styles=deepcopy(self.plot_styles),display_name=source_name,input_metadata=self._active_analysis_metadata(state),language=self.ui_language)
            freq=np.asarray(raw.get("freq",[]),dtype=float);inten=np.asarray(raw.get("inten",[]),dtype=float);mask=np.isfinite(freq)&np.isfinite(inten)&(freq>=lo)&(freq<=hi)
            if int(mask.sum())<4:
                self.notify_info("The selected region contains too few channels." if self.ui_language=="en" else "La región seleccionada contiene muy pocos canales.");self._clear_plot_selection_visual();return
            TEMP_DIR.mkdir(parents=True,exist_ok=True);signature=hashlib.sha1(f"{source_path}|{lo:.12g}|{hi:.12g}|{len(history)}".encode()).hexdigest()[:10];out=TEMP_DIR/f"m1_extract_{Path(source_path).stem}_{signature}.dat"
            meta=self._active_analysis_metadata(state); header=["CZSpec temporary spectral extraction",f"source_path={source_path}"]
            for key in ("canonical_name","raw_source_name","rest_frequency_mhz","vlsr_kms","m1_reference_line_active","bunit","frequency_step_mhz","velocity_step_kms"):
                val=meta.get(key)
                if val not in (None,"",[]):header.append(f"{key}={val}")
            np.savetxt(out,np.column_stack([freq[mask],inten[mask]]),header="\n".join(header),comments="# ")
            display=f"{source_name} · "+(f"extract {lo:.6g}–{hi:.6g} MHz" if self.ui_language=="en" else f"recorte {lo:.6g}–{hi:.6g} MHz")
            # Nueva selección después de volver atrás crea una nueva rama de historial.
            history=history[:idx+1];history.append({"path":str(out),"display_name":display});state["extraction_history"]=history;state["extraction_index"]=len(history)-1;state["analysis_path"]=str(out);state["display_name"]=display
            self._refresh_active_metadata_plot();self._invalidate_active_analysis_after_smoothing(state);self.raw_plot_json=state.get("raw_plot_json");self.current_plot_json=self.raw_plot_json;self.render_plot_full(self.raw_plot_json,mode="raw");self._clear_plot_selection_visual();self._update_extraction_nav_buttons()
            self.log((f"[OK] Temporary spectral extraction: {lo:.6g}–{hi:.6g} MHz" if self.ui_language=="en" else f"[OK] Recorte espectral temporal: {lo:.6g}–{hi:.6g} MHz"))
        except Exception as exc:self.log(f"[ERROR] Spectral extraction: {exc}");self.notify("Error",str(exc))

    def restore_full_spectrum(self):
        if not self.selected_file or self.selected_file not in self.spectrum_session:return
        state=self.spectrum_session[self.selected_file];history,idx=self._ensure_extraction_history(state)
        if idx==0:self._clear_plot_selection_visual();return
        self._apply_extraction_history_index(0)
        self.log("[OK] Full selection state restored." if self.ui_language=="en" else "[OK] Se restauró el estado espectral completo previo a los recortes.")

    def _detection_item_by_id(self, detection_id: str):
        target = str(detection_id or "")
        if not target:
            return None
        for item in list((self.last_result or {}).get("detected_peak_items") or []):
            if str(item.get("detection_id") or "") == target:
                return item
        return None

    def _mark_detection_id_for_removal(self, detection_id: str, fallback_frequency: float | None = None):
        """Mark exactly one accepted component by immutable detection_id.

        Visual labels (L1, L2, ...) and fitted centers are intentionally not
        identities: both can change after sorting/refitting.  This is the only
        backend used by plot and table deletion.
        """
        detection_id = str(detection_id or "")
        item = self._detection_item_by_id(detection_id)
        if item is None:
            return False, None
        if detection_id in {str(v) for v in self.removed_detection_ids}:
            return False, item
        try:
            seed = float(item.get("freq", fallback_frequency))
        except Exception:
            seed = float(fallback_frequency) if fallback_frequency is not None else np.nan
        self.removed_detection_ids.append(detection_id)
        if np.isfinite(seed):
            # Keep the old frequency tombstone only as a residual-search guard.
            # It never decides which retained component is removed.
            channel = max(self._manual_edit_tolerance_mhz() / 1.25, 1e-7)
            tol = max(0.20 * channel, 1e-8)
            if not any(abs(seed - f) < tol for f in self.removed_peak_freqs):
                self.removed_peak_freqs.append(seed)
            self.manual_peak_freqs = [f for f in self.manual_peak_freqs if abs(f - seed) >= tol]
        return True, item

    def _remove_detection_by_id_from_plot(self, detection_id: str, frequency_mhz: float):
        if not self.selected_file:
            return
        # Plot clicks remain possible while the worker is fitting.  Never mutate
        # the tombstone set in the middle of an in-flight local refit, otherwise
        # the worker result and the edit state can describe different component
        # sets (the intermittent wrong-line deletion seen in a78).
        if "spectral_analysis" in self._active_tasks:
            self.notify_info(
                "Wait for the current local refit to finish before deleting another component."
                if self.ui_language == "en" else
                "Espera a que termine el reajuste local actual antes de eliminar otra componente."
            )
            return
        changed, item = self._mark_detection_id_for_removal(detection_id, frequency_mhz)
        if not changed:
            return
        try:
            seed = float(item.get("freq", frequency_mhz))
        except Exception:
            seed = float(frequency_mhz)
        self.log(
            (f"[OK] Detection removed: id={detection_id}, seed={seed:.6f} MHz"
             if self.ui_language == "en" else
             f"[OK] Detección eliminada: id={detection_id}, semilla={seed:.6f} MHz")
        )
        self.update_detections_preserving_view()

    def _remove_detection_from_plot(self,line_number:int,frequency_mhz:float):
        """Compatibility route for old cached plots that only carry L-number."""
        if not self.selected_file:
            return
        items=list((self.last_result or {}).get("detected_peak_items") or [])
        candidate = items[int(line_number)-1] if 1 <= int(line_number) <= len(items) else None
        if candidate is None:
            return
        detection_id = str(candidate.get("detection_id") or "")
        if detection_id:
            self._remove_detection_by_id_from_plot(detection_id, frequency_mhz)

    def _add_detection_from_plot(self, frequency_mhz: float, _intensity: float = 0.0):
        if not self.selected_file or not np.isfinite(frequency_mhz):
            return
        if "spectral_analysis" in self._active_tasks:
            self.notify_info(
                "Wait for the current local refit to finish before adding another component."
                if self.ui_language == "en" else
                "Espera a que termine el reajuste local actual antes de agregar otra componente."
            )
            return
        fmin, fmax = self._get_current_spectrum_range()
        if fmin is None or not (fmin <= frequency_mhz <= fmax):
            return
        tol = self._manual_edit_tolerance_mhz()
        if not any(abs(float(frequency_mhz) - f) < tol for f in self.manual_peak_freqs):
            self.manual_peak_freqs.append(float(frequency_mhz))
        self.removed_peak_freqs = [f for f in self.removed_peak_freqs if abs(float(frequency_mhz) - f) >= tol]
        self.log(
            f"[OK] Manual detection added from plot at {frequency_mhz:.6f} MHz" if self.ui_language == "en"
            else f"[OK] Detección manual agregada desde la gráfica en {frequency_mhz:.6f} MHz"
        )
        self.update_detections_preserving_view()

    def _get_current_spectrum_range(self):
        """
        Devuelve (fmin, fmax) del espectro cargado.
        """
        if not self.selected_file:
            return None, None

        try:
            state = self.spectrum_session.get(self.selected_file, {})
            raw_result = state.get("raw_result") or load_raw_spectrum(self.selected_file)
            freq = np.asarray(raw_result["freq"], dtype=float)
            if freq.size == 0:
                return None, None
            return float(freq.min()), float(freq.max())
        except Exception:
            return None, None

    def _parse_float_list(self, raw_text: str) -> list[float]:
        """
        Parsea una lista de frecuencias separadas por comas, espacios o saltos de línea.
        No acepta rangos con '-'.
        Ejemplo:
            85926.11, 86245.62 86342.09
        """
        if not raw_text or not raw_text.strip():
            return []

        text = raw_text.strip()

        # Si hay rangos tipo 13-17, esto NO debe interpretarse como frecuencias
        if re.search(r"\d+\s*-\s*\d+", text):
            raise ValueError(
                "Se detectaron rangos tipo 13-17. Para AGREGAR solo se aceptan frecuencias individuales."
            )

        parts = re.split(r"[,\s;]+", text)
        values = []

        for part in parts:
            part = part.strip()
            if not part:
                continue
            values.append(float(part))

        return values

    def _parse_index_ranges(self, raw_text: str) -> tuple[list[int], list[str]]:
        """
        Parsea índices/rangos tipo:
            5,10,13-17,22-24
        Devuelve:
            - lista ordenada de índices únicos
            - lista de tokens inválidos
        """
        if not raw_text or not raw_text.strip():
            return [], []

        indices = set()
        invalid = []

        parts = [p.strip() for p in raw_text.split(",") if p.strip()]

        for part in parts:
            if re.fullmatch(r"\d+", part):
                indices.add(int(part))
                continue

            if re.fullmatch(r"\d+\s*-\s*\d+", part):
                a_txt, b_txt = re.split(r"\s*-\s*", part)
                a = int(a_txt)
                b = int(b_txt)

                if a <= b:
                    for k in range(a, b + 1):
                        indices.add(k)
                else:
                    for k in range(b, a + 1):
                        indices.add(k)
                continue

            invalid.append(part)

        return sorted(indices), invalid

    def _get_detection_items(self):
        """Return visible detections with immutable IDs and current centers."""
        items = []
        for row in range(self.detections_list.rowCount()):
            cell = self.detections_list.item(row, 0)
            if cell is None:
                continue
            data = cell.data(Qt.ItemDataRole.UserRole)
            if not isinstance(data, dict) or "freq" not in data:
                continue
            items.append({
                "display_index": len(items) + 1,
                "detection_id": str(data.get("detection_id") or ""),
                "freq": float(data["freq"]),
                "fit_freq": float(data.get("fit_freq", data["freq"])),
                "origin": data.get("origin", "auto"),
                "item": cell,
                "row": row,
                "data": data,
            })
        return items

    def _resolve_removal_input(self, raw_text: str):
        """
        Interpreta el input del botón Eliminar.
        Puede ser:
        - índices/rangos: 5,10,13-17
        - frecuencias: 85926.11, 86245.62

        Regresa un dict con:
            {
                "freqs_to_remove": [...],
                "invalid_tokens": [...],
                "missing_indices": [...],
                "missing_freqs": [...],
                "mode": "indices" | "frequencies" | "empty"
            }
        """
        result = {
            "freqs_to_remove": [],
            "invalid_tokens": [],
            "missing_indices": [],
            "missing_freqs": [],
            "mode": "empty",
        }

        raw_text = (raw_text or "").strip()
        if not raw_text:
            return result

        detection_items = self._get_detection_items()
        if not detection_items:
            return result

        # Si hay un rango explícito, interpretamos como índices/rangos
        if re.search(r"\d+\s*-\s*\d+", raw_text):
            idx_list, invalid = self._parse_index_ranges(raw_text)
            result["invalid_tokens"] = invalid
            result["mode"] = "indices"

            valid_map = {d["display_index"]: d["freq"] for d in detection_items}

            for idx in idx_list:
                if idx in valid_map:
                    result["freqs_to_remove"].append(valid_map[idx])
                else:
                    result["missing_indices"].append(idx)

            return result

        # Si no hay rangos, intentamos decidir:
        # - enteros pequeños -> índices
        # - decimales o números grandes -> frecuencias
        parts = [p.strip() for p in re.split(r"[,\s;]+", raw_text) if p.strip()]
        if not parts:
            return result

        looks_like_indices = True
        for p in parts:
            if not re.fullmatch(r"\d+", p):
                looks_like_indices = False
                break

        if looks_like_indices:
            idx_list, invalid = self._parse_index_ranges(",".join(parts))
            result["invalid_tokens"] = invalid
            result["mode"] = "indices"

            valid_map = {d["display_index"]: d["freq"] for d in detection_items}

            for idx in idx_list:
                if idx in valid_map:
                    result["freqs_to_remove"].append(valid_map[idx])
                else:
                    result["missing_indices"].append(idx)

            return result

        # Si no fueron índices, interpretamos como frecuencias
        result["mode"] = "frequencies"

        try:
            freq_list = self._parse_float_list(raw_text)
        except Exception:
            result["invalid_tokens"] = [raw_text]
            return result

        detection_freqs = [d["freq"] for d in detection_items]

        # tolerancia pequeña pero realista para empatar contra detecciones mostradas
        # aquí usamos 0.01 MHz
        tol_mhz = 0.01

        for f_user in freq_list:
            matched = None
            best_diff = None

            for f_det in detection_freqs:
                diff = abs(f_user - f_det)
                if diff <= tol_mhz and (best_diff is None or diff < best_diff):
                    matched = f_det
                    best_diff = diff

            if matched is not None:
                result["freqs_to_remove"].append(matched)
            else:
                result["missing_freqs"].append(f_user)

        return result

    def _manual_edit_tolerance_mhz(self) -> float:
        """Tolerancia de edición equivalente a aproximadamente un canal.

        Las listas de M1 muestran el centro *ajustado*, mientras que el estado de
        borrado conserva la frecuencia-semilla (un canal real). Compararlas con
        una tolerancia numérica de 1e-6 MHz hacía que una línea eliminada y luego
        re-agregada pudiera quedar simultáneamente en ``manual_peak_freqs`` y
        ``removed_peak_freqs``. La tolerancia basada en el muestreo resuelve esa
        diferencia sin fusionar líneas físicamente separadas.
        """
        try:
            if self.selected_file:
                state = self.spectrum_session.get(self.selected_file, {})
                raw = state.get("raw_result") or load_raw_spectrum(self.selected_file)
                freq = np.asarray(raw.get("freq", []), dtype=float)
                freq = np.sort(freq[np.isfinite(freq)])
                diffs = np.diff(freq)
                diffs = diffs[diffs > 0]
                if diffs.size:
                    return max(1.25 * float(np.nanmedian(diffs)), 1e-6)
        except Exception:
            pass
        return 0.01

    def _mark_frequency_for_removal(self, freq: float):
        """Legacy/manual-input resolver; deletion itself remains ID based."""
        try:
            target = float(freq)
        except Exception:
            return False
        if not np.isfinite(target):
            return False
        items = list((self.last_result or {}).get("detected_peak_items") or [])
        if not items:
            return False
        # Compare against both displayed fitted center and immutable seed.  This
        # function is only for typed frequency input; plot/table paths carry IDs.
        candidates = []
        for item in items:
            detection_id = str(item.get("detection_id") or "")
            if not detection_id:
                continue
            try:
                seed = float(item.get("freq"))
                fit = float(item.get("fit_freq", seed))
            except Exception:
                continue
            dist = min(abs(target - seed), abs(target - fit))
            candidates.append((dist, detection_id, seed))
        if not candidates:
            return False
        candidates.sort(key=lambda row: row[0])
        broad = self._manual_edit_tolerance_mhz()
        dist, detection_id, seed = candidates[0]
        if dist > max(broad, 0.01):
            return False
        # If two components are effectively equidistant, refuse to guess.
        if len(candidates) > 1 and abs(candidates[1][0] - dist) < 1e-9:
            return False
        changed, _ = self._mark_detection_id_for_removal(detection_id, seed)
        return changed

    def add_manual_detection(self):
        if not self.selected_file:
            QMessageBox.warning(self, "Advertencia", "Primero carga un archivo.")
            return

        raw = self.manual_freq_input.text().strip()
        if not raw:
            QMessageBox.warning(self, "Advertencia", "Escribe una o varias frecuencias en MHz.")
            return

        fmin, fmax = self._get_current_spectrum_range()
        if fmin is None or fmax is None:
            QMessageBox.warning(self, "Advertencia", "No se pudo determinar el rango del espectro cargado.")
            return

        try:
            freq_values = self._parse_float_list(raw)
        except Exception as e:
            QMessageBox.warning(self, "Advertencia", str(e))
            return

        if not freq_values:
            QMessageBox.warning(self, "Advertencia", "No se detectaron frecuencias válidas.")
            return

        added = 0
        duplicates = []
        out_of_range = []
        tol = self._manual_edit_tolerance_mhz()

        for freq in freq_values:
            if not (fmin <= freq <= fmax):
                out_of_range.append(freq)
                continue

            if any(abs(freq - f) < tol for f in self.manual_peak_freqs):
                duplicates.append(freq)
                continue

            self.manual_peak_freqs.append(freq)
            # Re-agregar significa explícitamente "deshacer el borrado". La
            # eliminación previa puede almacenar la semilla mientras el usuario
            # escribe el centro ajustado; por eso se usa tolerancia de canal.
            self.removed_peak_freqs = [f for f in self.removed_peak_freqs if abs(f - freq) >= tol]
            added += 1

        self.manual_freq_input.clear()

        if added > 0:
            self.log(f"[OK] Detecciones manuales agregadas: {added}")

        if duplicates:
            self.log(
                "[INFO] Frecuencias omitidas por estar repetidas: "
                + ", ".join(f"{x:.6f}" for x in duplicates)
            )

        if out_of_range:
            msg = (
                "Las siguientes frecuencias están fuera del rango del espectro cargado:\n\n"
                + "\n".join(f"{x:.6f} MHz" for x in out_of_range)
            )
            self.log("[WARN] " + msg.replace("\n", " | "))
            QMessageBox.warning(self, "Frecuencias fuera de rango", msg)

        if added == 0 and not out_of_range and not duplicates:
            self.notify_info("No se agregó ninguna frecuencia.")
            return

        if added > 0:
            self.update_detections_preserving_view()

    def _selected_detection_rows(self) -> list[int]:
        """Return selected detection rows robustly from embedded/detached tables.

        ``selectedRows()`` can be empty on some Qt styles after the row was
        focused programmatically.  Collecting selectedIndexes and falling back
        to currentRow restores the pre-a65 behaviour expected by M1 users.
        """
        rows = set()
        model = self.detections_list.selectionModel()
        if model is not None:
            rows.update(index.row() for index in model.selectedIndexes())
        if not rows and self.detections_list.currentRow() >= 0:
            rows.add(self.detections_list.currentRow())
        floating = getattr(self, "_detected_lines_floating_table", None)
        if floating is not None and floating.isVisible():
            fmodel = floating.selectionModel()
            if fmodel is not None:
                rows.update(index.row() for index in fmodel.selectedIndexes())
            if not rows and floating.currentRow() >= 0:
                rows.add(floating.currentRow())
        return sorted(r for r in rows if 0 <= r < self.detections_list.rowCount())

    def remove_selected_detections(self):
        selected_rows = self._selected_detection_rows()
        raw = self.manual_freq_input.text().strip()
        ids_to_remove = []
        removed_count = 0

        # Rows are identity-based.  The visible L-number is never used as an ID.
        for row in selected_rows:
            item = self.detections_list.item(row, 0)
            if item is None:
                continue
            data = item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(data, dict):
                continue
            detection_id = str(data.get("detection_id") or "")
            if detection_id and detection_id not in ids_to_remove:
                ids_to_remove.append(detection_id)

        # Text input remains supported for compatibility.  Index/frequency text
        # is resolved against the current accepted state and then converted to ID.
        parsed = self._resolve_removal_input(raw)
        for freq in parsed["freqs_to_remove"]:
            candidates=[]
            for det in list((self.last_result or {}).get("detected_peak_items") or []):
                did=str(det.get("detection_id") or "")
                if not did: continue
                try:
                    seed=float(det.get("freq")); fit=float(det.get("fit_freq",seed))
                except Exception:
                    continue
                candidates.append((min(abs(float(freq)-seed),abs(float(freq)-fit)),did))
            if candidates:
                candidates.sort(key=lambda x:x[0])
                did=candidates[0][1]
                if did not in ids_to_remove: ids_to_remove.append(did)

        if not ids_to_remove and not parsed["invalid_tokens"] and not parsed["missing_indices"] and not parsed["missing_freqs"]:
            self.notify_info(
                "Select detections in the table or enter indices/ranges/frequencies to remove."
                if self.ui_language == "en" else
                "Selecciona detecciones en la lista o escribe índices/rangos/frecuencias para eliminar."
            )
            return

        for detection_id in ids_to_remove:
            changed, _item = self._mark_detection_id_for_removal(detection_id)
            if changed:
                removed_count += 1

        self.manual_freq_input.clear()
        if removed_count > 0:
            self.log(
                f"[OK] Detections marked for removal: {removed_count}"
                if self.ui_language == "en" else
                f"[OK] Detecciones marcadas para eliminar: {removed_count}"
            )

        if parsed["invalid_tokens"]:
            msg = (
                "Se ignoraron entradas con formato inválido:\n\n"
                + "\n".join(str(x) for x in parsed["invalid_tokens"])
            )
            self.log("[WARN] " + msg.replace("\n", " | "))
            QMessageBox.warning(self, "Formato inválido", msg)
        if parsed["missing_indices"]:
            msg = (
                "Los siguientes índices no existen en las detecciones actuales:\n\n"
                + ", ".join(str(x) for x in parsed["missing_indices"])
            )
            self.log("[WARN] " + msg.replace("\n", " | "))
            QMessageBox.warning(self, "Índices inexistentes", msg)
        if parsed["missing_freqs"]:
            msg = (
                "No se encontraron detecciones cercanas a las siguientes frecuencias:\n\n"
                + "\n".join(f"{x:.6f} MHz" for x in parsed["missing_freqs"])
            )
            self.log("[WARN] " + msg.replace("\n", " | "))
            QMessageBox.warning(self, "Frecuencias sin coincidencia", msg)

        if removed_count > 0:
            # One local refit for the full edit, even when several rows were selected.
            self.update_detections_preserving_view()

    def run_process(self):
        self.execute_analysis(preserve_view=False, reset_manual_state=True)

    def _translate_species_log_line(self, message: str) -> str:
        text = str(message)
        en = self.ui_language == "en"
        pairs = (
            ("Generación de gráficas desactivada en esta corrida.", "Plot generation disabled for this run."),
            ("Tabla principal final:", "Final main table:"),
            ("filas", "rows"),
            ("JPL Q(T):", "JPL Q(T):"),
            ("tags cargados", "tags loaded"),
            ("CDMS Q(T):", "CDMS Q(T):"),
            ("Buscando coincidencias cercanas para", "Searching nearby matches for"),
            ("líneas", "lines"),
            ("Consulta base a Splatalogue y TOP-K completados.", "Base Splatalogue query and TOP-K completed."),
            ("Identificación molecular terminada correctamente.", "Molecular identification completed successfully."),
            ("Selección actualizada para", "Selection updated for"),
            ("con filtro activo", "with active filter"),
            ("Filtros de identificación actualizados.", "Identification filters updated."),
            ("Perfil:", "Profile:"),
            ("Archivo de entrada:", "Input file:"),
            ("Nombre base de salida:", "Output base name:"),
            ("Temperaturas objetivo:", "Target temperatures:"),
            ("Perfil de identificación:", "Identification profile:"),
            ("Filtros M2:", "M2 filters:"),
            ("Generar gráficas Q(T):", "Generate Q(T) plots:"),
            ("Generar gráficas Plotly:", "Generate Plotly plots:"),
            ("Calcular Q(T):", "Compute Q(T):"),
            ("Directorio raíz de species_search:", "species_search root directory:"),
            ("Directorio de ejecución:", "Run directory:"),
            ("Ruta prevista para Plotly:", "Planned Plotly path:"),
            ("Ruta prevista para Q(T):", "Planned Q(T) path:"),
            ("CSV cargado:", "CSV loaded:"),
            ("filas iniciales", "initial rows"),
            ("CSV limpio:", "Clean CSV:"),
            ("filas válidas", "valid rows"),
            ("Sin candidatos en consulta base.", "No candidates in base query."),
            ("candidatos base.", "base candidates."),
            ("Total de candidatos acumulados:", "Total accumulated candidates:"),
            ("[RESCATE] Reintentando", "[RESCUE] Retrying"),
            ("líneas con ventana ampliada.", "lines with expanded window."),
            ("Error en rescate:", "Rescue error:"),
            ("[SOFT] Aplicando modo soft a", "[SOFT] Applying soft mode to"),
            ("[EMERGENCIA] Buscando coincidencias cercanas para", "[EMERGENCY] Searching nearby matches for"),
            ("Error en emergencia:", "Emergency error:"),
            ("Cálculo de Q(T) desactivado en esta corrida.", "Q(T) calculation disabled for this run."),
            ("Gráficas Q(T) generadas:", "Q(T) plots generated:"),
            ("No se generó figura para Source=", "No figure generated for Source="),
            ("No se generaron gráficas Plotly", "No Plotly plots were generated"),
            ("Ocurrió un error al ejecutar el buscador de especies.", "An error occurred while running molecular identification."),
            ("Observaciones sin coincidencias:", "Observations without matches:"),
            ("Proceso terminado correctamente.", "Process completed successfully."),
            ("Candidatos", "Candidates"),
            ("Sin candidato plausible", "No plausible candidate"),
            ("Guardado", "Saved"),
            ("Error", "Error"),
        )
        if en:
            for es_text, en_text in pairs:
                text = text.replace(es_text, en_text)
        else:
            # Translate the known English messages emitted directly by newer M2 paths.
            for es_text, en_text in pairs:
                text = text.replace(en_text, es_text)
            text = text.replace("Molecular identification completed successfully. Main results and TOP-K are available.",
                                "La identificación molecular terminó correctamente. Las tablas de resultados principales y TOP-K ya están disponibles.")
            text = text.replace("Selection updated for", "Selección actualizada para")
            text = text.replace("with active filter", "con filtro activo")
        return text

    def log_species(self, message: str):
        raw = str(message)
        if hasattr(self, "_species_log_history"):
            self._species_log_history.append(raw)
            if len(self._species_log_history) > 2500:
                self._species_log_history = self._species_log_history[-2500:]
        self.species_log_area.append(self._translate_species_log_line(raw))

    def _rebuild_species_log_display(self):
        if not hasattr(self, "species_log_area") or not hasattr(self, "_species_log_history"):
            return
        self.species_log_area.clear()
        for raw in self._species_log_history:
            self.species_log_area.append(self._translate_species_log_line(raw))

    def _translate_column_density_log_line(self, message: str) -> str:
        text = str(message)
        en = self.ui_language == "en"
        pairs = (
            ("No hay selección disponible desde el buscador de especies.", "No selection is available from M2."),
            ("Entrada actualizada desde el buscador de especies:", "Input refreshed from M2:"),
            ("CSV manual cargado para densidad de columna:", "Manual column-density CSV loaded:"),
            ("No se pudo cargar el CSV manual:", "Could not load the manual CSV:"),
            ("Iniciando método ópticamente delgado (MOD)", "Starting optically thin method (OTM)"),
            ("Resultados MOD cargados en la tabla.", "OTM results loaded into the table."),
            ("No hay datos de entrada para MOD.", "No input data are available for OTM."),
            ("Iniciando método de transiciones hiperfinas (MTH)", "Starting hyperfine-transition method (HTM)"),
            ("MTH terminado correctamente.", "HTM completed successfully."),
            ("No hay datos de entrada para MTH.", "No input data are available for HTM."),
            ("Filas de entrada:", "Input rows:"),
            ("Temperaturas:", "Temperatures:"),
            ("Razones isotópicas de sesión:", "Session isotopic ratios:"),
            ("Aproximación de r:", "r approximation:"),
            ("Razones isotópicas actualizadas en sesión:", "Session isotopic ratios updated:"),
            ("Filtro aplicado:", "Filter applied:"),
        )
        if en:
            for es_text, en_text in pairs:
                text = text.replace(es_text, en_text)
            text = text.replace("MOD", "OTM").replace("MTH", "HTM")
        else:
            for es_text, en_text in pairs:
                text = text.replace(en_text, es_text)
            text = text.replace("OTM", "MOD").replace("HTM", "MTH")
        return text

    def log_column_density(self, message: str):
        raw = str(message)
        if hasattr(self, "_column_density_log_history"):
            self._column_density_log_history.append(raw)
            if len(self._column_density_log_history) > 2500:
                self._column_density_log_history = self._column_density_log_history[-2500:]
        if hasattr(self, "column_density_log_area"):
            self.column_density_log_area.append(self._translate_column_density_log_line(raw))

    def _rebuild_column_density_log_display(self):
        if not hasattr(self, "column_density_log_area"):
            return
        self.column_density_log_area.clear()
        for raw in list(getattr(self, "_column_density_log_history", []) or []):
            self.column_density_log_area.append(self._translate_column_density_log_line(raw))

    @staticmethod
    def _read_species_input_table(file_path: str) -> pd.DataFrame:
        """Lee tablas exportadas por M1 y las normaliza para el backend CSV de M2."""
        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix == ".csv":
            return pd.read_csv(path)
        if suffix in {".tsv"}:
            return pd.read_csv(path, sep="\t")
        if suffix in {".txt", ".dsv"}:
            return pd.read_csv(path, sep=None, engine="python")
        if suffix in {".xlsx", ".xls", ".ods"}:
            return pd.read_excel(path)
        if suffix == ".xml":
            return pd.read_xml(path)
        if suffix == ".json":
            try:
                return pd.read_json(path)
            except ValueError:
                return pd.read_json(path, lines=True)
        if suffix in {".html", ".htm"}:
            tables = pd.read_html(path)
            if not tables:
                raise ValueError("No se encontró ninguna tabla HTML.")
            return tables[0]
        if suffix in {".tex", ".latex"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            match = re.search(
                r"\\begin\{tabular\}.*?(.*?)\\end\{tabular\}",
                text,
                flags=re.S,
            )
            if not match:
                raise ValueError("No se encontró un entorno tabular en el archivo LaTeX.")
            rows = []
            for raw_line in match.group(1).splitlines():
                line = raw_line.strip()
                if not line or line.startswith("%"):
                    continue
                if any(token in line for token in ("\\toprule", "\\midrule", "\\bottomrule", "\\hline")):
                    line = line.replace("\\toprule", "").replace("\\midrule", "").replace("\\bottomrule", "").replace("\\hline", "").strip()
                    if not line:
                        continue
                if "&" not in line:
                    continue
                line = re.sub(r"\\\\\s*$", "", line).strip()
                cells = [
                    re.sub(r"\\([_%&#{}$])", r"\1", cell.strip())
                    for cell in line.split("&")
                ]
                rows.append(cells)
            if len(rows) < 2:
                raise ValueError("La tabla LaTeX no contiene filas de datos reconocibles.")
            width = max(len(row) for row in rows)
            rows = [row + [""] * (width - len(row)) for row in rows]
            header = rows[0]
            return pd.DataFrame(rows[1:], columns=header)
        raise ValueError(f"Formato de tabla no compatible: {suffix or 'sin extensión'}")

    def load_species_file(self):
        en = self.ui_language == "en"
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select M2 input table" if en else "Seleccionar tabla de entrada para M2",
            "",
            (
                "Tables (*.csv *.tsv *.txt *.dsv *.xlsx *.xls *.ods *.xml *.json *.html *.htm *.tex *.latex);;"
                "CSV (*.csv);;Excel/ODS (*.xlsx *.xls *.ods);;JSON/XML/HTML (*.json *.xml *.html *.htm);;"
                "LaTeX (*.tex *.latex);;All files (*)"
                if en else
                "Tablas (*.csv *.tsv *.txt *.dsv *.xlsx *.xls *.ods *.xml *.json *.html *.htm *.tex *.latex);;"
                "CSV (*.csv);;Excel/ODS (*.xlsx *.xls *.ods);;JSON/XML/HTML (*.json *.xml *.html *.htm);;"
                "LaTeX (*.tex *.latex);;Todos los archivos (*)"
            ),
        )
        if not file_path:
            return

        try:
            df = self._read_species_input_table(file_path)
            if df is None or df.empty:
                raise ValueError("The selected table is empty." if en else "La tabla seleccionada está vacía.")

            TEMP_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_csv = TEMP_DIR / f"{Path(file_path).stem}_for_species_{timestamp}.csv"
            df.to_csv(temp_csv, index=False)

            self.species_original_input_file = file_path
            self.species_selected_file = str(temp_csv)
            self.species_file_label.setText(
                (f"Loaded table: {Path(file_path).name} · {len(df)} row(s)" if en else
                 f"Tabla cargada: {Path(file_path).name} · {len(df)} fila(s)")
            )
            if not self.species_output_input.text().strip():
                self.species_output_input.setText(
                    self._suggest_species_output_name(df, Path(file_path).stem)
                )
            self.log_species(
                (f"[OK] M2 table loaded: {file_path} -> {temp_csv}" if en else
                 f"[OK] Tabla cargada para M2: {file_path} -> {temp_csv}")
            )
        except Exception as exc:
            self.log_species(f"[ERROR] {exc}")
            QMessageBox.critical(
                self,
                "Input error" if en else "Error de entrada",
                str(exc),
            )

    def load_column_density_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar CSV para densidad de columna",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return

        try:
            df = pd.read_csv(file_path)

            if df is None or df.empty:
                QMessageBox.warning(self, "Aviso", "El CSV seleccionado está vacío.")
                return

            self.column_density_manual_file = file_path
            self.column_density_manual_df = df.copy()
            self.column_density_source_df = df.copy()

            self.column_density_source_label.setText(
                f"CSV manual cargado: {Path(file_path).name} ({len(df)} fila(s))"
            )

            self.refresh_column_density_tables_from_filter()

            self.vasyunina_run_button.setEnabled(True)
            self.sanhueza_run_button.setEnabled(True)

            self.save_vasyunina_button.setEnabled(False)
            self.save_sanhueza_button.setEnabled(False)

            self.populate_table_widget_from_dataframe(self.vasyunina_results_table, None)
            self.populate_table_widget_from_dataframe(self.sanhueza_results_table, None)

            self.column_density_vasyunina_df = None
            self.column_density_sanhueza_df = None
            self._refresh_column_density_comparison_tables(None, None)
            self.column_density_tables_tabs.setCurrentWidget(
                self.column_density_source_table_box
            )

            self.log_column_density(f"[OK] CSV manual cargado para densidad de columna: {file_path}")

        except Exception as e:
            self.log_column_density(f"[ERROR] No se pudo cargar el CSV manual: {e}")
            QMessageBox.critical(self, "Error", str(e))

    def _session_peak_results_dataframe(self, scope: str = "session") -> tuple[pd.DataFrame, list[str]]:
        """Return M1 rows while preserving the source identity and source physics.

        M2 needs more than the fitted line table: the final identified-spectrum view
        must be able to reconnect every row with its originating spectrum and with
        the source VLSR.  Keeping those values here avoids fragile filename guesses
        later in the pipeline.
        """

        self._save_active_spectrum_state()
        paths = (
            [self.selected_file]
            if scope == "active" and self.selected_file
            else list(self.selected_files)
        )
        frames = []
        missing = []
        for file_path in paths:
            state = self.spectrum_session.get(file_path, {})
            result = state.get("last_result") or {}
            frame = result.get("results_df")
            if frame is None or frame.empty:
                missing.append(Path(file_path).name)
                continue

            prepared = frame.copy()
            # Keep both meanings visible: T_A is the fitted component amplitude,
            # whereas the purple M1 detection marker is the observed baseline-
            # corrected spectrum evaluated at the fitted centre.  They can differ
            # for noise/blends and must not be mistaken for a transfer mismatch.
            peak_items = list(result.get("detected_peak_items") or [])
            if peak_items and "detection_id" in prepared.columns:
                obs_at_fit = {}
                try:
                    from plotly import io as _pio
                    _fig = _pio.from_json(state.get("analyzed_plot_json") or result.get("plot_json") or "{}")
                    _det_trace = next((tr for tr in _fig.data if isinstance(getattr(tr, "meta", None), dict) and str(tr.meta.get("czspec_role") or "") == "detection"), None)
                    if _det_trace is not None:
                        for xval, yval, cdata in zip(list(_det_trace.x or []), list(_det_trace.y or []), list(_det_trace.customdata or [])):
                            try:
                                did = str(cdata[0]) if isinstance(cdata, (list, tuple)) else ""
                                if did:
                                    obs_at_fit[did] = float(yval)
                            except Exception:
                                pass
                except Exception:
                    obs_at_fit = {}
                if obs_at_fit:
                    prepared["T_obs_at_fit [K]"] = prepared["detection_id"].astype(str).map(obs_at_fit)
            meta = dict(self._active_analysis_metadata(state) or {})
            source_label = str(
                state.get("display_name")
                or self._spectrum_display_name(file_path)
                or meta.get("canonical_name")
                or meta.get("raw_source_name")
                or meta.get("source")
                or Path(file_path).stem
            ).strip()
            # M2 shows a human-facing source label.  The exact technical path is
            # preserved separately in source_path for reproducibility.
            prepared["Source"] = source_label

            prepared["source_path"] = str(file_path)
            try:
                vlsr = float(meta.get("vlsr_kms"))
                if np.isfinite(vlsr):
                    prepared["source_vlsr_kms"] = vlsr
            except Exception:
                pass
            frames.append(prepared)

        if not frames:
            return pd.DataFrame(), missing
        return pd.concat(frames, ignore_index=True, sort=False), missing

    def refresh_species_input_from_m1(self):
        en = self.ui_language == "en"
        scope = str(self.species_m1_scope_combo.currentData() or "active")
        frame, missing = self._session_peak_results_dataframe(scope)
        if frame.empty:
            self.notify_info(
                ("No analyzed results are available in the selected source. Run the active spectrum or the whole session in M1 first."
                 if en else
                 "No hay resultados analizados en el origen elegido. Ejecuta primero el análisis del espectro o de toda la sesión en el módulo 1.")
            )
            return
        if scope == "session":
            base_name = f"session_{len(self.selected_files)}_spectra" if en else f"sesion_{len(self.selected_files)}_espectros"
            description = (f"entire session ({len(frame)} lines)" if en else f"toda la sesión ({len(frame)} líneas)")
        else:
            base_name = Path(self.selected_file).stem if self.selected_file else ("spectrum" if en else "espectro")
            description = ((f"active spectrum {Path(self.selected_file).name}" if self.selected_file else "active spectrum") if en else
                           (f"espectro activo {Path(self.selected_file).name}" if self.selected_file else "espectro activo"))
        # Populate Q(T) temperatures only when the selected M1 spectra actually
        # carry excitation-temperature metadata.  No artificial default is used.
        temp_values = []
        temp_paths = ([self.selected_file] if scope == "active" and self.selected_file else list(self.selected_files))
        for _path in temp_paths:
            _state = (self.spectrum_session or {}).get(_path, {})
            _meta = dict(self._active_analysis_metadata(_state) or {})
            for _value in list(_meta.get("excitation_temperatures_k") or []):
                try:
                    _v = float(_value)
                    if np.isfinite(_v) and _v > 0:
                        temp_values.append(_v)
                except Exception:
                    pass
        if temp_values:
            _text = ", ".join(f"{v:g}" for v in sorted(set(temp_values)))
            self.species_temperatures_input.setText(_text)
        else:
            self.species_temperatures_input.clear()
            self.species_temperatures_input.setPlaceholderText("" )

        self.sync_peak_results_to_species_tab(frame, base_name=base_name, source_description=description)
        if missing:
            self.log_species(
                (("[WARN] Files without results were omitted: " if en else "[WARN] Archivos sin resultados, omitidos de la entrada: ")
                 + ", ".join(missing))
            )
            self.notify(
                "Partial input" if en else "Entrada parcial",
                (f"M2 received {len(frame)} lines; {len(missing)} file(s) still have no analysis." if en else
                 f"M2 recibió {len(frame)} líneas; {len(missing)} archivo(s) aún no tienen análisis."),
            )
        else:
            self.notify_success(
                f"M2 received {len(frame)} line(s) from {description}." if en else
                f"M2 recibió {len(frame)} línea(s) desde {description}."
            )

    def _suggest_species_output_name(self, df: pd.DataFrame | None = None, fallback: str = "m2_identification") -> str:
        """Build a compact M2 basename from source metadata whenever possible."""
        labels = []
        if df is not None and not df.empty and "Source" in df.columns:
            labels = [str(v).strip() for v in df["Source"].dropna().unique().tolist() if str(v).strip()]
        if len(labels) == 1:
            stem = self._make_safe_output_name(labels[0], fallback)
            return f"{stem}_M2"
        if len(labels) > 1:
            canonical = {re.split(r"[·|]", value, maxsplit=1)[0].strip().casefold() for value in labels}
            if len(canonical) == 1:
                stem = self._make_safe_output_name(re.split(r"[·|]", labels[0], maxsplit=1)[0].strip(), fallback)
                return f"{stem}_M2"
            return f"session_{len(labels)}_sources_M2"
        return f"{self._make_safe_output_name(fallback, 'm2_identification')}_M2"

    def sync_peak_results_to_species_tab(
        self,
        df: pd.DataFrame,
        *,
        base_name: str | None = None,
        source_description: str | None = None,
    ):
        """
        Envía automáticamente los resultados del módulo de detección
        a la pestaña del buscador de especies mediante un CSV temporal.
        """
        if df is None or df.empty:
            self.log("[INFO] No hay resultados de detección para enviar al buscador.")
            return

        try:
            temp_dir = TEMP_DIR
            temp_dir.mkdir(parents=True, exist_ok=True)

            base_name = (
                str(base_name).strip()
                if base_name
                else Path(self.selected_file).stem if self.selected_file else "deteccion"
            )
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_csv = temp_dir / f"{base_name}_for_species_{timestamp}.csv"

            prepared = df.copy()
            # Preserve the exact observed marker intensity shown in M1.  T_A [K]
            # remains the fitted component amplitude used by the physical methods;
            # T_obs_at_fit is the baseline-corrected observed spectrum at ν_fit.
            # Both are valid but answer different questions, so M2 carries both.
            if "detection_id" in prepared.columns and "T_obs_at_fit [K]" not in prepared.columns:
                observed_by_id = {}
                for _path, _state in (self.spectrum_session or {}).items():
                    _result = (_state or {}).get("last_result") or {}
                    _json = (_state or {}).get("analyzed_plot_json") or _result.get("plot_json")
                    if not _json:
                        continue
                    try:
                        from plotly import io as _pio
                        _fig = _pio.from_json(_json)
                        _trace = next((tr for tr in _fig.data if isinstance(getattr(tr, "meta", None), dict) and str(tr.meta.get("czspec_role") or "") == "detection"), None)
                        if _trace is None:
                            continue
                        _cd = list(_trace.customdata or [])
                        for _y, _row in zip(list(_trace.y or []), _cd):
                            try:
                                _did = str(_row[0]) if isinstance(_row, (list, tuple)) else ""
                                if _did:
                                    observed_by_id[_did] = float(_y)
                            except Exception:
                                pass
                    except Exception:
                        pass
                if observed_by_id:
                    prepared["T_obs_at_fit [K]"] = prepared["detection_id"].astype(str).map(observed_by_id)

            # Direct M1 -> M2 transfers already carry these columns for session
            # data.  Active-spectrum transfers created by legacy states are
            # completed here from the current session metadata.
            if self.selected_file and len(self.selected_files) <= 1:
                state = self.spectrum_session.get(self.selected_file, {})
                meta = dict(self._active_analysis_metadata(state) or {})
                if "source_path" not in prepared.columns:
                    prepared["source_path"] = str(self.selected_file)
                try:
                    vlsr = float(meta.get("vlsr_kms"))
                    if np.isfinite(vlsr) and "source_vlsr_kms" not in prepared.columns:
                        prepared["source_vlsr_kms"] = vlsr
                except Exception:
                    pass
            prepared.to_csv(temp_csv, index=False)

            self.auto_species_csv_path = str(temp_csv)
            self.species_selected_file = str(temp_csv)
            description = source_description or base_name
            self.species_file_label.setText(
                ((f"M1 input: {description} · {len(prepared)} line(s)" if self.ui_language == "en" else
                  f"Entrada M1: {description} · {len(prepared)} línea(s)"))
            )

            if not self.species_output_input.text().strip():
                self.species_output_input.setText(
                    self._suggest_species_output_name(prepared, base_name)
                )

            self.log(f"[OK] Resultados enviados automáticamente al buscador: {temp_csv}")
            self.log_species(
                f"CSV recibido desde M1 ({description}, {len(df)} línea(s)): {temp_csv}"
            )

        except Exception as e:
            self.log(f"[ERROR] No se pudo sincronizar con el buscador de especies: {e}")

    def _parse_species_temperatures(self) -> list[float]:
        raw = self.species_temperatures_input.text().strip()
        if not raw:
            return []

        values = []
        for chunk in raw.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                val = float(chunk)
                if val > 0:
                    values.append(val)
            except ValueError:
                pass

        return values
    
    @staticmethod
    def _capture_table_column_visibility(table_widget: QTableWidget) -> dict[str, bool]:
        visibility = dict(
            getattr(table_widget, "_czspec_visibility_by_name", {}) or {}
        )
        for column in range(table_widget.columnCount()):
            header = table_widget.horizontalHeaderItem(column)
            if header is not None:
                internal_name = _table_header_internal_name(header)
                visibility[internal_name] = not table_widget.isColumnHidden(column)
        table_widget._czspec_visibility_by_name = visibility
        return visibility

    @staticmethod
    def _apply_table_column_visibility(
        table_widget: QTableWidget,
        previous_visibility: dict[str, bool] | None = None,
    ):
        previous_visibility = previous_visibility or {}
        updated_visibility = {}
        for column in range(table_widget.columnCount()):
            header = table_widget.horizontalHeaderItem(column)
            if header is None:
                continue
            column_name = _table_header_internal_name(header)
            is_visible = previous_visibility.get(
                column_name,
                _column_visible_by_default(table_widget, column_name),
            )
            table_widget.setColumnHidden(column, not is_visible)
            updated_visibility[column_name] = bool(is_visible)
        table_widget._czspec_visibility_by_name = updated_visibility

    def _friendly_source_label_for_row(self, row) -> str:
        """Return the human-facing M1 spectrum label for an M2/M3 table row."""
        try:
            getter = row.get
        except Exception:
            getter = lambda key, default=None: default
        raw_source = str(getter("Source", "") or "").strip()
        source_path = str(getter("source_path", "") or "").strip()
        try:
            nu = float(getter("ν_obs_MHz", np.nan))
        except Exception:
            nu = np.nan

        def norm(value):
            try:
                return os.path.normcase(os.path.abspath(str(value))) if str(value).strip() else ""
            except Exception:
                return str(value or "").casefold()

        # Exact path identity first.  This preserves user-renamed/canonical M1 labels.
        if source_path:
            target = norm(source_path)
            for key, state in (self.spectrum_session or {}).items():
                candidates = [key, state.get("analysis_path"), state.get("original_analysis_path")]
                if any(target and norm(c) == target for c in candidates if c):
                    return str(state.get("display_name") or Path(str(key)).name)

        # Technical cache filenames can change between sessions.  Frequency
        # coverage is the stable scientific identity for .30m sub-spectra.
        if np.isfinite(nu):
            matches=[]
            for key, state in (self.spectrum_session or {}).items():
                raw = state.get("raw_result") or {}
                try:
                    freq=np.asarray(raw.get("freq", []), dtype=float)
                    freq=freq[np.isfinite(freq)]
                    if freq.size and float(freq.min())-1e-6 <= nu <= float(freq.max())+1e-6:
                        span=max(float(freq.max()-freq.min()),1e-12)
                        centre=0.5*(float(freq.min())+float(freq.max()))
                        matches.append((span, abs(nu-centre), str(state.get("display_name") or Path(str(key)).name)))
                except Exception:
                    pass
            if matches:
                matches.sort(key=lambda item:(item[0],item[1]))
                return matches[0][2]

        # Last chance: match the technical name/path against current session paths.
        token = raw_source.casefold()
        if token:
            for key, state in (self.spectrum_session or {}).items():
                pool = [str(key), str(state.get("analysis_path") or ""), str(state.get("original_analysis_path") or "")]
                for value in pool:
                    if token in {Path(value).name.casefold(), Path(value).stem.casefold(), value.casefold()}:
                        return str(state.get("display_name") or Path(str(key)).name)
        return raw_source

    def _friendly_source_dataframe(self, df: pd.DataFrame | None) -> pd.DataFrame | None:
        if df is None or df.empty or "Source" not in df.columns:
            return df
        out=df.copy()
        out["Source"]=[self._friendly_source_label_for_row(row) for _,row in out.iterrows()]
        return out

    def populate_table_widget_from_dataframe(self, table_widget: QTableWidget, df):
        previous_visibility = self._capture_table_column_visibility(table_widget)
        table_widget.clear()

        if df is None or df.empty:
            table_widget.setRowCount(0)
            table_widget.setColumnCount(0)
            return

        df_to_show = df.copy()

        table_widget.setColumnCount(len(df_to_show.columns))
        table_widget.setRowCount(len(df_to_show))
        _set_scientific_table_headers(table_widget, df_to_show.columns)

        for row_idx in range(len(df_to_show)):
            for col_idx, col_name in enumerate(df_to_show.columns):
                value = df_to_show.iloc[row_idx, col_idx]
                if str(col_name) == "Source":
                    text = self._friendly_source_label_for_row(df_to_show.iloc[row_idx])
                else:
                    text = "" if pd.isna(value) else str(value)
                item = QTableWidgetItem(text)
                table_widget.setItem(row_idx, col_idx, item)

        table_widget.resizeColumnsToContents()
        self._apply_table_column_visibility(table_widget, previous_visibility)

    def _get_species_filter_fields(self) -> list[str]:
        fields = []

        if self.species_search_obs_id_cb.isChecked():
            fields.append("obs_id")
        if self.species_search_name_cb.isChecked():
            fields.append("name")
        if self.species_search_chemical_name_cb.isChecked():
            fields.append("chemical_name")
        if self.species_search_species_id_cb.isChecked():
            fields.append("species_id")
        if self.species_search_moleculeTag_cb.isChecked():
            fields.append("moleculeTag")

        return fields

    def _filter_species_dataframe(self, df: pd.DataFrame | None) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        if not self.species_filter_active:
            return df.copy()

        search_text = (self.species_filter_text or "").strip()
        fields = self.species_filter_fields or []

        if not search_text or not fields:
            return df.copy()

        terms = self._parse_multi_search_terms(search_text)
        if not terms:
            return df.copy()

        global_mask = pd.Series(False, index=df.index)

        for field in fields:
            if field not in df.columns:
                continue

            field_mask = self._build_multi_term_mask(df, field, terms)
            global_mask = global_mask | field_mask

        return df[global_mask].copy()

    def _get_current_species_topk_view_df(self) -> pd.DataFrame:
        if self.species_topk_df is None or self.species_topk_df.empty:
            return pd.DataFrame()

        return self._filter_species_dataframe(self.species_topk_df)

    def _get_current_species_main_view_df(self) -> pd.DataFrame:
        # Identified rows follow the user's TOP-K checkboxes.  Explicit
        # "no plausible candidate" rows have no TOP-K entry, but must remain
        # visible in the main table so failed identifications are transparent.
        selected = pd.DataFrame()
        if self.species_topk_df is not None and not self.species_topk_df.empty and "selected" in self.species_topk_df.columns:
            selected = self.species_topk_df[self.species_topk_df["selected"] == True].copy()
            selected = selected.drop(columns=["selected", "__source_index__"], errors="ignore")

        unidentified = pd.DataFrame()
        if self.species_last_main_df is not None and not self.species_last_main_df.empty:
            base = self.species_last_main_df.copy()
            if "score_mode" in base.columns:
                unidentified = base[base["score_mode"].fillna("").astype(str).eq("none")].copy()
            elif "chemical_name" in base.columns:
                unidentified = base[base["chemical_name"].fillna("").astype(str).str.contains("sin candidato", case=False, na=False)].copy()
            if not unidentified.empty and not selected.empty and "obs_id" in selected.columns and "obs_id" in unidentified.columns:
                unidentified = unidentified[~unidentified["obs_id"].isin(selected["obs_id"])].copy()

        pieces = [part for part in (selected, unidentified) if part is not None and not part.empty]
        if not pieces:
            return pd.DataFrame()
        main_df = pd.concat(pieces, ignore_index=True, sort=False)
        if "obs_id" in main_df.columns:
            main_df = main_df.sort_values("obs_id", kind="stable").reset_index(drop=True)
        return self._filter_species_dataframe(main_df)

    def apply_species_filter(self):
        search_text = self.species_search_input.text().strip()
        fields = self._get_species_filter_fields()

        if not search_text:
            self.notify_info("Enter a search value." if self.ui_language == "en" else "Escribe un valor para buscar.")
            return

        if not fields:
            self.notify_info("Select at least one search field." if self.ui_language == "en" else "Selecciona al menos un campo de búsqueda.")
            return

        self.species_filter_active = True
        self.species_filter_text = search_text
        self.species_filter_fields = fields

        self.populate_species_topk_table()
        self.refresh_species_main_table_from_selection()

        terms = self._parse_multi_search_terms(search_text)
        self.log_species(
            f"[INFO] Filtro aplicado: {terms} en {', '.join(fields)}"
        )

    def clear_species_filter(self):
        self.species_filter_active = False
        self.species_filter_text = ""
        self.species_filter_fields = []

        self.species_search_input.clear()

        self.populate_species_topk_table()
        self.refresh_species_main_table_from_selection()

        self.log_species("[INFO] Filter cleared." if self.ui_language == "en" else "[INFO] Filtro limpiado.")

    def _get_column_density_filter_fields(self) -> list[str]:
        fields = []

        if self.cd_search_obs_id_cb.isChecked():
            fields.append("obs_id")
        if self.cd_search_name_cb.isChecked():
            fields.append("name")
        if self.cd_search_chemical_name_cb.isChecked():
            fields.append("chemical_name")
        if self.cd_search_species_id_cb.isChecked():
            fields.append("species_id")
        if self.cd_search_moleculeTag_cb.isChecked():
            fields.append("moleculeTag")

        return fields

    def _filter_column_density_dataframe(self, df: pd.DataFrame | None) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        if not self.column_density_filter_active:
            return df.copy()

        search_text = (self.column_density_filter_text or "").strip()
        fields = self.column_density_filter_fields or []

        if not search_text or not fields:
            return df.copy()

        terms = self._parse_multi_search_terms(search_text)
        if not terms:
            return df.copy()

        global_mask = pd.Series(False, index=df.index)

        for field in fields:
            if field not in df.columns:
                continue

            field_mask = self._build_multi_term_mask(df, field, terms)
            global_mask = global_mask | field_mask

        return df[global_mask].copy()

    @staticmethod
    def _copy_table_column_visibility(
        source_table: QTableWidget,
        target_table: QTableWidget,
    ):
        visibility_by_name = {}
        for column in range(source_table.columnCount()):
            header = source_table.horizontalHeaderItem(column)
            if header is not None:
                internal_name = _table_header_internal_name(header)
                visibility_by_name[internal_name] = source_table.isColumnHidden(column)

        for column in range(target_table.columnCount()):
            header = target_table.horizontalHeaderItem(column)
            internal_name = _table_header_internal_name(header)
            if header is not None and internal_name in visibility_by_name:
                target_table.setColumnHidden(
                    column,
                    visibility_by_name[internal_name],
                )

    def _sync_column_density_comparison_visibility(self):
        self._copy_table_column_visibility(
            self.vasyunina_results_table,
            self.vasyunina_comparison_table,
        )
        self._copy_table_column_visibility(
            self.sanhueza_results_table,
            self.sanhueza_comparison_table,
        )

    def _refresh_column_density_comparison_tables(self, vasy_df, sanh_df):
        self.populate_table_widget_from_dataframe(
            self.vasyunina_comparison_table,
            vasy_df,
        )
        self.populate_table_widget_from_dataframe(
            self.sanhueza_comparison_table,
            sanh_df,
        )
        self._sync_column_density_comparison_visibility()

    def refresh_column_density_tables_from_filter(self):
        source_df = self._filter_column_density_dataframe(self.column_density_source_df)
        vasy_df = self._filter_column_density_dataframe(self.column_density_vasyunina_df)
        sanh_df = self._filter_column_density_dataframe(self.column_density_sanhueza_df)

        self.column_density_source_filtered_df = source_df.copy()
        self.column_density_vasyunina_filtered_df = vasy_df.copy()
        self.column_density_sanhueza_filtered_df = sanh_df.copy()

        self.populate_table_widget_from_dataframe(self.column_density_source_table, source_df)
        self.populate_table_widget_from_dataframe(self.vasyunina_results_table, vasy_df)
        self.populate_table_widget_from_dataframe(self.sanhueza_results_table, sanh_df)
        self._refresh_column_density_comparison_tables(vasy_df, sanh_df)

    def apply_column_density_filter(self):
        search_text = self.cd_search_input.text().strip()
        fields = self._get_column_density_filter_fields()

        if not search_text:
            self.notify_info("Escribe un valor para buscar.")
            return

        if not fields:
            self.notify_info("Selecciona al menos un campo de búsqueda.")
            return

        self.column_density_filter_active = True
        self.column_density_filter_text = search_text
        self.column_density_filter_fields = fields

        self.refresh_column_density_tables_from_filter()

        terms = self._parse_multi_search_terms(search_text)
        self.log_column_density(
            f"[INFO] Filtro aplicado: {terms} en {', '.join(fields)}"
        )

    def clear_column_density_filter(self):
        self.column_density_filter_active = False
        self.column_density_filter_text = ""
        self.column_density_filter_fields = []

        self.cd_search_input.clear()

        self.refresh_column_density_tables_from_filter()
        self.log_column_density("[INFO] Filtro de densidad de columna limpiado.")

    def _prepare_species_topk_dataframe(self, df: pd.DataFrame | None) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        out = df.copy()

        if "selected" not in out.columns:
            if "rank" in out.columns:
                rank_num = pd.to_numeric(out["rank"], errors="coerce")
                out["selected"] = rank_num.eq(1)
            else:
                out["selected"] = False
        else:
            out["selected"] = out["selected"].fillna(False).astype(bool)

        out = out.reset_index(drop=True)

        if "__source_index__" not in out.columns:
            out["__source_index__"] = out.index

        cols = list(out.columns)

        if "selected" in cols:
            cols.insert(0, cols.pop(cols.index("selected")))

        if "__source_index__" in cols:
            cols.append(cols.pop(cols.index("__source_index__")))

        out = out[cols]
        return out

    def _style_topk_row(self, row_idx: int, selected: bool):
        bg = QColor("#DBEAFE") if selected else QColor("#FFFFFF")
        fg = QColor("#1D4ED8") if selected else QColor("#111827")
        for col in range(self.species_topk_table.columnCount()):
            item = self.species_topk_table.item(row_idx, col)
            if item is None:
                continue
            item.setBackground(bg)
            item.setForeground(fg)
            font = item.font(); font.setBold(bool(selected)); item.setFont(font)

    def populate_species_topk_table(self):
        df = self._get_current_species_topk_view_df()
        self.species_topk_filtered_df = df.copy()

        self._species_topk_updating = True
        previous_visibility = self._capture_table_column_visibility(self.species_topk_table)
        self.species_topk_table.clear()

        if df is None or df.empty:
            self.species_topk_table.setRowCount(0)
            self.species_topk_table.setColumnCount(0)
            self._species_topk_updating = False
            return

        # Selection is communicated by highlighting the whole row, which saves
        # one column and makes browsing candidates faster and visually clearer.
        columns = [c for c in df.columns if c not in {"__source_index__", "selected"}]
        self.species_topk_table.setColumnCount(len(columns))
        self.species_topk_table.setRowCount(len(df))
        _set_scientific_table_headers(self.species_topk_table, columns)

        for row_idx in range(len(df)):
            source_index_value = df.iloc[row_idx]["__source_index__"] if "__source_index__" in df.columns else df.index[row_idx]
            for col_idx, col_name in enumerate(columns):
                value = df.iloc[row_idx][col_name]
                if str(col_name) == "Source":
                    text = self._friendly_source_label_for_row(df.iloc[row_idx])
                else:
                    text = "" if pd.isna(value) else str(value)
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                item.setData(Qt.UserRole, source_index_value)
                self.species_topk_table.setItem(row_idx, col_idx, item)
            self._style_topk_row(row_idx, bool(df.iloc[row_idx].get("selected", False)))

        self.species_topk_table.resizeColumnsToContents()
        self._apply_table_column_visibility(self.species_topk_table, previous_visibility)
        self._species_topk_updating = False

    def refresh_species_main_table_from_selection(self):
        main_df = self._get_current_species_main_view_df()
        self.species_main_filtered_df = main_df.copy()

        if main_df is None or main_df.empty:
            self.populate_table_widget_from_dataframe(self.species_table, None)
            return

        self.populate_table_widget_from_dataframe(self.species_table, main_df)

    def get_species_selected_dataframe(self) -> pd.DataFrame:
        """
        Devuelve la salida actual del buscador de especies.
        Esta será la entrada común para las ramas 3.1 y 3.2.
        """
        if self.species_topk_df is None or self.species_topk_df.empty:
            return pd.DataFrame()

        if "selected" not in self.species_topk_df.columns:
            return pd.DataFrame()

        out = self.species_topk_df[self.species_topk_df["selected"] == True].copy()

        if "selected" in out.columns:
            out = out.drop(columns=["selected"])

        out = out.reset_index(drop=True)

        if "__source_index__" not in out.columns:
            out["__source_index__"] = out.index

        cols = list(out.columns)
        if "__source_index__" in cols:
            cols.append(cols.pop(cols.index("__source_index__")))
            out = out[cols]

        return out
    
    def refresh_column_density_source_preview(self):
        en = self.ui_language == "en"
        df = self.get_species_selected_dataframe()
        df = self._friendly_source_dataframe(df)
        self.column_density_source_df = df.copy() if df is not None else pd.DataFrame()

        if df is None or df.empty:
            self.column_density_source_label.setText("No data available from molecular identification" if en else "Sin datos disponibles desde M2")
            self.populate_table_widget_from_dataframe(self.column_density_source_table, None)
            self.vasyunina_run_button.setEnabled(False)
            self.sanhueza_run_button.setEnabled(False)
            self.save_vasyunina_button.setEnabled(False)
            self.save_sanhueza_button.setEnabled(False)
            if hasattr(self, "column_density_final_spectrum_button"):
                self.column_density_final_spectrum_button.setEnabled(False)
            self.log_column_density("[INFO] No hay selección disponible desde M2.")
            return

        source_count = 0
        if "Source" in df.columns:
            source_count = int(df["Source"].dropna().astype(str).nunique())
        source_suffix = (
            (f" · {source_count} source file(s)" if en else f" · {source_count} archivo(s) fuente") if source_count else ""
        )
        self.column_density_source_label.setText(
            (f"{len(df)} row(s) received from molecular identification{source_suffix}." if en else
             f"Se recibieron {len(df)} fila(s) desde M2{source_suffix}.")
        )
        self.refresh_column_density_tables_from_filter()
        self.column_density_tables_tabs.setCurrentWidget(
            self.column_density_source_table_box
        )

        self.vasyunina_run_button.setEnabled(True)
        self.sanhueza_run_button.setEnabled(True)
        if hasattr(self, "column_density_final_spectrum_button"):
            self.column_density_final_spectrum_button.setEnabled(bool(self.species_last_main_df is not None and not self.species_last_main_df.empty))
        self._apply_m3_metadata_temperatures()

        self.log_column_density(
            (f"[OK] Input refreshed from molecular identification: {len(df)} row(s){source_suffix}." if en else
             f"[OK] Entrada actualizada desde M2: {len(df)} fila(s){source_suffix}.")
        )

    def _suggest_m3_temperatures_from_metadata(self) -> list[float]:
        """Return source Tex values without equating Tex with Tkin/Trot."""
        values=[]
        for file_path in list(getattr(self, "selected_files", []) or []):
            state=(self.spectrum_session or {}).get(file_path,{})
            meta=dict(self._active_analysis_metadata(state) or {})
            for value in list(meta.get("excitation_temperatures_k") or []):
                try:
                    val=float(value)
                    if np.isfinite(val) and val>0: values.append(val)
                except Exception:
                    pass
        # Q(T) sampling temperatures from M2 are not automatically treated as
        # excitation temperatures.  M3 only auto-fills Tex explicitly stored
        # in M1 source metadata/registry.
        return sorted(set(values))

    def _apply_m3_metadata_temperatures(self):
        if getattr(self, "_m3_temperature_user_edited", False):
            return
        values=self._suggest_m3_temperatures_from_metadata()
        if not values:
            self.vasyunina_temperatures_input.clear()
            self.sanhueza_tex_input.clear()
            self.vasyunina_temperatures_input.setPlaceholderText("")
            self.sanhueza_tex_input.setPlaceholderText("")
            return
        text=", ".join(f"{v:g}" for v in values)
        # M3 is explicitly receiving an M1→M2 chain, so source Tex metadata are
        # loaded into the editable fields rather than shown as a fake default.
        self.vasyunina_temperatures_input.setText(text)
        self.sanhueza_tex_input.setText(text)
        self.vasyunina_temperatures_input.setPlaceholderText("")
        self.sanhueza_tex_input.setPlaceholderText("")

    def _parse_vasyunina_temperatures(self) -> list[float]:
        raw = self.vasyunina_temperatures_input.text().strip()
        if not raw:
            return []

        values = []
        for chunk in raw.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                val = float(chunk)
                if val > 0:
                    values.append(val)
            except ValueError:
                pass

        return values
    
    def _parse_sanhueza_temperatures(self) -> list[float]:
        raw = self.sanhueza_tex_input.text().strip()
        if not raw:
            return []

        values = []
        for chunk in raw.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                val = float(chunk)
                if val > 0:
                    values.append(val)
            except ValueError:
                pass

        return values
    
    def _format_sanhueza_isotopic_ratios_summary(self) -> str:
        ratios = getattr(self, "sanhueza_isotopic_ratios", {})
        order = ["13C", "15N", "18O", "17O", "34S", "33S"]

        parts = []
        for key in order:
            if key in ratios:
                parts.append(f"{key}={ratios[key]:g}")

        if parts:
            return " | ".join(parts)
        return "No ratios configured." if self.ui_language == "en" else "Sin razones configuradas."


    def open_sanhueza_isotopic_ratios_dialog(self):
        dialog = IsotopicRatiosDialog(
            current_ratios=self.sanhueza_isotopic_ratios,
            language=self.ui_language,
            parent=self,
        )

        if dialog.exec():
            self.sanhueza_isotopic_ratios = dialog.get_ratios()

            if hasattr(self, "sanhueza_ratios_summary_label"):
                self.sanhueza_ratios_summary_label.setText(
                    self._format_sanhueza_isotopic_ratios_summary()
                )

            self.log_column_density(
                f"[MTH] Razones isotópicas actualizadas en sesión: "
                f"{self.sanhueza_isotopic_ratios}"
            )
    
    def run_vasyunina_process(self):
        en = self.ui_language == "en"
        if self.column_density_manual_df is not None and not self.column_density_manual_df.empty:
            df_input = self.column_density_manual_df.copy()
        else:
            df_input = self.get_species_selected_dataframe()

        if df_input is None or df_input.empty:
            QMessageBox.warning(
                self,
                "Notice" if en else "Aviso",
                "No molecular-identification data are available to run MOD." if en else "No hay datos desde el buscador de especies para ejecutar MOD."
            )
            self.log_column_density("[ERROR] No hay datos de entrada para MOD.")
            return

        tex_list = self._parse_vasyunina_temperatures()
        if not tex_list:
            QMessageBox.warning(self, "OTM" if en else "MOD",
                                "Enter at least one excitation temperature." if en else "Ingresa al menos una temperatura de excitación.")
            return
        output_name = "column_density_mod"
        if self.species_output_input.text().strip():
            output_name = f"{self.species_output_input.text().strip()}_mod"

        self.log_column_density("[INFO] Iniciando método ópticamente delgado (MOD)...")
        self.log_column_density(f"[INFO] Filas de entrada: {len(df_input)}")
        self.log_column_density(f"[INFO] Temperaturas: {tex_list}")

        def work(progress):
            return run_vasyunina_from_dataframe(
                df_input=df_input,
                tex_list=tex_list,
                output_name=output_name,
                ndigits=4,
                save_outputs=False,
                progress_callback=progress,
            )

        def on_success(result):
            for line in result.logs:
                self.log_column_density(line)

            if not result.success:
                QMessageBox.critical(self, "MOD error" if en else "Error en MOD", result.message)
                return

            self.column_density_vasyunina_df = self._friendly_source_dataframe(result.dataframe)
            self.refresh_column_density_tables_from_filter()
            self.refresh_lte_inputs()
            self._refresh_advanced_modules()
            target_tab = (
                self.column_density_comparison_box
                if self.column_density_sanhueza_df is not None
                and not self.column_density_sanhueza_df.empty
                else self.vasyunina_results_box
            )
            self.column_density_tables_tabs.setCurrentWidget(target_tab)
            self.save_vasyunina_button.setEnabled(True)
            self.log_column_density("[OK] Resultados MOD cargados en la tabla.")
            self.notify_success(
                "MOD column-density calculation finished successfully; results are available in the table." if en else
                "El cálculo de densidad de columna mediante MOD terminó correctamente. Los resultados ya están disponibles en la tabla."
            )

        def on_error(message, details):
            self.log_column_density(f"[ERROR] MOD: {message}")
            self.log_column_density(details)
            QMessageBox.critical(self, "MOD error" if en else "Error en MOD", message)

        self._start_background_task(
            "column_density_mod",
            work,
            on_success,
            on_error=on_error,
            busy_widgets=(self.vasyunina_run_button,),
            status_message=("Calculating column density with MOD..." if en else "Calculando densidad de columna mediante MOD..."),
        )

    
    def run_sanhueza_process(self):
        en = self.ui_language == "en"
        if self.column_density_manual_df is not None and not self.column_density_manual_df.empty:
            df_input = self.column_density_manual_df.copy()
        else:
            df_input = self.get_species_selected_dataframe()

        if df_input is None or df_input.empty:
            QMessageBox.warning(self, "Notice" if en else "Aviso", "No selected data are available to run MTH." if en else "No hay datos seleccionados para ejecutar MTH.")
            self.log_column_density("[ERROR] No hay datos de entrada para MTH.")
            return

        Tex_values = self._parse_sanhueza_temperatures()
        if not Tex_values:
            QMessageBox.warning(
                self, "HTM" if en else "MTH",
                "Enter at least one excitation temperature." if en else "Ingresa al menos una temperatura de excitación."
            )
            return
        tau_max = None
        tau_text = self.sanhueza_tau_max_input.text().strip()
        if tau_text:
            try:
                tau_max = float(tau_text)
            except ValueError:
                QMessageBox.warning(
                    self,
                    "MTH",
                    "Maximum τ must be numeric." if en else "El valor de τ máximo debe ser numérico."
                )
                return

        use_r_fixed = self.sanhueza_r_mode_checkbox.isChecked()
        isotopic_ratios = dict(self.sanhueza_isotopic_ratios)
        output_name = "column_density_mth"
        if self.species_output_input.text().strip():
            output_name = f"{self.species_output_input.text().strip()}_mth"

        self.column_density_log_area.clear()
        self._column_density_log_history = []
        self.log_column_density("[INFO] Iniciando método de transiciones hiperfinas (MTH)...")
        self.log_column_density(f"[INFO] Filas de entrada: {len(df_input)}")
        self.log_column_density(f"[INFO] Tex: {Tex_values}")
        self.log_column_density(f"[INFO] Razones isotópicas de sesión: {isotopic_ratios}")
        self.log_column_density(f"[INFO] tau_max: {tau_max}")
        self.log_column_density(f"[INFO] Aproximación de r: {use_r_fixed}")

        def work(progress):
            return run_sanhueza_from_dataframe(
                df_input,
                Tex_values=Tex_values,
                iso_ratio=50.0,  # respaldo técnico; ya no viene de la GUI
                tau_max=tau_max,
                use_r_fixed=use_r_fixed,
                output_name=output_name,
                save_outputs=False,
                isotopic_ratios=isotopic_ratios,
                progress_callback=progress,
            )

        def on_success(result):
            for log in result.logs:
                self.log_column_density(log)

            if not result.success:
                QMessageBox.warning(self, "MTH", result.message)
                return

            self.column_density_sanhueza_df = self._friendly_source_dataframe(result.dataframe)
            self.refresh_column_density_tables_from_filter()
            self.refresh_lte_inputs()
            self._refresh_advanced_modules()
            target_tab = (
                self.column_density_comparison_box
                if self.column_density_vasyunina_df is not None
                and not self.column_density_vasyunina_df.empty
                else self.sanhueza_results_box
            )
            self.column_density_tables_tabs.setCurrentWidget(target_tab)
            self.save_sanhueza_button.setEnabled(True)
            self.log_column_density("[OK] MTH terminado correctamente.")
            self.notify_success(
                "MTH column-density calculation finished successfully; results are available in the table." if en else
                "El cálculo de densidad de columna mediante MTH terminó correctamente. Los resultados ya están disponibles en la tabla."
            )

        def on_error(message, details):
            self.log_column_density(f"[ERROR] MTH: {message}")
            self.log_column_density(details)
            QMessageBox.critical(self, "MTH error" if en else "Error en MTH", message)

        self._start_background_task(
            "column_density_mth",
            work,
            on_success,
            on_error=on_error,
            busy_widgets=(self.sanhueza_run_button,),
            status_message=("Calculating column density with MTH..." if en else "Calculando densidad de columna mediante MTH..."),
        )

    def _style_topk_selection_item(self, item: QTableWidgetItem, selected: bool):
        en = self.ui_language == "en"
        item.setText(("Selected" if en else "Seleccionado") if selected else ("Select" if en else "Seleccionar"))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if selected:
            item.setBackground(QColor("#DBEAFE"))
            item.setForeground(QColor("#1D4ED8"))
            font = item.font(); font.setBold(True); item.setFont(font)
        else:
            item.setBackground(QColor("#FFFFFF"))
            item.setForeground(QColor("#111827"))
            font = item.font(); font.setBold(False); item.setFont(font)

    def _refresh_species_selection_dependents(self):
        """Refresh modules downstream of M2 after the UI has had time to repaint."""
        try:
            self.refresh_column_density_source_preview()
            self.refresh_lte_inputs()
        except Exception as exc:
            self.log_species(
                (f"[WARN] Delayed downstream refresh failed: {exc}" if self.ui_language == "en" else
                 f"[WARN] Falló la actualización diferida de módulos posteriores: {exc}")
            )

    def on_species_topk_cell_clicked(self, row: int, column: int):
        if self._species_topk_updating:
            return
        item = self.species_topk_table.item(row, column)
        if item is None or self.species_topk_df is None or self.species_topk_df.empty:
            return
        source_index = item.data(Qt.UserRole)
        if source_index is None or "__source_index__" not in self.species_topk_df.columns:
            return
        source_mask = self.species_topk_df["__source_index__"] == source_index
        if not source_mask.any():
            return
        master_row = self.species_topk_df[source_mask].iloc[0]
        obs_id = master_row["obs_id"]
        same_obs_mask = self.species_topk_df["obs_id"] == obs_id
        self.species_topk_df.loc[same_obs_mask, "selected"] = False
        self.species_topk_df.loc[source_mask, "selected"] = True

        # Repaint only the rows belonging to this observed line; the selected
        # candidate is the blue row itself, so no dedicated Selection column is
        # needed and candidate switching remains lightweight.
        self._species_topk_updating = True
        try:
            for r in range(self.species_topk_table.rowCount()):
                first = self.species_topk_table.item(r, 0)
                if first is None:
                    continue
                src = first.data(Qt.UserRole)
                matches = self.species_topk_df["__source_index__"] == src
                if not matches.any():
                    continue
                candidate = self.species_topk_df[matches].iloc[0]
                try:
                    same_obs = float(candidate.get("obs_id")) == float(obs_id)
                except Exception:
                    same_obs = str(candidate.get("obs_id")) == str(obs_id)
                if same_obs:
                    self._style_topk_row(r, bool(candidate.get("selected", False)))
            self.refresh_species_main_table_from_selection()
        finally:
            self._species_topk_updating = False

        if hasattr(self, "_species_selection_refresh_timer"):
            self._species_selection_refresh_timer.start()
        self.log_species(
            (f"[INFO] Selection updated for obs_id={obs_id}." if self.ui_language == "en" else
             f"[INFO] Selección actualizada para obs_id={obs_id}.")
        )

    def _species_spectrum_mode_changed(self):
        if not hasattr(self, "species_spectrum_mode_combo"):
            return
        en = self.ui_language == "en"
        mode = str(self.species_spectrum_mode_combo.currentData() or "active")
        external = mode == "external"
        self.species_load_spectrum_button.setEnabled(external)
        if external:
            count = len(getattr(self, "species_external_spectrum_files", []) or [])
            self.species_spectrum_file_label.setText(
                (f"External spectra: {count} selected" if en else f"Espectros externos: {count} seleccionado(s)")
                if count else
                ("No external spectrum selected" if en else "Sin espectro externo seleccionado")
            )
        elif mode == "session":
            count = len(self.selected_files or [])
            self.species_spectrum_file_label.setText(
                f"M1 session: {count} spectrum/spectra" if en else f"Sesión M1: {count} espectro(s)"
            )
        else:
            label = self._spectrum_display_name(self.selected_file) if self.selected_file else None
            self.species_spectrum_file_label.setText(
                (f"Active M1 spectrum: {label}" if en else f"Espectro M1 activo: {label}")
                if label else ("No active M1 spectrum" if en else "Sin espectro M1 activo")
            )

    def load_species_spectrum_files(self):
        en = self.ui_language == "en"
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select spectra for M2" if en else "Seleccionar espectros para M2",
            "",
            ("Spectra (*.dat *.txt *.csv *.fits *.fit *.fts);;All files (*)" if en else
             "Espectros (*.dat *.txt *.csv *.fits *.fit *.fts);;Todos los archivos (*)"),
        )
        if not paths:
            return
        self.species_external_spectrum_files = [str(Path(path)) for path in paths]
        index = self.species_spectrum_mode_combo.findData("external")
        if index >= 0:
            self.species_spectrum_mode_combo.setCurrentIndex(index)
        self._species_spectrum_mode_changed()
        self.log_species(
            f"[OK] {len(paths)} external spectrum/spectra selected for M2." if en else
            f"[OK] {len(paths)} espectro(s) externo(s) seleccionado(s) para M2."
        )

    def open_species_search_filters(self):
        dialog = SpeciesSearchFilterDialog(
            getattr(self, "species_search_policy", None),
            language=self.ui_language,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.species_search_policy = dialog.configuration()
        self.settings.setValue(
            "m2/search_policy",
            json.dumps(self.species_search_policy, ensure_ascii=False),
        )
        profile = self.species_search_policy.get("profile", "star_forming")
        self.log_species(
            f"[INFO] Identification filters updated. Profile: {profile}." if self.ui_language == "en" else
            f"[INFO] Filtros de identificación actualizados. Perfil: {profile}."
        )
        self.notify_success(
            "M2 identification filters updated." if self.ui_language == "en" else
            "Filtros de identificación de M2 actualizados."
        )

    def _species_run_directory(self) -> Path | None:
        if not self.species_last_result:
            return None
        raw = str(self.species_last_result.extra.get("run_dir") or "").strip()
        return Path(raw) if raw else None

    def _species_current_main_for_products(self) -> pd.DataFrame:
        current = self._get_current_species_main_view_df()
        if current is None or current.empty:
            return pd.DataFrame()
        out = current.copy()
        if "score_mode" in out.columns:
            out = out[~out["score_mode"].fillna("").astype(str).eq("none")].copy()
        if "orderedfreq" in out.columns:
            out = out[pd.to_numeric(out["orderedfreq"], errors="coerce").notna()].copy()
        return out.reset_index(drop=True)

    def generate_species_qt_products(self, export_after: bool = False):
        en = self.ui_language == "en"
        rows = self._species_current_main_for_products()
        if rows.empty:
            self.notify_info("Run molecular identification first." if en else "Primero ejecuta la identificación molecular.")
            return
        temperatures = list(self.species_last_target_temperatures or self._parse_species_temperatures())
        self.log_species("[INFO] Building Q(T) products..." if en else "[INFO] Construyendo productos Q(T)...")

        def work(progress):
            from plotly import graph_objects as go
            from czspec.logic.species_search import (
                parse_cdms_catalog_for_logic, build_cdms_logq_dict,
                load_jpl_points_table, get_partition_values_for_row,
                build_qt_unique_key, build_qt_species_label, qcol_name,
                CDMS_PATH, JPL_TABLE_PATH,
            )
            progress(5, "Loading partition catalogs" if en else "Cargando catálogos de partición")
            cdms_logq = build_cdms_logq_dict(parse_cdms_catalog_for_logic(CDMS_PATH))
            jpl_points = load_jpl_points_table(JPL_TABLE_PATH)
            products = {}
            seen = set()
            total = max(1, len(rows))
            for pos, (_, row) in enumerate(rows.iterrows(), start=1):
                key = build_qt_unique_key(row)
                if key in seen:
                    continue
                seen.add(key)
                q_values, q_source, temp_grid, q_grid = get_partition_values_for_row(
                    row, cdms_logq, jpl_points, temperatures
                )
                if q_source == "NONE" or not temp_grid or not q_grid:
                    continue
                temp = np.asarray(temp_grid, dtype=float)
                q = np.asarray(q_grid, dtype=float)
                mask = np.isfinite(temp) & np.isfinite(q) & (temp > 0) & (q > 0)
                if not mask.any():
                    continue
                order = np.argsort(temp[mask])
                temp = temp[mask][order]; q = q[mask][order]
                label = build_qt_species_label(row)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=temp, y=q, mode="lines+markers", name=q_source))
                target_x, target_y, target_text = [], [], []
                for t in temperatures:
                    value = q_values.get(qcol_name(t), np.nan)
                    try: value = float(value)
                    except Exception: value = np.nan
                    if np.isfinite(value) and value > 0:
                        target_x.append(float(t)); target_y.append(value); target_text.append(f"Q({t:g} K)={value:.6g}")
                if target_x:
                    fig.add_trace(go.Scatter(
                        x=target_x, y=target_y, mode="markers+text", text=target_text,
                        textposition="top center", name="Q(T) target" if en else "Q(T) objetivo",
                    ))
                fig.update_layout(
                    title=f"Q(T) — {label}",
                    xaxis_title="Temperature [K]" if en else "Temperatura [K]",
                    yaxis_title="Q(T)", template="plotly_white", hovermode="closest",
                )
                products[label] = fig.to_json()
                progress(min(95, 5 + int(90 * pos / total)), f"Q(T): {label}")
            return products

        def on_success(products):
            self.species_qt_products = dict(products or {})
            count = len(self.species_qt_products)
            self.species_export_qt_button.setEnabled(bool(count))
            self.species_open_qt_button.setEnabled(True)
            self.log_species(f"[OK] Q(T) products built: {count}." if en else f"[OK] Productos Q(T) construidos: {count}.")
            if export_after and count:
                QTimer.singleShot(0, self.export_species_qt_products)
            elif count:
                self.notify_success(f"{count} Q(T) product(s) ready." if en else f"{count} producto(s) Q(T) listos.")
            else:
                self.notify_info("No valid Q(T) products could be built." if en else "No se pudieron construir productos Q(T) válidos.")

        def on_error(message, details):
            self.log_species(f"[ERROR] Q(T): {message}"); self.log_species(details)
            QMessageBox.critical(self, "Q(T)", message)

        self._start_background_task(
            "species_qt_products", work, on_success, on_error=on_error,
            busy_widgets=(self.species_export_qt_button,),
            status_message="Building Q(T)..." if en else "Generando Q(T)...",
        )

    def _species_spectrum_entries(self) -> list[dict]:
        """Describe spectra selected for the M2 final-spectrum product."""
        mode = str(self.species_spectrum_mode_combo.currentData() or "active")
        entries = []
        if mode == "external":
            for path in getattr(self, "species_external_spectrum_files", []) or []:
                entries.append({"path": str(path), "name": Path(path).name, "external": True})
            return entries
        paths = list(self.selected_files or []) if mode == "session" else ([self.selected_file] if self.selected_file else [])
        for path in paths:
            state = self.spectrum_session.get(path, {})
            result = state.get("last_result") or {}
            plot_json = state.get("analyzed_plot_json") or result.get("plot_json") or state.get("raw_plot_json")
            if not plot_json:
                continue
            meta = dict(state.get("source_metadata") or {})
            entries.append({
                "path": str(path),
                "name": str(state.get("display_name") or Path(path).name),
                "plot_json": plot_json,
                "source_metadata": meta,
                "external": False,
            })
        return entries

    @staticmethod
    def _species_rows_for_spectrum(rows: pd.DataFrame, entry: dict) -> pd.DataFrame:
        """Return M2 identifications that actually fall inside one plotted spectrum.

        Frequency coverage is the primary invariant.  This is essential for CLASS
        ``.30m`` sessions where many averaged spectra can originate from the same
        physical file/path and therefore cannot be disambiguated reliably by path
        alone.  Source/path metadata is used only as a preference *after* the
        frequency window has selected the scientifically compatible rows.
        """
        if rows is None or rows.empty:
            return pd.DataFrame()

        work = rows.copy()
        plot_json = entry.get("plot_json")

        # 1) First constrain by the real frequency coverage of this exact plotted
        # spectrum.  This prevents a shared .30m source path from binding rows from
        # another internal spectrum/scan to the selected Final Spectrum.
        frequency_matched = pd.DataFrame()
        if plot_json and "ν_obs_MHz" in work.columns:
            try:
                fig = json.loads(plot_json) if isinstance(plot_json, str) else deepcopy(plot_json)
                xs = []
                for tr in fig.get("data", []) or []:
                    values = tr.get("x")
                    if values is None:
                        continue
                    arr = pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(dtype=float)
                    arr = arr[np.isfinite(arr)]
                    if arr.size:
                        xs.append(arr)
                if xs:
                    xmin = min(float(np.min(a)) for a in xs)
                    xmax = max(float(np.max(a)) for a in xs)
                    span = max(xmax - xmin, 1e-9)
                    # A tiny numerical tolerance only; do not pull neighbouring
                    # spectral windows into this plot.
                    tol = max(1e-6, 0.001 * span)
                    nu = pd.to_numeric(work["ν_obs_MHz"], errors="coerce")
                    frequency_matched = work[nu.between(xmin - tol, xmax + tol, inclusive="both")].copy()
            except Exception:
                frequency_matched = pd.DataFrame()

        candidates = frequency_matched if not frequency_matched.empty else work

        # 2) Within the compatible frequency window, prefer exact source identity
        # when it is available.  Never let stale/portable path metadata erase an
        # otherwise unambiguous frequency match.
        path = str(entry.get("path") or "")
        norm_path = os.path.normcase(os.path.abspath(path)) if path else ""
        if "source_path" in candidates.columns and path:
            source_paths = candidates["source_path"].fillna("").astype(str)
            matched = candidates[source_paths.eq(path)]
            if matched.empty:
                normalized = source_paths.map(
                    lambda p: os.path.normcase(os.path.abspath(p)) if str(p).strip() else ""
                )
                matched = candidates[normalized.eq(norm_path)]
            if not matched.empty:
                return matched.copy()

        if "Source" in candidates.columns:
            meta = dict(entry.get("source_metadata") or {})
            tokens = {
                str(entry.get("name") or "").casefold(),
                Path(path).name.casefold() if path else "",
                Path(path).stem.casefold() if path else "",
                str(meta.get("canonical_name") or "").casefold(),
                str(meta.get("raw_source_name") or "").casefold(),
                str(meta.get("source") or "").casefold(),
            }
            tokens.discard("")
            source = candidates["Source"].fillna("").astype(str)
            mask = pd.Series(False, index=candidates.index)
            for token in tokens:
                # Avoid overly broad one/two-character aliases.
                if len(token) >= 3:
                    mask = mask | source.str.casefold().str.contains(re.escape(token), na=False)
            matched = candidates[mask]
            if not matched.empty:
                return matched.copy()

        # If frequency coverage already isolated rows, that match is stronger than
        # potentially stale file/source strings and is therefore the safe fallback.
        if not frequency_matched.empty:
            return frequency_matched.copy()

        return pd.DataFrame(columns=rows.columns)

    def _build_identified_species_plot(self, base_plot_json: str, rows: pd.DataFrame, title: str) -> str:
        from plotly import io as pio
        from plotly import graph_objects as go
        fig = pio.from_json(base_plot_json)
        label_field = str(self.species_spectrum_label_mode_combo.currentData() or "name")
        en = self.ui_language == "en"

        x_arrays, y_arrays = [], []
        for trace in fig.data:
            try:
                x = np.asarray(trace.x, dtype=float); y = np.asarray(trace.y, dtype=float)
            except Exception:
                continue
            mask = np.isfinite(x) & np.isfinite(y)
            if mask.any():
                x_arrays.append(x[mask]); y_arrays.append(y[mask])
        if not x_arrays:
            return fig.to_json()
        xmin = min(float(np.min(x)) for x in x_arrays); xmax = max(float(np.max(x)) for x in x_arrays)
        span = max(xmax - xmin, 1e-9); padding = span * 0.002

        obs_x, obs_y, labels, hover = [], [], [], []
        expected_x, expected_y, expected_hover = [], [], []

        def nearest_y(freq):
            best = None
            for x, y in zip(x_arrays, y_arrays):
                idx = int(np.argmin(np.abs(x - freq)))
                dist = abs(float(x[idx]) - freq)
                if best is None or dist < best[0]:
                    best = (dist, float(y[idx]))
            return best[1] if best else 0.0

        for _, row in rows.iterrows():
            try: obs = float(row.get("ν_obs_MHz", np.nan))
            except Exception: obs = np.nan
            if not np.isfinite(obs) or obs < xmin-padding or obs > xmax+padding:
                continue
            label = str(row.get(label_field, "") or "").strip()
            if not label:
                label = str(row.get("name", "") or row.get("chemical_name", "") or "").strip()
            if not label:
                continue
            y = nearest_y(obs)
            try: rest = float(row.get("orderedfreq", np.nan))
            except Exception: rest = np.nan
            try: vline = float(row.get("v_line_radio_kms", np.nan))
            except Exception: vline = np.nan
            try: vlsr = float(row.get("source_vlsr_kms", np.nan))
            except Exception: vlsr = np.nan
            try: dv = float(row.get("delta_v_lsr_kms", np.nan))
            except Exception: dv = np.nan
            try: expected = float(row.get("nu_expected_vlsr_mhz", np.nan))
            except Exception: expected = np.nan
            obs_id = row.get("obs_id", "")
            obs_x.append(obs); obs_y.append(y); labels.append(label)
            hover.append(
                f"ID: {obs_id}<br>{'Species' if en else 'Especie'}: {label}<br>"
                f"νobs: {obs:.6f} MHz<br>νrest: {rest:.6f} MHz" if np.isfinite(rest) else
                f"ID: {obs_id}<br>{'Species' if en else 'Especie'}: {label}<br>νobs: {obs:.6f} MHz"
            )
            if hover:
                extra = ""
                if np.isfinite(vline): extra += f"<br>vline: {vline:.3f} km/s"
                if np.isfinite(vlsr): extra += f"<br>VLSR: {vlsr:.3f} km/s"
                if np.isfinite(dv): extra += f"<br>ΔvLSR: {dv:+.3f} km/s"
                hover[-1] += extra
            if np.isfinite(expected) and xmin-padding <= expected <= xmax+padding:
                expected_x.append(expected); expected_y.append(y)
                expected_hover.append(
                    f"{'Expected at source VLSR' if en else 'Esperada al VLSR de la fuente'}<br>ν={expected:.6f} MHz"
                    + (f"<br>VLSR={vlsr:.3f} km/s" if np.isfinite(vlsr) else "")
                )

        if expected_x:
            fig.add_trace(go.Scatter(
                x=expected_x, y=expected_y, mode="markers", name="ν(VLSR)",
                marker=dict(symbol="x", size=9), text=expected_hover, hovertemplate="%{text}<extra></extra>",
            ))
        if obs_x:
            fig.add_trace(go.Scatter(
                x=obs_x, y=obs_y, mode="markers+text", name="Identified lines" if en else "Líneas identificadas",
                text=labels, textposition="top center", marker=dict(symbol="diamond", size=8),
                customdata=hover, hovertemplate="%{customdata}<extra></extra>",
            ))
        fig.update_layout(
            title=(f"Final identified spectrum — {title}" if en else f"Espectro final identificado — {title}"),
            template="plotly_white", hovermode="closest",
        )
        return fig.to_json()

    def _prepare_species_final_sources(self, force: bool = False) -> dict:
        """Cache base spectra once; switching labels/styles never reparses files."""
        if not force and getattr(self, "_species_final_sources_cache", None):
            return self._species_final_sources_cache
        rows = self._species_current_main_for_products()
        entries = self._species_spectrum_entries()
        cache = {}
        for entry in entries:
            plot_json = entry.get("plot_json")
            if entry.get("external") and not plot_json:
                raw = load_raw_spectrum(
                    entry["path"], plot_styles=deepcopy(self.m2_plot_styles),
                    display_name=entry.get("name"), language=self.ui_language,
                )
                plot_json = raw.get("plot_json")
                entry = dict(entry); entry["plot_json"] = plot_json
            if not plot_json:
                continue
            subset = self._species_rows_for_spectrum(rows, entry)
            if subset.empty:
                self.log_species(
                    (("[WARN] Source/path association was empty; Final Spectrum will use a frequency-window fallback for " if self.ui_language == "en" else
                      "[WARN] La asociación por origen/ruta quedó vacía; Final Spectrum usará respaldo por ventana de frecuencia para ")
                     + str(entry.get("name") or Path(entry.get("path") or "spectrum").name))
                )
                # The renderer applies the exact plotted frequency window again.
                # Passing the full M2 result here is safer than returning zero
                # labels when portable .30m source/path metadata is ambiguous.
                subset = rows.copy()
            cache[str(entry.get("name") or Path(entry.get("path") or "spectrum").name)] = {
                "plot_json": plot_json, "rows": subset, "entry": entry,
            }
        self._species_final_sources_cache = cache
        return cache

    def _species_final_figure_provider(self, source_name: str, label_mode: str) -> str | None:
        cache = self._prepare_species_final_sources()
        payload = cache.get(source_name)
        if not payload:
            return None
        label_mode = label_mode if label_mode in {"name", "chemical_name", "none"} else "name"
        self.species_final_label_mode = label_mode
        state = {"source_metadata": dict((payload.get("entry") or {}).get("source_metadata") or {})}
        configured_base = self._configure_m1_plot_json(
            payload["plot_json"], state=state, axis_config_override=self.m2_axis_config
        )
        return self._build_identified_species_plot_with_field(
            configured_base, payload["rows"], source_name, label_mode,
            source_metadata=state["source_metadata"],
        )

    def open_species_plot_style_dialog(self):
        meta = {}
        try:
            entries = self._species_spectrum_entries()
            if entries:
                meta = dict(entries[0].get("source_metadata") or {})
        except Exception:
            pass
        dialog = SpeciesPlotStyleDialog(
            self.m2_plot_styles, axis_config=self.m2_axis_config,
            vlsr_style=self.m2_vlsr_style, language=self.ui_language,
            native_intensity_unit=meta.get("bunit") or meta.get("intensity_unit"), parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.m2_plot_styles = deepcopy(dialog.styles)
        self.m2_axis_config = deepcopy(dialog.axis_configuration())
        self.m2_vlsr_style = deepcopy(dialog.vlsr_style())
        self.settings.setValue("m2/plot_styles", json.dumps(self.m2_plot_styles, ensure_ascii=False))
        self.settings.setValue("m2/axis_config", json.dumps(self.m2_axis_config, ensure_ascii=False))
        self.settings.setValue("m2/vlsr_style", json.dumps(self.m2_vlsr_style, ensure_ascii=False))
        self.species_spectrum_products = {}
        self.log_species("[INFO] M2 plot styles updated." if self.ui_language == "en" else "[INFO] Estilos y ejes del espectro final M2 actualizados.")

    def generate_species_spectrum_products(self, export_after: bool = False):
        en = self.ui_language == "en"
        rows = self._species_current_main_for_products()
        if rows.empty:
            self.notify_info("Run molecular identification first." if en else "Primero ejecuta la identificación molecular.")
            return
        cache = self._prepare_species_final_sources(force=True)
        if not cache:
            self.notify_info("No spectrum is available for the selected M2 source." if en else "No hay un espectro disponible para el origen seleccionado en M2.")
            return
        label_mode = self.species_final_label_mode
        self.log_species("[INFO] Building final identified spectra..." if en else "[INFO] Construyendo espectros finales identificados...")

        def work(progress):
            products = {}
            names = list(cache)
            total = max(1, len(names))
            for pos, name in enumerate(names, start=1):
                raw = self._species_final_figure_provider(name, label_mode)
                if raw: products[name] = raw
                progress(min(95, int(95*pos/total)), f"{pos}/{total}: {name}")
            return products

        def on_success(products):
            self.species_spectrum_products = dict(products or {})
            available = bool(self.species_spectrum_products)
            self.species_export_spectra_button.setEnabled(available)
            self.species_final_spectrum_button.setEnabled(bool(cache))
            self.species_open_plotly_button.setEnabled(True)
            count=len(self.species_spectrum_products)
            self.log_species(f"[OK] Final identified spectra built: {count}." if en else f"[OK] Espectros finales identificados construidos: {count}.")
            if export_after and available:
                QTimer.singleShot(0, self.export_species_spectrum_products)
            elif available:
                self.notify_success(f"{count} spectrum product(s) ready." if en else f"{count} espectro(s) identificado(s) listos.")

        def on_error(message, details):
            self.log_species(f"[ERROR] Final spectra: {message}"); self.log_species(details)
            QMessageBox.critical(self, "M2", message)

        self._start_background_task(
            "species_spectrum_products", work, on_success, on_error=on_error,
            busy_widgets=(self.species_export_spectra_button,),
            status_message="Building identified spectra..." if en else "Generando espectros identificados...",
        )

    def _plotly_nearest_y(fig, freq: float):
        best = None
        for trace in fig.data:
            try:
                x = np.asarray(trace.x, dtype=float); y = np.asarray(trace.y, dtype=float)
            except Exception:
                continue
            mask = np.isfinite(x) & np.isfinite(y)
            if not mask.any():
                continue
            x = x[mask]; y = y[mask]
            idx = int(np.argmin(np.abs(x - freq)))
            dist = abs(float(x[idx]) - freq)
            if best is None or dist < best[0]:
                best = (dist, float(y[idx]))
        return best[1] if best else 0.0

    def _build_identified_species_plot_with_field(self, base_plot_json: str, rows: pd.DataFrame, title: str, label_field: str, source_metadata: dict | None = None) -> str:
        """Overlay M2 identifiers and one VLSR reference per identified M1 detection.

        The immutable ``detection_id`` carried by the M1 detection trace is the
        primary key.  Frequency is only a defensive fallback for legacy rows.
        This avoids ambiguous source/path matching in multi-spectrum CLASS .30m
        sessions, where several averaged spectra can originate from one file.

        IMPORTANT: this function is called *after* the M1 axis/style pipeline.
        Therefore M2 annotations are the last graphical layer added and cannot
        be silently removed by subsequent M1 post-processing.
        """
        from plotly import io as pio
        from plotly import graph_objects as go

        fig = pio.from_json(base_plot_json)
        en = self.ui_language == "en"
        styles = deepcopy(self.m2_plot_styles or DEFAULT_PLOT_STYLES)

        # Apply M2 style choices to inherited M1 traces and remove any legacy
        # M2 overlays/residual trace before rebuilding the final product.
        kept = []
        detection_trace = None
        for trace in fig.data:
            meta = trace.meta if isinstance(getattr(trace, "meta", None), dict) else {}
            role = str(meta.get("czspec_role") or "").lower()
            name = str(trace.name or "").casefold()
            if role in {"m2_identifier", "m2_vlsr_reference", "legend_m2_vlsr"}:
                continue

            style_role = None
            if role == "detection" or "detecci" in name or "detection" in name:
                style_role = "detections"
                detection_trace = trace
            elif role == "fit_component":
                style_role = "fit_components"
            elif role in {"fit", "fit_sum", "legend_final_profiles"} or "ajuste gauss" in name or "fit" in name:
                style_role = "fits"
            elif role == "legend_fit_components":
                style_role = "fit_components"
            elif role == "residual" or "residual final" in name or "final residual" in name:
                style_role = "residual"
            elif "ajuste de base" in name or "baseline" in name:
                style_role = "baseline"
            elif "corregido por base" in name or "baseline corrected" in name:
                style_role = "corrected"
            elif "espectro" in name or "spectrum" in name:
                style_role = "spectrum"

            if style_role == "detections":
                marker = dict(trace.marker.to_plotly_json() if trace.marker else {})
                marker.update({
                    "color": styles["detections"].get("color"),
                    "size": styles["detections"].get("size", 7.0),
                })
                trace.marker = marker
            elif style_role in styles and hasattr(trace, "line"):
                line = dict(trace.line.to_plotly_json() if trace.line else {})
                line.update({
                    k: styles[style_role].get(k)
                    for k in ("color", "width", "dash")
                    if styles[style_role].get(k) is not None
                })
                trace.line = line
            kept.append(trace)
        fig.data = tuple(kept)

        # Reuse the exact M1 L# annotation anchors.  M1 already knows the
        # correct plotted coordinates for every accepted detection, so M2 must
        # enrich those labels rather than trying to reconstruct their position
        # from a parallel table.  This is especially important for CLASS .30m
        # sessions, where several internal spectra may share the same source
        # path.  detection_id/frequency remain defensive fallbacks only.
        m1_label_anchors = []
        annotations = []
        for ann in list(fig.layout.annotations or []):
            txt = str(getattr(ann, "text", "") or "").strip()
            plain = re.sub(r"<[^>]+>", "", txt).strip()
            match = re.fullmatch(r"L(\d+)", plain)
            if match:
                try:
                    ax = float(getattr(ann, "x", np.nan))
                    ay = float(getattr(ann, "y", np.nan))
                except Exception:
                    ax = ay = np.nan
                m1_label_anchors.append({
                    "line_no": int(match.group(1)),
                    "plot_x": ax,
                    "plot_y": ay,
                    "xref": str(getattr(ann, "xref", "x") or "x"),
                    "yref": str(getattr(ann, "yref", "y") or "y"),
                })
                continue
            annotations.append(ann)
        fig.layout.annotations = tuple(annotations)

        rows = rows.copy() if rows is not None else pd.DataFrame()
        if rows.empty or detection_trace is None:
            fig.update_layout(
                title=(f"Final identified spectrum — {title}" if en else f"Espectro final identificado — {title}"),
                template="plotly_white", hovermode="closest",
            )
            return fig.to_json()

        # Normalize M2 keys. detection_id is authoritative; observed frequency
        # remains available as a precise fallback for legacy TOP-K tables.
        if "detection_id" in rows.columns:
            rows["__did__"] = rows["detection_id"].fillna("").astype(str).str.strip()
        else:
            rows["__did__"] = ""
        if "ν_obs_MHz" in rows.columns:
            rows["__nu__"] = pd.to_numeric(rows["ν_obs_MHz"], errors="coerce")
        else:
            rows["__nu__"] = np.nan

        by_detection = {}
        by_line = {}

        def _row_line_number(value):
            try:
                if pd.isna(value):
                    return None
            except Exception:
                pass
            text = str(value or "").strip()
            match = re.search(r"(?:^|\b)L?\s*(\d+)(?:\b|$)", text, flags=re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except Exception:
                    return None
            try:
                return int(float(text))
            except Exception:
                return None

        for _, row in rows.iterrows():
            did = str(row.get("__did__", "") or "").strip()
            if did and did not in by_detection:
                by_detection[did] = row
            if "Line" in rows.columns:
                line_no = _row_line_number(row.get("Line"))
                if line_no is not None and line_no not in by_line:
                    by_line[line_no] = row

        # Read exact plotted detections from M1. customdata is
        # [detection_id, line_number, seed_frequency, fit_amplitude].
        axis_cfg = dict((fig.layout.meta or {}).get("czspec_spectral_axes") or {}) if isinstance(fig.layout.meta, dict) else {}
        orientation = str(axis_cfg.get("orientation") or "horizontal")
        try:
            det_x = np.asarray(detection_trace.x, dtype=float)
            det_y = np.asarray(detection_trace.y, dtype=float)
        except Exception:
            det_x = np.asarray([], dtype=float); det_y = np.asarray([], dtype=float)
        custom = list(detection_trace.customdata or [])

        detections_from_trace = []
        did_by_line = {}
        for idx in range(min(len(det_x), len(det_y))):
            cd = custom[idx] if idx < len(custom) else []
            try:
                did = str(cd[0] or "").strip()
            except Exception:
                did = ""
            try:
                line_no = int(float(cd[1]))
            except Exception:
                line_no = idx + 1
            freq = float(det_y[idx] if orientation == "vertical" else det_x[idx])
            if did:
                did_by_line.setdefault(line_no, did)
            detections_from_trace.append({
                "did": did,
                "line_no": line_no,
                "freq": freq,
                "plot_x": float(det_x[idx]),
                "plot_y": float(det_y[idx]),
                "xref": "x",
                "yref": "y",
            })

        # Prefer M1's already-visible L# annotations as graphical anchors.
        # They are the most reliable representation of what the user actually
        # sees.  If labels were intentionally disabled in M1, fall back to the
        # detection trace.
        detections = []
        if m1_label_anchors:
            for anchor in m1_label_anchors:
                line_no = int(anchor["line_no"])
                plot_x = float(anchor.get("plot_x", np.nan))
                plot_y = float(anchor.get("plot_y", np.nan))
                freq = float(plot_y if orientation == "vertical" else plot_x)
                detections.append({
                    "did": did_by_line.get(line_no, ""),
                    "line_no": line_no,
                    "freq": freq,
                    "plot_x": plot_x,
                    "plot_y": plot_y,
                    "xref": str(anchor.get("xref") or "x"),
                    "yref": str(anchor.get("yref") or "y"),
                })
        else:
            detections = detections_from_trace

        # Adaptive fallback tolerance: M2 normally receives the exact fitted
        # centre from M1, so this only needs to cover tiny legacy round-off.
        det_freqs = np.asarray([d["freq"] for d in detections if np.isfinite(d["freq"])], dtype=float)
        diffs = np.diff(np.sort(det_freqs)) if det_freqs.size > 1 else np.asarray([])
        diffs = diffs[np.isfinite(diffs) & (diffs > 0)]
        if diffs.size:
            freq_tol = max(1e-5, min(0.02, 0.15 * float(np.nanmedian(diffs))))
        else:
            freq_tol = 0.01

        def row_for_detection(det):
            did = det["did"]
            if did and did in by_detection:
                return by_detection[did]
            # Within one already-frequency-filtered spectrum, the local M1 Line
            # number is an exact and much more robust key than file/path text.
            line_no = int(det.get("line_no", -1))
            if line_no in by_line:
                return by_line[line_no]
            nu = pd.to_numeric(rows["__nu__"], errors="coerce")
            finite = nu.notna()
            if not finite.any():
                return None
            distance = (nu - float(det["freq"])).abs()
            idx = distance[finite].idxmin()
            try:
                if float(distance.loc[idx]) <= freq_tol:
                    return rows.loc[idx]
            except Exception:
                pass
            return None

        detection_color = str(styles.get("detections", {}).get("color", "#8B5CF6"))
        vstyle = {"color": "#D97706", "width": 1.5, "dash": "dot"}
        vstyle.update(self.m2_vlsr_style or {})
        c_kms = 299792.458

        source_metadata = dict(source_metadata or {})
        source_vlsr_fallback = np.nan
        for key in ("vlsr_kms", "v_lsr_kms", "VLSR", "VLSR [km/s]", "source_vlsr_kms"):
            try:
                value = float(source_metadata.get(key, np.nan))
            except Exception:
                value = np.nan
            if np.isfinite(value):
                source_vlsr_fallback = value
                break

        # Scientific plot limits for VLSR reference traces.
        x_arrays, y_arrays = [], []
        for trace in fig.data:
            meta = trace.meta if isinstance(getattr(trace, "meta", None), dict) else {}
            role = str(meta.get("czspec_role") or "")
            if role.startswith("legend_") or str(trace.name or "").startswith("__czspec_"):
                continue
            try:
                xx = np.asarray(trace.x, dtype=float); yy = np.asarray(trace.y, dtype=float)
            except Exception:
                continue
            mask = np.isfinite(xx) & np.isfinite(yy)
            if mask.any():
                x_arrays.append(xx[mask]); y_arrays.append(yy[mask])
        if x_arrays:
            xmin = min(float(np.min(a)) for a in x_arrays); xmax = max(float(np.max(a)) for a in x_arrays)
            ymin = min(float(np.min(a)) for a in y_arrays); ymax = max(float(np.max(a)) for a in y_arrays)
        else:
            xmin = ymin = -1.0; xmax = ymax = 1.0

        identifier_annotations = []
        has_vlsr_references = False
        matched_count = 0
        for det in detections:
            row = row_for_detection(det)
            if row is None:
                continue
            matched_count += 1
            line_no = int(det["line_no"])

            molecular = ""
            if label_field != "none":
                molecular = str(row.get(label_field, "") or "").strip()
                if not molecular:
                    molecular = str(row.get("name", "") or row.get("chemical_name", "") or "").strip()
            line_label = f"L{line_no}" + (f" {molecular}" if molecular else "")

            if label_field != "none":
                identifier_annotations.append(dict(
                    x=float(det["plot_x"]), y=float(det["plot_y"]),
                    xref=str(det.get("xref") or "x"), yref=str(det.get("yref") or "y"), text=line_label,
                    showarrow=False, textangle=-45, captureevents=True,
                    xanchor="left", yanchor="bottom", xshift=5,
                    yshift=9 + 10 * ((line_no - 1) % 4),
                    font=dict(size=11, color=detection_color),
                    bgcolor="rgba(255,255,255,0.68)", borderpad=1,
                ))

            def _num(key):
                try:
                    value = float(row.get(key, np.nan))
                    return value if np.isfinite(value) else np.nan
                except Exception:
                    return np.nan

            rest = _num("orderedfreq")
            vlsr = _num("source_vlsr_kms")
            if not np.isfinite(vlsr):
                vlsr = source_vlsr_fallback
            expected = _num("nu_expected_vlsr_mhz")
            if not np.isfinite(expected) and np.isfinite(rest) and np.isfinite(vlsr):
                expected = rest * (1.0 - vlsr / c_kms)

            if np.isfinite(expected):
                if orientation == "vertical":
                    if ymin <= expected <= ymax:
                        has_vlsr_references = True
                        fig.add_trace(go.Scatter(
                            x=[xmin, xmax], y=[expected, expected], mode="lines",
                            name=f"VLSR L{line_no}" + (f" · {molecular}" if molecular else ""),
                            showlegend=False,
                            line=dict(color=str(vstyle.get("color", "#D97706")), width=float(vstyle.get("width", 1.5)), dash=str(vstyle.get("dash", "dot"))),
                            hovertemplate=f"VLSR L{line_no}<br>ν(VLSR)={expected:.8f} MHz<extra></extra>",
                            meta={"czspec_role": "m2_vlsr_reference", "line_no": line_no},
                            legendgroup="m2_vlsr_references",
                        ))
                else:
                    if xmin <= expected <= xmax:
                        has_vlsr_references = True
                        fig.add_trace(go.Scatter(
                            x=[expected, expected], y=[ymin, ymax], mode="lines",
                            name=f"VLSR L{line_no}" + (f" · {molecular}" if molecular else ""),
                            showlegend=False,
                            line=dict(color=str(vstyle.get("color", "#D97706")), width=float(vstyle.get("width", 1.5)), dash=str(vstyle.get("dash", "dot"))),
                            hovertemplate=f"VLSR L{line_no}<br>ν(VLSR)={expected:.8f} MHz<extra></extra>",
                            meta={"czspec_role": "m2_vlsr_reference", "line_no": line_no},
                            legendgroup="m2_vlsr_references",
                        ))

        if identifier_annotations and label_field != "none":
            fig.update_layout(annotations=list(fig.layout.annotations or []) + identifier_annotations)

        if has_vlsr_references:
            fig.add_trace(go.Scatter(
                x=[None], y=[None], mode="lines",
                name="Referencias VLSR por línea" if not en else "Per-line VLSR references",
                showlegend=True, hoverinfo="skip", legendgroup="m2_vlsr_references",
                line=dict(color=str(vstyle.get("color", "#D97706")), width=float(vstyle.get("width", 1.5)), dash=str(vstyle.get("dash", "dot"))),
                meta={"czspec_role": "legend_m2_vlsr"},
            ))

        # Record association diagnostics in layout metadata and the M2 log. This
        # makes a future mismatch visible instead of silently producing a blank
        # overlay.
        meta = dict(fig.layout.meta or {}) if isinstance(fig.layout.meta, dict) else {}
        meta["m2_identifier_matches"] = int(matched_count)
        meta["m2_identifier_candidates"] = int(len(detections))
        fig.layout.meta = meta
        if detections and matched_count == 0:
            self.log_species(
                f"[WARN] Final Spectrum: 0/{len(detections)} detections matched M2 identifications for {title}."
                if en else
                f"[WARN] Espectro final: 0/{len(detections)} detecciones empataron con identificaciones M2 para {title}."
            )

        fig.update_layout(
            title=(f"Final identified spectrum — {title}" if en else f"Espectro final identificado — {title}"),
            template="plotly_white", hovermode="closest",
        )
        return fig.to_json()

    def open_species_final_spectrum(self):
        en = self.ui_language == "en"
        rows = self._species_current_main_for_products()
        if rows.empty:
            self.notify_info("Run molecular identification first." if en else "Primero ejecuta la identificación molecular.")
            return
        cache = self._prepare_species_final_sources(force=True)
        if not cache:
            self.notify_info("No spectrum is available for the selected source." if en else "No hay un espectro disponible para el origen seleccionado.")
            return
        dialog = SpeciesSpectrumDialog(
            list(cache.keys()), self._species_final_figure_provider,
            style_callback=self.open_species_plot_style_dialog,
            language=self.ui_language, label_mode=self.species_final_label_mode,
            output_directory=SPECIES_IMAGES_DIR, module_label="M2",
            filename_prefix=self._module_save_label("M2"), parent=self,
        )
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._species_spectrum_dialog = dialog
        dialog.show(); dialog.raise_(); dialog.activateWindow()

    def _column_density_final_figure_provider(self, source_name: str, label_mode: str) -> str | None:
        """Reuse the M2 spectrum and attach M3 N/τ information to line-label hover.

        Column density is not plotted as an intensity-vs-frequency curve.  It is
        attached to the corresponding L# identifier, preserving the physical
        meaning of the spectral axes while still making the M3 result available
        directly from the spectrum.
        """
        raw = self._species_final_figure_provider(source_name, label_mode)
        if not raw:
            return raw
        try:
            from plotly import io as pio
            fig = pio.from_json(raw)
        except Exception:
            return raw

        info_by_obs: dict[int, list[str]] = {}
        mod_df = getattr(self, "column_density_vasyunina_df", None)
        if mod_df is not None and not mod_df.empty and "obs_id" in mod_df.columns:
            for _, row in mod_df.iterrows():
                try:
                    obs = int(float(row.get("obs_id")))
                except Exception:
                    continue
                parts=[]
                for col in mod_df.columns:
                    m=re.fullmatch(r"N_tot_([0-9]+(?:\.[0-9]+)?)K_cm2", str(col))
                    if not m:
                        continue
                    try:
                        val=float(row.get(col, np.nan))
                    except Exception:
                        continue
                    if not np.isfinite(val):
                        continue
                    err_col=f"N_tot_{m.group(1)}K_err_cm2"
                    try:
                        err=float(row.get(err_col, np.nan))
                    except Exception:
                        err=np.nan
                    text=f"N({m.group(1)} K)={val:.3e} cm⁻²"
                    if np.isfinite(err): text += f" ± {err:.2e}"
                    parts.append(text)
                if parts:
                    prefix = "OTM" if self.ui_language == "en" else "MOD"
                    info_by_obs.setdefault(obs, []).append(prefix + ": " + "; ".join(parts))

        mth_df = getattr(self, "column_density_sanhueza_df", None)
        if mth_df is not None and not mth_df.empty and "obs_id" in mth_df.columns:
            for _, row in mth_df.iterrows():
                try:
                    obs=int(float(row.get("obs_id")))
                except Exception:
                    continue
                try:
                    tex=float(row.get("Tex [K]", np.nan))
                except Exception:
                    tex=np.nan
                vals=[]
                for col in mth_df.columns:
                    m=re.fullmatch(r"N_(\d+)_cm2", str(col))
                    if not m:
                        continue
                    idx=m.group(1)
                    try:
                        val=float(row.get(col, np.nan))
                    except Exception:
                        continue
                    if not np.isfinite(val):
                        continue
                    ref=str(row.get(f"ref_{idx}_name", "") or "").strip()
                    bit=f"N{idx}={val:.3e} cm⁻²" + (f" ({ref})" if ref else "")
                    vals.append(bit)
                if vals:
                    prefix = "HTM" if self.ui_language == "en" else "MTH"
                    ttxt=f" · Tₑₓ={tex:g} K" if np.isfinite(tex) else ""
                    info_by_obs.setdefault(obs, []).append(prefix + ttxt + ": " + "; ".join(vals))

        if not info_by_obs:
            return fig.to_json()
        for ann in list(fig.layout.annotations or []):
            text=str(getattr(ann, "text", "") or "")
            m=re.match(r"L(\d+)\b", re.sub(r"<[^>]+>", "", text))
            if not m:
                continue
            obs=int(m.group(1))
            details=info_by_obs.get(obs)
            if details:
                ann.hovertext = "<br>".join(details)
                ann.captureevents = True
        return fig.to_json()

    def open_column_density_final_spectrum(self):
        """Open the identified spectrum from M3 without inventing a spectral N axis.

        Column density is a derived property of an identified transition/species,
        not a channel-by-channel intensity coordinate.  M3 therefore reuses the
        scientifically aligned M2 spectrum and saves it into M3's own figures
        folder.  Physical N/τ annotations can be added as metadata without
        pretending that N is another spectral intensity trace.
        """
        en = self.ui_language == "en"
        rows = self._species_current_main_for_products()
        if rows.empty:
            self.notify_info("Run molecular identification first." if en else "Primero ejecuta la identificación molecular.")
            return
        cache = self._prepare_species_final_sources(force=True)
        if not cache:
            self.notify_info("No spectrum is available for M3." if en else "No hay un espectro disponible para M3.")
            return
        dialog = SpeciesSpectrumDialog(
            list(cache.keys()), self._column_density_final_figure_provider,
            style_callback=self.open_species_plot_style_dialog,
            language=self.ui_language, label_mode=self.species_final_label_mode,
            output_directory=COLUMN_DENSITY_IMAGES_DIR, module_label="M3",
            window_title=("Espectro final — M3" if not en else "Final spectrum — M3"),
            filename_prefix=self._module_save_label("M3"), parent=self,
        )
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._column_density_spectrum_dialog = dialog
        dialog.show(); dialog.raise_(); dialog.activateWindow()

    def _write_m2_table_file(self, df: pd.DataFrame, path: Path, fmt: str, title: str, decimals: int):
        export_df = df.copy()
        for col in export_df.columns:
            if pd.api.types.is_float_dtype(export_df[col]):
                export_df[col] = export_df[col].round(decimals)
        float_format = f"%.{decimals}f"
        if fmt == "csv": export_df.to_csv(path,index=False,encoding="utf-8",float_format=float_format)
        elif fmt == "tsv": export_df.to_csv(path,index=False,sep="\t",encoding="utf-8",float_format=float_format)
        elif fmt == "dsv": export_df.to_csv(path,index=False,sep=";",encoding="utf-8",float_format=float_format)
        elif fmt == "txt": path.write_text(export_df.to_string(index=False,float_format=lambda v:f"{float(v):.{decimals}f}"),encoding="utf-8")
        elif fmt == "json": export_df.to_json(path,orient="records",indent=2,force_ascii=False,double_precision=decimals)
        elif fmt == "xml": export_df.to_xml(path,index=False,root_name="czspec_m2_results",row_name="candidate")
        elif fmt == "xlsx": export_df.to_excel(path,index=False,float_format=float_format)
        elif fmt == "ods": export_df.to_excel(path,index=False,engine="odf",float_format=float_format)
        elif fmt == "html": self._write_m1_html_table(export_df,path,title,decimals=decimals)
        elif fmt == "latex": self._write_m1_standalone_latex(export_df,path,title,decimals=decimals)
        else: raise ValueError(f"Unsupported format: {fmt}")

    def export_species_tables(self):
        en = self.ui_language == "en"
        if not self.species_last_result:
            self.notify_info("Run molecular identification first." if en else "Primero ejecuta la identificación molecular.")
            return
        formats = list(self.m2_table_export_formats or [])
        if not formats:
            self.notify_info("Select M2 table formats in Settings." if en else "Selecciona formatos de tabla de M2 en Configuración.")
            return
        main = self._filter_dataframe_by_visible_columns(self._get_current_species_main_view_df(), self.species_table)
        topk = self._filter_dataframe_by_visible_columns(self._get_current_species_topk_view_df(), self.species_topk_table)
        if (main is None or main.empty) and (topk is None or topk.empty):
            self.notify_info("There are no visible rows/columns to export." if en else "No hay filas/columnas visibles para exportar.")
            return
        SPECIES_TABLES_DIR.mkdir(parents=True, exist_ok=True)
        base = self._module_output_stem("M2", self.species_output_input.text() or "m2_identification")
        decimals = max(0,min(10,int(getattr(self,"table_decimal_places",3))))
        made=[]; failed=[]
        datasets=(("main",main,"M2 main molecular identifications" if en else "Identificaciones moleculares principales M2"),("topk",topk,"M2 TOP-K molecular candidates" if en else "Candidatos moleculares TOP-K M2"))
        for kind,df,title in datasets:
            if df is None or df.empty: continue
            df=df.drop(columns=["__source_index__"],errors="ignore")
            for fmt in formats:
                try:
                    folder=SPECIES_TABLES_DIR/fmt.upper(); folder.mkdir(parents=True,exist_ok=True)
                    ext="tex" if fmt=="latex" else fmt
                    path=_unique_output_path(folder/f"{base}_{kind}.{ext}")
                    self._write_m2_table_file(df,path,fmt,title,decimals); made.append(path)
                except Exception as exc: failed.append(f"{kind}/{fmt}: {exc}")
        self.log_species(f"[OK] Exported M2 table files: {len(made)}" if en else f"[OK] Archivos de tabla M2 exportados: {len(made)}")
        msg=(f"{len(made)} table file(s) exported. The current filter and visible columns were respected." if en else f"Se exportaron {len(made)} archivo(s) de tabla. Se respetaron el filtro actual y las columnas visibles.")
        if failed: msg+="\n\n"+("Unavailable formats:" if en else "Formatos no disponibles:")+"\n"+"\n".join(failed[:12])
        self.notify("M2 tables" if en else "Tablas M2",msg,duration_ms=10000)

    def _export_species_plot_collection(self, products: dict[str,str], subfolder: str, prefix: str, formats: list[str]):
        from plotly import io as pio
        if subfolder == "q_t":
            root = SPECIES_GRAPHICS_DIR / "q_t"
        elif subfolder == "spectra":
            root = SPECIES_GRAPHICS_DIR / "spectra"
        else:
            root = SPECIES_GRAPHICS_DIR / subfolder
        root.mkdir(parents=True,exist_ok=True)
        made=[]; failed=[]
        for label,raw in products.items():
            safe=self._make_safe_output_name(label,prefix); fig=pio.from_json(raw)
            for fmt in formats:
                try:
                    folder=root/fmt.upper(); folder.mkdir(parents=True,exist_ok=True)
                    label_prefix = self._module_save_label("M2")
                    stem = f"{prefix}_{safe}"
                    if label_prefix and not stem.casefold().startswith(label_prefix.casefold()):
                        stem = f"{label_prefix}_{stem}"
                    path=_unique_output_path(folder/f"{stem}.{fmt}")
                    if fmt=="html": fig.write_html(str(path),include_plotlyjs=True,full_html=True)
                    else: fig.write_image(str(path),scale=2)
                    made.append(path)
                except Exception as exc: failed.append(f"{label}/{fmt}: {exc}")
        return root,made,failed

    def export_species_qt_products(self):
        en=self.ui_language=="en"
        if not self.species_qt_products:
            self.generate_species_qt_products(export_after=True)
            return
        formats=list(self.m2_plot_export_formats or [])
        if not formats:
            self.notify_info("Select M2 plot formats in Settings." if en else "Selecciona formatos gráficos de M2 en Configuración."); return
        def work(progress):
            progress(10,"Exporting Q(T)" if en else "Exportando Q(T)")
            return self._export_species_plot_collection(dict(self.species_qt_products),"q_t","QT",formats)
        def ok(payload):
            root,made,failed=payload
            if self.species_last_result:self.species_last_result.qt_dir=str(root)
            self.species_open_qt_button.setEnabled(True)
            self.log_species(f"[OK] Q(T) files exported: {len(made)}")
            msg=(f"{len(made)} Q(T) file(s) exported." if en else f"Se exportaron {len(made)} archivo(s) Q(T).")
            if failed:msg+="\n\n"+("Unavailable formats:" if en else "Formatos no disponibles:")+"\n"+"\n".join(failed[:10])
            self.notify("Q(T)",msg,duration_ms=10000)
        def err(message,details):self.log_species(f"[ERROR] Q(T) export: {message}");self.log_species(details);QMessageBox.critical(self,"Q(T)",message)
        self._start_background_task("species_export_qt",work,ok,on_error=err,busy_widgets=(self.species_export_qt_button,),status_message="Exporting Q(T)..." if en else "Exportando Q(T)...")

    def export_species_spectrum_products(self):
        en=self.ui_language=="en"
        if not self.species_spectrum_products:
            self.generate_species_spectrum_products(export_after=True)
            return
        formats=list(self.m2_plot_export_formats or [])
        if not formats:
            self.notify_info("Select M2 plot formats in Settings." if en else "Selecciona formatos gráficos de M2 en Configuración."); return
        def work(progress):
            progress(10,"Exporting spectra" if en else "Exportando espectros")
            return self._export_species_plot_collection(dict(self.species_spectrum_products),"spectra","M2_spectrum",formats)
        def ok(payload):
            root,made,failed=payload
            if self.species_last_result:self.species_last_result.plotly_dir=str(root)
            self.species_open_plotly_button.setEnabled(True)
            self.log_species(f"[OK] Spectrum files exported: {len(made)}")
            msg=(f"{len(made)} spectrum file(s) exported." if en else f"Se exportaron {len(made)} archivo(s) de espectro.")
            if failed:msg+="\n\n"+("Unavailable formats:" if en else "Formatos no disponibles:")+"\n"+"\n".join(failed[:10])
            self.notify("M2 spectra" if en else "Espectros M2",msg,duration_ms=10000)
        def err(message,details):self.log_species(f"[ERROR] Spectrum export: {message}");self.log_species(details);QMessageBox.critical(self,"M2 spectra" if en else "Espectros M2",message)
        self._start_background_task("species_export_spectra",work,ok,on_error=err,busy_widgets=(self.species_export_spectra_button,),status_message="Exporting spectra..." if en else "Exportando espectros...")

    def run_species_process(self):
        en = self.ui_language == "en"
        if not bool(getattr(self, "network_online", True)):
            message = (
                "M2 molecular identification uses Splatalogue and is skipped in Offline mode. Load an existing M2 table or enable Online mode."
                if en else
                "La identificación molecular de M2 usa Splatalogue y se omite en modo sin Internet. Carga una tabla M2 existente o activa el modo Online."
            )
            self.log_species("[OFFLINE] " + message)
            self.notify_info(message)
            return
        if not self.species_selected_file:
            QMessageBox.warning(
                self, "Notice" if en else "Aviso",
                "Select or refresh an input table for M2 first." if en else "Primero selecciona o actualiza una tabla de entrada para M2."
            )
            return

        output_name = self.species_output_input.text().strip()
        if not output_name:
            try:
                preview = self._read_species_input_table(self.species_selected_file)
            except Exception:
                preview = pd.DataFrame()
            output_name = self._suggest_species_output_name(preview, Path(self.species_selected_file).stem)
            self.species_output_input.setText(output_name)

        temperatures = self._parse_species_temperatures()
        topk = self.species_topk_input.value()

        self.species_log_area.clear()
        self._species_log_history = []
        self.species_topk_df = None
        self.species_topk_filtered_df = None
        self.species_main_filtered_df = None
        self.species_qt_products = {}
        self.species_spectrum_products = {}
        self._species_final_sources_cache = {}
        self.species_generate_qt_button.setEnabled(False)
        self.species_generate_spectra_button.setEnabled(False)
        self.species_export_tables_button.setEnabled(False)
        self.species_export_qt_button.setEnabled(False)
        self.species_export_spectra_button.setEnabled(False)
        self.species_final_spectrum_button.setEnabled(False)

        self.species_filter_active = False
        self.species_filter_text = ""
        self.species_filter_fields = []
        self.species_search_input.clear()

        self.column_density_filter_active = False
        self.column_density_filter_text = ""
        self.column_density_filter_fields = []

        if hasattr(self, "cd_search_input"):
            self.cd_search_input.clear()

        self.column_density_vasyunina_df = None
        self.column_density_sanhueza_df = None

        self.column_density_source_df = None

        self.populate_table_widget_from_dataframe(self.species_table, None)
        self.species_topk_table.clear()
        self.species_topk_table.setRowCount(0)
        self.species_topk_table.setColumnCount(0)

        self.populate_table_widget_from_dataframe(self.column_density_source_table, None)
        self.populate_table_widget_from_dataframe(self.vasyunina_results_table, None)
        self.populate_table_widget_from_dataframe(self.sanhueza_results_table, None)
        self._refresh_column_density_comparison_tables(None, None)
        self.column_density_tables_tabs.setCurrentWidget(
            self.column_density_source_table_box
        )
        self.column_density_source_label.setText("Sin datos disponibles desde el buscador de especies")
        self.vasyunina_run_button.setEnabled(False)
        self.sanhueza_run_button.setEnabled(False)
        self.save_vasyunina_button.setEnabled(False)
        self.save_sanhueza_button.setEnabled(False)
        

        self.log_species("Starting molecular identification..." if en else "Iniciando identificación molecular...")
        self.log_species("Querying Splatalogue and building candidates..." if en else "Consultando Splatalogue y construyendo candidatos...")

        config = SpeciesSearchConfig(
            csv_input=self.species_selected_file,
            output_name=output_name,
            target_temperatures=temperatures,
            topk=topk,
            compute_q_values=True,
            generate_qt_plots=False,
            generate_plotly=False,
            search_policy=deepcopy(self.species_search_policy),
        )

        def work(progress):
            return run_species_search(config, progress_callback=progress)

        def on_success(result):
            self.species_last_result = result

            for line in result.logs:
                self.log_species(line)

            if not result.success:
                QMessageBox.critical(self, "Error", result.message)
                return
            
            self.species_last_output_name = output_name
            self.species_last_target_temperatures = temperatures
            self.species_last_main_df = self._friendly_source_dataframe(result.main_dataframe.copy()) if result.main_dataframe is not None else None
            self.species_last_topk_df = self._friendly_source_dataframe(result.topk_dataframe.copy()) if result.topk_dataframe is not None else None
            self.species_generate_qt_button.setEnabled(True)
            self.species_generate_spectra_button.setEnabled(True)
            self.species_export_tables_button.setEnabled(True)
            self.species_export_qt_button.setEnabled(True)
            self.species_export_spectra_button.setEnabled(True)
            self._species_final_sources_cache = {}
            self.species_final_spectrum_button.setEnabled(bool(self._species_spectrum_entries()))

            self.species_topk_df = self._prepare_species_topk_dataframe(self.species_last_topk_df)
            self.populate_species_topk_table()
            self.refresh_species_main_table_from_selection()
            self.refresh_column_density_source_preview()
            self.refresh_lte_inputs()

            self.species_open_plotly_button.setEnabled(True)
            self.species_open_qt_button.setEnabled(True)
            self.species_open_results_button.setEnabled(True)
            self.species_export_tables_button.setEnabled(True)

            self.log_species("Process completed successfully." if en else "Proceso terminado correctamente.")
            self.notify_success(
                "Molecular identification completed successfully. Main results and TOP-K are available."
                if en else
                "La identificación molecular terminó correctamente. Las tablas de resultados principales y TOP-K ya están disponibles."
            )

        def on_error(message, details):
            self.log_species(f"[ERROR] Buscador de especies: {message}")
            self.log_species(details)
            QMessageBox.critical(self, "Error en identificación molecular", message)

        self._start_background_task(
            "species_search",
            work,
            on_success,
            on_error=on_error,
            busy_widgets=(self.species_run_button, self.species_load_button, self.species_refresh_from_m1_button),
            status_message=("Querying Splatalogue and identifying candidates..." if en else "Consultando Splatalogue e identificando candidatos..."),
        )

    def generate_species_plots(self):
        if not self.species_selected_file:
            QMessageBox.warning(self, "Aviso", "Primero ejecuta el buscador de especies.")
            return

        if not self.species_last_output_name:
            QMessageBox.warning(self, "Aviso", "No hay una ejecución previa del buscador para generar gráficas.")
            return

        temperatures = self.species_last_target_temperatures or self._parse_species_temperatures()
        topk = self.species_topk_input.value()

        self.log_species("[INFO] Generando gráficas Q(T) y Plotly...")
        config = SpeciesSearchConfig(
            csv_input=self.species_selected_file,
            output_name=self.species_last_output_name,
            target_temperatures=temperatures,
            topk=topk,
            compute_q_values=True,
            generate_qt_plots=True,
            generate_plotly=True,
        )

        def work(progress):
            return run_species_search(config, progress_callback=progress)

        def on_success(result):

            for line in result.logs:
                self.log_species(line)

            if not result.success:
                QMessageBox.critical(self, "Error", result.message)
                return

            if result.plotly_dir:
                self.species_open_plotly_button.setEnabled(True)
            if result.qt_dir:
                self.species_open_qt_button.setEnabled(True)
            if result.extra.get("run_dir"):
                self.species_open_results_button.setEnabled(True)

            self.species_last_result = result
            self.log_species("[OK] Gráficas generadas correctamente.")
            self.notify_success("Las gráficas Q(T) y Plotly se generaron correctamente.")

        def on_error(message, details):
            self.log_species(f"[ERROR] No se pudieron generar las gráficas: {message}")
            self.log_species(details)
            QMessageBox.critical(self, "Error al generar gráficas", message)

        self._start_background_task(
            "species_plots",
            work,
            on_success,
            on_error=on_error,
            busy_widgets=(self.species_generate_plots_button,),
            status_message="Generando gráficas Q(T) y Plotly...",
        )
    
    def save_species_results(self):
        if not self.species_last_result:
            QMessageBox.warning(self, "Aviso", "No hay resultados para guardar.")
            return

        result = self.species_last_result
        run_dir = Path(result.extra.get("run_dir", ""))

        if not run_dir:
            QMessageBox.warning(self, "Aviso", "No se encontró la carpeta de resultados.")
            return

        try:
            from czspec.logic.species_search import (
                ensure_dir,
                sanitize_name,
                make_qt_plot,
                make_source_plot,
                save_plotly_html,
                parse_cdms_catalog_for_logic,
                build_cdms_logq_dict,
                load_jpl_points_table,
                get_partition_values_for_row,
                build_qt_unique_key,
                build_qt_species_label,
                CDMS_PATH,
                JPL_TABLE_PATH,
            )

            ensure_dir(run_dir)
            plotly_dir = ensure_dir(run_dir / "plotly")
            qt_dir = ensure_dir(run_dir / "q_t")

            output_name = self.species_output_input.text().strip()
            base_name = sanitize_name(output_name) if output_name else "resultados_especies"

            if self.species_filter_active:
                topk_df = self._get_current_species_topk_view_df()
                main_df = self._get_current_species_main_view_df()
            else:
                topk_df = self.species_topk_df.copy() if self.species_topk_df is not None else None

                if topk_df is not None and not topk_df.empty and "selected" in topk_df.columns:
                    main_df = topk_df[topk_df["selected"] == True].copy()
                    if "selected" in main_df.columns:
                        main_df = main_df.drop(columns=["selected"])
                else:
                    main_df = result.main_dataframe.copy() if result.main_dataframe is not None else None

            main_csv = None
            main_html = None
            topk_csv = None
            topk_html = None

            main_df_export = self._filter_dataframe_by_visible_columns(main_df, self.species_table)
            topk_df_export = self._filter_dataframe_by_visible_columns(topk_df, self.species_topk_table)

            if main_df_export is not None and not main_df_export.empty:
                if "__source_index__" in main_df_export.columns:
                    main_df_export = main_df_export.drop(columns=["__source_index__"])
                main_csv = run_dir / f"{base_name}_main.csv"
                main_html = run_dir / f"{base_name}_main.html"
                main_df_export.to_csv(main_csv, index=False)
                main_df_export.to_html(main_html, index=False)

            if topk_df_export is not None and not topk_df_export.empty:
                if "__source_index__" in topk_df_export.columns:
                    topk_df_export = topk_df_export.drop(columns=["__source_index__"])
                topk_csv = run_dir / f"{base_name}_topk.csv"
                topk_html = run_dir / f"{base_name}_topk.html"
                topk_df_export.to_csv(topk_csv, index=False)
                topk_df_export.to_html(topk_html, index=False)

            if not any((main_csv, main_html, topk_csv, topk_html)):
                QMessageBox.warning(
                    self,
                    "Aviso",
                    "No hay tablas visibles para guardar como CSV o HTML.",
                )
                return

            for label, path in (
                ("CSV principal", main_csv),
                ("HTML principal", main_html),
                ("CSV TOP-K", topk_csv),
                ("HTML TOP-K", topk_html),
            ):
                if path:
                    self.log_species(f"{label} guardado: {path}")

            result.main_csv_path = str(main_csv) if main_csv else None
            result.main_html_path = str(main_html) if main_html else None
            result.topk_csv_path = str(topk_csv) if topk_csv else None
            result.topk_html_path = str(topk_html) if topk_html else None
            self.species_open_results_button.setEnabled(True)
            self.notify_success(
                "Las tablas visibles se guardaron correctamente en formatos "
                "CSV y HTML. Las gráficas se generan desde su acción independiente."
            )
            return

        # =========================
        # Guardar Q(T)
        # =========================
            cdms_q_df = parse_cdms_catalog_for_logic(CDMS_PATH)
            cdms_logq = build_cdms_logq_dict(cdms_q_df)
            jpl_points = load_jpl_points_table(JPL_TABLE_PATH)
            target_temperatures = result.extra.get("target_temperatures", [10.0, 28.0])

            qt_plot_written = set()
            if main_df is not None and not main_df.empty:
                for idx in main_df.index:
                    row = main_df.loc[idx]

                    qt_key = build_qt_unique_key(row)
                    if not qt_key or qt_key in qt_plot_written:
                        continue

                    qvals, qsource, temp_grid, q_grid = get_partition_values_for_row(
                        candidate_row=row,
                        cdms_logq=cdms_logq,
                        jpl_points=jpl_points,
                        target_temperatures=target_temperatures,
                    )

                    if qsource == "NONE":
                        continue

                    species_label = build_qt_species_label(row)
                    safe_label = sanitize_name(species_label)

                    plot_path = qt_dir / f"{safe_label}_qt.png"
                    make_qt_plot(
                        output_path=plot_path,
                        species_label=species_label,
                        temp_grid=temp_grid,
                        q_grid=q_grid,
                        target_temperatures=target_temperatures,
                        q_values=qvals,
                        q_source=qsource,
                    )
                    qt_plot_written.add(qt_key)

        # =========================
        # Guardar Plotly
        # =========================
            csv_input = Path(result.extra.get("csv_input", ""))
            if csv_input.exists() and main_df is not None and not main_df.empty:
                try:
                    df_input = pd.read_csv(csv_input)

                    # reconstruir obs_id igual que en run_species_search()
                    if "obs_id" not in df_input.columns:
                        df_input = df_input.copy()
                        df_input["obs_id"] = df_input.index

                    if "Source" in df_input.columns:
                        sources = sorted(df_input["Source"].dropna().astype(str).unique().tolist())

                        for src in sources:
                            fig = make_source_plot(
                                df_input=df_input,
                                out_df=main_df,
                                source_name=src,
                                csv_input_path=csv_input,
                                run_dir=run_dir,
                            )
                            if fig is not None:
                                safe_src = re.sub(r"\W+", "_", str(src))
                                out_html = plotly_dir / f"{safe_src}.html"
                                save_plotly_html(fig, out_html)
                                self.log_species(f"[PLOTLY] Guardado: {out_html}")
                            else:
                                self.log_species(f"[PLOTLY] No se generó figura para Source={src}")
                    else:
                        self.log_species("[PLOTLY] El CSV de entrada no tiene columna 'Source'.")

                        for src in sources:
                            fig = make_source_plot(
                                df_input=df_input,
                                out_df=main_df,
                                source_name=src,
                                csv_input_path=csv_input,
                                run_dir=run_dir,
                            )
                            if fig is not None:
                                safe_src = re.sub(r"\W+", "_", str(src))
                                out_html = plotly_dir / f"{safe_src}.html"
                                save_plotly_html(fig, out_html)
                except Exception as plotly_exc:
                    self.log_species(f"[ERROR] No se pudo guardar Plotly: {plotly_exc}")

            if main_csv:
                self.log_species(f"Archivo CSV principal guardado: {main_csv}")
            if main_html:
                self.log_species(f"Archivo HTML principal guardado: {main_html}")
            if topk_csv:
                self.log_species(f"Archivo CSV TOP-K guardado: {topk_csv}")
            if topk_html:
                self.log_species(f"Archivo HTML TOP-K guardado: {topk_html}")

            self.log_species(f"Carpeta Plotly guardada: {plotly_dir}")
            self.log_species(f"Carpeta Q(T) guardada: {qt_dir}")

            # actualizar rutas visibles
            result.main_csv_path = str(main_csv) if main_csv else None
            result.main_html_path = str(main_html) if main_html else None
            result.topk_csv_path = str(topk_csv) if topk_csv else None
            result.topk_html_path = str(topk_html) if topk_html else None
            result.plotly_dir = str(plotly_dir)
            result.qt_dir = str(qt_dir)

            self.species_open_results_button.setEnabled(True)
            self.species_open_plotly_button.setEnabled(True)
            self.species_open_qt_button.setEnabled(True)

            self.notify_success("Resultados, Plotly y Q(T) guardados correctamente.")

        except Exception as e:
            self.log_species(f"[ERROR] No se pudieron guardar los resultados: {e}")
            QMessageBox.critical(self, "Error", str(e))

    def save_species_latex_results(self):
        try:
            base_name = self._make_safe_output_name(
                self.species_output_input.text(),
                "resultados_especies"
            )

            out_dir = SPECIES_LATEX_DIR
            out_dir.mkdir(parents=True, exist_ok=True)

            main_df = self._get_current_species_main_view_df()
            topk_df = self._get_current_species_topk_view_df()

            main_df = self._filter_dataframe_by_visible_columns(main_df, self.species_table)
            topk_df = self._filter_dataframe_by_visible_columns(topk_df, self.species_topk_table)

            generated_files = []

            if main_df is not None and not main_df.empty:
                main_path = out_dir / f"{base_name}_resultados_principales.tex"
                self._export_dataframe_to_latex(
                    main_df,
                    main_path,
                    caption="Resultados principales del buscador de especies",
                    label="tab:species_main",
                )
                generated_files.append(str(main_path))
                self.log_species(f"[OK] LaTeX generado: {main_path}")

            if topk_df is not None and not topk_df.empty:
                topk_path = out_dir / f"{base_name}_topk.tex"
                self._export_dataframe_to_latex(
                    topk_df,
                    topk_path,
                    caption="Tabla TOP-K del buscador de especies",
                    label="tab:species_topk",
                )
                generated_files.append(str(topk_path))
                self.log_species(f"[OK] LaTeX generado: {topk_path}")

            if not generated_files:
                QMessageBox.warning(self, "LaTeX", "No hay tablas visibles para exportar.")
                return

            self.notify_success(
                "Tablas LaTeX del buscador de especies guardadas correctamente."
            )

        except Exception as e:
            self.log_species(f"[ERROR] {e}")
            QMessageBox.critical(self, "Error LaTeX", str(e))

    def save_column_density_latex_results(self):
        try:
            base_name = self._make_safe_output_name(
                self.species_output_input.text(),
                "column_density"
            )

            out_dir = COLUMN_DENSITY_LATEX_DIR
            out_dir.mkdir(parents=True, exist_ok=True)

            source_df = self._filter_column_density_dataframe(self.column_density_source_df)
            vasy_df = self._filter_column_density_dataframe(self.column_density_vasyunina_df)
            sanh_df = self._filter_column_density_dataframe(self.column_density_sanhueza_df)

            source_df = self._filter_dataframe_by_visible_columns(source_df, self.column_density_source_table)
            vasy_df = self._filter_dataframe_by_visible_columns(vasy_df, self.vasyunina_results_table)
            sanh_df = self._filter_dataframe_by_visible_columns(sanh_df, self.sanhueza_results_table)

            generated_files = []

            if source_df is not None and not source_df.empty:
                path_source = out_dir / f"{base_name}_fuente.tex"
                self._export_dataframe_to_latex(
                    source_df,
                    path_source,
                    caption="Tabla fuente para densidad de columna",
                    label="tab:cd_source",
                )
                generated_files.append(str(path_source))
                self.log_column_density(f"[OK] LaTeX generado: {path_source}")

            if vasy_df is not None and not vasy_df.empty:
                path_vasy = out_dir / f"{base_name}_mod.tex"
                self._export_dataframe_to_latex(
                    vasy_df,
                    path_vasy,
                    caption="Resultados del método ópticamente delgado (MOD)",
                    label="tab:cd_mod",
                )
                generated_files.append(str(path_vasy))
                self.log_column_density(f"[OK] LaTeX generado: {path_vasy}")

            if sanh_df is not None and not sanh_df.empty:
                path_sanh = out_dir / f"{base_name}_mth.tex"
                self._export_dataframe_to_latex(
                    sanh_df,
                    path_sanh,
                    caption="Resultados del método de transiciones hiperfinas (MTH)",
                    label="tab:cd_mth",
                )
                generated_files.append(str(path_sanh))
                self.log_column_density(f"[OK] LaTeX generado: {path_sanh}")

            if not generated_files:
                QMessageBox.warning(self, "LaTeX", "No hay tablas visibles para exportar.")
                return

            self.notify_success(
                "Tablas LaTeX de densidad de columna guardadas correctamente."
            )

        except Exception as e:
            self.log_column_density(f"[ERROR] {e}")
            QMessageBox.critical(self, "Error LaTeX", str(e))

    def _open_folder(self, path: Path):
        try:
            path.mkdir(parents=True, exist_ok=True)

            open_folder_in_system(path)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir la carpeta:\n{e}")

    def export_column_density_tables(self):
        """Export available M3 OTM/MOD and HTM/MTH tables using M3 settings."""
        en = self.ui_language == "en"
        datasets = []
        mod_df = self.column_density_vasyunina_filtered_df if self.column_density_filter_active and self.column_density_vasyunina_filtered_df is not None else self.column_density_vasyunina_df
        mth_df = self.column_density_sanhueza_filtered_df if self.column_density_filter_active and self.column_density_sanhueza_filtered_df is not None else self.column_density_sanhueza_df
        if mod_df is not None and not mod_df.empty:
            datasets.append(("otm" if en else "mod", self._filter_dataframe_by_visible_columns(mod_df, self.vasyunina_results_table), "M3 OTM results" if en else "Resultados M3 MOD"))
        if mth_df is not None and not mth_df.empty:
            datasets.append(("htm" if en else "mth", self._filter_dataframe_by_visible_columns(mth_df, self.sanhueza_results_table), "M3 HTM results" if en else "Resultados M3 MTH"))
        datasets = [(kind, df, title) for kind, df, title in datasets if df is not None and not df.empty]
        if not datasets:
            self.notify_info("Run OTM or HTM first." if en else "Ejecuta primero MOD o MTH.")
            return
        formats = list(getattr(self, "m3_table_export_formats", None) or [])
        if not formats:
            self.notify_info("Select M3 table formats in Settings." if en else "Selecciona formatos de tabla de M3 en Configuración.")
            return
        COLUMN_DENSITY_TABLES_DIR.mkdir(parents=True, exist_ok=True)
        base = self._module_output_stem("M3", self.species_output_input.text() or "m3_column_density")
        decimals = max(0, min(10, int(getattr(self, "table_decimal_places", 3))))
        made=[]; failed=[]
        for kind, df, title in datasets:
            df = self._friendly_source_dataframe(df.copy())
            for fmt in formats:
                try:
                    folder = COLUMN_DENSITY_TABLES_DIR / fmt.upper(); folder.mkdir(parents=True, exist_ok=True)
                    ext = "tex" if fmt == "latex" else fmt
                    path = _unique_output_path(folder / f"{base}_{kind}.{ext}")
                    self._write_m2_table_file(df, path, fmt, title, decimals)
                    made.append(path)
                except Exception as exc:
                    failed.append(f"{kind}/{fmt}: {exc}")
        self.log_column_density((f"[OK] Exported M3 table files: {len(made)}" if en else f"[OK] Archivos de tabla M3 exportados: {len(made)}"))
        msg = (f"{len(made)} M3 table file(s) exported." if en else f"Se exportaron {len(made)} archivo(s) de tabla M3.")
        if failed:
            msg += "\n\n" + ("Unavailable formats:" if en else "Formatos no disponibles:") + "\n" + "\n".join(failed[:12])
        self.notify("M3 tables" if en else "Tablas M3", msg, duration_ms=10000)

    def export_column_density_spectra(self):
        """Generate and export M3 final spectra with OTM/HTM hover metadata."""
        en = self.ui_language == "en"
        has_mod = self.column_density_vasyunina_df is not None and not self.column_density_vasyunina_df.empty
        has_mth = self.column_density_sanhueza_df is not None and not self.column_density_sanhueza_df.empty
        if not (has_mod or has_mth):
            self.notify_info("Run OTM or HTM first." if en else "Ejecuta primero MOD o MTH.")
            return
        formats = list(getattr(self, "m3_plot_export_formats", None) or [])
        if not formats:
            self.notify_info("Select M3 spectrum formats in Settings." if en else "Selecciona formatos de espectro de M3 en Configuración.")
            return
        cache = self._prepare_species_final_sources(force=True)
        if not cache:
            self.notify_info("No spectrum is available for M3." if en else "No hay un espectro disponible para M3.")
            return
        products = {}
        for source_name in list(cache.keys()):
            raw = self._column_density_final_figure_provider(source_name, self.species_final_label_mode)
            if raw:
                products[source_name] = raw
        if not products:
            self.notify_info("No M3 final spectra could be generated." if en else "No se pudieron generar espectros finales de M3.")
            return
        from plotly import io as pio
        root = COLUMN_DENSITY_GRAPHICS_DIR / "spectra"; root.mkdir(parents=True, exist_ok=True)
        made=[]; failed=[]
        for label, raw in products.items():
            safe = self._make_safe_output_name(label, "M3_spectrum")
            fig = pio.from_json(raw)
            for fmt in formats:
                try:
                    folder = root / fmt.upper(); folder.mkdir(parents=True, exist_ok=True)
                    stem = f"M3_spectrum_{safe}"
                    label_prefix = self._module_save_label("M3")
                    if label_prefix and not stem.casefold().startswith(label_prefix.casefold()):
                        stem = f"{label_prefix}_{stem}"
                    path = _unique_output_path(folder / f"{stem}.{fmt}")
                    if fmt == "html":
                        fig.write_html(str(path), include_plotlyjs=True, full_html=True)
                    else:
                        fig.write_image(str(path), scale=2)
                    made.append(path)
                except Exception as exc:
                    failed.append(f"{label}/{fmt}: {exc}")
        self.log_column_density((f"[OK] Exported M3 spectrum files: {len(made)}" if en else f"[OK] Archivos de espectro M3 exportados: {len(made)}"))
        msg = (f"{len(made)} M3 spectrum file(s) exported." if en else f"Se exportaron {len(made)} archivo(s) de espectro M3.")
        if failed:
            msg += "\n\n" + ("Unavailable formats:" if en else "Formatos no disponibles:") + "\n" + "\n".join(failed[:10])
        self.notify("M3 spectra" if en else "Espectros M3", msg, duration_ms=10000)

    def save_vasyunina_results(self, silent: bool = False):
        if self.column_density_source_df is None or self.column_density_source_df.empty:
            if not silent: QMessageBox.warning(self, "Aviso", "No hay datos fuente para guardar MOD.")
            return False

        if self.column_density_vasyunina_df is None or self.column_density_vasyunina_df.empty:
            if not silent: QMessageBox.warning(self, "Aviso", "Primero ejecuta MOD.")
            return False

        try:
            output_name = "column_density_mod"
            if self.species_output_input.text().strip():
                output_name = f"{self.species_output_input.text().strip()}_mod"

            source_df_to_save = (
                self.column_density_vasyunina_filtered_df
                if self.column_density_filter_active and self.column_density_vasyunina_filtered_df is not None
                else self.column_density_vasyunina_df
            )

            df_to_save = self._filter_dataframe_by_visible_columns(
                source_df_to_save,
                self.vasyunina_results_table,
            )

            if df_to_save is None or df_to_save.empty:
                QMessageBox.warning(self, "MOD", "No hay columnas visibles para guardar.")
                return

            from czspec.logic.vasyunina import ensure_dir, sanitize_name, _save_df_both

            out_dir = ensure_dir(VASYUNINA_OUTPUT_DIR)
            base_name = sanitize_name(output_name)
            out_base = out_dir / base_name

            sci_cols = [c for c in df_to_save.columns if c.startswith("N_tot_")]

            csv_path, html_path = _save_df_both(
                df_to_save,
                str(out_base),
                ndigits=4,
                index=False,
                html_title="Resultados de densidad de columna — MOD",
                html_caption="Columnas exportadas según la vista actual de la tabla",
                sci_cols=sci_cols,
            )

            self.log_column_density(f"[OK] CSV generado: {csv_path}")
            self.log_column_density(f"[OK] HTML generado: {html_path}")

            if not silent:
                self.notify_success("Resultados MOD guardados correctamente." if self.ui_language != "en" else "OTM results saved successfully.")
            return True

        except Exception as e:
            self.log_column_density(f"[ERROR] {e}")
            if not silent: QMessageBox.critical(self, "Error en MOD", str(e))
            return False


    def save_sanhueza_results(self, silent: bool = False):
        if self.column_density_source_df is None or self.column_density_source_df.empty:
            if not silent: QMessageBox.warning(self, "Aviso", "No hay datos fuente para guardar MTH.")
            return False

        if self.column_density_sanhueza_df is None or self.column_density_sanhueza_df.empty:
            if not silent: QMessageBox.warning(self, "Aviso", "Primero ejecuta MTH.")
            return False

        try:
            output_name = "column_density_mth"
            if self.species_output_input.text().strip():
                output_name = f"{self.species_output_input.text().strip()}_mth"

            source_df_to_save = (
                self.column_density_sanhueza_filtered_df
                if self.column_density_filter_active and self.column_density_sanhueza_filtered_df is not None
                else self.column_density_sanhueza_df
            )

            df_to_save = self._filter_dataframe_by_visible_columns(
                source_df_to_save,
                self.sanhueza_results_table,
            )

            if df_to_save is None or df_to_save.empty:
                QMessageBox.warning(self, "MTH", "No hay columnas visibles para guardar.")
                return

            from czspec.logic.sanhueza import ensure_dir, sanitize_name, _save_df_both, SCI_COLS

            out_dir = ensure_dir(SANHUEZA_OUTPUT_DIR)
            base_name = sanitize_name(output_name)
            out_base = out_dir / base_name

            csv_path, html_path = _save_df_both(
                df_to_save,
                str(out_base),
                ndigits=4,
                index=False,
                html_title="Resultados de densidad de columna — MTH",
                html_caption="Columnas exportadas según la vista actual de la tabla",
                sci_cols=SCI_COLS,
            )

            self.log_column_density(f"[OK] CSV generado: {csv_path}")
            self.log_column_density(f"[OK] HTML generado: {html_path}")

            if not silent:
                self.notify_success("Resultados MTH guardados correctamente." if self.ui_language != "en" else "HTM results saved successfully.")
            return True

        except Exception as e:
            self.log_column_density(f"[ERROR] {e}")
            if not silent: QMessageBox.critical(self, "Error en MTH", str(e))
            return False

    def open_species_tables_folder(self):
        SPECIES_TABLES_DIR.mkdir(parents=True, exist_ok=True)
        open_folder_in_system(SPECIES_TABLES_DIR)

    def open_species_plotly_folder(self):
        path = SPECIES_GRAPHICS_DIR / "spectra"; path.mkdir(parents=True, exist_ok=True)
        open_folder_in_system(path)

    def open_species_qt_folder(self):
        path = SPECIES_GRAPHICS_DIR / "q_t"; path.mkdir(parents=True, exist_ok=True)
        open_folder_in_system(path)

    def open_species_figures_folder(self):
        SPECIES_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        open_folder_in_system(SPECIES_IMAGES_DIR)

    def open_fullscreen_plot(self):
        plot_json = self.current_plot_json
        mode = self.current_view_mode or "interactive"

        if not plot_json:
            self.notify_info("No hay gráfica disponible.")
            return

        self.fullscreen_dialog = FullScreenPlotDialog(plot_json, mode, self)
        self.fullscreen_dialog.open_fullscreen()

    def save_current_plot_image(self):
        if not self.selected_file:
            self.notify_info("No hay archivo base seleccionado.")
            return

        if not self.current_plot_json:
            self.notify_info("No hay gráfica para guardar.")
            return

        def _after_capture(captured_json):
            if not captured_json:
                QMessageBox.warning(self, "Advertencia", "No se pudo capturar la vista actual.")
                return

            try:
                PEAK_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
                base_name = (
                    f"sesion_{len(self.selected_files)}_espectros"
                    if self.current_view_mode == "comparison"
                    else Path(self.selected_file).stem
                )
                custom_name = str(getattr(self, "m1_image_name_input", QLineEdit()).text() if hasattr(self, "m1_image_name_input") else "").strip()
                if custom_name:
                    safe = self._make_safe_output_name(Path(custom_name).stem, base_name)
                    output_path = _unique_output_path(PEAK_IMAGES_DIR / f"{safe}.png")
                else:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = PEAK_IMAGES_DIR / f"{base_name}_{self.current_view_mode}_{timestamp}.png"
                save_plot_json_to_png(captured_json, str(output_path))
                self.log(f"[OK] Imagen guardada: {output_path}")
                self.notify_success(f"Imagen guardada en:\n{output_path}")
            except Exception as e:
                self.log(f"[ERROR] No se pudo guardar la imagen: {e}")
                QMessageBox.critical(self, "Error", str(e))

        self.capture_current_plot_json(_after_capture)

    def _m1_export_base_name(self, file_path: str | None = None) -> str:
        path = str(file_path or self.selected_file or "analisis")
        if path in self.spectrum_session:
            label = self.spectrum_session[path].get("display_name") or Path(path).stem
        else:
            label = Path(path).stem
        return self._make_safe_output_name(str(label), "analisis")

    def _m1_export_source_name(self, file_path: str, state: dict | None = None) -> str:
        state = state or self.spectrum_session.get(file_path, {})
        meta = dict(state.get("source_metadata") or {})
        value = meta.get("canonical_name") or meta.get("raw_source_name") or meta.get("source")
        if not value:
            label = str(state.get("display_name") or Path(file_path).stem)
            value = label.split("·", 1)[0].strip()
        return self._make_safe_output_name(str(value or "unknown_source"), "unknown_source")

    def _m1_table_glossary(self, columns) -> list[tuple[str, str]]:
        en = self.ui_language == "en"
        base = {
            "Line": "Sequential M1 line identifier." if en else "Identificador secuencial de la línea en M1.",
            "Source": "Source identity associated with the spectrum." if en else "Identidad de la fuente asociada al espectro.",
            "ν[MHz]": "Fitted line-center frequency in MHz." if en else "Frecuencia central ajustada de la línea en MHz.",
            "v_LSR[km/s]": "Line-center velocity in the LSR frame when a valid spectral reference is available." if en else "Velocidad del centro de línea en el marco LSR cuando existe una referencia espectral válida.",
            "T_A [K]": "Fitted peak intensity in the current calibrated scale." if en else "Intensidad pico ajustada en la escala de calibración activa.",
            "Δv [Km/s]": "FWHM of the fitted component." if en else "FWHM de la componente ajustada.",
            "σ_Δv [Km/s]": "Estimated 1σ uncertainty of FWHM." if en else "Incertidumbre 1σ estimada del FWHM.",
            "IntInt [K*Km/s]": "Integrated intensity of the fitted component." if en else "Intensidad integrada de la componente ajustada.",
            "σ_IntInt [K*Km/s]": "Estimated 1σ uncertainty of integrated intensity." if en else "Incertidumbre 1σ estimada de la intensidad integrada.",
            "GOI": ("Group/individual flag: Individual means the component was fitted alone; Group means it belongs to a simultaneous multi-component complex."
                    if en else "Indicador grupo/individual: Individual significa que la componente se ajustó de forma aislada; Grupo indica un complejo con ajuste multicomponente simultáneo."),
            "Ajuste": ("Applied profile. Gaussian: I=I0 exp[-(ν-ν0)^2/(2σ^2)]. Lorentzian: I=I0 γ²/[(ν-ν0)²+γ²]. Voigt: convolution of Gaussian and Lorentzian components, normalized to fitted peak intensity."
                       if en else "Perfil aplicado. Gaussiano: I=I0 exp[-(ν-ν0)^2/(2σ²)]. Lorentziano: I=I0 γ²/[(ν-ν0)²+γ²]. Voigt: convolución de las componentes gaussiana y lorentziana, normalizada a la intensidad pico ajustada."),
            "SNR": "Peak signal-to-noise ratio using the local robust noise estimate." if en else "Relación señal-ruido del pico usando la estimación robusta local del ruido.",
            "Confianza": ("Diagnostic confidence class assigned from the detection/fitting quality checks."
                           if en else "Clase diagnóstica de confianza asignada a partir de los controles de detección y ajuste."),
            "Tipo": "Emission or absorption classification." if en else "Clasificación de la componente como emisión o absorción.",
            "Origen": ("Detection provenance: auto = initial automatic search; residual = recovered in the residual after a previous fit; manual = explicitly added by the user."
                        if en else "Procedencia de la detección: auto = búsqueda automática inicial; residual = recuperada en el residual tras un ajuste previo; manual = agregada explícitamente por el usuario."),
            "Semilla_ν[MHz]": "Seed frequency used by the stable manual-editing state." if en else "Frecuencia semilla usada por el estado estable de edición manual.",
            "BIC_grupo": "Bayesian Information Criterion of the accepted group model." if en else "Criterio de Información Bayesiano del modelo de grupo aceptado.",
            "AIC_grupo": "Akaike Information Criterion of the accepted group model." if en else "Criterio de Información de Akaike del modelo de grupo aceptado.",
            "ΔBIC_última": "Last BIC improvement used by the iterative deblending decision." if en else "Última mejora de BIC usada en la decisión iterativa de deblending.",
        }
        return [(str(col), base.get(str(col), ("M1 result column." if en else "Columna de resultados de M1."))) for col in columns]

    def _write_m1_html_table(self, df: pd.DataFrame, path: Path, title: str, decimals: int | None = None):
        import html
        glossary = self._m1_table_glossary(df.columns)
        if decimals is None:
            decimals = int(getattr(self, "table_decimal_places", 3))
        decimals = max(0, min(10, int(decimals)))
        table_html = df.to_html(
            index=False, border=0, classes="czspec-table", na_rep="—", escape=True,
            float_format=lambda value: f"{float(value):.{decimals}f}",
        )
        glossary_html = "".join(
            f"<dt><code>{html.escape(name)}</code></dt><dd>{html.escape(desc)}</dd>"
            for name, desc in glossary
        )
        document = f'''<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font-family:Inter,Arial,sans-serif;margin:28px;color:#172033}}h1{{font-size:22px}}.wrap{{overflow:auto;max-height:72vh;border:1px solid #dbe2ea;border-radius:8px}}table{{border-collapse:collapse;width:max-content;min-width:100%}}th,td{{padding:7px 10px;border-bottom:1px solid #e7ecf2;white-space:nowrap}}th{{position:sticky;top:0;background:#f6f8fb;z-index:2;text-align:left}}tr:nth-child(even){{background:#fbfcfe}}h2{{margin-top:28px;font-size:18px}}dt{{font-weight:700;margin-top:10px}}dd{{margin-left:0;color:#475569;line-height:1.45}}</style></head><body>
<h1>{html.escape(title)}</h1><div class="wrap">{table_html}</div><h2>{'Column glossary' if self.ui_language=='en' else 'Índice de columnas'}</h2><dl>{glossary_html}</dl></body></html>'''
        path.write_text(document, encoding="utf-8")

    @staticmethod
    def _latex_escape_text(value: str) -> str:
        repl = {"\\":r"\textbackslash{}", "&":r"\&", "%":r"\%", "$":r"\$", "#":r"\#", "_":r"\_", "{":r"\{", "}":r"\}", "~":r"\textasciitilde{}", "^":r"\textasciicircum{}"}
        return "".join(repl.get(ch, ch) for ch in str(value))

    def _write_m1_standalone_latex(self,df:pd.DataFrame,path:Path,caption:str,decimals:int|None=None):
        """Genera un .tex standalone sin depender de pandas Styler/Jinja2."""
        if decimals is None: decimals=int(getattr(self,"table_decimal_places",3))
        decimals=max(0,min(10,int(decimals)))
        caption_tex=self._latex_escape_text(caption)
        header_map={
            "ν[MHz]":r"$\nu$ [MHz]","v_LSR[km/s]":r"$v_{\rm LSR}$ [km s$^{-1}$]",
            "Δv_fuente[km/s]":r"$\Delta v_{\rm fuente}$ [km s$^{-1}$]","T_A [K]":r"$T_{\rm A}$ [K]",
            "Δv [Km/s]":r"$\Delta v$ [km s$^{-1}$]","σ_Δv [Km/s]":r"$\sigma_{\Delta v}$ [km s$^{-1}$]",
            "IntInt [K*Km/s]":r"$\int T\,dv$ [K km s$^{-1}$]","σ_IntInt [K*Km/s]":r"$\sigma_{\int Tdv}$ [K km s$^{-1}$]",
            "Semilla_ν[MHz]":r"$\nu_{\rm seed}$ [MHz]","Desplazamiento_centro[km/s]":r"$\Delta v_{\rm centro}$ [km s$^{-1}$]","ΔBIC_última":r"$\Delta$BIC final",
        }
        def fmt(v):
            if pd.isna(v):return "--"
            if isinstance(v,(float,np.floating)):return f"{float(v):.{decimals}f}"
            if isinstance(v,(int,np.integer)):return str(int(v))
            return self._latex_escape_text(str(v))
        headers=[header_map.get(str(c),self._latex_escape_text(str(c))) for c in df.columns]
        n=max(1,len(headers)); landscape=n>8
        # longtable con columnas centradas y ancho natural; no necesita Jinja2.
        colspec="@{}"+" ".join(["c"]*n)+"@{}"
        label_seed=re.sub(r"[^a-zA-Z0-9]+","_",path.stem).strip("_").lower()[:48] or "czspec_m1"
        rows=[]
        rows.append(r"\begin{longtable}{"+colspec+"}")
        rows.append(r"\caption{"+caption_tex+r"}\label{tab:"+label_seed+r"}\\")
        rows.append(r"\toprule")
        rows.append(" & ".join(headers)+r" \\")
        rows.append(r"\midrule")
        rows.append(r"\endfirsthead")
        rows.append(r"\toprule")
        rows.append(" & ".join(headers)+r" \\")
        rows.append(r"\midrule")
        rows.append(r"\endhead")
        for values in df.itertuples(index=False,name=None):rows.append(" & ".join(fmt(v) for v in values)+r" \\")
        rows.append(r"\bottomrule")
        rows.append(r"\end{longtable}")
        note=(r"\noindent\textit{Nota:} Tabla exportada por CZSpec M1. Las columnas fueron seleccionadas por el usuario; la representación numérica respeta la precisión decimal configurada.\par\medskip" if self.ui_language=="es" else r"\noindent\textit{Note:} Table exported by CZSpec M1. Columns were selected by the user; numeric display follows the configured decimal precision.\par\medskip")
        content=("\\documentclass[10pt]{article}\n\\usepackage[margin=1.6cm]{geometry}\n\\usepackage{booktabs,longtable,array}\n\\usepackage{pdflscape}\n\\usepackage[T1]{fontenc}\n\\usepackage[utf8]{inputenc}\n\\begin{document}\n")
        if landscape:content+="\\begin{landscape}\n"
        content+="\n".join(rows)+"\n"+note+"\n"
        if landscape:content+="\\end{landscape}\n"
        content+="\\end{document}\n";path.write_text(content,encoding="utf-8")

    def _m1_export_session_name(self, source: str) -> str:
        label = str(getattr(self, "save_label_input", None).text() if getattr(self, "save_label_input", None) is not None else "").strip()
        base = " ".join(part for part in (source.strip(), label) if part)
        base = re.sub(r'[\\/:*?"<>|]+', "_", base).strip() or "CZSpec"
        roots = (PEAK_TABLES_DIR, PEAK_GRAPHICS_DIR)
        if not any((root / base).exists() for root in roots):
            return base
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        candidate = f"{base} {stamp}"
        i = 2
        while any((root / candidate).exists() for root in roots):
            candidate = f"{base} ({i})"; i += 1
        return candidate

    def export_table_results(self):
        analyzed = []
        for file_path in self.selected_files or ([self.selected_file] if self.selected_file else []):
            state = self.spectrum_session.get(file_path, {})
            result = state.get("last_result") or {}
            df = result.get("results_df")
            if df is not None and not df.empty:
                analyzed.append((file_path, state, df))
        if not analyzed:
            self.notify_info("Run an analysis first." if self.ui_language == "en" else "Primero ejecuta un análisis.")
            return
        formats = list(self.table_export_formats or ["csv", "html", "latex"])
        if not formats:
            self.notify_info("Select at least one table format in Settings." if self.ui_language == "en" else "Selecciona al menos un formato de tabla en Configuración.")
            return
        export_columns = list(analyzed[0][2].columns)
        dialog = DataFrameColumnExportDialog(export_columns, language=self.ui_language, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        export_columns = dialog.selected_columns()
        decimals = max(0, min(10, int(getattr(self, "table_decimal_places", 3))))
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        made, failed = [], []
        session_names = {}
        for file_path, state, df in analyzed:
            cols = [c for c in export_columns if c in df.columns]
            export_df = df[cols].copy()
            # Keep numeric columns numeric for XLSX/ODS/JSON/XML while applying
            # the user-requested precision consistently across every format.
            for col in export_df.columns:
                if pd.api.types.is_float_dtype(export_df[col]):
                    export_df[col] = export_df[col].round(decimals)
            base = self._m1_export_base_name(file_path)
            source = self._m1_export_source_name(file_path, state)
            session_names.setdefault(source, self._m1_export_session_name(source))
            source = session_names[source]
            title = ("M1 spectral-line results — " if self.ui_language == "en" else "Resultados de líneas espectrales M1 — ") + self._spectrum_display_name(file_path)
            for fmt in formats:
                try:
                    fmt_dir = PEAK_TABLES_DIR / source / fmt.upper()
                    fmt_dir.mkdir(parents=True, exist_ok=True)
                    ext = "tex" if fmt == "latex" else fmt
                    path = fmt_dir / f"{base}_M1_{stamp}.{ext}"
                    float_format = f"%.{decimals}f"
                    if fmt == "csv": export_df.to_csv(path, index=False, encoding="utf-8", float_format=float_format)
                    elif fmt == "tsv": export_df.to_csv(path, index=False, sep="\t", encoding="utf-8", float_format=float_format)
                    elif fmt == "dsv": export_df.to_csv(path, index=False, sep=";", encoding="utf-8", float_format=float_format)
                    elif fmt == "txt": path.write_text(export_df.to_string(index=False, float_format=lambda v: f"{float(v):.{decimals}f}"), encoding="utf-8")
                    elif fmt == "json": export_df.to_json(path, orient="records", indent=2, force_ascii=False, double_precision=decimals)
                    elif fmt == "xml": export_df.to_xml(path, index=False, root_name="czspec_m1_results", row_name="line")
                    elif fmt == "xlsx": export_df.to_excel(path, index=False, float_format=float_format)
                    elif fmt == "ods": export_df.to_excel(path, index=False, engine="odf", float_format=float_format)
                    elif fmt == "html": self._write_m1_html_table(export_df, path, title, decimals=decimals)
                    elif fmt == "latex":
                        self._write_m1_standalone_latex(export_df, path, title, decimals=decimals)
                    else: continue
                    made.append(path)
                except Exception as exc:
                    failed.append(f"{base}/{fmt}: {exc}")
        if made:
            self.log("[OK] " + ("Tables exported: " if self.ui_language=="en" else "Tablas exportadas: ") + str(len(made)))
        message = (f"{len(made)} table file(s) created under:\n{PEAK_TABLES_DIR}" if self.ui_language=="en" else f"Se generaron {len(made)} archivo(s) de tabla bajo:\n{PEAK_TABLES_DIR}")
        if failed: message += "\n\n" + ("Unavailable formats:" if self.ui_language=="en" else "Formatos no disponibles:") + "\n" + "\n".join(failed[:12])
        self.notify("Export Tables" if self.ui_language=="en" else "Exportar tablas", message, duration_ms=10000)

    def _plot_export_variants(self):
        variants=[]
        for file_path in self.selected_files or ([self.selected_file] if self.selected_file else []):
            state=self.spectrum_session.get(file_path, {})
            if state.get("raw_plot_json"):
                variants.append((file_path, state, "raw", state["raw_plot_json"], False))
            analyzed=state.get("analyzed_plot_json") or (state.get("last_result") or {}).get("plot_json")
            if analyzed:
                variants.append((file_path, state, "with_legend", analyzed, True))
                variants.append((file_path, state, "no_legend", analyzed, False))
        return variants

    def _prepare_static_plot_json(self, plot_json: str, state: dict, showlegend: bool) -> str:
        configured = self._configure_m1_plot_json(plot_json, state=state)
        fig = json.loads(configured)
        layout=fig.setdefault("layout", {})
        layout["showlegend"] = bool(showlegend)
        margin=dict(layout.get("margin") or {}); margin["r"] = 220 if showlegend else 35; layout["margin"] = margin
        return json.dumps(fig, ensure_ascii=False)

    def export_plots_results(self):
        variants=self._plot_export_variants()
        if not variants:
            self.notify_info("No plots are available to export." if self.ui_language=="en" else "No hay gráficas disponibles para exportar.");return
        formats=list(self.plot_export_formats or ["html","png","jpg","pdf"])
        if not formats:
            self.notify_info("Select at least one plot format in Settings." if self.ui_language=="en" else "Selecciona al menos un formato de gráfica en Configuración.");return
        PEAK_GRAPHICS_DIR.mkdir(parents=True,exist_ok=True);stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
        session_names={}
        # Preparar el JSON configurado en el hilo GUI; la escritura pesada se delega.
        jobs=[]
        for file_path,state,variant,canonical,showlegend in variants:
            base=self._m1_export_base_name(file_path);source0=self._m1_export_source_name(file_path,state);session_names.setdefault(source0,self._m1_export_session_name(source0));source=session_names[source0];prepared=self._prepare_static_plot_json(canonical,state,showlegend)
            for fmt in formats:jobs.append((source,base,variant,fmt,prepared))
        def work(progress):
            made=[];failed=[];total=max(1,len(jobs))
            for i,(source,base,variant,fmt,prepared) in enumerate(jobs,1):
                progress(int(100*(i-1)/total),(f"Exportando gráfica {i}/{total}" if self.ui_language=="es" else f"Exporting plot {i}/{total}"))
                try:
                    fmt_dir=PEAK_GRAPHICS_DIR/source/fmt.upper();fmt_dir.mkdir(parents=True,exist_ok=True)
                    path=fmt_dir/f"{base}_{variant}_{stamp}.{fmt}"
                    if fmt=="html":
                        from plotly import io as pio
                        pio.from_json(prepared).write_html(str(path),include_plotlyjs=True,full_html=True)
                    else:save_plot_json_to_file(prepared,str(path),scale=2.0)
                    made.append(str(path))
                except Exception as exc:failed.append(f"{base}/{variant}/{fmt}: {exc}")
            progress(100,"Exportación terminada" if self.ui_language=="es" else "Export complete");return {"made":made,"failed":failed}
        def on_success(payload):
            made=payload.get("made",[]);failed=payload.get("failed",[])
            if made:self.log("[OK] "+("Plots exported: " if self.ui_language=="en" else "Gráficas exportadas: ")+str(len(made)))
            message=(f"{len(made)} plot file(s) created in:\n{PEAK_GRAPHICS_DIR}" if self.ui_language=="en" else f"Se generaron {len(made)} archivo(s) de gráfica en:\n{PEAK_GRAPHICS_DIR}")
            if failed:message+="\n\n"+("Unavailable formats:" if self.ui_language=="en" else "Formatos no disponibles:")+"\n"+"\n".join(failed[:12])
            self.notify("Export Plots" if self.ui_language=="en" else "Exportar gráficas",message,duration_ms=12000)
        def on_error(message,details):self.log(f"[ERROR] Plot export: {message}");self.log(details);self.notify("Error",message)
        self._start_background_task("export_m1_plots",work,on_success,on_error=on_error,busy_widgets=(self.export_html_button,),status_message="Exportando gráficas..." if self.ui_language=="es" else "Exporting plots...")

    # Aliases retained for external integrations from earlier alpha builds.
    def export_csv_results(self):
        self.export_table_results()

    def export_html_results(self):
        self.export_plots_results()

    def open_tables_folder(self):
        try:
            open_folder_in_system(TABLES_DIR)
            self.log(f"[OK] Carpeta de tablas abierta: {TABLES_DIR}")
        except Exception as e:
            self.log(f"[ERROR] No se pudo abrir la carpeta de tablas: {e}")
            QMessageBox.critical(self, "Error", str(e))

    def open_images_folder(self):
        try:
            open_folder_in_system(IMAGES_DIR)
            self.log(f"[OK] Carpeta de imágenes abierta: {IMAGES_DIR}")
        except Exception as e:
            self.log(f"[ERROR] No se pudo abrir la carpeta de imágenes: {e}")
            QMessageBox.critical(self, "Error", str(e))

    def open_species_results_folder(self):
        SPECIES_SEARCH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        try:
            open_folder_in_system(SPECIES_SEARCH_OUTPUT_DIR)
            self.log_species(f"[OK] M2 output folder: {SPECIES_SEARCH_OUTPUT_DIR}")
        except Exception as e:
            self.log_species(f"[ERROR] Could not open M2 output folder: {e}")
            QMessageBox.critical(self, "Error", str(e))

    def open_vasyunina_folder(self):
        path = VASYUNINA_OUTPUT_DIR
        if path.exists():
            open_folder_in_system(path)
        else:
            QMessageBox.warning(self, "Aviso", "No existe todavía la carpeta MOD.")


    def open_sanhueza_folder(self):
        path = SANHUEZA_OUTPUT_DIR
        if path.exists():
            open_folder_in_system(path)
        else:
            QMessageBox.warning(self, "Aviso", "No existe todavía la carpeta MTH.")
    
    
def main():
    from czspec.app import main as run_application

    return run_application()


if __name__ == "__main__":
    main()
