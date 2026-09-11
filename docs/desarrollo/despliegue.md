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
pip install --break-system-packages -r requirements.txt
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

## Autostart en Linux (`cliente/autostart/`)

### Instalar

```bash
cd cliente/autostart
./instalar_linux.sh
```

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

```
1. Desplegar biblioteca_servidor en la PC maestra
2. Anotar IP local de la PC maestra
3. En cada PC hija:
      pip install -r requirements.txt
      python setup.py
4. Probar con 2-3 PCs antes de las 16
5. Verificar en el panel admin que llegan las sesiones
6. (Opcional) túnel Cloudflare para acceso externo al panel — ver biblioteca_servidor
```
