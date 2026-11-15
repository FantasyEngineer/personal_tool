#!/usr/bin/env python3
"""生成应用图标和 macOS 菜单栏模板图标。"""

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(__file__).resolve().parent
ICON_PATH = BASE / "icon.png"
TRAY_PATH = BASE / "tray_template.png"
ICO_PATH = BASE / "icon.ico"
ICNS_PATH = BASE / "icon.icns"
SIZE = 1024
RENDER_SCALE = 4
INK = (31, 33, 37, 255)
PAPER = (248, 248, 246, 255)
TRANSPARENT = (0, 0, 0, 0)


def draw_toolbox(draw, scale, color, background, zoom=1.0, stroke=56):
    def point(value):
        return round(((value - SIZE / 2) * zoom + SIZE / 2) * scale)

    def box(left, top, right, bottom):
        return point(left), point(top), point(right), point(bottom)

    line_width = round(stroke * scale)

    draw.rounded_rectangle(
        box(210, 410, 814, 770),
        radius=round(68 * zoom * scale),
        outline=color,
        width=line_width,
    )

    # 给提手留出开口，避免箱体顶边穿过提手。
    draw.rectangle(box(355, 378, 669, 444), fill=background)
    handle = [(390, 438), (390, 360), (414, 300), (610, 300), (634, 360), (634, 438)]
    handle_points = [(point(x), point(y)) for x, y in handle]
    draw.line(handle_points, fill=color, width=line_width, joint="curve")
    cap_radius = line_width // 2
    for x, y in handle:
        cx, cy = point(x), point(y)
        draw.ellipse(
            (cx - cap_radius, cy - cap_radius, cx + cap_radius, cy + cap_radius),
            fill=color,
        )

    divider_y = point(585)
    draw.line(
        (point(252), divider_y, point(772), divider_y),
        fill=color,
        width=round(line_width * 0.72),
    )
    clasp = box(477, 548, 547, 635)
    draw.rounded_rectangle(
        clasp,
        radius=round(17 * zoom * scale),
        fill=color,
    )


def render_icon():
    scale = RENDER_SCALE
    image = Image.new("RGBA", (SIZE * scale, SIZE * scale), TRANSPARENT)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (40 * scale, 40 * scale, 984 * scale, 984 * scale),
        radius=220 * scale,
        fill=INK,
    )
    draw_toolbox(draw, scale, PAPER, INK)
    return image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def render_tray_icon():
    scale = RENDER_SCALE
    image = Image.new("RGBA", (SIZE * scale, SIZE * scale), TRANSPARENT)
    draw = ImageDraw.Draw(image)
    draw_toolbox(
        draw,
        scale,
        INK,
        TRANSPARENT,
        zoom=1.22,
        stroke=84,
    )
    return image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def make_ico(image):
    image.save(
        ICO_PATH,
        format="ICO",
        sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)],
    )


def make_icns(image):
    with tempfile.TemporaryDirectory(prefix="toolbox-iconset-") as temp_dir:
        iconset = Path(temp_dir) / "icon.iconset"
        iconset.mkdir()
        for size in (16, 32, 64, 128, 256, 512):
            image.resize((size, size), Image.Resampling.LANCZOS).save(
                iconset / f"icon_{size}x{size}.png"
            )
            if size <= 512:
                image.resize((size * 2, size * 2), Image.Resampling.LANCZOS).save(
                    iconset / f"icon_{size}x{size}@2x.png"
                )
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(ICNS_PATH)],
            check=True,
        )


def main():
    icon = render_icon()
    tray_icon = render_tray_icon()
    icon.save(ICON_PATH)
    tray_icon.save(TRAY_PATH)
    make_ico(icon)
    print(f"已生成 {ICON_PATH.name}、{TRAY_PATH.name} 和 {ICO_PATH.name}")
    if sys.platform == "darwin":
        make_icns(icon)
        print(f"已生成 {ICNS_PATH.name}")
    else:
        print("当前平台不是 macOS，跳过 .icns 生成。")


if __name__ == "__main__":
    main()
