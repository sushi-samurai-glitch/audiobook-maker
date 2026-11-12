"""Draw the app icon (a music note on the app's amber tile) as a 1024 px PNG; PyInstaller turns it into .icns.

python packaging/make_icon.py packaging/icon.png"""
import sys

from PIL import Image, ImageDraw

SIZE = 1024
BG, TILE, AMBER = (18, 19, 23, 0), (42, 38, 32, 255), (242, 169, 59, 255)


def draw(path):
    img = Image.new("RGBA", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(img)
    margin = 100  # macOS icons leave room around the tile
    d.rounded_rectangle([margin, margin, SIZE - margin, SIZE - margin], radius=185, fill=TILE)
    # A beamed pair of eighth notes.
    stem_w, head_rx, head_ry = 34, 92, 70
    left, right, top, bottom = 360, 640, 300, 690
    for x in (left, right):
        d.ellipse([x - 2 * head_rx + stem_w, bottom - head_ry, x + stem_w, bottom + head_ry], fill=AMBER)
        d.rectangle([x, top, x + stem_w, bottom], fill=AMBER)
    d.polygon([(left, top), (right + stem_w, top - 60), (right + stem_w, top + 40), (left, top + 100)], fill=AMBER)
    img.save(path)


if __name__ == "__main__":
    draw(sys.argv[1] if len(sys.argv) > 1 else "icon.png")
