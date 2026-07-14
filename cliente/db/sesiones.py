from db.connection import get_connection


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
    from core.config import now_sv
    ahora = now_sv().isoformat()
    conn = get_connection()
    placeholders = ",".join("?" * len(ids))
    conn.execute(
        f"UPDATE sesiones_pendientes SET sincronizado=1, timestamp_sync=? WHERE id IN ({placeholders})",
        [ahora] + ids
    )
    conn.commit()
    conn.close()
