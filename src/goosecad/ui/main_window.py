"""Qt desktop workspace for native parameter documents (experimental).

All document and VTK work currently runs on the GUI thread; asynchronous
evaluation and cancellation are a separate P0 acceptance gate.
"""
from pathlib import Path
from math import isfinite

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QDockWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QFileDialog, QMessageBox,
    QListWidget, QAbstractItemView,
)
import vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from goosecad.document.native import NativeDocument, Feature
from goosecad.document.session import DocumentSession
from goosecad.view.scene import Scene


def sample_session():
    return DocumentSession(NativeDocument(
        {"width": 20, "depth": 30, "height": 40},
        (Feature("box", "box", ("width", "depth", "height")),),
    ))


def terminal_bodies(document):
    """Avoid drawing intermediate operands over a final Boolean result."""
    consumed = {dep for feature in document.features for dep in feature.dependencies}
    return tuple(f.id for f in document.features if f.id not in consumed)


class MainWindow(QMainWindow):
    def __init__(self, session=None, *, viewport_factory=QVTKRenderWindowInteractor,
                 scene_factory=Scene):
        super().__init__()
        self.resize(1100, 720)
        self._scene_factory = scene_factory
        self.session = None
        self.scene = None
        self._ready = False
        self._staged = False
        self._view_ok = False
        self.viewport = viewport_factory(self)
        self.viewport.setAccessibleName("Vista tridimensional")
        self.setCentralWidget(self.viewport)
        self._make_panels()
        self._make_actions()
        self._install(session if session is not None else sample_session())
        self.statusBar().showMessage("Documento paramétrico experimental")

    def _make_panels(self):
        dock = QDockWidget("Parámetros", self)
        panel = QWidget(dock)
        layout = QVBoxLayout(panel)
        self.parameters = QTableWidget(0, 2, panel)
        self.parameters.setHorizontalHeaderLabels(["Parámetro", "Valor"])
        self.parameters.horizontalHeader().setStretchLastSection(True)
        self.parameters.setAccessibleName("Parámetros editables")
        self.parameters.itemChanged.connect(self._mark_staged)
        layout.addWidget(self.parameters)
        self.apply_button = QPushButton("Aplicar cambios", panel)
        self.apply_button.clicked.connect(self.apply_parameters)
        layout.addWidget(self.apply_button)
        dock.setWidget(panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        browser = QDockWidget("Operaciones", self)
        self.bodies = QListWidget(browser)
        self.bodies.setAccessibleName("Operaciones y cuerpos finales")
        self.bodies.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.bodies.itemSelectionChanged.connect(self._select_body)
        browser.setWidget(self.bodies)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, browser)

    def _make_actions(self):
        file_menu = self.menuBar().addMenu("&Archivo")
        edit_menu = self.menuBar().addMenu("&Editar")
        view_menu = self.menuBar().addMenu("&Vista")
        bar = self.addToolBar("Documento")
        def action(menu, title, callback, shortcut=None):
            result = QAction(title, self)
            if shortcut is not None:
                result.setShortcut(shortcut)
            result.triggered.connect(callback)
            menu.addAction(result)
            bar.addAction(result)
            return result
        self.open_action = action(file_menu, "&Abrir…", self.open_dialog, QKeySequence.StandardKey.Open)
        self.save_action = action(file_menu, "&Guardar", self.save_document, QKeySequence.StandardKey.Save)
        self.save_as_action = action(file_menu, "Guardar &como…", self.save_as_dialog, QKeySequence.StandardKey.SaveAs)
        self.undo_action = action(edit_menu, "&Deshacer", self.undo, QKeySequence.StandardKey.Undo)
        self.redo_action = action(edit_menu, "&Rehacer", self.redo, QKeySequence.StandardKey.Redo)
        self.fit_action = action(view_menu, "Ajustar vista", self.fit_view)
        self.refresh_action = action(view_menu, "Actualizar vista", self.refresh_view)

    def _install(self, candidate):
        # Stage the new scene before discarding the previous document.
        window = self.viewport.GetRenderWindow()
        scene = self._scene_factory(candidate.document, render_window=window)
        try:
            candidate.attach_scene(scene)
            candidate.refresh(terminal_bodies(candidate.document))
            scene.fit()
        except Exception:
            candidate.detach_scene()
            scene.close()
            raise
        old_session, old_scene = self.session, self.scene
        self.session, self.scene = candidate, scene
        if old_scene is not None:
            old_session.detach_scene()
            old_scene.close()
        self._view_ok = True
        self._populate()
        if self._ready:
            self.refresh_view()

    def initialize_view(self):
        if self._ready:
            return
        self.viewport.Initialize()
        interactor = self.viewport.GetRenderWindow().GetInteractor()
        interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        interactor.AddObserver("KeyPressEvent", self._pick_key)
        self._ready = True
        self.refresh_view()

    def _pick_key(self, interactor, event):
        if interactor.GetKeySym().lower() != "p" or not self._view_ok:
            return
        try:
            hit = self.session.select_at(*interactor.GetEventPosition())
            self.statusBar().showMessage(
                f"{hit.body}: cara local {hit.face}" if hit else "Sin selección")
            self.scene.render()
        except Exception as exc:
            self._error(exc)

    def _populate(self):
        values = self.session.document.parameter_values()
        self.parameters.blockSignals(True)
        try:
            self.parameters.setRowCount(len(values))
            for row, (name, value) in enumerate(values.items()):
                key = QTableWidgetItem(name)
                key.setFlags(key.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.parameters.setItem(row, 0, key)
                self.parameters.setItem(row, 1, QTableWidgetItem(str(value)))
        finally:
            self.parameters.blockSignals(False)
        self.bodies.blockSignals(True)
        try:
            self.bodies.clear()
            self.bodies.addItems(list(terminal_bodies(self.session.document)))
        finally:
            self.bodies.blockSignals(False)
        self._editor_revision = self.session.document.revision
        self._staged = False
        self._update_actions()

    def _mark_staged(self, item):
        self._staged = True
        self._update_actions()

    def _update_actions(self):
        if self.session is None:
            return
        undo, redo = self.session.document.history_depths
        self.undo_action.setEnabled(bool(undo) and not self._staged)
        self.redo_action.setEnabled(bool(redo) and not self._staged)
        self.apply_button.setEnabled(self._staged)
        self.fit_action.setEnabled(self._view_ok)
        name = self.session.path.name if self.session.path else "Sin título"
        self.setWindowTitle(f"{name}{' *' if self.session.dirty or self._staged else ''} — GooseCAD Professional")

    def _error(self, exc):
        QMessageBox.warning(self, "GooseCAD Professional", str(exc))

    def apply_parameters(self):
        if not self._staged:
            return True
        try:
            current = self.session.document.parameter_values()
            changes = {}
            for row in range(self.parameters.rowCount()):
                name = self.parameters.item(row, 0).text()
                raw = self.parameters.item(row, 1).text().strip()
                # Preserve exact integer representation when unchanged.
                if raw == str(current[name]):
                    continue
                value = float(raw)
                if not isfinite(value):
                    raise ValueError("Los parámetros deben ser finitos.")
                if value != current[name]:
                    changes[name] = value
            self.session.edit(changes, expected_revision=self._editor_revision)
        except Exception as exc:
            self._error(exc)
            return False
        self._populate()
        self.refresh_view()
        return True

    def _history(self, method):
        if self._staged:
            return False
        try:
            method(expected_revision=self.session.document.revision)
        except Exception as exc:
            self._error(exc)
            return False
        self._populate()
        self.refresh_view()
        return True

    def undo(self):
        return self._history(self.session.undo)

    def redo(self):
        return self._history(self.session.redo)

    def refresh_view(self):
        try:
            self.session.refresh(terminal_bodies(self.session.document))
            if self._ready:
                self.scene.render()
            self._view_ok = True
        except Exception as exc:
            # Geometry may have committed even if the visual refresh failed.
            # Hide stale pixels and leave document/save/history available.
            self._view_ok = False
            self.viewport.hide()
            self.statusBar().showMessage("Documento conservado; vista no actualizada.")
            self._error(exc)
        else:
            self.viewport.show()
        self._update_actions()
        return self._view_ok

    def fit_view(self):
        if not self._view_ok:
            return
        self.scene.fit()
        if self._ready:
            self.scene.render()

    def _select_body(self):
        items = self.bodies.selectedItems()
        if items:
            try:
                hit = self.session.select_body(items[0].text())
                self.statusBar().showMessage(f"Cuerpo: {hit.body}")
            except Exception as exc:
                self._error(exc)

    def save_document(self):
        if not self.apply_parameters():
            return False
        if self.session.path is None:
            return self.save_as_dialog()
        try:
            self.session.save()
        except Exception as exc:
            self._error(exc)
            return False
        self._update_actions()
        return True

    def save_as_path(self, path):
        if not self.apply_parameters():
            return False
        try:
            self.session.save_as(Path(path))
        except Exception as exc:
            self._error(exc)
            return False
        self._update_actions()
        return True

    def save_as_dialog(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar documento nuevo", "", "GooseCAD (*.gcad)",
            options=QFileDialog.Option.DontConfirmOverwrite)
        if not path:
            return False
        if not Path(path).suffix:
            path += ".gcad"
        return self.save_as_path(path)

    def _can_replace(self):
        if not (self.session.dirty or self._staged):
            return True
        choice = QMessageBox.question(
            self, "Cambios sin guardar", "¿Guardar los cambios antes de continuar?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
        if choice == QMessageBox.StandardButton.Save:
            return self.save_document()
        return choice == QMessageBox.StandardButton.Discard

    def open_path(self, path):
        if not self._can_replace():
            return False
        try:
            candidate = DocumentSession.open(path)
            self._install(candidate)
        except Exception as exc:
            self._error(exc)
            return False
        return True

    def open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir documento", "", "GooseCAD (*.gcad *.goosecad);;Todos (*)")
        if path:
            return self.open_path(path)
        return False

    def closeEvent(self, event):
        if not self._can_replace():
            event.ignore()
            return
        if self.scene is not None:
            self.session.detach_scene()
            self.scene.close()
            self.scene = None
        self.viewport.close()
        event.accept()
