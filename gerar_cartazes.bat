@echo off
rem Gera os cartazes no Windows (Python nativo, sem WSL).
rem Na primeira vez cria .venv e instala o PyMuPDF.
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Criando .venv...
    py -3 -m venv .venv || goto :erro
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :erro
)

".venv\Scripts\python.exe" scripts\generate.py %* || goto :erro
start "" explorer.exe "%~dp0output"
pause
exit /b 0

:erro
echo.
echo Erro. Verifique se o Python 3 esta instalado: winget install Python.Python.3.12
pause
exit /b 1
