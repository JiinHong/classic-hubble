"""Validate the observed, uncompressed 24-bit Windows bitmap layout."""

import struct


def bitmap_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 54:
        raise ValueError("Invalid or unsupported bitmap")
    signature, size, reserved1, reserved2, offset = struct.unpack_from("<2sIHHI", data)
    header, width, height, planes, bits, compression, image_size, _, _, colors, important = (
        struct.unpack_from("<IiiHHIIiiII", data, 14)
    )
    if (
        signature != b"BM" or size != len(data) or reserved1 or reserved2
        or offset != 54 or header != 40 or width <= 0 or height == 0
        or planes != 1 or bits != 24 or compression != 0 or colors or important
        or width * abs(height) > 40_000_000
    ):
        raise ValueError("Invalid or unsupported bitmap")
    # RGB scanlines are padded to DWORD boundaries, including top-down bitmaps.
    payload_size = ((width * bits + 31) // 32) * 4 * abs(height)
    if image_size not in (0, payload_size) or offset + payload_size != len(data):
        raise ValueError("Invalid or unsupported bitmap")
    return width, abs(height)
