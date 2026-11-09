import subprocess

for code in range(ord('A'), ord('X') + 1):
    letter = chr(code)
    img_path = f'D:/ATC/radar-trainer/scratch/voci_pt_{letter}.png'
    res = subprocess.run(['powershell', '-ExecutionPolicy', 'Bypass', '-File',
                          r'D:\ATC\radar-trainer\scripts\ocr_image.ps1', img_path],
                         capture_output=True, text=True)
    text = res.stdout.strip().replace('\n', ' ')
    print(f'{letter}: {text}')
