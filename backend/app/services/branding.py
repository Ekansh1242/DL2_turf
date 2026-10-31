"""
College branding for PDF documents. No real RCOEM logo file was
available, so this generates a simple placeholder crest on first use
and caches it. Once you have the real logo, set COLLEGE_LOGO_PATH in
.env to its file path and this module will use that instead --
nothing else in the codebase needs to change.
"""
from __future__ import annotations

import io
import os
from functools import lru_cache

COLLEGE_LOGO_PATH = os.environ.get("COLLEGE_LOGO_PATH")


def _generate_placeholder_logo() -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    size = 200
    img = Image.new("RGB", (size, size), "#4c1d95")
    draw = ImageDraw.Draw(img)
    draw.ellipse((10, 10, size - 10, size - 10), fill="#6d28d9", outline="#ffffff", width=4)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    text = "RCOEM"
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - w) / 2, (size - h) / 2 - 5), text, fill="white", font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@lru_cache(maxsize=1)
def get_logo_bytes() -> bytes | None:
    """Returns raw PNG bytes for the college logo, or None if unavailable.
    PDFs still build fine without it -- this is decorative, not load-bearing."""
    try:
        if COLLEGE_LOGO_PATH and os.path.exists(COLLEGE_LOGO_PATH):
            with open(COLLEGE_LOGO_PATH, "rb") as f:
                return f.read()
        return _generate_placeholder_logo()
    except Exception:
        return None
