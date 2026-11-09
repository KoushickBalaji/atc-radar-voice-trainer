from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VOTR.png')
w, h = im.size

# Save 4 quadrants of the map area
# Map area: x from 0.05 to 0.95, y from 0.12 to 0.65
mx0, my0, mx1, my1 = int(0.05 * w), int(0.12 * h), int(0.95 * w), int(0.65 * h)
cx, cy = (mx0 + mx1) // 2, (my0 + my1) // 2

nw = im.crop((mx0, my0, cx, cy))
ne = im.crop((cx, my0, mx1, cy))
sw = im.crop((mx0, cy, cx, my1))
se = im.crop((cx, cy, mx1, my1))

nw.save(r'D:\ATC\radar-trainer\scratch\votr_nw.png')
ne.save(r'D:\ATC\radar-trainer\scratch\votr_ne.png')
sw.save(r'D:\ATC\radar-trainer\scratch\votr_sw.png')
se.save(r'D:\ATC\radar-trainer\scratch\votr_se.png')
print('4 quadrants saved.')
