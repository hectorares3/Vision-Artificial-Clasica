@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
echo Mide todas las piezas del dataset y genera CSV y gráficas en resultados\
echo.
%PY% src\medir_dataset.py
echo.
pause
