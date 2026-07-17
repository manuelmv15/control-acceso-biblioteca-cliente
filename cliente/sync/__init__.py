import logging
import threading
from pathlib import Path

from core.config import PC_ID, PC_NOMBRE, SYNC_INTERVAL, SERVER_URL
from db.sesiones import obtener_pendientes, marcar_sincronizado
from db.estudiantes import (
    buscar_estudiante_cache,
    obtener_estudiantes_pendientes,
    marcar_estudiante_sincronizado,
)
from network.client import hay_conexion
from network.sesiones import enviar_sesiones, enviar_estado
from network.estudiantes import registrar_estudiante, actualizar_estudiante
import core.estado as estado_mod

LOG_FILE = Path(__file__).parent.parent / "sync.log"
log = logging.getLogger("sync")
log.setLevel(logging.INFO)
log.propagate = False
if not log.handlers:
    _formatter = logging.Formatter("%(asctime)s [SYNC] %(message)s")
    for _handler in (logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()):
        _handler.setFormatter(_formatter)
        log.addHandler(_handler)

_wake = threading.Event()


def _sincronizar_estudiantes_pendientes():
    """Reenvía al servidor los registros/actualizaciones de estudiantes que
    se guardaron localmente sin conexión (ver ui/registro.py)."""
    pendientes = obtener_estudiantes_pendientes()
    if not pendientes:
        return
    sincronizados = 0
    for est in pendientes:
        modo = est.get("pendiente_modo") or "crear"
        if modo == "actualizar":
            ok = actualizar_estudiante(est["carnet"], est) or registrar_estudiante(est)
        else:
            ok = registrar_estudiante(est)
        if ok:
            marcar_estudiante_sincronizado(est["carnet"])
            sincronizados += 1
    log.info(f"Estudiantes pendientes: {sincronizados}/{len(pendientes)} sincronizados")


def _ejecutar_ciclo():
    if not hay_conexion():
        log.info("Sin conexión — skip")
        return

    _sincronizar_estudiantes_pendientes()

    estado_actual = estado_mod.get_estado()
    enviar_estado({
        "pc_id": PC_ID,
        "pc_nombre": PC_NOMBRE,
        "sesion_activa": estado_actual["activa"],
        "carnet": estado_actual["carnet"],
        "nombre": estado_actual["nombre"],
        "hora_inicio": estado_actual["hora_inicio"],
        "carrera": estado_actual["carrera"],
        "facultad": estado_actual["facultad"],
        "sexo": estado_actual["sexo"],
        "fecha_nacimiento": estado_actual["fecha_nacimiento"],
    })

    pendientes = obtener_pendientes()
    if not pendientes:
        log.info("Sin pendientes")
        return

    sesiones_enriquecidas = []
    for s in pendientes:
        sesion = dict(s)
        if s["carnet"]:
            est = buscar_estudiante_cache(s["carnet"])
            if est:
                sesion["nombre"] = est.get("nombre")
                sesion["carrera"] = est.get("carrera")
                sesion["facultad"] = est.get("facultad")
                sesion["sexo"] = est.get("sexo")
                sesion["fecha_nacimiento"] = est.get("fecha_nacimiento")
        sesiones_enriquecidas.append(sesion)

    payload = {
        "pc_id": PC_ID,
        "pc_nombre": PC_NOMBRE,
        "sesiones": sesiones_enriquecidas,
    }
    ok = enviar_sesiones(payload)
    if ok:
        ids = [s["id"] for s in pendientes]
        marcar_sincronizado(ids)
        log.info(f"Sincronizadas {len(ids)} sesiones")
    else:
        log.warning("Servidor rechazó el payload — reintentará")


def _ciclo_sync():
    while True:
        _wake.wait(timeout=SYNC_INTERVAL)
        _wake.clear()
        try:
            _ejecutar_ciclo()
        except Exception as e:
            log.error(f"Error inesperado: {e}")


def forzar_sync():
    """Despierta el daemon para sincronizar ahora sin esperar el intervalo."""
    _wake.set()


def iniciar():
    t = threading.Thread(target=_ciclo_sync, daemon=True, name="sync-worker")
    t.start()
    log.info(f"Sync daemon iniciado — intervalo {SYNC_INTERVAL}s → {SERVER_URL}")
    return t
