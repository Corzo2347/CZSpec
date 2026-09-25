"""Interfaz del módulo 5: razones de densidad columnar."""

from __future__ import annotations

from datetime import datetime
import json
import math
import re
from pathlib import Path

import pandas as pd

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from czspec.logic.ratio_analysis import (
    calculate_ratio_series,
    extract_column_density_records,
    results_dataframe,
    unique_series,
)
from czspec.paths import (
    MOLECULAR_RATIOS_GRAPHICS_DIR,
    MOLECULAR_RATIOS_IMAGES_DIR,
    MOLECULAR_RATIOS_OUTPUT_DIR,
    MOLECULAR_RATIOS_TABLES_DIR,
)
from czspec.utils.export_utils import open_folder_in_system


RATIO_PRESETS = [
    ("Personalizada", "", "", ""),
    ("HCN / HNC — gas denso (MTH)", "MTH", "HCN", "HNC"),
    ("N₂H⁺ / HCO⁺ — gas denso (MTH)", "MTH", "N2H", "HCO+"),
    ("HCN / HCO⁺ — ionización/opacidad (MTH)", "MTH", "HCN", "HCO+"),
    ("C₂H / HCN — química carbonada (MOD)", "MOD", "CCH", "HCN"),
    ("CH₃CN / H₂CO — gas calentado (MOD)", "MOD", "CH3CN", "H2CO"),
    ("CS / H₂CO — azufre/formaldehído (MTH)", "MTH", "CS", "H2CO"),
    ("HCN / H¹³CN — opacidad/isótopos (MOD)", "MOD", "HCN", "H13CN"),
    ("HCN / HC¹⁵N — opacidad/isótopos (MOD)", "MOD", "HCN", "HC15N"),
    ("HCO⁺ / H¹³CO⁺ — opacidad/isótopos (MOD)", "MOD", "HCO+", "H13CO+"),
    ("SiO / SO — choques (MOD)", "MOD", "SIO", "SO"),
    ("SO / SO₂ — química del azufre (MOD)", "MOD", "SO", "SO2"),
    ("CH₃OH / H₂CO — hielos y desorción (MOD)", "MOD", "CH3OH", "H2CO"),
]


def _normalized_species(text: str) -> str:
    value = str(text).upper()
    replacements = {"₂": "2", "₃": "3", "⁺": "+", "Α": "A"}
    for old, new in replacements.items():
        value = value.replace(old, new)
    return re.sub(r"[^A-Z0-9+]", "", value)


class MolecularRatioWidget(QWidget):
    def __init__(self, data_provider, parent=None):
        super().__init__(parent)
        self.data_provider = data_provider
        self.records = []
        self.series = {}
        self.results = pd.DataFrame()
        self.plot_view = None
        self._plot_ready = False
        self._pending_plot = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        intro = QLabel(
            "Calcula razones N(A)/N(B) a partir de las soluciones del módulo 3. "
            "CZSpec exige el mismo método y la misma Tₑₓ para ambos términos."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        left = QWidget()
        left.setMinimumWidth(330)
        left.setMaximumWidth(430)
        left_layout = QVBoxLayout(left)

        selection_box = QGroupBox("Definir el cociente")
        selection = QFormLayout(selection_box)
        self.preset_combo = QComboBox()
        for label, method, numerator, denominator in RATIO_PRESETS:
            self.preset_combo.addItem(label, (method, numerator, denominator))
        self.method_combo = QComboBox()
        self.method_combo.addItem("MOD — N ópticamente delgada", "MOD")
        self.method_combo.addItem("MTH — N corregida por opacidad", "MTH")
        self.numerator_combo = QComboBox()
        self.denominator_combo = QComboBox()
        selection.addRow("Diagnóstico sugerido:", self.preset_combo)
        selection.addRow("Método M3:", self.method_combo)
        selection.addRow("Numerador N(A):", self.numerator_combo)
        selection.addRow("Denominador N(B):", self.denominator_combo)
        left_layout.addWidget(selection_box)

        action_box = QGroupBox("Cálculo y exportación")
        action_layout = QVBoxLayout(action_box)
        self.calculate_button = QPushButton("Calcular temperaturas comunes")
        self.export_button = QPushButton("Guardar tabla CSV")
        self.save_plot_button = QPushButton("Guardar gráfica")
        self.export_button.setEnabled(False)
        self.save_plot_button.setEnabled(False)
        action_layout.addWidget(self.calculate_button)
        action_layout.addWidget(self.export_button)
        action_layout.addWidget(self.save_plot_button)
        left_layout.addWidget(action_box)

        folders = QGroupBox("Carpetas de salida")
        folder_grid = QGridLayout(folders)
        for index, (label, path) in enumerate(
            (
                ("Guardado general", MOLECULAR_RATIOS_OUTPUT_DIR),
                ("Gráficos", MOLECULAR_RATIOS_GRAPHICS_DIR),
                ("Tablas", MOLECULAR_RATIOS_TABLES_DIR),
                ("Imágenes", MOLECULAR_RATIOS_IMAGES_DIR),
            )
        ):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, p=path: open_folder_in_system(p))
            folder_grid.addWidget(button, index // 2, index % 2)
        left_layout.addWidget(folders)

        warning = QLabel(
            "Interpretación: estas son razones de densidad columnar, no abundancias "
            "moleculares absolutas. No incluyen por sí solas efectos sistemáticos de "
            "haz, llenado, autoabsorción, excitación o mezcla cinemática."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet(
            "background:#FFF7ED;color:#9A3412;border:1px solid #FDBA74;"
            "border-radius:8px;padding:10px;"
        )
        left_layout.addWidget(warning)
        left_layout.addStretch()
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        plot_box = QGroupBox("Razón frente a temperatura de excitación")
        plot_layout = QVBoxLayout(plot_box)
        self.plot_stack = QStackedWidget()
        self.plot_placeholder = QLabel(
            "Actualiza los resultados de M3 y selecciona un numerador y un denominador."
        )
        self.plot_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.plot_placeholder.setWordWrap(True)
        self.plot_stack.addWidget(self.plot_placeholder)
        plot_layout.addWidget(self.plot_stack)
        right_layout.addWidget(plot_box, 3)

        table_box = QGroupBox("Resultados y trazabilidad")
        table_layout = QVBoxLayout(table_box)
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table_layout.addWidget(self.table)
        self.status = QLabel("Sin resultados de densidad columnar disponibles.")
        self.status.setWordWrap(True)
        table_layout.addWidget(self.status)
        right_layout.addWidget(table_box, 2)
        splitter.addWidget(right)
        splitter.setSizes([370, 1000])

        self.preset_combo.currentIndexChanged.connect(self._apply_preset)
        self.method_combo.currentIndexChanged.connect(self._populate_series)
        self.calculate_button.clicked.connect(self.calculate)
        self.export_button.clicked.connect(self.export_csv)
        self.save_plot_button.clicked.connect(self.save_plot)

    def refresh(self):
        mod_df, mth_df, dataset = self.data_provider()
        self.records = extract_column_density_records(mod_df, mth_df, dataset=dataset)
        self.series = unique_series(self.records)
        self._populate_series()
        methods = sorted({record.method for record in self.records})
        if self.records:
            self.status.setText(
                f"{len(self.records)} solución(es) físicas disponibles · métodos: "
                f"{', '.join(methods)}."
            )
        else:
            self.status.setText("Ejecuta MOD o MTH en el módulo 3 para habilitar M5.")

    def _populate_series(self):
        method = self.method_combo.currentData()
        current_num = self.numerator_combo.currentData()
        current_den = self.denominator_combo.currentData()
        entries = [(key, record) for key, record in self.series.items() if record.method == method]
        for combo, previous in ((self.numerator_combo, current_num), (self.denominator_combo, current_den)):
            combo.blockSignals(True)
            combo.clear()
            for key, record in entries:
                combo.addItem(record.label, key)
            previous_index = combo.findData(previous)
            if previous_index >= 0:
                combo.setCurrentIndex(previous_index)
            combo.blockSignals(False)
        enabled = len(entries) >= 2
        self.calculate_button.setEnabled(enabled)

    def _select_matching(self, combo: QComboBox, token: str):
        token = _normalized_species(token)
        matches = []
        for index in range(combo.count()):
            record = self.series.get(combo.itemData(index))
            species = _normalized_species(record.species if record else combo.itemText(index))
            if not token or not species.startswith(token):
                continue
            # Favorece una coincidencia molecular exacta y evita que "SO" elija
            # silenciosamente SO2 o que "HCN" termine en H13CN/HC15N.
            exact = species == token or species.startswith(token + "V")
            matches.append((0 if exact else 1, len(species), index))
        if matches:
            combo.setCurrentIndex(min(matches)[2])
            return True
        return False

    def _apply_preset(self):
        method, numerator, denominator = self.preset_combo.currentData()
        if not method:
            return
        method_index = self.method_combo.findData(method)
        if method_index >= 0:
            self.method_combo.setCurrentIndex(method_index)
        num_found = self._select_matching(self.numerator_combo, numerator)
        den_found = self._select_matching(self.denominator_combo, denominator)
        if not (num_found and den_found):
            self.status.setText(
                "El diagnóstico elegido no está completo en los resultados actuales; "
                "puedes seleccionar manualmente otras líneas."
            )

    def calculate(self):
        numerator_key = self.numerator_combo.currentData()
        denominator_key = self.denominator_combo.currentData()
        if not numerator_key or not denominator_key or numerator_key == denominator_key:
            self._error("Selecciona dos series distintas para construir el cociente.")
            return
        try:
            calculated = calculate_ratio_series(self.records, numerator_key, denominator_key)
        except ValueError as exc:
            self._error(str(exc))
            return
        self.results = results_dataframe(calculated)
        self._populate_table()
        self._render_plot()
        self.export_button.setEnabled(True)
        self.save_plot_button.setEnabled(True)
        self.status.setStyleSheet("color:#166534;")
        self.status.setText(
            f"Razón calculada en {len(self.results)} temperatura(s) común(es). "
            "Las barras representan la incertidumbre estadística propagada cuando existe."
        )

    def _error(self, message: str):
        self.status.setStyleSheet("color:#B91C1C;")
        self.status.setText(message)

    def _populate_table(self):
        columns = [
            ("tex_k", "Tₑₓ [K]"),
            ("ratio", "N(A) / N(B)"),
            ("uncertainty", "σ de la razón"),
            ("method", "Método"),
            ("numerator_label", "Numerador"),
            ("denominator_label", "Denominador"),
            ("status", "Estado"),
        ]
        self.table.setRowCount(len(self.results))
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels([label for _, label in columns])
        for row_index, (_, row) in enumerate(self.results.iterrows()):
            for column_index, (name, _label) in enumerate(columns):
                value = row.get(name, "")
                if name in {"ratio", "uncertainty"} and pd.notna(value):
                    text = f"{float(value):.5g}"
                else:
                    text = "" if pd.isna(value) else str(value)
                self.table.setItem(row_index, column_index, QTableWidgetItem(text))

    def _plot_json(self) -> str:
        import plotly.graph_objects as go

        first = self.results.iloc[0]
        y_error = self.results["uncertainty"].where(self.results["uncertainty"].notna(), 0.0)
        figure = go.Figure(
            go.Scatter(
                x=self.results["tex_k"],
                y=self.results["ratio"],
                error_y={"type": "data", "array": y_error, "visible": True},
                mode="lines+markers",
                line={"color": "#2563EB", "width": 2.2},
                marker={"size": 8, "color": "#0EA5E9"},
                name="N(A)/N(B)",
                hovertemplate="Tₑₓ=%{x:.3g} K<br>Razón=%{y:.4g}<extra></extra>",
            )
        )
        figure.update_layout(
            template="plotly_white",
            title=f"{first['numerator_label']} / {first['denominator_label']}",
            xaxis_title="Temperatura de excitación Tₑₓ [K]",
            yaxis_title="Razón de densidades columnares N(A)/N(B)",
            margin={"l": 70, "r": 25, "t": 75, "b": 65},
            showlegend=False,
        )
        return figure.to_json()

    def _ensure_plot_view(self):
        if self.plot_view is not None:
            return
        try:
            from PySide6.QtWebEngineCore import QWebEngineSettings
            from PySide6.QtWebEngineWidgets import QWebEngineView
            from czspec.utils.plotly_runtime import prepare_plotly_view_file
        except ImportError as exc:
            self._error(f"No se pudo cargar el visor interactivo: {exc}")
            return
        self.plot_view = QWebEngineView()
        self.plot_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
        )
        self.plot_view.loadFinished.connect(self._on_plot_loaded)
        self.plot_stack.addWidget(self.plot_view)
        self.plot_stack.setCurrentWidget(self.plot_view)
        self.plot_view.load(QUrl.fromLocalFile(str(prepare_plotly_view_file())))

    def _on_plot_loaded(self, ok: bool):
        self._plot_ready = bool(ok)
        if ok and self._pending_plot:
            payload = self._pending_plot
            self._pending_plot = None
            self._send_plot(payload)

    def _send_plot(self, plot_json: str):
        if not self.plot_view or not self._plot_ready:
            self._pending_plot = plot_json
            return
        self.plot_view.page().runJavaScript(
            f"window.czspecRender({json.dumps(plot_json)}, 'interactive', true);"
        )

    def _render_plot(self):
        plot_json = self._plot_json()
        self._pending_plot = plot_json
        self._ensure_plot_view()
        self._send_plot(plot_json)

    def export_csv(self):
        if self.results.empty:
            return
        MOLECULAR_RATIOS_TABLES_DIR.mkdir(parents=True, exist_ok=True)
        default = MOLECULAR_RATIOS_TABLES_DIR / f"razones_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Guardar razones", str(default), "CSV (*.csv)")
        if path:
            self.results.to_csv(path, index=False)
            self.status.setText(f"Tabla guardada: {path}")

    def save_plot(self):
        if self.results.empty:
            return
        MOLECULAR_RATIOS_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        default = MOLECULAR_RATIOS_IMAGES_DIR / f"razones_{datetime.now():%Y%m%d_%H%M%S}.png"
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar gráfica", str(default), "PNG (*.png);;SVG (*.svg);;PDF (*.pdf)"
        )
        if not path:
            return
        import plotly.io as pio

        pio.write_image(pio.from_json(self._plot_json()), path)
        self.status.setText(f"Gráfica guardada: {path}")
