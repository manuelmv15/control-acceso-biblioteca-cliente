import threading

_lock = threading.Lock()
_estado = {
    "activa": False,
    "carnet": None,
    "nombre": None,
    "hora_inicio": None,
}


def set_sesion_activa(carnet: str, nombre: str, hora_inicio: str):
    with _lock:
        _estado.update({
            "activa": True,
            "carnet": carnet,
            "nombre": nombre,
            "hora_inicio": hora_inicio,
        })


def set_sesion_inactiva():
    with _lock:
        _estado.update({
            "activa": False,
            "carnet": None,
            "nombre": None,
            "hora_inicio": None,
        })


def get_estado() -> dict:
    with _lock:
        return dict(_estado)
