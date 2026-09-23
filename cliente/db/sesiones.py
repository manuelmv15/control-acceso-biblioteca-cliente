from db.connection import get_connection

# Valores de sesiones_pendientes.sincronizado. RECHAZADA marca una sesión que
# el servidor rechazó por datos inválidos (422): reenviarla daría siempre el
# mismo error, así que sale de la cola en vez de bloquear a las demás. Se
# conserva en la base local para poder revisarla.
PENDIENTE = 0
SINCRONIZADA = 1
RECHAZADA = -1


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


def obtener_pendientes(limite: int | None = None) -> list:
    """Sesiones cerradas que faltan por enviar, de la más antigua a la más
    reciente. `limite` acota cuántas se devuelven, para enviarlas por lotes
    que el servidor acepte."""
    sql = "SELECT * FROM sesiones_pendientes WHERE sincronizado = ? AND hora_fin IS NOT NULL ORDER BY hora_fin, id"
    params: list = [PENDIENTE]
    if limite is not None:
        sql += " LIMIT ?"
        params.append(limite)
    conn = get_connection()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _marcar(ids: list, estado: int):
    if not ids:
        return
    from core.tiempo import now_sv
    ahora = now_sv().isoformat()
    conn = get_connection()
    placeholders = ",".join("?" * len(ids))
    conn.execute(
        f"UPDATE sesiones_pendientes SET sincronizado=?, timestamp_sync=? WHERE id IN ({placeholders})",
        [estado, ahora] + ids
    )
    conn.commit()
    conn.close()


def marcar_sincronizado(ids: list):
    _marcar(ids, SINCRONIZADA)


def marcar_rechazada(ids: list):
    _marcar(ids, RECHAZADA)
