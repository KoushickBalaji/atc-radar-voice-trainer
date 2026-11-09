from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VOCL.png')
w, h = im.size
sx = w / 595.32
sy = h / 807.84

# Crop around A1..F1:
pts_v = {
    'A1': (206.1, 355.3),
    'B1': (292.5, 391.4),
    'C1': (264.3, 262.8),
    'D1': (291.3, 225.4),
    'E1': (430.5, 409.6),
    'F1': (405.3, 214.1),
}

for name, (px, py) in pts_v.items():
    cx, cy = int(px * sx), int(py * sy)
    crop = im.crop((cx - 100, cy - 100, cx + 100, cy + 100))
    crop.save(rf'D:\ATC\radar-trainer\scratch\vocl_pt_{name}.png')

print('VOCL A1-F1 crops saved.')
