"""Envío de la cola de sesiones al servidor por lotes (lo usa sync/).

Mandar toda la cola en un solo POST /sync la bloqueaba para siempre en dos
casos: si pasaba del máximo de sesiones que acepta el servidor (p. ej. tras
semanas sin red), o si una sola sesión traía datos que el servidor rechaza
(422). Como el servidor valida el lote completo, nada se marcaba enviado y
el mismo lote se reintentaba en cada ciclo.

Aquí la cola sale en lotes de TAMANO_LOTE y, si un lote recibe 422, se parte
en mitades hasta aislar las sesiones inválidas. Esas se marcan rechazadas y
las demás se envían normalmente. Un fallo de red, un 429 o cualquier otra
respuesta corta el envío sin marcar nada, para reintentar en el próximo
ciclo.

Sin efectos secundarios al importar: las funciones de red y de la base local
llegan como parámetros, así los tests no necesitan ni `requests` ni
config.ini.
"""
from collections.abc import Callable
from dataclasses import dataclass

# Coincide con el máximo por defecto del servidor (SYNC_MAX_SESIONES).
TAMANO_LOTE = 100

HTTP_OK = 200
HTTP_DATOS_INVALIDOS = 422


@dataclass
class ResultadoEnvio:
    enviadas: int = 0
    rechazadas: int = 0
    completo: bool = True  # False si se cortó por red/429 y quedan pendientes


def enviar_por_lotes(
    obtener_lote: Callable[[int], list[dict]],
    enviar: Callable[[list[dict]], int | None],
    marcar_enviadas: Callable[[list], None],
    marcar_rechazadas: Callable[[list], None],
    tamano: int = TAMANO_LOTE,
) -> ResultadoEnvio:
    """`obtener_lote(n)` devuelve hasta n sesiones pendientes; `enviar(sesiones)`
    las manda y devuelve el código HTTP (None si no hubo respuesta).

    Cada lote termina con todas sus sesiones marcadas (enviadas o rechazadas)
    o con el envío cortado, así que el bucle siempre avanza o se detiene."""
    resultado = ResultadoEnvio()
    while True:
        lote = obtener_lote(tamano)
        if not lote:
            return resultado
        if not _enviar_aislando(lote, enviar, marcar_enviadas, marcar_rechazadas, resultado):
            resultado.completo = False
            return resultado


def _enviar_aislando(lote, enviar, marcar_enviadas, marcar_rechazadas, resultado) -> bool:
    """Devuelve False si hay que dejar de enviar en este ciclo."""
    status = enviar(lote)
    ids = [s["id"] for s in lote]
    if status == HTTP_OK:
        marcar_enviadas(ids)
        resultado.enviadas += len(ids)
        return True
    if status != HTTP_DATOS_INVALIDOS:
        return False
    if len(lote) == 1:
        marcar_rechazadas(ids)
        resultado.rechazadas += 1
        return True
    mitad = len(lote) // 2
    return (
        _enviar_aislando(lote[:mitad], enviar, marcar_enviadas, marcar_rechazadas, resultado)
        and _enviar_aislando(lote[mitad:], enviar, marcar_enviadas, marcar_rechazadas, resultado)
    )
