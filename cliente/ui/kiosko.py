import uuid
from datetime import datetime, date
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget, QApplication, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QTimer, QKeyCombination
from PyQt6.QtGui import QKeySequence, QShortcut, QIcon, QPixmap, QColor

from ui.login import PantallaLogin
from ui.registro import PantallaRegistro
from ui.bienvenida import PantallaBienvenida
from ui.flotante import WidgetFlotatante
from database import guardar_sesion, actualizar_hora_fin
from config import PC_ID
from sync import forzar_sync
import estado as estado_mod

PANTALLA_LOGIN = 0
PANTALLA_REGISTRO = 1
PANTALLA_SESION = 2

DURACION_SESION_MS = 60 * 60 * 1000  # 60 minutos

SALIDA_SECRETA = QKeySequence(
    QKeyCombination(
        Qt.KeyboardModifier.ControlModifier |
        Qt.KeyboardModifier.ShiftModifier |
        Qt.KeyboardModifier.AltModifier,
        Qt.Key.Key_Q
    )
)


def _icono_fallback() -> QIcon:
    pix = QPixmap(32, 32)
    pix.fill(QColor("#1a3c6e"))
    return QIcon(pix)


class VentanaKiosko(QMainWindow):
    def __init__(self):
        super().__init__()
        self._sesion_activa_id: str | None = None
        self._sesion_inicio: datetime | None = None
        self._estudiante_activo: dict | None = None

        self._timer_sesion = QTimer(self)
        self._timer_sesion.setSingleShot(True)
        self._timer_sesion.timeout.connect(self._sesion_expirada)

        self._cargar_estilos()
        self._construir_ui()
        self._configurar_tray()
        self._registrar_atajos()
        self._mostrar_login()

    def _cargar_estilos(self):
        qss_path = Path(__file__).parent / "estilos.qss"
        if qss_path.exists():
            QApplication.instance().setStyleSheet(qss_path.read_text(encoding="utf-8"))

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
        self.registro.actualizacion_exitosa.connect(self._on_actualizacion_exitosa)
        self.registro.cancelar.connect(self._on_cancelar_registro)
        self.bienvenida.cerrar_sesion.connect(self._on_cerrar_sesion)

        self.flotante = WidgetFlotatante()
        self.flotante.cerrar_sesion.connect(self._on_cerrar_sesion)
        self.flotante.actualizar_datos.connect(self._on_actualizar_datos)

    def _configurar_tray(self):
        logo = Path(__file__).parent.parent / "assets" / "logo.png"
        icono = QIcon(str(logo)) if logo.exists() else _icono_fallback()

        self.tray = QSystemTrayIcon(icono, self)
        menu = QMenu()
        menu.addAction("Cerrar sesión", self._on_cerrar_sesion)
        menu.addSeparator()
        menu.addAction("Salir (admin)", self._salida_admin)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("Biblioteca — Control de acceso")
        self.tray.activated.connect(self._tray_click)
        self.tray.show()

    def _tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._mostrar_login()

    def _registrar_atajos(self):
        salida = QShortcut(SALIDA_SECRETA, self)
        salida.activated.connect(self._salida_admin)

    # ── Login / ocultamiento ─────────────────────────────────────────────

    def _mostrar_login(self):
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
        )
        self.stack.setCurrentIndex(PANTALLA_LOGIN)
        self.login.limpiar()
        self.showFullScreen()
        self.raise_()
        self.activateWindow()

    def _ocultar_a_tray(self):
        self.hide()
        self.tray.showMessage(
            "Biblioteca",
            "Sesión iniciada. En 1 hora se pedirá carnet nuevamente.",
            QSystemTrayIcon.MessageIcon.Information,
            4000,
        )
        self.flotante.iniciar_sesion(self._sesion_inicio, DURACION_SESION_MS)

    # ── Eventos de sesión ────────────────────────────────────────────────

    def _on_login(self, estudiante: dict):
        ahora = datetime.now()
        self._sesion_activa_id = str(uuid.uuid4())
        self._sesion_inicio = ahora
        self._estudiante_activo = estudiante

        guardar_sesion({
            "id": self._sesion_activa_id,
            "pc_id": PC_ID,
            "carnet": estudiante["carnet"],
            "hora_inicio": ahora.isoformat(),
            "hora_fin": None,
            "fecha": date.today().isoformat(),
        })
        estado_mod.set_sesion_activa(
            carnet=estudiante["carnet"],
            nombre=estudiante.get("nombre", ""),
            hora_inicio=ahora.isoformat(),
            carrera=estudiante.get("carrera"),
            facultad=estudiante.get("facultad"),
            departamento=estudiante.get("departamento"),
            sexo=estudiante.get("sexo"),
            fecha_nacimiento=estudiante.get("fecha_nacimiento"),
        )

        self.bienvenida.iniciar_sesion(estudiante, ahora)
        self.stack.setCurrentIndex(PANTALLA_SESION)
        self.showFullScreen()

        # Mostrar bienvenida 3 segundos y ocultar
        QTimer.singleShot(3000, self._ocultar_a_tray)

        # Iniciar temporizador de 1 hora
        self._timer_sesion.start(DURACION_SESION_MS)

    def _on_cancelar_registro(self):
        self.registro._limpiar()
        if self._sesion_activa_id:
            self.hide()
        else:
            self._mostrar_login()

    def _on_actualizar_datos(self):
        if self._estudiante_activo:
            self.registro.cargar_datos(self._estudiante_activo)
            self.stack.setCurrentIndex(PANTALLA_REGISTRO)
            self.showFullScreen()

    def _on_actualizacion_exitosa(self, datos: dict):
        self._estudiante_activo = datos
        if self._sesion_activa_id:
            estado_mod.set_sesion_activa(
                carnet=datos["carnet"],
                nombre=datos.get("nombre", ""),
                hora_inicio=self._sesion_inicio.isoformat() if self._sesion_inicio else "",
                carrera=datos.get("carrera"),
                facultad=datos.get("facultad"),
                departamento=datos.get("departamento"),
                sexo=datos.get("sexo"),
                fecha_nacimiento=datos.get("fecha_nacimiento"),
            )
            from sync import forzar_sync
            forzar_sync()
        self.hide()
        self.tray.showMessage(
            "Biblioteca",
            "Datos actualizados correctamente.",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    def _on_cerrar_sesion(self):
        self._timer_sesion.stop()
        if self._sesion_activa_id:
            actualizar_hora_fin(self._sesion_activa_id, datetime.now().isoformat())
            self._sesion_activa_id = None
            self._sesion_inicio = None
        self._estudiante_activo = None
        estado_mod.set_sesion_inactiva()
        forzar_sync()

        self.flotante.detener()
        self.bienvenida.detener()
        self._mostrar_login()

    def _sesion_expirada(self):
        if self._sesion_activa_id:
            actualizar_hora_fin(self._sesion_activa_id, datetime.now().isoformat())
        self._sesion_activa_id = None
        self._sesion_inicio = None
        self._estudiante_activo = None
        estado_mod.set_sesion_inactiva()
        forzar_sync()

        self.flotante.detener()
        self.bienvenida.detener()
        self.tray.showMessage(
            "Biblioteca",
            "Sesión de 1 hora completada. Ingrese su carnet para continuar.",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )
        self._mostrar_login()

    def _salida_admin(self):
        if self._sesion_activa_id:
            actualizar_hora_fin(self._sesion_activa_id, datetime.now().isoformat())
        self._timer_sesion.stop()
        self.tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        # X oculta a tray en lugar de cerrar
        event.ignore()
        self.hide()
