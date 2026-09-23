import requests
from core.config import KIOSK_API_KEY, PC_ID, SERVER_URL, VERIFY_TLS

_HEADERS = {"X-Kiosk-Key": KIOSK_API_KEY, "X-PC-Id": PC_ID} if KIOSK_API_KEY else {}


def enviar_estado(payload: dict) -> bool:
    try:
        r = requests.post(f"{SERVER_URL}/estado", json=payload, headers=_HEADERS, timeout=5, verify=VERIFY_TLS)
        return r.status_code == 200
    except Exception:
        return False


def enviar_sesiones(payload: dict) -> int | None:
    """Devuelve el código HTTP de la respuesta, o None si no hubo respuesta.
    Quien llama necesita distinguir un 422 (el lote tiene datos inválidos y
    reenviarlo igual no sirve) de un fallo de red o un 429 (reintentar)."""
    try:
        r = requests.post(f"{SERVER_URL}/sync", json=payload, headers=_HEADERS, timeout=15, verify=VERIFY_TLS)
        return r.status_code
    except Exception:
        return None
