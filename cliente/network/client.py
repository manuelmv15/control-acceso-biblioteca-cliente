import requests
from core.config import SERVER_URL


def hay_conexion(timeout: int = 5) -> bool:
    try:
        r = requests.get(f"{SERVER_URL}/health", timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False
