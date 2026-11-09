from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VEPT.png')
w, h = im.size
# Crop center map of VEPT
crop = im.crop((int(w * 0.1), int(h * 0.15), int(w * 0.9), int(h * 0.75)))
crop.save(r'D:\ATC\radar-trainer\scratch\VEPT_map.png')
print('VEPT map cropped.')
