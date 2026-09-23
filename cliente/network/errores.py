"""Errores de las llamadas al servidor que quien llama tiene que distinguir
de un simple «no se pudo». Van aparte de network/estudiantes.py para poder
importarlos sin cargar core.config (servicio/ y los tests los usan)."""


class ServidorNoDisponible(Exception):
    """No hubo una respuesta que permita saber si el estudiante existe: sin
    red, timeout, 429 (límite de consultas) o error del servidor."""


class CarnetYaRegistrado(Exception):
    """El servidor ya tiene una ficha con ese carnet (409)."""
