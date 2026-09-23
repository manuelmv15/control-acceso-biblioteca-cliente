"""Cliente del socket del servicio del kiosko (ver core/ipc.py y servicio/).

La UI no lee config.ini ni la base local: todo lo que necesita se lo pide
al servicio con `llamar()`.
"""
import socket

from core.ipc import MAX_BYTES_MENSAJE, ErrorProtocolo, codificar, decodificar, ruta_socket

# Mayor que la peor operación del servicio: registrar un estudiante puede
# encadenar varias consultas al servidor, cada una con su propio timeout.
TIMEOUT_SEGUNDOS = 45


class ServicioNoDisponible(Exception):
    """No se pudo hablar con el servicio (no está corriendo, sin permisos
    sobre el socket, timeout o respuesta ilegible)."""


class ErrorServicio(Exception):
    """El servicio respondió con un error de la operación."""

    def __init__(self, codigo: str, mensaje: str = ""):
        super().__init__(mensaje or codigo)
        self.codigo = codigo
        self.mensaje = mensaje


def llamar(op: str, **args):
    try:
        ruta = ruta_socket()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conexion:
            conexion.settimeout(TIMEOUT_SEGUNDOS)
            conexion.connect(str(ruta))
            conexion.sendall(codificar({"op": op, "args": args}))
            with conexion.makefile("rb") as lector:
                respuesta = decodificar(lector.readline(MAX_BYTES_MENSAJE + 1))
    except (OSError, RuntimeError, ErrorProtocolo) as exc:
        raise ServicioNoDisponible(str(exc)) from exc
    if respuesta.get("ok"):
        return respuesta.get("resultado")
    raise ErrorServicio(respuesta.get("error", "error_desconocido"), respuesta.get("mensaje", ""))
