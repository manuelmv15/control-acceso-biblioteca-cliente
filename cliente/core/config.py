"""Configuración del servicio del kiosko (servicio/). Lee config.ini, que
contiene la API key de la PC y el hash del PIN de administrador, así que
solo debe importarlo el proceso del servicio: la UI corre como otro usuario
del sistema y no tiene permiso de lectura sobre DATA_DIR (ver core/rutas.py).
La UI toma la hora de core/tiempo.py y lo demás se lo pide al servicio."""
import configparser
import os
import uuid
from pathlib import Path
from urllib.parse import urlparse

from core.rutas import DATA_DIR
from core.tiempo import TZ_SV, now_sv  # noqa: F401 (re-exportados para el servicio)

CONFIG_FILE = DATA_DIR / "config.ini"
PC_ID_FILE = DATA_DIR / ".pc_id"

_config = configparser.ConfigParser()
_config.read(CONFIG_FILE, encoding="utf-8")

# Best-effort: protege KIOSK_API_KEY/pin_hash contra otras cuentas del
# sistema si config.ini ya existía de una instalación anterior a este
# chmod (setup.py solo corre una vez, esto corre en cada arranque). Solo
# sirve si el estudiante usa una cuenta distinta de la del servicio: el
# dueño del archivo siempre puede leerlo, por eso la UI corre con otro
# usuario y habla con el servicio por un socket local (ver servicio/).
if CONFIG_FILE.exists():
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass


def _get(section, key, env_var=None, default=""):
    if env_var and os.environ.get(env_var):
        return os.environ[env_var]
    try:
        return _config[section][key]
    except KeyError:
        return default


def _load_pc_id() -> str:
    if PC_ID_FILE.exists():
        return PC_ID_FILE.read_text().strip()
    new_id = str(uuid.uuid4())
    PC_ID_FILE.write_text(new_id)
    return new_id


# Vía de escape explícita para aceptar SERVER_URL en http:// hacia un host
# que no es localhost — ver _validar_server_url() más abajo. Default false:
# hay que fijarlo a propósito, no es el comportamiento por omisión.
PERMITIR_HTTP_INSEGURO: bool = _get(
    "servidor", "permitir_http_inseguro", "BIBLIOTECA_PERMITIR_HTTP", "false"
).strip().lower() in ("1", "true", "si", "sí")


def _validar_server_url(url: str) -> str:
    """PII de estudiantes y telemetría de hardware viajan en cada request a
    SERVER_URL; sin TLS, cualquiera en la misma LAN puede leerlas/alterarlas
    (incluyendo KIOSK_API_KEY, enviada en texto plano como header). Solo se
    permite http:// hacia localhost — para cualquier otro host hace falta
    https:// (ver docs/desarrollo/despliegue.md, sección TLS) o asumir el
    riesgo a propósito con [servidor] permitir_http_inseguro = true."""
    host = urlparse(url).hostname
    if urlparse(url).scheme == "http" and host not in ("localhost", "127.0.0.1") and not PERMITIR_HTTP_INSEGURO:
        raise RuntimeError(
            f"SERVER_URL ({url}) usa http:// hacia un host que no es localhost — "
            "la PII de estudiantes y KIOSK_API_KEY viajarían en texto plano por la "
            "red. Configurá https:// (ver docs/desarrollo/despliegue.md, sección "
            "TLS), usá localhost/127.0.0.1 solo para desarrollo, o si aceptás el "
            "riesgo en una LAN cerrada y confiable, fijá "
            "[servidor] permitir_http_inseguro = true en config.ini "
            "(o BIBLIOTECA_PERMITIR_HTTP=1) explícitamente."
        )
    return url


SERVER_URL: str = _validar_server_url(
    _get("servidor", "url", "BIBLIOTECA_SERVER_URL", "http://localhost:8000")
)
KIOSK_API_KEY: str = _get("servidor", "kiosk_key", "BIBLIOTECA_KIOSK_KEY", "")
ADMIN_PIN_HASH: str = _get("admin", "pin_hash", "BIBLIOTECA_ADMIN_PIN_HASH", "")

# Certificado de la CA interna (PEM) que firmó el certificado del servidor,
# para validar la conexión HTTPS cuando el servidor no tiene un certificado
# de una CA pública (caso normal en la LAN del laboratorio, sin dominio
# público — ver servidor/scripts/generar_ca.sh). Relativo a DATA_DIR si no
# es una ruta absoluta. Si queda vacío, se usa el almacén de CAs del sistema
# operativo (correcto si el servidor sí tiene un certificado público real).
_CA_CERT_RAW: str = _get("servidor", "ca_cert", "BIBLIOTECA_CA_CERT", "")
CA_CERT_PATH: str = ""
if _CA_CERT_RAW:
    _ca_path = Path(_CA_CERT_RAW)
    if not _ca_path.is_absolute():
        _ca_path = DATA_DIR / _ca_path
    if not _ca_path.exists():
        raise RuntimeError(
            f"[servidor] ca_cert ({_CA_CERT_RAW}) está configurado pero el archivo "
            f"no existe en {_ca_path}. Copiá el ca.pem generado por "
            f"servidor/scripts/generar_ca.sh, o dejá el campo vacío si el servidor "
            f"usa un certificado de una CA pública reconocida."
        )
    CA_CERT_PATH = str(_ca_path)

# Parámetro `verify` listo para pasarle a requests.*: la ruta a la CA interna
# si está configurada, o True (almacén de CAs del sistema) en caso contrario.
VERIFY_TLS = CA_CERT_PATH or True
PC_ID: str = _load_pc_id()
PC_NOMBRE: str = _get("pc", "nombre", "BIBLIOTECA_PC_NOMBRE", "PC-00")
SYNC_INTERVAL: int = int(_get("sync", "intervalo_segundos", default="30"))

DURACION_SESION_MINUTOS: int = int(_get("sesion", "duracion_minutos", default="60"))
DURACION_SESION_MS: int = DURACION_SESION_MINUTOS * 60 * 1000

HARDWARE_INTERVAL_SEGUNDOS: int = int(_get("hardware", "intervalo_segundos", default="300"))

# Deshabilita atajos de GNOME (tecla Super, Alt+Tab, etc.) que permiten
# salir del kiosko sin cerrar sesión — ver core/bloqueo_escritorio.py.
BLOQUEAR_ATAJOS_ESCRITORIO: bool = _get(
    "escritorio", "bloquear_atajos", "BIBLIOTECA_BLOQUEAR_ATAJOS", "true"
).strip().lower() not in ("0", "false", "no")

# Grupo del sistema cuyos miembros (el usuario de la sesión gráfica del
# kiosko) pueden conectarse al socket del servicio, además del propio
# usuario del servicio. Si el grupo no existe (desarrollo con un único
# usuario), solo se aceptan conexiones del mismo usuario que corre el
# servicio. Ver servicio/servidor.py.
GRUPO_UI: str = _get("servicio", "grupo_ui", "BIBLIOTECA_GRUPO_UI", "kiosko-ui")
