from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VOBG.png')
w, h = im.size

# Let's crop the main map area: x from 0.05 to 0.95, y from 0.1 to 0.85
crop_map = im.crop((int(w * 0.05), int(h * 0.1), int(w * 0.95), int(h * 0.85)))
crop_map.save(r'D:\ATC\radar-trainer\scratch\VOBG_main_map.png')
print('Saved VOBG_main_map.png')
