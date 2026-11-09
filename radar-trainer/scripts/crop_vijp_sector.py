from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VIJP.png')
w, h = im.size

# In VIJP, the northern sector is in the top center of the map
# x from 0.2 to 0.8, y from 0.15 to 0.45
crop = im.crop((int(0.2 * w), int(0.15 * h), int(0.8 * w), int(0.45 * h)))
crop.save(r'D:\ATC\radar-trainer\scratch\VIJP_north_sector.png')
print('VIJP north sector cropped.')
