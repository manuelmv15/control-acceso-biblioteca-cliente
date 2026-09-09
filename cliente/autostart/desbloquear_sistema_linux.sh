#!/usr/bin/env bash
set -euo pipefail

# Revierte lo aplicado por bloquear_sistema_linux.sh: dconf de sistema con
# locks + bloqueo de cambio de TTY. Útil para volver una PC a un estado
# normal (ej. una máquina de desarrollo donde se corrió el script por
# error, o para depurar el kiosko con una terminal real).
#
# No reinstala gnome-terminal/xterm/nautilus si se desinstalaron —
# hacelo manualmente con tu gestor de paquetes. Tampoco toca
# configuración de BIOS/UEFI (eso siempre fue manual, ver
# docs/desarrollo/despliegue.md).

if [[ $EUID -eq 0 ]]; then
    echo "No corras este script directamente como root — usa sudo solo cuando se te pida (el script lo invoca internamente)."
    exit 1
fi

echo "=== Revirtiendo bloqueo de escritorio a nivel de sistema (Linux) ==="

if [[ -f /etc/dconf/db/local.d/00-kiosko ]]; then
    sudo rm -f /etc/dconf/db/local.d/00-kiosko
    echo "dconf de sistema (00-kiosko) eliminado."
else
    echo "No había dconf de sistema (00-kiosko) instalado."
fi

if [[ -f /etc/dconf/db/local.d/locks/00-kiosko ]]; then
    sudo rm -f /etc/dconf/db/local.d/locks/00-kiosko
    echo "Locks de dconf (00-kiosko) eliminados."
else
    echo "No había locks de dconf (00-kiosko) instalados."
fi

if command -v dconf >/dev/null 2>&1; then
    sudo dconf update
fi

if [[ -f /etc/systemd/logind.conf.d/90-kiosko.conf ]]; then
    sudo rm -f /etc/systemd/logind.conf.d/90-kiosko.conf
    if sudo systemctl restart systemd-logind 2>/dev/null; then
        echo "Bloqueo de TTY revertido (systemd-logind reiniciado)."
    else
        echo "Bloqueo de TTY revertido (reiniciá la PC para que aplique)."
    fi
else
    echo "No había bloqueo de TTY instalado."
fi

echo ""
echo "gnome-terminal/xterm/nautilus (si se desinstalaron con bloquear_sistema_linux.sh) no se reinstalan automáticamente."
echo "=== Listo ==="
