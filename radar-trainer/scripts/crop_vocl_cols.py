from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\VOCL_table_exact.png')
w, h = im.size

# Let's crop:
# Col 1: S.No (x from 0 to 60)
# Col 2: Points (x from 60 to 140)
# Col 3: Latitude (x from 140 to 320)
# Col 4: Longitude (x from 320 to 500)
for name, (x0, x1) in [('sno', (0, 70)), ('pt', (70, 140)), ('lat', (140, 320)), ('lon', (320, 500))]:
    c = im.crop((x0, 30, x1, 350))
    c.save(rf'D:\ATC\radar-trainer\scratch\vocl_col_{name}.png')

print('VOCL columns saved.')
