from datetime import datetime

from core.config import TZ_SV, now_sv
import db.hardware as db_hardware

UMBRAL_PENDIENTE_HORAS = 300
UMBRAL_CRITICO_HORAS = 400


def calcular_estado(horas: float) -> str:
    if horas > UMBRAL_CRITICO_HORAS:
        return "critico"
    if horas >= UMBRAL_PENDIENTE_HORAS:
        return "pendiente"
    return "optimo"


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(TZ_SV).replace(tzinfo=None)
    return dt


def registrar_heartbeat(pc_id: str, uptime_seed_segundos: float) -> float:
    """Acumula horas reales transcurridas desde el último heartbeat (o siembra
    el acumulador con el uptime actual del SO si es la primera vez). Persiste
    en hardware_local vía db/hardware.py y devuelve el total acumulado."""
    ahora = now_sv()
    ahora_naive = ahora.replace(tzinfo=None)
    estado_local = db_hardware.obtener_estado_local(pc_id)

    if estado_local is None:
        horas = uptime_seed_segundos / 3600
        ultimo_mantenimiento_conocido = None
    else:
        ultimo_heartbeat = _parse(estado_local["ultimo_heartbeat"]) or ahora_naive
        delta_horas = max(0.0, (ahora_naive - ultimo_heartbeat).total_seconds() / 3600)
        horas = estado_local["horas_acumuladas"] + delta_horas
        ultimo_mantenimiento_conocido = estado_local["ultimo_mantenimiento_conocido"]

    db_hardware.guardar_estado_local(pc_id, horas, ahora.isoformat(), ultimo_mantenimiento_conocido)
    return horas


def aplicar_reset_si_corresponde(pc_id: str, ultimo_mantenimiento_servidor: str | None) -> float | None:
    """Si el servidor reporta un mantenimiento más reciente que el último
    conocido localmente, resetea el acumulador a 0. Devuelve las horas nuevas
    (0.0) si hubo reset, o None si no correspondía."""
    if not ultimo_mantenimiento_servidor:
        return None

    estado_local = db_hardware.obtener_estado_local(pc_id)
    conocido = estado_local["ultimo_mantenimiento_conocido"] if estado_local else None

    if conocido is not None:
        servidor_dt = _parse(ultimo_mantenimiento_servidor)
        conocido_dt = _parse(conocido)
        if servidor_dt is not None and conocido_dt is not None and servidor_dt <= conocido_dt:
            return None

    db_hardware.guardar_estado_local(pc_id, 0.0, now_sv().isoformat(), ultimo_mantenimiento_servidor)
    return 0.0
