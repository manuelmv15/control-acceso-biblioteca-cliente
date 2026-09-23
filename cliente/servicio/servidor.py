"""Socket UNIX por el que la UI le pide operaciones al servicio.

Controles, del más externo al más interno:
1. Permisos del sistema de archivos: el socket se crea con modo 0660 (y, si
   se puede, con el grupo de la UI). En la instalación de producción además
   vive en un directorio al que solo acceden el servicio y ese grupo.
2. Credenciales del proceso que se conecta (SO_PEERCRED, las da el kernel y
   no se pueden falsificar): solo el propio usuario del servicio o un
   miembro del grupo de la UI (core.config.GRUPO_UI).
3. Lista cerrada de operaciones y de argumentos (OPERACIONES) y validación
   de cada argumento en servicio/operaciones.py.
"""
import grp
import logging
import os
import pwd
import socket
import socketserver
import stat
import struct
from pathlib import Path

from core.ipc import (
    MAX_BYTES_MENSAJE,
    ErrorProtocolo,
    codificar,
    decodificar,
    respuesta_error,
    respuesta_ok,
)

from servicio.operaciones import ErrorOperacion, ServicioKiosko

log = logging.getLogger("servicio")

# op -> (argumentos obligatorios, argumentos opcionales). Cualquier otra op
# o argumento se rechaza sin llegar a ServicioKiosko.
OPERACIONES: dict[str, tuple[frozenset, frozenset]] = {
    "info": (frozenset(), frozenset()),
    "buscar_estudiante": (frozenset({"carnet"}), frozenset()),
    "guardar_estudiante": (frozenset({"modo", "datos"}), frozenset()),
    "abrir_sesion": (frozenset(), frozenset({"carnet", "sector"})),
    "cerrar_sesion": (frozenset(), frozenset()),
    "estado_pin_admin": (frozenset(), frozenset()),
    "verificar_pin_admin": (frozenset({"pin"}), frozenset()),
}

# Una conexión que no manda su petición completa en este tiempo se corta,
# para que un cliente lento no retenga hilos del servicio.
TIMEOUT_CONEXION_SEGUNDOS = 10


def despachar(servicio: ServicioKiosko, peticion: dict) -> dict:
    op = peticion.get("op")
    args = peticion.get("args", {})
    if not isinstance(op, str) or op not in OPERACIONES:
        return respuesta_error("op_desconocida", f"operación desconocida: {op!r}")
    if not isinstance(args, dict):
        return respuesta_error("args_invalidos", "args debe ser un objeto")
    obligatorios, opcionales = OPERACIONES[op]
    faltan = obligatorios - args.keys()
    sobran = args.keys() - obligatorios - opcionales
    if faltan or sobran:
        return respuesta_error(
            "args_invalidos", f"faltan {sorted(faltan)}, no se esperaban {sorted(sobran)}"
        )
    try:
        return respuesta_ok(getattr(servicio, op)(**args))
    except ErrorOperacion as exc:
        return respuesta_error(exc.codigo, exc.mensaje)
    except Exception:
        log.exception("Error inesperado en la operación %s", op)
        return respuesta_error("error_interno", "error interno del servicio")


def credenciales_peer(conexion: socket.socket) -> tuple[int, int, int]:
    """(pid, uid, gid) del proceso al otro lado del socket, según el kernel."""
    formato = "3i"
    datos = conexion.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize(formato))
    return struct.unpack(formato, datos)


def peer_autorizado(uid: int, gid: int, grupo_ui: str) -> bool:
    if uid == os.geteuid():
        return True
    if not grupo_ui:
        return False
    try:
        grupo = grp.getgrnam(grupo_ui)
    except KeyError:
        return False
    if gid == grupo.gr_gid:
        return True
    try:
        nombre = pwd.getpwuid(uid).pw_name
    except KeyError:
        return False
    return nombre in grupo.gr_mem


class _Handler(socketserver.StreamRequestHandler):
    timeout = TIMEOUT_CONEXION_SEGUNDOS

    def handle(self):
        pid, uid, gid = credenciales_peer(self.request)
        if not peer_autorizado(uid, gid, self.server.grupo_ui):
            log.warning("Conexión rechazada: pid=%d uid=%d gid=%d no autorizado", pid, uid, gid)
            return
        try:
            linea = self.rfile.readline(MAX_BYTES_MENSAJE + 1)
        except TimeoutError:
            return
        try:
            respuesta = despachar(self.server.servicio, decodificar(linea))
        except ErrorProtocolo as exc:
            respuesta = respuesta_error("peticion_invalida", str(exc))
        try:
            self.wfile.write(codificar(respuesta))
        except ErrorProtocolo:
            self.wfile.write(codificar(respuesta_error("error_interno", "respuesta demasiado grande")))
        except OSError:
            pass  # el cliente cerró la conexión antes de leer la respuesta


class ServidorKiosko(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True

    def __init__(self, ruta: Path, servicio: ServicioKiosko, grupo_ui: str):
        self.servicio = servicio
        self.grupo_ui = grupo_ui
        self.ruta = Path(ruta)
        _eliminar_socket_viejo(self.ruta)
        # El umask hace que el socket nazca con 0660 en vez de crearse con
        # permisos más abiertos y corregirlos después con chmod.
        umask_anterior = os.umask(0o117)
        try:
            super().__init__(str(self.ruta), _Handler)
        finally:
            os.umask(umask_anterior)
        self._asignar_grupo()

    def _asignar_grupo(self):
        if not self.grupo_ui:
            return
        try:
            gid = grp.getgrnam(self.grupo_ui).gr_gid
        except KeyError:
            log.info("Grupo %s inexistente: el socket solo acepta al usuario del servicio", self.grupo_ui)
            return
        try:
            os.chown(self.ruta, -1, gid)
        except PermissionError:
            # El usuario del servicio no pertenece al grupo: el acceso depende
            # entonces de los permisos del directorio del socket.
            log.warning("No se pudo asignar el grupo %s a %s", self.grupo_ui, self.ruta)

    def server_close(self):
        super().server_close()
        _eliminar_socket_viejo(self.ruta)


def _eliminar_socket_viejo(ruta: Path):
    """Borra un socket que quedó de una ejecución anterior. Nunca borra otro
    tipo de archivo: si en esa ruta hay algo que no es un socket, el bind
    falla y hay que revisarlo a mano."""
    try:
        if not stat.S_ISSOCK(ruta.lstat().st_mode):
            return
    except FileNotFoundError:
        return
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as prueba:
        try:
            prueba.connect(str(ruta))
        except OSError:
            ruta.unlink(missing_ok=True)  # nadie escucha: es un resto de otra ejecución
            return
    raise RuntimeError(f"Ya hay un servicio del kiosko escuchando en {ruta}")
