"""Qt desktop workspace for native parameter documents (experimental).

Parameter commands use a single document worker; Qt/VTK refresh stays on
its owning thread. File commands and display preparation also use the worker.
"""
from pathlib import Path
from math import isfinite

from PySide6.QtCore import Qt, Signal, QTimer, QSettings, QStandardPaths
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QDockWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QFileDialog, QMessageBox,
    QListWidget, QAbstractItemView, QApplication, QInputDialog,
)
import vtk
from .viewport import OwnedViewport
from .recovery_dialog import RecoveryDialog

from goosecad.document.native import NativeDocument, Feature
from goosecad.document.session import DocumentSession
from goosecad.document.tasks import DocumentTasks
from goosecad.document.autosave import AutosaveSlot
from goosecad.parametric import Cancelled
from goosecad.view.scene import Scene
from goosecad.view.preparation import terminal_bodies


def sample_session():
    return DocumentSession(NativeDocument(
        {"width": 20, "depth": 30, "height": 40},
        (Feature("box", "box", ("width", "depth", "height")),),
    ))


class MainWindow(QMainWindow):
    task_finished = Signal()

    def __init__(self, session=None, *, viewport_factory=OwnedViewport,
                 scene_factory=Scene, autosave_root=None, autosave_interval=None):
        super().__init__()
        self.resize(1100, 720)
        self._scene_factory = scene_factory
        self.session = None
        self.scene = None
        self.tasks = None
        self._after_task = None
        self._cancel_requested = False
        self.task_finished.connect(self._poll_task, Qt.ConnectionType.QueuedConnection)
        self._ready = False
        self._pick_observer = None
        self._staged = False
        self._view_ok = False
        local_data = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
        self._autosave_root = (Path(autosave_root) if autosave_root is not None else
                               Path(local_data) / "recovery" if local_data else None)
        self._settings = QSettings("GooseCAD", "GooseCAD Professional")
        self._persist_autosave = autosave_interval is None
        try:
            interval = int(self._settings.value("autosave/seconds", 120)
                           if autosave_interval is None else autosave_interval)
        except (TypeError, ValueError):
            interval = 120
        self._autosave_interval = min(3600, max(0, interval))
        self._autosave_slot = None
        self._autosave_timer = QTimer(self)
        self._autosave_timer.timeout.connect(self._autosave_tick)
        self.viewport = viewport_factory(self)
        self.viewport.setAccessibleName("Vista tridimensional")
        self.setCentralWidget(self.viewport)
        self._make_panels()
        self._make_actions()
        self._install(session if session is not None else sample_session())
        self._configure_autosave_timer()
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
        self.apply_button.clicked.connect(self.start_parameter_edit)
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
        self.recover_action = action(file_menu, "Recuperar versión anterior…", self.recover_dialog)
        self.autosave_recover_action = action(file_menu, "Recuperar guardado automático…", self.autosave_recover_dialog)
        self.autosave_settings_action = QAction("Configurar guardado automático…", self)
        self.autosave_settings_action.triggered.connect(self.configure_autosave)
        file_menu.addAction(self.autosave_settings_action)
        self.save_action = action(file_menu, "&Guardar", self.request_save, QKeySequence.StandardKey.Save)
        self.save_as_action = action(file_menu, "Guardar &como…", self.request_save_as, QKeySequence.StandardKey.SaveAs)
        self.undo_action = action(edit_menu, "&Deshacer", self.start_undo, QKeySequence.StandardKey.Undo)
        self.redo_action = action(edit_menu, "&Rehacer", self.start_redo, QKeySequence.StandardKey.Redo)
        self.cancel_action = action(edit_menu, "Cancelar operación", self.cancel_task)
        self.fit_action = action(view_menu, "Ajustar vista", self.fit_view)
        self.refresh_action = action(view_menu, "Actualizar vista", self.request_refresh)

    def _install(self, candidate, prepared=None):
        # Stage the new scene before discarding the previous document.
        window = self.viewport.GetRenderWindow()
        if prepared is None:
            scene = self._scene_factory(candidate.document, render_window=window)
        else:
            plan = prepared.request
            if plan.document is not candidate.document:
                raise ValueError("Prepared display does not match candidate")
            scene = self._scene_factory(candidate.document, render_window=window,
                                        cache=plan.cache, settings=plan.settings,
                                        max_vertices=plan.max_vertices,
                                        max_triangles=plan.max_triangles)
        try:
            candidate.attach_scene(scene)
            if prepared is None:
                candidate.refresh(terminal_bodies(candidate.document))
            else:
                candidate.publish_refresh(prepared)
            scene.fit()
        except Exception:
            candidate.detach_scene()
            scene.close()
            raise
        old_session, old_scene, old_tasks = self.session, self.scene, self.tasks
        self.session, self.scene = candidate, scene
        self.tasks = DocumentTasks(candidate, notify=self.task_finished.emit)
        self._autosave_slot = (AutosaveSlot(self._autosave_root, candidate.document)
                               if self._autosave_root is not None else None)
        if old_tasks is not None:
            old_tasks.close()
        if old_scene is not None:
            old_session.detach_scene()
            old_scene.close()
        self._view_ok = True
        self._populate()
        if self._ready:
            # Candidate already has valid VTK actors; do not tessellate again.
            try:
                self.viewport.show()
                self.scene.render()
            except Exception as exc:
                self._view_ok = False
                self.viewport.hide()
                self._update_actions()
                self._error(exc)

    def initialize_view(self):
        if self._ready:
            return
        self.viewport.Initialize()
        interactor = self.viewport.GetRenderWindow().GetInteractor()
        interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        self._pick_observer = interactor.AddObserver("KeyPressEvent", self._pick_key)
        self._ready = True
        self.refresh_view()

    def _pick_key(self, interactor, event):
        if self.tasks.busy or interactor.GetKeySym().lower() != "p" or not self._view_ok:
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
        busy = self.tasks.busy
        for action in (self.open_action, self.recover_action, self.autosave_recover_action,
                       self.autosave_settings_action, self.save_action, self.save_as_action, self.refresh_action):
            action.setEnabled(not busy)
        self.parameters.setEnabled(not busy)
        self.bodies.setEnabled(not busy)
        self.viewport.setEnabled(not busy)
        self.cancel_action.setEnabled(self.tasks.can_cancel and not self._cancel_requested)
        if busy:
            self.undo_action.setEnabled(False)
            self.redo_action.setEnabled(False)
            self.fit_action.setEnabled(False)
            self.apply_button.setEnabled(False)
            self.setWindowTitle("Operación en curso… — GooseCAD Professional")
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

    def _parameter_changes(self):
        current = self.session.document.parameter_values()
        changes = {}
        for row in range(self.parameters.rowCount()):
            name = self.parameters.item(row, 0).text()
            raw = self.parameters.item(row, 1).text().strip()
            if raw == str(current[name]):
                continue
            value = float(raw)
            if not isfinite(value):
                raise ValueError("Los parámetros deben ser finitos.")
            if value != current[name]:
                changes[name] = value
        return changes

    def _start_task(self, method, *args, after=None, **kwargs):
        if self.tasks.busy:
            return False
        try:
            method(*args, **kwargs)
        except Exception as exc:
            self._error(exc)
            return False
        self._after_task = after
        self._cancel_requested = False
        self.statusBar().showMessage(
            "Guardando… No interrumpa el guardado." if self.tasks.kind in ("save", "autosave")
            else "Calculando… Vista anterior; selección deshabilitada."
            if self.tasks.kind in ("mutation_display", "mesh")
            else "Operación en curso… Puede solicitar cancelación.")
        self._update_actions()
        return True

    def start_parameter_edit(self, *, after=None):
        if self.tasks.busy:
            return False
        if not self._staged:
            return after() if after is not None else True
        try:
            changes = self._parameter_changes()
            request = self.scene.plan_refresh(terminal_bodies(self.session.document))
        except Exception as exc:
            self._error(exc)
            return False
        return self._start_task(self.tasks.edit, changes, after=after,
                                expected_revision=self._editor_revision,
                                display_request=request)

    def _start_history_task(self, method):
        if self.tasks.busy or self._staged:
            return False
        try:
            request = self.scene.plan_refresh(terminal_bodies(self.session.document))
        except Exception as exc:
            self._error(exc)
            return False
        return self._start_task(method, display_request=request)

    def start_undo(self):
        return self._start_history_task(self.tasks.undo)

    def start_redo(self):
        return self._start_history_task(self.tasks.redo)

    def cancel_task(self):
        if self.tasks.request_cancel():
            self._cancel_requested = True
            self.statusBar().showMessage("Cancelación solicitada; esperando un punto seguro.")
            self._update_actions()

    def _poll_task(self):
        if self.scene is None or not self.tasks.ready:
            return
        after, self._after_task = self._after_task, None
        kind = self.tasks.kind
        try:
            result = self.tasks.collect()
        except Cancelled:
            if kind == "mesh":
                self._invalidate_display("Vista cancelada; el modelo conserva sus cambios.")
            else:
                self._update_actions()
                self.statusBar().showMessage("Operación cancelada sin publicar cambios.")
            return
        except Exception as exc:
            self._update_actions()
            if kind == "mesh":
                self._invalidate_display("Modelo conservado; vista no actualizada.")
            if kind == "autosave":
                self._autosave_timer.stop()
                self.statusBar().showMessage("Guardado automático detenido; revise la carpeta de recuperación.")
            self._error(exc)
            return
        if kind in ("open", "recovery"):
            try:
                self._install(result.session, result.prepared)
            except Exception as exc:
                self._update_actions()
                self._error(exc)
                return
            self.statusBar().showMessage(
                "Versión recuperada; guarde como documento nuevo."
                if kind == "recovery" else "Documento abierto.")
        elif kind == "save":
            self._update_actions()
            self.statusBar().showMessage("Documento guardado.")
        elif kind == "autosave":
            self._update_actions()
            if result is not None:
                self.statusBar().showMessage("Copia de recuperación actualizada; documento aún sin guardar.")
        elif kind == "mesh":
            if not self._publish_display(result):
                return
        elif kind == "mutation_display":
            self._populate()
            if result.display_error is not None:
                cancelled = isinstance(result.display_error, Cancelled)
                self._invalidate_display(
                    "Vista cancelada; cambios del modelo conservados." if cancelled
                    else "Modelo conservado; vista no actualizada.")
                if not cancelled:
                    self._error(result.display_error)
                return
            if not self._publish_display(result.prepared):
                return
        else:
            self._populate()
            self.request_refresh(after=after)
            return
        if after is not None:
            after()

    def _invalidate_display(self, message):
        self._view_ok = False
        self.viewport.hide()
        self._update_actions()
        self.statusBar().showMessage(message)

    def _publish_display(self, prepared):
        try:
            self.session.publish_refresh(prepared)
            if self.viewport.isHidden():
                self.viewport.show()
            if self._ready:
                self.scene.render()
        except Exception as exc:
            self._invalidate_display("Modelo conservado; vista no actualizada.")
            self._error(exc)
            return False
        self._view_ok = True
        self._update_actions()
        self.statusBar().showMessage("Vista actualizada.")
        return True

    def apply_parameters(self):
        """Synchronous compatibility path for direct calls/modal save-discard flow."""
        if self.tasks.busy:
            return False
        if not self._staged:
            return True
        try:
            self.session.edit(self._parameter_changes(), expected_revision=self._editor_revision)
        except Exception as exc:
            self._error(exc)
            return False
        self._populate()
        self.refresh_view()
        return True

    def _history(self, method):
        if self.tasks.busy or self._staged:
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

    def request_refresh(self, *, after=None):
        if self.tasks.busy:
            return False
        # Keep the previous display visible but non-interactive while busy;
        # only hide it if publishing the new revision fails or is cancelled.
        try:
            request = self.scene.plan_refresh(terminal_bodies(self.session.document))
        except Exception as exc:
            self._update_actions()
            self._error(exc)
            return False
        started = self._start_task(self.tasks.prepare_meshes, request, after=after)
        if not started:
            self._update_actions()
        return started

    def refresh_view(self):
        if self.tasks.busy:
            return False
        try:
            self.session.refresh(terminal_bodies(self.session.document))
            if self.viewport.isHidden():
                self.viewport.show()
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
        if self.tasks.busy or not self._view_ok:
            return
        self.scene.fit()
        if self._ready:
            self.scene.render()

    def _select_body(self):
        if self.tasks.busy:
            return
        items = self.bodies.selectedItems()
        if items:
            try:
                hit = self.session.select_body(items[0].text())
                self.statusBar().showMessage(f"Cuerpo: {hit.body}")
            except Exception as exc:
                self._error(exc)

    def _choose_save_path(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar documento nuevo", "", "GooseCAD (*.gcad)",
            options=QFileDialog.Option.DontConfirmOverwrite)
        if not path:
            return None
        if not Path(path).suffix:
            path += ".gcad"
        return Path(path)

    def _start_save(self, *, destination=None, after=None):
        if self.tasks.busy:
            return False
        if destination is None and self.session.path is None:
            destination = self._choose_save_path()
            if destination is None:
                return False
        if destination is None:
            return self._start_task(self.tasks.save, after=after)
        return self._start_task(self.tasks.save_as, destination, after=after)

    def request_save(self, *, after=None):
        return self.start_parameter_edit(after=lambda: self._start_save(after=after))

    def request_save_as(self):
        if self.tasks.busy:
            return False
        destination = self._choose_save_path()
        if destination is None:
            return False
        return self.start_parameter_edit(
            after=lambda: self._start_save(destination=destination))

    def _confirm_then(self, action):
        """Continue only after successful asynchronous save, or explicit discard."""
        if self.tasks.busy:
            return False
        if not (self.session.dirty or self._staged):
            return action()
        choice = QMessageBox.question(
            self, "Cambios sin guardar", "¿Guardar los cambios antes de continuar?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
        if choice == QMessageBox.StandardButton.Save:
            return self.request_save(after=action)
        if choice == QMessageBox.StandardButton.Discard:
            return action()
        return False

    def request_open_path(self, path, *, recovery=False, recovery_copy=False):
        return self._confirm_then(
            lambda: self._start_task(self.tasks.open, path, recovery=recovery,
                                     recovery_copy=recovery_copy,
                                     display_config=self.scene.display_config))

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
        if self.tasks.busy:
            self.statusBar().showMessage("Espere el cálculo o solicite cancelación.")
            return False
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
        if self.tasks.busy:
            return False
        path, _ = QFileDialog.getOpenFileName(self, "Abrir documento", "", "GooseCAD (*.gcad *.goosecad);;Todos (*)")
        if path:
            return self.request_open_path(path)
        return False

    def recover_path(self, path):
        if not self._can_replace():
            return False
        try:
            candidate = DocumentSession.open_recovery(path)
            self._install(candidate)
        except Exception as exc:
            self._error(exc)
            return False
        self.statusBar().showMessage("Versión recuperada; guarde como documento nuevo.")
        return True

    def recover_dialog(self):
        if self.tasks.busy:
            return False
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccione el documento principal", "", "GooseCAD (*.gcad *.goosecad);;Todos (*)")
        return self.request_open_path(path, recovery=True) if path else False

    def _configure_autosave_timer(self):
        self._autosave_timer.stop()
        if self._autosave_root is not None and self._autosave_interval:
            self._autosave_timer.start(self._autosave_interval * 1000)

    def configure_autosave(self):
        if self.tasks.busy:
            return
        interval, accepted = QInputDialog.getInt(
            self, "Guardado automático", "Intervalo en segundos (0 = desactivado):",
            self._autosave_interval, 0, 3600, 15)
        if accepted:
            self._autosave_interval = interval
            if self._persist_autosave:
                self._settings.setValue("autosave/seconds", interval)
            self._configure_autosave_timer()

    def _autosave_tick(self):
        if (self.scene is None or self.tasks.busy or self._autosave_slot is None
                or not self._autosave_interval or QApplication.activeModalWidget() is not None):
            return False
        if not self.session.dirty or self._autosave_slot.last_revision == self.session.document.revision:
            return False
        return self._start_task(self.tasks.autosave, self._autosave_slot)

    def autosave_recover_dialog(self):
        if self.tasks.busy:
            return False
        root = self._autosave_root
        if root is None or not root.is_dir():
            self.statusBar().showMessage("No hay copias automáticas disponibles.")
            return False
        active = self._autosave_slot.path if self._autosave_slot is not None else None
        dialog = RecoveryDialog(root, active_path=active, parent=self)
        if dialog.exec() and dialog.selected_path is not None:
            return self.request_open_path(dialog.selected_path, recovery_copy=True)
        return False

    def closeEvent(self, event):
        if self.scene is None:
            event.accept()
            return
        if self.tasks.busy:
            self.statusBar().showMessage("Espere a que termine la operación.")
            event.ignore()
            return
        if self.session.dirty or self._staged:
            choice = QMessageBox.question(
                self, "Cambios sin guardar", "¿Guardar los cambios antes de cerrar?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
            if choice == QMessageBox.StandardButton.Save:
                event.ignore()
                self.request_save(after=self.close)
                return
            if choice != QMessageBox.StandardButton.Discard:
                event.ignore()
                return
        self._autosave_timer.stop()
        if self.tasks is not None:
            self.tasks.close()
        if self.scene is not None:
            if self._pick_observer is not None:
                self.viewport.GetRenderWindow().GetInteractor().RemoveObserver(self._pick_observer)
                self._pick_observer = None
            self.session.detach_scene()
            self.scene.close()
            self.scene = None
        self.viewport.close()
        event.accept()
