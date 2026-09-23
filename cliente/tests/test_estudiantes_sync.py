"""Tests del reenvío de estudiantes pendientes (core/estudiantes_sync.py)
contra la base local real. La red se representa con `RedFalsa`, que
responde como el servidor: 409 si el carnet ya existe."""

from core.estudiantes_sync import sincronizar_pendientes
from db.estudiantes import buscar_estudiante_cache, guardar_estudiante_cache, obtener_estudiantes_pendientes
from network.errores import CarnetYaRegistrado, ServidorNoDisponible

ESTUDIANTE = {
    "carnet": "AB12345",
    "nombre": "Ana Pérez",
    "carrera": "Ingeniería de Sistemas Informáticos",
    "facultad": "Departamento de Ingeniería y Arquitectura",
    "fecha_nacimiento": "2003",
    "sexo": "F",
}


class RedFalsa:
    def __init__(self, en_servidor=None, acepta=True, caido=False):
        self.en_servidor = dict(en_servidor or {})
        self.acepta = acepta
        self.caido = caido
        self.registrados = []

    def obtener_estudiante(self, carnet):
        if self.caido:
            raise ServidorNoDisponible("sin respuesta")
        return self.en_servidor.get(carnet)

    def registrar_estudiante(self, datos):
        self.registrados.append(datos["carnet"])
        if datos["carnet"] in self.en_servidor:
            raise CarnetYaRegistrado(datos["carnet"])
        if self.acepta:
            self.en_servidor[datos["carnet"]] = dict(datos)
        return self.acepta

    def actualizar_estudiante(self, carnet, datos):
        return False


def _pendiente(est, modo="crear"):
    guardar_estudiante_cache(est, sincronizado=0, pendiente_modo=modo)


def test_registro_pendiente_nuevo_se_marca_sincronizado(db_temporal):
    _pendiente(ESTUDIANTE)
    red = RedFalsa()

    resultado = sincronizar_pendientes(red)

    assert (resultado.pendientes, resultado.sincronizados, resultado.reemplazados) == (1, 1, [])
    assert obtener_estudiantes_pendientes() == []
    assert red.en_servidor["AB12345"]["nombre"] == "Ana Pérez"


def test_registro_pendiente_de_carnet_existente_toma_la_ficha_del_servidor(db_temporal):
    """Registrado sin red con un carnet que ya existía: el 409 no es un
    éxito. La caché pasa a tener la ficha del servidor y no los datos
    tecleados, que si no se mostrarían y se reenviarían en cada sync."""
    _pendiente({**ESTUDIANTE, "nombre": "Impostor", "sexo": "M"})
    red = RedFalsa(en_servidor={"AB12345": {**ESTUDIANTE, "id": "x", "fecha_registro": "2026-01-01"}})

    resultado = sincronizar_pendientes(red)

    assert resultado.reemplazados == ["AB12345"]
    assert resultado.sincronizados == 0
    cache = buscar_estudiante_cache("AB12345")
    assert (cache["nombre"], cache["sexo"], cache["sincronizado"]) == ("Ana Pérez", "F", 1)
    assert red.en_servidor["AB12345"]["nombre"] == "Ana Pérez"


def test_carnet_existente_sin_poder_leer_la_ficha_queda_pendiente(db_temporal):
    _pendiente({**ESTUDIANTE, "nombre": "Impostor"})
    red = RedFalsa(en_servidor={"AB12345": ESTUDIANTE})
    red.caido = True

    resultado = sincronizar_pendientes(red)

    assert resultado.reemplazados == []
    pendientes = obtener_estudiantes_pendientes()
    assert [(p["carnet"], p["nombre"]) for p in pendientes] == [("AB12345", "Impostor")]


def test_actualizacion_pendiente_de_ficha_que_no_llego_al_servidor_la_crea(db_temporal):
    _pendiente(ESTUDIANTE, modo="actualizar")
    red = RedFalsa()

    resultado = sincronizar_pendientes(red)

    assert resultado.sincronizados == 1
    assert red.registrados == ["AB12345"]


def test_fallo_de_red_deja_el_registro_pendiente(db_temporal):
    _pendiente(ESTUDIANTE)

    resultado = sincronizar_pendientes(RedFalsa(acepta=False))

    assert resultado.sincronizados == 0
    assert len(obtener_estudiantes_pendientes()) == 1
