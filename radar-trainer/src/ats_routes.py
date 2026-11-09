"""Published ATS tracks clipped to the configured lateral control-area boundary."""
import json
import math
from pathlib import Path

from msaw import contains

DATA = Path(__file__).resolve().parents[1] / 'data' / 'ats_routes'


def boundary_exit(start, end, polygon):
    """First outward crossing along the finite route leg, ignoring tangent vertices."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    cuts = {0., 1.}
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        ex, ey = b[0] - a[0], b[1] - a[1]
        det = dx * ey - dy * ex
        if abs(det) < 1e-10:
            continue
        ax, ay = a[0] - start[0], a[1] - start[1]
        t, u = (ax * ey - ay * ex) / det, (ax * dy - ay * dx) / det
        if 0 < t < 1 and -1e-9 <= u <= 1 + 1e-9:
            cuts.add(t)
    ordered = sorted(cuts)
    for lo, hi in zip(ordered, ordered[1:]):
        mid = (lo + hi) / 2
        if not contains(start[0] + dx * mid, start[1] + dy * mid, polygon):
            return (start[0] + dx * lo, start[1] + dy * lo)
    return None


class AirportRoutes:
    def __init__(self, airport):
        self.branches = []
        path = DATA / (airport.ICAO + '.json')
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding='utf-8'))
        area = next(a for a in airport.control_areas.areas if a['id'] == data['area'])
        self.area = area['name']
        self.edition = data['edition']
        self.fixes = data['fixes']
        for route, record in data['routes'].items():
            for names in record['branches']:
                points = [airport.to_nm(*self.fixes[name]) for name in names]
                for i, (a, b) in enumerate(zip(points, points[1:])):
                    edge = boundary_exit(a, b, area['points'])
                    if edge is not None:
                        self.branches.append(dict(route=route, via=names[1], outside=names[i+1],
                                                  fixes=names[:i+1], points=points[:i+1] + [edge]))
                        break
                else:
                    # A route ending inside the area has no next fix beyond an edge.
                    self.branches.append(dict(route=route, via=names[1], outside=None,
                                              fixes=names, points=points))

    def overlay(self):
        grouped = {}
        for branch in self.branches:
            key = (tuple(branch['points']), branch['outside'])
            if key not in grouped:
                grouped[key] = dict(points=branch['points'], waypoint=branch['outside'], routes=[])
            grouped[key]['routes'].append(branch['route'])
        return list(grouped.values())

    def entry(self, route, via, route_distance_nm=None):
        branch = next((b for b in self.branches if (b['route'], b['via']) == (route, via)), None)
        if not branch or not branch['outside']:
            raise ValueError(f'No boundary entry for {route} via {via}')
        points = branch['points']
        index = len(points) - 2
        leg_length = math.dist(points[index], points[index+1])
        offset = leg_length - min(1, leg_length / 2)
        if route_distance_nm is not None:
            # Measure the remaining flight path from the hub along the published legs.
            offset = route_distance_nm
            for index, (inner, outer) in enumerate(zip(points, points[1:])):
                leg_length = math.dist(inner, outer)
                if offset <= leg_length and leg_length > 0:
                    break
                offset -= leg_length
            else:
                raise ValueError(f'Requested entry exceeds the modeled {route} branch via {via}')
        inner, outer = points[index:index+2]
        dx, dy = outer[0] - inner[0], outer[1] - inner[1]
        fraction = offset / leg_length
        names = branch['fixes'] + [branch['outside']]
        return dict(x=inner[0] + dx*fraction, y=inner[1] + dy*fraction,
                    heading=math.degrees(math.atan2(-dx, -dy)) % 360,
                    inbound=list(reversed(names[:index+1])), outside=names[index+1])
