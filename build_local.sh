#!/usr/bin/env bash
# Local one-shot build for the current machine.
# GitHub Actions does the same thing for BOTH macOS and Windows; run this only
# if you want a package for the OS you are on right now.
set -euo pipefail

cd "$(dirname "$0")"

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# Generate icons if a master PNG exists but the outputs are missing.
if [ -f assets/icon.png ]; then
  [ -f assets/icon.ico ] || python assets/generate_icons.py
fi

pyinstaller --noconfirm toolbox.spec

echo
echo "Done. Bundle is in ./dist/Toolbox/"
