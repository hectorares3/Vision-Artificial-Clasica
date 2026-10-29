@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
echo Clic en las 4 esquinas de la hoja, pulsa una tecla, Enter si es A4 y marca la zona útil (solo tapete).
echo.
%PY% src\calibrar_escala.py
echo.
pause
