import requests
from core.config import SERVER_URL, KIOSK_API_KEY, VERIFY_TLS

_HEADERS = {"X-Kiosk-Key": KIOSK_API_KEY} if KIOSK_API_KEY else {}


def obtener_estudiante(carnet: str) -> dict | None:
    try:
        r = requests.get(f"{SERVER_URL}/estudiantes/{carnet}", headers=_HEADERS, timeout=8, verify=VERIFY_TLS)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def registrar_estudiante(datos: dict) -> bool:
    try:
        r = requests.post(f"{SERVER_URL}/estudiantes", json=datos, headers=_HEADERS, timeout=8, verify=VERIFY_TLS)
        return r.status_code in (200, 201, 409)
    except Exception:
        return False


def actualizar_estudiante(carnet: str, datos: dict) -> bool:
    try:
        r = requests.put(f"{SERVER_URL}/estudiantes/{carnet}", json=datos, headers=_HEADERS, timeout=8, verify=VERIFY_TLS)
        return r.status_code in (200, 201)
    except Exception:
        return False
