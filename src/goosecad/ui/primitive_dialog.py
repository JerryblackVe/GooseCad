"""Accessible numeric primitive template dialog; geometry is built elsewhere."""
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QComboBox,
                               QDoubleSpinBox,QDialogButtonBox,QLabel)
from goosecad.document.primitives import PrimitiveSpec, PRIMITIVES

_LABELS = {"width":"Ancho (mm)","depth":"Profundidad (mm)",
           "height":"Altura (mm)","radius":"Radio (mm)"}
_DEFAULTS = {"width":20,"depth":30,"height":40,"radius":10}


class PrimitiveDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo documento sólido")
        self.setMinimumWidth(360)
        layout=QVBoxLayout(self)
        description=QLabel("Cree un documento nuevo con una primitiva paramétrica.",self)
        description.setWordWrap(True)
        layout.addWidget(description)
        form=QFormLayout()
        self.kind=QComboBox(self)
        self.kind.setAccessibleName("Tipo de sólido")
        for label,kind in (("Caja","box"),("Cilindro","cylinder"),("Esfera","sphere")):
            self.kind.addItem(label,kind)
        form.addRow("Tipo de sólido",self.kind)
        self.inputs={}
        self.labels={}
        for name,label in _LABELS.items():
            spin=QDoubleSpinBox(self)
            spin.setDecimals(6)
            spin.setRange(.000001,1_000_000)
            spin.setValue(_DEFAULTS[name])
            spin.setAccessibleName(label)
            caption=QLabel(label,self)
            caption.setBuddy(spin)
            form.addRow(caption,spin)
            self.inputs[name]=spin
            self.labels[name]=caption
        layout.addLayout(form)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                 QDialogButtonBox.StandardButton.Cancel,self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.kind.currentIndexChanged.connect(self._update_fields)
        self._update_fields()

    def _update_fields(self):
        visible=PRIMITIVES[self.kind.currentData()]
        for name,spin in self.inputs.items():
            spin.setVisible(name in visible)
            self.labels[name].setVisible(name in visible)

    def specification(self):
        kind=self.kind.currentData()
        return PrimitiveSpec(kind,tuple(self.inputs[name].value()
                                       for name in PRIMITIVES[kind]))
