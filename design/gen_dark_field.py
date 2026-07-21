"""Dark Cartography — survey plate of a fictional transit lattice.

Renders a museum-grade PNG. All geometry is procedural; no real city.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- config

FONT_DIR = Path("/home/small-hsn/.agents/skills/canvas-design/canvas-fonts")
OUT = Path("/home/small-hsn/projects/mapro/design/dark_field_survey.png")

SS = 2  # supersample
W, H = 3200 * SS, 4000 * SS

BG = (14, 17, 22)  # 0E1116
STAR = (232, 228, 218)  # E8E4DA warm white
GOLD = (212, 168, 83)  # D4A853
BLUE = (74, 122, 140)  # 4A7A8C
GRID = (42, 47, 56)  # 2A2F38
INK = (150, 148, 140)

rng = random.Random(20260721)

# world coordinates: x in [0,100], y in [0,125]; y up
WX, WY = 100.0, 125.0
# plate area on canvas (margins)
MARG_X = 0.105
PLATE_TOP = 0.075
PLATE_BOT = 0.155  # room for caption block
PX0 = W * MARG_X
PX1 = W * (1 - MARG_X)
PY0 = H * PLATE_TOP
PY1 = H * (1 - PLATE_BOT)


def to_px(x: float, y: float) -> tuple[float, float]:
    return (
        PX0 + (x / WX) * (PX1 - PX0),
        PY1 - (y / WY) * (PY1 - PY0),
    )


# ---------------------------------------------------------------- network

# waypoints obey 0/45/90 lattice moves. river void: band y ~ [52, 62].
LINES: dict[str, list[tuple[float, float]]] = {
    "A": [(10, 78), (34, 78), (46, 90), (66, 90), (78, 78), (92, 78)],
    "B": [(56, 116), (56, 88), (48, 80), (48, 40), (58, 30), (58, 12)],
    "C": [(32, 66), (32, 94), (42, 104), (64, 104), (76, 92), (76, 72), (64, 66)],
    "D": [(12, 108), (40, 80), (40, 68), (62, 46), (62, 30)],
    "E": [(14, 30), (38, 30), (50, 42), (76, 42), (88, 30)],
    "F": [(18, 90), (30, 102), (52, 112), (70, 112)],
    "G": [(24, 94), (24, 46), (34, 36), (34, 20)],
    "H": [(86, 98), (86, 64), (72, 50), (72, 34)],
}
PLOTTED = {"A": GOLD, "B": BLUE}
RIVER = (50.0, 63.0)  # y-band kept free of stations
SPACING = 4.6


def seg_points(
    a: tuple[float, float], b: tuple[float, float]
) -> list[tuple[float, float]]:
    ax, ay = a
    bx, by = b
    d = math.hypot(bx - ax, by - ay)
    n = max(1, round(d / SPACING))
    return [(ax + (bx - ax) * i / n, ay + (by - ay) * i / n) for i in range(1, n)]


def build() -> tuple[
    dict[tuple[float, float], set[str]], dict[str, list[tuple[float, float]]]
]:
    """Return station->lines map and per-line ordered stations."""
    raw: dict[str, list[tuple[float, float]]] = {}
    for lid, wps in LINES.items():
        pts: list[tuple[float, float]] = [wps[0]]
        for a, b in zip(wps, wps[1:]):
            pts.extend(seg_points(a, b))
            pts.append(b)
        # drop stations inside the river band
        pts = [p for p in pts if not (RIVER[0] < p[1] < RIVER[1])]
        raw[lid] = pts
    # merge nearby stations across lines -> transfers
    merged: list[tuple[float, float]] = []
    station_lines: dict[int, set[str]] = {}
    line_station_idx: dict[str, list[int]] = {}
    for lid, pts in raw.items():
        idxs = []
        for p in pts:
            found = -1
            for i, q in enumerate(merged):
                if math.hypot(p[0] - q[0], p[1] - q[1]) < 2.6:
                    found = i
                    break
            if found < 0:
                merged.append(p)
                found = len(merged) - 1
                station_lines[found] = set()
            station_lines[found].add(lid)
            if not idxs or idxs[-1] != found:
                idxs.append(found)
        line_station_idx[lid] = idxs
    stations = {merged[i]: station_lines[i] for i in range(len(merged))}
    per_line = {
        lid: [merged[i] for i in idxs] for lid, idxs in line_station_idx.items()
    }
    return stations, per_line


# ---------------------------------------------------------------- luminance layer


def gaussian_sprite(radius_px: float, size: int) -> np.ndarray:
    ax = np.arange(size) - (size - 1) / 2
    xx, yy = np.meshgrid(ax, ax)
    rr = np.sqrt(xx * xx + yy * yy)
    core = np.clip(1.0 - rr / radius_px, 0, 1) ** 1.6
    halo = np.exp(-((rr / (radius_px * 2.6)) ** 2)) * 0.30
    return np.clip(core + halo, 0, 1)


def add_sprite(
    buf: np.ndarray, x: float, y: float, spr: np.ndarray, gain: float
) -> None:
    s = spr.shape[0]
    x0 = int(round(x - s / 2))
    y0 = int(round(y - s / 2))
    x1, y1 = x0 + s, y0 + s
    if x1 < 0 or y1 < 0 or x0 >= buf.shape[1] or y0 >= buf.shape[0]:
        return
    sx0, sy0 = max(0, -x0), max(0, -y0)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(buf.shape[1], x1), min(buf.shape[0], y1)
    buf[y0:y1, x0:x1] += spr[sy0 : sy0 + (y1 - y0), sx0 : sx0 + (x1 - x0)] * gain


# ---------------------------------------------------------------- main render


def render() -> None:
    stations, per_line = build()
    n_objects = len(stations)
    n_transfer = sum(1 for s in stations.values() if len(s) >= 2)

    # ---- background: uneven dark field with vignette + faint sky-glow at core
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = to_px(52, 84)  # glow above the river, at the dense core
    d_core = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (0.55 * W)
    glow = np.exp(-(d_core**2)) * 0.035
    d_edge = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    vign = -0.025 * np.clip(d_edge - 0.55, 0, 1) ** 1.5
    base = np.zeros((H, W, 3), np.float32)
    for c in range(3):
        base[..., c] = BG[c] / 255.0 * (1 + glow + vign)

    # ---- luminance layers (additive exposure)
    lum_w = np.zeros((H, W), np.float32)  # warm-white stars
    lum_g = np.zeros((H, W), np.float32)  # gold trace
    lum_b = np.zeros((H, W), np.float32)  # blue trace

    # traces: hairlines broken at stations (line never crosses a body)
    def draw_trace(pts: list[tuple[float, float]], buf: np.ndarray) -> None:
        px = [to_px(*p) for p in pts]
        for (x0, y0), (x1, y1) in zip(px, px[1:]):
            d = math.hypot(x1 - x0, y1 - y0)
            gap = 15 * SS  # clearance around each body
            if d <= 2 * gap:
                continue
            t0, t1 = gap / d, 1 - gap / d
            ax, ay = x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0
            bx, by = x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1
            steps = int(d)
            for i in range(steps + 1):
                t = i / steps
                add_sprite(
                    buf,
                    ax + (bx - ax) * t,
                    ay + (by - ay) * t,
                    trace_spr,
                    0.20,
                )

    trace_spr = gaussian_sprite(1.4 * SS, int(8 * SS))
    draw_trace(per_line["A"], lum_g)
    draw_trace(per_line["B"], lum_b)

    # stars: magnitude driven by degree (number of lines through node)
    spr_cache: dict[int, np.ndarray] = {}
    for (x, y), lines_here in stations.items():
        deg = len(lines_here)
        r = {1: 4.2, 2: 7.0}.get(deg, 9.5) * SS
        r *= 1 + rng.uniform(-0.15, 0.15)  # brightness jitter, not position
        gain = {1: 0.62, 2: 0.95}.get(deg, 1.25)
        gain *= 1 + rng.uniform(-0.12, 0.12)
        key = int(r)
        if key not in spr_cache:
            spr_cache[key] = gaussian_sprite(key, int(key * 7))
        px, py = to_px(x, y)
        jx = rng.uniform(-0.6, 0.6) * SS  # ±3% positional noise only
        jy = rng.uniform(-0.6, 0.6) * SS
        add_sprite(lum_w, px + jx, py + jy, spr_cache[key], gain)

    # composite additive exposure over base (screen-like)
    star = np.array(STAR, np.float32) / 255.0
    gold = np.array(GOLD, np.float32) / 255.0
    blue = np.array(BLUE, np.float32) / 255.0
    img = base.copy()
    for c in range(3):
        img[..., c] += lum_w * star[c]
        img[..., c] += lum_g * gold[c] * 0.85
        img[..., c] += lum_b * blue[c] * 0.85
    img = np.clip(img, 0, 1)

    # ---- film grain: shadow-bound high-frequency + sparse cold hot pixels
    lum_map = img.mean(axis=2)
    shadow = np.clip(1 - lum_map / 0.20, 0, 1)
    noise = (np.random.default_rng(7).standard_normal((H, W)) * 0.016).astype(
        np.float32
    )
    for c in range(3):
        img[..., c] = np.clip(img[..., c] + noise * shadow, 0, 1)
    hot = np.random.default_rng(11)
    for _ in range(int(W * H / 9e5)):
        hx, hy = hot.integers(0, W), hot.integers(0, H)
        img[hy : hy + 2, hx : hx + 2] += np.array([0.05, 0.07, 0.09])
    img = np.clip(img, 0, 1)

    canvas = Image.fromarray((img * 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(canvas, "RGBA")

    # ---- reseau grid: etched crosses at lattice intersections (Carte du Ciel)
    pitch = 10.0
    cross = 5 * SS
    for gx in range(0, int(WX) + 1, int(pitch)):
        for gy in range(0, int(WY) + 1, int(pitch)):
            px, py = to_px(gx, gy)
            a = (96, 102, 112, 120)
            d.line([(px - cross, py), (px + cross, py)], fill=a, width=SS)
            d.line([(px, py - cross), (px, py + cross)], fill=a, width=SS)

    # plate frame
    frame = (*INK, 150)
    d.rectangle([PX0, PY0, PX1, PY1], outline=frame, width=SS)

    # ---- edge scales: honest mapping to world units
    fnt_tick = ImageFont.truetype(str(FONT_DIR / "GeistMono-Regular.ttf"), int(26 * SS))
    tick_a = (*INK, 190)
    for gx in range(0, int(WX) + 1, 2):
        px, _ = to_px(gx, 0)
        long = gx % 10 == 0
        tl = (14 if long else 7) * SS
        d.line([(px, PY1), (px, PY1 + tl)], fill=tick_a, width=SS)
        d.line([(px, PY0), (px, PY0 - tl)], fill=tick_a, width=SS)
        if long:
            d.text(
                (px, PY1 + 20 * SS),
                f"{gx:03d}",
                font=fnt_tick,
                fill=(*INK, 210),
                anchor="ma",
            )
    for gy in range(0, int(WY) + 1, 2):
        _, py = to_px(0, gy)
        long = gy % 10 == 0
        tl = (14 if long else 7) * SS
        d.line([(PX0, py), (PX0 - tl, py)], fill=tick_a, width=SS)
        d.line([(PX1, py), (PX1 + tl, py)], fill=tick_a, width=SS)
        if long:
            d.text(
                (PX0 - 22 * SS, py),
                f"{gy:03d}",
                font=fnt_tick,
                fill=(*INK, 210),
                anchor="rm",
            )

    # ---- transfer rings (open ring residue of interchange symbol)
    for (x, y), lines_here in stations.items():
        if len(lines_here) >= 3:
            px, py = to_px(x, y)
            r = 16 * SS
            d.ellipse([px - r, py - r, px + r, py + r], outline=(*STAR, 120), width=SS)

    # ---- annotation: dashed circle on the densest southern cluster
    fnt_note = ImageFont.truetype(str(FONT_DIR / "GeistMono-Regular.ttf"), int(24 * SS))
    south = [p for p in stations if p[1] < RIVER[0]]
    dense = max(
        south,
        key=lambda p: sum(
            1 for q in stations if math.hypot(p[0] - q[0], p[1] - q[1]) < 10
        ),
    )
    cxp, cyp = to_px(*dense)
    rr = 60 * SS
    for ang in range(0, 360, 9):
        a0 = math.radians(ang)
        a1 = math.radians(ang + 5)
        d.line(
            [
                (cxp + rr * math.cos(a0), cyp + rr * math.sin(a0)),
                (cxp + rr * math.cos(a1), cyp + rr * math.sin(a1)),
            ],
            fill=(*INK, 170),
            width=SS,
        )
    d.text(
        (cxp + rr + 16 * SS, cyp),
        "cluster 04",
        font=fnt_note,
        fill=(*INK, 200),
        anchor="lm",
    )

    # ---- unidentified source in the river void (the only crosshair)
    ux, uy = to_px(68, 56.5)
    arm = 20 * SS
    gapc = 7 * SS
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        d.line(
            [(ux + dx * gapc, uy + dy * gapc), (ux + dx * arm, uy + dy * arm)],
            fill=(*GOLD, 200),
            width=SS,
        )
    d.text(
        (ux + arm + 12 * SS, uy),
        "unidentified source",
        font=fnt_note,
        fill=(*INK, 200),
        anchor="lm",
    )

    # ---- typography block
    fnt_title = ImageFont.truetype(str(FONT_DIR / "Jura-Medium.ttf"), int(64 * SS))
    fnt_small = ImageFont.truetype(
        str(FONT_DIR / "GeistMono-Regular.ttf"), int(28 * SS)
    )

    def tracked(
        draw: ImageDraw.ImageDraw,
        xy: tuple[float, float],
        text: str,
        font,
        fill,
        tracking: float,
        anchor_left: bool = True,
    ):
        x, y = xy
        for ch in text:
            draw.text((x, y), ch, font=font, fill=fill)
            x += draw.textlength(ch, font=font) + tracking

    ty = H * (1 - PLATE_BOT) + 70 * SS
    tracked(
        d, (PX0, ty + 30 * SS), "DARK FIELD SURVEY", fnt_title, (*STAR, 235), 26 * SS
    )
    d.text(
        (PX0, ty + 130 * SS),
        f"{n_objects} objects · {n_transfer} interchanges · 8 traces · 2 plotted",
        font=fnt_small,
        fill=(*INK, 220),
    )
    d.text(
        (PX0, ty + 180 * SS),
        "schematic projection · 45° lattice · epoch 2026.5",
        font=fnt_small,
        fill=(*INK, 220),
    )
    # plate number, right aligned
    d.text((PX1, ty + 30 * SS), "PLATE", font=fnt_small, fill=(*INK, 220), anchor="ra")
    fnt_plate = ImageFont.truetype(str(FONT_DIR / "Jura-Medium.ttf"), int(64 * SS))
    d.text((PX1, ty + 72 * SS), "01", font=fnt_plate, fill=(*STAR, 235), anchor="ra")

    # ---- magnitude legend above the plate: three specimen dots + counts
    ly = PY0 - 48 * SS
    lx = PX0
    legend = [(4.2, "1"), (7.0, "2"), (9.5, "3+")]
    for r_w, label in legend:
        r = r_w * SS * 0.85
        d.ellipse([lx - r, ly - r, lx + r, ly + r], fill=(*STAR, 225))
        d.text((lx + 16 * SS, ly), label, font=fnt_tick, fill=(*INK, 210), anchor="lm")
        lx += 90 * SS
    d.text(
        (lx + 6 * SS, ly),
        "lines through node",
        font=fnt_tick,
        fill=(*INK, 190),
        anchor="lm",
    )
    # field designation, top right
    d.text((PX1, ly), "field DC-01", font=fnt_tick, fill=(*INK, 210), anchor="rm")

    out = canvas.resize((W // SS, H // SS), Image.LANCZOS)
    out.save(OUT)
    print("saved", OUT, "objects:", n_objects, "transfers:", n_transfer)


if __name__ == "__main__":
    render()
