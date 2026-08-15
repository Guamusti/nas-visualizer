#!/usr/bin/env bash
# Arranque para macOS / Linux
set -e
cd "$(dirname "$0")/backend"

if [ ! -d ".venv" ]; then
  echo "→ Creando entorno virtual de Python..."
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "→ Instalando dependencias..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "→ Instalando soporte RAW (opcional)..."
if pip install -q rawpy==0.23.2 2>/dev/null; then
  echo "  ✓ Soporte RAW instalado"
else
  echo "  ⚠️  rawpy no disponible en esta versión de Python."
  echo "     Los RAW conservarán fecha/GPS/lugar, pero sin miniatura previa."
  echo "     Consejo: usa Python 3.12 para soporte RAW completo."
fi

if [ ! -f ".env" ]; then
  echo "→ Creando .env desde la plantilla. EDÍTALO con los datos de tu NAS."
  cp .env.example .env
  echo ""
  echo "  ⚠️  Edita backend/.env con la IP, usuario y contraseña de tu NAS,"
  echo "      luego vuelve a ejecutar ./run.sh"
  echo ""
  exit 0
fi

echo "→ Arrancando NAS Visualizer en http://localhost:8000"
python main.py
