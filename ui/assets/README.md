# Logo assets

`logo-icon.png` is the icon cut from the official Safehouse logo image (house + shield, green LED, Wi-Fi signal).
Only the black background around the icon was made transparent (flood fill from the edges), so the dark inside of
the shield and the house and the blue/green glow are kept. The same PNG is embedded in `ui/index.html` as a base64
data URI so it loads on any device without extra files.

`logo-source.png` is the official logo image; `tools/extract_logo.py` recreates `logo-icon.png` from it
(needs numpy and Pillow). After regenerating, re-embed it in `ui/index.html` (two `<img class="brand-mark">`).
