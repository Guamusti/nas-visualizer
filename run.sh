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
