from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from config import now_sv


class PantallaBienvenida(QWidget):
    cerrar_sesion = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sesion_inicio = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._actualizar_timer)
        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(24)
        layout.setContentsMargins(80, 60, 80, 60)

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        lbl_bienvenido = QLabel("Bienvenido(a),")
        lbl_bienvenido.setObjectName("subtitulo")
        lbl_bienvenido.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_bienvenido)

        self.lbl_nombre = QLabel("")
        self.lbl_nombre.setObjectName("nombre-estudiante")
        self.lbl_nombre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_nombre)

        self.lbl_carrera = QLabel("")
        self.lbl_carrera.setObjectName("info")
        self.lbl_carrera.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_carrera)

        lbl_tiempo_lbl = QLabel("Tiempo en sesión:")
        lbl_tiempo_lbl.setObjectName("subtitulo")
        lbl_tiempo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_tiempo_lbl)

        self.lbl_timer = QLabel("00:00:00")
        self.lbl_timer.setObjectName("timer")
        self.lbl_timer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_timer)

        self.lbl_hora_inicio = QLabel("")
        self.lbl_hora_inicio.setObjectName("info")
        self.lbl_hora_inicio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_hora_inicio)

        layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        btn = QPushButton("Cerrar Sesión")
        btn.setObjectName("btn-cerrar-sesion")
        btn.clicked.connect(self.cerrar_sesion)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacerItem(QSpacerItem(0, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def iniciar_sesion(self, estudiante: dict, hora_inicio: datetime):
        self._sesion_inicio = hora_inicio
        self.lbl_nombre.setText(estudiante.get("nombre", "Estudiante"))
        self.lbl_carrera.setText(estudiante.get("carrera", ""))
        self.lbl_hora_inicio.setText(f"Sesión iniciada: {hora_inicio.strftime('%H:%M:%S')}")
        self._actualizar_timer()
        self._timer.start(1000)

    def detener(self):
        self._timer.stop()

    def _actualizar_timer(self):
        if not self._sesion_inicio:
            return
        delta = now_sv() - self._sesion_inicio
        total = int(delta.total_seconds())
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        self.lbl_timer.setText(f"{h:02d}:{m:02d}:{s:02d}")
