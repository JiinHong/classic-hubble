"""Small real PDF files, with no document-generation runtime dependency."""


def make_pdf(pages=None, *, rotation=0, box=(0, 0, 300, 200)):
    pages = pages if pages is not None else [{"text": "Bach BWV 1001"}]
    objects = [b"", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    page_ids = []
    for spec in pages:
        commands = b""
        if spec.get("text"):
            text = spec["text"].encode("ascii")
            commands += b"BT /F1 12 Tf 20 150 Td (" + text + b") Tj ET\n"
        image_resource = b""
        if spec.get("image"):
            objects.append(
                b"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 "
                b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Length 3 >>\n"
                b"stream\n\x11\x22\x33\nendstream"
            )
            image_resource = f"/XObject << /Im1 {len(objects)} 0 R >>".encode()
            commands += b"q 120 0 0 80 20 20 cm /Im1 Do Q\n"
        if spec.get("path"):
            commands += b"20 20 120 80 re f\n"
        objects.append(
            f"<< /Length {len(commands)} >>\nstream\n".encode()
            + commands
            + b"endstream"
        )
        content_id = len(objects)
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [{' '.join(map(str, box))}] "
                f"/Rotate {rotation} /Resources << /Font << /F1 3 0 R >> "
            ).encode()
            + image_resource
            + f" >> /Contents {content_id} 0 R >>".encode()
        )
        page_ids.append(len(objects))
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = (
        f"<< /Type /Pages /Count {len(pages)} /Kids ["
        + " ".join(f"{i} 0 R" for i in page_ids)
        + "] >>"
    ).encode()
    data = b"%PDF-1.7\n"
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(data)
    data += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    data += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    data += (
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    ).encode()
    return data
