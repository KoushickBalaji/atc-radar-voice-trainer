from PIL import Image

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VOCL.png')
crop = im.crop((200, 1600, 700, 2150))
crop.save(r'D:\ATC\radar-trainer\scratch\VOCL_table_exact.png')
print('Cropped exact VOCL table.')
