from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VIJP.png')
w, h = im.size

# Crop table in lower part of VIJP: x from 0.05 to 0.65, y from 0.65 to 0.95
crop_table = im.crop((int(0.05 * w), int(0.65 * h), int(0.65 * w), int(0.95 * h)))
crop_table.save(r'D:\ATC\radar-trainer\scratch\VIJP_table.png')

# Crop center map of VIJP: x from 0.05 to 0.95, y from 0.1 to 0.7
crop_map = im.crop((int(0.05 * w), int(0.1 * h), int(0.95 * w), int(0.7 * h)))
crop_map.save(r'D:\ATC\radar-trainer\scratch\VIJP_map.png')
print('VIJP crops saved.')
