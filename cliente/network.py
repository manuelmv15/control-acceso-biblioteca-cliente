import requests
from config import SERVER_URL


def hay_conexion(timeout: int = 5) -> bool:
    try:
        r = requests.get(f"{SERVER_URL}/health", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def obtener_estudiante(carnet: str) -> dict | None:
    try:
        r = requests.get(f"{SERVER_URL}/estudiantes/{carnet}", timeout=8)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def registrar_estudiante(datos: dict) -> bool:
    try:
        r = requests.post(f"{SERVER_URL}/estudiantes", json=datos, timeout=8)
        return r.status_code in (200, 201, 409)
    except Exception:
        return False


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
