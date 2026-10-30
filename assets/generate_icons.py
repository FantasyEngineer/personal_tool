#!/usr/bin/env python3
"""Generate app icons (icon.ico + icon.icns) from a single master PNG.

Put a square master image at assets/icon.png (recommended 1024x1024), then run:

    python assets/generate_icons.py

Outputs next to this script:
  - icon.ico   (Windows, multi-resolution 16-256px)
  - icon.icns  (macOS, built with sips + iconutil; only on macOS)

Commit both files so GitHub Actions can embed them without needing Pillow/PyQt
to regenerate icons at build time.
"""

import os
import subprocess
import sys

from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(BASE, "icon.png")
ICO_PATH = os.path.join(BASE, "icon.ico")
ICNS_PATH = os.path.join(BASE, "icon.icns")
ICNS_SIZES = [16, 32, 64, 128, 256, 512, 1024]


def make_ico():
    img = Image.open(MASTER).convert("RGBA")
    img.save(ICO_PATH, format="ICO", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    print("wrote", ICO_PATH)


def make_icns():
    iconset = os.path.join(BASE, "icon.iconset")
    os.makedirs(iconset, exist_ok=True)
    for size in ICNS_SIZES:
        out = os.path.join(iconset, f"icon_{size}x{size}.png")
        out2x = os.path.join(iconset, f"icon_{size}x{size}@2x.png")
        subprocess.run(["sips", "-z", str(size), str(size), MASTER, "--out", out],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if size <= 512:
            subprocess.run(["sips", "-z", str(size * 2), str(size * 2), MASTER, "--out", out2x],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["iconutil", "-c", "icns", iconset, "-o", ICNS_PATH], check=True)
    print("wrote", ICNS_PATH)


def main():
    if not os.path.exists(MASTER):
        sys.exit("ERROR: assets/icon.png not found. Add a square master icon first.")
    make_ico()
    if sys.platform == "darwin":
        make_icns()
    else:
        print("Skipping .icns generation (needs macOS). Run this script on a Mac for icon.icns.")


if __name__ == "__main__":
    main()
