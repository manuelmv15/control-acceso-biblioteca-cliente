from pathlib import Path

from PyQt6.QtGui import QIcon, QPixmap, QColor

_LOGO_PATH = Path(__file__).parent.parent / "assets" / "logo_icono.png"


def _icono_fallback() -> QIcon:
    pix = QPixmap(32, 32)
    pix.fill(QColor("#8B0E13"))
    return QIcon(pix)


def cargar_icono_app() -> QIcon:
    """Ícono de la app: ventanas, tray y barra de tareas.

    Usa assets/logo_icono.png (fondo blanco, se ve mejor en la barra de
    aplicaciones) si existe; si no, cae a un cuadrado rojo institucional
    para no dejar el ícono genérico del sistema operativo.
    """
    if _LOGO_PATH.exists():
        return QIcon(str(_LOGO_PATH))
    return _icono_fallback()
