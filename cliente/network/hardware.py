import requests
from core.config import SERVER_URL, VERIFY_TLS


def enviar_hardware(pc_id: str, payload: dict) -> dict | None:
    """Envía la lectura de hardware al servidor. Devuelve el JSON de respuesta
    (con ultimo_mantenimiento/estado_mantenimiento) o None si falló."""
    try:
        r = requests.post(f"{SERVER_URL}/pcs/{pc_id}/hardware", json=payload, timeout=10, verify=VERIFY_TLS)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None
