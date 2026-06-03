import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "biblioteca_local.db"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sesiones_pendientes (
            id TEXT PRIMARY KEY,
            pc_id TEXT NOT NULL,
            carnet TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT,
            fecha TEXT NOT NULL,
            sincronizado INTEGER DEFAULT 0,
            timestamp_sync TEXT
        );

        CREATE TABLE IF NOT EXISTS estudiantes_cache (
            carnet TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            carrera TEXT,
            facultad TEXT,
            departamento TEXT,
            fecha_nacimiento TEXT,
            sexo TEXT
        );
    """)
    conn.commit()
    conn.close()


def guardar_sesion(sesion: dict):
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO sesiones_pendientes
            (id, pc_id, carnet, hora_inicio, hora_fin, fecha, sincronizado)
        VALUES (:id, :pc_id, :carnet, :hora_inicio, :hora_fin, :fecha, 0)
    """, sesion)
    conn.commit()
    conn.close()


def actualizar_hora_fin(sesion_id: str, hora_fin: str):
    conn = get_connection()
    conn.execute(
        "UPDATE sesiones_pendientes SET hora_fin = ? WHERE id = ?",
        (hora_fin, sesion_id)
    )
    conn.commit()
    conn.close()


def obtener_pendientes() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sesiones_pendientes WHERE sincronizado = 0 AND hora_fin IS NOT NULL"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def marcar_sincronizado(ids: list):
    if not ids:
        return
    from config import now_sv
    ahora = now_sv().isoformat()
    conn = get_connection()
    placeholders = ",".join("?" * len(ids))
    conn.execute(
        f"UPDATE sesiones_pendientes SET sincronizado=1, timestamp_sync=? WHERE id IN ({placeholders})",
        [ahora] + ids
    )
    conn.commit()
    conn.close()


def guardar_estudiante_cache(est: dict):
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO estudiantes_cache
            (carnet, nombre, carrera, facultad, departamento, fecha_nacimiento, sexo)
        VALUES (:carnet, :nombre, :carrera, :facultad, :departamento, :fecha_nacimiento, :sexo)
    """, est)
    conn.commit()
    conn.close()


def buscar_estudiante_cache(carnet: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM estudiantes_cache WHERE carnet = ?", (carnet,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
