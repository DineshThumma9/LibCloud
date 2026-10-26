import base64
import logging
import struct
import zlib
from typing import Optional

log = logging.getLogger(__name__)


class ValidationResult(tuple):
    """
    Tuple representing (is_valid, reason).
    Unpacks as 2 items (is_valid, reason) for backwards compatibility with tests,
    while also exposing .mime_type, .is_valid, and .reason attributes.
    """
    def __new__(cls, is_valid: bool, reason: str, mime_type: str = ""):
        obj = super().__new__(cls, (is_valid, reason))
        obj.is_valid = is_valid
        obj.reason = reason
        obj.mime_type = mime_type
        return obj


class ImageProcessor:
    def __init__(self):
        self.validation_failures: list[dict] = []
        self._seen_validation_failures: set[str] = set()

    @staticmethod
    def validate_image(content: bytes, mime_type: str = "") -> ValidationResult:
        """
        Validates image bytes. Returns ValidationResult(is_valid, reason, mime_type).
        Checks file signatures (magic bytes), minimum size, and SVG structure.
        """
        if not content or len(content) < 40:
            return ValidationResult(False, "file_too_small_or_empty", "")

        # Reject HTML error pages masked as 200 OK
        header = content[:1024].lower()
        if b"<!doctype html" in header or b"<html" in header:
            return ValidationResult(False, "is_html_page_not_image", "")

        # SVG Validation
        if b"<svg" in header or "svg" in mime_type:
            text = content.decode("utf-8", errors="ignore").lower()
            if "<svg" not in text:
                return ValidationResult(False, "malformed_svg_missing_svg_tag", "")
            if "</svg>" not in text and "/>" not in text:
                return ValidationResult(False, "malformed_svg_unclosed", "")
            return ValidationResult(True, "valid_svg", "image/svg+xml")

        # PNG Validation
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            if len(content) < 24:
                return ValidationResult(False, "corrupt_png_header", "")
            try:
                width, height = struct.unpack(">II", content[16:24])
                if width <= 2 and height <= 2:
                    return ValidationResult(False, f"rejected_tracking_pixel_{width}x{height}", "")
                aspect = max(width, height) / max(min(width, height), 1)
                if (width >= 600 and aspect > 1.6) or aspect > 4.5:
                    return ValidationResult(False, f"rejected_banner_aspect_ratio_{width}x{height}", "")
                return ValidationResult(True, f"valid_png_{width}x{height}", "image/png")
            except Exception:
                return ValidationResult(True, "valid_png", "image/png")

        # ICO Validation
        if content.startswith(b"\x00\x00\x01\x00"):
            return ValidationResult(True, "valid_ico", "image/x-icon")

        # JPEG Validation
        if content.startswith(b"\xff\xd8\xff"):
            return ValidationResult(True, "valid_jpeg", "image/jpeg")

        # WebP Validation
        if content.startswith(b"RIFF") and b"WEBP" in content[8:16]:
            return ValidationResult(True, "valid_webp", "image/webp")

        return ValidationResult(False, "unknown_unsupported_format", "")

    @staticmethod
    def _png_pixels(content: bytes) -> Optional[tuple[int, int, int, bytes]]:
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            return None
        pos = 8
        ihdr = None
        chunks = []
        while pos + 8 <= len(content):
            length = struct.unpack(">I", content[pos:pos + 4])[0]
            kind = content[pos + 4:pos + 8]
            body = content[pos + 8:pos + 8 + length]
            if kind == b"IHDR":
                ihdr = struct.unpack(">IIBBBBB", body)
            elif kind == b"IDAT":
                chunks.append(body)
            pos += 12 + length
        if not ihdr or not chunks:
            return None
        width, height, depth, color_type, _, _, interlace = ihdr
        if depth != 8 or color_type not in (2, 6) or interlace != 0:
            return None
        bpp = 3 if color_type == 2 else 4
        stride = width * bpp
        try:
            raw = zlib.decompress(b"".join(chunks))
        except zlib.error:
            return None
        if len(raw) < height * (stride + 1):
            return None
        out = bytearray(height * stride)
        prev = bytearray(stride)
        pos = 0
        for y in range(height):
            filter_type = raw[pos]
            pos += 1
            row = bytearray(raw[pos:pos + stride])
            pos += stride
            if filter_type == 1:
                for i in range(bpp, stride):
                    row[i] = (row[i] + row[i - bpp]) & 255
            elif filter_type == 2:
                for i in range(stride):
                    row[i] = (row[i] + prev[i]) & 255
            elif filter_type == 3:
                for i in range(stride):
                    left = row[i - bpp] if i >= bpp else 0
                    row[i] = (row[i] + ((left + prev[i]) >> 1)) & 255
            elif filter_type == 4:
                for i in range(stride):
                    left = row[i - bpp] if i >= bpp else 0
                    up = prev[i]
                    up_left = prev[i - bpp] if i >= bpp else 0
                    p = left + up - up_left
                    pa = abs(p - left)
                    pb = abs(p - up)
                    pc = abs(p - up_left)
                    predictor = left if (pa <= pb and pa <= pc) else (up if pb <= pc else up_left)
                    row[i] = (row[i] + predictor) & 255
            elif filter_type != 0:
                return None
            out[y * stride:(y + 1) * stride] = row
            prev = row
        return width, height, color_type, bytes(out)

    @classmethod
    def same_pixels(cls, a: bytes, b: bytes) -> bool:
        if a == b:
            return True
        try:
            left = cls._png_pixels(a)
            right = cls._png_pixels(b)
        except Exception:
            return False
        return left is not None and left == right

    def to_data_uri(self, content: bytes, mime: str = "", source: str = "") -> Optional[str]:
        val = self.validate_image(content, mime)
        if not val.is_valid:
            log.info("Validation rejected image from %s: %s", source, val.reason)
            if source and source not in self._seen_validation_failures:
                self._seen_validation_failures.add(source)
                self.validation_failures.append({
                    "url": source,
                    "reason": val.reason,
                    "size_bytes": len(content)
                })
            return None
        detected_mime = val.mime_type or (mime if mime.startswith("image/") else "image/png")
        b64 = base64.b64encode(content).decode("utf-8")
        return f"data:{detected_mime};base64,{b64}"
