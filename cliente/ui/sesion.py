from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from datetime import datetime
from core.config import now_sv
from ui.icono import cargar_icono_app


class VentanaSesion(QWidget):
    """Ventana normal (con barra de título, minimizable) que muestra el
    estado de la sesión activa mientras el estudiante usa el equipo.

    Reemplaza al antiguo widget flotante sin decoraciones: esta es una
    página completa que se comporta como cualquier ventana del sistema.
    """

    cerrar_sesion = pyqtSignal()
    actualizar_datos = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._sesion_inicio: datetime | None = None
        self._duracion_ms: int = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._actualizar)
        self.setWindowTitle("Biblioteca — Sesión activa")
        self.setWindowIcon(cargar_icono_app())
        self.resize(420, 480)
        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(48, 40, 48, 40)

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.lbl_nombre = QLabel("")
        self.lbl_nombre.setObjectName("nombre-estudiante")
        self.lbl_nombre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_nombre.setWordWrap(True)
        layout.addWidget(self.lbl_nombre)

        self.lbl_carrera = QLabel("")
        self.lbl_carrera.setObjectName("info")
        self.lbl_carrera.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_carrera.setWordWrap(True)
        layout.addWidget(self.lbl_carrera)

        lbl_titulo = QLabel("Tiempo restante")
        lbl_titulo.setObjectName("subtitulo")
        lbl_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_titulo)

        self.lbl_tiempo = QLabel("00:00:00")
        self.lbl_tiempo.setObjectName("timer")
        self.lbl_tiempo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_tiempo)

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.btn_actualizar = QPushButton("Actualizar mis datos")
        self.btn_actualizar.setObjectName("btn-secundario")
        self.btn_actualizar.clicked.connect(self.actualizar_datos)
        layout.addWidget(self.btn_actualizar, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_cerrar = QPushButton("Cerrar Sesión")
        btn_cerrar.setObjectName("btn-cerrar-sesion")
        btn_cerrar.clicked.connect(self.cerrar_sesion)
        layout.addWidget(btn_cerrar, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def iniciar_sesion(self, estudiante: dict, hora_inicio: datetime,
                        duracion_ms: int, es_invitado: bool = False):
        self._sesion_inicio = hora_inicio
        self._duracion_ms = duracion_ms
        self.lbl_nombre.setText(estudiante.get("nombre", "Estudiante"))
        self.lbl_carrera.setText(estudiante.get("carrera", ""))
        self.btn_actualizar.setVisible(not es_invitado)
        self._actualizar()
        self._timer.start(1000)
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def actualizar_estudiante(self, estudiante: dict):
        """Refresca nombre/carrera sin reiniciar el cronómetro (usado tras
        editar los datos desde 'Actualizar mis datos')."""
        self.lbl_nombre.setText(estudiante.get("nombre", "Estudiante"))
        self.lbl_carrera.setText(estudiante.get("carrera", ""))

    def detener(self):
        self._timer.stop()
        self._sesion_inicio = None
        self.hide()

    def _actualizar(self):
        if not self._sesion_inicio:
            return
        transcurrido_s = (now_sv() - self._sesion_inicio).total_seconds()
        restante_s = max(0, self._duracion_ms / 1000 - transcurrido_s)
        h = int(restante_s) // 3600
        m = (int(restante_s) % 3600) // 60
        s = int(restante_s) % 60
        self.lbl_tiempo.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def closeEvent(self, event):
        # La X minimiza en lugar de cerrar: la sesión sigue activa aunque
        # el estudiante quite esta ventana de en medio.
        event.ignore()
        self.showMinimized()
