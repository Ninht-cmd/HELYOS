#!/usr/bin/env bash
# Script de développement HELYOS (Git Bash / Linux / macOS).
# Commandes : setup | test | run | up | up-all | down
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KERNEL="$ROOT/apps/jarvis-kernel"
SRC="$KERNEL/src"
TESTS="$KERNEL/tests"
VENV="$ROOT/.venv"
COMPOSE="$ROOT/deploy/docker-compose.yml"

py() {
  if [ -x "$VENV/bin/python" ]; then echo "$VENV/bin/python";
  elif [ -x "$VENV/Scripts/python.exe" ]; then echo "$VENV/Scripts/python.exe";
  else echo "python"; fi
}

cmd="${1:-test}"
case "$cmd" in
  setup)
    python -m venv "$VENV"
    "$(py)" -m pip install --upgrade pip
    "$(py)" -m pip install -e "$KERNEL[server,dev]"
    echo "OK -> ./scripts/dev.sh test"
    ;;
  test)
    PYTHONPATH="$SRC" "$(py)" -m unittest discover -s "$TESTS" -t "$KERNEL" -v
    ;;
  run)
    PYTHONPATH="$SRC" "$(py)" -m jarvis_kernel
    ;;
  up)      docker compose -f "$COMPOSE" --profile core up -d ;;
  up-all)  docker compose -f "$COMPOSE" --profile all up -d ;;
  down)    docker compose -f "$COMPOSE" --profile all down ;;
  *) echo "Commande inconnue: $cmd (setup|test|run|up|up-all|down)"; exit 1 ;;
esac
