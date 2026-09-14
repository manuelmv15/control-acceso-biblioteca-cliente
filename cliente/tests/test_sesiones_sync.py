"""Tests del flujo de sync offline→online de sesiones (db/sesiones.py), que
es lo que sync/_ejecutar_ciclo orquesta cada SYNC_INTERVAL segundos: una
sesión se guarda localmente apenas empieza (haya o no conexión), se le pone
hora_fin al cerrarla, y solo se marca sincronizada cuando el servidor la
aceptó — así una caída de red no pierde sesiones, solo las reintenta en el
próximo ciclo.

No se importan network/sesiones.py ni sync/__init__.py: el primero
necesitaría mockear `requests` (no hay una librería de mocking HTTP entre las
dependencias del proyecto) y el segundo tiene efectos secundarios de import
(arma un logger con FileHandler sobre cliente/sync.log). En su lugar, estos
tests ejercitan el contrato real que _ejecutar_ciclo usa contra la base de
datos (obtener_pendientes / marcar_sincronizado) y representan el resultado
del envío HTTP con un simple booleano, tal como hace ese mismo código
(`ok = enviar_sesiones(payload); if ok: marcar_sincronizado(ids)`)."""

from db.sesiones import (
    actualizar_hora_fin,
    guardar_sesion,
    marcar_sincronizado,
    obtener_pendientes,
)


def _sesion(id_, pc_id="PC-01", carnet="AB12345",
            hora_inicio="2026-09-01T10:00:00", fecha="2026-09-01"):
    return {
        "id": id_,
        "pc_id": pc_id,
        "carnet": carnet,
        "hora_inicio": hora_inicio,
        "hora_fin": None,
        "fecha": fecha,
    }


def test_sesion_en_curso_no_aparece_como_pendiente(db_temporal):
    """Mientras la sesión sigue activa (hora_fin NULL) no debe sincronizarse
    todavía — mandarla a mitad de sesión perdería la hora_fin real."""
    guardar_sesion(_sesion("s1"))
    assert obtener_pendientes() == []


def test_sesion_cerrada_queda_pendiente_hasta_que_se_sincroniza(db_temporal):
    guardar_sesion(_sesion("s1"))
    actualizar_hora_fin("s1", "2026-09-01T11:00:00")

    pendientes = obtener_pendientes()
    assert [s["id"] for s in pendientes] == ["s1"]
    assert pendientes[0]["sincronizado"] == 0
    assert pendientes[0]["hora_fin"] == "2026-09-01T11:00:00"


def test_marcar_sincronizado_saca_la_sesion_de_pendientes(db_temporal):
    guardar_sesion(_sesion("s1"))
    actualizar_hora_fin("s1", "2026-09-01T11:00:00")

    marcar_sincronizado(["s1"])

    assert obtener_pendientes() == []


def test_envio_fallido_deja_la_sesion_pendiente_para_reintentar(db_temporal):
    """Si el servidor rechaza el payload, `ok` da False y _ejecutar_ciclo no
    llama a marcar_sincronizado — la sesión sigue en la cola para el próximo
    ciclo. Este test simula exactamente esa rama."""
    guardar_sesion(_sesion("s1"))
    actualizar_hora_fin("s1", "2026-09-01T11:00:00")
    ids_pendientes = [s["id"] for s in obtener_pendientes()]

    ok = False  # equivalente a que enviar_sesiones() haya devuelto False
    if ok:
        marcar_sincronizado(ids_pendientes)

    assert [s["id"] for s in obtener_pendientes()] == ["s1"]


def test_solo_se_marcan_sincronizadas_las_sesiones_realmente_enviadas(db_temporal):
    """Dos sesiones pendientes; solo una viajó en el payload aceptado por el
    servidor (p. ej. la otra se generó recién, entre leer pendientes y
    enviar). marcar_sincronizado no debe tocar la que no se mandó."""
    guardar_sesion(_sesion("s1"))
    actualizar_hora_fin("s1", "2026-09-01T11:00:00")
    guardar_sesion(_sesion("s2", carnet="CD67890"))
    actualizar_hora_fin("s2", "2026-09-01T11:05:00")

    marcar_sincronizado(["s1"])

    restantes = {s["id"] for s in obtener_pendientes()}
    assert restantes == {"s2"}


def test_marcar_sincronizado_con_lista_vacia_no_falla(db_temporal):
    # Rama explícita en db/sesiones.py: `if not ids: return` — cubre el caso
    # de un ciclo de sync sin nada pendiente que enviar.
    marcar_sincronizado([])
