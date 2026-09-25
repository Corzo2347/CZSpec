"""Configuración no modal del modelo no-LTE de M4."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from czspec.network import online_enabled

from czspec.logic.nonlte_model import (
    SUPPORTED_GEOMETRIES,
    file_sha256,
    lamda_molecule_name,
)
from czspec.paths import LAMDA_DATA_DIR


def _identity(value: str) -> str:
    text = str(value or "").split(" v =", 1)[0].split("[", 1)[0]
    text = text.replace("&Sigma;", "").replace("Σ", "")
    return re.sub(r"[^a-z0-9+]", "", text.casefold())


class NonLTEConfigDialog(QDialog):
    """Mesa de archivos LAMDA y condiciones colisionales."""

    run_requested = Signal(object)
    assignments_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Modelo no-LTE RADEX/LAMDA — CZSpec")
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.resize(930, 690)
        self.components = []
        self.assignments = {}

        root = QVBoxLayout(self)
        intro = QLabel(
            "Asigna a cada componente de M3 un archivo LAMDA con tasas "
            "colisionales. Tkin y las densidades son entradas; Tₑₓ y τ se "
            "resolverán por transición. Los archivos importados se copian al "
            "espacio de trabajo para conservar la sesión."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Usar", "Componente M3", "Método", "Molécula LAMDA", "Archivo", "Estado"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for column in (2, 3, 4, 5):
            self.table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeToContents
            )
        self.table.itemChanged.connect(self._on_check_changed)
        root.addWidget(self.table, stretch=1)

        files_row = QHBoxLayout()
        assign = QPushButton("Asignar archivo LAMDA…")
        assign.clicked.connect(self.assign_selected_file)
        import_many = QPushButton("Importar varios y autoasignar…")
        import_many.clicked.connect(self.import_many)
        clear = QPushButton("Quitar asignación")
        clear.clicked.connect(self.clear_selected_assignment)
        folder = QPushButton("Abrir datos LAMDA")
        folder.clicked.connect(self.open_lamda_folder)
        official = QPushButton("Sitio oficial LAMDA")
        official.setEnabled(online_enabled())
        if not online_enabled():
            official.setToolTip("Disponible en modo Online")
        official.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl("https://home.strw.leidenuniv.nl/~moldata/")
            ) if online_enabled() else None
        )
        for widget in (assign, import_many, clear, folder, official):
            files_row.addWidget(widget)
        root.addLayout(files_row)

        conditions = QFormLayout()
        conditions.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.tkin = QDoubleSpinBox()
        self.tkin.setRange(0.1, 100000.0)
        self.tkin.setDecimals(3)
        self.tkin.setValue(20.0)
        self.tkin.setSuffix(" K")
        self.h2_density = QLineEdit("1e4")
        self.h2_density.setToolTip("Densidad total de H₂ en cm⁻³.")
        self.opr = QDoubleSpinBox()
        self.opr.setRange(0.0, 1000.0)
        self.opr.setDecimals(4)
        self.opr.setValue(3.0)
        self.geometry = QComboBox()
        for key, label in SUPPORTED_GEOMETRIES.items():
            self.geometry.addItem(label, key)
        self.overlap = QCheckBox("Tratar solapamiento de líneas")
        self.background = QDoubleSpinBox()
        self.background.setRange(0.0, 1000.0)
        self.background.setDecimals(3)
        self.background.setValue(2.725)
        self.background.setSuffix(" K")
        self.extra_colliders = QLineEdit("e=0, H=0, He=0, H+=0")
        self.extra_colliders.setToolTip(
            "Densidades adicionales en cm⁻³. Sólo se usarán colisionadores "
            "presentes en el archivo LAMDA."
        )
        conditions.addRow("Temperatura cinética Tkin:", self.tkin)
        conditions.addRow("Densidad total n(H₂) [cm⁻³]:", self.h2_density)
        conditions.addRow("Razón orto/para de H₂:", self.opr)
        conditions.addRow("Geometría:", self.geometry)
        conditions.addRow("Fondo continuo:", self.background)
        conditions.addRow("Otros colisionadores:", self.extra_colliders)
        conditions.addRow("Solapamiento:", self.overlap)
        root.addLayout(conditions)

        note = QLabel(
            "CZSpec rechaza Tkin fuera del intervalo tabulado por LAMDA en vez "
            "de extrapolar silenciosamente. Para-H₂ y orto-H₂ se reparten desde "
            "n(H₂) usando la razón indicada cuando el archivo los separa."
        )
        note.setWordWrap(True)
        root.addWidget(note)

        footer = QHBoxLayout()
        self.summary = QLabel("Sin componentes preparadas.")
        self.summary.setWordWrap(True)
        footer.addWidget(self.summary, stretch=1)
        run = QPushButton("Generar modelo no-LTE global")
        run.clicked.connect(self.emit_run)
        close = QPushButton("Cerrar")
        close.clicked.connect(self.hide)
        footer.addWidget(run)
        footer.addWidget(close)
        root.addLayout(footer)

    def set_state(self, components, assignments, defaults=None):
        self.components = list(components or [])
        self.assignments = dict(assignments or {})
        defaults = dict(defaults or {})
        if defaults:
            self.tkin.setValue(float(defaults.get("tkin_k", self.tkin.value())))
            self.h2_density.setText(str(defaults.get("h2_density_cm3", "1e4")))
            self.opr.setValue(float(defaults.get("h2_opr", self.opr.value())))
            index = self.geometry.findData(defaults.get("geometry"))
            if index >= 0:
                self.geometry.setCurrentIndex(index)
            self.background.setValue(
                float(defaults.get("background_temperature_k", self.background.value()))
            )
            self.overlap.setChecked(bool(defaults.get("treat_line_overlap", False)))
            extras = defaults.get("additional_colliders_cm3")
            if extras:
                self.extra_colliders.setText(
                    ", ".join(f"{key}={value:g}" for key, value in extras.items())
                )
        self.refresh_table()

    @staticmethod
    def component_key(component) -> str:
        return str(component.get("solution_key") or component.get("label"))

    def refresh_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.components))
        assigned_count = 0
        for row_index, component in enumerate(self.components):
            key = self.component_key(component)
            assignment = self.assignments.get(key, {})
            path = Path(str(assignment.get("path", "")))
            valid = path.is_file()
            assigned_count += int(valid)
            enabled = QTableWidgetItem()
            enabled.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            enabled.setCheckState(
                Qt.CheckState.Checked
                if valid and assignment.get("enabled", True)
                else Qt.CheckState.Unchecked
            )
            enabled.setData(Qt.ItemDataRole.UserRole, key)
            self.table.setItem(row_index, 0, enabled)
            solution = component.get("solution", {})
            values = (
                component.get("label", key),
                solution.get("method", ""),
                assignment.get("molecule", "—"),
                path.name if valid else "—",
                "Listo" if valid else "Requiere LAMDA",
            )
            for column, value in enumerate(values, start=1):
                item = QTableWidgetItem(str(value))
                if column == 4 and valid:
                    item.setToolTip(str(path))
                self.table.setItem(row_index, column, item)
        self.summary.setText(
            f"{len(self.components)} componente(s) de M3; "
            f"{assigned_count} con archivo LAMDA asignado."
        )
        self.table.blockSignals(False)

    def _selected_component(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.components):
            return None
        return self.components[row]

    def _copy_lamda_file(self, source: str | Path) -> dict:
        source = Path(source)
        molecule = lamda_molecule_name(source)
        digest = file_sha256(source)
        LAMDA_DATA_DIR.mkdir(parents=True, exist_ok=True)
        target = LAMDA_DATA_DIR / f"{source.stem}-{digest[:10]}{source.suffix or '.dat'}"
        if not target.exists():
            shutil.copy2(source, target)
        return {"path": str(target), "molecule": molecule, "sha256": digest, "enabled": True}

    def assign_selected_file(self):
        component = self._selected_component()
        if component is None:
            self.summary.setText("Selecciona primero una componente de la tabla.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo LAMDA",
            str(Path.home()),
            "Archivos LAMDA (*.dat *.txt);;Todos los archivos (*)",
        )
        if not path:
            return
        try:
            self.assignments[self.component_key(component)] = self._copy_lamda_file(path)
        except Exception as exc:
            self.summary.setText(f"No se pudo importar: {exc}")
            return
        self.assignments_changed.emit(dict(self.assignments))
        self.refresh_table()

    def import_many(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Importar archivos LAMDA",
            str(Path.home()),
            "Archivos LAMDA (*.dat *.txt);;Todos los archivos (*)",
        )
        if not paths:
            return
        imported = []
        for path in paths:
            try:
                imported.append(self._copy_lamda_file(path))
            except Exception:
                continue
        assigned = 0
        for component in self.components:
            key = self.component_key(component)
            if key in self.assignments and Path(
                str(self.assignments[key].get("path", ""))
            ).is_file():
                continue
            row = component.get("row", {})
            target = _identity(row.get("name", "") if hasattr(row, "get") else "")
            if not target:
                target = _identity(component.get("label", ""))
            matches = [item for item in imported if _identity(item["molecule"]) == target]
            if len(matches) == 1:
                self.assignments[key] = dict(matches[0])
                assigned += 1
        self.assignments_changed.emit(dict(self.assignments))
        self.refresh_table()
        self.summary.setText(
            f"Se importaron {len(imported)} archivo(s) y se autoasignaron {assigned}. "
            "Los restantes pueden asignarse manualmente."
        )

    def clear_selected_assignment(self):
        component = self._selected_component()
        if component is None:
            return
        self.assignments.pop(self.component_key(component), None)
        self.assignments_changed.emit(dict(self.assignments))
        self.refresh_table()

    def _on_check_changed(self, item):
        if item.column() != 0:
            return
        key = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if key in self.assignments:
            self.assignments[key]["enabled"] = (
                item.checkState() == Qt.CheckState.Checked
            )
            self.assignments_changed.emit(dict(self.assignments))

    def open_lamda_folder(self):
        LAMDA_DATA_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(LAMDA_DATA_DIR)))

    @staticmethod
    def _positive_number(text: str, label: str) -> float:
        try:
            value = float(str(text).strip())
        except ValueError as exc:
            raise ValueError(f"{label} no es un número válido.") from exc
        if value <= 0:
            raise ValueError(f"{label} debe ser mayor que cero.")
        return value

    def _additional_colliders(self) -> dict[str, float]:
        allowed = {"e", "H", "He", "H+"}
        result = {}
        for part in self.extra_colliders.text().split(","):
            if not part.strip():
                continue
            if "=" not in part:
                raise ValueError("Usa el formato e=0, H=0, He=0, H+=0.")
            key, raw = [value.strip() for value in part.split("=", 1)]
            if key not in allowed:
                raise ValueError(f"Colisionador no reconocido: {key}")
            value = float(raw)
            if value < 0:
                raise ValueError("Las densidades adicionales no pueden ser negativas.")
            result[key] = value
        return result

    def configuration(self) -> dict:
        selected = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            key = str(item.data(Qt.ItemDataRole.UserRole) or "")
            assignment = self.assignments.get(key, {})
            if (
                item.checkState() == Qt.CheckState.Checked
                and Path(str(assignment.get("path", ""))).is_file()
            ):
                selected.append(key)
        if not selected:
            raise ValueError("Activa al menos una componente con archivo LAMDA.")
        return {
            "selected_component_keys": selected,
            "assignments": dict(self.assignments),
            "tkin_k": float(self.tkin.value()),
            "h2_density_cm3": self._positive_number(
                self.h2_density.text(), "n(H₂)"
            ),
            "h2_opr": float(self.opr.value()),
            "geometry": str(self.geometry.currentData()),
            "background_temperature_k": float(self.background.value()),
            "additional_colliders_cm3": self._additional_colliders(),
            "treat_line_overlap": bool(self.overlap.isChecked()),
        }

    def emit_run(self):
        try:
            configuration = self.configuration()
        except Exception as exc:
            self.summary.setText(str(exc))
            return
        self.run_requested.emit(configuration)

    def state_json(self) -> str:
        return json.dumps(self.assignments, ensure_ascii=False)
