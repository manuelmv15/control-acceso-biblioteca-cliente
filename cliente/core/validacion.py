import re

# Formato oficial de carnet: dos letras seguidas de cinco números (ej. AB12345).
CARNET_PATRON = re.compile(r"^[A-Z]{2}\d{5}$")
CARNET_PLACEHOLDER = "AA12345"


def normalizar_carnet(valor: str) -> str:
    """Recorta espacios y pasa a mayúsculas para comparar/guardar de forma consistente."""
    return (valor or "").strip().upper()


def carnet_valido(valor: str) -> bool:
    """Un carnet válido tiene el formato AA##### (dos letras y cinco números)."""
    return bool(CARNET_PATRON.match(normalizar_carnet(valor)))
