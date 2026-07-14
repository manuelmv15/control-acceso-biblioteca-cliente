from db.connection import get_connection


def _migrar_carnet_nullable(conn):
    """sesiones_pendientes.carnet era NOT NULL; el modo Invitado necesita
    guardar sesiones sin carnet. SQLite no soporta ALTER COLUMN, así que
    se reconstruye la tabla solo si todavía tiene la constraint vieja."""
    cols = conn.execute("PRAGMA table_info(sesiones_pendientes)").fetchall()
    if not cols:
        return
    carnet_col = next((c for c in cols if c["name"] == "carnet"), None)
    if carnet_col is None or carnet_col["notnull"] == 0:
        return
    conn.executescript("""
        ALTER TABLE sesiones_pendientes RENAME TO sesiones_pendientes_old;
        CREATE TABLE sesiones_pendientes (
            id TEXT PRIMARY KEY,
            pc_id TEXT NOT NULL,
            carnet TEXT,
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT,
            fecha TEXT NOT NULL,
            sincronizado INTEGER DEFAULT 0,
            timestamp_sync TEXT
        );
        INSERT INTO sesiones_pendientes SELECT * FROM sesiones_pendientes_old;
        DROP TABLE sesiones_pendientes_old;
    """)
    conn.commit()


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sesiones_pendientes (
            id TEXT PRIMARY KEY,
            pc_id TEXT NOT NULL,
            carnet TEXT,
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

        CREATE TABLE IF NOT EXISTS hardware_local (
            pc_id TEXT PRIMARY KEY,
            horas_acumuladas REAL NOT NULL DEFAULT 0,
            ultimo_heartbeat TEXT,
            ultimo_mantenimiento_conocido TEXT
        );
    """)
    conn.commit()

    _migrar_carnet_nullable(conn)
    conn.close()
