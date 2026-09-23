"""Servicio en segundo plano del kiosko.

Es el único proceso que lee config.ini (API key de la PC, hash del PIN de
administrador), la clave de cifrado local y la base SQLite, y el único que
habla con el servidor. Corre con un usuario del sistema propio; la UI corre
con el usuario de la sesión gráfica —el mismo que usa el estudiante tras
iniciar sesión— y solo puede pedirle las operaciones de
`servicio/operaciones.py` a través del socket local de `servicio/servidor.py`.

Arranque: `python -m servicio` desde cliente/.
"""
