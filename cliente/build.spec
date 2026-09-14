# -*- mode: python ; coding: utf-8 -*-

# Empaqueta el kiosko como un binario ONEDIR (NO onefile) para Linux, con
# PyInstaller.
#
# onedir, no onefile, a propósito: core/config.py (CONFIG_FILE, PC_ID_FILE),
# db/connection.py (DB_PATH), etc. resuelven sus rutas de datos persistentes
# con `Path(__file__).parent...`. En un bundle onefile, PyInstaller extrae
# todo a un directorio TEMPORAL nuevo en cada arranque (`sys._MEIPASS`
# efímero) -- .pc_id/config.ini/la base local nunca sobrevivirían a un
# reinicio del kiosko, rompiendo la identidad de la PC y el caché local. En
# onedir, la carpeta `_internal/` (donde caen esos módulos) es un directorio
# real y persistente junto al ejecutable, así que esas rutas sí sobreviven
# entre ejecuciones -- se verificó a mano (build de prueba, dos corridas)
# que el PC_ID generado en la primera corrida se reusa en la segunda.
#
# Uso:
#   cd cliente && pyinstaller build.spec
#
# El resultado queda en dist/biblioteca-kiosko/ (ejecutable + _internal/).
# Para correrlo hay que copiar esa carpeta completa a la PC destino, no solo
# el ejecutable.

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('ui/estilos.qss', 'ui')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='biblioteca-kiosko',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='biblioteca-kiosko',
)
