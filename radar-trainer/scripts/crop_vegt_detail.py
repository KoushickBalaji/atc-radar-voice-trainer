from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VEGT.png')
w, h = im.size

# Let's crop the map area: x from 0.05 to 0.75, y from 0.1 to 0.95
crop = im.crop((int(0.05 * w), int(0.1 * h), int(0.75 * w), int(0.95 * h)))
crop.save(r'D:\ATC\radar-trainer\scratch\VEGT_map_detail.png')
print('VEGT map detail saved.')
