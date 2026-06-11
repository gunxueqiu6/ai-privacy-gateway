"""
Generate browser extension PNG icons using Pillow.
Produces 16/48/128 px shield icons with gradient background.
"""
import os

from PIL import Image, ImageDraw, ImageFont

# Color palette matching the website dark theme
BG_DARK = (10, 10, 15, 255)
PRIMARY = (134, 239, 172, 255)   # #86efac — green accent
ACCENT = (167, 139, 250, 255)    # #a78bfa — purple accent
BORDER = (60, 60, 70, 255)


def _draw_shield(draw, size, pad, radius):
    """Draw a stylized shield shape."""
    cx, cy = size / 2, size / 2
    w, h = size - 2 * pad, size - 2 * pad
    x0, y0 = pad, pad
    x1, y1 = pad + w, pad + h

    # Shield: top arc + bottom rounded rect
    arc_r = w / 2
    arc_top = y0 + arc_r * 0.45

    # Filled shield background
    draw.rounded_rectangle(
        [x0 + w * 0.15, arc_top, x1 - w * 0.15, y1],
        radius=radius,
        fill=BG_DARK,
    )
    draw.rectangle(
        [x0 + w * 0.15, arc_top, x1 - w * 0.15, y1 - radius],
        fill=BG_DARK,
    )

    # Shield outline
    draw.arc(
        [x0, y0 - arc_r * 0.3, x1, y0 + arc_r * 1.2],
        start=200,
        end=340,
        fill=PRIMARY,
        width=max(1, size // 28),
    )
    draw.line(
        [(x0 + w * 0.15, arc_top), (x0 + w * 0.15, y1)],
        fill=PRIMARY,
        width=max(1, size // 28),
    )
    draw.line(
        [(x1 - w * 0.15, arc_top), (x1 - w * 0.15, y1)],
        fill=PRIMARY,
        width=max(1, size // 28),
    )
    draw.arc(
        [x0 + w * 0.15, y1 - radius * 2, x1 - w * 0.15, y1 + radius * 0.5],
        start=0,
        end=180,
        fill=PRIMARY,
        width=max(1, size // 28),
    )


def create_icon(size):
    """Create a shield icon with gradient accents."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = size * 0.18
    radius = size * 0.18

    # Shield shape
    _draw_shield(draw, size, pad, int(radius))

    # Lock icon in center (simplified)
    cx, cy = size / 2, size / 2
    lock_w = size * 0.18
    lock_h = size * 0.22
    lx0, ly0 = cx - lock_w / 2, cy - lock_h * 0.15
    lx1, ly1 = cx + lock_w / 2, cy + lock_h

    # Lock body
    draw.rounded_rectangle(
        [lx0, ly0 + lock_h * 0.1, lx1, ly1],
        radius=max(1, int(size * 0.05)),
        fill=PRIMARY,
    )
    # Lock shackle
    shackle_r = max(1, size // 22)
    draw.arc(
        [
            cx - lock_w * 0.3,
            ly0 - lock_h * 0.2,
            cx + lock_w * 0.3,
            ly0 + lock_h * 0.55,
        ],
        start=180,
        end=360,
        fill=PRIMARY,
        width=shackle_r,
    )

    return img


sizes = [16, 48, 128]
output_dir = os.path.dirname(__file__)

for size in sizes:
    img = create_icon(size)
    output_path = os.path.join(output_dir, f"icon{size}.png")
    img.save(output_path, "PNG")
    print(f"Created {output_path} ({size}x{size})")

print("All icons generated successfully!")
