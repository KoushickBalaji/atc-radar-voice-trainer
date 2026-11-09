import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0'}
req = urllib.request.Request('https://docs.virtualnas.net/crc/stars/', headers=headers)
with urllib.request.urlopen(req) as resp:
    html = resp.read().decode('utf-8', errors='ignore')
    imgs = re.findall(r'src=["\']([^"\']+\.(?:png|jpg|jpeg|gif|webp))["\']', html)
    links = re.findall(r'href=["\']([^"\']+)["\']', html)
    print("Images in crc/stars/:", len(imgs))
    for img in imgs:
        print(" ", img)
    print("Sub-pages in crc/stars/:")
    for link in links:
        if 'stars' in link.lower():
            print(" ", link)
