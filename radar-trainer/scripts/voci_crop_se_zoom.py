from PIL import Image

im = Image.open('D:/ATC/radar-trainer/scratch/VOCI_map.png')
w, h = im.size

# Let's crop the South-East sector: x from 0.65 to 0.95, y from 0.50 to 0.85
crop = im.crop((int(0.65*w), int(0.50*h), int(0.95*w), int(0.85*h)))
crop.save('D:/ATC/radar-trainer/scratch/voci_se_zoom.png')
print('voci_se_zoom.png saved')
