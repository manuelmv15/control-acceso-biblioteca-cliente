"""Tests del envío por lotes de la cola de sesiones (core/lotes_sync.py)
contra la base local real (db/sesiones.py). El servidor se representa con
`ServidorFalso`, que responde como POST /sync: rechaza el lote entero con
422 si una sola sesión es inválida o si trae más sesiones de las
permitidas."""

from core.lotes_sync import enviar_por_lotes
from db.connection import get_connection
from db.sesiones import (
    RECHAZADA,
    actualizar_hora_fin,
    guardar_sesion,
    marcar_rechazada,
    marcar_sincronizado,
    obtener_pendientes,
)


class ServidorFalso:
    def __init__(self, invalidas=(), max_sesiones=100, caido=False):
        self.invalidas = set(invalidas)
        self.max_sesiones = max_sesiones
        self.caido = caido
        self.recibidas = []
        self.envios = 0

    def enviar(self, sesiones):
        self.envios += 1
        if self.caido:
            return None
        if len(sesiones) > self.max_sesiones or any(s["id"] in self.invalidas for s in sesiones):
            return 422
        self.recibidas.extend(s["id"] for s in sesiones)
        return 200


def _crear_cerradas(n):
    ids = []
    for i in range(n):
        id_ = f"s{i:04d}"
        guardar_sesion({
            "id": id_, "pc_id": "PC-01", "carnet": "AB12345",
            "hora_inicio": "2026-09-01T10:00:00", "hora_fin": None, "fecha": "2026-09-01",
        })
        actualizar_hora_fin(id_, f"2026-09-01T11:{i // 60:02d}:{i % 60:02d}")
        ids.append(id_)
    return ids


def _enviar(servidor, tamano=100):
    return enviar_por_lotes(
        obtener_lote=lambda n: obtener_pendientes(limite=n),
        enviar=servidor.enviar,
        marcar_enviadas=marcar_sincronizado,
        marcar_rechazadas=marcar_rechazada,
        tamano=tamano,
    )


def _estado(id_):
    conn = get_connection()
    fila = conn.execute("SELECT sincronizado FROM sesiones_pendientes WHERE id = ?", (id_,)).fetchone()
    conn.close()
    return fila["sincronizado"]


def test_una_sesion_invalida_no_bloquea_a_las_demas(db_temporal):
    ids = _crear_cerradas(10)
    servidor = ServidorFalso(invalidas={"s0003"})

    resultado = _enviar(servidor)

    assert resultado.completo
    assert resultado.enviadas == 9
    assert resultado.rechazadas == 1
    assert sorted(servidor.recibidas) == [i for i in ids if i != "s0003"]
    assert obtener_pendientes() == []
    # La rechazada no se borra: queda en la base local para revisarla.
    assert _estado("s0003") == RECHAZADA


def test_la_sesion_rechazada_no_se_reenvia_en_el_siguiente_ciclo(db_temporal):
    _crear_cerradas(5)
    servidor = ServidorFalso(invalidas={"s0000"})
    _enviar(servidor)
    envios_primer_ciclo = servidor.envios

    resultado = _enviar(servidor)

    assert resultado.enviadas == resultado.rechazadas == 0
    # Un solo SELECT vacío, ningún POST nuevo.
    assert servidor.envios == envios_primer_ciclo


def test_cola_mayor_que_el_maximo_del_servidor_se_envia_por_lotes(db_temporal):
    """Tras semanas sin red la cola puede pasar del máximo que acepta el
    servidor; enviarla entera daría 422 siempre."""
    _crear_cerradas(250)
    servidor = ServidorFalso(max_sesiones=100)

    resultado = _enviar(servidor)

    assert resultado.completo
    assert resultado.enviadas == 250
    assert servidor.envios == 3
    assert obtener_pendientes() == []


def test_sin_red_no_se_marca_nada(db_temporal):
    ids = _crear_cerradas(3)
    servidor = ServidorFalso(caido=True)

    resultado = _enviar(servidor)

    assert not resultado.completo
    assert [s["id"] for s in obtener_pendientes()] == ids


def test_error_distinto_de_422_corta_sin_marcar_rechazadas(db_temporal):
    """Un 429 o un 500 no dice nada de los datos de la sesión: hay que
    reintentar, nunca marcarla rechazada."""
    ids = _crear_cerradas(4)

    resultado = enviar_por_lotes(
        obtener_lote=lambda n: obtener_pendientes(limite=n),
        enviar=lambda sesiones: 429,
        marcar_enviadas=marcar_sincronizado,
        marcar_rechazadas=marcar_rechazada,
    )

    assert not resultado.completo
    assert resultado.rechazadas == 0
    assert [s["id"] for s in obtener_pendientes()] == ids


def test_obtener_pendientes_respeta_el_limite_y_el_orden(db_temporal):
    ids = _crear_cerradas(5)
    assert [s["id"] for s in obtener_pendientes(limite=2)] == ids[:2]
