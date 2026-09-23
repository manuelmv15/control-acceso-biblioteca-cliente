import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from core.tiempo import now_sv
from PyQt6.QtCore import QKeyCombination, Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStackedWidget,
    QSystemTrayIcon,
)

from ui import servicio
from ui.bienvenida import PantallaBienvenida
from ui.icono import cargar_icono_app
from ui.log import log
from ui.login import PantallaLogin
from ui.registro import PantallaRegistro
from ui.sesion import VentanaSesion

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

# Solo se usa si el servicio no responde al abrir la sesión, para no dejar
# el temporizador sin valor; la duración real la fija el servicio.
DURACION_SESION_MS_POR_DEFECTO = 60 * 60 * 1000


class VentanaKiosko(QMainWindow):
    def __init__(self):
        super().__init__()
        self._sesion_activa_id: str | None = None
        self._sesion_inicio: datetime | None = None
        self._estudiante_activo: dict | None = None
        self._estudiante_mostrado: dict | None = None
        self._es_invitado: bool = False
        self._duracion_sesion_ms: int = DURACION_SESION_MS_POR_DEFECTO

        self._timer_sesion = QTimer(self)
        self._timer_sesion.setSingleShot(True)
        self._timer_sesion.timeout.connect(self._sesion_expirada)

        self.setWindowIcon(cargar_icono_app())
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
        self.login.solicitar_apagar.connect(self._apagar_equipo)
        self.login.solicitar_reiniciar.connect(self._reiniciar_equipo)
        self.login.solicitar_cerrar_programa.connect(self._salida_admin)
        self.registro.registro_exitoso.connect(self._on_login)
        self.registro.actualizacion_exitosa.connect(self._on_actualizacion_exitosa)
        self.registro.acceso_no_estudiante.connect(self._on_login_no_estudiante)
        self.registro.cancelar.connect(self._on_cancelar_registro)

        self.ventana_sesion = VentanaSesion()
        self.ventana_sesion.cerrar_sesion.connect(self._on_cerrar_sesion)
        self.ventana_sesion.actualizar_datos.connect(self._on_actualizar_datos)
        self.ventana_sesion.reiniciar_tiempo.connect(self._on_reiniciar_tiempo)

    def _configurar_tray(self):
        self.tray = QSystemTrayIcon(cargar_icono_app(), self)
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
            "Sesión iniciada.",
            QSystemTrayIcon.MessageIcon.Information,
            4000,
        )
        self.ventana_sesion.iniciar_sesion(
            self._estudiante_mostrado, self._sesion_inicio, self._duracion_sesion_ms, self._es_invitado
        )

    # ── Eventos de sesión ────────────────────────────────────────────────

    def _on_login(self, estudiante: dict | None, etiqueta_sector: str = ""):
        """estudiante=None representa un acceso sin registro (sector no
        estudiantil): sin carnet ni datos personales, misma duración de
        sesión que un estudiante. El servicio registra la sesión, fija su
        hora de inicio y su duración y reporta el estado al servidor."""
        try:
            if estudiante:
                sesion = servicio.llamar("abrir_sesion", carnet=estudiante["carnet"])
            else:
                sesion = servicio.llamar("abrir_sesion", sector=etiqueta_sector)
        except (servicio.ServicioNoDisponible, servicio.ErrorServicio) as exc:
            log.error("No se pudo abrir la sesión: %s", exc)
            QMessageBox.warning(
                self, "Sistema no disponible",
                "No se pudo iniciar la sesión. Intente de nuevo en unos segundos."
            )
            self._mostrar_login()
            return

        ahora = datetime.fromisoformat(sesion["hora_inicio"])
        self._sesion_activa_id = sesion["sesion_id"]
        self._sesion_inicio = ahora
        self._duracion_sesion_ms = sesion["duracion_sesion_ms"]
        self._estudiante_activo = sesion["estudiante"]
        self._es_invitado = sesion["estudiante"] is None
        log.info("Sesión iniciada (%s)", "invitado" if self._es_invitado else "estudiante")

        self._estudiante_mostrado = sesion["estudiante"] or {
            "nombre": etiqueta_sector, "carrera": "Acceso sin registro", "carnet": None,
        }
        self.bienvenida.iniciar_sesion(self._estudiante_mostrado, ahora)
        self.stack.setCurrentIndex(PANTALLA_SESION)
        self.showFullScreen()

        # Mostrar bienvenida 3 segundos y ocultar
        QTimer.singleShot(3000, self._ocultar_a_tray)

        self._timer_sesion.start(self._duracion_sesion_ms)

    def _on_login_no_estudiante(self, sector: str):
        self._on_login(None, etiqueta_sector=sector)

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
        # El servicio ya actualizó el estado de la sesión activa y forzó el
        # sync al guardar los datos; acá solo se refresca lo que se muestra.
        self._estudiante_activo = datos
        self._estudiante_mostrado = datos
        self.ventana_sesion.actualizar_estudiante(datos)
        self.hide()
        self.tray.showMessage(
            "Biblioteca",
            "Datos actualizados correctamente.",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    def _on_reiniciar_tiempo(self):
        """Reinicia el contador de tiempo restante a una hora completa, por
        si el estudiante desea continuar usando el equipo."""
        if not self._sesion_activa_id:
            return
        ahora = now_sv()
        log.info("Tiempo de sesión reiniciado a %d min", self._duracion_sesion_ms // 60000)
        self._timer_sesion.start(self._duracion_sesion_ms)
        self.ventana_sesion.iniciar_sesion(
            self._estudiante_mostrado, ahora, self._duracion_sesion_ms, self._es_invitado
        )
        self.tray.showMessage(
            "Biblioteca",
            "Tiempo de sesión reiniciado a 1 hora.",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    def _cerrar_sesion_en_servicio(self):
        """Pide al servicio registrar la hora de fin de la sesión activa (y
        sincronizarla). Si el servicio no responde, la UI vuelve igual al
        login: la sesión queda abierta en el servicio hasta que se abra la
        siguiente o se detenga el servicio, y ahí se cierra."""
        self._timer_sesion.stop()
        if self._sesion_activa_id:
            try:
                servicio.llamar("cerrar_sesion")
            except (servicio.ServicioNoDisponible, servicio.ErrorServicio) as exc:
                log.error("No se pudo cerrar la sesión en el servicio: %s", exc)
        self._sesion_activa_id = None
        self._sesion_inicio = None
        self._estudiante_activo = None
        self._estudiante_mostrado = None
        self._es_invitado = False

    def _on_cerrar_sesion(self):
        self._cerrar_sesion_en_servicio()

        self.ventana_sesion.detener()
        self.bienvenida.detener()
        self._mostrar_login()

    def _sesion_expirada(self):
        self._cerrar_sesion_en_servicio()

        self.ventana_sesion.detener()
        self.bienvenida.detener()
        self.tray.showMessage(
            "Biblioteca",
            "Sesión completada. Ingrese su carnet para continuar.",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )
        self._mostrar_login()

    def _salida_admin(self):
        if not self._verificar_pin_admin():
            return
        log.info("Kiosko cerrado vía Salir (admin)")
        self._cerrar_sesion_en_servicio()
        self.tray.hide()
        QApplication.quit()

    def _apagar_equipo(self):
        if not self._verificar_pin_admin():
            return
        log.info("Apagado del equipo solicitado desde login (admin)")
        self._preparar_apagado_o_reinicio()
        try:
            subprocess.run([shutil.which("systemctl") or "systemctl", "poweroff"], check=True, timeout=10)
        except Exception as exc:
            log.error("Error al apagar el equipo: %s", exc)
            QMessageBox.warning(self, "Error", "No se pudo apagar el equipo.")

    def _reiniciar_equipo(self):
        if not self._verificar_pin_admin():
            return
        log.info("Reinicio del equipo solicitado desde login (admin)")
        self._preparar_apagado_o_reinicio()
        try:
            subprocess.run([shutil.which("systemctl") or "systemctl", "reboot"], check=True, timeout=10)
        except Exception as exc:
            log.error("Error al reiniciar el equipo: %s", exc)
            QMessageBox.warning(self, "Error", "No se pudo reiniciar el equipo.")

    def _preparar_apagado_o_reinicio(self):
        """Cierra la sesión activa (si la hay) y detiene el timer antes de
        entregarle el control al sistema operativo."""
        self._cerrar_sesion_en_servicio()
        self.tray.hide()

    def _verificar_pin_admin(self) -> bool:
        """El hash del PIN y el contador de intentos fallidos los guarda el
        servicio; la UI solo pide el PIN y muestra el resultado. Si el
        servicio no responde, la salida queda bloqueada (falla cerrado)."""
        try:
            estado = servicio.llamar("estado_pin_admin")
            if estado["estado"] == "disponible":
                pin, ok = QInputDialog.getText(
                    self, "Salida de administrador", "PIN de administrador:",
                    QLineEdit.EchoMode.Password
                )
                if not ok:
                    return False
                estado = servicio.llamar("verificar_pin_admin", pin=pin)
        except (servicio.ServicioNoDisponible, servicio.ErrorServicio) as exc:
            log.error("No se pudo verificar el PIN de administrador: %s", exc)
            QMessageBox.warning(
                self, "Sistema no disponible",
                "No se pudo verificar el PIN porque el servicio del kiosko no responde."
            )
            return False

        resultado = estado["estado"]
        if resultado == "ok":
            log.info("Salida admin autorizada (PIN correcto)")
            return True
        log.warning("Salida admin denegada: %s", resultado)
        if resultado == "bloqueado":
            QMessageBox.warning(
                self, "PIN bloqueado",
                f"Demasiados intentos fallidos. Esperá {estado['minutos']} minuto(s) antes de volver a intentar."
            )
        elif resultado == "sin_pin":
            QMessageBox.warning(
                self, "Salida bloqueada",
                "No hay un PIN de administrador configurado en config.ini "
                "([admin] pin_hash). Configúralo antes de poder salir del kiosko."
            )
        elif resultado == "legacy":
            QMessageBox.warning(
                self, "Reconfiguración requerida",
                "El PIN de administrador quedó guardado en un formato antiguo "
                "e inseguro. Volvé a ejecutar setup.py para configurar un PIN "
                "nuevo antes de poder salir del kiosko."
            )
        else:
            QMessageBox.warning(self, "PIN incorrecto", "El PIN ingresado no es válido.")
        return False

    def closeEvent(self, event):
        # X oculta a tray en lugar de cerrar
        event.ignore()
        self.hide()
