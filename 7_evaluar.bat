@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
echo Aciertos y errores: matrices de confusión y comparación de inventarios.
echo.
%PY% src\evaluar.py
echo.
pause
