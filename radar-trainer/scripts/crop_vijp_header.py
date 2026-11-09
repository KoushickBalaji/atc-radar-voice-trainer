from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VIJP.png')
w, h = im.size
crop = im.crop((int(0.05 * w), int(0.55 * h), int(0.55 * w), int(0.75 * h)))
crop.save(r'D:\ATC\radar-trainer\scratch\VIJP_table_header.png')
print('VIJP table header saved.')
