# Usage: python tools/extract_logo.py ui/assets/logo-source.png ui/assets/logo-icon.png /tmp/preview.png   (needs numpy + Pillow)
"""Cut the icon out of the official logo photo and turn only the surrounding black background into alpha.
The dark inside of the shield / house is kept (it is not connected to the outside background)."""
import sys
from collections import deque
import numpy as np
from PIL import Image

src, out, preview = sys.argv[1], sys.argv[2], sys.argv[3]
im = Image.open(src).convert("RGB")
x0, y0, x1, y1 = 60, 122, 184, 258            # icon + glow margin (text starts at x=190)
a = np.asarray(im.crop((x0, y0, x1, y1))).astype(np.float64)
h, w, _ = a.shape
mx = a.max(axis=2)

# background colour = median of the crop border
border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
bg = np.median(border, axis=0)
bg_level = bg.max()

# 1) flood-fill from the border through "dim" pixels: that region is background + soft glow
DIM = 95
region = np.zeros((h, w), bool)
q = deque((y, x) for y in range(h) for x in (0, w - 1)) ; q.extend((y, x) for x in range(w) for y in (0, h - 1))
while q:
    y, x = q.popleft()
    if region[y, x] or mx[y, x] > DIM:
        continue
    region[y, x] = True
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny, nx = y + dy, x + dx
        if 0 <= ny < h and 0 <= nx < w and not region[ny, nx]:
            q.append((ny, nx))

# 2) alpha: opaque for the logo itself; inside the background region it ramps with brightness (keeps the glow)
lum = mx - bg_level
alpha = np.where(region, np.clip(lum / (DIM - bg_level), 0, 1) ** 1.15, 1.0)
# 3) un-premultiply the glow so its colour stays blue/green on any background
safe = np.maximum(alpha, 1e-3)[..., None]
rgb = np.where(region[..., None], np.clip((a - bg * (1 - alpha[..., None])) / safe, 0, 255), a)
rgba = np.dstack([rgb, alpha * 255]).round().astype(np.uint8)
# trim fully transparent margins
ys, xs = np.nonzero(rgba[..., 3] > 6)
rgba = rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
Image.fromarray(rgba).save(out, optimize=True)

# preview on dark, light and magenta backgrounds (magenta makes any leftover black obvious)
icon = Image.fromarray(rgba)
s = 3
big = icon.resize((icon.width * s, icon.height * s), Image.LANCZOS)
sheet = Image.new("RGB", (big.width * 3 + 80, big.height + 40), (40, 40, 40))
for i, col in enumerate([(9, 9, 11), (248, 250, 253), (255, 0, 200)]):
    tile = Image.new("RGB", big.size, col); tile.paste(big, (0, 0), big)
    sheet.paste(tile, (20 + i * (big.width + 20), 20))
sheet.save(preview)
print("bg", bg.round(), "icon size", icon.size, "transparent px:", int((rgba[..., 3] < 10).sum()), "of", rgba.shape[0] * rgba.shape[1])
