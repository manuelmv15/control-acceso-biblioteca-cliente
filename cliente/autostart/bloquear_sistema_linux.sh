#!/usr/bin/env bash
set -euo pipefail

# Endurece el sistema operativo para que un usuario del kiosko no pueda
# alcanzar una terminal ni un explorador de archivos desde la sesión
# gráfica, y desde ahí llegar al código o a config.ini (KIOSK_API_KEY,
# hash del PIN admin). Ver docs/desarrollo/despliegue.md, sección
# "Bloqueo de escritorio para producción".
#
# Complementa (no reemplaza) a core/bloqueo_escritorio.py: ese aplica
# dconf de *usuario* (reversible con `gsettings set` dentro de la misma
# sesión); este script aplica dconf de *sistema* con locks (mandatorio,
# no revertible así), bloqueo de cambio de TTY, y opcionalmente
# desinstala terminal/explorador de archivos.
#
# Requiere sudo. Idempotente: se puede correr varias veces sin problema.
# Para revertir lo que este script sí puede revertir (dconf + TTY, no la
# desinstalación de paquetes ni el BIOS), ver desbloquear_sistema_linux.sh.

if [[ $EUID -eq 0 ]]; then
    echo "No corras este script directamente como root — usa sudo solo cuando se te pida (el script lo invoca internamente)."
    exit 1
fi

echo "=== Bloqueo de escritorio a nivel de sistema (Linux) ==="
echo "Requiere sudo. Pensado para PCs de kiosko dedicadas — no lo corras en tu equipo de desarrollo."
echo ""

# --- 1/3: dconf de sistema con locks -----------------------------------
echo "--- 1/3: dconf de sistema (Activities, Alt+Tab, dock, terminal) ---"
sudo mkdir -p /etc/dconf/db/local.d/locks

sudo tee /etc/dconf/db/local.d/00-kiosko > /dev/null <<'EOF'
# Generado por bloquear_sistema_linux.sh — ver docs/desarrollo/despliegue.md.
[org/gnome/desktop/wm/keybindings]
switch-applications=@as []
switch-applications-backward=@as []
switch-windows=@as []
switch-windows-backward=@as []
switch-group=@as []
switch-group-backward=@as []
show-desktop=@as []
panel-main-menu=@as []

[org/gnome/shell/keybindings]
toggle-overview=@as []
toggle-application-view=@as []

[org/gnome/shell]
favorite-apps=@as []

[org/gnome/mutter]
overlay-key=''

[org/gnome/settings-daemon/plugins/media-keys]
terminal=@as []
EOF

sudo tee /etc/dconf/db/local.d/locks/00-kiosko > /dev/null <<'EOF'
/org/gnome/desktop/wm/keybindings/switch-applications
/org/gnome/desktop/wm/keybindings/switch-applications-backward
/org/gnome/desktop/wm/keybindings/switch-windows
/org/gnome/desktop/wm/keybindings/switch-windows-backward
/org/gnome/desktop/wm/keybindings/switch-group
/org/gnome/desktop/wm/keybindings/switch-group-backward
/org/gnome/desktop/wm/keybindings/show-desktop
/org/gnome/desktop/wm/keybindings/panel-main-menu
/org/gnome/shell/keybindings/toggle-overview
/org/gnome/shell/keybindings/toggle-application-view
/org/gnome/shell/favorite-apps
/org/gnome/mutter/overlay-key
/org/gnome/settings-daemon/plugins/media-keys/terminal
EOF

if command -v dconf >/dev/null 2>&1; then
    sudo dconf update
    echo "dconf de sistema aplicado y bloqueado."
else
    echo "AVISO: 'dconf' no está disponible — los archivos se escribieron pero no se pudo correr 'dconf update'. Este paso solo tiene efecto en GNOME."
fi

# --- 2/3: bloquear cambio de TTY (Ctrl+Alt+F2, etc.) --------------------
echo ""
echo "--- 2/3: Bloqueo de cambio de terminal virtual (TTY) ---"
sudo mkdir -p /etc/systemd/logind.conf.d
sudo tee /etc/systemd/logind.conf.d/90-kiosko.conf > /dev/null <<'EOF'
# Generado por bloquear_sistema_linux.sh — ver docs/desarrollo/despliegue.md.
[Login]
NAutoVTs=1
ReserveVT=1
EOF
if sudo systemctl restart systemd-logind 2>/dev/null; then
    echo "TTY bloqueado (systemd-logind reiniciado)."
else
    echo "AVISO: no se pudo reiniciar systemd-logind — reiniciá la PC para que el bloqueo de TTY aplique."
fi

# --- 3/3: desinstalar terminal/explorador de archivos (opcional) --------
echo ""
echo "--- 3/3: Desinstalar terminal y explorador de archivos (opcional) ---"
echo "Quita gnome-terminal, xterm y nautilus — si no están instalados, ningún"
echo "atajo (cubierto o no arriba) puede alcanzarlos. En algunas distros esto"
echo "puede arrastrar otros paquetes del entorno GNOME; revisá lo que apt"
echo "propone antes de confirmar."
read -rp "¿Desinstalar gnome-terminal/xterm/nautilus ahora? [s/N]: " resp
if [[ "${resp,,}" == "s" ]]; then
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get remove -y gnome-terminal xterm nautilus \
            || echo "AVISO: falló la desinstalación de alguno de los paquetes (puede que ya no estuvieran instalados) — revisá el mensaje de apt arriba."
    else
        echo "AVISO: no se encontró 'apt-get' — desinstalá manualmente el equivalente en esta distro."
    fi
else
    echo "Omitido."
fi

echo ""
echo "=== Listo ==="
echo "Pendiente MANUAL (no se puede automatizar desde acá):"
echo "  - BIOS/UEFI con contraseña de administrador."
echo "  - Deshabilitar boot por USB/medios externos en el orden de arranque."
echo "  - Deshabilitar modo recovery/single-user de GRUB."
echo "Ver docs/desarrollo/despliegue.md, sección 'Bloqueo de escritorio para producción'."
echo ""
echo "Para revertir el bloqueo de dconf/TTY aplicado por este script: ./desbloquear_sistema_linux.sh"
