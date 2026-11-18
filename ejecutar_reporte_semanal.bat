@echo off
REM Genera el reporte de los últimos 7 días y lo envía por correo.
REM Lo usa el Programador de tareas de Windows (ver README).
chcp 65001 >nul
cd /d "%~dp0"
if not exist salida mkdir salida
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" generar_reporte.py --ultimos-dias 7 --enviar >> salida\registro.log 2>&1
) else (
    python generar_reporte.py --ultimos-dias 7 --enviar >> salida\registro.log 2>&1
)
