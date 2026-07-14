import platform
import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

DISCOS_CANDIDATOS = ["/dev/sda", "/dev/nvme0n1", "/dev/vda"]


def identificacion() -> dict:
    """Identificador legible adicional. La clave primaria real sigue siendo
    PC_ID (.pc_id), ya usada como FK en el servidor — esto es solo para
    inventario/lectura humana."""
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = None
    try:
        mac_int = uuid.getnode()
        mac = ":".join(f"{(mac_int >> despl) & 0xff:02x}" for despl in range(40, -8, -8))
    except Exception:
        mac = None
    return {"hostname": hostname, "mac": mac}


def specs() -> dict:
    cpu = platform.processor() or None
    if not cpu and psutil:
        nucleos = psutil.cpu_count(logical=False)
        cpu = f"{nucleos} núcleos físicos" if nucleos else None

    ram_total_mb = None
    almacenamiento_total_gb = None
    if psutil:
        try:
            ram_total_mb = round(psutil.virtual_memory().total / 1024**2)
        except Exception:
            pass
        try:
            almacenamiento_total_gb = round(psutil.disk_usage("/").total / 1024**3)
        except Exception:
            pass

    return {
        "cpu": cpu,
        "ram_total_mb": ram_total_mb,
        "almacenamiento_total_gb": almacenamiento_total_gb,
        "sistema_operativo": platform.platform(),
    }


def salud() -> dict:
    """Métricas opcionales — best-effort, nunca lanzan. None si no se pueden leer."""
    temperatura_cpu_c = None
    if psutil and hasattr(psutil, "sensors_temperatures"):
        try:
            lecturas = psutil.sensors_temperatures()
            valores = [t.current for sensores in lecturas.values() for t in sensores if t.current]
            if valores:
                temperatura_cpu_c = round(sum(valores) / len(valores), 1)
        except Exception:
            pass

    disco_smart_ok = None
    if shutil.which("smartctl"):
        for disco in DISCOS_CANDIDATOS:
            if not Path(disco).exists():
                continue
            try:
                r = subprocess.run(
                    ["smartctl", "-H", disco],
                    capture_output=True, text=True, timeout=5,
                )
                salida = r.stdout.lower()
                if "passed" in salida:
                    disco_smart_ok = True
                elif "failed" in salida:
                    disco_smart_ok = False
            except Exception:
                pass
            break

    return {"temperatura_cpu_c": temperatura_cpu_c, "disco_smart_ok": disco_smart_ok}


def uptime_sistema_segundos() -> float:
    """Uptime real del SO actual — solo se usa para sembrar el acumulador
    de horas la primera vez que corre el agente en esta PC."""
    if psutil:
        try:
            return max(0.0, time.time() - psutil.boot_time())
        except Exception:
            pass
    return 0.0
