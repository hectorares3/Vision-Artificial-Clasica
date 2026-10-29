@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
echo Fotos de UNA clase de pieza (varias piezas iguales por foto, en posiciones y giros distintos).
echo Primero escribe aqui el nombre de la clase, p. ej. 2x4_rojo, y pulsa Enter.
echo Luego HAZ CLIC en la imagen de la camara para guardar cada foto (o pulsa s con esa ventana activa).
echo Antes de cada foto pulsa el numero de piezas que hay en el tapete (1-9).
echo.
%PY% src\captura.py --destino dataset
echo.
pause
