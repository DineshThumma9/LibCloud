import base64
import logging
import re
import struct
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
                if width / max(height, 1) > 1.6 or height / max(width, 1) > 1.6:
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
    def sanitize_svg(svg_text: str) -> str:
        """
        1. Strips hardcoded white background <rect> elements to eliminate bright box contrast.
        2. Inverts near-black fills to white (#ffffff) for visibility on dark backgrounds.
        3. Injects fill="#ffffff" if no fill is defined anywhere (preventing default black).
        """
        svg_text = re.sub(
            r'<rect[^>]*fill=["\'](?:#fff(?:fff)?|white)["\'][^>]*\/?>',
            '',
            svg_text,
            flags=re.IGNORECASE,
        )
        svg_text = re.sub(
            r'<rect[^>]*style=["\'][^"\']*fill:\s*(?:#fff(?:fff)?|white)[^"\']*["\'][^>]*\/?>',
            '',
            svg_text,
            flags=re.IGNORECASE,
        )

        dark_colors = {
            "#000", "#000000", "#111", "#111111", "#161618",
            "#181717", "#1a1a1a", "#222", "#222222", "#2d3748", "black"
        }

        def replace_fill(match):
            val = match.group(1).lower().strip()
            if val in dark_colors:
                return 'fill="#ffffff"'
            return match.group(0)

        svg_text = re.sub(r'fill=["\']([^"\']+)["\']', replace_fill, svg_text, flags=re.IGNORECASE)

        def replace_style_fill(match):
            val = match.group(1).lower().strip()
            if val in dark_colors:
                return 'fill: #ffffff'
            return match.group(0)

        svg_text = re.sub(r'fill:\s*([^;}"\']+)', replace_style_fill, svg_text, flags=re.IGNORECASE)

        if "fill=" not in svg_text and "fill:" not in svg_text:
            svg_text = re.sub(r'<svg\b([^>]*)>', r'<svg\1 fill="#ffffff">', svg_text, count=1, flags=re.IGNORECASE)

        return svg_text

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
        if detected_mime == "image/svg+xml":
            try:
                text = content.decode("utf-8", errors="ignore")
                sanitized = self.sanitize_svg(text)
                content = sanitized.encode("utf-8")
            except Exception as e:
                log.debug("Failed sanitizing SVG from %s: %s", source, e)
        b64 = base64.b64encode(content).decode("utf-8")
        return f"data:{detected_mime};base64,{b64}"
