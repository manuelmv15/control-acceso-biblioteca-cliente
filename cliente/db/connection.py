import os
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "biblioteca_local.db"


def _restringir_permisos():
    """biblioteca_local.db guarda PII de estudiantes (nombre, carrera,
    facultad, año de nacimiento, sexo) sin cifrar; restringe el acceso al
    dueño del proceso para que otras cuentas locales no puedan leerla.
    Incluye -wal/-shm (modo WAL): también pueden contener filas recientes."""
    for sufijo in ("", "-wal", "-shm"):
        p = DB_PATH.with_name(DB_PATH.name + sufijo)
        if p.exists():
            os.chmod(p, 0o600)


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _restringir_permisos()
    return conn
