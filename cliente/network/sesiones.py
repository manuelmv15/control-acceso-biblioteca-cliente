import requests
from core.config import SERVER_URL, KIOSK_API_KEY, PC_ID, VERIFY_TLS

_HEADERS = {"X-Kiosk-Key": KIOSK_API_KEY, "X-PC-Id": PC_ID} if KIOSK_API_KEY else {}


def enviar_estado(payload: dict) -> bool:
    try:
        r = requests.post(f"{SERVER_URL}/estado", json=payload, headers=_HEADERS, timeout=5, verify=VERIFY_TLS)
        return r.status_code == 200
    except Exception:
        return False


def enviar_sesiones(payload: dict) -> bool:
    try:
        r = requests.post(f"{SERVER_URL}/sync", json=payload, headers=_HEADERS, timeout=15, verify=VERIFY_TLS)
        return r.status_code == 200
    except Exception:
        return False
