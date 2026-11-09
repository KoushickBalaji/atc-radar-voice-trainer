import subprocess

sectors = ['4600', '5200', '6000', '5500', '5000', '5700']
for s in sectors:
    print(f'=== SECTOR {s} ===')
    img_path = rf'D:\ATC\radar-trainer\scratch\vobg_sector_{s}.png'
    cmd = ['powershell', '-ExecutionPolicy', 'Bypass', '-File', r'D:\ATC\radar-trainer\scripts\ocr_image.ps1', '-ImagePath', img_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    for line in res.stdout.split('\n'):
        line = line.strip()
        if any(c in line for c in ['Point', 'MVA', '12°', '13°', 'VOR', 'FL', 'GND', '4600', '5200', '6000', '5500', '5000', '5700']) or (len(line) <= 5 and any(c.isupper() for c in line)):
            print('  ', line)
