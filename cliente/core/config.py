import os
import uuid
import configparser
from datetime import datetime
from pathlib import Path
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


SERVER_URL: str = _get("servidor", "url", "BIBLIOTECA_SERVER_URL", "http://localhost:8000")
KIOSK_API_KEY: str = _get("servidor", "kiosk_key", "BIBLIOTECA_KIOSK_KEY", "")
ADMIN_PIN_HASH: str = _get("admin", "pin_hash", "BIBLIOTECA_ADMIN_PIN_HASH", "")
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
