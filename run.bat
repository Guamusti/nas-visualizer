@echo off
REM Arranque para Windows
cd /d "%~dp0backend"

if not exist ".venv\" (
  echo Creando entorno virtual de Python...
  python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Instalando dependencias...
python -m pip install -q --upgrade pip
pip install -q -r requirements.txt

if not exist ".env" (
  echo Creando .env desde la plantilla. EDITALO con los datos de tu NAS.
  copy .env.example .env
  echo.
  echo   Edita backend\.env con la IP, usuario y contrasena de tu NAS,
  echo   luego vuelve a ejecutar run.bat
  echo.
  pause
  exit /b 0
)

echo Arrancando NAS Visualizer en http://localhost:8000
python main.py
