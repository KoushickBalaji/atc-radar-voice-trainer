from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VIJP.png')
crop = im.crop((50, 1400, 1200, 1750))
crop.save(r'D:\ATC\radar-trainer\scratch\VIJP_airspace_wide.png')
print('Airspace wide cropped.')
