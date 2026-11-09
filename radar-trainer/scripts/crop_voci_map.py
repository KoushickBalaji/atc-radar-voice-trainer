from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VOCI.png')
w, h = im.size

# Crop map of VOCI: x from 0.05 to 0.95, y from 0.1 to 0.7
crop = im.crop((int(w * 0.05), int(h * 0.1), int(w * 0.95), int(h * 0.7)))
crop.save(r'D:\ATC\radar-trainer\scratch\VOCI_map.png')
print('VOCI map saved.')
