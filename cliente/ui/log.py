import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE = Path(__file__).parent.parent / "ui.log"
log = logging.getLogger("ui")
log.setLevel(logging.INFO)
log.propagate = False
if not log.handlers:
    _formatter = logging.Formatter("%(asctime)s [UI] %(message)s")
    _file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    for _handler in (_file_handler, logging.StreamHandler()):
        _handler.setFormatter(_formatter)
        log.addHandler(_handler)
    if LOG_FILE.exists():
        os.chmod(LOG_FILE, 0o600)
