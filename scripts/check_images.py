import urllib.request
import re

url = 'https://www.rediff.com/business/slide-show/slide-1-air-traffic-control-tower-mumbai-airport/20131106.htm'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        imgs = re.findall(r'https?://[^\s"\'<>]+\.jpg', html)
        for img in set(imgs):
            if 'atc' in img:
                print(img)
except Exception as e:
    print('Error:', e)
