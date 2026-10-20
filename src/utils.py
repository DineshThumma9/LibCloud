import math
import logging
from typing import Union, Iterable, Optional

log = logging.getLogger(__name__)

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
    bg_color: str = "#1a1b26",
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

    if not badge_dic:
        return f'<svg width="{eff_width}" height="{eff_height}" viewBox="0 0 {eff_width} {eff_height}" xmlns="http://www.w3.org/2000/svg"/>'

    items = list(badge_dic.items()) if hasattr(badge_dic, "items") else list(badge_dic)
    # Take up to max_logos, sorted descending by frequency
    sorted_items = sorted(items, key=lambda x: x[2], reverse=True)[:eff_max_logos]

    if not sorted_items:
        return f'<svg width="{eff_width}" height="{eff_height}" viewBox="0 0 {eff_width} {eff_height}" xmlns="http://www.w3.org/2000/svg"/>'

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

                svg_elements.append(
                    f'<g class="logo-item">\n'
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
        f'style="background-color: {bg_color}; border-radius: 16px; display: block; margin: auto; max-width: 100%; height: auto;">\n'
        f'{style_block}'
        f'  {"".join(svg_elements)}\n'
        f'</svg>'
    )
