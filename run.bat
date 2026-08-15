@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0backend"

echo ============================================
echo    NAS Visualizer - Arranque (Windows)
echo ============================================
echo.

REM --- Detectar Python (py launcher o python) ---
set PYCMD=
where py >nul 2>nul && set PYCMD=py
if "!PYCMD!"=="" (
  where python >nul 2>nul && set PYCMD=python
)

if "!PYCMD!"=="" (
  echo [ERROR] No se encontro Python en este ordenador.
  echo.
  echo   1. Descargalo desde: https://www.python.org/downloads/
  echo   2. Durante la instalacion MARCA la casilla "Add Python to PATH".
  echo   3. Cierra esta ventana y vuelve a ejecutar run.bat
  echo.
  pause
  exit /b 1
)

echo Python detectado con el comando: !PYCMD!
!PYCMD! --version
echo.

REM --- Crear entorno virtual ---
if not exist ".venv\" (
  echo Creando entorno virtual de Python...
  !PYCMD! -m venv .venv
  if errorlevel 1 (
    echo [ERROR] No se pudo crear el entorno virtual.
    pause
    exit /b 1
  )
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo [ERROR] No se pudo activar el entorno virtual.
  pause
  exit /b 1
)

echo Instalando dependencias (la primera vez puede tardar unos minutos)...
python -m pip install --upgrade pip >nul 2>nul
pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [ERROR] Fallo instalando las dependencias. Lee el mensaje de arriba.
  pause
  exit /b 1
)

REM --- Soporte RAW (opcional): si falla, la app sigue funcionando ---
echo Instalando soporte RAW (opcional)...
pip install "rawpy>=0.24" >nul 2>nul
if errorlevel 1 (
  echo   [AVISO] No se pudo instalar rawpy en esta version de Python.
  echo   Los RAW conservaran fecha/GPS/lugar, pero sin miniatura previa.
  echo   Consejo: usa Python 3.12 para soporte RAW completo.
) else (
  echo   Soporte RAW instalado correctamente.
)
echo.

REM --- Configuracion .env ---
if not exist ".env" (
  copy .env.example .env >nul
  echo ============================================
  echo    ACCION NECESARIA - Configura tu NAS
  echo ============================================
  echo.
  echo Se ha creado el archivo de configuracion:
  echo    %cd%\.env
  echo.
  echo Abrelo con el Bloc de notas y pon la IP, usuario, contrasena
  echo y la carpeta de tu NAS. Luego vuelve a ejecutar run.bat
  echo.
  pause
  exit /b 0
)

echo ============================================
echo    Arrancando el servidor...
echo ============================================
echo.
echo   Abre en el navegador:  http://localhost:8000
echo   Para detener el servidor: pulsa Ctrl+C
echo   (NO cierres esta ventana mientras uses la app)
echo.
python main.py

echo.
echo El servidor se ha detenido.
pause
