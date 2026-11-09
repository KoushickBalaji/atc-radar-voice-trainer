from PIL import Image

im = Image.open('D:/ATC/radar-trainer/scratch/VOCI_overlay_test.png')
w, h = im.size

# Crop central cluster
crop = im.crop((int(0.4*w), int(0.35*h), int(0.75*w), int(0.7*h)))
crop.save('D:/ATC/radar-trainer/scratch/voci_cluster.png')
print('voci_cluster.png saved')
