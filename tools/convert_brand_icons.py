#!/usr/bin/env python3
"""Convert a source image into Home Assistant brand icon/logo assets.

Creates:
- icon.png, icon@2x.png
- dark_icon.png, dark_icon@2x.png
- logo.png, logo@2x.png
- dark_logo.png, dark_logo@2x.png

Usage:
  python tools/convert_brand_icons.py \
    --src /path/to/advanced_pool_controller.jpg \
    --out /path/to/brands/custom_integrations/pool_controller
"""
from __future__ import annotations

import argparse
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter


def _fit_image(src: Image.Image, size: int) -> Image.Image:
    """Fit image into a square canvas (contain), preserving aspect ratio."""
    img = src.convert("RGBA")
    w, h = img.size
    if w == 0 or h == 0:
        raise ValueError("Source image has invalid dimensions")

    scale = min(size / w, size / h)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    resized = img.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    offset = ((size - new_w) // 2, (size - new_h) // 2)
    canvas.paste(resized, offset)
    return canvas


def _apply_alpha(img: Image.Image, alpha: Image.Image) -> Image.Image:
    out = img.convert("RGBA")
    out.putalpha(alpha)
    return out


def _drop_shadow(alpha: Image.Image, offset: tuple[int, int], blur_radius: int, color=(0, 0, 0, 110)) -> Image.Image:
    shadow = Image.new("RGBA", alpha.size, color)
    shadow.putalpha(alpha)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    canvas = Image.new("RGBA", alpha.size, (0, 0, 0, 0))
    canvas.paste(shadow, offset, shadow)
    return canvas


def _dark_variant(src: Image.Image) -> Image.Image:
    """Create a dark-optimized variant by reducing stroke weight and softening colors."""
    img = src.convert("RGBA")

    # Dark mode: reduce saturation, raise brightness slightly to avoid glare.
    try:
        img = ImageEnhance.Color(img).enhance(0.85)
        img = ImageEnhance.Brightness(img).enhance(1.10)
        img = ImageEnhance.Contrast(img).enhance(1.04)
    except Exception:
        pass

    alpha = img.split()[-1]
    # Shrink alpha to reduce visual stroke weight (irradiation compensation).
    try:
        shrunk = alpha.filter(ImageFilter.MinFilter(size=3))
    except Exception:
        shrunk = alpha
    img = _apply_alpha(img, shrunk)

    # Inner glow for dark mode (subtle light lift).
    glow = Image.new("RGBA", img.size, (255, 255, 255, 90))
    glow_mask = shrunk.filter(ImageFilter.GaussianBlur(radius=3))
    glow.putalpha(glow_mask)

    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out = Image.alpha_composite(out, glow)
    out = Image.alpha_composite(out, img)
    return out


def _light_variant(src: Image.Image) -> Image.Image:
    """Create a light-optimized variant by thickening strokes and adding drop shadow."""
    img = src.convert("RGBA")

    # Light mode: slightly darker + more saturated for crisp contrast.
    try:
        img = ImageEnhance.Color(img).enhance(1.08)
        img = ImageEnhance.Brightness(img).enhance(0.94)
        img = ImageEnhance.Contrast(img).enhance(1.08)
    except Exception:
        pass

    alpha = img.split()[-1]
    # Thicken strokes slightly for light backgrounds.
    try:
        expanded = alpha.filter(ImageFilter.MaxFilter(size=3))
    except Exception:
        expanded = alpha
    img = _apply_alpha(img, expanded)

    # Soft drop shadow (visible in light mode).
    shadow = _drop_shadow(expanded, offset=(0, 6), blur_radius=8, color=(0, 0, 0, 90))

    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out = Image.alpha_composite(out, shadow)
    out = Image.alpha_composite(out, img)
    return out


def _save(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, help="Path to source image (JPG/PNG)")
    parser.add_argument("--out", required=True, help="Output directory for brand assets")
    args = parser.parse_args()

    src_path = Path(args.src)
    out_dir = Path(args.out)
    if not src_path.exists():
        raise FileNotFoundError(src_path)

    src = Image.open(src_path)

    # Sizes: icon 256 (+2x 512), logo 256 (+2x 512)
    icon = _fit_image(src, 256)
    icon2x = _fit_image(src, 512)
    logo = _fit_image(src, 256)
    logo2x = _fit_image(src, 512)

    # Light variants: slightly darker + dark shadow for contrast on light backgrounds.
    icon_light = _light_variant(icon)
    icon2x_light = _light_variant(icon2x)
    logo_light = _light_variant(logo)
    logo2x_light = _light_variant(logo2x)

    # Dark variants: softer colors + inner glow for contrast on dark backgrounds.
    dark_icon = _dark_variant(icon)
    dark_icon2x = _dark_variant(icon2x)
    dark_logo = _dark_variant(logo)
    dark_logo2x = _dark_variant(logo2x)

    assets = {
        "icon.png": icon_light,
        "icon@2x.png": icon2x_light,
        "dark_icon.png": dark_icon,
        "dark_icon@2x.png": dark_icon2x,
        "logo.png": logo_light,
        "logo@2x.png": logo2x_light,
        "dark_logo.png": dark_logo,
        "dark_logo@2x.png": dark_logo2x,
    }

    for name, img in assets.items():
        _save(img, out_dir / name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
