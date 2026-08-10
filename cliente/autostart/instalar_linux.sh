#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="${PYTHON:-python3}"
ICON="$APP_DIR/assets/logo_icono.png"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/biblioteca-kiosko.desktop"
APPS_DIR="$HOME/.local/share/applications"
APPS_DESKTOP_FILE="$APPS_DIR/biblioteca-kiosko.desktop"

echo "=== Instalando autostart (Linux) ==="
mkdir -p "$AUTOSTART_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Biblioteca Kiosko
Exec=$PYTHON $APP_DIR/main.py
Icon=$ICON
StartupWMClass=biblioteca-kiosko
X-GNOME-Autostart-enabled=true
NoDisplay=false
Hidden=false
Comment=Sistema de control de biblioteca universitaria
EOF

chmod +x "$DESKTOP_FILE"
echo "Autostart creado: $DESKTOP_FILE"

# Entrada en el menú de aplicaciones: es la que GNOME/el dock realmente
# consulta para el ícono de la barra de apps (el .desktop de autostart de
# arriba solo controla el arranque de sesión, GNOME no lo usa para eso).
# main.py llama a app.setDesktopFileName("biblioteca-kiosko"), que debe
# coincidir con el nombre de este archivo (sin ".desktop").
mkdir -p "$APPS_DIR"
cat > "$APPS_DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Biblioteca Kiosko
Exec=$PYTHON $APP_DIR/main.py
Icon=$ICON
StartupWMClass=biblioteca-kiosko
Terminal=false
Categories=Utility;
Comment=Sistema de control de biblioteca universitaria
EOF
echo "Entrada de aplicación creada: $APPS_DESKTOP_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS_DIR" 2>/dev/null || true
fi

echo ""
echo "Para desinstalar: rm $DESKTOP_FILE $APPS_DESKTOP_FILE"
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
