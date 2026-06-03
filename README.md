# Biblioteca Horas Sociales — Cliente (Kiosko)

Cliente de escritorio para el sistema de control de horas sociales de biblioteca universitaria. Corre en cada PC hija; se comunica con el servidor central vía HTTP.

**Requiere:** Python 3.10+, PyQt6

---

## Instalación

### Opción A — Entorno virtual (recomendado)

Aisla dependencias del sistema. No ensucia el Python global.

```bash
# 1. Clonar repositorio
git clone <url-del-repo>
cd bliblioteca-horas-sociales_cliente/cliente

# 2. Crear entorno virtual
python3 -m venv venv

# 3. Activar
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Configurar la PC
python setup.py
```

Para ejecutar después:

```bash
source venv/bin/activate   # (Linux) — omitir si ya activo
python main.py
```

---

### Opción B — Instalación directa en la máquina

Sin entorno virtual. Las dependencias van al Python del sistema.

```bash
git clone <url-del-repo>
cd bliblioteca-horas-sociales_cliente/cliente

pip install -r requirements.txt   # puede requerir pip3 o --user en Linux
python setup.py
python main.py
```

> **Linux:** si `pip` instala en el Python del sistema puede requerir `sudo pip3 install -r requirements.txt` o agregar `--break-system-packages` en distribuciones que lo protejan (Debian 12+, Ubuntu 23+).

---

### Configuración inicial (`setup.py`)

`setup.py` se ejecuta **una sola vez por PC**. Solicita:

| Dato | Ejemplo |
|------|---------|
| Nombre de la PC | `PC-01` |
| URL del servidor | `http://192.168.1.100:8000` |

Genera automáticamente:
- `config.ini` — nombre de PC y URL del servidor
- `.pc_id` — identificador UUID único e inmutable de esta PC
- `biblioteca_local.db` — base de datos SQLite local

> **No borrar `.pc_id`.** Si se elimina, la PC queda registrada como una nueva máquina en el servidor.

---

### Autostart (arranque automático)

#### Linux

```bash
bash autostart/instalar_linux.sh
```

Crea `~/.config/autostart/biblioteca-kiosko.desktop`. Opcionalmente instala un servicio systemd (requiere `sudo`).

Para desinstalar:

```bash
rm ~/.config/autostart/biblioteca-kiosko.desktop
# Si instalaste systemd:
sudo systemctl disable biblioteca-kiosko
sudo rm /etc/systemd/system/biblioteca-kiosko.service
```

#### Windows

Ejecutar como administrador:

```
autostart\instalar_windows.bat
```

Registra la app en `HKCU\...\Run` y crea una tarea programada. Para desinstalar:

```
autostart\desinstalar_windows.bat
```

---

## Actualizar a una versión nueva

### Si está instalado con entorno virtual

```bash
# 1. Ir al directorio del proyecto
cd bliblioteca-horas-sociales_cliente

# 2. Bajar cambios
git pull

# 3. Activar entorno virtual
source cliente/venv/bin/activate   # Linux
# cliente\venv\Scripts\activate    # Windows

# 4. Actualizar dependencias (por si se agregaron nuevas)
pip install -r cliente/requirements.txt

# 5. Ejecutar
python cliente/main.py
```

### Si está instalado directamente en la máquina

```bash
# 1. Ir al directorio del proyecto
cd bliblioteca-horas-sociales_cliente

# 2. Bajar cambios
git pull

# 3. Actualizar dependencias
pip install -r cliente/requirements.txt

# 4. Ejecutar
python cliente/main.py
```

> **Importante:** `config.ini` y `.pc_id` **no se modifican** con `git pull` porque están en `.gitignore`. La configuración de la PC se conserva entre actualizaciones. No hace falta volver a ejecutar `setup.py`.

---

## Estructura del proyecto

```
cliente/
├── main.py          # Punto de entrada
├── setup.py         # Configuración inicial (ejecutar una vez)
├── config.py        # Carga config.ini y .pc_id
├── database.py      # SQLite local
├── sync.py          # Sincronización con servidor
├── network.py       # Llamadas HTTP
├── estado.py        # Estado de sesión
├── ui/              # Ventanas PyQt6
├── autostart/       # Scripts de arranque automático
├── requirements.txt
├── config.ini       # Generado por setup.py (no en git)
└── .pc_id           # Generado por setup.py (no en git)
```

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `ModuleNotFoundError: PyQt6` | Dependencias no instaladas | `pip install -r requirements.txt` |
| `No module named 'requests'` | Igual | Igual |
| App no conecta al servidor | URL incorrecta en `config.ini` | Editar `[servidor] url` en `config.ini` |
| PC aparece duplicada en servidor | Se borró `.pc_id` | Contactar admin del servidor para eliminar registro huérfano |
| Ventana no abre (Linux sin entorno gráfico) | Falta `DISPLAY` | Verificar sesión gráfica activa |
