from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any, Optional

try:
    import mss  # type: ignore
except Exception:  # pragma: no cover
    mss = None

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None

try:
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover
    pytesseract = None


@dataclass
class ScreenRegion:
    left: int
    top: int
    width: int
    height: int


def capture_screen(region: Optional[ScreenRegion] = None) -> bytes:
    if mss is None or Image is None:
        raise RuntimeError("mss and pillow packages are required for screen capture")
    image = capture_screen_image(region=region)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def capture_screen_image(region: Optional[ScreenRegion] = None) -> Any:
    if mss is None or Image is None:
        raise RuntimeError("mss and pillow packages are required for screen capture")
    with mss.mss() as sct:
        if region:
            monitor = {
                "left": region.left,
                "top": region.top,
                "width": region.width,
                "height": region.height,
            }
        else:
            monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        return Image.frombytes("RGB", shot.size, shot.rgb)


def ocr_screen(region: Optional[ScreenRegion] = None, lang: str = "eng") -> str:
    if pytesseract is None:
        raise RuntimeError("pytesseract package is not installed")
    image = capture_screen_image(region=region)
    text = pytesseract.image_to_string(image, lang=lang)
    return text.strip()
