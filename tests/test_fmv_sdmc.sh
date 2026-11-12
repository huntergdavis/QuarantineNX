#!/usr/bin/env bash
# Run from repo root after building build/fmv-smoke; pass your own original AVI.
set -euo pipefail
if [ "$#" -ne 1 ]; then printf 'usage: %s /path/to/BQUAR1DK.AVI\n' "$0" >&2; exit 2; fi
movie=$(realpath "$1")
smoke=$(realpath build/fmv-smoke)
mkdir -p build
scratch=$(mktemp -d -p "$PWD/build" fmv-sdmc-XXXXXXXX)
trap 'python3 -c '\''import shutil,sys; shutil.rmtree(sys.argv[1])'\'' "$scratch"' EXIT
mkdir -p "$scratch/sdmc:/data" "$scratch/empty" "$scratch/build/fmv-logs"
ln -s "$movie" "$scratch/sdmc:/data/BQUAR1DK.AVI"
cd "$scratch"
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy "$smoke" 'sdmc:/data' "$scratch/empty"
python3 - <<'PY'
from pathlib import Path
logs = [p.read_text() for p in Path('build/fmv-logs').glob('fmv-diagnostic-*.log')]
assert any('local_open=ok errno=0 protocol_plain=unknown protocol_file=file' in log for log in logs)
print('local-open and protocol diagnostics verified')
PY
