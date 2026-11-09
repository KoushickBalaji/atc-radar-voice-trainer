from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\vobg_pt_B.png')
# The center is at (80, 80)
# Let's inspect the RGB values of pixels around the center
colors = set()
for x in range(30, 130):
    for y in range(30, 130):
        colors.add(im.getpixel((x, y)))

print('Unique colors around point B:', len(colors))
# Find dark or distinct line colors
for c in sorted(colors, key=lambda c: sum(c[:3]))[:20]:
    print(c)
