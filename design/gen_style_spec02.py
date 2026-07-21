"""SPEC 02 — bundling & station symbols, real 4/12 university corridor.

Demonstrates: gap stations, seam slot, bundle transfer capsules,
diagonal bundle entry aiming at own slot, concentric corners.
Flat only. Small preview output.
"""

from __future__ import annotations

import colorsys
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SS = 2
FW, FH = 1280, 1600
W_, H_ = FW * SS, FH * SS

BG = "#FAFAF7"
TXT = "#1A1A1A"
SUB = "#8A8A8A"
GUIDE = "#DEDEDA"

CJK = "/usr/share/fonts/adobe-source-han-sans/SourceHanSansCN-Regular.otf"
CJK_M = "/usr/share/fonts/adobe-source-han-sans/SourceHanSansCN-Medium.otf"
LATIN = "/home/small-hsn/.agents/skills/canvas-design/canvas-fonts/GeistMono-Regular.ttf"

LIB = Path(__file__).resolve().parent.parent / "library" / "gz"
MARGIN = int(W_ * 0.055)
LW = 14 * SS  # line width W
GAP = LW * 0.15  # bundle seam
OFF = LW + GAP  # centre distance between bundle strokes
R_RING = LW * 0.55
W_RING = max(2, int(LW * 0.16))
R_CORNER = LW * 1.25
GAP_ST = LW * 0.35  # normal-station cut width


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


def load_gz() -> tuple[dict, dict]:
    stations: dict[str, dict] = {}
    for f in (LIB / "stations").glob("*.json"):
        stations.update(json.loads(f.read_text())["stations"])
    lines: dict[str, dict] = {}
    for f in (LIB / "lines").glob("*.json"):
        lines.update(json.loads(f.read_text())["lines"])
    return stations, lines


STATIONS, LINES = load_gz()
C4 = normalize_line_color(LINES["4"]["color"])
C12 = normalize_line_color(LINES["12"]["color"])
C7 = normalize_line_color(LINES["7"]["color"])

img = Image.new("RGB", (W_, H_), BG)
d = ImageDraw.Draw(img)

f_h1 = ImageFont.truetype(CJK_M, 30 * SS)
f_cap = ImageFont.truetype(LATIN, 15 * SS)
f_sec = ImageFont.truetype(CJK_M, 19 * SS)
f_zh = ImageFont.truetype(CJK, 16 * SS)
f_zh_m = ImageFont.truetype(CJK_M, 16 * SS)
f_en = ImageFont.truetype(LATIN, 9 * SS)
f_note = ImageFont.truetype(CJK, 14 * SS)

# ---------------------------------------------------------------- helpers


def fillet_path(pts: list[tuple[float, float]], r: float, n: int = 24) -> list[tuple[float, float]]:
    """Polyline with circular fillets at interior vertices."""
    out: list[tuple[float, float]] = [pts[0]]
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
        v1 = (p1[0] - p0[0], p1[1] - p0[1])
        v2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1, l2 = math.hypot(*v1), math.hypot(*v2)
        u1 = (v1[0] / l1, v1[1] / l1)
        u2 = (v2[0] / l2, v2[1] / l2)
        ang = math.acos(max(-1, min(1, u1[0] * u2[0] + u1[1] * u2[1])))
        if ang < 1e-3:
            out.append(p1)
            continue
        t = min(r * math.tan(ang / 2), l1 * 0.45, l2 * 0.45)
        a = (p1[0] - u1[0] * t, p1[1] - u1[1] * t)
        b = (p1[0] + u2[0] * t, p1[1] + u2[1] * t)
        out.append(a)
        for k in range(1, n):
            s = k / n
            # quadratic bezier approximates the small arc well enough at 45/90 deg
            x = (1 - s) ** 2 * a[0] + 2 * (1 - s) * s * p1[0] + s**2 * b[0]
            y = (1 - s) ** 2 * a[1] + 2 * (1 - s) * s * p1[1] + s**2 * b[1]
            out.append((x, y))
        out.append(b)
    out.append(pts[-1])
    return out


def stroke(pts: list[tuple[float, float]], color: str, width: int = LW) -> None:
    d.line(pts, fill=color, width=width, joint="curve")


def gap_station(p: tuple[float, float], dir_deg: float, breadth: float = LW * 0.55) -> None:
    """Centred white slot inside the stroke; outer edges stay solid."""
    a = math.radians(dir_deg)
    nx, ny = -math.sin(a), math.cos(a)
    h = breadth / 2
    d.line(
        [(p[0] - nx * h, p[1] - ny * h), (p[0] + nx * h, p[1] + ny * h)],
        fill=BG,
        width=int(GAP_ST),
    )


def seam_slot(p: tuple[float, float], dir_deg: float) -> None:
    """Bundle normal station: slot on the seam, outer edges stay solid."""
    a = math.radians(dir_deg)
    nx, ny = -math.sin(a), math.cos(a)
    h = (GAP + LW) / 2  # eats half of each stroke
    d.line(
        [(p[0] - nx * h, p[1] - ny * h), (p[0] + nx * h, p[1] + ny * h)],
        fill=BG,
        width=int(GAP_ST),
    )


def ring(p: tuple[float, float]) -> None:
    d.ellipse(
        [p[0] - R_RING, p[1] - R_RING, p[0] + R_RING, p[1] + R_RING],
        fill=BG,
        outline=TXT,
        width=W_RING,
    )


def capsule(p0: tuple[float, float], p1: tuple[float, float]) -> None:
    x0, x1 = min(p0[0], p1[0]) - R_RING, max(p0[0], p1[0]) + R_RING
    y0, y1 = min(p0[1], p1[1]) - R_RING, max(p0[1], p1[1]) + R_RING
    d.rounded_rectangle([x0, y0, x1, y1], radius=R_RING, fill=BG, outline=TXT, width=W_RING)


def sec_title(y: float, zh: str, en: str) -> None:
    d.text((MARGIN, y), zh, font=f_sec, fill=TXT, anchor="lm")
    d.text((W_ - MARGIN, y), en, font=f_cap, fill=SUB, anchor="rm")
    d.line([(MARGIN, y + 26 * SS), (W_ - MARGIN, y + 26 * SS)], fill=GUIDE, width=SS)


def name_of(sid: str) -> tuple[str, str]:
    n = STATIONS[sid]["name"]
    return n["zh-CN"], n.get("en-US", "").upper()


# ---------------------------------------------------------------- header

y = MARGIN
d.text((MARGIN, y), "并线与站符 · 风格样张", font=f_h1, fill=TXT, anchor="la")
d.text((W_ - MARGIN, y + 12 * SS), "SPEC 02", font=f_cap, fill=SUB, anchor="ra")
d.text((MARGIN, y + 48 * SS), "4/12 大学城段 · 真实数据 · 画布层并线", font=f_note, fill=SUB, anchor="la")

y0 = y + 110 * SS
sec_title(y0, "线网裁片", "bundling · gap stations · capsules")

# ---------------------------------------------------------------- world mapping

# world crop: x 1000..1400, y 250..720 (screen y = world y, no flip)
bx0, by0 = MARGIN, y0 + 60 * SS
bx1, by1 = W_ - MARGIN, y0 + 900 * SS
sc = min((bx1 - bx0) / 400.0, (by1 - by0) / 470.0)
ox_ = (bx0 + bx1) / 2 - (1000 + 1400) / 2 * sc
oy_ = (by0 + by1) / 2 - (250 + 720) / 2 * sc


def P(x: float, yv: float) -> tuple[float, float]:
    return (ox_ + x * sc, oy_ + yv * sc)


X4 = P(1225, 0)[0]  # line 4 keeps its original alignment
XS = X4 - OFF  # line 12 slot, west side

# ---------------------------------------------------------------- strokes

# line 7 crossing (under everything)
p7 = fillet_path(
    [P(1137, 688), P(1175, 650), P(1225, 600), P(1350, 475), P(1388, 437)],
    R_CORNER,
)
stroke(p7, C7)

# line 4: vertical trunk, corner at 418 to 45 deg
p4 = fillet_path(
    [(X4, P(0, 250)[1]), (X4, P(0, 600)[1]), P(1300, 675), P(1330, 705)],
    R_CORNER,
)
stroke(p4, C4)

# line 12: west approach, diagonal entry aiming at own slot, terminus at 418
y400 = P(0, 400)[1]
ya = P(0, 450)[1] - LW * 1.7  # finish merging just above Guanzhou
xk = XS - (ya - y400)  # 45 deg approach start
p12 = fillet_path(
    [P(1000, 400), (xk, y400), (XS, ya), (XS, P(0, 600)[1])],
    R_CORNER,
)
stroke(p12, C12)

# ---------------------------------------------------------------- stations

# normal gap stations
gap_station(P(1050, 400), 0)  # 赤沙北
gap_station(P(1150, 400), 0)  # 北山
gap_station(P(1275, 650), 45)  # 新造
gap_station(P(1300, 675), 45)  # 官桥
gap_station(P(1175, 650), -45)  # 板桥 (line 7)
gap_station(P(1350, 475), -45)  # 深井 (line 7)

# single transfers (other lines out of crop)
ring((X4, P(0, 275)[1]))  # 车陂南 4/5
ring((X4, P(0, 350)[1]))  # 万胜围 4/8
ring(P(1100, 400))  # 赤沙 11/12

# bundle transfer capsules across both strokes
for yv in (450, 525, 600):
    capsule((XS, P(0, yv)[1]), (X4, P(0, yv)[1]))

# ---------------------------------------------------------------- labels

lab_x = X4 + R_RING + LW * 0.9


def label_r(yv: float, zh: str, en: str, medium: bool = True) -> None:
    d.text((lab_x, yv - 11 * SS), zh, font=f_zh_m if medium else f_zh, fill=TXT, anchor="lm")
    d.text((lab_x, yv + 12 * SS), en, font=f_en, fill=SUB, anchor="lm")


for sid, yv in [("422", 275), ("421", 350), ("420", 450), ("419", 525), ("418", 600)]:
    zh, en = name_of(sid)
    label_r(P(0, yv)[1], zh, en)

# down-right diagonal: clear quadrant is upper-right
for sid, wx, wy in [("417", 1275, 650), ("416", 1300, 675)]:
    zh, en = name_of(sid)
    p = P(wx, wy)
    d.text((p[0] + LW * 1.1, p[1] - LW * 0.55), zh, font=f_zh, fill=TXT, anchor="ls")
    d.text((p[0] + LW * 1.1, p[1] - LW * 0.35), en, font=f_en, fill=SUB, anchor="la")

for sid, wx in [("1220", 1050), ("1101", 1100), ("1222", 1150)]:
    zh, en = name_of(sid)
    p = P(wx, 400)
    d.text((p[0], p[1] + LW * 1.2), zh, font=f_zh_m if sid == "1101" else f_zh, fill=TXT, anchor="ma")
    d.text((p[0], p[1] + LW * 1.2 + 23 * SS), en, font=f_en, fill=SUB, anchor="ma")

# line 7 stations, labels on the clear side
zh, en = name_of("708")
p = P(1175 - 12, 650 + 14)
d.text(p, zh, font=f_zh, fill=TXT, anchor="ra")
d.text((p[0], p[1] + 23 * SS), en, font=f_en, fill=SUB, anchor="ra")
# up-right diagonal: clear quadrant is lower-right
zh, en = name_of("710")
p = P(1350, 475)
d.text((p[0] + LW * 0.9, p[1] + LW * 0.5), zh, font=f_zh, fill=TXT, anchor="la")
d.text((p[0] + LW * 0.9, p[1] + LW * 0.5 + 26 * SS), en, font=f_en, fill=SUB, anchor="la")

# legend
ly = by1 + 34 * SS
lx = MARGIN
for lid, c in [("4", C4), ("12", C12), ("7", C7)]:
    d.rectangle([lx, ly - 6 * SS, lx + 34 * SS, ly + 6 * SS], fill=c)
    name = LINES[lid]["name"]["zh-CN"]
    d.text((lx + 44 * SS, ly), name, font=f_note, fill=TXT, anchor="lm")
    lx += 44 * SS + int(d.textlength(name, font=f_note)) + 40 * SS

# ---------------------------------------------------------------- specimens

y1 = ly + 56 * SS
sec_title(y1, "符号规格", "W = line width · seam 0.15W")

sy = y1 + 96 * SS
ix = [MARGIN + LW * 3, W_ * 0.31, W_ * 0.56, W_ * 0.82]

# 1 gap station
stroke([(ix[0] - LW * 2.4, sy), (ix[0] + LW * 2.4, sy)], C4)
gap_station((ix[0], sy), 0)
d.text((ix[0], sy + LW * 2.2), "单线中缝槽 0.35W", font=f_note, fill=SUB, anchor="ma")

# 2 seam slot (co-running normal station)
for k in (-1, 1):
    stroke([(ix[1] - LW * 2.4, sy + k * OFF / 2), (ix[1] + LW * 2.4, sy + k * OFF / 2)], C4 if k < 0 else C12)
seam_slot((ix[1], sy), 0)
d.text((ix[1], sy + LW * 2.2), "束中缝白槽", font=f_note, fill=SUB, anchor="ma")

# 3 bundle capsule
for k in (-1, 1):
    stroke([(ix[2] - LW * 2.4, sy + k * OFF / 2), (ix[2] + LW * 2.4, sy + k * OFF / 2)], C4 if k < 0 else C12)
capsule((ix[2], sy - OFF / 2), (ix[2], sy + OFF / 2))
d.text((ix[2], sy + LW * 2.2), "束上换乘胶囊", font=f_note, fill=SUB, anchor="ma")

# 4 concentric corner: east-going bundle turns north, shared arc centre
base_y = sy + LW * 1.2
xc = ix[3] + LW * 0.8
x_start = ix[3] - LW * 2.6
y_end = sy - LW * 1.6
for k, c in ((0, C4), (1, C12)):  # k=0 inner (upper-left), k=1 outer
    yk = base_y - OFF + k * OFF
    xkk = xc - OFF + k * OFF
    pts = fillet_path(
        [(x_start, yk), (xkk, yk), (xkk, y_end)],
        R_CORNER + k * OFF,
    )
    stroke(pts, c)
d.text((ix[3], sy + LW * 2.2), "同心圆角拐弯", font=f_note, fill=SUB, anchor="ma")

# footer
d.text((MARGIN, H_ - MARGIN), "并线为画布层计算 · 换乘由 isTransfer 决定 · 无元数据", font=f_note, fill=SUB, anchor="ls")
d.text((W_ - MARGIN, H_ - MARGIN), "preview ≤ 1600px", font=f_cap, fill=SUB, anchor="rs")

out = img.resize((FW, FH), Image.LANCZOS)
out_path = Path(__file__).resolve().parent / "style_spec_02.png"
out.save(out_path)
print("saved", out_path, out.size)
