"""
Generate og-image.png (1200×630) for social sharing previews.
Matches the promo tile branding.
"""
import os
from PIL import Image, ImageDraw, ImageFont

BG_DARK = (10, 10, 15, 255)
PRIMARY = (134, 239, 172, 255)   # #86efac
ACCENT = (167, 139, 250, 255)    # #a78bfa
TEXT_WHITE = (240, 240, 245, 255)
TEXT_GRAY = (160, 160, 170, 255)

W, H = 1200, 630


def _draw_shield(draw, cx, cy, size):
    w = size
    h = size * 1.15
    x0, y0 = cx - w / 2, cy - h / 2
    x1, y1 = cx + w / 2, cy + h / 2
    arc_r = w / 2
    arc_top = y0 + arc_r * 0.4
    radius = int(size * 0.22)
    line_w = max(1, int(size // 20))

    # Shield body
    draw.rounded_rectangle(
        [x0 + w * 0.12, arc_top, x1 - w * 0.12, y1],
        radius=radius, fill=BG_DARK,
    )
    draw.rectangle(
        [x0 + w * 0.12, arc_top, x1 - w * 0.12, y1 - radius],
        fill=BG_DARK,
    )
    # Outline
    draw.arc(
        [x0, y0 - arc_r * 0.25, x1, y0 + arc_r * 1.15],
        start=200, end=340, fill=PRIMARY, width=line_w,
    )
    draw.line([(x0 + w * 0.12, arc_top), (x0 + w * 0.12, y1)],
              fill=PRIMARY, width=line_w)
    draw.line([(x1 - w * 0.12, arc_top), (x1 - w * 0.12, y1)],
              fill=PRIMARY, width=line_w)
    draw.arc(
        [x0 + w * 0.12, y1 - radius * 2, x1 - w * 0.12, y1 + radius * 0.4],
        start=0, end=180, fill=PRIMARY, width=line_w,
    )
    # Lock
    lock_w = size * 0.16
    lock_h = size * 0.2
    lx0, ly0 = cx - lock_w / 2, cy - lock_h * 0.1
    lx1, ly1 = cx + lock_w / 2, cy + lock_h * 0.9
    draw.rounded_rectangle(
        [lx0, ly0 + lock_h * 0.08, lx1, ly1],
        radius=max(1, int(size * 0.05)), fill=PRIMARY,
    )
    shackle_r = max(1, int(size // 18))
    draw.arc(
        [cx - lock_w * 0.28, ly0 - lock_h * 0.22,
         cx + lock_w * 0.28, ly0 + lock_h * 0.5],
        start=180, end=360, fill=PRIMARY, width=shackle_r,
    )


def _draw_glow(draw):
    # Accent glow top-right
    for i in range(40, 0, -1):
        alpha = int(6 * (1 - i / 40))
        r = i * 10
        draw.ellipse(
            [W * 0.88 - r, H * 0.12 - r, W * 0.88 + r, H * 0.12 + r],
            fill=(*ACCENT[:3], alpha),
        )
    # Primary glow bottom-left
    for i in range(25, 0, -1):
        alpha = int(5 * (1 - i / 25))
        r = i * 8
        draw.ellipse(
            [W * 0.08 - r, H * 0.85 - r, W * 0.08 + r, H * 0.85 + r],
            fill=(*PRIMARY[:3], alpha),
        )


img = Image.new("RGBA", (W, H), BG_DARK)
draw = ImageDraw.Draw(img)

_draw_glow(draw)

# Shield — center-left
shield_size = int(min(W, H) * 0.38)
_draw_shield(draw, W * 0.28, H * 0.48, shield_size)

# Title
try:
    title_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 52)
    subtitle_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 28)
    tag_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)
except (OSError, IOError):
    title_font = ImageFont.load_default()
    subtitle_font = ImageFont.load_default()
    tag_font = ImageFont.load_default()

draw.text((W * 0.48, H * 0.28), "AI Privacy Gateway", fill=TEXT_WHITE, font=title_font)
draw.text((W * 0.48, H * 0.42), "保护 AI 对话隐私，自动脱敏敏感信息", fill=TEXT_GRAY, font=subtitle_font)

# Feature bullets
features = ["▸ 6 大 AI 平台全覆盖", "▸ 13+ 种敏感实体自动检测", "▸ 一键脱敏，完全本地运行"]
try:
    bullet_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)
except (OSError, IOError):
    bullet_font = ImageFont.load_default()

y = H * 0.58
for i, line in enumerate(features):
    draw.text((W * 0.48, y + i * 42), "▸", fill=PRIMARY, font=bullet_font)
    draw.text((W * 0.48 + 30, y + i * 42), line[3:], fill=TEXT_GRAY, font=bullet_font)

# Bottom tagline
draw.text(
    (W * 0.48, H * 0.88),
    "github.com/gunxueqiu6/ai-privacy-gateway",
    fill=(*PRIMARY[:3], 180),
    font=tag_font,
)

# Output to website-astro/public/
output_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "website-astro", "public", "og-image.png")
output_path = os.path.normpath(output_path)
img.save(output_path, "PNG")
print(f"Created {output_path} ({W}x{H})")
