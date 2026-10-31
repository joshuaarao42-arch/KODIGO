"""QR rendering."""
from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field, fields as dc_fields
from typing import List, Optional

import qrcode
from PIL import Image, ImageDraw, ImageOps
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_L, ERROR_CORRECT_M
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask
from qrcode.image.styles.moduledrawers.pil import (
    CircleModuleDrawer,
    RoundedModuleDrawer,
    SquareModuleDrawer,
)

from . import payloads

MODULE_STYLES = ("Square", "Rounded", "Dots")
QUALITY_BOX_SIZE = {"Standard": 10, "High": 20, "Ultra": 40}
MAX_LOGO_SCALE = 0.30
_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")


class QRDataTooLarge(Exception):
    """QR capacity error."""


@dataclass
class QRStyle:
    fg: str = "#12174A"
    bg: str = "#FFFFFF"
    logo_path: Optional[str] = None
    logo_scale: float = 0.22
    module_style: str = "Rounded"
    quality: str = "High"
    border: int = 4

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "QRStyle":
        names = {f.name for f in dc_fields(cls)}
        return cls(**{k: v for k, v in (data or {}).items() if k in names})


@dataclass
class RenderResult:
    image: Image.Image
    modules: int
    ec_label: str
    warnings: List[str] = field(default_factory=list)


# Colors
def hex_to_rgb(value: str) -> tuple:
    m = _HEX_RE.match(value.strip())
    if not m:
        raise ValueError(f"Invalid color: {value!r}")
    h = m.group(1)
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def luminance(value: str) -> float:
    def chan(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = hex_to_rgb(value)
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def contrast_ratio(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# Logo
def _apply_logo(img: Image.Image, path: str, scale: float, bg_rgb: tuple) -> None:
    scale = max(0.08, min(float(scale), MAX_LOGO_SCALE))
    logo = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
    side = int(img.width * scale)
    ratio = min(side / logo.width, side / logo.height)
    logo = logo.resize(
        (max(1, int(logo.width * ratio)), max(1, int(logo.height * ratio))),
        Image.Resampling.LANCZOS,
    )
    pad = max(4, int(side * 0.12))
    pw, ph = logo.width + 2 * pad, logo.height + 2 * pad
    plate = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    ImageDraw.Draw(plate).rounded_rectangle(
        (0, 0, pw - 1, ph - 1), radius=int(pad * 1.6), fill=tuple(bg_rgb) + (255,)
    )
    plate.alpha_composite(logo, (pad, pad))
    img.alpha_composite(plate, ((img.width - pw) // 2, (img.height - ph) // 2))


# Rendering
def _drawer(name: str):
    return {
        "Rounded": RoundedModuleDrawer(),
        "Dots": CircleModuleDrawer(),
    }.get(name, SquareModuleDrawer())


def render(payload: str, style: QRStyle, preview_px: Optional[int] = None) -> RenderResult:
    """Render a QR code. `preview_px` picks a box size close to that pixel size (fast, crisp
    preview); otherwise the export quality preset decides the resolution."""
    if not payload:
        raise ValueError("Nothing to encode")

    fg, bg = hex_to_rgb(style.fg), hex_to_rgb(style.bg)
    border = max(1, int(style.border))
    use_logo = bool(style.logo_path)
    levels = [ERROR_CORRECT_H] if use_logo else [ERROR_CORRECT_M, ERROR_CORRECT_L]
    ec_names = {ERROR_CORRECT_H: "H", ERROR_CORRECT_M: "M", ERROR_CORRECT_L: "L"}

    qr = None
    for level in levels:
        candidate = qrcode.QRCode(version=None, error_correction=level, box_size=10, border=border)
        candidate.add_data(payload)
        try:
            candidate.make(fit=True)
            qr, used = candidate, level
            break
        except (qrcode.exceptions.DataOverflowError, ValueError):
            continue
    if qr is None:
        raise QRDataTooLarge(
            "This content is too long for a QR code"
            + (" with a logo — remove the logo or shorten the text." if use_logo else " — please shorten it.")
        )

    total = qr.modules_count + 2 * border
    if preview_px:
        qr.box_size = max(2, math.ceil(preview_px / total))
    else:
        qr.box_size = QUALITY_BOX_SIZE.get(style.quality, 20)

    made = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=_drawer(style.module_style),
        color_mask=SolidFillColorMask(back_color=bg, front_color=fg),
    )
    pil = made.get_image() if hasattr(made, "get_image") else made._img
    img = pil.convert("RGBA")

    warnings: List[str] = []
    if use_logo:
        try:
            _apply_logo(img, style.logo_path, style.logo_scale, bg)
        except Exception:
            warnings.append("Logo couldn't be loaded, so it was skipped.")

    return RenderResult(img.convert("RGB"), qr.modules_count, ec_names[used], warnings)


def render_from_settings(settings: dict, preview_px: Optional[int] = None) -> RenderResult:
    payload = payloads.build(settings.get("kind", "url"), settings.get("fields", {}))
    return render(payload, QRStyle.from_dict(settings.get("style", {})), preview_px)


def save_png(image: Image.Image, path: str) -> None:
    image.convert("RGB").save(path, "PNG", dpi=(300, 300), optimize=True)
