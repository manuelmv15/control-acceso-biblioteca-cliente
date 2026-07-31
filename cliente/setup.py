"""Script de configuración inicial — ejecutar una vez por PC hija."""
import configparser
import getpass
import hashlib
import uuid
import sys
import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.ini"
PC_ID_FILE = BASE_DIR / ".pc_id"


def preguntar(prompt: str, default: str = "") -> str:
    if default:
        respuesta = input(f"{prompt} [{default}]: ").strip()
        return respuesta or default
    respuesta = input(f"{prompt}: ").strip()
    return respuesta


def preguntar_server_url() -> str:
    """PII de estudiantes y telemetría de hardware viajan en cada request a
    esta URL; sin TLS, cualquiera en la misma LAN puede leerlas/alterarlas.
    Solo se acepta http:// hacia localhost (desarrollo)."""
    while True:
        url = preguntar("URL del servidor", "http://localhost:8000")
        host = urlparse(url).hostname
        if urlparse(url).scheme == "http" and host not in ("localhost", "127.0.0.1"):
            print(
                f"  ⚠️  '{url}' usa http:// hacia un host que no es localhost: la PII de "
                f"estudiantes viajaría en texto plano por la red. Usa https:// (o "
                f"localhost/127.0.0.1 solo para desarrollo)."
            )
            continue
        return url


def generar_pc_id() -> str:
    if PC_ID_FILE.exists():
        pc_id = PC_ID_FILE.read_text().strip()
        print(f"  PC_ID existente: {pc_id}")
        return pc_id
    pc_id = str(uuid.uuid4())
    PC_ID_FILE.write_text(pc_id)
    print(f"  PC_ID generado: {pc_id}")
    return pc_id


def instalar_autostart_linux(app_path: str):
    desktop_dir = Path.home() / ".config" / "autostart"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    desktop_file = desktop_dir / "biblioteca-kiosko.desktop"
    python = sys.executable
    desktop_file.write_text(f"""[Desktop Entry]
Type=Application
Name=Biblioteca Kiosko
Exec={python} {app_path}
X-GNOME-Autostart-enabled=true
NoDisplay=false
Hidden=false
""")
    print(f"  Autostart creado: {desktop_file}")


def main():
    print("=== Configuración de PC Biblioteca ===\n")

    nombre = preguntar("Nombre de esta PC (ej: PC-01)", "PC-01")
    server_url = preguntar_server_url()
    kiosk_key = preguntar("API key de kiosko (la misma KIOSK_API_KEY del servidor)", "")
    admin_pin = getpass.getpass("PIN de administrador para 'Salir (admin)' del kiosko (no se muestra en pantalla): ").strip()
    admin_pin_hash = hashlib.sha256(admin_pin.encode()).hexdigest() if admin_pin else ""

    config = configparser.ConfigParser()
    config["pc"] = {"nombre": nombre}
    config["servidor"] = {"url": server_url, "kiosk_key": kiosk_key}
    config["sync"] = {"intervalo_segundos": "30"}
    config["admin"] = {"pin_hash": admin_pin_hash}

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        config.write(f)
    print(f"\nConfig guardada: {CONFIG_FILE}")

    pc_id = generar_pc_id()

    # Crear DB local
    sys.path.insert(0, str(BASE_DIR))
    from db import init_db
    init_db()
    print("  Base de datos local inicializada")

    # Autostart
    instalar = preguntar("\n¿Instalar autostart? (s/n)", "s").lower()
    if instalar == "s":
        app_main = str(BASE_DIR / "main.py")
        instalar_autostart_linux(app_main)

    print(f"\n=== Configuración completa ===")
    print(f"  PC: {nombre}")
    print(f"  ID: {pc_id}")
    print(f"  Servidor: {server_url}")
    if not kiosk_key:
        print("  ⚠️  Sin API key de kiosko: el login/registro de estudiantes fallará (401) hasta que la configures en config.ini")
    if not admin_pin_hash:
        print("  ⚠️  Sin PIN de administrador: 'Salir (admin)' quedará bloqueado hasta que configures [admin] pin_hash en config.ini")
    print(f"\nEjecutar: python main.py")


if __name__ == "__main__":
    main()
