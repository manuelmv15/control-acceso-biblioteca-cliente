# Guía de usuario — Kiosko de Biblioteca

Esta guía es para quien **usa las PCs de la sala de biblioteca**: estudiantes, y también personal administrativo, docentes o visitantes. No requiere conocimientos técnicos.

Si sos desarrollador y buscás cómo instalar o modificar el sistema, ver [`desarrollo/despliegue.md`](./desarrollo/despliegue.md) y [`desarrollo/estructura.md`](./desarrollo/estructura.md).

## Iniciar sesión con tu carnet

Al sentarte frente a una PC de la sala, vas a ver una pantalla de acceso a pantalla completa (no podés minimizarla ni acceder al escritorio sin identificarte).

1. Escribí tu **número de carnet** en el campo de login.
2. Confirmá.

Si tu carnet ya está registrado, entrás directo. Si el sistema no lo reconoce, te va a invitar a **registrarte**.

## Registrarte por primera vez

Si tu carnet no existe en el sistema, se abre un formulario corto:

- **Nombre completo**
- **Carnet**
- **Año de nacimiento**
- **Sector**: Estudiante, Administrativo, Docente o Visitante
- **Sede**, **facultad/departamento** y **carrera** (si aplica) — se eligen de listas desplegables.
- **Género**

> Si elegís un sector distinto a **Estudiante**, no se te piden datos personales adicionales y entrás como **invitado** (sesión anónima) — ideal para personal administrativo, docentes o visitantes que solo necesitan usar la PC un momento.

Completá el formulario y confirmá. Si en ese momento no hay conexión a internet, tus datos igual quedan guardados en la PC y se envían al servidor automáticamente en cuanto vuelva la conexión — no necesitás hacer nada más.

## Durante tu sesión

Después de un breve mensaje de bienvenida, la pantalla completa desaparece y queda un **widget flotante** en la pantalla — un botón circular con el tiempo restante de tu sesión.

- Hacé clic en el widget para expandirlo y ver más opciones.
- **Actualizar mis datos**: disponible si te registraste como estudiante (no aparece en modo invitado), para corregir o completar tu información.
- **Cerrar sesión**: termina tu sesión manualmente en cualquier momento.

Tu sesión tiene una duración configurada por la biblioteca (por defecto 60 minutos). Cuando se acaba el tiempo, la sesión se cierra automáticamente y la pantalla vuelve al login para el siguiente usuario.

## Cerrar tu sesión

Podés cerrar sesión de dos formas:
- Manualmente, desde el widget flotante ("Cerrar sesión") o desde el ícono en la bandeja del sistema.
- Automáticamente, cuando se agota el tiempo de tu sesión.

En ambos casos la PC vuelve a la pantalla de login, lista para el siguiente usuario.

## Preguntas frecuentes

**Escribí mi carnet y dice que no existe, pero ya me había registrado antes.**
Puede que te hayas registrado en otra PC y esa sesión aún no se sincronizó con el servidor (por ejemplo, si esa PC estuvo sin internet). Probá de nuevo en unos minutos, o completá el formulario de registro otra vez — el sistema no va a duplicar tu carnet si ya existe.

**No tengo carnet de estudiante, ¿puedo usar la PC igual?**
Sí. Elegí un sector distinto a "Estudiante" (Administrativo, Docente o Visitante) al registrarte y vas a entrar como invitado, sin necesidad de dar datos personales.

**Se me olvidó cerrar sesión, ¿qué pasa?**
Tu sesión se cierra sola automáticamente cuando se cumple el tiempo configurado. No queda abierta indefinidamente.

**No puedo minimizar la ventana ni acceder al escritorio.**
Es esperado: la PC está en modo kiosko y solo permite usarla mientras hay una sesión iniciada. Si necesitás algo distinto, consultá con el personal de la biblioteca.

**¿Qué hace el ícono en la bandeja del sistema?**
Ofrece un menú con "Cerrar sesión" y una opción de salida solo para administradores del sistema (requiere un PIN que únicamente conoce el personal técnico) — no es una función para uso general.

**¿Mis datos están seguros si se corta la luz o el internet a mitad de mi sesión?**
Sí. La PC guarda tu sesión localmente y la envía al servidor apenas se restablece la conexión, sin que pierdas tu registro de uso.
