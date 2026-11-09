from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VOCL.png')
w, h = im.size
crop = im.crop((0, 1500, w, h))
crop.save(r'D:\ATC\radar-trainer\scratch\VOCL_full_bottom.png')
print('VOCL full bottom saved.')
