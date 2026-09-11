import subprocess
import time
import uuid
from datetime import date, datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget, QApplication, QSystemTrayIcon, QMenu,
    QInputDialog, QLineEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QKeyCombination
from PyQt6.QtGui import QKeySequence, QShortcut

from ui.login import PantallaLogin
from ui.registro import PantallaRegistro
from ui.bienvenida import PantallaBienvenida
from ui.sesion import VentanaSesion
from ui.icono import cargar_icono_app
from db.sesiones import guardar_sesion, actualizar_hora_fin
from db.pin_admin import obtener_estado_pin, guardar_estado_pin
from core.config import PC_ID, DURACION_SESION_MS, ADMIN_PIN_HASH, now_sv
from core.pin_hash import verificar_pin, es_hash_legacy
from sync import forzar_sync
import core.estado as estado_mod
from ui.log import log

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

# Rate limiting del PIN de administrador local: sin esto, alguien con
# acceso físico prolongado a un kiosko puede probar PINs manualmente sin
# límite ni demora. Se persiste en la base local (tabla pin_admin_lockout,
# ver db/pin_admin.py) para que reiniciar la app del kiosko no resetee el
# contador de intentos fallidos — solo hay un teclado local frente a un
# único diálogo, así que se guarda una sola fila por PC_ID.
PIN_ADMIN_MAX_INTENTOS = 5
PIN_ADMIN_BLOQUEO_SEGUNDOS = 5 * 60


class VentanaKiosko(QMainWindow):
    def __init__(self):
        super().__init__()
        self._sesion_activa_id: str | None = None
        self._sesion_inicio: datetime | None = None
        self._estudiante_activo: dict | None = None
        self._estudiante_mostrado: dict | None = None
        self._es_invitado: bool = False
        self._pin_admin_fallos, self._pin_admin_bloqueado_hasta = obtener_estado_pin(PC_ID)

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
            self._estudiante_mostrado, self._sesion_inicio, DURACION_SESION_MS, self._es_invitado
        )

    # ── Eventos de sesión ────────────────────────────────────────────────

    def _on_login(self, estudiante: dict | None, etiqueta_sector: str = ""):
        """estudiante=None representa un acceso sin registro (sector no
        estudiantil): sin carnet ni datos personales, misma duración de
        sesión que un estudiante."""
        ahora = now_sv()
        self._sesion_activa_id = str(uuid.uuid4())
        self._sesion_inicio = ahora
        self._estudiante_activo = estudiante
        self._es_invitado = estudiante is None

        carnet = estudiante["carnet"] if estudiante else None
        if carnet:
            log.info("Sesión iniciada — carnet %s", carnet)
        else:
            log.info("Sesión iniciada — invitado (%s)", etiqueta_sector or "sin sector")
        guardar_sesion({
            "id": self._sesion_activa_id,
            "pc_id": PC_ID,
            "carnet": carnet,
            "hora_inicio": ahora.isoformat(),
            "hora_fin": None,
            "fecha": date.today().isoformat(),
        })
        estado_mod.set_sesion_activa(
            carnet=carnet,
            nombre=estudiante.get("nombre", "") if estudiante else etiqueta_sector,
            hora_inicio=ahora.isoformat(),
            carrera=estudiante.get("carrera") if estudiante else None,
            facultad=estudiante.get("facultad") if estudiante else None,
            sexo=estudiante.get("sexo") if estudiante else None,
            fecha_nacimiento=estudiante.get("fecha_nacimiento") if estudiante else None,
        )

        self._estudiante_mostrado = estudiante or {
            "nombre": etiqueta_sector, "carrera": "Acceso sin registro", "carnet": None,
        }
        self.bienvenida.iniciar_sesion(self._estudiante_mostrado, ahora)
        self.stack.setCurrentIndex(PANTALLA_SESION)
        self.showFullScreen()

        # Mostrar bienvenida 3 segundos y ocultar
        QTimer.singleShot(3000, self._ocultar_a_tray)

        self._timer_sesion.start(DURACION_SESION_MS)

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
        self._estudiante_activo = datos
        self._estudiante_mostrado = datos
        self.ventana_sesion.actualizar_estudiante(datos)
        if self._sesion_activa_id:
            estado_mod.set_sesion_activa(
                carnet=datos["carnet"],
                nombre=datos.get("nombre", ""),
                hora_inicio=self._sesion_inicio.isoformat() if self._sesion_inicio else "",
                carrera=datos.get("carrera"),
                facultad=datos.get("facultad"),
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

    def _on_reiniciar_tiempo(self):
        """Reinicia el contador de tiempo restante a una hora completa, por
        si el estudiante desea continuar usando el equipo."""
        if not self._sesion_activa_id:
            return
        ahora = now_sv()
        log.info(
            "Tiempo de sesión reiniciado a %d min — carnet %s",
            DURACION_SESION_MS // 60000,
            self._estudiante_activo["carnet"] if self._estudiante_activo else "invitado",
        )
        self._timer_sesion.start(DURACION_SESION_MS)
        self.ventana_sesion.iniciar_sesion(
            self._estudiante_mostrado, ahora, DURACION_SESION_MS, self._es_invitado
        )
        self.tray.showMessage(
            "Biblioteca",
            "Tiempo de sesión reiniciado a 1 hora.",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    def _on_cerrar_sesion(self):
        self._timer_sesion.stop()
        if self._sesion_activa_id:
            actualizar_hora_fin(self._sesion_activa_id, now_sv().isoformat())
            self._sesion_activa_id = None
            self._sesion_inicio = None
        self._estudiante_activo = None
        self._estudiante_mostrado = None
        self._es_invitado = False
        estado_mod.set_sesion_inactiva()
        forzar_sync()

        self.ventana_sesion.detener()
        self.bienvenida.detener()
        self._mostrar_login()

    def _sesion_expirada(self):
        if self._sesion_activa_id:
            actualizar_hora_fin(self._sesion_activa_id, now_sv().isoformat())
        self._sesion_activa_id = None
        self._sesion_inicio = None
        self._estudiante_activo = None
        self._estudiante_mostrado = None
        self._es_invitado = False
        estado_mod.set_sesion_inactiva()
        forzar_sync()

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
        if self._sesion_activa_id:
            actualizar_hora_fin(self._sesion_activa_id, now_sv().isoformat())
        self._timer_sesion.stop()
        self.tray.hide()
        QApplication.quit()

    def _apagar_equipo(self):
        if not self._verificar_pin_admin():
            return
        log.info("Apagado del equipo solicitado desde login (admin)")
        self._preparar_apagado_o_reinicio()
        try:
            subprocess.run(["systemctl", "poweroff"], check=True, timeout=10)
        except Exception as exc:
            log.error("Error al apagar el equipo: %s", exc)
            QMessageBox.warning(self, "Error", "No se pudo apagar el equipo.")

    def _reiniciar_equipo(self):
        if not self._verificar_pin_admin():
            return
        log.info("Reinicio del equipo solicitado desde login (admin)")
        self._preparar_apagado_o_reinicio()
        try:
            subprocess.run(["systemctl", "reboot"], check=True, timeout=10)
        except Exception as exc:
            log.error("Error al reiniciar el equipo: %s", exc)
            QMessageBox.warning(self, "Error", "No se pudo reiniciar el equipo.")

    def _preparar_apagado_o_reinicio(self):
        """Cierra la sesión activa (si la hay) y detiene el timer antes de
        entregarle el control al sistema operativo."""
        if self._sesion_activa_id:
            actualizar_hora_fin(self._sesion_activa_id, now_sv().isoformat())
        self._timer_sesion.stop()
        self.tray.hide()

    def _verificar_pin_admin(self) -> bool:
        restante = self._pin_admin_bloqueado_hasta - time.time()
        if restante > 0:
            minutos = int(restante // 60) + 1
            log.warning("Salida admin bloqueada: PIN bloqueado por %d intentos fallidos (%d min restantes)",
                        self._pin_admin_fallos, minutos)
            QMessageBox.warning(
                self, "PIN bloqueado",
                f"Demasiados intentos fallidos. Esperá {minutos} minuto(s) antes de volver a intentar."
            )
            return False
        if not ADMIN_PIN_HASH:
            log.warning("Salida admin bloqueada: sin PIN configurado")
            QMessageBox.warning(
                self, "Salida bloqueada",
                "No hay un PIN de administrador configurado en config.ini "
                "([admin] pin_hash). Configúralo antes de poder salir del kiosko."
            )
            return False
        if es_hash_legacy(ADMIN_PIN_HASH):
            # Hash del formato viejo (SHA-256 plano sin sal) — no se puede
            # migrar en caliente sin conocer el PIN en texto plano, así que
            # se bloquea y se pide reconfigurar.
            log.warning("Salida admin bloqueada: pin_hash en formato legacy, requiere reconfigurar")
            QMessageBox.warning(
                self, "Reconfiguración requerida",
                "El PIN de administrador quedó guardado en un formato antiguo "
                "e inseguro. Volvé a ejecutar setup.py para configurar un PIN "
                "nuevo antes de poder salir del kiosko."
            )
            return False
        pin, ok = QInputDialog.getText(
            self, "Salida de administrador", "PIN de administrador:",
            QLineEdit.EchoMode.Password
        )
        if not ok:
            return False
        if verificar_pin(pin, ADMIN_PIN_HASH):
            log.info("Salida admin autorizada (PIN correcto)")
            self._pin_admin_fallos = 0
            self._pin_admin_bloqueado_hasta = 0.0
            guardar_estado_pin(PC_ID, self._pin_admin_fallos, self._pin_admin_bloqueado_hasta)
            return True
        self._pin_admin_fallos += 1
        log.warning("Salida admin denegada: PIN incorrecto (intento %d/%d)",
                    self._pin_admin_fallos, PIN_ADMIN_MAX_INTENTOS)
        if self._pin_admin_fallos >= PIN_ADMIN_MAX_INTENTOS:
            self._pin_admin_bloqueado_hasta = time.time() + PIN_ADMIN_BLOQUEO_SEGUNDOS
            log.warning("PIN de administrador bloqueado por %d minutos tras exceder intentos",
                        PIN_ADMIN_BLOQUEO_SEGUNDOS // 60)
            guardar_estado_pin(PC_ID, self._pin_admin_fallos, self._pin_admin_bloqueado_hasta)
            QMessageBox.warning(
                self, "PIN bloqueado",
                f"Demasiados intentos fallidos. El PIN quedó bloqueado por "
                f"{PIN_ADMIN_BLOQUEO_SEGUNDOS // 60} minutos."
            )
        else:
            guardar_estado_pin(PC_ID, self._pin_admin_fallos, self._pin_admin_bloqueado_hasta)
            QMessageBox.warning(self, "PIN incorrecto", "El PIN ingresado no es válido.")
        return False

    def closeEvent(self, event):
        # X oculta a tray en lugar de cerrar
        event.ignore()
        self.hide()
