import re


def color_html_to_rgb(html_color: str) -> tuple[int, int, int]:
    """Convert HTML color string to RGB tuple.

    Supports formats:
    - `#RGB`
    - `#RRGGBB`
    - `rgb(R, G, B)`

    The `#` is optional and the values are case-insensitive.
    Args:
        html_color: HTML color string to convert.
    """
    # normalize
    html_color_stripped = (
        html_color.lower().strip().removeprefix("#").removesuffix(";").strip()
    )

    # Try to match #RGB or #RRGGBB
    hex_match = re.match(r"^([a-f0-9]{6}|[a-f0-9]{3})$", html_color_stripped)
    if hex_match:
        hex_color = hex_match.group(1)
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    # Try to match rgb(r, g, b)
    rgb_match = re.match(
        r"^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$", html_color_stripped
    )
    if rgb_match:
        return tuple(int(x) for x in rgb_match.groups())

    # Try named colors
    named_colors = {
        "red": (255, 0, 0),
        "green": (0, 128, 0),
        "blue": (0, 0, 255),
        # Add more colors as needed
    }
    if html_color_stripped in named_colors:
        return named_colors[html_color_stripped]

    raise ValueError(f"Invalid color format: {html_color}")
