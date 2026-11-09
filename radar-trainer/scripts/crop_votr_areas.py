from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VOTR.png')
w, h = im.size
sx = w / 595.32
sy = h / 807.84

# Crop around:
# Area A (top / north): y from 0.15 to 0.45, x from 0.2 to 0.8
crop_a = im.crop((int(0.2 * w), int(0.15 * h), int(0.8 * w), int(0.45 * h)))
crop_a.save(r'D:\ATC\radar-trainer\scratch\votr_crop_a.png')

# Area B (center / east): y from 0.35 to 0.65, x from 0.4 to 0.9
crop_b = im.crop((int(0.4 * w), int(0.35 * h), int(0.9 * w), int(0.65 * h)))
crop_b.save(r'D:\ATC\radar-trainer\scratch\votr_crop_b.png')

# Area C (west): y from 0.35 to 0.65, x from 0.1 to 0.5
crop_c = im.crop((int(0.1 * w), int(0.35 * h), int(0.5 * w), int(0.65 * h)))
crop_c.save(r'D:\ATC\radar-trainer\scratch\votr_crop_c.png')

print('VOTR area crops saved.')
