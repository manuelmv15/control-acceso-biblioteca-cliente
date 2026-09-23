"""Interfaz gráfica del kiosko.

Corre con el usuario de la sesión gráfica, el mismo que usa el estudiante
cuando el kiosko se oculta en la bandeja, así que no lee config.ini ni la
base local ni habla con el servidor: todo eso lo hace el servicio en
segundo plano (`python -m servicio`), con otro usuario, y la UI se lo pide
por su socket local (ver ui/servicio.py).
"""
import sys

from core.bloqueo_escritorio import aplicar as aplicar_bloqueo_escritorio
from PyQt6.QtWidgets import QApplication
from ui import servicio
from ui.icono import cargar_icono_app
from ui.kiosko import VentanaKiosko
from ui.log import log


def _debe_bloquear_atajos() -> bool:
    """Lo decide config.ini ([escritorio] bloquear_atajos), que solo puede
    leer el servicio. Si el servicio todavía no responde (p. ej. la sesión
    gráfica arrancó antes que él), se bloquean igual: es la opción segura."""
    try:
        return servicio.llamar("info")["bloquear_atajos"]
    except (servicio.ServicioNoDisponible, servicio.ErrorServicio) as exc:
        log.warning("Servicio del kiosko no disponible al arrancar la UI: %s", exc)
        return True


def main():
    if _debe_bloquear_atajos():
        aplicar_bloqueo_escritorio()

    app = QApplication(sys.argv)
    app.setWindowIcon(cargar_icono_app())
    # Identifica la app ante el entorno de escritorio (GNOME/Wayland en las
    # PCs cliente) para que el dock/barra de apps use el ícono del
    # .desktop instalado por autostart/instalar_linux.sh en vez del
    # genérico. Debe coincidir con el nombre de ese .desktop (sin
    # extensión) y con su StartupWMClass.
    app.setDesktopFileName("biblioteca-kiosko")

    ventana = VentanaKiosko()
    ventana.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
