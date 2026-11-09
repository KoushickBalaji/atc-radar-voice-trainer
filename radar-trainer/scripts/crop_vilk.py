from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VILK.png')
w, h = im.size
crop = im.crop((int(0.1 * w), int(0.15 * h), int(0.9 * w), int(0.65 * h)))
crop.save(r'D:\ATC\radar-trainer\scratch\VILK_map.png')
print('VILK map saved.')
