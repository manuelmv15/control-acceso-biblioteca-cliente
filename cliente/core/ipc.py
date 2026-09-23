"""Protocolo entre la UI del kiosko y el servicio en segundo plano.

La UI corre con el usuario de la sesión gráfica (el mismo que usa el
estudiante) y el servicio con un usuario propio, dueño de config.ini, de la
clave de cifrado y de la base local. La UI nunca toca esos archivos: le pide
al servicio operaciones concretas (buscar un carnet, abrir o cerrar la
sesión, verificar el PIN de administrador...) a través de un socket UNIX.

Formato: una petición por conexión. El cliente envía una línea JSON
`{"op": "<nombre>", "args": {...}}` y el servicio responde con otra línea:
`{"ok": true, "resultado": ...}` o `{"ok": false, "error": "<codigo>",
"mensaje": "<texto>"}`.

Sin efectos secundarios al importar: lo usan la UI, el servicio y los tests.
"""
import json
import os
from pathlib import Path

# Límite de una línea de petición o respuesta. Las operaciones reales ocupan
# unos cientos de bytes; el límite evita que un cliente agote la memoria
# del servicio con una línea interminable.
MAX_BYTES_MENSAJE = 64 * 1024

# Directorio que crea systemd para el servicio (RuntimeDirectory=biblioteca).
DIR_SOCKET_SISTEMA = Path("/run/biblioteca")
NOMBRE_SOCKET = "kiosko.sock"


class ErrorProtocolo(ValueError):
    """Mensaje que no cumple el formato del protocolo."""


def ruta_socket() -> Path:
    """Ruta del socket del servicio. `BIBLIOTECA_SOCKET` tiene prioridad;
    si no, se usa /run/biblioteca/ cuando existe (instalación con el
    servicio de systemd) o, en desarrollo, el directorio de runtime del
    propio usuario ($XDG_RUNTIME_DIR, que solo él puede escribir)."""
    explicita = os.environ.get("BIBLIOTECA_SOCKET")
    if explicita:
        return Path(explicita)
    if DIR_SOCKET_SISTEMA.is_dir():
        return DIR_SOCKET_SISTEMA / NOMBRE_SOCKET
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        return Path(runtime) / f"biblioteca-{NOMBRE_SOCKET}"
    raise RuntimeError(
        "No se pudo determinar la ruta del socket del servicio del kiosko: "
        f"no existe {DIR_SOCKET_SISTEMA} ni está definida XDG_RUNTIME_DIR. "
        "Definí BIBLIOTECA_SOCKET con la misma ruta en el servicio y en la UI."
    )


def codificar(mensaje: dict) -> bytes:
    datos = json.dumps(mensaje, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    if len(datos) > MAX_BYTES_MENSAJE:
        raise ErrorProtocolo("mensaje demasiado grande")
    return datos


def decodificar(linea: bytes) -> dict:
    if len(linea) > MAX_BYTES_MENSAJE:
        raise ErrorProtocolo("mensaje demasiado grande")
    if not linea.endswith(b"\n"):
        raise ErrorProtocolo("mensaje incompleto")
    try:
        mensaje = json.loads(linea)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ErrorProtocolo("JSON inválido") from exc
    if not isinstance(mensaje, dict):
        raise ErrorProtocolo("se esperaba un objeto JSON")
    return mensaje


def respuesta_ok(resultado=None) -> dict:
    return {"ok": True, "resultado": resultado}


def respuesta_error(error: str, mensaje: str = "") -> dict:
    return {"ok": False, "error": error, "mensaje": mensaje}
