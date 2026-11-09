from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VOTR.png')
w, h = im.size
# Crop legend, table, notes
crop1 = im.crop((int(w * 0.05), int(h * 0.65), int(w * 0.95), int(h * 0.98)))
crop1.save(r'D:\ATC\radar-trainer\scratch\VOTR_bottom.png')

crop2 = im.crop((int(w * 0.1), int(h * 0.1), int(w * 0.9), int(h * 0.7)))
crop2.save(r'D:\ATC\radar-trainer\scratch\VOTR_map.png')
print('VOTR cropped.')
