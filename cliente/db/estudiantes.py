from db.connection import get_connection


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
