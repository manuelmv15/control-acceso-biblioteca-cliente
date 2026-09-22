"""Hashing del PIN de administrador del kiosko.

Antes se guardaba `hashlib.sha256(pin.encode()).hexdigest()` — SHA-256 sin
sal ni costo computacional, trivial de romper offline si `config.ini` se
filtra (backup, USB, otra cuenta local antes del `chmod`), especialmente
porque el PIN suele ser corto/numérico.

Este módulo porta el mismo esquema que ya usa el servidor para las
contraseñas de admin (ver `servidor/routers/auth.py::generar_hash` /
`verificar_password`): PBKDF2-HMAC-SHA256 con sal aleatoria de 16 bytes y
formato `pbkdf2_sha256$<iteraciones>$<salt_hex>$<hash_hex>`.
"""
import hashlib
import hmac
import secrets

PBKDF2_ITERACIONES = 600_000  # misma recomendación OWASP (2023+) que usa el servidor
LONGITUD_MINIMA_PIN = 4


def generar_hash_pin(pin: str) -> str:
    """Genera un hash `pbkdf2_sha256$<iteraciones>$<salt_hex>$<hash_hex>` para
    guardar en `config.ini` ([admin] pin_hash)."""
    salt = secrets.token_bytes(16)
    derivado = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, PBKDF2_ITERACIONES)
    return f"pbkdf2_sha256${PBKDF2_ITERACIONES}${salt.hex()}${derivado.hex()}"


def _parsear_hash(hash_almacenado: str) -> tuple[int, bytes, str]:
    """Descompone un hash `pbkdf2_sha256$<iteraciones>$<salt_hex>$<hash_hex>`. Lanza
    ValueError si el formato no es válido (algoritmo distinto, número de campos
    incorrecto, hex inválido, etc.)."""
    algoritmo, iteraciones_s, salt_hex, hash_hex = hash_almacenado.split("$")
    if algoritmo != "pbkdf2_sha256":
        raise ValueError(f"algoritmo desconocido: {algoritmo}")
    return int(iteraciones_s), bytes.fromhex(salt_hex), hash_hex


def verificar_pin(pin: str, hash_almacenado: str) -> bool:
    """Verifica `pin` contra un hash generado con `generar_hash_pin()`. Nunca
    compara PINs en texto plano, y usa `hmac.compare_digest` para evitar
    timing attacks."""
    try:
        iteraciones, salt, hash_hex = _parsear_hash(hash_almacenado)
    except (ValueError, AttributeError):
        return False
    derivado = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iteraciones)
    return hmac.compare_digest(derivado.hex(), hash_hex)


def es_hash_legacy(hash_almacenado: str) -> bool:
    """True si `hash_almacenado` es del formato viejo (SHA-256 plano sin sal)
    en vez de `pbkdf2_sha256$...` — indica que hace
    falta reconfigurar el PIN (ejecutar `setup.py` de nuevo) para migrar al
    hash fuerte. Un `config.ini` vacío (sin PIN configurado) no es legacy,
    solo está sin configurar."""
    if not hash_almacenado:
        return False
    return not hash_almacenado.startswith("pbkdf2_sha256$")
