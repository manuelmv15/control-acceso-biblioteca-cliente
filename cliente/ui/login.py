from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from pathlib import Path

from ui.log import log


class PantallaLogin(QWidget):
    login_exitoso = pyqtSignal(dict)
    ir_registro = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(80, 60, 80, 60)

        # Logo
        logo_path = Path(__file__).parent.parent / "assets" / "logo.png"
        if logo_path.exists():
            lbl_logo = QLabel()
            pix = QPixmap(str(logo_path)).scaledToHeight(100, Qt.TransformationMode.SmoothTransformation)
            lbl_logo.setPixmap(pix)
            lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl_logo)

        lbl_titulo = QLabel("Biblioteca Universitaria")
        lbl_titulo.setObjectName("titulo")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_titulo)

        lbl_sub = QLabel("Ingrese su número de carnet para continuar")
        lbl_sub.setObjectName("subtitulo")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_sub)

        layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.carnet_input = QLineEdit()
        self.carnet_input.setPlaceholderText("Número de carnet")
        self.carnet_input.setMaxLength(20)
        self.carnet_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.carnet_input.returnPressed.connect(self._intentar_login)
        layout.addWidget(self.carnet_input)

        self.lbl_error = QLabel("")
        self.lbl_error.setObjectName("error")
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_error)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        btn_registrar = QPushButton("Soy nuevo — Registrarme")
        btn_registrar.setObjectName("btn-secundario")
        btn_registrar.clicked.connect(self.ir_registro)
        btn_row.addWidget(btn_registrar)

        btn_entrar = QPushButton("Ingresar")
        btn_entrar.clicked.connect(self._intentar_login)
        btn_row.addWidget(btn_entrar)

        layout.addLayout(btn_row)

        layout.addSpacerItem(QSpacerItem(0, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def _intentar_login(self):
        from db.estudiantes import buscar_estudiante_cache, guardar_estudiante_cache
        from network.estudiantes import obtener_estudiante
        from network.client import hay_conexion

        carnet = self.carnet_input.text().strip()
        if not carnet:
            self.lbl_error.setText("Ingrese su carnet")
            return

        self.lbl_error.setText("Buscando...")

        est = buscar_estudiante_cache(carnet)
        if not est and hay_conexion():
            datos = obtener_estudiante(carnet)
            if datos:
                est = datos
                guardar_estudiante_cache({
                    "carnet": datos.get("carnet", carnet),
                    "nombre": datos.get("nombre", ""),
                    "carrera": datos.get("carrera", ""),
                    "facultad": datos.get("facultad", ""),
                    "fecha_nacimiento": datos.get("fecha_nacimiento", ""),
                    "sexo": datos.get("sexo", ""),
                })

        if est:
            log.info("Login OK — carnet %s", carnet)
            self.lbl_error.setText("")
            self.carnet_input.clear()
            self.login_exitoso.emit(est)
        else:
            log.info("Login fallido — carnet %s no encontrado", carnet)
            self.lbl_error.setText("Carnet no encontrado. ¿Es su primera vez? Regístrese.")

    def limpiar(self):
        self.carnet_input.clear()
        self.lbl_error.setText("")
        self.carnet_input.setFocus()
