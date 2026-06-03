import os
import uuid
import configparser
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ_SV = ZoneInfo("America/El_Salvador")


def now_sv() -> datetime:
    return datetime.now(TZ_SV)

BASE_DIR = Path(__file__).parent
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
PC_ID: str = _load_pc_id()
PC_NOMBRE: str = _get("pc", "nombre", "BIBLIOTECA_PC_NOMBRE", "PC-00")
SYNC_INTERVAL: int = int(_get("sync", "intervalo_segundos", default="30"))
