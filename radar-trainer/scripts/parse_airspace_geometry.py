"""Test parsing and boundary verification for candidate control areas."""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / 'src'))
from airport_profiles import get_profile
from control_area import validate, boundary

COORD_RE = re.compile(r'(\d{6}(?:\.\d+)?)\s*([NS])\s*(\d{7}(?:\.\d+)?)\s*([EW])', re.I)
PAIR_RE = re.compile(r'(\d{6}(?:\.\d+)?)[NS]\s*(\d{7}(?:\.\d+)?)[EW]', re.I)

def dms(val, hemisphere):
    deglen = 2 if hemisphere in 'NS' else 3
    deg = int(val[:deglen])
    minutes = int(val[deglen:deglen+2])
    sec = float(val[deglen+2:])
    res = deg + minutes / 60.0 + sec / 3600.0
    return -res if hemisphere in 'SW' else res

def parse_coord_match(m):
    return [dms(m[1], m[2]), dms(m[3], m[4])]

def parse_first_coord(text):
    m = COORD_RE.search(text)
    if m:
        return parse_coord_match(m)
    m2 = PAIR_RE.search(text)
    if m2:
        # extract N/S and E/W
        raw = text[m2.start():m2.end()]
        ns = 'N' if 'N' in raw.upper() else 'S'
        ew = 'E' if 'E' in raw.upper() else 'W'
        return [dms(m2[1], ns), dms(m2[2], ew)]
    return None

def parse_polygon(text, airport):
    """Parse text into polygon edges, validating arc endpoints against airport."""
    # Clean up text
    t = re.sub(r'\s+', ' ', text).strip()
    if 'point of origin' not in t.lower() and not re.search(r'to\s+\d{6}', t, re.I):
        raise ValueError('No explicit closure')
        
    # Split before "excluding" or vertical limits
    t_geom = re.split(r'excluding|vertical limit|\u2022|FL\s*\d+|Airspace classified', t, flags=re.I)[0]
    
    # Find all coordinates
    # Let's see: tokens can be coordinates or arc descriptions
    # Regex find all coords with their positions
    coords = list(PAIR_RE.finditer(t_geom))
    if len(coords) < 3:
        raise ValueError('Less than 3 coordinates')
        
    edges = [{'point': parse_first_coord(t_geom[coords[0].start():coords[0].end()])}]
    
    i = 1
    while i < len(coords):
        between = t_geom[coords[i-1].end():coords[i].start()]
        if re.search(r'arc', between, re.I):
            # Arc description: e.g. "then along clockwise arc of 25 NM radius centred at 110137N 0770230E to"
            clockwise = not bool(re.search(r'counter\s*clockwise|anti\s*clockwise', between, re.I))
            rad_m = re.search(r'(\d+(?:\.\d+)?)\s*NM', between, re.I)
            if not rad_m:
                raise ValueError('Arc radius not found')
            radius_nm = float(rad_m[1])
            # Center coordinate is coords[i]
            center = parse_first_coord(t_geom[coords[i].start():coords[i].end()])
            # End coordinate is coords[i+1] if available
            if i + 1 < len(coords):
                end_pt = parse_first_coord(t_geom[coords[i+1].start():coords[i+1].end()])
                edges.append({
                    'point': end_pt,
                    'center': center,
                    'radius_nm': radius_nm,
                    'clockwise': clockwise
                })
                i += 2
            else:
                # Arc closes to starting point
                edges.append({
                    'point': edges[0]['point'],
                    'center': center,
                    'radius_nm': radius_nm,
                    'clockwise': clockwise
                })
                i += 1
        else:
            edges.append({'point': parse_first_coord(t_geom[coords[i].start():coords[i].end()])})
            i += 1
            
    return edges

if __name__ == '__main__':
    # Test on VOCB CTA A
    vocb = get_profile('VOCB')
    txt = "Area bounded by 111403N 0764025E; then along the clockwise arc of a circle of 25 NM radius centered at 110137N 0770230E to 105416N 0763812E; 105500N 0762900E; 111500N 0763100E to point of origin"
    edges = parse_polygon(txt, vocb)
    print(f'VOCB parsed {len(edges)} edges')
    area = {'shape': 'polygon', 'edges': edges}
    pts = boundary(vocb, area)
    print(f'Boundary produced {len(pts)} points successfully!')
