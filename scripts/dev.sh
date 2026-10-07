#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"
export AI_PN2_DATA_DIR="${AI_PN2_DATA_DIR:-$(dirname "$repo_dir")/ai-pn2-data}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$AI_PN2_DATA_DIR/cache}"
venv_dir="${AI_PN2_VENV:-$(dirname "$repo_dir")/ai-pn2-venv}"
case "${1:-web}" in
  web) export AI_PN2_DEBUG=1; exec "$venv_dir/bin/python" manage.py runserver 127.0.0.1:8000 --noreload ;;
  worker) exec "$venv_dir/bin/python" -u manage.py runworker ;;
  *) echo 'Usage: bash scripts/dev.sh web|worker' >&2; exit 2 ;;
esac
