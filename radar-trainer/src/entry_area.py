"""Airport-specific lateral entry placement, independent of radar zoom/range.

Published areas are lateral entry envelopes, not a model of airspace access,
vertical limits, watch hours, exclusions or inter-unit handoff agreements.
"""
import json
import math
from functools import lru_cache
from pathlib import Path


@lru_cache
def catalogue():
    path = Path(__file__).resolve().parents[1] / 'data/entry_areas.json'
    return json.loads(path.read_text(encoding='utf-8'))


def polygons(airport):
    result = []
    config = catalogue().get(airport.ICAO, {})
    for area in config.get('areas', []):
        points = []
        if area['shape'] == 'circle':
            cx, cy = airport.to_nm(*area['center'])
            points = [(cx + area['radius_nm'] * math.sin(math.radians(a)),
                       cy + area['radius_nm'] * math.cos(math.radians(a))) for a in range(360)]
        else:
            for edge in area['edges']:
                end = airport.to_nm(*edge['point'])
                if 'center' not in edge:
                    points.append(end)
                    continue
                cx, cy = airport.to_nm(*edge['center'])
                ax, ay = points[-1]
                start = math.atan2(ax-cx, ay-cy)
                finish = math.atan2(end[0]-cx, end[1]-cy)
                direction = 1 if edge['clockwise'] else -1
                sweep = (direction*(finish-start)) % (2*math.pi)
                steps = max(1, math.ceil(math.degrees(sweep)/.25))
                r1, r2 = math.hypot(ax-cx, ay-cy), math.hypot(end[0]-cx, end[1]-cy)
                for i in range(1, steps):
                    fraction = i/steps
                    angle = start + direction*sweep*fraction
                    radius = r1 + (r2-r1)*fraction
                    points.append((cx+radius*math.sin(angle), cy+radius*math.cos(angle)))
                points.append(end)
        result.append(dict(name=area['name'], points=points, source=area['source']))
    return result


def outer_crossing(airport, points, cross):
    """Last boundary crossing on the outbound ray parallel to final."""
    local = [airport.approach_geometry(x,y) for x,y in points]
    crossings = []
    for (a,c), (b,d) in zip(local,local[1:]+local[:1]):
        if abs(d-c)<1e-9:
            if abs(c-cross)<1e-6: crossings.extend([a,b])
        elif min(c,d)<=cross<=max(c,d):
            crossings.append(a+(b-a)*(cross-c)/(d-c))
    return max((x for x in crossings if x >= 0), default=None)


def entry_position(airport):
    start = airport.exercise['start']
    cross = start['cross_nm']
    published = polygons(airport)
    boundaries = [dict(p,kind='published') for p in published]
    boundaries += [dict(p,name='SMAC coverage',kind='smac') for p in airport.msaw.regions]
    intersections = [(outer_crossing(airport,b['points'],cross),b) for b in boundaries]
    intersections = [(distance,b) for distance,b in intersections if distance is not None]
    if not intersections:
        return dict(along_nm=start['along_nm'],cross_nm=cross,status='unverified',buffer_nm=None,
                    boundary=None,source=None,
                    note='No usable entry boundary on this arrival path. Saved exercise position retained; an outside-area start is not verified.')
    distance, boundary = max(intersections,key=lambda item:item[0])
    # Entry allowance is an exercise setting, not a published transfer point.
    buffer = 2.0
    along = distance + buffer
    return dict(along_nm=along,cross_nm=cross,status='boundary_based',buffer_nm=buffer,
                boundary=boundary['name'],source=boundary.get('source') or airport.msaw.config['source'],
                note='Entry is 2 NM beyond the outermost available published lateral area or SMAC coverage on this arrival path. Vertical limits and transfer agreements are not modeled.',
                incomplete=bool(catalogue().get(airport.ICAO,{}).get('unresolved')))
