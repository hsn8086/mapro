"""SPEC 03 — bundling case gallery.

Six panels: same-side join/leave, opposite-side leave with 45-degree
crossing, three-line bundle slot order, true shared-track running,
in-bundle concentric corner, third-party line crossing under a bundle.
Flat only. Small preview output.
"""

from __future__ import annotations

import colorsys
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
LATIN = (
    "/home/small-hsn/.agents/skills/canvas-design/canvas-fonts/GeistMono-Regular.ttf"
)

MARGIN = int(W_ * 0.055)
LW = 18 * SS
GAP = LW * 0.15
OFF = LW + GAP
R_RING = LW * 0.55
W_RING = max(2, int(LW * 0.16))
R_CORNER = LW * 1.25
GAP_ST = LW * 0.35


def normalize_line_color(c: str) -> str:
    c = c.lstrip("#")
    r, g, b = (int(c[i : i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    s = min(max(s, 0.55), 0.85)
    l = min(max(l, 0.38), 0.58)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


CA = normalize_line_color("#00679e")  # blue trunk
CB = normalize_line_color("#c70541")  # red joiner
CC = normalize_line_color("#d14d23")  # orange third line
CD = normalize_line_color("#01824a")  # green

img = Image.new("RGB", (W_, H_), BG)
d = ImageDraw.Draw(img)

f_h1 = ImageFont.truetype(CJK_M, 30 * SS)
f_cap = ImageFont.truetype(LATIN, 15 * SS)
f_sec = ImageFont.truetype(CJK_M, 19 * SS)
f_ttl = ImageFont.truetype(CJK_M, 16 * SS)
f_note = ImageFont.truetype(CJK, 13 * SS)

# ---------------------------------------------------------------- helpers


def fillet_path(pts, r, n=36):
    out = [pts[0]]
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
            out.append(
                (
                    (1 - s) ** 2 * a[0] + 2 * (1 - s) * s * p1[0] + s**2 * b[0],
                    (1 - s) ** 2 * a[1] + 2 * (1 - s) * s * p1[1] + s**2 * b[1],
                )
            )
        out.append(b)
    out.append(pts[-1])
    return out


def stroke(pts, color, width=LW):
    d.line(pts, fill=color, width=width, joint="curve")


def gap_station(p, dir_deg, breadth=LW * 0.55):
    a = math.radians(dir_deg)
    nx, ny = -math.sin(a), math.cos(a)
    h = breadth / 2
    d.line(
        [(p[0] - nx * h, p[1] - ny * h), (p[0] + nx * h, p[1] + ny * h)],
        fill=BG,
        width=int(GAP_ST),
    )


def seam_slot(p, dir_deg):
    a = math.radians(dir_deg)
    nx, ny = -math.sin(a), math.cos(a)
    h = (GAP + LW) / 2
    d.line(
        [(p[0] - nx * h, p[1] - ny * h), (p[0] + nx * h, p[1] + ny * h)],
        fill=BG,
        width=int(GAP_ST),
    )


def ring(p):
    d.ellipse(
        [p[0] - R_RING, p[1] - R_RING, p[0] + R_RING, p[1] + R_RING],
        fill=BG,
        outline=TXT,
        width=W_RING,
    )


def capsule(p0, p1):
    x0, x1 = min(p0[0], p1[0]) - R_RING, max(p0[0], p1[0]) + R_RING
    y0, y1 = min(p0[1], p1[1]) - R_RING, max(p0[1], p1[1]) + R_RING
    d.rounded_rectangle(
        [x0, y0, x1, y1], radius=R_RING, fill=BG, outline=TXT, width=W_RING
    )


def sec_title(y, zh, en):
    d.text((MARGIN, y), zh, font=f_sec, fill=TXT, anchor="lm")
    d.text((W_ - MARGIN, y), en, font=f_cap, fill=SUB, anchor="rm")
    d.line([(MARGIN, y + 26 * SS), (W_ - MARGIN, y + 26 * SS)], fill=GUIDE, width=SS)


# ---------------------------------------------------------------- header

y = MARGIN
d.text((MARGIN, y), "并线案例集 · 风格样张", font=f_h1, fill=TXT, anchor="la")
d.text((W_ - MARGIN, y + 12 * SS), "SPEC 03", font=f_cap, fill=SUB, anchor="ra")
d.text(
    (MARGIN, y + 48 * SS),
    "并入 · 解出 · 交叉 · 并轨 · 拐弯",
    font=f_note,
    fill=SUB,
    anchor="la",
)

y0 = y + 106 * SS
sec_title(y0, "六种情形", "bundling cases")

# ---------------------------------------------------------------- panels

PW, PH = 545 * SS, 380 * SS
COLS = [MARGIN, MARGIN + PW + 30 * SS]
ROWS = [y0 + 54 * SS, y0 + 54 * SS + (PH + 30 * SS), y0 + 54 * SS + 2 * (PH + 30 * SS)]


def panel(col, row, title, note):
    ox, oy = COLS[col], ROWS[row]
    d.text((ox, oy), title, font=f_ttl, fill=TXT, anchor="la")
    d.text((ox, oy + PH - 16 * SS), note, font=f_note, fill=SUB, anchor="ls")
    return ox, oy + 34 * SS  # diagram origin


# ---- A: same-side join & leave, no crossing
ox, oy = panel(0, 0, "A · 同侧并入 / 解出", "槽位取来向一侧 · 无交叉")
xT = ox + 330 * SS
xS = xT - OFF
stroke([(xT, oy), (xT, oy + 290 * SS)], CA)
x_dia = ox + 246 * SS  # start of 45-deg approach
y_in = oy + 30 * SS
y_arr = y_in + (xS - x_dia)  # arrival depth of the 45-deg segment
y_out = oy + 226 * SS
pB = fillet_path(
    [
        (ox + 10 * SS, y_in),
        (x_dia, y_in),
        (xS, y_arr),
        (xS, y_out),
        (x_dia, y_out + (xS - x_dia)),
        (ox + 10 * SS, y_out + (xS - x_dia)),
    ],
    R_CORNER,
)
stroke(pB, CB)
gap_station((xT, oy + 40 * SS), 90)
gap_station((ox + 110 * SS, y_in), 0)
capsule((xS, oy + 160 * SS), (xT, oy + 160 * SS))

# ---- B: opposite-side leave -> 45 deg crossing, no symbol at cross
ox, oy = panel(
    1, 0, "B · 异侧解出 · 45° 斜跨", "跨越处无符号 · 跨越线在上层 · 远离站点"
)
xT = ox + 300 * SS
xS = xT - OFF
stroke([(xT, oy), (xT, oy + 290 * SS)], CA)
x_dia = ox + 216 * SS
y_in = oy + 30 * SS
y_arr = y_in + (xS - x_dia)
pB = fillet_path(
    [
        (ox + 10 * SS, y_in),
        (x_dia, y_in),
        (xS, y_arr),
        (xS, oy + 210 * SS),
        (xS + 115 * SS, oy + 325 * SS),
    ],
    R_CORNER,
)
stroke(pB, CB)
capsule((xS, oy + 150 * SS), (xT, oy + 150 * SS))
gap_station((xT, oy + 45 * SS), 90)

# ---- C: three-line bundle, slot order by approach side
ox, oy = panel(0, 1, "C · 三线束 · 槽序按来向", "西来占西槽 · 东来占东槽 · 贯穿线不动")
xT = ox + 280 * SS
xB = xT - OFF
xC = xT + OFF
stroke([(xT, oy), (xT, oy + 290 * SS)], CA)
pB = fillet_path(
    [
        (ox + 10 * SS, oy + 50 * SS),
        (ox + 96 * SS, oy + 50 * SS),
        (xB, oy + 50 * SS + (xB - (ox + 96 * SS))),
        (xB, oy + 290 * SS),
    ],
    R_CORNER,
)
stroke(pB, CB)
pC = fillet_path(
    [
        (ox + 520 * SS, oy + 20 * SS),
        (ox + 420 * SS, oy + 20 * SS),
        (xC, oy + 20 * SS + ((ox + 420 * SS) - xC)),
        (xC, oy + 290 * SS),
    ],
    R_CORNER,
)
stroke(pC, CD)
capsule((xB, oy + 244 * SS), (xC, oy + 244 * SS))
gap_station((xT, oy + 40 * SS), 90)

# ---- D: true shared track, seam-slot normal stations
ox, oy = panel(1, 1, "D · 并轨贯通 · 普通站", "共轨段站点非换乘 · 中缝白槽 · 外缘连续")
xc = ox + 270 * SS
for k, c in ((-1, CA), (1, CB)):
    stroke([(xc + k * OFF / 2, oy + 10 * SS), (xc + k * OFF / 2, oy + 290 * SS)], c)
for yy_ in (70, 150, 230):
    seam_slot((xc, oy + yy_ * SS), 90)

# ---- E: in-bundle corner, true concentric arcs sharing one centre
ox, oy = panel(0, 2, "E · 束内拐弯 · 同心圆角", "内线小半径 · 外线大半径 · 缝宽恒定")
Cx, Cy = ox + 300 * SS, oy + 130 * SS
rA = R_CORNER * 1.4
for k, c in ((0, CA), (1, CB)):  # k=0 inner (upper horizontal, left vertical)
    r = rA + k * OFF
    d.line([(ox + 20 * SS, Cy + r), (Cx, Cy + r)], fill=c, width=LW)
    ro = r + LW / 2  # PIL arc width grows inward; bbox at outer edge
    d.arc([Cx - ro, Cy - ro, Cx + ro, Cy + ro], 0, 90, fill=c, width=LW)
    d.line([(Cx + r, Cy), (Cx + r, oy + 10 * SS)], fill=c, width=LW)
seam_slot((ox + 140 * SS, Cy + rA + OFF / 2), 0)
capsule((Cx + rA, oy + 60 * SS), (Cx + rA + OFF, oy + 60 * SS))

# ---- F: third line crossing under the bundle
ox, oy = panel(
    1, 2, "F · 第三线横穿 · 不并入", "束几何不变 · 交叉处无符号 · 横穿线在下层"
)
xc = ox + 270 * SS
stroke([(ox + 10 * SS, oy + 175 * SS), (ox + 520 * SS, oy + 175 * SS)], CC)
for k, c in ((-1, CA), (1, CB)):
    stroke([(xc + k * OFF / 2, oy + 10 * SS), (xc + k * OFF / 2, oy + 290 * SS)], c)
capsule((xc - OFF / 2, oy + 70 * SS), (xc + OFF / 2, oy + 70 * SS))
seam_slot((xc, oy + 250 * SS), 90)
gap_station((ox + 100 * SS, oy + 175 * SS), 0)

# ---------------------------------------------------------------- footer rules

fy = ROWS[2] + PH + 26 * SS
d.line([(MARGIN, fy), (W_ - MARGIN, fy)], fill=GUIDE, width=SS)
rules = [
    "槽位分配：并入线取来向一侧槽位，后并入者排更外侧，贯穿线保持原对齐不动",
    "必须跨越时：45° 斜段直接跨越，交叉处无符号，距最近站符 ≥ 1.5W，跨越线绘制在上层",
    "第三方横穿：束几何不变，交叉处无符号，横穿线绘制在束下层",
]
for i, r in enumerate(rules):
    d.text(
        (MARGIN, fy + (22 + i * 26) * SS),
        f"{i + 1}.  {r}",
        font=f_note,
        fill=SUB,
        anchor="lm",
    )

d.text(
    (W_ - MARGIN, H_ - MARGIN), "preview ≤ 1600px", font=f_cap, fill=SUB, anchor="rs"
)

out = img.resize((FW, FH), Image.LANCZOS)
out_path = Path(__file__).resolve().parent / "style_spec_03.png"
out.save(out_path)
print("saved", out_path, out.size)
