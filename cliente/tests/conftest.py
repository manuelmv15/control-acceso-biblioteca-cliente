import sys
from pathlib import Path

import pytest

# Los módulos de la app se importan como paquetes de nivel superior
# (`from db.sesiones import ...`, no `from cliente.db...`), así que hace
# falta el directorio `cliente/` en sys.path — igual que cuando corre
# main.py con `cliente/` como cwd.
CLIENTE_DIR = Path(__file__).resolve().parents[1]
if str(CLIENTE_DIR) not in sys.path:
    sys.path.insert(0, str(CLIENTE_DIR))

from db import connection as db_connection  # noqa: E402
from db.schema import init_db  # noqa: E402


@pytest.fixture
def db_temporal(tmp_path, monkeypatch):
    """Aísla cada test en una base SQLite nueva bajo tmp_path en vez de
    tocar `cliente/biblioteca_local.db` (la base real del kiosko). db/*.py
    llama siempre a `db.connection.get_connection()`, que abre `DB_PATH` —
    reemplazar ese atributo del módulo alcanza para redirigir todas las
    funciones de db/ sin tocar su código."""
    ruta = tmp_path / "biblioteca_local_test.db"
    monkeypatch.setattr(db_connection, "DB_PATH", ruta)
    init_db()
    return ruta
