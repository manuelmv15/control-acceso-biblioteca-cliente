import threading

_lock = threading.Lock()
_estado = {
    "activa": False,
    "carnet": None,
    "nombre": None,
    "hora_inicio": None,
    "carrera": None,
    "facultad": None,
    "departamento": None,
    "sexo": None,
    "fecha_nacimiento": None,
}


def set_sesion_activa(carnet: str | None, nombre: str, hora_inicio: str,
                      carrera: str = None, facultad: str = None,
                      departamento: str = None, sexo: str = None,
                      fecha_nacimiento: str = None):
    with _lock:
        _estado.update({
            "activa": True,
            "carnet": carnet,
            "nombre": nombre,
            "hora_inicio": hora_inicio,
            "carrera": carrera,
            "facultad": facultad,
            "departamento": departamento,
            "sexo": sexo,
            "fecha_nacimiento": fecha_nacimiento,
        })


def set_sesion_inactiva():
    with _lock:
        _estado.update({
            "activa": False,
            "carnet": None,
            "nombre": None,
            "hora_inicio": None,
            "carrera": None,
            "facultad": None,
            "departamento": None,
            "sexo": None,
            "fecha_nacimiento": None,
        })


def get_estado() -> dict:
    with _lock:
        return dict(_estado)
