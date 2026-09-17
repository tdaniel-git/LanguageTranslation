#!/usr/bin/env bash
# One-command start: creates a venv, installs deps, launches the app.
set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
PORT="${PORT:-8000}"

if [ ! -d ".venv" ]; then
  echo "==> Creating virtual environment (.venv)"
  "$PYTHON" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Installing dependencies (first run only; this can take a few minutes)"
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt

echo "==> Starting NLLB Translator on http://localhost:${PORT}"
echo "    (First request downloads the model ~2.5GB — please be patient.)"
cd backend
PORT="$PORT" python app.py
