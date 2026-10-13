#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Ambiente virtual nao encontrado em .venv/"
  echo "Crie com:"
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  python -m pip install -r requirements.txt"
  exit 1
fi

cd "$ROOT_DIR"
"$VENV_PYTHON" scripts/generate.py "$@"
