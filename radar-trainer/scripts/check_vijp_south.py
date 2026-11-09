from PIL import Image
import subprocess

# Let's crop around the center/south of VIJP map: y from 0.35 to 0.65, x from 0.1 to 0.9
im = Image.open(r'D:\ATC\radar-trainer\scratch\smac_images\VIJP.png')
w, h = im.size
crop = im.crop((int(0.1 * w), int(0.35 * h), int(0.9 * w), int(0.65 * h)))
crop.save(r'D:\ATC\radar-trainer\scratch\VIJP_south_map.png')

cmd = ['powershell', '-ExecutionPolicy', 'Bypass', '-File', r'D:\ATC\radar-trainer\scripts\ocr_image.ps1', '-ImagePath', r'D:\ATC\radar-trainer\scratch\VIJP_south_map.png']
res = subprocess.run(cmd, capture_output=True, text=True)
for line in res.stdout.split('\n'):
    if any(k in line for k in ['3300', '3800', 'MVA', 'ARP']):
        print(line)
