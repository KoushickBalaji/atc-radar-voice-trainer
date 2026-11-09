from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VEGT.png')
w, h = im.size
print('VEGT size:', w, h)
# Landscape: 2339 x 1653
# Map is on the left/center, instructions on the bottom/right
crop_map = im.crop((int(0.05 * w), int(0.05 * h), int(0.95 * w), int(0.75 * h)))
crop_map.save(r'D:\ATC\radar-trainer\scratch\VEGT_map.png')
print('VEGT map saved.')
