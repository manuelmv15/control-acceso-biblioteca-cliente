#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/biblioteca-kiosko.desktop"
SERVICE_NAME="biblioteca-kiosko"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

echo "=== Desinstalando autostart de Biblioteca Kiosko (Linux) ==="

# Detener la app si ya está corriendo, para que no siga regenerando
# sync.log / __pycache__ / .pc_id / biblioteca_local.db después de borrarlos
# Se busca por "python.*main\.py" (no por la ruta absoluta) porque si alguien
# lanzó la app con una ruta relativa (ej. "cd cliente && python3 main.py"),
# el comando en ps no contiene $APP_DIR y un patrón con ruta completa no haría match.
PROC_PATTERN="python.*main\.py"
if pgrep -f "$PROC_PATTERN" >/dev/null 2>&1; then
    echo "Deteniendo instancia en ejecución de main.py..."
    pkill -f "$PROC_PATTERN" || true
    for _ in $(seq 1 10); do
        pgrep -f "$PROC_PATTERN" >/dev/null 2>&1 || break
        sleep 0.5
    done
    if pgrep -f "$PROC_PATTERN" >/dev/null 2>&1; then
        echo "  No respondió, forzando cierre (SIGKILL)..."
        pkill -9 -f "$PROC_PATTERN" || true
        sleep 0.5
    fi
fi

# Autostart de sesion (XDG)
if [[ -f "$DESKTOP_FILE" ]]; then
    rm -f "$DESKTOP_FILE"
    echo "Autostart de sesión eliminado: $DESKTOP_FILE"
else
    echo "No había autostart de sesión instalado."
fi

# Servicio systemd
if systemctl list-unit-files 2>/dev/null | grep -q "^${SERVICE_NAME}.service"; then
    echo "Deteniendo y deshabilitando servicio systemd..."
    sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    sudo rm -f "$SERVICE_FILE"
    sudo systemctl daemon-reload
    echo "Servicio systemd eliminado."
else
    echo "No había servicio systemd instalado."
fi

echo ""
echo "Autostart desinstalado. El código fuente no se modificó."
echo ""

# Archivos generados en tiempo de ejecucion (regenerables, sin riesgo de perder datos).
# Se limpian aqui y otra vez al final: si algo (ej. el proceso que acabamos de matar
# terminando de vaciar su buffer de log) los recrea, la segunda pasada los vuelve a borrar.
limpiar_artefactos() {
    while IFS= read -r -d '' dir; do
        if ! rm -rf "$dir" 2>/dev/null; then
            sudo rm -rf "$dir"
        fi
    done < <(find "$APP_DIR" -depth -type d -name "__pycache__" -print0 2>/dev/null)

    if [[ -f "$APP_DIR/sync.log" ]] && ! rm -f "$APP_DIR/sync.log" 2>/dev/null; then
        sudo rm -f "$APP_DIR/sync.log"
    fi

    if [[ -f "$APP_DIR/hardware.log" ]] && ! rm -f "$APP_DIR/hardware.log" 2>/dev/null; then
        sudo rm -f "$APP_DIR/hardware.log"
    fi
}

limpiar_artefactos

echo ""
read -rp "¿Borrar también la configuración de esta PC (config.ini, .pc_id) para poder reconfigurarla desde cero? [s/N]: " resp
if [[ "${resp,,}" == "s" ]]; then
    rm -f "$APP_DIR/config.ini" "$APP_DIR/.pc_id"
    echo "Configuración eliminada."
else
    echo "Configuración conservada."
fi

echo ""
DB_FILE="$APP_DIR/biblioteca_local.db"
if [[ -f "$DB_FILE" ]]; then
    echo "AVISO: la base de datos local puede tener sesiones aún no sincronizadas con el servidor."
    read -rp "¿Borrar la base de datos local (biblioteca_local.db)? [s/N]: " resp_db
    if [[ "${resp_db,,}" == "s" ]]; then
        rm -f "$DB_FILE" "$DB_FILE-wal" "$DB_FILE-shm"
        echo "Base de datos local eliminada."
    else
        echo "Base de datos local conservada."
    fi
fi

echo ""
echo "Verificando que no haya quedado nada regenerado..."
sleep 1
limpiar_artefactos

if find "$APP_DIR" -type d -name "__pycache__" 2>/dev/null | grep -q .; then
    echo "AVISO: __pycache__ se sigue regenerando. Revisa si hay algún proceso corriendo main.py (ps -ef | grep main.py)."
else
    echo "Cache (__pycache__) eliminado."
fi

if [[ -f "$APP_DIR/sync.log" ]]; then
    echo "AVISO: sync.log se sigue regenerando. Revisa si hay algún proceso corriendo main.py (ps -ef | grep main.py)."
else
    echo "sync.log eliminado."
fi

if [[ -f "$APP_DIR/hardware.log" ]]; then
    echo "AVISO: hardware.log se sigue regenerando. Revisa si hay algún proceso corriendo main.py (ps -ef | grep main.py)."
else
    echo "hardware.log eliminado."
fi

echo ""
echo "Para volver a instalar y configurar: python3 $APP_DIR/setup.py"
echo "=== Listo ==="
