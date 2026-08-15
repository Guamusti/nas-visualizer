@echo off
REM Actualiza la app a la ultima version del repositorio (Windows)
cd /d "%~dp0"

where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] No se encontro git. Descarga el ZIP desde GitHub manualmente
  echo o instala git desde https://git-scm.com/download/win
  pause
  exit /b 1
)

echo Descargando la ultima version...
git fetch origin claude/nas-viewer-ai-features-rhfxb6
if errorlevel 1 (
  echo [ERROR] No se pudo conectar con GitHub. Revisa tu conexion.
  pause
  exit /b 1
)
git checkout claude/nas-viewer-ai-features-rhfxb6 2>nul
git pull origin claude/nas-viewer-ai-features-rhfxb6
if errorlevel 1 (
  echo [ERROR] No se pudo actualizar. Lee el mensaje de arriba.
  pause
  exit /b 1
)

echo.
echo Actualizado. Ejecuta run.bat para arrancar la app.
echo (Tu configuracion .env y tus fotos indexadas se conservan.)
pause
