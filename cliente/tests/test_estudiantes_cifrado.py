"""Tests del cifrado en reposo de estudiantes_cache (db/cifrado.py,
integrado en db/estudiantes.py) — corrección de B6 de la auditoría.

Cubren: que los campos PII queden cifrados en la fila cruda de SQLite (no
solo "descifrables", sino efectivamente distintos del texto plano); que el
roundtrip guardar→buscar devuelva los valores originales; que `carnet` (la
clave primaria, usada en WHERE) se guarde en texto plano a propósito; y que
un valor legacy sin cifrar (guardado por una versión anterior del código)
se siga leyendo tal cual en vez de romper."""

import sqlite3

from db.cifrado import cifrar_campo, descifrar_campo
from db.connection import get_connection
from db.estudiantes import buscar_estudiante_cache, guardar_estudiante_cache


def _estudiante(carnet="AB12345"):
    return {
        "carnet": carnet,
        "nombre": "Ana Pérez",
        "carrera": "Ingeniería",
        "facultad": "Facultad de Ingeniería",
        "fecha_nacimiento": "2000-01-01",
        "sexo": "F",
    }


def test_roundtrip_cifrar_descifrar_campo(db_temporal):
    original = "Ana Pérez"
    token = cifrar_campo(original)
    assert token != original
    assert descifrar_campo(token) == original


def test_descifrar_campo_none_devuelve_none(db_temporal):
    assert cifrar_campo(None) is None
    assert descifrar_campo(None) is None


def test_descifrar_campo_valor_legacy_sin_cifrar_se_devuelve_tal_cual(db_temporal):
    """Un valor guardado antes de esta corrección (texto plano, no un token
    Fernet) no debe hacer fallar el descifrado — se lee como está."""
    assert descifrar_campo("Ana Pérez") == "Ana Pérez"


def test_guardar_y_buscar_devuelve_los_valores_originales(db_temporal):
    est = _estudiante()
    guardar_estudiante_cache(est)

    encontrado = buscar_estudiante_cache(est["carnet"])

    assert encontrado is not None
    assert encontrado["nombre"] == est["nombre"]
    assert encontrado["carrera"] == est["carrera"]
    assert encontrado["facultad"] == est["facultad"]
    assert encontrado["fecha_nacimiento"] == est["fecha_nacimiento"]
    assert encontrado["sexo"] == est["sexo"]


def test_fila_cruda_en_sqlite_no_contiene_pii_en_texto_plano(db_temporal):
    """La comprobación real de B6: leyendo la tabla sin pasar por
    db/estudiantes.py (como haría quien abra el .db con cualquier lector de
    SQLite), el nombre no debe aparecer en texto plano."""
    est = _estudiante()
    guardar_estudiante_cache(est)

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    fila = conn.execute(
        "SELECT * FROM estudiantes_cache WHERE carnet = ?", (est["carnet"],)
    ).fetchone()
    conn.close()

    assert fila["nombre"] != est["nombre"]
    assert fila["carrera"] != est["carrera"]
    assert est["nombre"] not in fila["nombre"]


def test_carnet_se_guarda_en_texto_plano(db_temporal):
    """carnet es la clave primaria y se busca con WHERE carnet = ?; Fernet
    no es determinístico, así que cifrarlo rompería esa búsqueda — se deja
    sin cifrar a propósito."""
    est = _estudiante()
    guardar_estudiante_cache(est)

    conn = get_connection()
    fila = conn.execute(
        "SELECT carnet FROM estudiantes_cache WHERE carnet = ?", (est["carnet"],)
    ).fetchone()
    conn.close()

    assert fila["carnet"] == est["carnet"]
