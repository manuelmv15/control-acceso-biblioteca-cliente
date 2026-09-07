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
4. **API key de kiosko** (`KIOSK_API_KEY`) — debe ser **exactamente la misma** que la configurada en el `.env` del servidor. Sin esto, el login y registro de estudiantes fallan con 401.
5. **PIN de administrador** para la salida administrativa del kiosko (se pide oculto con `getpass`, se guarda como hash SHA-256, nunca en texto plano). Si se deja vacío, la salida administrativa queda bloqueada hasta configurarlo.

Luego `setup.py`:
- Escribe `config.ini` con todo lo anterior.
- Genera (o reutiliza) `.pc_id` — UUID4 que identifica a esta PC de forma estable, independiente del hostname/MAC.
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
| `KIOSK_API_KEY` | `[servidor] kiosk_key` | `BIBLIOTECA_KIOSK_KEY` | `""` (vacío → login/registro falla con 401) |
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

## Checklist antes de poner una PC en producción

- [ ] `KIOSK_API_KEY` coincide exactamente con la del servidor.
- [ ] PIN de administrador configurado (no vacío) — de lo contrario nadie puede hacer la salida administrativa.
- [ ] `SERVER_URL` apunta a la IP/dominio correcto de la PC maestra, no a `localhost`.
- [ ] `SERVER_URL` usa `https://` con el `ca.pem` de la CA interna configurado en `[servidor] ca_cert` (ver sección **TLS**) — o, si se decidió operar en `http://` a propósito, `permitir_http_inseguro = true` está fijado y el riesgo fue aceptado conscientemente, no por omisión.
- [ ] Autostart (`.desktop` y, recomendado, servicio `systemd`) instalado y probado con un reinicio real de la PC.
- [ ] Probado con 2-3 PCs antes de desplegar las 16 (o el total de la sala).
- [ ] Verificado en el panel admin del servidor que la PC aparece y llegan sus sesiones + heartbeat de hardware.
- [ ] Si el compositor es GNOME, confirmar que el bloqueo de atajos de escritorio (`core/bloqueo_escritorio.py`) se aplicó correctamente (ver `estructura.md`) — es best-effort y solo actúa sobre GNOME.

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
