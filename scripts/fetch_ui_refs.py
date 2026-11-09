import urllib.request
import re
import os

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def fetch_page(url):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

# Check AeroExpo for Indra CWP
html = fetch_page('https://www.aeroexpo.online/aeronautic-manufacturer/indra-5014.html')
matches = re.findall(r'https?://[^\s"\'<>]+\.(?:jpg|png|webp)', html, re.IGNORECASE)
print(f"Found {len(matches)} image links on Indra page:")
for m in sorted(list(set(matches)))[:15]:
    print(m)
