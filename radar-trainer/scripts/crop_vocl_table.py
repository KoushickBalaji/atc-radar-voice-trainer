from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VOCL.png')
w, h = im.size

# Crop table on the right side of VOCL: x from 0.6 to 0.98, y from 0.5 to 0.95
crop = im.crop((int(w * 0.55), int(h * 0.5), int(w * 0.98), int(h * 0.95)))
crop.save(r'D:\ATC\radar-trainer\scratch\VOCL_table.png')
print('VOCL table cropped.')
