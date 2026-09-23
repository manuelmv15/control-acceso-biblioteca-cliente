import requests
from core.config import KIOSK_API_KEY, PC_ID, SERVER_URL, VERIFY_TLS

from network.errores import CarnetYaRegistrado, ServidorNoDisponible

_HEADERS = {"X-Kiosk-Key": KIOSK_API_KEY, "X-PC-Id": PC_ID} if KIOSK_API_KEY else {}


def obtener_estudiante(carnet: str) -> dict | None:
    """Devuelve la ficha, o None solo si el servidor confirma que no existe
    (404). Cualquier otro resultado lanza ServidorNoDisponible: tratar un
    fallo de red o un 429 como «no existe» llevaba a registrar de nuevo un
    carnet que ya estaba en el servidor."""
    try:
        r = requests.get(f"{SERVER_URL}/estudiantes/{carnet}", headers=_HEADERS, timeout=8, verify=VERIFY_TLS)
    except Exception as exc:
        raise ServidorNoDisponible(str(exc)) from exc
    if r.status_code == 200:
        return r.json()
    if r.status_code == 404:
        return None
    raise ServidorNoDisponible(f"HTTP {r.status_code}")


def registrar_estudiante(datos: dict) -> bool:
    """True si el servidor creó la ficha, False si no se pudo enviar.
    Lanza CarnetYaRegistrado si el carnet ya existía: no es un éxito, porque
    la ficha del servidor no tiene por qué coincidir con `datos`."""
    try:
        r = requests.post(f"{SERVER_URL}/estudiantes", json=datos, headers=_HEADERS, timeout=8, verify=VERIFY_TLS)
    except Exception:
        return False
    if r.status_code == 409:
        raise CarnetYaRegistrado(datos.get("carnet"))
    return r.status_code in (200, 201)


def actualizar_estudiante(carnet: str, datos: dict) -> bool:
    try:
        r = requests.put(f"{SERVER_URL}/estudiantes/{carnet}", json=datos, headers=_HEADERS, timeout=8, verify=VERIFY_TLS)
        return r.status_code in (200, 201)
    except Exception:
        return False
