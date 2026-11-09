#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
if [ ! -x "$root/.venv/bin/freemocap" ]; then
    echo 'Run uv sync --frozen --python 3.12 in the repository first.' >&2
    exit 1
fi
# Upstream's launcher kills an occupied default port. Refuse before launching.
"$root/.venv/bin/python" - <<'PY'
import socket
with socket.socket() as s:
    if s.connect_ex(('127.0.0.1',53117)) == 0:
        raise SystemExit('Port 53117 is busy. Close the existing FreeMoCap server first.')
PY
state="$root/.mujina-data"
mkdir -p "$state/electron"
"$root/.venv/bin/python" - "$state" <<'PY'
import json,sys
from pathlib import Path
state=Path(sys.argv[1]);config=state/'electron'/'freemocap-config.json'
if not config.exists():config.write_text(json.dumps({'baseDataFolder':str(state/'recordings-data')}))
PY
export FREEMOCAP_SERVER_EXECUTABLE="$root/.venv/bin/freemocap"
export FREEMOCAP_USER_DATA_DIR="$state/electron"
cd "$root/freemocap-ui"
exec npm run dev -- --host 127.0.0.1
