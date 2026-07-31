import os
import uuid
import configparser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

TZ_SV = ZoneInfo("America/El_Salvador")


def now_sv() -> datetime:
    return datetime.now(TZ_SV)

BASE_DIR = Path(__file__).parent.parent
CONFIG_FILE = BASE_DIR / "config.ini"
PC_ID_FILE = BASE_DIR / ".pc_id"

_config = configparser.ConfigParser()
_config.read(CONFIG_FILE, encoding="utf-8")


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


def _validar_server_url(url: str) -> str:
    """PII de estudiantes y telemetría de hardware viajan en cada request a
    SERVER_URL; sin TLS, cualquiera en la misma LAN puede leerlas/alterarlas.
    Solo se permite http:// hacia localhost (desarrollo)."""
    host = urlparse(url).hostname
    if urlparse(url).scheme == "http" and host not in ("localhost", "127.0.0.1"):
        raise RuntimeError(
            f"SERVER_URL ({url}) usa http:// hacia un host que no es localhost — "
            f"la PII de estudiantes y la telemetría de hardware viajarían en texto "
            f"plano por la red. Configura 'url' en config.ini (o BIBLIOTECA_SERVER_URL) "
            f"con https://, o usa localhost/127.0.0.1 solo para desarrollo."
        )
    return url


SERVER_URL: str = _validar_server_url(
    _get("servidor", "url", "BIBLIOTECA_SERVER_URL", "http://localhost:8000")
)
KIOSK_API_KEY: str = _get("servidor", "kiosk_key", "BIBLIOTECA_KIOSK_KEY", "")
ADMIN_PIN_HASH: str = _get("admin", "pin_hash", "BIBLIOTECA_ADMIN_PIN_HASH", "")
PC_ID: str = _load_pc_id()
PC_NOMBRE: str = _get("pc", "nombre", "BIBLIOTECA_PC_NOMBRE", "PC-00")
SYNC_INTERVAL: int = int(_get("sync", "intervalo_segundos", default="30"))

DURACION_SESION_MINUTOS: int = int(_get("sesion", "duracion_minutos", default="60"))
DURACION_SESION_MS: int = DURACION_SESION_MINUTOS * 60 * 1000

HARDWARE_INTERVAL_SEGUNDOS: int = int(_get("hardware", "intervalo_segundos", default="300"))
