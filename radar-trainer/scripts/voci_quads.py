from PIL import Image

im = Image.open('D:/ATC/radar-trainer/scratch/VOCI_map.png')
w, h = im.size

# Let's crop 4 detailed quadrants of the map to see every line and letter:
# Map center is around (w*0.5, h*0.5)
cx, cy = int(w * 0.5), int(h * 0.5)

nw = im.crop((0, 0, cx + 50, cy + 50))
ne = im.crop((cx - 50, 0, w, cy + 50))
sw = im.crop((0, cy - 50, cx + 50, h))
se = im.crop((cx - 50, cy - 50, w, h))

nw.save('D:/ATC/radar-trainer/scratch/voci_nw.png')
ne.save('D:/ATC/radar-trainer/scratch/voci_ne.png')
sw.save('D:/ATC/radar-trainer/scratch/voci_sw.png')
se.save('D:/ATC/radar-trainer/scratch/voci_se.png')
print('VOCI 4 quadrants saved!')
