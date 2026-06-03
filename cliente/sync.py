import logging
import threading
import time
from pathlib import Path

from config import PC_ID, PC_NOMBRE, SYNC_INTERVAL, SERVER_URL
from database import obtener_pendientes, marcar_sincronizado
from network import hay_conexion, enviar_sesiones, enviar_estado
import estado as estado_mod

LOG_FILE = Path(__file__).parent / "sync.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SYNC] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("sync")


def _ciclo_sync():
    while True:
        time.sleep(SYNC_INTERVAL)
        try:
            if not hay_conexion():
                log.info("Sin conexión — skip")
                continue

            estado_actual = estado_mod.get_estado()
            enviar_estado({
                "pc_id": PC_ID,
                "pc_nombre": PC_NOMBRE,
                "sesion_activa": estado_actual["activa"],
                "carnet": estado_actual["carnet"],
                "nombre": estado_actual["nombre"],
                "hora_inicio": estado_actual["hora_inicio"],
            })

            pendientes = obtener_pendientes()
            if not pendientes:
                log.info("Sin pendientes")
                continue

            payload = {
                "pc_id": PC_ID,
                "pc_nombre": PC_NOMBRE,
                "sesiones": pendientes,
            }
            ok = enviar_sesiones(payload)
            if ok:
                ids = [s["id"] for s in pendientes]
                marcar_sincronizado(ids)
                log.info(f"Sincronizadas {len(ids)} sesiones")
            else:
                log.warning("Servidor rechazó el payload — reintentará")
        except Exception as e:
            log.error(f"Error inesperado: {e}")


def iniciar():
    t = threading.Thread(target=_ciclo_sync, daemon=True, name="sync-worker")
    t.start()
    log.info(f"Sync daemon iniciado — intervalo {SYNC_INTERVAL}s → {SERVER_URL}")
    return t
