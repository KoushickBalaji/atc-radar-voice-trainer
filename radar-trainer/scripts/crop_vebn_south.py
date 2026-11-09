from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VEBN.png')
w, h = im.size

# Let's crop the bottom half of the map where 2300 and 2500 meet
crop = im.crop((int(w * 0.15), int(h * 0.35), int(w * 0.85), int(h * 0.65)))
crop.save(r'D:\ATC\radar-trainer\scratch\VEBN_south_boundary.png')
print('VEBN south boundary cropped.')
