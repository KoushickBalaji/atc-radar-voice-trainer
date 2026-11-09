import urllib.request
import re
import os

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def get_images(url):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            matches = re.findall(r'src=["\']([^"\']+\.(?:png|jpg|jpeg|gif))["\']', html, re.I)
            print(f"From {url}: {len(matches)}")
            for m in matches:
                print(' ', m)
            return matches
    except Exception as e:
        print('Error:', e)
        return []

get_images('https://vstars.rosscarlson.dev/')
get_images('https://docs.virtualnas.net/crc/views/stars/')
