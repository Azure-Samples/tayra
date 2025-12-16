#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$PROJECT_ROOT"

if [ -f "../../infra/scripts/set-env.sh" ]; then
  echo "Loading environment variables from infra/scripts/set-env.sh"
  # shellcheck disable=SC1091
  source "../../infra/scripts/set-env.sh"
fi

exec uvicorn classification_engine.app.main:app --host 0.0.0.0 --port 8000 --reload
