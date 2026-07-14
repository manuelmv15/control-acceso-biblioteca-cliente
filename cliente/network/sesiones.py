import requests
from core.config import SERVER_URL


def enviar_estado(payload: dict) -> bool:
    try:
        r = requests.post(f"{SERVER_URL}/estado", json=payload, timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def enviar_sesiones(payload: dict) -> bool:
    try:
        r = requests.post(f"{SERVER_URL}/sync", json=payload, timeout=15)
        return r.status_code == 200
    except Exception:
        return False
