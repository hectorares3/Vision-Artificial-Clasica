@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
echo Fotos de escenas mezcladas para evaluar. s para guardar. Luego escribe a mano el .real.json de cada una.
echo.
%PY% src\captura.py --destino pruebas
echo.
pause
