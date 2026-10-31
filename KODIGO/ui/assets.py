"""Generated UI assets."""
from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from . import theme


def _hex(value: str | tuple[str, str]) -> tuple:
    value = theme.color(value)
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _diagonal_gradient(size: int, c1: tuple, c2: tuple) -> Image.Image:
    v = Image.linear_gradient("L").resize((size, size))
    h = v.transpose(Image.Transpose.ROTATE_90)
    mask = ImageChops.add(v, h, scale=2)
    return Image.composite(
        Image.new("RGB", (size, size), c2), Image.new("RGB", (size, size), c1), mask
    )


def brand_mark(size: int = 64) -> Image.Image:
    """Brand mark."""
    s = size * 4
    img = _diagonal_gradient(s, _hex(theme.BLUE), _hex(theme.VIOLET)).convert("RGBA")
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * 0.26), fill=255)
    img.putalpha(mask)

    d = ImageDraw.Draw(img)
    pad = s * 0.21
    cell = (s - 2 * pad) / 7

    def sq(cx, cy, w, h, r, fill):
        x0, y0 = pad + cx * cell, pad + cy * cell
        d.rounded_rectangle((x0, y0, x0 + w * cell, y0 + h * cell), radius=r * cell, fill=fill)

    white, inner = (255, 255, 255, 255), (92, 100, 235, 255)
    for cx, cy in ((0, 0), (4, 0), (0, 4)):
        sq(cx, cy, 3, 3, 0.7, white)
        sq(cx + 1, cy + 1, 1, 1, 0.25, inner)
    for cx, cy in ((4, 4), (6, 4), (5, 5), (4, 6), (6, 6)):
        sq(cx, cy, 1, 1, 0.3, white)
    return img.resize((size, size), Image.Resampling.LANCZOS)


def ensure_icon(path) -> Path:
    path = Path(path)
    brand_mark(256).save(
        path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    return path


def thumbnail_bytes(img: Image.Image, size: int = 256) -> bytes:
    im = img.convert("RGB")
    im.thumbnail((size, size), Image.Resampling.LANCZOS)
    buf = BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


@lru_cache(maxsize=8)
def _stage_backdrop(w: int, h: int, bg_hex: str, with_shadow: bool) -> Image.Image:
    """Preview backdrop."""
    m = min(w, h)
    base = Image.new("RGBA", (w, h), _hex(bg_hex) + (255,))

    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for (cx, cy, r, color) in (
        (0.30 * w, 0.32 * h, 0.42 * m, _hex(theme.BLUE)),
        (0.72 * w, 0.70 * h, 0.46 * m, _hex(theme.VIOLET)),
    ):
        gd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color + (120,))
    glow = glow.filter(ImageFilter.GaussianBlur(m * 0.16))
    base = Image.alpha_composite(base, glow).convert("RGB")

    if with_shadow:
        side = int(m * 0.84)
        x, y = (w - side) // 2, (h - side) // 2 + int(side * 0.03)
        shadow = Image.new("L", (w, h), 0)
        ImageDraw.Draw(shadow).rounded_rectangle(
            (x, y, x + side, y + side), radius=int(side * 0.05), fill=170
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(side * 0.035))
        base.paste((0, 0, 0), mask=shadow)

    # Rounded stage corners
    rounded = Image.new("RGB", (w, h), _hex(theme.STAGE))
    clip = Image.new("L", (w, h), 0)
    ImageDraw.Draw(clip).rounded_rectangle((0, 0, w - 1, h - 1), radius=14, fill=255)
    rounded.paste(base, mask=clip)
    return rounded


def compose_stage(qr_img: Optional[Image.Image], w: int, h: int, bg_hex: str) -> Image.Image:
    """Preview stage."""
    w, h = max(80, int(w)), max(80, int(h))
    canvas = _stage_backdrop(w, h, bg_hex, qr_img is not None).copy()
    side = int(min(w, h) * 0.84)
    x, y = (w - side) // 2, (h - side) // 2

    if qr_img is None:
        d = ImageDraw.Draw(canvas)
        s2 = int(side * 0.5)
        x2, y2 = (w - s2) // 2, (h - s2) // 2
        d.rounded_rectangle((x2, y2, x2 + s2, y2 + s2), radius=int(s2 * 0.08),
                            outline=_hex(theme.BORDER_HI), width=2)
        return canvas

    q = qr_img.convert("RGB").resize((side, side), Image.Resampling.LANCZOS)
    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, side - 1, side - 1), radius=int(side * 0.04), fill=255)
    canvas.paste(q, (x, y), mask)
    return canvas
