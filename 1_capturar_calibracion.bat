@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
echo Ajusta antes luz, exposición (+/-) y ganancia (a/d): tapete vacío con luz ~80-120. k guarda los ajustes.
echo Tapete VACÍO: pulsa f (fondo, varias fotos). Con una hoja A4 plana: pulsa r. q para salir.
echo.
%PY% src\captura.py --destino calibracion
echo.
pause
