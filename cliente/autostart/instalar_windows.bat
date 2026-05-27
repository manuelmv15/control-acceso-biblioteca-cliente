@echo off
setlocal EnableDelayedExpansion
title Biblioteca Kiosko - Instalacion de arranque automatico

set "APP_DIR=%~dp0.."
set "APP_DIR=%APP_DIR:~0,-1%"
for %%I in ("%APP_DIR%") do set "APP_DIR=%%~fI"
set "MAIN_PY=%APP_DIR%\main.py"

echo ====================================================
echo  Biblioteca Kiosko - Instalacion de autostart
echo ====================================================
echo.
echo Directorio de la app: %APP_DIR%
echo.

:: Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no encontrado. Instalar Python 3.10+ primero.
    pause & exit /b 1
)

for /f "tokens=*" %%i in ('python -c "import sys; print(sys.executable)"') do set "PYTHON_EXE=%%i"
echo Python: %PYTHON_EXE%
echo.

:: Opcion 1: Registro
echo [1] Agregando al registro de Windows (Run al iniciar sesion)...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" ^
    /v "BibliotecaKiosko" ^
    /t REG_SZ ^
    /d "\"%PYTHON_EXE%\" \"%MAIN_PY%\"" ^
    /f
echo     OK - Autostart en registro creado

:: Opcion 2: Tarea programada (mas robusta)
echo.
echo [2] Creando tarea programada...
schtasks /create /tn "BibliotecaKiosko" ^
    /tr "\"%PYTHON_EXE%\" \"%MAIN_PY%\"" ^
    /sc ONLOGON ^
    /rl LIMITED ^
    /f >nul 2>&1
if %errorlevel% equ 0 (
    echo     OK - Tarea programada creada
) else (
    echo     AVISO: No se pudo crear tarea programada (puede requerir admin)
)

echo.
echo ====================================================
echo  Instalacion completada
echo  La app iniciara automaticamente al encender la PC
echo.
echo  Para DESINSTALAR ejecutar: desinstalar_windows.bat
echo ====================================================
echo.
pause
