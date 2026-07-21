"""Flat metro-map style specimen sheet (small preview).

One page: real cropped network sample (5+ stations around a transfer),
symbol specimens, colour normalisation. Flat only: no grain, no shadows,
no gradients.
"""

from __future__ import annotations

import colorsys
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SS = 2
FW, FH = 1280, 1600  # final size, long edge <= 1600
W, H = FW * SS, FH * SS

BG = "#FAFAF7"
TXT = "#1A1A1A"
SUB = "#8A8A8A"
INACT = "#D8D8D4"
UC = "#B8B8B4"
GUIDE = "#DEDEDA"

CJK = "/usr/share/fonts/adobe-source-han-sans/SourceHanSansCN-Regular.otf"
CJK_M = "/usr/share/fonts/adobe-source-han-sans/SourceHanSansCN-Medium.otf"
LATIN = "/home/small-hsn/.agents/skills/canvas-design/canvas-fonts/GeistMono-Regular.ttf"

LIB = Path(__file__).resolve().parent.parent / "library" / "gz"
MARGIN = int(W * 0.055)
LW = 14 * SS  # line width W in the demo


def hx(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def normalize_line_color(c: str) -> str:
    r, g, b = (v / 255 for v in hx(c))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    s = min(max(s, 0.55), 0.85)
    l = min(max(l, 0.38), 0.58)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


# ---------------------------------------------------------------- data crop


def load_gz() -> tuple[dict, dict]:
    stations: dict[str, dict] = {}
    for f in (LIB / "stations").glob("*.json"):
        stations.update(json.loads(f.read_text())["stations"])
    lines: dict[str, dict] = {}
    for f in (LIB / "lines").glob("*.json"):
        lines.update(json.loads(f.read_text())["lines"])
    return stations, lines


def crop_around(center_id: str, reach: int = 2) -> tuple[dict[str, list[str]], set[str]]:
    """Per-line ordered station-id windows of +-reach around the centre."""
    windows: dict[str, list[str]] = {}
    used: set[str] = set()
    for lid in STATIONS[center_id]["lines"]:
        order = [
            e["id"]
            for e in LINES[lid]["stations"]
            if e.get("status") != "planned" and e["id"] in STATIONS
        ]
        i = order.index(center_id)
        win = order[max(0, i - reach) : i + reach + 1]
        windows[lid] = win
        used.update(win)
    return windows, used


STATIONS, LINES = load_gz()
WINDOWS, USED = crop_around("109")  # 公园前: lines 1 x 2

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

f_h1 = ImageFont.truetype(CJK_M, 30 * SS)
f_cap = ImageFont.truetype(LATIN, 15 * SS)
f_sec = ImageFont.truetype(CJK_M, 19 * SS)
f_zh = ImageFont.truetype(CJK, 16 * SS)
f_zh_m = ImageFont.truetype(CJK_M, 16 * SS)
f_en = ImageFont.truetype(LATIN, 9 * SS)
f_note = ImageFont.truetype(CJK, 14 * SS)


# ---------------------------------------------------------------- draw helpers


def rline(p0, p1, color, width=LW):
    d.line([p0, p1], fill=color, width=width)
    r = width / 2
    for p in (p0, p1):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=color)


def tick(p, angle_deg, color):
    a = math.radians(angle_deg)
    nx, ny = -math.sin(a), math.cos(a)
    r0, r1 = LW * 0.5, LW * 1.0
    d.line(
        [(p[0] + nx * r0, p[1] + ny * r0), (p[0] + nx * r1, p[1] + ny * r1)],
        fill=color,
        width=max(2, int(LW * 0.18)),
    )


def transfer_ring(p):
    r = LW * 0.55
    w = max(2, int(LW * 0.16))
    d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=BG, outline=TXT, width=w)


def stadium(p0, p1):
    """Long-transfer capsule between two points (axis-aligned)."""
    r = LW * 0.55
    w = max(2, int(LW * 0.16))
    x0, x1 = min(p0[0], p1[0]) - r, max(p0[0], p1[0]) + r
    y0, y1 = min(p0[1], p1[1]) - r, max(p0[1], p1[1]) + r
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=BG, outline=TXT, width=w)


def dashed(p0, p1, color, width, dash=12 * SS, gap=8 * SS):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    dist = math.hypot(dx, dy)
    ux, uy = dx / dist, dy / dist
    t = 0.0
    while t < dist:
        t2 = min(t + dash, dist)
        d.line(
            [(p0[0] + ux * t, p0[1] + uy * t), (p0[0] + ux * t2, p0[1] + uy * t2)],
            fill=color,
            width=width,
        )
        t = t2 + gap


def sec_title(y, zh, en):
    d.text((MARGIN, y), zh, font=f_sec, fill=TXT, anchor="lm")
    d.text((W - MARGIN, y), en, font=f_cap, fill=SUB, anchor="rm")
    d.line([(MARGIN, y + 26 * SS), (W - MARGIN, y + 26 * SS)], fill=GUIDE, width=SS)


# ---------------------------------------------------------------- header

y = MARGIN
d.text((MARGIN, y), "扁平制图 · 风格样张", font=f_h1, fill=TXT, anchor="la")
d.text((W - MARGIN, y + 12 * SS), "SPEC 01", font=f_cap, fill=SUB, anchor="ra")
d.text((MARGIN, y + 48 * SS), "实用 · 地铁图 · 简约", font=f_note, fill=SUB, anchor="la")

# ---------------------------------------------------------------- real crop demo

y0 = y + 120 * SS
sec_title(y0, "真实裁片 · 公园前 ±2 站", "library/gz crop · normalized colors")

# fit crop coordinates into a box
box_x0, box_y0 = MARGIN + LW * 4, y0 + 90 * SS
box_x1, box_y1 = W - MARGIN - LW * 4, y0 + 560 * SS
xs = [STATIONS[s]["x"] for s in USED]
ys = [STATIONS[s]["y"] for s in USED]
x_min, x_max, y_min, y_max = min(xs), max(xs), min(ys), max(ys)
scale = min((box_x1 - box_x0) / (x_max - x_min), (box_y1 - box_y0) / (y_max - y_min))
ox = (box_x0 + box_x1) / 2 - (x_min + x_max) / 2 * scale
oy = (box_y0 + box_y1) / 2 + (y_min + y_max) / 2 * scale


def to_px(sid: str) -> tuple[float, float]:
    s = STATIONS[sid]
    return (ox + s["x"] * scale, oy - s["y"] * scale)


line_colors = {lid: normalize_line_color(LINES[lid]["color"]) for lid in WINDOWS}

# lines first
for lid, win in WINDOWS.items():
    pts = [to_px(s) for s in win]
    for p0, p1 in zip(pts, pts[1:]):
        rline(p0, p1, line_colors[lid])

# station ticks on top
for lid, win in WINDOWS.items():
    pts = [to_px(s) for s in win]
    for i, sid in enumerate(win):
        st = STATIONS[sid]
        p = pts[i]
        if st.get("isTransfer"):
            continue
        q = pts[i + 1] if i + 1 < len(pts) else pts[i - 1]
        ang = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))
        tick(p, ang, line_colors[lid])

# rings for every transfer station in the crop (once each)
drawn: set[str] = set()
for lid, win in WINDOWS.items():
    for sid in win:
        if STATIONS[sid].get("isTransfer") and sid not in drawn:
            transfer_ring(to_px(sid))
            drawn.add(sid)


# labels: horizontal segments -> below the point; vertical -> beside it
def local_dir(sid: str) -> str:
    for lid, win in WINDOWS.items():
        if sid in win:
            i = win.index(sid)
            q = win[i + 1] if i + 1 < len(win) else win[i - 1]
            px, py = to_px(sid)
            qx, qy = to_px(q)
            return "v" if abs(qy - py) > abs(qx - px) else "h"
    return "h"


for sid in sorted(USED):
    st = STATIONS[sid]
    p = to_px(sid)
    zh = st["name"]["zh-CN"]
    en = st["name"].get("en-US", "")
    medium = bool(st.get("isTransfer"))
    f_main = f_zh_m if medium else f_zh
    if sid == "109":  # crossing: tuck into the upper-left quadrant
        d.text((p[0] - LW * 1.2, p[1] - LW * 2.6), zh, font=f_zh_m, fill=TXT, anchor="rs")
        d.text((p[0] - LW * 1.2, p[1] - LW * 1.4), en.upper(), font=f_en, fill=SUB, anchor="rs")
    elif local_dir(sid) == "v":
        d.text((p[0] + LW * 1.3, p[1] - 12 * SS), zh, font=f_main, fill=TXT, anchor="lm")
        d.text((p[0] + LW * 1.3, p[1] + 12 * SS), en.upper(), font=f_en, fill=SUB, anchor="lm")
    else:
        d.text((p[0], p[1] + LW * 1.1), zh, font=f_main, fill=TXT, anchor="ma")
        d.text((p[0], p[1] + LW * 1.1 + 24 * SS), en.upper(), font=f_en, fill=SUB, anchor="ma")

# minimal legend, no box
ly = box_y1 + 40 * SS
lx = MARGIN
for lid in WINDOWS:
    d.rectangle([lx, ly - 6 * SS, lx + 34 * SS, ly + 6 * SS], fill=line_colors[lid])
    name = LINES[lid]["name"]["zh-CN"]
    d.text((lx + 44 * SS, ly), name, font=f_note, fill=TXT, anchor="lm")
    lx += 44 * SS + int(d.textlength(name, font=f_note)) + 40 * SS

# ---------------------------------------------------------------- symbols

y1 = ly + 60 * SS
sec_title(y1, "符号规格", "symbols · W = line width")

sy = y1 + 100 * SS
items_x = [MARGIN + LW * 3, W * 0.31, W * 0.56, W * 0.81]
C_A = line_colors[list(WINDOWS)[0]]
C_B = line_colors[list(WINDOWS)[1]] if len(WINDOWS) > 1 else "#4a7a8c"
gap = LW * 0.15

rline((items_x[0] - LW * 2.2, sy), (items_x[0] + LW * 2.2, sy), C_B)
tick((items_x[0], sy), 0, C_B)
d.text((items_x[0], sy + LW * 2.2), "普通站 tick 0.5W", font=f_note, fill=SUB, anchor="ma")

rline((items_x[1] - LW * 2.2, sy), (items_x[1] + LW * 2.2, sy), C_A)
transfer_ring((items_x[1], sy))
d.text((items_x[1], sy + LW * 2.2), "换乘环 r 0.55W", font=f_note, fill=SUB, anchor="ma")

rline((items_x[2] - LW * 2.2, sy - LW * 0.9), (items_x[2] + LW * 2.2, sy - LW * 0.9), C_A)
rline((items_x[2] - LW * 2.2, sy + LW * 0.9), (items_x[2] + LW * 2.2, sy + LW * 0.9), C_B)
stadium((items_x[2], sy - LW * 0.9), (items_x[2], sy + LW * 0.9))
d.text((items_x[2], sy + LW * 2.2), "长换乘 胶囊", font=f_note, fill=SUB, anchor="ma")

d.line([(items_x[3] - LW * 2.2, sy - LW * 0.5 - gap / 2), (items_x[3] + LW * 2.2, sy - LW * 0.5 - gap / 2)], fill=C_A, width=LW)
d.line([(items_x[3] - LW * 2.2, sy + LW * 0.5 + gap / 2), (items_x[3] + LW * 2.2, sy + LW * 0.5 + gap / 2)], fill=C_B, width=LW)
d.text((items_x[3], sy + LW * 2.2), "共线缝 0.15W", font=f_note, fill=SUB, anchor="ma")

# under-construction dash specimen
dy2 = sy + 90 * SS
dashed((MARGIN + LW, dy2), (MARGIN + LW * 9, dy2), UC, LW // 2)
d.text((MARGIN + LW * 10, dy2), "在建 · 灰阶虚线", font=f_note, fill=SUB, anchor="lm")

# ---------------------------------------------------------------- colours

y2 = dy2 + 70 * SS
sec_title(y2, "线路色归一化", "S 55–85 · L 38–58")

GZ_SAMPLE = [("1", "#edcf3b"), ("2", "#00679e"), ("5", "#c70541"), ("11", "#F5BB17"), ("21", "#230b55"), ("GF", "#bbd80a")]
swy = y2 + 80 * SS
col_w = (W - 2 * MARGIN - 5 * 24 * SS) / 6
for i, (lid, c) in enumerate(GZ_SAMPLE):
    x = MARGIN + i * (col_w + 24 * SS)
    n = normalize_line_color(c)
    d.rectangle([x, swy, x + col_w, swy + 30 * SS], fill=c)
    d.rectangle([x, swy + 38 * SS, x + col_w, swy + 68 * SS], fill=n)
    d.text((x, swy - 12 * SS), lid, font=f_cap, fill=TXT, anchor="ls")
    d.text((x + col_w, swy + 86 * SS), n.upper(), font=f_en, fill=SUB, anchor="ra")

gy = swy + 130 * SS
grays = [("文字", TXT), ("副文", SUB), ("规划", INACT), ("在建", UC), ("辅助", GUIDE)]
gw = (W - 2 * MARGIN - 4 * 24 * SS) / 5
for i, (name, c) in enumerate(grays):
    x = MARGIN + i * (gw + 24 * SS)
    d.rectangle([x, gy, x + gw, gy + 26 * SS], fill=c)
    d.text((x, gy + 38 * SS), f"{name}  {c.upper()}", font=f_note, fill=SUB, anchor="la")

# footer
d.text((MARGIN, H - MARGIN), "无网格 · 无阴影 · 无渐变 · 徽章默认关闭", font=f_note, fill=SUB, anchor="ls")
d.text((W - MARGIN, H - MARGIN), "preview ≤ 1600px", font=f_cap, fill=SUB, anchor="rs")

out = img.resize((FW, FH), Image.LANCZOS)
out_path = Path(__file__).resolve().parent / "style_spec_01.png"
out.save(out_path)
print("saved", out_path, out.size)
