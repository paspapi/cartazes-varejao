@echo off
setlocal

set "WSL_PROJECT_DIR=/home/anando/projects/cartazes-varejao"
set "WINDOWS_OUTPUT_DIR=\\wsl$\Ubuntu\home\anando\projects\cartazes-varejao\output"

wsl.exe bash -lc "cd \"%WSL_PROJECT_DIR%\" && if [ ! -f .venv/bin/activate ]; then echo Ambiente .venv nao encontrado em %WSL_PROJECT_DIR%/.venv; exit 1; fi && source .venv/bin/activate && python scripts/generate.py"

if exist "%WINDOWS_OUTPUT_DIR%" (
    start "" explorer.exe "%WINDOWS_OUTPUT_DIR%"
)

echo.
pause
