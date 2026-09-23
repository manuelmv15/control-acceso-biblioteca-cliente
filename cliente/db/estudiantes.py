from db.cifrado import cifrar_estudiante, descifrar_estudiante
from db.connection import get_connection


def guardar_estudiante_cache(est: dict, sincronizado: int = 1, pendiente_modo: str | None = None):
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO estudiantes_cache
            (carnet, nombre, carrera, facultad, fecha_nacimiento, sexo, sincronizado, pendiente_modo)
        VALUES (:carnet, :nombre, :carrera, :facultad, :fecha_nacimiento, :sexo, :sincronizado, :pendiente_modo)
    """, {**cifrar_estudiante(est), "sincronizado": sincronizado, "pendiente_modo": pendiente_modo})
    conn.commit()
    conn.close()


def buscar_estudiante_cache(carnet: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM estudiantes_cache WHERE carnet = ?", (carnet,)
    ).fetchone()
    conn.close()
    return descifrar_estudiante(dict(row)) if row else None


def obtener_estudiantes_pendientes() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM estudiantes_cache WHERE sincronizado = 0"
    ).fetchall()
    conn.close()
    return [descifrar_estudiante(dict(r)) for r in rows]


def marcar_estudiante_sincronizado(carnet: str):
    conn = get_connection()
    conn.execute(
        "UPDATE estudiantes_cache SET sincronizado = 1, pendiente_modo = NULL WHERE carnet = ?",
        (carnet,)
    )
    conn.commit()
    conn.close()


CAMPOS_ESTUDIANTE = ("carnet", "nombre", "carrera", "facultad", "fecha_nacimiento", "sexo")


def guardar_estudiante_del_servidor(carnet: str, datos: dict) -> dict:
    """Cachea la ficha tal como la tiene el servidor, marcada como
    sincronizada, y descarta lo que hubiera en local para ese carnet."""
    est = {campo: datos.get(campo) or "" for campo in CAMPOS_ESTUDIANTE}
    est["carnet"] = datos.get("carnet") or carnet
    guardar_estudiante_cache(est)
    return est
