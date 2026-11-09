import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0'}

def check_url(url):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            links = re.findall(r'href=["\']([^"\']+)["\']', html)
            imgs = re.findall(r'src=["\']([^"\']+\.(?:png|jpg|jpeg|gif))["\']', html)
            print(f"{url} -> {len(links)} links, {len(imgs)} images")
            for img in imgs:
                print("  img:", img)
            for link in links:
                if 'stars' in link.lower():
                    print("  stars link:", link)
    except Exception as e:
        print(f"{url} -> {e}")

check_url('https://docs.virtualnas.net/')
