import base64
import struct

from app.processor import ImageProcessor


class TestImageValidation:
    def test_svg_with_xml_prolog(self):
        svg_content = b'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40"/></svg>'
        valid, reason = ImageProcessor.validate_image(svg_content)
        assert valid is True
        assert reason == "valid_svg"

    def test_svg_with_long_header(self):
        long_comment = b"<!-- " + (b"A" * 200) + b" -->\n"
        svg_content = long_comment + b'<svg viewBox="0 0 100 100"><rect width="10" height="10"/></svg>'
        valid, reason = ImageProcessor.validate_image(svg_content)
        assert valid is True
        assert reason == "valid_svg"

    def test_reject_html_page(self):
        html_content = b"<!DOCTYPE html><html><head><title>404 Not Found</title></head><body>Error</body></html>"
        valid, reason = ImageProcessor.validate_image(html_content)
        assert valid is False
        assert reason == "is_html_page_not_image"

    def test_reject_tracking_pixel(self):
        # 1x1 PNG header
        png_1x1 = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", 1, 1) + b"\x08\x06\x00\x00\x00" + (b"\x00" * 30)
        valid, reason = ImageProcessor.validate_image(png_1x1)
        assert valid is False
        assert "rejected_tracking_pixel" in reason

    def test_valid_png(self):
        png_32x32 = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", 32, 32) + b"\x08\x06\x00\x00\x00" + (b"\x00" * 30)
        valid, reason = ImageProcessor.validate_image(png_32x32)
        assert valid is True
        assert "valid_png" in reason

    def test_svg_content_is_preserved(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10" fill="#fff"></rect><path fill="#010101" d="M0 0h10v10z"/></svg>'
        uri = ImageProcessor().to_data_uri(svg, "image/svg+xml")
        decoded = base64.b64decode(uri.split(",", 1)[1]).decode("utf-8")
        assert 'fill="#010101"' in decoded
        assert 'fill="#fff"' in decoded


class TestImageGeometry:
    def test_reject_widescreen_banner(self):
        # 1200x630 banner
        banner_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", 1200, 630) + b"\x08\x06\x00\x00\x00" + (b"\x00" * 30)
        valid, reason = ImageProcessor.validate_image(banner_bytes)
        assert valid is False
        assert "rejected_banner_aspect_ratio" in reason

    def test_same_pixels_with_different_png_filters(self):
        from tests.helpers import make_png

        rows = [[255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255]] * 4
        a = make_png(4, 4, rows, 0)
        b = make_png(4, 4, rows, 2)
        changed = [[0, 0, 255, 255, 255, 0, 0, 255, 0, 255, 0, 255]] * 4

        assert a != b
        assert ImageProcessor.same_pixels(a, b) is True
        assert ImageProcessor.same_pixels(a, make_png(4, 4, changed, 0)) is False
