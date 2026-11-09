import subprocess

for col in ['sno', 'pt', 'lat', 'lon']:
    print(f'=== COL {col} ===')
    cmd = ['powershell', '-ExecutionPolicy', 'Bypass', '-File', r'D:\ATC\radar-trainer\scripts\ocr_image.ps1', '-ImagePath', rf'D:\ATC\radar-trainer\scratch\vocl_col_{col}.png']
    res = subprocess.run(cmd, capture_output=True, text=True)
    for l in res.stdout.split('\n'):
        if l.strip():
            print(' ', l.strip())
