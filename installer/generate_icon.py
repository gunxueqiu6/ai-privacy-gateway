"""
Generate a simple app icon for AI Privacy Gateway installer.
Produces installer/app.ico — a multi-size .ico file with a shield-like design.
"""
import struct
from io import BytesIO
from PIL import Image, ImageDraw


def _make_frame(size: int) -> Image.Image:
    """Create a single RGBA frame of the given size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background: rounded rectangle (shield-like)
    margin = max(1, size // 12)
    body = (
        margin,
        margin,
        size - margin - 1,
        size - margin - 1,
    )
    color = (56, 189, 248)  # sky blue #38bdf8
    draw.rounded_rectangle(body, radius=size // 5, fill=color)

    # Letter "P" drawn manually (avoids font-rendering issues at small sizes)
    letter_color = (255, 255, 255)
    cx = size // 2
    stem_w = max(2, size // 8)
    bowl_r = max(2, size // 5)
    top = margin + 2
    bottom = size - margin - 2

    # Vertical stem
    stem_left = cx - stem_w // 2
    draw.rectangle([stem_left, top, stem_left + stem_w, bottom], fill=letter_color)

    # Horizontal top bar
    draw.rectangle([stem_left, top, size - margin - 2, top + stem_w], fill=letter_color)

    # Bowl (upper-right arc)
    bowl_left = stem_left
    bowl_top = top
    bowl_right = bowl_left + bowl_r * 2
    bowl_bottom = bowl_top + bowl_r * 2
    draw.pieslice(
        [bowl_left, bowl_top, bowl_right, bowl_bottom],
        start=-90,
        end=90,
        fill=letter_color,
    )
    return img


def _build_ico(sizes: list[int]) -> bytes:
    """Build a true multi-resource .ico file with embedded PNG data."""
    frames = [_make_frame(s) for s in sizes]

    header = struct.pack("<HHH", 0, 1, len(frames))   # reserved, type=ico, count
    dir_entries = b""
    image_data = b""
    offset = 6 + 16 * len(frames)                       # header + all dir entries

    for i, img in enumerate(frames):
        buf = BytesIO()
        img.save(buf, format="png")
        png_data = buf.getvalue()

        w, h = img.size
        entry = struct.pack(
            "<BBBBHHII",
            w if w < 256 else 0,
            h if h < 256 else 0,
            0,      # color palette (unused)
            0,      # reserved
            1,      # color planes
            32,     # bits per pixel
            len(png_data),
            offset,
        )
        dir_entries += entry
        image_data += png_data
        offset += len(png_data)

    return header + dir_entries + image_data


def create_icon() -> bytes:
    """Return bytes of a multi-size .ico file (16, 24, 32, 48)."""
    return _build_ico([16, 24, 32, 48])


if __name__ == "__main__":
    import os

    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "app.ico")
    data = create_icon()
    with open(out_path, "wb") as f:
        f.write(data)
    print(f"Icon saved: {out_path} ({len(data)} bytes)")
