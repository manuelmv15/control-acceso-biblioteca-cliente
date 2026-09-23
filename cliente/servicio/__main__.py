"""Punto de entrada del servicio: `python -m servicio` desde cliente/."""
import logging
import os
import signal
from logging.handlers import RotatingFileHandler
from types import SimpleNamespace

from core.config import (
    ADMIN_PIN_HASH,
    BLOQUEAR_ATAJOS_ESCRITORIO,
    DURACION_SESION_MS,
    GRUPO_UI,
    PC_ID,
)
from core.ipc import ruta_socket
from core.rutas import DATA_DIR
from db import init_db
from hardware.agent import iniciar as iniciar_hardware_agent
from network.client import hay_conexion
from network.estudiantes import actualizar_estudiante, obtener_estudiante, registrar_estudiante
from sync import forzar_sync
from sync import iniciar as iniciar_sync

from servicio.operaciones import ServicioKiosko
from servicio.servidor import ServidorKiosko

LOG_FILE = DATA_DIR / "servicio.log"
log = logging.getLogger("servicio")


def _configurar_log():
    log.setLevel(logging.INFO)
    log.propagate = False
    formatter = logging.Formatter("%(asctime)s [SERVICIO] %(message)s")
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    for handler in (file_handler, logging.StreamHandler()):
        handler.setFormatter(formatter)
        log.addHandler(handler)
    os.chmod(LOG_FILE, 0o600)


def _terminar(signum, _frame):
    raise SystemExit(128 + signum)


def main():
    _configurar_log()
    init_db()

    servicio = ServicioKiosko(
        pc_id=PC_ID,
        duracion_sesion_ms=DURACION_SESION_MS,
        admin_pin_hash=ADMIN_PIN_HASH,
        bloquear_atajos=BLOQUEAR_ATAJOS_ESCRITORIO,
        red=SimpleNamespace(
            hay_conexion=hay_conexion,
            obtener_estudiante=obtener_estudiante,
            registrar_estudiante=registrar_estudiante,
            actualizar_estudiante=actualizar_estudiante,
        ),
        forzar_sync=forzar_sync,
    )
    servidor = ServidorKiosko(ruta_socket(), servicio, GRUPO_UI)
    log.info("Servicio escuchando en %s", servidor.ruta)

    iniciar_sync()
    iniciar_hardware_agent()

    # systemd detiene el servicio con SIGTERM (apagado, reinicio, stop):
    # se convierte en SystemExit para pasar por el finally y cerrar la
    # sesión abierta con su hora real de fin.
    signal.signal(signal.SIGTERM, _terminar)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servicio.cerrar_sesion()
        servidor.server_close()
        log.info("Servicio detenido")


if __name__ == "__main__":
    main()
