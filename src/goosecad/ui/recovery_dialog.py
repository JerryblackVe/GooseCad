"""Explicit recovery management: metadata catalog, open and archive."""
from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton, QAbstractItemView, QMessageBox)
from goosecad.document.autosave import recovery_catalog, archive_recovery


class RecoveryDialog(QDialog):
    def __init__(self, root, active_path=None, parent=None):
        super().__init__(parent)
        self.root = root
        self.active_path = active_path
        self.selected_path = None
        self.setWindowTitle("Copias locales de recuperación")
        self.resize(850, 400)
        layout = QVBoxLayout(self)
        label = QLabel("Abra una copia como documento nuevo. Archivar mueve una copia "
                       "a la subcarpeta archive sin borrar sus datos.", self)
        label.setWordWrap(True)
        layout.addWidget(label)
        self.table = QTableWidget(0,5,self)
        self.table.setHorizontalHeaderLabels(["Archivo","Versión","Modificación","Bytes","Estado"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAccessibleName("Copias disponibles de recuperación")
        self.table.itemSelectionChanged.connect(self.update_buttons)
        layout.addWidget(self.table)
        buttons = QHBoxLayout()
        self.open_button = QPushButton("Abrir copia",self)
        self.archive_button = QPushButton("Archivar copia",self)
        self.refresh_button = QPushButton("Actualizar lista",self)
        close_button = QPushButton("Cerrar",self)
        for button in (self.open_button,self.archive_button,self.refresh_button,close_button):
            buttons.addWidget(button)
        self.open_button.clicked.connect(self.open_selected)
        self.archive_button.clicked.connect(self.archive_selected)
        self.refresh_button.clicked.connect(self.reload)
        close_button.clicked.connect(self.reject)
        layout.addLayout(buttons)
        self.entries = ()
        self.reload()

    def reload(self):
        try:
            self.entries = recovery_catalog(self.root)
        except Exception as exc:
            self.entries = ()
            QMessageBox.warning(self,"Recuperación",str(exc))
        self.table.setRowCount(0)
        for row, entry in enumerate(self.entries):
            self.table.insertRow(row)
            timestamp = datetime.fromtimestamp(entry.modified_ns/1e9).astimezone()
            status = ("Bloqueada" if entry.locked else
                      "Activa" if entry.primary == self.active_path else "Disponible")
            for col,value in enumerate((entry.path.name,
                    "Anterior" if entry.previous else "Actual",
                    timestamp.strftime("%Y-%m-%d %H:%M:%S %Z"),
                    str(entry.size),status)):
                self.table.setItem(row,col,QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
        self.update_buttons()

    def selected(self):
        rows = self.table.selectionModel().selectedRows()
        return self.entries[rows[0].row()] if rows else None

    def update_buttons(self):
        entry = self.selected()
        self.open_button.setEnabled(entry is not None)
        self.archive_button.setEnabled(entry is not None and not entry.locked
                                       and entry.primary != self.active_path)

    def open_selected(self):
        entry = self.selected()
        if entry is not None:
            self.selected_path = entry.path
            self.accept()

    def archive_selected(self):
        entry = self.selected()
        if entry is None or entry.locked or entry.primary == self.active_path:
            return
        answer = QMessageBox.question(self,"Archivar copia",
            "¿Mover esta copia a la carpeta archive? No se eliminarán sus datos. "
            "Asegúrese de que ningún otro GooseCAD esté usando esta copia.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            archive_recovery(self.root,entry,active_path=self.active_path)
        except Exception as exc:
            QMessageBox.warning(self,"Recuperación",str(exc))
        self.reload()
