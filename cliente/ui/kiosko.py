import uuid
from datetime import datetime, date
from pathlib import Path

from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QApplication
from PyQt6.QtCore import Qt, QKeyCombination
from PyQt6.QtGui import QKeySequence, QShortcut

from ui.login import PantallaLogin
from ui.registro import PantallaRegistro
from ui.bienvenida import PantallaBienvenida
from database import guardar_sesion, actualizar_hora_fin
from config import PC_ID

PANTALLA_LOGIN = 0
PANTALLA_REGISTRO = 1
PANTALLA_SESION = 2

SALIDA_SECRETA = QKeySequence(
    QKeyCombination(
        Qt.KeyboardModifier.ControlModifier |
        Qt.KeyboardModifier.ShiftModifier |
        Qt.KeyboardModifier.AltModifier,
        Qt.Key.Key_Q
    )
)


class VentanaKiosko(QMainWindow):
    def __init__(self):
        super().__init__()
        self._sesion_activa_id: str | None = None
        self._sesion_inicio: datetime | None = None

        self._configurar_ventana()
        self._cargar_estilos()
        self._construir_ui()
        self._registrar_atajos()

    def _configurar_ventana(self):
        self.setWindowTitle("Biblioteca")
        self.showFullScreen()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.CustomizeWindowHint
        )
        self.setWindowState(Qt.WindowState.WindowFullScreen)

    def _cargar_estilos(self):
        qss_path = Path(__file__).parent / "estilos.qss"
        if qss_path.exists():
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    def _construir_ui(self):
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login = PantallaLogin()
        self.registro = PantallaRegistro()
        self.bienvenida = PantallaBienvenida()

        self.stack.addWidget(self.login)
        self.stack.addWidget(self.registro)
        self.stack.addWidget(self.bienvenida)

        self.login.login_exitoso.connect(self._on_login)
        self.login.ir_registro.connect(lambda: self.stack.setCurrentIndex(PANTALLA_REGISTRO))
        self.registro.registro_exitoso.connect(self._on_login)
        self.registro.cancelar.connect(lambda: self.stack.setCurrentIndex(PANTALLA_LOGIN))
        self.bienvenida.cerrar_sesion.connect(self._on_cerrar_sesion)

        self.stack.setCurrentIndex(PANTALLA_LOGIN)

    def _registrar_atajos(self):
        salida = QShortcut(SALIDA_SECRETA, self)
        salida.activated.connect(self._salida_admin)

    def _on_login(self, estudiante: dict):
        ahora = datetime.now()
        self._sesion_activa_id = str(uuid.uuid4())
        self._sesion_inicio = ahora

        guardar_sesion({
            "id": self._sesion_activa_id,
            "pc_id": PC_ID,
            "carnet": estudiante["carnet"],
            "hora_inicio": ahora.isoformat(),
            "hora_fin": None,
            "fecha": date.today().isoformat(),
        })

        self.bienvenida.iniciar_sesion(estudiante, ahora)
        self.stack.setCurrentIndex(PANTALLA_SESION)

    def _on_cerrar_sesion(self):
        if self._sesion_activa_id:
            hora_fin = datetime.now().isoformat()
            actualizar_hora_fin(self._sesion_activa_id, hora_fin)
            self._sesion_activa_id = None
            self._sesion_inicio = None

        self.bienvenida.detener()
        self.login.limpiar()
        self.stack.setCurrentIndex(PANTALLA_LOGIN)

    def _salida_admin(self):
        if self._sesion_activa_id:
            self._on_cerrar_sesion()
        QApplication.quit()

    def keyPressEvent(self, event):
        # Absorber teclas que no son el atajo de salida
        bloqueadas = {
            Qt.Key.Key_Escape, Qt.Key.Key_Meta,
            Qt.Key.Key_Super_L, Qt.Key.Key_Super_R,
        }
        if event.key() in bloqueadas:
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        # Prevenir cierre con Alt+F4 o botón X
        event.ignore()
