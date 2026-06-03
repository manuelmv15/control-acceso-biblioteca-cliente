from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from datetime import datetime


class WidgetFlotatante(QWidget):
    cerrar_sesion = pyqtSignal()
    actualizar_datos = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._sesion_inicio: datetime | None = None
        self._duracion_ms: int = 0
        self._expandido = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._actualizar)
        self._construir_ui()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.panel = QWidget()
        self.panel.setObjectName("flotante-panel")
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(16, 14, 16, 14)
        panel_layout.setSpacing(10)

        lbl = QLabel("Tiempo restante")
        lbl.setObjectName("flotante-titulo")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(lbl)

        self.lbl_tiempo = QLabel("01:00:00")
        self.lbl_tiempo.setObjectName("flotante-timer")
        self.lbl_tiempo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(self.lbl_tiempo)

        btn_actualizar = QPushButton("Actualizar mis datos")
        btn_actualizar.setObjectName("btn-secundario")
        btn_actualizar.clicked.connect(self.actualizar_datos)
        panel_layout.addWidget(btn_actualizar)

        btn_cerrar = QPushButton("Cerrar Sesión")
        btn_cerrar.setObjectName("btn-cerrar-sesion")
        btn_cerrar.clicked.connect(self.cerrar_sesion)
        panel_layout.addWidget(btn_cerrar)

        self.panel.hide()
        layout.addWidget(self.panel)

        self.btn = QPushButton("⏱")
        self.btn.setObjectName("flotante-btn")
        self.btn.setFixedSize(56, 56)
        self.btn.clicked.connect(self._toggle)
        layout.addWidget(self.btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _toggle(self):
        self._expandido = not self._expandido
        self.panel.setVisible(self._expandido)
        self._posicionar()

    def _posicionar(self):
        self.adjustSize()
        screen = QApplication.primaryScreen().availableGeometry()
        margin = 16
        x = screen.right() - self.width() - margin
        y = screen.bottom() - self.height() - margin
        self.move(x, y)

    def iniciar_sesion(self, hora_inicio: datetime, duracion_ms: int):
        self._sesion_inicio = hora_inicio
        self._duracion_ms = duracion_ms
        self._expandido = False
        self.panel.hide()
        self._actualizar()
        self._timer.start(1000)
        self._posicionar()
        self.show()
        self.raise_()

    def detener(self):
        self._timer.stop()
        self._sesion_inicio = None
        self._expandido = False
        self.panel.hide()
        self.hide()

    def _actualizar(self):
        if not self._sesion_inicio:
            return
        transcurrido_s = (datetime.now() - self._sesion_inicio).total_seconds()
        restante_s = max(0, self._duracion_ms / 1000 - transcurrido_s)
        h = int(restante_s) // 3600
        m = (int(restante_s) % 3600) // 60
        s = int(restante_s) % 60
        self.lbl_tiempo.setText(f"{h:02d}:{m:02d}:{s:02d}")
