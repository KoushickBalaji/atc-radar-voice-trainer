from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VEBN.png')
w, h = im.size

# In VEBN.png, let's crop around y=0.45 to 0.55 across x=0.2 to 0.8
crop = im.crop((int(w * 0.2), int(h * 0.45), int(w * 0.8), int(h * 0.58)))
crop.save(r'D:\ATC\radar-trainer\scratch\VEBN_dividing_line.png')
print('Dividing line crop saved.')
