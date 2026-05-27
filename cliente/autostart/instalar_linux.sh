#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="${PYTHON:-python3}"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/biblioteca-kiosko.desktop"

echo "=== Instalando autostart (Linux) ==="
mkdir -p "$AUTOSTART_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Biblioteca Kiosko
Exec=$PYTHON $APP_DIR/main.py
X-GNOME-Autostart-enabled=true
NoDisplay=false
Hidden=false
Comment=Sistema de control de biblioteca universitaria
EOF

chmod +x "$DESKTOP_FILE"
echo "Autostart creado: $DESKTOP_FILE"
echo ""
echo "Para desinstalar: rm $DESKTOP_FILE"
echo ""

# Opción systemd (para arranque antes del login gráfico)
read -rp "¿Instalar también como servicio systemd? (requiere sudo) [s/N]: " resp
if [[ "${resp,,}" == "s" ]]; then
    SERVICE_FILE="/etc/systemd/system/biblioteca-kiosko.service"
    USER_NAME="$(whoami)"
    sudo tee "$SERVICE_FILE" > /dev/null <<SEOF
[Unit]
Description=Biblioteca Kiosko
After=graphical.target

[Service]
Type=simple
User=$USER_NAME
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/$USER_NAME/.Xauthority
WorkingDirectory=$APP_DIR
ExecStart=$PYTHON $APP_DIR/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
SEOF
    sudo systemctl daemon-reload
    sudo systemctl enable biblioteca-kiosko
    echo "Servicio systemd instalado"
    echo "Para desinstalar: sudo systemctl disable biblioteca-kiosko && sudo rm $SERVICE_FILE"
fi
