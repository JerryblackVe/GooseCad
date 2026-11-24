"""Select ordered Boolean operands; calculation runs on the worker."""
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QComboBox,
                               QLabel,QDialogButtonBox)
from goosecad.document.primitives import BooleanSpec


class BooleanDialog(QDialog):
    def __init__(self,bodies,parent=None):
        super().__init__(parent)
        bodies=tuple(bodies)
        if len(bodies)<2 or len(set(bodies))!=len(bodies):
            raise ValueError("Two distinct terminal bodies required")
        self.setWindowTitle("Operación booleana")
        layout=QVBoxLayout(self)
        form=QFormLayout()
        self.kind=QComboBox(self)
        for title,kind in (("Unión","union"),("Diferencia A − B","cut"),("Intersección","common")):
            self.kind.addItem(title,kind)
        self.left=QComboBox(self)
        self.right=QComboBox(self)
        self.left.addItems(bodies)
        self.right.addItems(bodies)
        self.right.setCurrentIndex(1)
        for label,widget in (("Operación",self.kind),("Cuerpo A",self.left),("Cuerpo B",self.right)):
            widget.setAccessibleName(label)
            form.addRow(label,widget)
        layout.addLayout(form)
        hint=QLabel("El orden importa para la diferencia. Los operandos se conservan "
                    "en el historial paramétrico y dejan de ser cuerpos finales.",self)
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                      QDialogButtonBox.StandardButton.Cancel,self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.left.currentIndexChanged.connect(self._validate)
        self.right.currentIndexChanged.connect(self._validate)
        layout.addWidget(self.buttons)
        self._validate()

    def _validate(self):
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            self.left.currentText()!=self.right.currentText())

    def specification(self):
        return BooleanSpec(self.kind.currentData(),self.left.currentText(),self.right.currentText())
