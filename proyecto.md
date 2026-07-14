## 1. El Flujo de Experiencia del Usuario (UX)
Para que el sistema funcione sin fricciones, el acceso a las computadoras debe estar bloqueado por una **pantalla de inicio de sesión personalizada** (un *display manager* modificado o un cliente de escritorio que se ejecute en pantalla completa al arrancar el sistema).

```
                 [ Pantalla de Inicio ]
                           |
            +--------------+--------------+
            |                             |
      [ Estudiante ]                 [ Invitado ]
            |                             |
    * Carnet/ID                     * Botón "Entrar como Invitado"
    * API/BD Universitaria          * Registro de inicio de sesión
    * Obtiene: Carrera, Facultad,   * Temporizador activo (1h)
      Año de Nacimiento, Sexo.            |
            +--------------+--------------+
                           |
                  [ Sesión Activa ]
                           |
             ( Monitoreo de Hardware en segundo plano )
                           |
                 [ Cierre de Sesión ]
         ( Guarda hora de fin y tiempo de uso )
```

- **Flujo Estudiante:** El estudiante ingresa su número de carnet o ID. El sistema consulta rápidamente la base de datos de la universidad (o un archivo local de estudiantes) para recuperar automáticamente su **Carrera, Facultad, Año de Nacimiento** y **Sexo**. Esto evita que el estudiante tenga que escribir todo manualmente cada vez que usa una PC.
- **Flujo Invitado:** Un botón simple que dice "Acceder como Invitado". Al hacer clic, se inicia un temporizador. Para evitar abusos, puedes configurar que las sesiones de invitado se cierren automáticamente después de cierto tiempo (por ejemplo, 2 horas).

## 2. Módulo de Mantenimiento de Hardware (El "Fierro")
Esta es la parte más robusta del proyecto. En lugar de llevar un registro manual en papel, cada computadora tendrá un **agente (un servicio en segundo plano)** que reportará el estado de la máquina a una base de datos centralizada.

### Datos clave a recolectar de la PC:

- **Identificador Único:** Nombre del host (ej. `LAB-01-PC05`) o dirección MAC.
- **Tiempo de Encendido Acumulado (Uptime Histórico):** Cuántas horas reales ha estado encendida la máquina desde el último mantenimiento registrado.
- **Especificaciones de Hardware:** Procesador, memoria RAM, almacenamiento y sistema operativo (útil para inventario).
- **Métricas de Salud (Opcional pero recomendado):** Temperatura promedio del procesador (para detectar si la pasta térmica ya no sirve) y estado de salud del disco (S.M.A.R.T.).

### ¿Cómo calcular el mantenimiento preventivo?
En lugar de hacerlo por "fechas de calendario" (que no reflejan el uso real), el sistema disparará alertas basadas en **horas de uso acumuladas**.

**Estado**  **Horas de Uso**  **Acción del Sistema**

**Óptimo**  < 300 hrs  Funcionamiento normal.

**Mantenimiento Pendiente**  300 - 400 hrs  Envía una alerta silenciosa al panel de administración.

**Crítico (Requiere atención)**  > 400 hrs  Muestra una notificación al administrador y resalta la PC en rojo en el dashboard.

