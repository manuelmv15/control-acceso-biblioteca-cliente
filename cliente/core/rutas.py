"""Rutas del código y de los datos persistentes del kiosko.

Se separan a propósito: en producción el código se instala de solo lectura
(propiedad de root) y los datos —config.ini con la API key de la PC,
db_key.bin, la base local, .pc_id y los logs del servicio— viven en un
directorio que solo puede leer el usuario del servicio en segundo plano
(ver servicio/), nunca el usuario de la sesión gráfica que usa el
estudiante. `BIBLIOTECA_DATA_DIR` fija ese directorio; si no se define, los
datos quedan junto al código, como en desarrollo.

Sin efectos secundarios al importar (no lee config.ini ni crea archivos):
lo importan tanto el servicio como la UI y los tests.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("BIBLIOTECA_DATA_DIR") or BASE_DIR)
