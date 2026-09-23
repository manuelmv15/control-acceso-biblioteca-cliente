import os
import sqlite3

from core.rutas import DATA_DIR

DB_PATH = DATA_DIR / "biblioteca_local.db"


def _restringir_permisos():
    """biblioteca_local.db guarda PII de estudiantes (nombre, carrera,
    facultad, año de nacimiento, sexo); los campos PII están cifrados en
    reposo desde `db/cifrado.py`, pero esto restringe además el acceso al
    dueño del proceso para que otras cuentas locales no puedan ni siquiera
    leer el archivo cifrado. Incluye -wal/-shm (modo WAL): también pueden
    contener filas recientes."""
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
