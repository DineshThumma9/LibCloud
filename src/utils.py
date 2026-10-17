import math
import logging
from typing import Union, Iterable

log = logging.getLogger(__name__)


def transform_wordcloud(
    badge_dic: Union[dict, Iterable[tuple]],
    width: int = 920,
    height: int = 540,
    bg_color: str = "#1a1b26",
    max_logos: int = 50,
    padding: int = 14,
) -> str:
    """
    Renders an official SVG logo cloud using an elliptical Archimedean spiral.
    Places the highest-frequency logos at the center and spirals outward.
    Pure Python: Zero external C/numpy dependencies.
    """
    if not badge_dic:
        return f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg"/>'

    items = list(badge_dic.items()) if hasattr(badge_dic, "items") else list(badge_dic)
    # Take up to max_logos, sorted descending by frequency
    sorted_items = sorted(items, key=lambda x: x[1], reverse=True)[:max_logos]

    if not sorted_items:
        return f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg"/>'

    max_c = max(count for _, count in sorted_items)
    min_c = min(count for _, count in sorted_items)

    center_x, center_y = width // 2, height // 2
    aspect_ratio = width / max(height, 1)

    placed_boxes: list[tuple[float, float, float, float]] = []
    svg_elements: list[str] = []

    for uri, count in sorted_items:
        # Scale size dynamically: 44px to 105px based on frequency
        if max_c == min_c:
            size = 65
        else:
            size = int(44 + ((count - min_c) / (max_c - min_c)) * 61)

        theta = 0.0
        step = 0.18
        placed = False

        while theta < 250.0:
            r = 9.5 * theta
            # Stretch horizontally by aspect_ratio so the spiral fills the rectangular canvas
            cx = center_x + (r * aspect_ratio * 0.85) * math.cos(theta) - (size / 2)
            cy = center_y + r * math.sin(theta) - (size / 2)

            box = (cx - padding, cy - padding, cx + size + padding, cy + size + padding)

            # Check AABB collision
            collision = any(
                not (box[2] <= b[0] or box[0] >= b[2] or box[3] <= b[1] or box[1] >= b[3])
                for b in placed_boxes
            )

            if not collision and 20 <= cx <= width - size - 20 and 20 <= cy <= height - size - 20:
                placed_boxes.append((cx, cy, cx + size, cy + size))
                svg_elements.append(
                    f'<image href="{uri}" x="{cx:.1f}" y="{cy:.1f}" width="{size}" height="{size}" style="border-radius: 8px;" />'
                )
                placed = True
                break

            theta += step

    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'style="background-color: {bg_color}; border-radius: 16px; display: block; margin: auto;">\n'
        f'  {"".join(svg_elements)}\n'
        f'</svg>'
    )



