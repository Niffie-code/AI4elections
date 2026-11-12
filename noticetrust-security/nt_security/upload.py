"""Upload validation: size, real file type, decoded pixels, metadata stripping."""
import io

from fastapi import HTTPException, UploadFile
from PIL import Image

MAGIC = {
    "JPEG": (b"\xff\xd8\xff",),
    "PNG": (b"\x89PNG\r\n\x1a\n",),
}
EXT = {"JPEG": ".jpg", "PNG": ".png"}


def _reject(code: int, msg: str):
    # Generic messages on purpose: never echo parser internals back to the client.
    raise HTTPException(status_code=code, detail=msg)


async def read_limited(file: UploadFile, max_bytes: int) -> bytes:
    """Read the upload in chunks and stop as soon as the limit is crossed."""
    buf = bytearray()
    while chunk := await file.read(64 * 1024):
        buf.extend(chunk)
        if len(buf) > max_bytes:
            _reject(413, "File too large (max 10 MB).")
    if not buf:
        _reject(422, "Empty file.")
    return bytes(buf)


def validate_and_clean_image(data: bytes, max_pixels: int, max_dimension: int):
    """Return (clean_bytes, extension). Never trusts filename or client content-type.

    The image is fully decoded and re-encoded, which drops EXIF/GPS and any trailing
    or polyglot payload bytes appended after the image data.
    """
    fmt = next((f for f, sigs in MAGIC.items() if any(data.startswith(s) for s in sigs)), None)
    if fmt is None:
        _reject(415, "Only JPEG or PNG images are accepted.")
    try:
        img = Image.open(io.BytesIO(data))          # reads the header only
        if img.format != fmt:
            _reject(415, "Only JPEG or PNG images are accepted.")
        w, h = img.size
        if w < 1 or h < 1 or w > max_dimension or h > max_dimension or w * h > max_pixels:
            _reject(422, "Image dimensions are too large.")
        if getattr(img, "n_frames", 1) > 1:         # animated PNG / multi-frame
            _reject(422, "Animated images are not supported.")
        img.verify()                                 # structural check; invalidates the object
        img = Image.open(io.BytesIO(data))
        img.load()                                   # full decode, bounded by the checks above
        if img.mode not in ("RGB", "L", "RGBA"):
            img = img.convert("RGB")
        if fmt == "JPEG" and img.mode == "RGBA":
            img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, format=fmt)                    # no exif / pnginfo passed -> metadata dropped
        return out.getvalue(), EXT[fmt]
    except HTTPException:
        raise
    except Exception:                                # corrupt, truncated, bomb, parser bug
        _reject(422, "Could not read this image.")
