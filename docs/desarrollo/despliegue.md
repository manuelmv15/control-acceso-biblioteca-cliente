# Despliegue — Biblioteca Cliente

Documentación de desarrollo, parte 1 de 2. Para cómo está organizado el código, ver [`estructura.md`](./estructura.md). Para la guía de uso del kiosko, ver [`../usuario.md`](../usuario.md).

Este componente se instala **en cada PC de la sala** (kiosko). Requiere que `biblioteca_servidor` ya esté desplegado y accesible por red — ver `biblioteca_servidor/docs/desarrollo/despliegue.md`.

## Requisitos previos

- Python 3.x con PyQt6 disponible (en Linux, puede requerir paquetes del sistema para Qt según la distro).
- Acceso de red al backend `biblioteca_servidor` (local o remoto).
- Opcional: `smartctl` instalado en el sistema para reportar salud SMART del disco.

## Instalación inicial en una PC nueva

```bash
cd cliente
pip install -r requirements.txt
```

Si falla con `error: externally-managed-environment` (PEP 668 — común en distros Linux recientes cuando se usa el Python del sistema en vez de un venv), reintentar con:

```bash
pip install --break-system-packages -r requirements.txt
```

Justificado porque cada PC hija es de uso dedicado (kiosko), no un entorno de desarrollo general — mismo criterio que aplica `cliente/autostart/actualizar_linux.sh` al actualizar.

```bash
python setup.py
```

`setup.py` es el asistente de configuración inicial, se corre **una sola vez por PC**. Pide:

1. **Nombre de la PC** (default `PC-01`) — identificador legible, se muestra en el panel admin.
2. **URL del servidor** (default `http://localhost:8000`) — apuntar a la IP/dominio real de la PC maestra donde corre `biblioteca_servidor`. Si no es `http://localhost`/`127.0.0.1`, exige `https://` salvo que confirmes explícitamente que asumís el riesgo de usar `http://` sin cifrar — ver sección **TLS** más abajo.
3. **Certificado de la CA interna** (`ca.pem`), solo si elegiste `https://` — necesario para validar el servidor cuando usa un certificado propio (no de una CA pública). Ver sección **TLS**.
4. En este punto genera (o reutiliza) `.pc_id` — UUID4 que identifica a esta PC de forma estable, independiente del hostname/MAC — y lo muestra en pantalla.
5. **API key de esta PC** (`KIOSK_API_KEY`) — se genera desde el panel admin del servidor (pestaña "PCs", botón "Generar API key") usando el `PC_ID` que acaba de mostrar el paso anterior; el valor solo se ve una vez ahí. Sin esto, el login y registro de estudiantes fallan con 401.
6. **PIN de administrador** para la salida administrativa del kiosko (se pide oculto con `getpass`, se guarda como hash SHA-256, nunca en texto plano). Si se deja vacío, la salida administrativa queda bloqueada hasta configurarlo.

Luego `setup.py`:
- Escribe `config.ini` con todo lo anterior.
- Inicializa la base de datos SQLite local.
- Ofrece instalar el autostart (ver siguiente sección).

El kiosko son dos procesos: el servicio (`python -m servicio`), que lee `config.ini` y la base local y habla con el servidor, y la interfaz (`python main.py`), que solo le habla al servicio por un socket local. Tienen que correr con usuarios del sistema distintos para que el estudiante no pueda leer `config.ini` ni la base; ver [`estructura.md`](./estructura.md), sección **Separación entre la UI y el servicio**. `config.ini`, `.pc_id`, `db_key.bin`, la base y los logs del servicio van en `BIBLIOTECA_DATA_DIR` (por defecto, junto al código).

## Binario empaquetado (PyInstaller, CI)

`.github/workflows/pip-audit.yml` (job `build-cliente`) empaqueta `main.py` con PyInstaller (`cliente/build.spec`) en cada push/PR y sube el resultado como artifact (`biblioteca-kiosko-linux`, 30 días de retención) — sirve como verificación automática de que el kiosko sigue empaquetando y arrancando (smoke test headless), y como forma de bajar un build ya armado sin instalar Python en la PC destino.

**Sigue siendo `onedir`, no `onefile`**: el resultado es una carpeta (`biblioteca-kiosko/` con el ejecutable y `_internal/` al lado), no un solo archivo. Es a propósito — `config.ini`, `.pc_id` y la base SQLite local se guardan junto al código (`_internal/`), y en un bundle `onefile` esa carpeta se recrearía vacía en un directorio temporal distinto cada vez que se abre la app, perdiendo la identidad de la PC y el caché local en cada reinicio. Para usarlo hay que copiar la carpeta `biblioteca-kiosko/` completa, no solo el ejecutable.

**Limitación actual: `setup.py` no está empaquetado**, solo `main.py`. El binario no tiene el asistente de primera configuración — antes de usarlo en una PC hace falta generar su `config.ini`/`.pc_id` (con `python setup.py` desde un checkout del código, ver más abajo) y copiar esos dos archivos dentro de `_internal/` de la carpeta empaquetada. Como cada PC necesita su propio `.pc_id`/API key (ver siguiente sección), **no se puede copiar la misma carpeta ya configurada a las 16 PCs** — cada una necesita su propio `setup.py` + su propia copia de `_internal/config.ini`/`_internal/.pc_id`, o (más simple hoy) seguir instalando desde código fuente como abajo. Este binario es, por ahora, sobre todo una verificación de CI, no todavía el método de despliegue recomendado. Además, solo empaqueta la interfaz: el servicio (`python -m servicio`) no está incluido en el binario.

## Autostart en Linux (`cliente/autostart/`)

### Instalar

```bash
cd cliente/autostart
./instalar_linux.sh
```

> ⚠️ **Pendiente:** estos scripts todavía instalan un solo proceso (`main.py`) con el usuario de la sesión gráfica. Hay que adaptarlos a la separación entre UI y servicio: un usuario de servicio dueño de `BIBLIOTECA_DATA_DIR`, el servicio como unidad systemd con ese usuario y la UI en el autostart de la sesión del estudiante. Hasta entonces, el servicio se arranca a mano con `python -m servicio`.

Crea un `.desktop` en `~/.config/autostart/` para arrancar la app al iniciar sesión gráfica. Opcionalmente, con confirmación, instala también un servicio `systemd` (`biblioteca-kiosko.service`, `Restart=always`, con `DISPLAY`/`XAUTHORITY` configurados para acceso gráfico) habilitado con `systemctl enable` — recomendado para que el kiosko se recupere solo ante un cierre inesperado.

### Actualizar

```bash
cd cliente/autostart
./actualizar_linux.sh
```

Valida que no haya cambios locales sin commit, hace `git fetch` + `git merge --ff-only`, reinstala dependencias (maneja el caso PEP 668 "externally-managed-environment" con `--break-system-packages` — justificado porque la PC es de uso dedicado), y reinicia el servicio systemd si está habilitado (o avisa reabrir manualmente / que el cambio aplicará en el próximo arranque).

### Desinstalar

```bash
cd cliente/autostart
./desinstalar_linux.sh
```

Mata cualquier proceso en ejecución de la app, elimina el `.desktop` de autostart y (si existe) el servicio systemd, limpia `__pycache__`/`sync.log`/`hardware.log`, y pregunta si además borrar:
- `config.ini`/`.pc_id` (para reconfigurar la PC desde cero).
- `biblioteca_local.db` (**advierte** sobre posibles sesiones no sincronizadas — no borrar si hay sospecha de sesiones pendientes de enviar al servidor).

## Configuración (`config.ini` + variables de entorno)

`config.ini` y `.pc_id` están en `.gitignore` (específicos de cada máquina) — se generan con `setup.py`, no se versionan.

| Variable | Fuente en `config.ini` | Variable de entorno (override) | Default |
|---|---|---|---|
| `SERVER_URL` | `[servidor] url` | `BIBLIOTECA_SERVER_URL` | `http://localhost:8000` |
| `PERMITIR_HTTP_INSEGURO` | `[servidor] permitir_http_inseguro` | `BIBLIOTECA_PERMITIR_HTTP` | `false` — con `SERVER_URL` en `http://` hacia un host que no es localhost, la app rehúsa arrancar salvo que esto sea `true` |
| `CA_CERT_PATH` | `[servidor] ca_cert` | `BIBLIOTECA_CA_CERT` | `""` (vacío → usa el almacén de CAs del sistema; poner acá el `ca.pem` de la CA interna si el servidor no tiene un certificado público) |
| `KIOSK_API_KEY` | `[servidor] kiosk_key` | `BIBLIOTECA_KIOSK_KEY` | `""` (vacío → login/registro falla con 401). Key propia de esta PC (generada desde el panel para su `PC_ID`, no compartida con las demás) — se manda junto con `X-PC-Id` en cada request. |
| `ADMIN_PIN_HASH` | `[admin] pin_hash` | `BIBLIOTECA_ADMIN_PIN_HASH` | `""` (vacío → salida admin bloqueada) |
| `PC_ID` | archivo `.pc_id` | — (solo por archivo) | uuid4 generado |
| `PC_NOMBRE` | `[pc] nombre` | `BIBLIOTECA_PC_NOMBRE` | `PC-00` |
| `SYNC_INTERVAL` | `[sync] intervalo_segundos` | — | 30 |
| `DURACION_SESION_MINUTOS` | `[sesion] duracion_minutos` | — | 60 |
| `HARDWARE_INTERVAL_SEGUNDOS` | `[hardware] intervalo_segundos` | — | 300 |
| `BLOQUEAR_ATAJOS_ESCRITORIO` | `[escritorio] bloquear_atajos` | `BIBLIOTECA_BLOQUEAR_ATAJOS` | `true` |
| `GRUPO_UI` | `[servicio] grupo_ui` | `BIBLIOTECA_GRUPO_UI` | `kiosko-ui` (grupo del sistema cuyos miembros pueden usar el socket del servicio; si no existe, solo el propio usuario del servicio) |

Fuera de `config.ini`: `BIBLIOTECA_DATA_DIR` (directorio de datos del servicio), `BIBLIOTECA_SOCKET` (ruta del socket, la misma para el servicio y la UI) y `BIBLIOTECA_UI_LOG` (archivo de log opcional de la UI). Ver `estructura.md`.

## TLS (cifrado entre el kiosko y el servidor)

`SERVER_URL` hacia cualquier host que no sea `localhost`/`127.0.0.1` tiene que ser `https://` — si no, `core/config.py` lanza `RuntimeError` al arrancar (ver `_validar_server_url`). Es intencional: sin TLS, la PII de los estudiantes y el header `X-Kiosk-Key` viajan en texto plano por la red del laboratorio.

Como el servidor normalmente no tiene un dominio público (solo una IP de LAN), no aplica una CA pública tipo Let's Encrypt — `biblioteca_servidor/servidor/scripts/generar_ca.sh` genera una **CA interna propia** y un certificado para la IP del servidor. Pasos:

1. En la PC maestra, generar la CA y el certificado del servidor (ver `biblioteca_servidor/docs/desarrollo/despliegue.md`, sección TLS) — produce, entre otros, `ca.pem`.
2. Copiar ese `ca.pem` a cada PC hija, junto a `config.ini` (p. ej. `cliente/ca.pem`).
3. En `setup.py`, al elegir `https://`, indicar la ruta a ese `ca.pem` cuando se pregunte — o completarla a mano después en `config.ini`:
   ```ini
   [servidor]
   url = https://192.168.x.x:8000
   ca_cert = ca.pem
   ```
4. Si el servidor certificado por la CA interna todavía no está listo y hace falta seguir operando en `http://` mientras tanto, hay que asumirlo a propósito con `permitir_http_inseguro = true` en `config.ini` — nunca es el comportamiento por defecto.

Certificado del servidor con vencimiento ~825 días (ver script) — calendarizar su renovación, no hay renovación automática como con una CA pública.

## Bloqueo de escritorio para producción (evita fuga de `config.ini` y del código)

`core/bloqueo_escritorio.py` deshabilita atajos de GNOME (Activities, Alt+Tab, dock, terminal) escribiendo dconf **de usuario** (`gsettings set`) en cada arranque del kiosko. Es best-effort a propósito y tiene un límite conocido, documentado en su propio docstring: son claves reversibles por cualquiera que consiga una terminal en esa misma sesión (`gsettings set ...` las pisa de nuevo, sin esperar al próximo arranque del kiosko). Y una vez con terminal en esa cuenta, el problema deja de ser leer `config.ini` (`KIOSK_API_KEY` de esta PC + hash del PIN admin; comprometerla solo afecta a este equipo, ver `KIOSK_API_KEY` en la tabla de variables arriba) — ya hay acceso de red y al código fuente completos, con o sin el archivo. Verificado además que la propia app (`ui/`, `core/`) no expone ningún `QFileDialog` ni diálogo de impresión: toda la superficie de escape viene del entorno de escritorio, no de la app.

Para que el bloqueo sobreviva a una terminal abierta como ese mismo usuario, hace falta reforzarlo a nivel de sistema — esto **complementa** a `bloqueo_escritorio.py`, no lo reemplaza. Está automatizado en `cliente/autostart/bloquear_sistema_linux.sh` (requiere sudo, idempotente):

```bash
cd cliente/autostart
./bloquear_sistema_linux.sh
```

El script aplica, en orden:

1. **dconf de sistema, con locks** (en vez de solo dconf de usuario) — mismas claves que deshabilita `bloqueo_escritorio.py` (Activities, Alt+Tab, dock, atajo de terminal), pero escritas en `/etc/dconf/db/local.d/` + `/etc/dconf/db/local.d/locks/` y aplicadas con `dconf update`. A diferencia del dconf de usuario, estas quedan fijadas para cualquier usuario del sistema — `gsettings set` desde una terminal ya no las puede revertir.
2. **Bloqueo de cambio de terminal virtual** (`Ctrl+Alt+F2`), vía un drop-in en `/etc/systemd/logind.conf.d/90-kiosko.conf` (`NAutoVTs=1`, `ReserveVT=1`).
3. **Desinstalar terminal y explorador de archivos** (`gnome-terminal`, `xterm`, `nautilus`) — opcional, se pregunta antes de ejecutar porque en algunas distros puede arrastrar otros paquetes del entorno GNOME. Si no están instalados, ningún atajo (cubierto o no por el punto 1) puede alcanzarlos.

Ya está enganchado como paso opcional al final de `instalar_linux.sh` (se pregunta después de la opción de servicio systemd). Para revertir dconf + TTY (no la desinstalación de paquetes): `./desbloquear_sistema_linux.sh`.

Lo único que el script **no puede automatizar**, porque requiere acceso físico a la BIOS/UEFI de cada PC:

4. **BIOS/UEFI con contraseña de administrador**: deshabilitar boot por USB/medios externos y el modo recovery/single-user de GRUB. Sin esto, alguien arranca un live USB y monta el disco directamente — ningún bloqueo de la sesión gráfica importa en ese escenario.

Con las cuatro capas aplicadas no queda, dentro de la sesión del kiosko, ninguna ruta hacia una terminal ni un explorador de archivos — eso es lo que protege `config.ini` y el código fuente en la práctica, más que cualquier permiso de archivo por sí solo. `setup.py` y `core/config.py` ya aplican `chmod 0600` a `config.ini` como buena práctica complementaria contra *otras* cuentas del sistema, pero eso no cierra este vector por sí solo.

Mejora futura (no bloqueante): reemplazar la sesión GNOME completa por un compositor mínimo dedicado (p. ej. `cage`) que solo lance la app del kiosko, eliminando la superficie de escape por construcción en vez de ir deshabilitando atajos de GNOME uno por uno.

## Checklist antes de poner una PC en producción

- [ ] `KIOSK_API_KEY` generada desde el panel del servidor específicamente para el `PC_ID` de esta PC (pestaña "PCs" → "Generar API key"), no una key reutilizada de otra PC.
- [ ] PIN de administrador configurado (no vacío) — de lo contrario nadie puede hacer la salida administrativa.
- [ ] `SERVER_URL` apunta a la IP/dominio correcto de la PC maestra, no a `localhost`.
- [ ] `SERVER_URL` usa `https://` con el `ca.pem` de la CA interna configurado en `[servidor] ca_cert` (ver sección **TLS**) — o, si se decidió operar en `http://` a propósito, `permitir_http_inseguro = true` está fijado y el riesgo fue aceptado conscientemente, no por omisión.
- [ ] Autostart (`.desktop` y, recomendado, servicio `systemd`) instalado y probado con un reinicio real de la PC.
- [ ] Probado con 2-3 PCs antes de desplegar las 16 (o el total de la sala).
- [ ] Verificado en el panel admin del servidor que la PC aparece y llegan sus sesiones + heartbeat de hardware.
- [ ] Si el compositor es GNOME, aplicado el bloqueo de atajos **a nivel de sistema** (ver sección **Bloqueo de escritorio para producción** arriba) — el `core/bloqueo_escritorio.py` por sí solo es best-effort a nivel de usuario y no sobrevive a una terminal abierta en esa misma sesión.

## Orden de despliegue del sistema completo

Ver la guía paso a paso completa (servidor + todas las PCs + cómo se conectan entre sí) en `biblioteca_servidor/docs/desarrollo/despliegue.md`, sección **Orden de despliegue del sistema completo**, o en `DESPLIEGUE.md` en la raíz del workspace si ambos repos están junto a él. Resumen mínimo:

```
1. Desplegar biblioteca_servidor en la PC maestra (backend + MySQL)
2. Anotar la IP LAN de la PC maestra (ip a) y decidir si se usa TLS (recomendado)
3. En cada PC hija (repetir para las 16, empezando por 2-3 de prueba):
   a. pip install -r requirements.txt (--break-system-packages si PEP 668)
   b. python setup.py → nombre de PC, URL del servidor, ca.pem si hay TLS
   c. En el panel del servidor (pestaña "PCs"), generar la API key para el
      PC_ID que muestra setup.py, y pegarla cuando setup.py la pida
   d. Instalar autostart cuando setup.py lo ofrezca
4. Verificar en el panel admin (pestaña "PCs") que cada PC aparece y llegan
   su heartbeat de estado y sus sesiones
5. (Opcional) túnel Cloudflare para acceso externo al panel — ver biblioteca_servidor
```
