from db.connection import get_connection


def obtener_estado_local(pc_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM hardware_local WHERE pc_id = ?", (pc_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def guardar_estado_local(pc_id: str, horas_acumuladas: float, ultimo_heartbeat: str,
                          ultimo_mantenimiento_conocido: str | None):
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO hardware_local
            (pc_id, horas_acumuladas, ultimo_heartbeat, ultimo_mantenimiento_conocido)
        VALUES (?, ?, ?, ?)
    """, (pc_id, horas_acumuladas, ultimo_heartbeat, ultimo_mantenimiento_conocido))
    conn.commit()
    conn.close()
