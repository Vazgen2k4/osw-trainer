#!/bin/sh
# macOS / Linux launcher: finds a suitable Python 3 and hands over to start.py (which does the real work).
#   ./start.sh                 start the trainer (first run installs everything into .venv/)
#   ./start.sh --port 8800     any option of start.py / the trainer
set -e
cd "$(dirname "$0")"

# prefer versions that Morph-KGC's dependencies (pandas, duckdb) publish wheels for
for py in python3.13 python3.12 python3.11 python3.10 python3 python; do
  if command -v "$py" >/dev/null 2>&1 &&
     "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    exec "$py" start.py "$@"
  fi
done

echo "Python 3.10 or newer is required." >&2
echo "  macOS:          brew install python   (or https://www.python.org/downloads/)" >&2
echo "  Ubuntu/Debian:  sudo apt install python3 python3-venv" >&2
echo "  Fedora:         sudo dnf install python3" >&2
exit 1
