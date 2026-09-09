"""Bloqueo de atajos de teclado y del dock de GNOME que permiten salir del
kiosko sin cerrar sesión (tecla Super = resumen de Actividades, Alt+Tab,
"mostrar escritorio", iconos fijados en el dock como Terminal/Files, etc.).

`VentanaKiosko` solo controla la ventana a nivel de Qt (siempre encima, sin
bordes, pantalla completa) — esos atajos los captura el compositor de GNOME
(mutter/gnome-shell) *antes* de que el evento llegue a la app, así que
ningún `QShortcut` puede interceptarlos desde dentro. La única forma de
bloquearlos es a nivel del propio entorno de escritorio, vía gsettings.

Es best-effort a propósito: si el entorno no es GNOME, no hay `gsettings`
disponible, o alguna clave no existe en la versión instalada de GNOME
Shell, se ignora esa clave puntual y se sigue con las demás. Nunca debe
impedir que el kiosko arranque.

Limitación conocida: esto deshabilita las claves para el usuario actual
vía dconf de usuario, no las bloquea a nivel de sistema
(`/etc/dconf/db/.../locks`). Alguien con una terminal como ese mismo
usuario podría revertirlas con `gsettings set` — se reaplican en cada
arranque del kiosko, pero no dentro de una sesión ya abierta. Para un
bloqueo que sobreviva a eso (dconf de sistema con locks + endurecimiento
de BIOS/TTY), ver docs/desarrollo/despliegue.md, sección "Bloqueo de
escritorio para producción"
"""
import os
import shutil
import subprocess

from ui.log import log

# (esquema, clave) -> se vacían (arreglo vacío) para deshabilitar el atajo.
_CLAVES_A_VACIAR = [
    ("org.gnome.shell.keybindings", "toggle-overview"),
    ("org.gnome.shell.keybindings", "toggle-application-view"),
    ("org.gnome.desktop.wm.keybindings", "switch-applications"),
    ("org.gnome.desktop.wm.keybindings", "switch-applications-backward"),
    ("org.gnome.desktop.wm.keybindings", "switch-windows"),
    ("org.gnome.desktop.wm.keybindings", "switch-windows-backward"),
    ("org.gnome.desktop.wm.keybindings", "switch-group"),
    ("org.gnome.desktop.wm.keybindings", "switch-group-backward"),
    ("org.gnome.desktop.wm.keybindings", "show-desktop"),
    ("org.gnome.desktop.wm.keybindings", "panel-main-menu"),
    ("org.gnome.settings-daemon.plugins.media-keys", "terminal"),  # Ctrl+Alt+T
    # Iconos fijados en el dock (Firefox, Files, LibreOffice, Terminal...):
    # aunque los atajos de teclado estén bloqueados, un doble clic en
    # cualquiera de ellos desde el resumen de Actividades es otra salida
    # del kiosko igual de directa. Se vacía el dock entero.
    ("org.gnome.shell", "favorite-apps"),
]


def _es_gnome() -> bool:
    entorno = (
        os.environ.get("XDG_CURRENT_DESKTOP", "")
        + os.environ.get("DESKTOP_SESSION", "")
    ).lower()
    return "gnome" in entorno


def _set(esquema: str, clave: str, valor: str) -> bool:
    try:
        r = subprocess.run(
            ["gsettings", "set", esquema, clave, valor],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            log.debug("gsettings set %s %s falló: %s", esquema, clave, r.stderr.strip())
            return False
        return True
    except Exception as exc:
        log.debug("gsettings set %s %s excepción: %s", esquema, clave, exc)
        return False


def aplicar():
    """Deshabilita los atajos de GNOME que permiten salir del kiosko sin
    pasar por el login. Se llama en cada arranque de main.py."""
    if not _es_gnome():
        log.info(
            "Bloqueo de atajos: entorno no es GNOME (XDG_CURRENT_DESKTOP=%s), omitido",
            os.environ.get("XDG_CURRENT_DESKTOP", ""),
        )
        return
    if not shutil.which("gsettings"):
        log.warning("Bloqueo de atajos: gsettings no está disponible, omitido")
        return

    aplicadas, fallidas = 0, []

    # overlay-key es un string (no un arreglo): '' deshabilita la tecla
    # Super como atajo de "Actividades" (default de fábrica: 'Super_L').
    if _set("org.gnome.mutter", "overlay-key", "''"):
        aplicadas += 1
    else:
        fallidas.append("org.gnome.mutter.overlay-key")

    for esquema, clave in _CLAVES_A_VACIAR:
        if _set(esquema, clave, "[]"):
            aplicadas += 1
        else:
            fallidas.append(f"{esquema}.{clave}")

    if fallidas:
        log.warning(
            "Bloqueo de atajos GNOME: %d aplicadas, %d fallaron (%s)",
            aplicadas, len(fallidas), ", ".join(fallidas),
        )
    else:
        log.info("Bloqueo de atajos GNOME aplicado (%d claves)", aplicadas)
