"""Generates assets/app.ico (multi-resolution) and assets/app.png. Run: python tools/make_icon.py"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")
os.makedirs(OUT, exist_ok=True)

S = 1024


def gradient(size, c1, c2):
    base = Image.new("RGB", (size, size))
    px = base.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size)
            px[x, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
    return base


def star(d, cx, cy, r, fill):
    pts = []
    for i in range(8):
        ang = math.pi / 4 * i - math.pi / 2
        rad = r if i % 2 == 0 else r * 0.28
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    d.polygon(pts, fill=fill)


def build():
    bg = gradient(S, (14, 165, 160), (79, 70, 229)).convert("RGBA")
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((24, 24, S - 24, S - 24), radius=220, fill=255)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    img.paste(bg, (0, 0), mask)

    # soft shadow for the page
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((250, 190, 760, 840), radius=50, fill=(0, 0, 0, 110))
    sh = sh.filter(ImageFilter.GaussianBlur(28))
    img = Image.alpha_composite(img, sh)

    d = ImageDraw.Draw(img)
    # document page with folded corner
    page = [(230, 160), (610, 160), (760, 310), (760, 820), (230, 820)]
    d.polygon(page, fill=(255, 255, 255, 255))
    d.polygon([(610, 160), (610, 310), (760, 310)], fill=(205, 214, 236, 255))
    # picture inside: mountains + sun
    d.rounded_rectangle((290, 380, 700, 620), radius=24, fill=(226, 240, 255, 255))
    d.polygon([(290, 620), (430, 470), (510, 560), (590, 440), (700, 620)], fill=(14, 165, 160, 255))
    d.ellipse((600, 405, 665, 470), fill=(250, 190, 40, 255))
    # text lines
    for i, w in enumerate((410, 330, 380)):
        y = 665 + i * 46
        d.rounded_rectangle((290, y, 290 + w, y + 20), radius=10, fill=(150, 160, 190, 255))
    # sparkle (AI)
    star(d, 760, 235, 150, (255, 214, 64, 255))
    star(d, 885, 395, 62, (255, 255, 255, 255))
    return img


def make_check():
    """White tick used for checked checkboxes in the dark theme (assets/check.png)."""
    im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.line([(14, 34), (27, 47), (51, 18)], fill=(255, 255, 255, 255), width=9, joint="curve")
    im.resize((32, 32), Image.LANCZOS).save(os.path.join(OUT, "check.png"))


def main():
    make_check()
    big = build()
    big.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "app.png"))
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [big.resize((s, s), Image.LANCZOS) for s in sizes]
    frames[-1].save(os.path.join(OUT, "app.ico"), format="ICO", sizes=[(s, s) for s in sizes], append_images=frames[:-1])
    print("icon written to", OUT)


if __name__ == "__main__":
    main()
