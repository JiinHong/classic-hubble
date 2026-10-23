"""Bounded decoding for the observed still-AVIF KOPIS source variant."""

import io
import warnings

from .r2 import MAX_SOURCE_BYTES

MAX_AVIF_PIXELS = 40_000_000


def decode_still_avif(data: bytes):
    """Return an owned RGB image; callers must close it after use."""
    box_size = int.from_bytes(data[:4], "big")
    if (
        len(data) > MAX_SOURCE_BYTES
        or data[4:12] != b"ftypavif"
        or not 16 <= box_size <= len(data)
        or box_size % 4
        or any(data[i:i + 4] == b"avis" for i in range(16, box_size, 4))
    ):
        raise ValueError("Invalid or unsupported AVIF file type")
    try:
        from PIL import Image, ImageOps, features
    except ImportError:
        raise ValueError("AVIF decoder unavailable; Pillow is required") from None
    if not features.check("avif"):
        raise ValueError("AVIF decoder unavailable")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as original:
                if (
                    original.format != "AVIF"
                    or getattr(original, "n_frames", 1) != 1
                    or min(original.size) <= 0
                    or original.width * original.height > MAX_AVIF_PIXELS
                ):
                    raise ValueError("Unsupported AVIF dimensions or frame count")
                original.load()
                oriented = ImageOps.exif_transpose(original).convert("RGBA")
                background = Image.new("RGBA", oriented.size, "white")
                return Image.alpha_composite(background, oriented).convert("RGB")
    except (
        OSError, SyntaxError, ValueError,
        Image.DecompressionBombWarning, Image.DecompressionBombError,
    ):
        raise ValueError("Invalid or unsupported AVIF pixels") from None
