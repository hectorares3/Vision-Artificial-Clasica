@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
echo Instala las librerías necesarias (solo la primera vez)
echo.
%PY% -m pip install -r requirements.txt
echo.
pause
