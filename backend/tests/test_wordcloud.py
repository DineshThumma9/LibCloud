import base64

from app.services.render import transform_wordcloud


class TestWordcloudSvg:
    def test_empty_input_uses_preset_dimensions(self):
        svg = transform_wordcloud({}, preset="readme")
        assert 'width="920"' in svg
        assert 'height="540"' in svg

    def test_max_logos_keeps_highest_counts(self):
        badges = [
            ("A", "data:image/png;base64,AAA", 10),
            ("B", "data:image/png;base64,BBB", 5),
            ("C", "data:image/png;base64,CCC", 1),
        ]
        svg = transform_wordcloud(badges, preset="web", max_logos=2)
        assert svg.count('class="logo-item"') == 2
        assert "A (10)" in svg
        assert "B (5)" in svg
        assert "C (1)" not in svg

    def test_dark_theme_adds_plates(self):
        badges = [("A", "data:image/png;base64,AAA", 1)]
        svg = transform_wordcloud(badges, preset="web", theme="dark")
        assert svg.count('class="logo-plate"') == 1
        assert 'fill="#f1f5f9"' in svg
        assert '<rect width="1400" height="900" rx="16" fill="#1a1b26"' in svg

    def test_light_theme_omits_plates(self):
        badges = [("A", "data:image/png;base64,AAA", 1)]
        svg = transform_wordcloud(badges, preset="web", theme="light")
        assert 'class="logo-plate"' not in svg
        assert '<rect width="1400" height="900" rx="16" fill="#ffffff"' in svg

    def test_theme_inferred_from_light_background(self):
        badges = [("A", "data:image/png;base64,AAA", 1)]
        svg = transform_wordcloud(badges, preset="web", bg_color="#f8fafc")
        assert 'class="logo-plate"' not in svg

    def test_light_only_svg_gets_dark_plate(self):
        white_svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path fill="#ffffff" d="M0 0h10v10z"/></svg>'
        uri = "data:image/svg+xml;base64," + base64.b64encode(white_svg).decode()
        badges = [("A", uri, 1)]
        dark = transform_wordcloud(badges, preset="web", theme="dark")
        light = transform_wordcloud(badges, preset="web", theme="light")
        assert 'fill="#475569"' in dark
        assert 'fill="#475569"' in light
