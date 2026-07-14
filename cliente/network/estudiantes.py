import requests
from core.config import SERVER_URL


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


def actualizar_estudiante(carnet: str, datos: dict) -> bool:
    try:
        r = requests.put(f"{SERVER_URL}/estudiantes/{carnet}", json=datos, timeout=8)
        return r.status_code in (200, 201)
    except Exception:
        return False
