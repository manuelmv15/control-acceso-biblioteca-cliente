import sys
from PyQt6.QtWidgets import QApplication

from db import init_db
from sync import iniciar as iniciar_sync
from hardware.agent import iniciar as iniciar_hardware_agent
from ui.kiosko import VentanaKiosko
from ui.icono import cargar_icono_app


def main():
    init_db()
    iniciar_sync()
    iniciar_hardware_agent()

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
