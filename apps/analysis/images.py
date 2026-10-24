"""Image validation and preparation (all in memory, nothing written to disk)."""
import base64
import io

from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "MPO"}
AI_MAX_SIDE = 1024
THUMB_MAX_SIDE = 320


class InvalidImage(ValueError):
    pass


def load_image(raw_bytes, max_bytes):
    if not raw_bytes:
        raise InvalidImage("The file is empty.")
    if len(raw_bytes) > max_bytes:
        raise InvalidImage(f"Images must be smaller than {max_bytes // (1024 * 1024)} MB.")
    try:
        probe = Image.open(io.BytesIO(raw_bytes))
        probe.verify()
        image = Image.open(io.BytesIO(raw_bytes))
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise InvalidImage("That file is not a readable image.") from None
    if image.format not in ALLOWED_FORMATS:
        raise InvalidImage("Please upload a JPG, PNG or WEBP image.")
    image = ImageOps.exif_transpose(image)
    return image.convert("RGB")


def _jpeg_bytes(image, max_side, quality):
    copy = image.copy()
    copy.thumbnail((max_side, max_side))
    buffer = io.BytesIO()
    copy.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def for_ai(image):
    """JPEG bytes sized for Gemma (keeps token cost and latency down)."""
    return _jpeg_bytes(image, AI_MAX_SIDE, 85)


def thumbnail_data_uri(image):
    """Small JPEG data URI for the private dashboard."""
    data = base64.b64encode(_jpeg_bytes(image, THUMB_MAX_SIDE, 75)).decode("ascii")
    return f"data:image/jpeg;base64,{data}"
