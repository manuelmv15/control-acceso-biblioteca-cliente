# Estructura del proyecto — Biblioteca Cliente

Documentación de desarrollo, parte 2 de 2. Para cómo desplegar, ver [`despliegue.md`](./despliegue.md). Para la guía de uso del kiosko, ver [`../usuario.md`](../usuario.md).

## Qué hace en cada PC

1. Bloquea la PC detrás de una pantalla de login a pantalla completa hasta que alguien se identifica con su carnet.
2. Si el carnet no existe, ofrece un registro rápido (o acceso anónimo como invitado si el sector no es "Estudiante").
3. Mientras dura la sesión, muestra un widget flotante con el tiempo restante y permite cerrar sesión manualmente o por expiración automática.
4. Registra cada sesión (inicio/fin) en una base SQLite local y la sincroniza por lotes con el servidor.
5. En segundo plano, recolecta specs y salud de hardware (CPU, RAM, disco, temperatura) y las reporta periódicamente al servidor.

## Arquitectura y stack

- **UI**: PyQt6 (`QApplication`, `QMainWindow`, `QStackedWidget`), tema en `ui/estilos.qss` (paleta institucional UES: rojo `#8B0E13`).
- **DB local**: SQLite puro (sin ORM), `PRAGMA journal_mode=WAL`, `sqlite3.Row` como row factory (`db/connection.py`).
- **Red**: `requests`, HTTP síncrono contra la URL del servidor configurada.
- **Hardware**: `psutil` (opcional, con fallback si no está instalado) + `smartctl` vía `subprocess` para el estado SMART del disco.
- **Concurrencia**: dos hilos daemon independientes — sincronización general (`sync/`) y telemetría de hardware (`hardware/agent.py`) — cada uno despertable bajo demanda vía `threading.Event`.

Dependencias (`cliente/requirements.txt`): `PyQt6`, `requests`, `psutil`.

## Estructura de carpetas

```
cliente/
├── main.py                # entry point: init_db() → iniciar_sync() → iniciar_hardware_agent() → UI
├── setup.py                # configuración inicial por PC (una sola vez): config.ini + .pc_id
├── core/
│   ├── config.py            # carga de config.ini + overrides por variable de entorno
│   ├── estado.py             # estado en memoria de la sesión activa
│   └── bloqueo_escritorio.py  # deshabilita atajos de GNOME (best-effort)
├── db/                      # acceso a SQLite local
│   ├── connection.py, schema.py, estudiantes.py, hardware.py, sesiones.py
├── hardware/
│   ├── collector.py           # recolección de specs/salud
│   ├── mantenimiento.py         # acumulación de horas de uso y estado de mantenimiento
│   └── agent.py                  # hilo daemon que orquesta ambos y reporta al servidor
├── network/                 # cliente HTTP delgado por dominio (estudiantes, hardware, sesiones)
├── sync/__init__.py          # hilo daemon de sincronización general (sesiones + estudiantes + heartbeat)
├── ui/                       # pantallas: kiosko, login, registro, bienvenida, flotante
└── autostart/                # scripts de instalación/desinstalación/actualización en Linux
```

## Flujo de uso completo

1. **Arranque** (`main.py`): inicializa la DB local, lanza el hilo de sync, lanza el hilo del agente de hardware, y crea la `VentanaKiosko`.
2. **`VentanaKiosko`** (`ui/kiosko.py`): pantalla completa, sin bordes, siempre encima (`FramelessWindowHint | WindowStaysOnTopHint`). Contiene un `QStackedWidget` con login, registro y bienvenida/sesión, más un ícono de bandeja del sistema (menú: "Cerrar sesión" / "Salir (admin)") y un atajo oculto **`Ctrl+Shift+Alt+Q`** para salida administrativa.
3. **Login** (`ui/login.py`): el usuario escribe su carnet. Se busca primero en la caché local (`estudiantes_cache`); si no está y hay conexión, se consulta al servidor (`GET /estudiantes/{carnet}`) y se cachea el resultado. Si no existe, invita a registrarse.
4. **Registro** (`ui/registro.py`): formulario con nombre, carnet, año de nacimiento, sector (Estudiante/Administrativo/Docente/Visitante), sede, facultad/departamento y carrera (listas en cascada), y género. Si el sector no es "Estudiante", no se piden datos personales y se otorga acceso anónimo (modo invitado, sesión sin carnet). Si hay datos de estudiante, se valida duplicado e intenta enviarse al servidor (`POST`/`PUT /estudiantes`); si falla o no hay red, se guarda localmente marcado como pendiente de sincronizar.
5. **Sesión iniciada**: se genera un `uuid4` como id de sesión, se guarda en `sesiones_pendientes` local, se muestra una pantalla de bienvenida (`ui/bienvenida.py`, ~3s) y luego la ventana se oculta a la bandeja mostrando un **widget flotante** (`ui/flotante.py`) — botón circular expandible con el tiempo restante, botón de "Actualizar mis datos" (oculto para invitados) y "Cerrar sesión". Arranca un temporizador de duración de sesión configurable.
6. **Cierre de sesión**: manual o por expiración automática. En ambos casos se registra `hora_fin`, se limpia el estado en memoria, se fuerza una sincronización inmediata (sin esperar el intervalo periódico), y se vuelve a mostrar el login en pantalla completa.
7. **Salida administrativa**: solo posible con el atajo secreto o el ítem "Salir (admin)" del menú de bandeja, y ambos exigen ingresar el PIN de administrador (hash SHA-256 comparado con `hmac.compare_digest` contra `[admin] pin_hash` en `config.ini`) antes de cerrar cualquier sesión activa y terminar la aplicación. Si no hay PIN configurado, la salida queda bloqueada (falla cerrado, no hay bypass por defecto). El botón de cerrar normal del sistema operativo está interceptado: solo oculta la ventana a la bandeja, nunca cierra la app.

## Modelo de datos local (`db/schema.py`)

Tres tablas SQLite, con migraciones idempotentes que corren en cada arranque:

| Tabla | Campos principales | Propósito |
|---|---|---|
| `sesiones_pendientes` | `id` (PK, uuid), `pc_id`, `carnet` (nullable → modo invitado), `hora_inicio`, `hora_fin`, `fecha`, `sincronizado`, `timestamp_sync` | Cola de sesiones de uso a enviar al servidor vía `/sync` |
| `estudiantes_cache` | `carnet` (PK), `nombre`, `carrera`, `facultad`, `fecha_nacimiento`, `sexo`, `sincronizado`, `pendiente_modo` (`"crear"`/`"actualizar"`) | Caché local de estudiantes consultados o registrados sin conexión |
| `hardware_local` | `pc_id` (PK), `horas_acumuladas`, `ultimo_heartbeat`, `ultimo_mantenimiento_conocido` | Acumulador de horas de encendido de esta PC |

Migraciones destacadas: `_migrar_carnet_nullable` (reconstruye `sesiones_pendientes` si `carnet` aún tiene la vieja restricción `NOT NULL`, necesaria para el modo invitado) y `_migrar_estudiantes_pendientes` (añade columnas `sincronizado`/`pendiente_modo` si faltan).

El daemon de sincronización lee lo pendiente de ambas tablas, lo envía al servidor y marca como sincronizado tras éxito; las sesiones se enriquecen con datos del estudiante desde la caché antes de enviarse.

## Agente de hardware

- **`hardware/collector.py`**:
  - `identificacion()`: hostname y MAC — solo para inventario legible; la clave real de la PC es siempre `.pc_id`.
  - `specs()`: CPU, RAM total, almacenamiento total, sistema operativo.
  - `salud()`: temperatura promedio de CPU y estado SMART del disco (vía `smartctl -H` sobre discos candidatos como `/dev/sda`, `/dev/nvme0n1`, `/dev/vda`). Todo best-effort: nunca lanza excepción, devuelve `None` si no puede leer un dato.
  - `uptime_sistema_segundos()`: uptime del sistema operativo, usado solo para "sembrar" el acumulador de horas la primera vez.
- **`hardware/mantenimiento.py`**:
  - `calcular_estado(horas)`: `"optimo"` (<300h), `"pendiente"` (≥300h), `"critico"` (>400h) — mismos umbrales que usa el servidor.
  - `registrar_heartbeat(pc_id, uptime_seed_segundos)`: acumula horas reales transcurridas desde el último heartbeat.
  - `aplicar_reset_si_corresponde(pc_id, ultimo_mantenimiento_servidor)`: resetea el acumulador local a 0 si el servidor indica un mantenimiento más reciente que el conocido localmente.
- **`hardware/agent.py`**: hilo daemon que, cada `HARDWARE_INTERVAL_SEGUNDOS` (default 300s), arma un payload completo (identificación + specs + salud + horas acumuladas) y lo envía al servidor; aplica el posible reset de mantenimiento según la respuesta. Loguea en `hardware.log`. Expone `forzar_lectura()` para disparar un ciclo bajo demanda.

## Capa de red (`network/`)

- **`client.py`**: `hay_conexion(timeout=5)` — `GET /health`, chequeo previo antes de cualquier sincronización.
- **`estudiantes.py`**: `obtener_estudiante(carnet)` (`GET /estudiantes/{carnet}`), `registrar_estudiante(datos)` (`POST /estudiantes`, acepta 200/201/409 como éxito), `actualizar_estudiante(carnet, datos)` (`PUT /estudiantes/{carnet}`).
- **`hardware.py`**: `enviar_hardware(pc_id, payload)` (`POST /pcs/{pc_id}/hardware`), devuelve el JSON de respuesta (incluye `ultimo_mantenimiento`) o `None` si falla.
- **`sesiones.py`**: `enviar_estado(payload)` (`POST /estado`, heartbeat de sesión activa) y `enviar_sesiones(payload)` (`POST /sync`, batch de sesiones cerradas pendientes).

Todas las funciones de red capturan cualquier excepción y devuelven `None`/`False` en caso de fallo, sin propagar errores — esto hace trivial el patrón de reintento en el siguiente ciclo del daemon correspondiente.

## Sincronización general (`sync/__init__.py`)

Hilo daemon que, cada `SYNC_INTERVAL` (default 30s), en cada ciclo:
1. Verifica conexión (`hay_conexion()`); si no hay, salta el ciclo.
2. Reenvía estudiantes pendientes de sincronizar (registros/actualizaciones hechos offline).
3. Envía un heartbeat del estado actual de la sesión (`POST /estado`).
4. Envía las sesiones cerradas pendientes (`POST /sync`), enriquecidas con datos del estudiante desde la caché; marca como sincronizado lo que el servidor confirma.

Loguea todo en `sync.log`. Expone `forzar_sync()`, invocado tras login, logout o actualización de datos, para no esperar el intervalo completo.

## Configuración — para detalle de despliegue ver `despliegue.md`

`core/config.py` lee `config.ini` (secciones `[pc]`, `[servidor]`, `[sync]`, `[admin]`, `[escritorio]`) con override por variable de entorno. También define `TZ_SV = ZoneInfo("America/El_Salvador")` y `now_sv()`, usados en toda la app para timestamps consistentes.

## Detalles importantes / peculiaridades

- **Modo kiosko real**: la ventana está siempre encima y sin bordes, y el botón de cerrar del sistema operativo está interceptado (solo oculta a la bandeja). Esto es control a nivel de aplicación Qt — no evita atajos que el propio *compositor* de GNOME captura antes de que el evento llegue a la ventana (p. ej. la tecla **Super**, que abre el resumen de Actividades, desde donde se puede lanzar cualquier icono fijado en el dock sin pasar por el login). `core/bloqueo_escritorio.py` deshabilita vía `gsettings`, en cada arranque de `main.py`: tecla Super/`overlay-key`, Alt+Tab y variantes, "mostrar escritorio", el atajo de terminal (`Ctrl+Alt+T`) y el dock entero (`favorite-apps`). Es best-effort (solo actúa si detecta GNOME por `XDG_CURRENT_DESKTOP` y si hay `gsettings` disponible) y se puede desactivar con `[escritorio] bloquear_atajos = false`. Es una restricción de usuario, no de sistema: son claves dconf del usuario que ejecuta el kiosko — alguien con una terminal como ese mismo usuario podría revertirlas con `gsettings set` dentro de una sesión ya abierta (se reaplican en el próximo arranque del kiosko, no al instante). Para un bloqueo que sí sobreviva a eso (dconf de sistema con locks + endurecimiento de BIOS/TTY), ver `despliegue.md`, sección **Bloqueo de escritorio para producción**.
- **`.pc_id`**: archivo de texto plano con un UUID4, generado una sola vez. Es el identificador **estable y persistente** de la PC física usado en todos los payloads hacia el servidor — independiente del hostname/MAC, que solo sirven para inventario legible.
- **Tolerancia a fallos de red**: cualquier excepción en la capa `network/` se traga y los datos quedan marcados como pendientes en SQLite, reintentándose automáticamente en el siguiente ciclo del daemon de sync, sin intervención del usuario.
- **Modo invitado**: si el sector elegido no es "Estudiante", no se piden datos personales; la sesión se guarda con `carnet=None`. Requiere la migración `_migrar_carnet_nullable` en bases de datos creadas antes de que existiera este modo.
- **Logs**: `sync.log` y `hardware.log`, ambos regenerables (no versionados en git), limpiados por `desinstalar_linux.sh`.
- Los estilos y el catálogo de sedes/facultades/carreras en `ui/registro.py` replican la identidad visual y la oferta académica real de la UES (Facultad Multidisciplinaria de Oriente).

## Mapa del código (`.codebase-memory/`)

El repo mantiene un grafo de conocimiento del código (funciones, clases, archivos, imports, llamadas entre símbolos) indexado con `codebase-memory-mcp`, más un dashboard HTML que lo visualiza — útil para explorar quién llama a quién sin leer todo el código.

```
.codebase-memory/
├── graph.db.zst              # snapshot comprimido del grafo, para compartir sin reindexar
├── artifact.json              # metadata del último snapshot: commit, fecha, nº de nodos/aristas, tamaño
├── generate_dashboard.py     # script generador del dashboard
├── dashboard.template.html    # plantilla del dashboard
└── dashboard.html             # dashboard generado — no versionado, se regenera solo
```

Abrir `.codebase-memory/dashboard.html` directamente en el navegador. Reindexar pidiéndoselo a Claude Code o con la skill `codebase-memory`. Hay un hook `PostToolUse` en `.claude/settings.json` que regenera el dashboard automáticamente tras cada reindexación; a mano: `python3 .codebase-memory/generate_dashboard.py`.
