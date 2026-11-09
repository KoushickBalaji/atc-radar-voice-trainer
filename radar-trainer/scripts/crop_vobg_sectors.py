from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VOBG.png')
w, h = im.size

# Altitude label positions in page units (from find_vobg_elements.py):
# page width=595.32, height=807.84
# sx = w / 595.32, sy = h / 807.84
sx = w / 595.32
sy = h / 807.84

labels = {
    '4600': (385.7, 448.9),
    '5200': (526.8, 375.7),
    '6000': (408.2, 254.3),
    '5500': (116.2, 408.3),
    '5000': (266.0, 663.5),
    '5700': (411.3, 649.8),
}

for name, (px, py) in labels.items():
    cx, cy = int(px * sx), int(py * sy)
    box = (max(0, cx - 250), max(0, cy - 250), min(w, cx + 250), min(h, cy + 250))
    crop = im.crop(box)
    crop.save(rf'D:\ATC\radar-trainer\scratch\vobg_sector_{name}.png')

print('Sector crops saved.')
