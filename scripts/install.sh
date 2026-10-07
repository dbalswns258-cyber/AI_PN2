#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"
export AI_PN2_DATA_DIR="${AI_PN2_DATA_DIR:-$(dirname "$repo_dir")/ai-pn2-data}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$AI_PN2_DATA_DIR/cache}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$AI_PN2_DATA_DIR/cache/pip}"
venv_dir="${AI_PN2_VENV:-$(dirname "$repo_dir")/ai-pn2-venv}"
if [ ! -x "$venv_dir/bin/python" ]; then
  python3 -m venv "$venv_dir"
fi
"$venv_dir/bin/python" -m pip install --requirement requirements.txt
"$venv_dir/bin/python" -m pip check
"$venv_dir/bin/python" scripts/prepare_data.py
"$venv_dir/bin/python" manage.py migrate --noinput
"$venv_dir/bin/python" manage.py check
