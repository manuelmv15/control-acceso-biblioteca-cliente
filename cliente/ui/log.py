"""Log de la UI.

Por defecto solo va a stderr (el journal de la sesión gráfica): la UI corre
con la cuenta que usan todos los estudiantes, así que un archivo de log
propio quedaría legible para el siguiente. Por eso los eventos con carnet
(login, inicio y cierre de sesión) los registra el servicio en su propio
log, y acá no se escriben carnets. `BIBLIOTECA_UI_LOG` activa además un
archivo, para desarrollo.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

log = logging.getLogger("ui")
log.setLevel(logging.INFO)
log.propagate = False
if not log.handlers:
    _formatter = logging.Formatter("%(asctime)s [UI] %(message)s")
    _handlers: list[logging.Handler] = [logging.StreamHandler()]
    _archivo = os.environ.get("BIBLIOTECA_UI_LOG")
    if _archivo:
        _handlers.append(RotatingFileHandler(_archivo, maxBytes=1_000_000, backupCount=3, encoding="utf-8"))
    for _handler in _handlers:
        _handler.setFormatter(_formatter)
        log.addHandler(_handler)
    if _archivo:
        os.chmod(_archivo, 0o600)
