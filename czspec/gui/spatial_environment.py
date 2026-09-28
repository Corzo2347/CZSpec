"""Interfaz del módulo 6: entorno Aladin y capas paramétricas CZSpec."""

from __future__ import annotations

from datetime import datetime
import json
import math
from pathlib import Path
import uuid

from PySide6.QtCore import QObject, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from czspec.network import online_enabled

from czspec.logic.ratio_analysis import extract_column_density_records
from czspec.logic.spatial_representation import (
    SpatialLayerSpec,
    aladin_payload,
    homogenized_sigma_arcsec,
)
from czspec.paths import (
    PACKAGE_DIR,
    SPATIAL_GRAPHICS_DIR,
    SPATIAL_IMAGES_DIR,
    SPATIAL_REPRESENTATION_OUTPUT_DIR,
    SPATIAL_TABLES_DIR,
)
from czspec.utils.export_utils import open_folder_in_system


SOURCE_PRESETS = (
    ("LkHα 234 — J2000", 325.775000, 66.115000, 0.08),
    ("Cepheus A HW2 — J2000", 344.075000, 62.030278, 0.08),
    ("Coordenadas manuales", None, None, None),
)

SURVEYS = (
    ("DSS2 color — óptico", "P/DSS2/color"),
    ("DSS2 rojo — óptico", "P/DSS2/red"),
    ("2MASS color — infrarrojo cercano", "P/2MASS/color"),
    ("AllWISE color — infrarrojo medio", "P/allWISE/color"),
)

FAMILIES = (
    "Gas denso",
    "Choques y química del azufre",
    "Hielos y desorción",
    "Otra / personalizada",
)


def _family_for_species(species: str) -> tuple[str, str]:
    name = str(species).upper().replace(" ", "")
    if "SIO" in name or name.startswith("SO") or "S18O" in name:
        return "Choques y química del azufre", "anular"
    if any(token in name for token in ("CH3OH", "METHANOL")):
        return "Hielos y desorción", "anular"
    if any(token in name for token in ("HCO+", "HCN", "HNC", "N2H+", "CS", "H2CO")):
        return "Gas denso", "centrado"
    return "Otra / personalizada", "centrado"


class AladinBridge(QObject):
    statusChanged = Signal(str)

    @Slot(str)
    def reportStatus(self, message: str):
        self.statusChanged.emit(str(message))


class SpatialEnvironmentWidget(QWidget):
    def __init__(self, data_provider, parent=None):
        super().__init__(parent)
        self.data_provider = data_provider
        self.records = []
        self.layers: list[SpatialLayerSpec] = []
        self.viewer = None
        self.channel = None
        self.bridge = None
        self._viewer_ready = False
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        intro = QLabel(
            "Explora fondos observacionales en Aladin Lite y superpone perfiles "
            "paramétricos derivados de las densidades del módulo 3."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        panel = QWidget()
        panel.setMinimumWidth(330)
        panel.setMaximumWidth(430)
        panel_layout = QVBoxLayout(panel)

        position_box = QGroupBox("Campo celeste observacional")
        position_form = QFormLayout(position_box)
        self.source_combo = QComboBox()
        for label, ra, dec, fov in SOURCE_PRESETS:
            self.source_combo.addItem(label, (ra, dec, fov))
        self.ra_input = QDoubleSpinBox()
        self.ra_input.setRange(0.0, 360.0)
        self.ra_input.setDecimals(6)
        self.dec_input = QDoubleSpinBox()
        self.dec_input.setRange(-90.0, 90.0)
        self.dec_input.setDecimals(6)
        self.fov_input = QDoubleSpinBox()
        self.fov_input.setRange(0.005, 5.0)
        self.fov_input.setDecimals(3)
        self.fov_input.setValue(0.08)
        self.fov_input.setSuffix(" °")
        self.survey_combo = QComboBox()
        for label, survey_id in SURVEYS:
            self.survey_combo.addItem(label, survey_id)
        self.overlay_combo = QComboBox()
        self.overlay_combo.addItem("Sin segunda imagen", "")
        for label, survey_id in SURVEYS:
            self.overlay_combo.addItem(label, survey_id)
        self.overlay_opacity = QDoubleSpinBox()
        self.overlay_opacity.setRange(0.05, 1.0)
        self.overlay_opacity.setSingleStep(0.05)
        self.overlay_opacity.setValue(0.45)
        self.update_field_button = QPushButton("Aplicar campo y filtros")
        position_form.addRow("Fuente:", self.source_combo)
        position_form.addRow("RA ICRS [°]:", self.ra_input)
        position_form.addRow("Dec ICRS [°]:", self.dec_input)
        position_form.addRow("Campo visual:", self.fov_input)
        position_form.addRow("Fondo HiPS:", self.survey_combo)
        position_form.addRow("Superposición:", self.overlay_combo)
        position_form.addRow("Opacidad:", self.overlay_opacity)
        position_form.addRow(self.update_field_button)
        panel_layout.addWidget(position_box)

        layer_box = QGroupBox("Nueva capa molecular paramétrica")
        layer_form = QFormLayout(layer_box)
        self.record_combo = QComboBox()
        self.record_combo.addItem("Ejecuta MOD/MTH en el módulo 3", None)
        self.family_combo = QComboBox()
        self.family_combo.addItems(FAMILIES)
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("Perfil centrado", "centrado")
        self.profile_combo.addItem("Perfil anular", "anular")
        self.scale_input = QDoubleSpinBox()
        self.scale_input.setRange(0.2, 300.0)
        self.scale_input.setValue(10.0)
        self.scale_input.setSuffix(" ″")
        self.ring_input = QDoubleSpinBox()
        self.ring_input.setRange(0.0, 600.0)
        self.ring_input.setValue(20.0)
        self.ring_input.setSuffix(" ″")
        self.levels_input = QLineEdit("0.2, 0.4, 0.6, 0.8")
        self.common_beam_check = QCheckBox("Homogeneizar a haz común de 29″")
        self.common_beam_check.setChecked(True)
        self.order_scale_check = QCheckBox("Escala visual discreta según orden de N")
        self.order_scale_check.setChecked(True)
        self.color = "#14B8A6"
        self.color_button = QPushButton(self.color)
        self._update_color_button()
        self.width_input = QDoubleSpinBox()
        self.width_input.setRange(0.5, 8.0)
        self.width_input.setValue(2.0)
        self.width_input.setSuffix(" px")
        self.add_layer_button = QPushButton("Añadir capa al visor")
        self.add_layer_button.setEnabled(False)
        layer_form.addRow("Solución de M3:", self.record_combo)
        layer_form.addRow("Familia:", self.family_combo)
        layer_form.addRow("Geometría:", self.profile_combo)
        layer_form.addRow("Ancho s:", self.scale_input)
        layer_form.addRow("Radio r₀:", self.ring_input)
        layer_form.addRow("Niveles:", self.levels_input)
        layer_form.addRow("Color:", self.color_button)
        layer_form.addRow("Grosor:", self.width_input)
        layer_form.addRow(self.common_beam_check)
        layer_form.addRow(self.order_scale_check)
        layer_form.addRow(self.add_layer_button)
        panel_layout.addWidget(layer_box)

        manager_box = QGroupBox("Capas CZSpec")
        manager_layout = QVBoxLayout(manager_box)
        self.layer_list = QListWidget()
        self.layer_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.layer_list.setMinimumHeight(120)
        manager_layout.addWidget(self.layer_list)
        manager_buttons = QHBoxLayout()
        self.remove_layer_button = QPushButton("Quitar")
        self.clear_layers_button = QPushButton("Vaciar")
        manager_buttons.addWidget(self.remove_layer_button)
        manager_buttons.addWidget(self.clear_layers_button)
        manager_layout.addLayout(manager_buttons)
        panel_layout.addWidget(manager_box)

        output_box = QGroupBox("Guardar y abrir productos")
        output_grid = QGridLayout(output_box)
        self.save_session_button = QPushButton("Guardar sesión JSON")
        self.save_image_button = QPushButton("Capturar visor")
        output_grid.addWidget(self.save_session_button, 0, 0)
        output_grid.addWidget(self.save_image_button, 0, 1)
        for index, (label, path) in enumerate(
            (
                ("Guardado general", SPATIAL_REPRESENTATION_OUTPUT_DIR),
                ("Gráficos", SPATIAL_GRAPHICS_DIR),
                ("Tablas", SPATIAL_TABLES_DIR),
                ("Imágenes", SPATIAL_IMAGES_DIR),
            )
        ):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, p=path: open_folder_in_system(p))
            output_grid.addWidget(button, 1 + index // 2, index % 2)
        panel_layout.addWidget(output_box)

        warning = QLabel(
            "Advertencia permanente: el fondo HiPS/FITS es observacional; los contornos "
            "moleculares de CZSpec son perfiles paramétricos comparativos de datos de "
            "antena única. No son mapas resueltos, centroides medidos ni fronteras físicas."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet(
            "background:#FFF7ED;color:#9A3412;border:1px solid #FDBA74;"
            "border-radius:8px;padding:10px;"
        )
        panel_layout.addWidget(warning)
        panel_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(panel)
        splitter.addWidget(scroll)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        viewer_box = QGroupBox("Aladin Lite · contexto multibanda y capas moleculares")
        viewer_layout = QVBoxLayout(viewer_box)
        self.viewer_stack = QStackedWidget()
        placeholder = QWidget()
        placeholder_layout = QVBoxLayout(placeholder)
        placeholder_layout.addStretch()
        placeholder_label = QLabel(
            "El visor se carga únicamente al abrir M6 para no ralentizar el inicio de CZSpec.\n"
            "Requiere conexión a Internet para consultar los fondos HiPS de CDS."
        )
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setWordWrap(True)
        self.start_viewer_button = QPushButton("Iniciar entorno espacial")
        self.start_viewer_button.setMaximumWidth(260)
        placeholder_layout.addWidget(placeholder_label)
        placeholder_layout.addWidget(self.start_viewer_button, alignment=Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addStretch()
        self.viewer_stack.addWidget(placeholder)
        viewer_layout.addWidget(self.viewer_stack)
        self.status = QLabel("Visor espacial aún no iniciado.")
        self.status.setWordWrap(True)
        viewer_layout.addWidget(self.status)
        right_layout.addWidget(viewer_box)
        splitter.addWidget(right)
        splitter.setSizes([380, 1050])

        self.source_combo.currentIndexChanged.connect(self._apply_source_preset)
        self.update_field_button.clicked.connect(self.apply_field)
        self.start_viewer_button.clicked.connect(self.activate_viewer)
        self.record_combo.currentIndexChanged.connect(self._record_changed)
        self.profile_combo.currentIndexChanged.connect(self._profile_changed)
        self.color_button.clicked.connect(self._choose_color)
        self.add_layer_button.clicked.connect(self.add_layer)
        self.remove_layer_button.clicked.connect(self.remove_layer)
        self.clear_layers_button.clicked.connect(self.clear_layers)
        self.layer_list.itemChanged.connect(self._layer_visibility_changed)
        self.save_session_button.clicked.connect(self.save_session)
        self.save_image_button.clicked.connect(self.save_screenshot)
        self._apply_source_preset(0)
        self._profile_changed()

    def refresh(self):
        mod_df, mth_df, dataset = self.data_provider()
        self.records = extract_column_density_records(mod_df, mth_df, dataset=dataset)
        current_key = self.record_combo.currentData()
        self.record_combo.blockSignals(True)
        self.record_combo.clear()
        ordered = sorted(
            enumerate(self.records),
            key=lambda pair: (
                pair[1].method,
                pair[1].frequency_mhz if math.isfinite(pair[1].frequency_mhz) else math.inf,
                pair[1].species.casefold(),
                pair[1].tex_k,
            ),
        )
        for original_index, record in ordered:
            n_text = f"N={record.column_density_cm2:.3e} cm⁻²"
            tau_text = f" · τ={record.tau:.3g}" if math.isfinite(record.tau) else ""
            self.record_combo.addItem(
                f"{record.label} · Tₑₓ={record.tex_k:g} K · {n_text}{tau_text}",
                original_index,
            )
        if not ordered:
            self.record_combo.addItem("Ejecuta MOD/MTH en el módulo 3", None)
        previous_index = self.record_combo.findData(current_key)
        if previous_index >= 0:
            self.record_combo.setCurrentIndex(previous_index)
        self.record_combo.blockSignals(False)
        self.add_layer_button.setEnabled(bool(ordered))
        self._record_changed()

    def _apply_source_preset(self, _index=None):
        ra, dec, fov = self.source_combo.currentData()
        if ra is not None:
            self.ra_input.setValue(float(ra))
            self.dec_input.setValue(float(dec))
            self.fov_input.setValue(float(fov))

    def _record_changed(self):
        index = self.record_combo.currentData()
        if index is None or not (0 <= int(index) < len(self.records)):
            return
        record = self.records[int(index)]
        family, profile = _family_for_species(record.species)
        family_index = self.family_combo.findText(family)
        if family_index >= 0:
            self.family_combo.setCurrentIndex(family_index)
        profile_index = self.profile_combo.findData(profile)
        if profile_index >= 0:
            self.profile_combo.setCurrentIndex(profile_index)

    def _profile_changed(self):
        self.ring_input.setEnabled(self.profile_combo.currentData() == "anular")

    def _choose_color(self):
        color = QColorDialog.getColor(QColor(self.color), self, "Color de la capa")
        if color.isValid():
            self.color = color.name().upper()
            self._update_color_button()

    def _update_color_button(self):
        self.color_button.setText(self.color)
        self.color_button.setStyleSheet(
            f"background:{self.color};color:{'#0F172A' if QColor(self.color).lightness() > 150 else 'white'};"
        )

    def _levels(self) -> list[float]:
        levels = []
        for part in self.levels_input.text().replace(";", ",").split(","):
            if part.strip():
                levels.append(float(part.strip()))
        if not levels or any(not 0 < value < 1 for value in levels):
            raise ValueError("Escribe niveles entre 0 y 1, por ejemplo 0.2,0.4,0.6,0.8.")
        return sorted(set(levels))

    def activate_viewer(self):
        if not online_enabled():
            self.status.setText("Aladin Lite se omite en modo sin Internet.")
            return
        if self.viewer is not None:
            return
        try:
            from PySide6.QtWebChannel import QWebChannel
            from PySide6.QtWebEngineCore import QWebEngineSettings
            from PySide6.QtWebEngineWidgets import QWebEngineView
        except ImportError as exc:
            self.status.setText(f"Qt WebEngine no está disponible: {exc}")
            return
        self.viewer = QWebEngineView()
        self.viewer.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
        )
        self.viewer.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
        )
        self.bridge = AladinBridge(self)
        self.bridge.statusChanged.connect(self.status.setText)
        self.channel = QWebChannel(self.viewer.page())
        self.channel.registerObject("czspecBridge", self.bridge)
        self.viewer.page().setWebChannel(self.channel)
        self.viewer.loadFinished.connect(self._viewer_loaded)
        self.viewer_stack.addWidget(self.viewer)
        self.viewer_stack.setCurrentWidget(self.viewer)
        html_path = PACKAGE_DIR / "resources" / "aladin" / "m6_viewer.html"
        self.viewer.load(QUrl.fromLocalFile(str(html_path)))
        self.status.setText("Cargando Aladin Lite desde CDS…")

    def _viewer_loaded(self, ok: bool):
        self._viewer_ready = bool(ok)
        if not ok:
            self.status.setText("No se pudo abrir la página local del visor espacial.")
            return
        self.apply_field()
        self._render_layers()

    def _run_js(self, code: str):
        if self.viewer is not None and self._viewer_ready:
            self.viewer.page().runJavaScript(code)

    def apply_field(self):
        self.activate_viewer()
        ra = self.ra_input.value()
        dec = self.dec_input.value()
        fov = self.fov_input.value()
        survey = self.survey_combo.currentData()
        overlay = self.overlay_combo.currentData()
        self._run_js(f"window.czspecSetTarget({ra}, {dec}, {fov});")
        self._run_js(f"window.czspecSetSurvey({json.dumps(survey)});")
        if overlay:
            self._run_js(
                f"window.czspecSetOverlaySurvey({json.dumps(overlay)}, {self.overlay_opacity.value()});"
            )
        self.status.setText(f"Campo ICRS aplicado: RA={ra:.6f}°, Dec={dec:.6f}°.")

    def add_layer(self):
        index = self.record_combo.currentData()
        if index is None:
            self.status.setText("No hay una solución de M3 seleccionada.")
            return
        try:
            levels = self._levels()
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        record = self.records[int(index)]
        observed_beam = 17.0 if math.isfinite(record.frequency_mhz) and record.frequency_mhz >= 120000 else 29.0
        scale = self.scale_input.value()
        common_beam = None
        if self.common_beam_check.isChecked():
            scale = homogenized_sigma_arcsec(scale, observed_beam, 29.0)
            common_beam = 29.0
        if self.order_scale_check.isChecked() and record.column_density_cm2 > 0:
            decade = int(math.floor(math.log10(record.column_density_cm2)))
            scale *= max(0.75, min(1.55, 1.0 + 0.08 * (decade - 13)))
        name = (
            f"{record.species} · {record.method} · Tₑₓ={record.tex_k:g} K · "
            f"N={record.column_density_cm2:.2e} cm⁻²"
        )
        layer = SpatialLayerSpec(
            layer_id=uuid.uuid4().hex[:10],
            name=name,
            family=self.family_combo.currentText(),
            profile=self.profile_combo.currentData(),
            center_ra_deg=self.ra_input.value(),
            center_dec_deg=self.dec_input.value(),
            scale_arcsec=scale,
            ring_radius_arcsec=self.ring_input.value(),
            color=self.color,
            line_width=self.width_input.value(),
            levels=levels,
            method=record.method,
            tex_k=record.tex_k,
            molecule=record.species,
            column_density_cm2=record.column_density_cm2,
            uncertainty_cm2=(record.uncertainty_cm2 if math.isfinite(record.uncertainty_cm2) else None),
            observed_beam_arcsec=observed_beam,
            common_beam_arcsec=common_beam,
        )
        self.layers.append(layer)
        self._refresh_layer_list()
        self._render_layers()
        self.status.setText(
            f"Capa añadida: {record.species}. Perfil {layer.profile}; s efectivo={scale:.2f}″."
        )

    def _refresh_layer_list(self):
        self.layer_list.blockSignals(True)
        self.layer_list.clear()
        for layer in self.layers:
            item = QListWidgetItem(f"{layer.molecule} · {layer.family} · {layer.profile}")
            item.setData(Qt.ItemDataRole.UserRole, layer.layer_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if layer.visible else Qt.CheckState.Unchecked)
            item.setForeground(QColor(layer.color))
            item.setToolTip(layer.name)
            self.layer_list.addItem(item)
        self.layer_list.blockSignals(False)

    def _layer_visibility_changed(self, item: QListWidgetItem):
        layer_id = item.data(Qt.ItemDataRole.UserRole)
        for layer in self.layers:
            if layer.layer_id == layer_id:
                layer.visible = item.checkState() == Qt.CheckState.Checked
                break
        self._render_layers()

    def _render_layers(self):
        try:
            payload = aladin_payload(self.layers)
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        self._run_js(f"window.czspecSetLayers({json.dumps(payload, ensure_ascii=False)});")

    def remove_layer(self):
        item = self.layer_list.currentItem()
        if item is None:
            return
        layer_id = item.data(Qt.ItemDataRole.UserRole)
        self.layers = [layer for layer in self.layers if layer.layer_id != layer_id]
        self._refresh_layer_list()
        self._render_layers()

    def clear_layers(self):
        self.layers.clear()
        self._refresh_layer_list()
        self._render_layers()

    def _session_payload(self) -> dict:
        return {
            "schema": "czspec-spatial-session-v1",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "field": {
                "source": self.source_combo.currentText(),
                "ra_deg": self.ra_input.value(),
                "dec_deg": self.dec_input.value(),
                "fov_deg": self.fov_input.value(),
                "base_hips": self.survey_combo.currentData(),
                "overlay_hips": self.overlay_combo.currentData(),
                "overlay_opacity": self.overlay_opacity.value(),
            },
            "interpretation": (
                "El fondo es observacional; los contornos moleculares son perfiles "
                "paramétricos comparativos y no mapas resueltos."
            ),
            "layers": [layer.as_dict() for layer in self.layers],
        }

    def save_session(self):
        SPATIAL_TABLES_DIR.mkdir(parents=True, exist_ok=True)
        default = SPATIAL_TABLES_DIR / f"sesion_espacial_{datetime.now():%Y%m%d_%H%M%S}.json"
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar sesión espacial", str(default), "JSON (*.json)"
        )
        if path:
            Path(path).write_text(
                json.dumps(self._session_payload(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.status.setText(f"Sesión espacial guardada: {path}")

    def save_screenshot(self):
        if self.viewer is None:
            self.status.setText("Inicia el visor antes de capturar una imagen.")
            return
        SPATIAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        default = SPATIAL_IMAGES_DIR / f"campo_espacial_{datetime.now():%Y%m%d_%H%M%S}.png"
        path, _ = QFileDialog.getSaveFileName(self, "Capturar visor", str(default), "PNG (*.png)")
        if path:
            self.viewer.grab().save(path, "PNG")
            self.status.setText(f"Captura guardada: {path}")
