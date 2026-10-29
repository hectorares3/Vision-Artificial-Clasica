@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
echo Sistema completo con la cámara. ESPACIO congela, s guarda, q sale.
echo Con el tapete VACÍO, b recaptura el fondo (hazlo al empezar).
echo.
%PY% src\detectar.py --camara --debug
echo.
pause
