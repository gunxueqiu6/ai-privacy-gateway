"""
Generate Chrome Web Store promotional tile images.
Produces 440x280, 920x680, 1400x560 PNGs with the AI Privacy Gateway branding.
"""
import os
from PIL import Image, ImageDraw, ImageFont

BG_DARK = (10, 10, 15, 255)
PRIMARY = (134, 239, 172, 255)   # #86efac
ACCENT = (167, 139, 250, 255)    # #a78bfa
BORDER = (60, 60, 70, 255)
TEXT_WHITE = (240, 240, 245, 255)
TEXT_GRAY = (160, 160, 170, 255)


def _draw_shield(draw, cx, cy, size):
    """Draw a stylized shield icon at (cx, cy) with given size."""
    w = size
    h = size * 1.15
    pad = size * 0.08

    x0, y0 = cx - w / 2, cy - h / 2
    x1, y1 = cx + w / 2, cy + h / 2
    arc_r = w / 2
    arc_top = y0 + arc_r * 0.4
    radius = int(size * 0.22)

    # Shield body
    draw.rounded_rectangle(
        [x0 + w * 0.12, arc_top, x1 - w * 0.12, y1],
        radius=radius,
        fill=BG_DARK,
    )
    draw.rectangle(
        [x0 + w * 0.12, arc_top, x1 - w * 0.12, y1 - radius],
        fill=BG_DARK,
    )

    # Shield outline
    line_w = max(1, int(size // 20))
    draw.arc(
        [x0, y0 - arc_r * 0.25, x1, y0 + arc_r * 1.15],
        start=200, end=340,
        fill=PRIMARY, width=line_w,
    )
    draw.line([(x0 + w * 0.12, arc_top), (x0 + w * 0.12, y1)],
              fill=PRIMARY, width=line_w)
    draw.line([(x1 - w * 0.12, arc_top), (x1 - w * 0.12, y1)],
              fill=PRIMARY, width=line_w)
    draw.arc(
        [x0 + w * 0.12, y1 - radius * 2, x1 - w * 0.12, y1 + radius * 0.4],
        start=0, end=180,
        fill=PRIMARY, width=line_w,
    )

    # Lock icon inside
    lock_w = size * 0.16
    lock_h = size * 0.2
    lx0, ly0 = cx - lock_w / 2, cy - lock_h * 0.1
    lx1, ly1 = cx + lock_w / 2, cy + lock_h * 0.9

    draw.rounded_rectangle(
        [lx0, ly0 + lock_h * 0.08, lx1, ly1],
        radius=max(1, int(size * 0.05)),
        fill=PRIMARY,
    )
    shackle_r = max(1, int(size // 18))
    draw.arc(
        [cx - lock_w * 0.28, ly0 - lock_h * 0.22,
         cx + lock_w * 0.28, ly0 + lock_h * 0.5],
        start=180, end=360,
        fill=PRIMARY, width=shackle_r,
    )


def _draw_decorative_circles(draw, w, h):
    """Draw subtle decorative gradient circles in background."""
    import math
    # Accent glow top-right
    for i in range(30, 0, -1):
        alpha = int(8 * (1 - i / 30))
        r = i * 8
        draw.ellipse(
            [w * 0.85 - r, h * 0.15 - r, w * 0.85 + r, h * 0.15 + r],
            fill=(*ACCENT[:3], alpha),
        )
    # Primary glow bottom-left
    for i in range(20, 0, -1):
        alpha = int(6 * (1 - i / 20))
        r = i * 6
        draw.ellipse(
            [w * 0.12 - r, h * 0.82 - r, w * 0.12 + r, h * 0.82 + r],
            fill=(*PRIMARY[:3], alpha),
        )


def create_promo(width, height):
    """Create a promotional tile with the AI Privacy Gateway branding."""
    img = Image.new("RGBA", (width, height), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Decorative background
    _draw_decorative_circles(draw, width, height)

    # Shield icon — positioned on the left
    shield_size = min(width, height) * 0.3
    _draw_shield(draw, width * 0.22, height * 0.48, int(shield_size))

    # Try to load a font, fall back to default
    title_size = max(14, min(width, height) // 12)
    subtitle_size = max(10, title_size // 2)
    try:
        title_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", title_size)
        subtitle_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", subtitle_size)
    except (OSError, IOError):
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()

    # Title
    title = "AI Privacy Gateway"
    draw.text((width * 0.38, height * 0.28), title, fill=TEXT_WHITE, font=title_font)

    # Subtitle
    subtitle = "保护 AI 对话隐私，自动脱敏敏感信息"
    draw.text((width * 0.38, height * 0.42), subtitle, fill=TEXT_GRAY, font=subtitle_font)

    # Feature bullets
    features = [
        (PRIMARY, "▸ "),  # ▸
        (TEXT_GRAY, "6 大 AI 平台全覆盖"),
        (None, ""),
        (PRIMARY, "▸ "),
        (TEXT_GRAY, "13+ 种敏感实体自动检测"),
        (None, ""),
        (PRIMARY, "▸ "),
        (TEXT_GRAY, "一键脱敏，完全本地运行"),
    ]

    bullet_size = max(9, subtitle_size - 2)
    try:
        bullet_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", bullet_size)
    except (OSError, IOError):
        bullet_font = ImageFont.load_default()

    y_start = height * 0.58
    x_start = width * 0.38
    line_spacing = bullet_size * 2.2

    # Draw three feature lines
    line_texts = [
        "▸  6 大 AI 平台全覆盖",
        "▸  13+ 种敏感实体自动检测",
        "▸  一键脱敏，完全本地运行",
    ]
    for i, line in enumerate(line_texts):
        y = y_start + i * line_spacing
        # Draw colored bullet separately
        draw.text((x_start, y), "▸", fill=PRIMARY, font=bullet_font)
        draw.text((x_start + bullet_size * 1.5, y), line[3:], fill=TEXT_GRAY, font=bullet_font)

    # Bottom tagline
    tag_size = max(8, bullet_size - 1)
    try:
        tag_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", tag_size)
    except (OSError, IOError):
        tag_font = ImageFont.load_default()
    draw.text(
        (width * 0.38, height * 0.88),
        "github.com/gunxueqiu6/ai-privacy-gateway  |  privacygw.pages.dev",
        fill=(*BORDER[:3], 200),
        font=tag_font,
    )

    return img


sizes = [(440, 280), (920, 680), (1400, 560)]
output_dir = os.path.dirname(__file__)

for w, h in sizes:
    img = create_promo(w, h)
    fname = f"promo_{w}x{h}.png"
    output_path = os.path.join(output_dir, fname)
    img.save(output_path, "PNG")
    print(f"Created {output_path} ({w}x{h})")

print("All promotional tiles generated!")
