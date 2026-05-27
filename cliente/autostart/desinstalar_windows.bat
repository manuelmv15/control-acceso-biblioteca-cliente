@echo off
echo Desinstalando Biblioteca Kiosko autostart...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "BibliotecaKiosko" /f >nul 2>&1
schtasks /delete /tn "BibliotecaKiosko" /f >nul 2>&1
echo Listo.
pause
