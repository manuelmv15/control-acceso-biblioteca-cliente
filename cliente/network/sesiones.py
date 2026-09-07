import requests
from core.config import SERVER_URL, VERIFY_TLS


def enviar_estado(payload: dict) -> bool:
    try:
        r = requests.post(f"{SERVER_URL}/estado", json=payload, timeout=5, verify=VERIFY_TLS)
        return r.status_code == 200
    except Exception:
        return False


def enviar_sesiones(payload: dict) -> bool:
    try:
        r = requests.post(f"{SERVER_URL}/sync", json=payload, timeout=15, verify=VERIFY_TLS)
        return r.status_code == 200
    except Exception:
        return False
