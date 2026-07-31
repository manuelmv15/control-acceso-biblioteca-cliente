#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
REPO_DIR="$(cd "$APP_DIR/.." && pwd)"
PYTHON="${PYTHON:-python3}"
SERVICE_NAME="biblioteca-kiosko"

PIP_ERROR_LOG="$(mktemp)"
trap 'rm -f "$PIP_ERROR_LOG"' EXIT

echo "=== Actualizando Biblioteca Kiosko ==="

if [[ ! -d "$REPO_DIR/.git" ]]; then
    echo "ERROR: $REPO_DIR no es un repositorio git. No se puede actualizar."
    exit 1
fi

cd "$REPO_DIR"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
echo "Rama actual: $BRANCH"

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    echo "ERROR: hay cambios locales sin confirmar en el repositorio."
    echo "Resuélvelos antes de actualizar (git stash / git checkout -- .)."
    exit 1
fi

echo "Descargando cambios..."
git fetch origin "$BRANCH"

LOCAL_REV="$(git rev-parse HEAD)"
REMOTE_REV="$(git rev-parse "origin/$BRANCH")"

if [[ "$LOCAL_REV" == "$REMOTE_REV" ]]; then
    echo "Ya está en la última versión ($LOCAL_REV)."
else
    echo "Aplicando actualización ($LOCAL_REV -> $REMOTE_REV)..."
    git merge --ff-only "origin/$BRANCH"
fi

echo ""
echo "Actualizando dependencias..."
if ! "$PYTHON" -m pip install -q -r "$APP_DIR/requirements.txt" 2>"$PIP_ERROR_LOG"; then
    if grep -q "externally-managed-environment" "$PIP_ERROR_LOG"; then
        echo "El entorno de Python es externally-managed (PEP 668) — reintentando con --break-system-packages."
        echo "Esta PC es de uso dedicado para el kiosko, así que instalar en el Python del sistema es seguro."
        "$PYTHON" -m pip install -q --break-system-packages -r "$APP_DIR/requirements.txt"
    else
        cat "$PIP_ERROR_LOG" >&2
        exit 1
    fi
fi

echo ""
if systemctl is-enabled "$SERVICE_NAME" &>/dev/null; then
    if [[ -t 0 ]]; then
        read -r -p "¿Reiniciar el servicio ahora para aplicar los cambios? (s/n) " RESPUESTA
    else
        RESPUESTA="n"
        echo "Ejecución sin terminal (p. ej. cron) — no se reinicia automáticamente."
    fi
    if [[ "$RESPUESTA" == "s" || "$RESPUESTA" == "S" ]]; then
        echo "Reiniciando servicio systemd..."
        sudo systemctl restart "$SERVICE_NAME"
        echo "Servicio reiniciado con la nueva versión."
    else
        echo "Reinicio pendiente. Ejecuta 'sudo systemctl restart $SERVICE_NAME' cuando quieras aplicar los cambios."
    fi
elif pgrep -f "$APP_DIR/main.py" &>/dev/null; then
    echo "AVISO: la app está corriendo vía autostart de sesión (sin systemd)."
    echo "Cierra la app y vuelve a abrirla (o reinicia sesión) para aplicar los cambios."
else
    echo "Actualización lista. Se aplicará la próxima vez que inicie la app."
fi

echo ""
echo "=== Actualización completada ==="
