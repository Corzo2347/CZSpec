"""Explorador gráfico genérico para las tablas científicas de M2 y M3."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from PySide6.QtCore import Qt, QUrl, QSettings, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QSpinBox,
    QTabWidget,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from czspec.paths import IMAGES_DIR
from czspec.table_plot_data import (
    numeric_series,
    plot_axis_columns,
    uncertainty_column,
    with_scientific_series,
)
from czspec.table_schema import column_display_name, column_tooltip
from czspec.utils.plotly_runtime import prepare_plotly_view_file


PALETTES = {
    "CZSpec": ["#1D6EEB", "#E67E22", "#16A085", "#8E5CE6", "#D64550", "#2D3436"],
    "Astronomía": ["#0B132B", "#1C77C3", "#39A9DB", "#F4D35E", "#EE964B", "#C44536"],
    "Alto contraste": ["#000000", "#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00"],
}


class WheelSafeComboBox(QComboBox):
    """Deja que la rueda desplace el panel sin cambiar una selección."""

    def wheelEvent(self, event):
        event.ignore()


class SeriesColorDialog(QDialog):
    def __init__(self, series_names, colors, language="es", parent=None):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle("Colores de las series" if language == "es" else "Series colors")
        self.colors = dict(colors)
        self.buttons = {}
        layout = QVBoxLayout(self)
        form = QFormLayout()
        for name in series_names:
            button = QPushButton(self.colors.get(name, "#1D6EEB"))
            self._style_button(button, self.colors.get(name, "#1D6EEB"))
            button.clicked.connect(lambda checked=False, n=name, b=button: self._choose(n, b))
            form.addRow(str(name), button)
            self.buttons[name] = button
        layout.addLayout(form)
        actions = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        actions.accepted.connect(self.accept)
        actions.rejected.connect(self.reject)
        layout.addWidget(actions)

    @staticmethod
    def _style_button(button, color):
        button.setStyleSheet(
            f"QPushButton {{ background: {color}; color: white; font-weight: 700; }}"
        )

    def _choose(self, name, button):
        selected = QColorDialog.getColor(QColor(self.colors.get(name, "#1D6EEB")), self)
        if selected.isValid():
            self.colors[name] = selected.name().upper()
            button.setText(self.colors[name])
            self._style_button(button, self.colors[name])


class TablePlotDialog(QDialog):
    """Permite elegir tabla, ejes, series y estilo sin modificar los DataFrame."""

    image_saved = Signal(str)

    def __init__(
        self,
        datasets: dict[str, pd.DataFrame],
        parent=None,
        default_dataset=None,
        output_directory: Path | None = None,
        language: str = "es",
        filename_prefix: str = "",
    ):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle("Explorador gráfico de tablas — CZSpec" if language == "es" else "Table plot explorer — CZSpec")
        self.setWindowModality(Qt.NonModal)
        self.resize(1120, 720)
        self.datasets = {
            name: with_scientific_series(frame)
            for name, frame in datasets.items()
            if frame is not None and not frame.empty
        }
        self.current_plot_json = None
        self.output_directory = Path(output_directory or IMAGES_DIR)
        self.filename_prefix = re.sub(r"[^A-Za-z0-9._-]+", "_", str(filename_prefix or "")).strip("._-")
        self.series_colors = {}
        self.settings = QSettings("CZSpec", "CZSpec")
        self._runtime_ready = False
        self._updating_controls = False
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(140)
        self.update_timer.timeout.connect(self.update_plot)

        root = QVBoxLayout(self)
        intro = QLabel(
            ("Elige ejes y series; las opciones avanzadas están separadas por pestañas para mantener la ventana ligera."
             if language == "es" else
             "Choose axes and series; advanced options are separated into tabs to keep the window uncluttered.")
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        splitter = QSplitter(Qt.Horizontal)
        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        controls_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        controls_scroll.setMinimumWidth(330)
        controls_scroll.setMaximumWidth(430)
        controls_scroll.setWidget(self._build_controls())
        splitter.addWidget(controls_scroll)

        self.plot_view = QWebEngineView()
        self.plot_view.setMinimumWidth(620)
        splitter.addWidget(self.plot_view)
        splitter.setSizes([360, 820])
        root.addWidget(splitter, 1)

        actions = QHBoxLayout()
        self.image_name_input = QLineEdit()
        self.image_name_input.setPlaceholderText(self._tr("Nombre de imagen (opcional)", "Image name (optional)"))
        self.image_name_input.setToolTip(self._tr(
            "Si se deja vacío se usa el título de la gráfica y la fuente; si ya existe, se añade fecha y hora.",
            "Leave blank to use the graph title and source; if it already exists, date and time are appended.",
        ))
        self.image_name_input.setMaximumWidth(300)
        self.save_button = QPushButton("Guardar imagen..." if language == "es" else "Save image...")
        self.save_button.setProperty("actionRole", "export")
        self.save_button.setEnabled(False)
        self.close_button = QPushButton("Cerrar" if language == "es" else "Close")
        self.close_button.setProperty("actionRole", "utility")
        actions.addStretch()
        actions.addWidget(self.image_name_input)
        actions.addWidget(self.save_button)
        actions.addWidget(self.close_button)
        root.addLayout(actions)

        self.dataset_combo.currentIndexChanged.connect(self._dataset_changed)
        self.group_combo.currentIndexChanged.connect(self._group_changed)
        self.swap_button.clicked.connect(self._swap_axes)
        self.plot_button.clicked.connect(self.update_plot)
        self.colors_button.clicked.connect(self._choose_series_colors)
        self.save_button.clicked.connect(self.save_image)
        self.close_button.clicked.connect(self.accept)
        self.x_combo.currentIndexChanged.connect(self._axis_changed)
        self.y_combo.currentIndexChanged.connect(self._axis_changed)
        self.order_combo.currentIndexChanged.connect(self.schedule_update)
        self.mode_combo.currentIndexChanged.connect(self._plot_type_changed)
        self.dash_combo.currentIndexChanged.connect(self.schedule_update)
        self.line_width.valueChanged.connect(self.schedule_update)
        self.marker_size.valueChanged.connect(self.schedule_update)
        self.palette_combo.currentIndexChanged.connect(self._palette_changed)
        self.legend_combo.currentIndexChanged.connect(self.schedule_update)
        self.histogram_bins.valueChanged.connect(self.schedule_update)
        self.log_x.toggled.connect(self.schedule_update)
        self.log_y.toggled.connect(self.schedule_update)
        self.group_values.itemSelectionChanged.connect(self.schedule_update)
        self.title_input.textChanged.connect(self.schedule_update)
        self.x_label_input.textChanged.connect(self.schedule_update)
        self.y_label_input.textChanged.connect(self.schedule_update)
        self.advanced_axes.toggled.connect(self._dataset_changed)
        self.error_bars.toggled.connect(self.schedule_update)

        runtime_path = prepare_plotly_view_file()
        self.plot_view.loadFinished.connect(self._runtime_loaded)
        self.plot_view.load(QUrl.fromLocalFile(str(runtime_path)))

        if default_dataset:
            index = self.dataset_combo.findText(default_dataset)
            if index >= 0:
                self.dataset_combo.setCurrentIndex(index)
        self._dataset_changed()
        QTimer.singleShot(0, self._fit_to_available_screen)

    def _fit_to_available_screen(self):
        screen = self.screen()
        if screen is None:
            return
        available = screen.availableGeometry()
        width = min(1180, max(820, int(available.width() * 0.92)))
        height = min(820, max(560, int(available.height() * 0.88)))
        self.resize(width, height)
        self.move(
            available.x() + max(0, (available.width() - width) // 2),
            available.y() + max(0, (available.height() - height) // 2),
        )

    def _tr(self, es: str, en: str) -> str:
        return en if self.language == "en" else es

    def _column_label(self, column) -> str:
        label = column_display_name(column)
        if self.language != "en":
            return label
        translations = {
            "ID de observación": "Observation ID",
            "Posición TOP-K": "TOP-K rank",
            "Especie / transición": "Species / transition",
            "Nombre químico": "Chemical name",
            "Fórmula base": "Base formula",
            "Catálogo espectroscópico": "Spectroscopic catalog",
            "ν observada [MHz]": "Observed ν [MHz]",
            "ν de reposo [MHz]": "Rest ν [MHz]",
            "Archivo fuente": "Source file",
            "VLSR de la fuente [km s⁻¹]": "Source VLSR [km s⁻¹]",
            "Velocidad de la línea [km s⁻¹]": "Line velocity [km s⁻¹]",
            "Δv respecto a VLSR [km s⁻¹]": "Δv relative to VLSR [km s⁻¹]",
            "Temperatura pico observada [K]": "Observed peak temperature [K]",
            "Amplitud pico ajustada [K]": "Fitted peak amplitude [K]",
            "Tipo de ajuste": "Fit type",
            "Perfil ajustado": "Fit profile",
            "Método": "Method",
            "Transición de referencia": "Reference transition",
            "Función de partición Q(T)": "Partition function Q(T)",
        }
        return translations.get(label, label)

    def _build_controls(self):
        panel = QWidget()
        panel.setMinimumWidth(300)
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(panel)
        tabs = QTabWidget()
        layout.addWidget(tabs, stretch=1)

        # --- Data tab -------------------------------------------------
        data_tab = QWidget(); data_layout = QVBoxLayout(data_tab)
        data_box = QGroupBox(self._tr("Datos", "Data"))
        data_form = QFormLayout(data_box)
        self.dataset_combo = WheelSafeComboBox(); self.dataset_combo.addItems(self.datasets.keys())
        self.x_combo = WheelSafeComboBox(); self.y_combo = WheelSafeComboBox(); self.group_combo = WheelSafeComboBox()
        self.order_combo = WheelSafeComboBox()
        self.order_combo.addItem(self._tr("Valor del eje X", "X-axis value"), "x")
        self.order_combo.addItem(self._tr("Valor del eje Y", "Y-axis value"), "y")
        self.order_combo.addItem(self._tr("Orden original de la tabla", "Original table order"), "table")
        self.swap_button = QPushButton(self._tr("Intercambiar X ↔ Y", "Swap X ↔ Y"))
        data_form.addRow(self._tr("Tabla:", "Table:"), self.dataset_combo)
        data_form.addRow(self._tr("Eje X:", "X axis:"), self.x_combo)
        data_form.addRow(self._tr("Eje Y:", "Y axis:"), self.y_combo)
        data_form.addRow(self._tr("Separar por:", "Group by:"), self.group_combo)
        data_form.addRow(self._tr("Conectar según:", "Connect by:"), self.order_combo)
        self.advanced_axes = QCheckBox(self._tr("Mostrar variables avanzadas e internas", "Show advanced/internal variables"))
        self.advanced_axes.setToolTip(self._tr("Añade identificadores y campos de cálculo interno a los selectores de ejes.", "Adds identifiers and internal calculation fields to the axis selectors."))
        data_form.addRow(self.advanced_axes); data_form.addRow(self.swap_button)
        data_layout.addWidget(data_box)

        selection_box = QGroupBox(self._tr("Series incluidas", "Included series"))
        selection_layout = QVBoxLayout(selection_box)
        self.group_values = QListWidget(); self.group_values.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.group_values.setWordWrap(True); self.group_values.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.group_values.setMaximumHeight(190); selection_layout.addWidget(self.group_values)
        selection_buttons = QHBoxLayout()
        select_all = QPushButton(self._tr("Todas", "All")); select_none = QPushButton(self._tr("Ninguna", "None"))
        select_all.clicked.connect(self.group_values.selectAll); select_none.clicked.connect(self.group_values.clearSelection)
        selection_buttons.addWidget(select_all); selection_buttons.addWidget(select_none); selection_layout.addLayout(selection_buttons)
        data_layout.addWidget(selection_box); data_layout.addStretch()
        tabs.addTab(data_tab, self._tr("Datos", "Data"))

        # --- Style tab ------------------------------------------------
        style_tab = QWidget(); style_layout = QVBoxLayout(style_tab)
        style_box = QGroupBox(self._tr("Estilo", "Style")); style_form = QFormLayout(style_box)
        self.mode_combo = WheelSafeComboBox()
        for es, en, value in (
            ("Puntos conectados", "Connected points", "scatter_lines_markers"),
            ("Diagrama de dispersión", "Scatter", "scatter_markers"),
            ("Solo líneas", "Lines only", "scatter_lines"),
            ("Barras agrupadas", "Grouped bars", "bar"),
            ("Histograma", "Histogram", "histogram"),
            ("Diagrama de caja", "Box plot", "box"),
            ("Diagrama de violín", "Violin plot", "violin"),
        ):
            self.mode_combo.addItem(self._tr(es, en), value)
        self.dash_combo = WheelSafeComboBox()
        for es, en, value in (("Continua","Solid","solid"),("Guiones","Dashed","dash"),("Punteada","Dotted","dot"),("Guion y punto","Dash-dot","dashdot")):
            self.dash_combo.addItem(self._tr(es,en), value)
        self.line_width = QDoubleSpinBox(); self.line_width.setRange(0.5, 8.0); self.line_width.setSingleStep(0.25); self.line_width.setValue(float(self.settings.value("tablePlot/lineWidth", 2.0)))
        self.marker_size = QDoubleSpinBox(); self.marker_size.setRange(2.0, 20.0); self.marker_size.setValue(float(self.settings.value("tablePlot/markerSize", 7.0)))
        self.palette_combo = WheelSafeComboBox(); self.palette_combo.addItems(PALETTES.keys())
        self.colors_button = QPushButton(self._tr("Colores por serie...", "Series colors..."))
        self.legend_combo = WheelSafeComboBox()
        self.legend_combo.addItem(self._tr("Compacta a la derecha", "Compact on right"), "right")
        self.legend_combo.addItem(self._tr("Horizontal debajo", "Horizontal below"), "bottom")
        self.legend_combo.addItem(self._tr("Ocultar leyenda", "Hide legend"), "hidden"); self.legend_combo.setCurrentIndex(1)
        self.histogram_bins = QSpinBox(); self.histogram_bins.setRange(5, 200); self.histogram_bins.setValue(30); self.histogram_bins.setSuffix(self._tr(" intervalos", " bins")); self.histogram_bins.setEnabled(False)
        self.log_x = QCheckBox(self._tr("Escala logarítmica en X", "Logarithmic X scale")); self.log_y = QCheckBox(self._tr("Escala logarítmica en Y", "Logarithmic Y scale"))
        self.error_bars = QCheckBox(self._tr("Barras de error automáticas", "Automatic error bars")); self.error_bars.setChecked(True)
        self.error_bars.setToolTip(self._tr("Usa σ(N), σ(FWHM) o σ(∫T dv) cuando la tabla incluye esa incertidumbre.", "Uses σ(N), σ(FWHM), or σ(∫T dv) when available."))
        self.error_info = QLabel(self._tr("Sin incertidumbres asociadas a los ejes actuales.", "No uncertainties associated with the current axes.")); self.error_info.setWordWrap(True); self.error_info.setStyleSheet("color: #52627A; font-size: 11px;")
        style_form.addRow(self._tr("Trazado:", "Plot type:"), self.mode_combo); style_form.addRow(self._tr("Línea:", "Line:"), self.dash_combo)
        style_form.addRow(self._tr("Grosor:", "Width:"), self.line_width); style_form.addRow(self._tr("Tamaño de punto:", "Marker size:"), self.marker_size)
        style_form.addRow(self._tr("Paleta:", "Palette:"), self.palette_combo); style_form.addRow(self.colors_button)
        style_form.addRow(self._tr("Leyenda:", "Legend:"), self.legend_combo); style_form.addRow(self._tr("Histograma:", "Histogram:"), self.histogram_bins)
        style_form.addRow(self.log_x); style_form.addRow(self.log_y); style_form.addRow(self.error_bars); style_form.addRow(self.error_info)
        style_layout.addWidget(style_box); style_layout.addStretch(); tabs.addTab(style_tab, self._tr("Estilo", "Style"))

        # --- Labels tab -----------------------------------------------
        labels_tab = QWidget(); labels_layout = QVBoxLayout(labels_tab)
        labels_box = QGroupBox(self._tr("Rótulos", "Labels")); labels_form = QFormLayout(labels_box)
        self.title_input = QLineEdit(); self.x_label_input = QLineEdit(); self.y_label_input = QLineEdit()
        labels_form.addRow(self._tr("Título:", "Title:"), self.title_input); labels_form.addRow(self._tr("Etiqueta X:", "X label:"), self.x_label_input); labels_form.addRow(self._tr("Etiqueta Y:", "Y label:"), self.y_label_input)
        labels_layout.addWidget(labels_box); labels_layout.addStretch(); tabs.addTab(labels_tab, self._tr("Rótulos", "Labels"))

        self.plot_button = QPushButton(self._tr("Actualizar gráfica", "Update plot"))
        self.plot_button.setProperty("actionRole", "primary")
        layout.addWidget(self.plot_button)
        return panel

    def _runtime_loaded(self, ok):
        self._runtime_ready = bool(ok)
        if self._runtime_ready:
            self.schedule_update()

    def _dataset_changed(self):
        self._updating_controls = True
        frame = self._current_frame()
        previous_x = self.x_combo.currentData()
        previous_y = self.y_combo.currentData()
        numeric = plot_axis_columns(frame, advanced=self.advanced_axes.isChecked())
        self.x_combo.clear()
        self.y_combo.clear()
        for column in numeric:
            self.x_combo.addItem(self._column_label(column), column)
            self.y_combo.addItem(self._column_label(column), column)
            tooltip = column_tooltip(column)
            self.x_combo.setItemData(self.x_combo.count() - 1, tooltip, Qt.ToolTipRole)
            self.y_combo.setItemData(self.y_combo.count() - 1, tooltip, Qt.ToolTipRole)

        self.group_combo.clear()
        self.group_combo.addItem(self._tr("Una sola serie", "Single series"), "")
        for column in frame.columns:
            if frame[column].nunique(dropna=True) <= max(80, len(frame) // 2):
                self.group_combo.addItem(self._column_label(column), str(column))

        is_partition = "Q(T)" in frame.columns and "T_ex [K]" in frame.columns
        is_tau = (
            "τ" in frame.columns
            and "T_ex [K]" in frame.columns
            and self.dataset_combo.currentText().startswith("MTH · τ")
        )
        is_density = "N_total [cm^-2]" in frame.columns and "T_ex [K]" in frame.columns
        if is_partition:
            self._select_combo_data(self.x_combo, "T_ex [K]")
            self._select_combo_data(self.y_combo, "Q(T)")
            self.log_x.setChecked(False)
            self.log_y.setChecked(False)
            self._select_combo_data(self.order_combo, "x")
            self.title_input.setText(self._tr("Función de partición en función de la temperatura", "Partition function versus temperature"))
        elif is_tau:
            self._select_combo_data(self.x_combo, "T_ex [K]")
            self._select_combo_data(self.y_combo, "τ")
            self.log_x.setChecked(False)
            self.log_y.setChecked(False)
            self._select_combo_data(self.order_combo, "x")
            self.title_input.setText(self._tr("Profundidad óptica en función de Tₑₓ", "Optical depth versus Tₑₓ"))
        elif is_density:
            self._select_combo_data(self.x_combo, "N_total [cm^-2]")
            self._select_combo_data(self.y_combo, "T_ex [K]")
            self.log_x.setChecked(True)
            self._select_combo_data(self.order_combo, "y")
            self.title_input.setText(self._tr("Densidad columnar en función de Tₑₓ", "Column density versus Tₑₓ"))
        elif previous_x in numeric and previous_y in numeric:
            self._select_combo_data(self.x_combo, previous_x)
            self._select_combo_data(self.y_combo, previous_y)
            self.log_x.setChecked(False)
        elif len(numeric) >= 2:
            self.x_combo.setCurrentIndex(0)
            self.y_combo.setCurrentIndex(1)
            self.log_x.setChecked(False)

        preferred_group = "__czspec_series__" if "__czspec_series__" in frame.columns else ""
        self._select_combo_data(self.group_combo, preferred_group)
        self._group_changed()
        self._refresh_axis_labels()
        self._updating_controls = False
        self.schedule_update()

    def _plot_type_changed(self):
        if self._updating_controls:
            return
        plot_type = str(self.mode_combo.currentData() or "scatter_lines_markers")
        is_histogram = plot_type == "histogram"
        is_distribution = plot_type in {"histogram", "box", "violin"}
        self.histogram_bins.setEnabled(is_histogram)
        self.dash_combo.setEnabled(not is_distribution and plot_type != "bar")
        self.line_width.setEnabled(plot_type.startswith("scatter"))
        self.marker_size.setEnabled(plot_type.startswith("scatter"))
        self.y_combo.setEnabled(not is_histogram)
        self._refresh_axis_labels()
        self.schedule_update()

    @staticmethod
    def _select_combo_data(combo, value):
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _group_changed(self):
        self.group_values.clear()
        frame = self._current_frame()
        group_column = str(self.group_combo.currentData() or "")
        if not group_column or group_column not in frame.columns:
            self.group_values.setEnabled(False)
            self.schedule_update()
            return
        self.group_values.setEnabled(True)
        values = frame[group_column].dropna().astype(str).drop_duplicates().tolist()
        try:
            values = sorted(values, key=lambda value: float(value))
        except (TypeError, ValueError):
            values = sorted(values)
        for value in values:
            display_value = value
            if group_column == "__czspec_series__" and "__czspec_series_label__" in frame.columns:
                matches = frame.loc[
                    frame[group_column].astype(str) == value,
                    "__czspec_series_label__",
                ]
                if not matches.empty:
                    display_value = str(matches.iloc[0])
            item = QListWidgetItem(display_value)
            item.setData(Qt.UserRole, value)
            item.setToolTip(value)
            self.group_values.addItem(item)
            item.setSelected(True)
        self.schedule_update()

    def _current_frame(self):
        name = self.dataset_combo.currentText()
        return self.datasets.get(name, pd.DataFrame()).copy()

    def _swap_axes(self):
        x_data = self.x_combo.currentData()
        y_data = self.y_combo.currentData()
        self._select_combo_data(self.x_combo, y_data)
        self._select_combo_data(self.y_combo, x_data)
        self._refresh_axis_labels()
        self.schedule_update()

    def _axis_changed(self):
        if self._updating_controls:
            return
        self._refresh_axis_labels()
        self.schedule_update()

    def _palette_changed(self):
        if self._updating_controls:
            return
        self.series_colors.clear()
        self.schedule_update()

    def schedule_update(self, *args):
        if self._updating_controls or not self._runtime_ready:
            return
        self.update_timer.start()

    def _refresh_axis_labels(self):
        self.x_label_input.setText(column_display_name(self.x_combo.currentData() or ""))
        if str(self.mode_combo.currentData() or "") == "histogram":
            self.y_label_input.setText(self._tr("Conteo", "Count"))
        else:
            self.y_label_input.setText(column_display_name(self.y_combo.currentData() or ""))
        self._refresh_error_info()

    def _refresh_error_info(self):
        frame = self._current_frame()
        x_column = str(self.x_combo.currentData() or "")
        y_column = str(self.y_combo.currentData() or "")
        x_error = uncertainty_column(frame, x_column) if x_column else None
        y_error = uncertainty_column(frame, y_column) if y_column else None
        parts = []
        if x_error:
            parts.append(f"X: {self._column_label(x_error)}")
        if y_error:
            parts.append(f"Y: {self._column_label(y_error)}")
        self.error_info.setText(
            (self._tr("Incertidumbre automática · ", "Automatic uncertainty · ") + " · ".join(parts))
            if parts else self._tr("Sin incertidumbres asociadas a los ejes actuales.", "No uncertainties associated with the current axes.")
        )

    def _selected_groups(self):
        return {str(item.data(Qt.UserRole)) for item in self.group_values.selectedItems()}

    def _series_frames(self, frame, group_column):
        if not group_column:
            return [(self.dataset_combo.currentText(), frame)]
        selected = self._selected_groups()
        if not selected:
            return []
        filtered = frame[frame[group_column].astype(str).isin(selected)].copy()
        return [(str(value), group.copy()) for value, group in filtered.groupby(group_column, sort=False)]

    def _color_for_series(self, name, index):
        if name in self.series_colors:
            return self.series_colors[name]
        palette = PALETTES[self.palette_combo.currentText()]
        color = palette[index % len(palette)]
        self.series_colors[name] = color
        return color

    def _build_figure(self):
        frame = self._current_frame()
        x_column = str(self.x_combo.currentData() or "")
        y_column = str(self.y_combo.currentData() or "")
        group_column = str(self.group_combo.currentData() or "")
        plot_type = str(self.mode_combo.currentData() or "scatter_lines_markers")
        if not x_column or (plot_type != "histogram" and not y_column):
            raise ValueError(self._tr("La tabla no contiene dos columnas numéricas para graficar.", "The table does not contain two numeric columns to plot."))

        working = frame.copy()
        working["__x__"] = numeric_series(working[x_column])
        x_error_column = uncertainty_column(working, x_column)
        y_error_column = uncertainty_column(working, y_column)
        if x_error_column:
            working["__xerr__"] = numeric_series(working[x_error_column]).abs()
        required_values = ["__x__"]
        if plot_type != "histogram":
            working["__y__"] = numeric_series(working[y_column])
            if y_error_column:
                working["__yerr__"] = numeric_series(working[y_error_column]).abs()
            required_values.append("__y__")
        working = working.replace([np.inf, -np.inf], np.nan).dropna(subset=required_values)
        if self.log_x.isChecked():
            working = working[working["__x__"] > 0]
        if self.log_y.isChecked() and plot_type != "histogram":
            working = working[working["__y__"] > 0]

        traces = []
        for index, (series_name, series) in enumerate(self._series_frames(working, group_column)):
            order_mode = str(self.order_combo.currentData() or "table")
            if plot_type != "histogram":
                if order_mode == "x":
                    series = series.sort_values(["__x__", "__y__"], kind="mergesort")
                elif order_mode == "y":
                    series = series.sort_values(["__y__", "__x__"], kind="mergesort")
            display_name = series_name
            if "__czspec_series_label__" in series.columns and not series.empty:
                display_name = str(series["__czspec_series_label__"].iloc[0])
            color = self._color_for_series(display_name, index)
            custom_columns = [
                column for column in (
                    "obs_id", "name", "chemical_name", "Método", "Referencia",
                    "ID de referencia", "T_ex [K]", "N_total [cm^-2]",
                )
                if column in series.columns
            ]
            hover = []
            for _, row in series.iterrows():
                hover.append("<br>".join(
                    f"{self._column_label(column)}: {row.get(column)}"
                    for column in custom_columns
                ))
            trace_base = {
                "name": display_name,
                "text": hover,
            }
            errors = {}
            if self.error_bars.isChecked() and plot_type not in {"histogram", "box", "violin"}:
                if x_error_column and "__xerr__" in series:
                    errors["error_x"] = {
                        "type": "data",
                        "visible": True,
                        "array": [
                            float(value) if pd.notna(value) and np.isfinite(value) else None
                            for value in series["__xerr__"]
                        ],
                    }
                if y_error_column and "__yerr__" in series:
                    errors["error_y"] = {
                        "type": "data",
                        "visible": True,
                        "array": [
                            float(value) if pd.notna(value) and np.isfinite(value) else None
                            for value in series["__yerr__"]
                        ],
                    }
            if plot_type == "histogram":
                trace = {
                    **trace_base,
                    "type": "histogram",
                    "x": series["__x__"].astype(float).tolist(),
                    "nbinsx": int(self.histogram_bins.value()),
                    "opacity": 0.72,
                    "marker": {"color": color},
                    "hovertemplate": ("%{fullData.name}<br>" + self._tr("Intervalo", "Bin") + "=%{x:.6g}<br>" + self._tr("Conteo", "Count") + "=%{y}<extra></extra>"),
                }
            elif plot_type == "bar":
                trace = {
                    **trace_base,
                    **errors,
                    "type": "bar",
                    "x": series["__x__"].astype(float).tolist(),
                    "y": series["__y__"].astype(float).tolist(),
                    "marker": {"color": color},
                    "hovertemplate": "%{text}<br>X=%{x:.6g}<br>Y=%{y:.6g}<extra>%{fullData.name}</extra>",
                }
            elif plot_type == "box":
                trace = {
                    **trace_base,
                    "type": "box",
                    "y": series["__y__"].astype(float).tolist(),
                    "marker": {"color": color},
                    "line": {"color": color},
                    "boxpoints": "outliers",
                    "hovertemplate": "%{fullData.name}<br>Y=%{y:.6g}<extra></extra>",
                }
            elif plot_type == "violin":
                trace = {
                    **trace_base,
                    "type": "violin",
                    "y": series["__y__"].astype(float).tolist(),
                    "marker": {"color": color},
                    "line": {"color": color},
                    "box": {"visible": True},
                    "meanline": {"visible": True},
                    "points": "outliers",
                    "hovertemplate": "%{fullData.name}<br>Y=%{y:.6g}<extra></extra>",
                }
            else:
                scatter_mode = {
                    "scatter_lines_markers": "lines+markers",
                    "scatter_markers": "markers",
                    "scatter_lines": "lines",
                }[plot_type]
                trace = {
                    **trace_base,
                    **errors,
                    "type": "scatter",
                    "mode": scatter_mode,
                    "x": series["__x__"].astype(float).tolist(),
                    "y": series["__y__"].astype(float).tolist(),
                    "hovertemplate": "%{text}<br>X=%{x:.6g}<br>Y=%{y:.6g}<extra>%{fullData.name}</extra>",
                    "line": {
                        "color": color,
                        "width": float(self.line_width.value()),
                        "dash": str(self.dash_combo.currentData()),
                    },
                    "marker": {
                        "color": color,
                        "size": float(self.marker_size.value()),
                    },
                }
            traces.append(trace)
        if not traces:
            raise ValueError(self._tr("No quedaron puntos válidos con la selección actual.", "No valid points remain for the current selection."))

        if plot_type == "histogram":
            default_title = self._tr(f"Distribución de {self._column_label(x_column)}", f"Distribution of {self._column_label(x_column)}")
        elif plot_type in {"box", "violin"}:
            default_title = self._tr(f"Distribución de {self._column_label(y_column)}", f"Distribution of {self._column_label(y_column)}")
        else:
            default_title = self._tr(
                f"{self._column_label(y_column)} frente a {self._column_label(x_column)}",
                f"{self._column_label(y_column)} versus {self._column_label(x_column)}",
            )
        title = self.title_input.text().strip() or default_title
        legend_mode = str(self.legend_combo.currentData() or "right")
        legend = {"title": {"text": ""}}
        margin = {"l": 80, "r": 30, "t": 70, "b": 75}
        if legend_mode == "right":
            legend.update({"orientation": "v", "x": 1.02, "xanchor": "left", "y": 1.0})
        elif legend_mode == "bottom":
            legend.update({
                "orientation": "h", "x": 0.5, "xanchor": "center",
                "y": -0.22, "yanchor": "top",
            })
            margin["b"] = 125

        y_axis_title = self._tr("Conteo", "Count") if plot_type == "histogram" else (
            self.y_label_input.text().strip() or self._column_label(y_column)
        )
        x_axis_title = (
            self._tr("Serie", "Series") if plot_type in {"box", "violin"}
            else self.x_label_input.text().strip() or self._column_label(x_column)
        )
        layout = {
            "template": "plotly_white",
            "title": {"text": title, "x": 0.5},
            "xaxis": {
                "title": x_axis_title,
                "type": "log" if self.log_x.isChecked() else "linear",
                "showgrid": True,
            },
            "yaxis": {
                "title": y_axis_title,
                "type": "log" if self.log_y.isChecked() else "linear",
                "showgrid": True,
            },
            "showlegend": legend_mode != "hidden" and len(traces) > 1,
            "legend": legend,
            "hovermode": "closest",
            "margin": margin,
            "autosize": True,
            "barmode": "overlay" if plot_type == "histogram" else "group",
            "boxmode": "group",
            "violinmode": "group",
        }
        return {"data": traces, "layout": layout}

    def update_plot(self, *args):
        try:
            figure = self._build_figure()
        except Exception as exc:
            self.current_plot_json = None
            self.save_button.setEnabled(False)
            return
        self.current_plot_json = json.dumps(figure, ensure_ascii=False)
        payload = json.dumps(self.current_plot_json)
        script = f"window.czspecRender({payload}, 'interactive', true);"
        self.plot_view.page().runJavaScript(script)
        self.save_button.setEnabled(True)
        self.settings.setValue("tablePlot/lineWidth", self.line_width.value())
        self.settings.setValue("tablePlot/markerSize", self.marker_size.value())

    def _choose_series_colors(self):
        try:
            figure = self._build_figure()
        except Exception as exc:
            QMessageBox.information(self, self._tr("Sin series", "No series"), str(exc))
            return
        names = [str(trace["name"]) for trace in figure["data"]]
        dialog = SeriesColorDialog(names, self.series_colors, self.language, self)
        if dialog.exec() == QDialog.Accepted:
            self.series_colors.update(dialog.colors)
            self.update_plot()

    def _suggest_image_stem(self) -> str:
        custom = self.image_name_input.text().strip() if hasattr(self, "image_name_input") else ""
        if custom:
            raw = Path(custom).stem
        else:
            raw = self.title_input.text().strip() if hasattr(self, "title_input") else ""
            if not raw and self.current_plot_json:
                try:
                    fig = json.loads(self.current_plot_json)
                    title = ((fig.get("layout") or {}).get("title") or {})
                    raw = str(title.get("text") if isinstance(title, dict) else title or "").strip()
                except Exception:
                    raw = ""
            if not raw:
                raw = str(self.dataset_combo.currentText() or ("table_plot" if self.language == "en" else "grafica_tabla"))
            frame = self._current_frame()
            if frame is not None and not frame.empty and "Source" in frame.columns:
                sources = [str(v).strip() for v in frame["Source"].dropna().unique().tolist() if str(v).strip()]
                if len(sources) == 1 and sources[0].casefold() not in raw.casefold():
                    raw = f"{raw} - {sources[0]}"
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._-")
        safe = safe or ("table_plot" if self.language == "en" else "grafica_tabla")
        if self.filename_prefix and not safe.casefold().startswith(self.filename_prefix.casefold()):
            safe = f"{self.filename_prefix}_{safe}"
        return safe

    def save_image(self):
        if not self.current_plot_json:
            return
        self.output_directory.mkdir(parents=True, exist_ok=True)
        stem = self._suggest_image_stem()
        suggested = self.output_directory / f"{stem}.png"
        if suggested.exists():
            for index in range(1, 10000):
                candidate = self.output_directory / f"{stem}_{index:03d}.png"
                if not candidate.exists():
                    suggested = candidate
                    break
            else:
                suggested = self.output_directory / f"{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            self._tr("Guardar gráfica de tabla", "Save table plot"),
            str(suggested),
            "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)",
        )
        if not path:
            return
        destination = Path(path)
        if not destination.suffix:
            destination = destination.with_suffix(
                ".svg" if "SVG" in selected_filter else ".pdf" if "PDF" in selected_filter else ".png"
            )
        try:
            import plotly.io as pio

            figure = pio.from_json(self.current_plot_json)
            figure.write_image(str(destination), scale=2 if destination.suffix.lower() == ".png" else 1)
            self.image_saved.emit(str(destination))
        except Exception as exc:
            QMessageBox.critical(self, self._tr("No se pudo guardar", "Could not save"), str(exc))
