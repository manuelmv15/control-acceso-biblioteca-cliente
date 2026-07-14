import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "biblioteca_local.db"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn
