from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QRadioButton,
    QButtonGroup, QSpacerItem, QSizePolicy, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

CARRERAS = [
    "Ingeniería en Sistemas",
    "Ingeniería Civil",
    "Ingeniería Industrial",
    "Medicina",
    "Derecho",
    "Economía",
    "Administración de Empresas",
    "Contaduría Pública",
    "Psicología",
    "Comunicación",
    "Arquitectura",
    "Odontología",
    "Química y Farmacia",
    "Enfermería",
    "Trabajo Social",
    "Otra",
]

FACULTADES = [
    "Facultad de Ingeniería",
    "Facultad de Ciencias Médicas",
    "Facultad de Ciencias Jurídicas y Sociales",
    "Facultad de Ciencias Económicas",
    "Facultad de Humanidades",
    "Facultad de Ciencias Químicas y Farmacia",
    "Facultad de Odontología",
    "Facultad de Agronomía",
    "Otra",
]


class PantallaRegistro(QWidget):
    registro_exitoso = pyqtSignal(dict)
    cancelar = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._construir_ui()

    def _construir_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(60, 30, 60, 30)

        lbl_titulo = QLabel("Registro de Nuevo Estudiante")
        lbl_titulo.setObjectName("titulo")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(lbl_titulo)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setSpacing(16)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.nombre = QLineEdit()
        self.nombre.setPlaceholderText("Nombre completo")
        form.addRow("Nombre:", self.nombre)

        self.carnet = QLineEdit()
        self.carnet.setPlaceholderText("Número de carnet")
        form.addRow("Carnet:", self.carnet)

        self.fecha_nac = QLineEdit()
        self.fecha_nac.setPlaceholderText("YYYY-MM-DD")
        form.addRow("Fecha de nacimiento:", self.fecha_nac)

        self.carrera = QComboBox()
        self.carrera.addItems(CARRERAS)
        form.addRow("Carrera:", self.carrera)

        self.facultad = QComboBox()
        self.facultad.addItems(FACULTADES)
        form.addRow("Facultad:", self.facultad)

        self.departamento = QLineEdit()
        self.departamento.setPlaceholderText("Departamento")
        form.addRow("Departamento:", self.departamento)

        sexo_row = QHBoxLayout()
        self.sexo_group = QButtonGroup(self)
        for label, val in [("Masculino", "M"), ("Femenino", "F"), ("Otro", "O")]:
            rb = QRadioButton(label)
            rb.setProperty("valor", val)
            self.sexo_group.addButton(rb)
            sexo_row.addWidget(rb)
        sexo_row.addStretch()
        form.addRow("Sexo:", sexo_row)

        scroll.setWidget(form_widget)
        outer.addWidget(scroll)

        self.lbl_error = QLabel("")
        self.lbl_error.setObjectName("error")
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self.lbl_error)

        btn_row = QHBoxLayout()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btn-secundario")
        btn_cancelar.clicked.connect(self.cancelar)
        btn_row.addWidget(btn_cancelar)

        btn_guardar = QPushButton("Registrarme")
        btn_guardar.clicked.connect(self._guardar)
        btn_row.addWidget(btn_guardar)
        outer.addLayout(btn_row)

    def _guardar(self):
        import uuid
        from datetime import date
        from database import guardar_estudiante_cache
        from network import registrar_estudiante, hay_conexion

        nombre = self.nombre.text().strip()
        carnet = self.carnet.text().strip()

        if not nombre or not carnet:
            self.lbl_error.setText("Nombre y carnet son obligatorios")
            return

        sexo_btn = self.sexo_group.checkedButton()
        sexo = sexo_btn.property("valor") if sexo_btn else ""

        datos = {
            "id": str(uuid.uuid4()),
            "nombre": nombre,
            "carnet": carnet,
            "fecha_nacimiento": self.fecha_nac.text().strip() or None,
            "carrera": self.carrera.currentText(),
            "facultad": self.facultad.currentText(),
            "departamento": self.departamento.text().strip() or None,
            "sexo": sexo,
            "fecha_registro": date.today().isoformat(),
        }

        guardar_estudiante_cache({**datos, "nombre": nombre})

        if hay_conexion():
            ok = registrar_estudiante(datos)
            if not ok:
                self.lbl_error.setText("Error al registrar en servidor — guardado localmente")
        else:
            self.lbl_error.setText("Sin internet — guardado localmente, se sincronizará después")

        self.registro_exitoso.emit(datos)
        self._limpiar()

    def _limpiar(self):
        self.nombre.clear()
        self.carnet.clear()
        self.fecha_nac.clear()
        self.departamento.clear()
        self.lbl_error.setText("")
        self.sexo_group.setExclusive(False)
        for btn in self.sexo_group.buttons():
            btn.setChecked(False)
        self.sexo_group.setExclusive(True)
