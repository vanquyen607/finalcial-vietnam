"""Sinh icon PNG cho PWA từ Pillow (không cần file SVG rasterize)."""
from PIL import Image, ImageDraw

SIZES = [(192, "icon-192.png"), (512, "icon-512.png"), (180, "apple-touch-icon.png")]


def draw_icon(size: int) -> Image.Image:
    s = size
    scale = s / 512.0
    img = Image.new("RGB", (s, s), (0, 0, 0))
    d = ImageDraw.Draw(img)

    # Nền tối có chuyển nhẹ
    top, bottom = (18, 18, 20), (0, 0, 0)
    for y in range(s):
        t = y / max(1, s - 1)
        d.line([(0, y), (s, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))

    def pt(x: float, y: float) -> tuple[float, float]:
        return (x * scale, y * scale)

    gold = (212, 175, 55)
    light = (255, 224, 136)

    # Lục giác
    hex_pts = [(256, 60), (416, 150), (416, 330), (256, 420), (96, 330), (96, 150)]
    d.polygon([pt(*p) for p in hex_pts], outline=gold, width=max(2, int(14 * scale)))

    # Chữ A
    d.line([pt(170, 350), pt(256, 165)], fill=light, width=max(2, int(22 * scale)))
    d.line([pt(256, 165), pt(342, 350)], fill=light, width=max(2, int(22 * scale)))
    d.line([pt(203, 285), pt(309, 285)], fill=light, width=max(2, int(20 * scale)))

    return img


def main() -> None:
    import os

    out = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public", "icons"))
    os.makedirs(out, exist_ok=True)
    for size, name in SIZES:
        path = os.path.join(out, name)
        draw_icon(size).save(path, "PNG", optimize=True)
        print("wrote", path, size)


if __name__ == "__main__":
    main()
