import base64
import math
import logging
import re
from typing import Union, Iterable, Optional

log = logging.getLogger(__name__)

LOGO_PLATE = "#f1f5f9"
DARK_PLATE = "#475569"
DEFAULT_DARK_BG = "#1a1b26"
DEFAULT_LIGHT_BG = "#ffffff"

_HEX_COLOR = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_SVG_PAINT = re.compile(
    r'(?:fill|stroke|stop-color|color)\s*[:=]\s*["\']?\s*(#[0-9a-fA-F]{3,6}|rgba?\([^)]*\)|white|black|currentColor)',
    re.IGNORECASE,
)


def _relative_luminance(color: str) -> Optional[float]:
    value = color.strip()
    if value.lower() == "white":
        return 1.0
    if value.lower() == "black":
        return 0.0
    if value.lower() == "currentcolor":
        return None
    if value.lower().startswith("rgb"):
        numbers = re.findall(r"[\d.]+", value)
        if len(numbers) < 3:
            return None
        channels = [min(float(n), 255) / 255 for n in numbers[:3]]
    else:
        match = _HEX_COLOR.match(value)
        if not match:
            return None
        digits = match.group(1)
        if len(digits) == 3:
            digits = "".join(c * 2 for c in digits)
        channels = [int(digits[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _is_light_color(color: str) -> bool:
    luminance = _relative_luminance(color)
    return luminance is not None and luminance > 0.5


def _svg_min_luminance(uri: str) -> Optional[float]:
    if not uri.startswith("data:image/svg+xml;base64,"):
        return None
    try:
        svg = base64.b64decode(uri.split(",", 1)[1]).decode("utf-8", errors="ignore")
    except Exception:
        return None
    luminances = [
        luminance
        for color in _SVG_PAINT.findall(svg)
        if (luminance := _relative_luminance(color)) is not None
    ]
    return min(luminances) if luminances else None


def _plate_color(uri: str, theme: str) -> Optional[str]:
    min_luminance = _svg_min_luminance(uri)
    light_icon = min_luminance is not None and min_luminance > 0.6
    if theme == "dark":
        return DARK_PLATE if light_icon else LOGO_PLATE
    return DARK_PLATE if light_icon else None


CLOUD_PRESETS = {
    "web": {
        "width": 1400,
        "height": 900,
        "min_size": 36,
        "max_size": 92,
        "padding": 10,
        "max_logos": None,
    },
    "readme": {
        "width": 920,
        "height": 540,
        "min_size": 30,
        "max_size": 72,
        "padding": 8,
        "max_logos": None,
    },
}


def transform_wordcloud(
    badge_dic: Union[dict, Iterable[tuple]],
    preset: str = "web",
    width: Optional[int] = None,
    height: Optional[int] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    bg_color: Optional[str] = None,
    theme: Optional[str] = None,
    max_logos: Optional[int] = None,
    padding: Optional[int] = None,
) -> str:
    """
    Renders an official SVG logo cloud using an elliptical Archimedean spiral.
    Places the highest-frequency logos at the center and spirals outward.
    Supports configurable presets ('web' for max-space full-view, 'readme' for GitHub cards).
    Pure Python: Zero external C/numpy dependencies.
    """
    cfg = CLOUD_PRESETS.get(preset, CLOUD_PRESETS["web"])
    eff_width = width if width is not None else cfg["width"]
    eff_height = height if height is not None else cfg["height"]
    eff_min_size = min_size if min_size is not None else cfg["min_size"]
    eff_max_size = max_size if max_size is not None else cfg["max_size"]
    eff_padding = padding if padding is not None else cfg["padding"]
    eff_max_logos = max_logos if max_logos is not None else cfg["max_logos"]
    theme_value = theme.strip().lower() if isinstance(theme, str) else None
    resolved_theme = theme_value if theme_value in ("dark", "light") else (
        "light" if bg_color and _is_light_color(bg_color) else "dark"
    )
    eff_bg_color = bg_color or (DEFAULT_LIGHT_BG if resolved_theme == "light" else DEFAULT_DARK_BG)

    empty_svg = (
        f'<svg width="{eff_width}" height="{eff_height}" viewBox="0 0 {eff_width} {eff_height}" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{eff_width}" height="{eff_height}" rx="16" fill="{eff_bg_color}" /></svg>'
    )

    if not badge_dic:
        return empty_svg

    items = list(badge_dic.items()) if hasattr(badge_dic, "items") else list(badge_dic)
    # Take up to max_logos, sorted descending by frequency
    sorted_items = sorted(items, key=lambda x: x[2], reverse=True)[:eff_max_logos]

    if not sorted_items:
        return empty_svg

    max_c = max(count for _, _, count in sorted_items)
    min_c = min(count for _, _, count in sorted_items)

    center_x, center_y = eff_width // 2, eff_height // 2
    aspect_ratio = eff_width / max(eff_height, 1)

    placed_boxes: list[tuple[float, float, float, float]] = []
    svg_elements: list[str] = []

    # Dynamic spiral growth based on logo sizes
    spiral_growth = max(5.0, (eff_min_size + eff_max_size) / 13.5)
    margin = 16

    for norm_name, uri, count in sorted_items:
        if max_c == min_c:
            size = eff_min_size
        else:
            size = int(eff_min_size + ((count - min_c) / (max_c - min_c)) * (eff_max_size - eff_min_size))

        theta = 0.0
        step = 0.15
        placed = False

        while theta < 400.0:
            r = spiral_growth * theta
            # Stretch horizontally by aspect_ratio so the spiral fills the rectangular canvas
            cx = center_x + (r * aspect_ratio * 0.85) * math.cos(theta) - (size / 2)
            cy = center_y + r * math.sin(theta) - (size / 2)

            box = (cx - eff_padding, cy - eff_padding, cx + size + eff_padding, cy + size + eff_padding)

            # Check AABB collision
            collision = any(
                not (box[2] <= b[0] or box[0] >= b[2] or box[3] <= b[1] or box[1] >= b[3])
                for b in placed_boxes
            )

            if not collision and margin <= cx <= eff_width - size - margin and margin <= cy <= eff_height - size - margin:
                placed_boxes.append((cx, cy, cx + size, cy + size))
                tooltip = f"{norm_name} ({count})"

                pill_w = max(len(tooltip) * 8 + 18, 60)
                pill_x = max(10, min(eff_width - pill_w - 10, cx + size / 2 - pill_w / 2))
                pill_y = cy - 26 if (cy + size + 32 > eff_height) else cy + size + 6
                text_x = pill_x + pill_w / 2
                text_y = pill_y + 15

                plate = ""
                plate_color = _plate_color(uri, resolved_theme)
                if plate_color:
                    pad = max(2.0, size * 0.06)
                    radius = max(6.0, size * 0.16)
                    plate = (
                        f'  <rect class="logo-plate" x="{cx - pad:.1f}" y="{cy - pad:.1f}" '
                        f'width="{size + pad * 2:.1f}" height="{size + pad * 2:.1f}" '
                        f'rx="{radius:.1f}" fill="{plate_color}" />\n'
                    )

                svg_elements.append(
                    f'<g class="logo-item">\n'
                    f'{plate}'
                    f'  <image href="{uri}" x="{cx:.1f}" y="{cy:.1f}" width="{size}" height="{size}" style="border-radius: 8px;" />\n'
                    f'  <g class="logo-tooltip">\n'
                    f'    <rect x="{pill_x:.1f}" y="{pill_y:.1f}" width="{pill_w}" height="22" rx="6" fill="#0f172a" stroke="#38bdf8" stroke-width="1.2" />\n'
                    f'    <text x="{text_x:.1f}" y="{text_y:.1f}" text-anchor="middle" fill="#f8fafc" font-size="11" font-family="system-ui, -apple-system, sans-serif" font-weight="600">{tooltip}</text>\n'
                    f'  </g>\n'
                    f'</g>'
                )

                placed = True
                break

            theta += step

    log.info("Placed %d / %d logos in wordcloud canvas (%dx%d, preset=%s)", len(svg_elements), len(sorted_items), eff_width, eff_height, preset)

    style_block = (
        '  <style>\n'
        '    .logo-item { cursor: pointer; }\n'
        '    .logo-item image { transform-origin: center; transition: transform 0.2s ease, filter 0.2s ease; }\n'
        '    .logo-item:hover image { filter: drop-shadow(0 0 10px rgba(56, 189, 248, 0.5)); transform: scale(1.08); }\n'
        '    .logo-item .logo-tooltip { opacity: 0; pointer-events: none; transition: opacity 0.15s ease-in-out; }\n'
        '    .logo-item:hover .logo-tooltip { opacity: 1; }\n'
        '  </style>\n'
    )

    return (
        f'<svg width="{eff_width}" height="{eff_height}" viewBox="0 0 {eff_width} {eff_height}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'style="display: block; margin: auto; max-width: 100%; height: auto;">\n'
        f'  <rect width="{eff_width}" height="{eff_height}" rx="16" fill="{eff_bg_color}" />\n'
        f'{style_block}'
        f'  {"".join(svg_elements)}\n'
        f'</svg>'
    )
