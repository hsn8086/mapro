from __future__ import annotations

import os
from PIL import ImageFont


def get_font(
    font_paths: list[str],
    size: int,
    priority_index: int | None = None,
    weight: str = "Regular",
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    target_path: str | None = None

    def find_weight_variant(base_path: str, target_weight: str) -> str | None:
        dir_name = os.path.dirname(base_path)
        base_name = os.path.basename(base_path)
        name_part, ext = os.path.splitext(base_name)

        for suffix in ["-Regular", "-Normal", "Regular", "Normal"]:
            if name_part.endswith(suffix):
                name_part = name_part[: -len(suffix)]
                break

        candidates = [
            f"{name_part}-{target_weight}{ext}",
            f"{name_part}{target_weight}{ext}",
            f"{name_part} {target_weight}{ext}",
        ]

        for cand in candidates:
            full = os.path.join(dir_name, cand)
            if os.path.exists(full):
                return full
        return None

    if priority_index is not None and 0 <= priority_index < len(font_paths):
        base = font_paths[priority_index]
        if weight != "Regular":
            variant = find_weight_variant(base, weight)
            if variant:
                target_path = variant
        if not target_path and os.path.exists(base):
            target_path = base

    if not target_path:
        for p in font_paths:
            if weight != "Regular":
                variant = find_weight_variant(p, weight)
                if variant:
                    target_path = variant
                    break
            if os.path.exists(p):
                target_path = p
                break

    if target_path:
        try:
            return ImageFont.truetype(target_path, size)
        except Exception:
            pass

    return ImageFont.load_default()
