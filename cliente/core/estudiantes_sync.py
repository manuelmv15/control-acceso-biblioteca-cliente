"""Reenvío al servidor de los estudiantes que quedaron pendientes en la
caché local (registrados o editados sin conexión). Lo usa sync/.

Si el servidor responde que el carnet ya existe, el registro local no se da
por bueno: el estudiante pudo haberse registrado sin red con un carnet que
ya estaba en el servidor (por error o a propósito), y dejar esos datos en
la caché hacía que el kiosko los mostrara y los reenviara en cada sync. En
ese caso la caché se reemplaza por la ficha del servidor.

Sin efectos secundarios al importar: la red llega como parámetro, igual que
en core/lotes_sync.py.
"""
from dataclasses import dataclass, field

from db.estudiantes import (
    guardar_estudiante_del_servidor,
    marcar_estudiante_sincronizado,
    obtener_estudiantes_pendientes,
)
from network.errores import CarnetYaRegistrado, ServidorNoDisponible


@dataclass
class ResultadoEstudiantes:
    pendientes: int = 0
    sincronizados: int = 0
    # Carnets cuya caché se reemplazó por la ficha del servidor.
    reemplazados: list[str] = field(default_factory=list)


def sincronizar_pendientes(red) -> ResultadoEstudiantes:
    """`red` expone obtener_estudiante, registrar_estudiante y
    actualizar_estudiante con el contrato de network/estudiantes.py. Lo que
    no se pudo resolver queda pendiente para el próximo ciclo."""
    pendientes = obtener_estudiantes_pendientes()
    resultado = ResultadoEstudiantes(pendientes=len(pendientes))
    for est in pendientes:
        carnet = est["carnet"]
        try:
            if (est.get("pendiente_modo") or "crear") == "actualizar":
                # Si falla el PUT puede ser que la ficha nunca llegó al
                # servidor (se registró y se editó sin red): se intenta crear.
                ok = red.actualizar_estudiante(carnet, est) or red.registrar_estudiante(est)
            else:
                ok = red.registrar_estudiante(est)
        except CarnetYaRegistrado:
            if reemplazar_con_ficha_del_servidor(red, carnet):
                resultado.reemplazados.append(carnet)
            continue
        if ok:
            marcar_estudiante_sincronizado(carnet)
            resultado.sincronizados += 1
    return resultado


def reemplazar_con_ficha_del_servidor(red, carnet: str) -> bool:
    """Sobrescribe la caché local de `carnet` con la ficha del servidor.
    Devuelve False (y deja la caché como estaba) si no se pudo obtener."""
    try:
        datos = red.obtener_estudiante(carnet)
    except ServidorNoDisponible:
        return False
    if not datos:
        return False
    guardar_estudiante_del_servidor(carnet, datos)
    return True
