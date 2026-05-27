import sys
from PyQt6.QtWidgets import QApplication

from database import init_db
from sync import iniciar as iniciar_sync
from ui.kiosko import VentanaKiosko


def main():
    init_db()
    iniciar_sync()

    app = QApplication(sys.argv)

    ventana = VentanaKiosko()
    ventana.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
