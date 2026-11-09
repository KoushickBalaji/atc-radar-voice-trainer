from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VEBN.png')
w, h = im.size

# Crop map of VEBN: x from 0.1 to 0.9, y from 0.15 to 0.65
crop = im.crop((int(w * 0.1), int(h * 0.15), int(w * 0.9), int(h * 0.65)))
crop.save(r'D:\ATC\radar-trainer\scratch\VEBN_map.png')
print('VEBN map cropped.')
