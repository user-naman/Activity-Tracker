#!/usr/bin/env bash
# One-command setup for macOS / Linux. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"

say() { printf "\n\033[1m%s\033[0m\n" "$1"; }

say "1/4 Checking Python and ffmpeg"
PY=""
for c in python3.13 python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    PY="$c"; break
  fi
done
if ! command -v ffmpeg >/dev/null || [ -z "$PY" ]; then
  if command -v brew >/dev/null; then
    brew install python@3.12 ffmpeg
    PY="${PY:-python3.12}"
  else
    echo "Install Python 3.11+ and ffmpeg first."
    echo "  Mac: install Homebrew from https://brew.sh, then re-run this script."
    echo "  Linux: sudo apt install python3 python3-venv ffmpeg"
    exit 1
  fi
fi
echo "Python: $($PY --version)   ffmpeg: $(ffmpeg -version | head -1 | cut -d' ' -f3)"

say "2/4 Installing ClipForge (first time takes a few minutes)"
[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e ".[download,dev]"

say "3/4 Creating your config"
[ -f clipforge.toml ] && echo "clipforge.toml already exists, keeping it." || .venv/bin/clipforge init

say "4/4 Checking everything"
.venv/bin/clipforge doctor

say "Done. Start each session with:"
echo "  cd $(pwd) && source .venv/bin/activate"
