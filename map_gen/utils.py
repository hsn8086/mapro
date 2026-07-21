from __future__ import annotations

from PIL import Image, ImageDraw
import os


def prepare_canvas(
    width: int, height: int, bg_path: str | None, *, bg_color: str = "#FAFAF7"
) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    if bg_path and os.path.exists(bg_path):
        try:
            bg_img = Image.open(bg_path)
            bg_img = bg_img.resize((width, height), Image.Resampling.LANCZOS)
            img.paste(bg_img, (0, 0))
        except Exception:
            pass

    return img, draw
