from PIL import Image
import subprocess

im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VIJP.png')
w, h = im.size
# table text box is at y from 0.65 to 0.75, x from 0.05 to 0.45
crop = im.crop((int(0.05 * w), int(0.67 * h), int(0.35 * w), int(0.74 * h)))
crop.save(r'D:\ATC\radar-trainer\scratch\VIJP_table_box.png')

cmd = ['powershell', '-ExecutionPolicy Bypass', '-File', r'D:\ATC\radar-trainer\scripts\ocr_image.ps1', '-ImagePath', r'D:\ATC\radar-trainer\scratch\VIJP_table_box.png']
res = subprocess.run(['powershell', '-ExecutionPolicy', 'Bypass', '-File', r'D:\ATC\radar-trainer\scripts\ocr_image.ps1', '-ImagePath', r'D:\ATC\radar-trainer\scratch\VIJP_table_box.png'], capture_output=True, text=True)
print(res.stdout)
