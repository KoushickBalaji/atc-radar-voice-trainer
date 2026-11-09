"""SMAC-based training warning, evaluated on each simulation snapshot.

Coordinates are WGS84 [latitude, longitude]; arc edges are sampled in the
airport's local NM projection. Shared edges include their boundary and the
highest overlapping minimum wins. No terrain database or trajectory prediction.
"""
import math


def contains(x, y, polygon):
    inside = False
    for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
        dx, dy = bx - ax, by - ay
        length2 = dx * dx + dy * dy
        t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / length2)) if length2 else 0
        if math.hypot(x - ax - t * dx, y - ay - t * dy) <= 1e-6:
            return True
        if (ay > y) != (by > y) and x < ax + (y - ay) * dx / dy:
            inside = not inside
    return inside


class MinimumAltitudeMonitor:
    def __init__(self, airport):
        self.airport = airport
        self.config = airport.data.get('msaw')
        self.regions = []
        if not self.config:
            return
        conventions = {'schema_version': 1, 'coordinate_reference': 'WGS84',
                       'altitude_unit': 'ft', 'altitude_reference': 'AMSL'}
        for key, expected in conventions.items():
            if self.config.get(key, expected) != expected:
                raise ValueError(f'Unsupported SMAC {key}: expected {expected}')
        for value in self.config['points'].values():
            if (len(value) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in value)
                    or not -90 <= value[0] <= 90 or not -180 <= value[1] <= 180):
                raise ValueError('Invalid SMAC latitude/longitude')
        points = {key: airport.to_nm(*value) for key, value in self.config['points'].items()}
        for region in self.config['regions']:
            polygon = []
            for edge in region['boundary']:
                if isinstance(edge, str):
                    polygon.append(points[edge])
                    continue
                # Clockwise arc from previous point to named endpoint.
                cx, cy = airport.to_nm(*edge['center'])
                ax, ay = polygon[-1]
                bx, by = points[edge['to']]
                start = math.atan2(ax - cx, ay - cy)
                sweep = (math.atan2(bx - cx, by - cy) - start) % (2 * math.pi)
                r1, r2 = math.hypot(ax - cx, ay - cy), math.hypot(bx - cx, by - cy)
                steps = max(1, math.ceil(math.degrees(sweep) / .25))
                for i in range(1, steps):
                    f = i / steps
                    angle, radius = start + sweep * f, r1 + (r2 - r1) * f
                    polygon.append((cx + radius * math.sin(angle), cy + radius * math.cos(angle)))
                polygon.append((bx, by))
            if len(polygon) < 3 or region['minimum_ft'] <= 0:
                raise ValueError('Invalid SMAC region')
            self.regions.append(dict(id=region['id'], minimum_ft=region['minimum_ft'],
                                     points=polygon, label=airport.to_nm(*region['label'])))

    def nav(self):
        return dict(source=self.config['source'], regions=self.regions) if self.config else None

    def evaluate(self, aircraft, ils_phase=None):
        result = dict(status='unavailable', minimum_ft=None, deficit_ft=0, regions=[])
        if not self.config:
            return result
        values = [aircraft.get(k) for k in ('lat', 'lon', 'alt_ft')]
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
            return dict(result, status='invalid_position')
        x, y = self.airport.to_nm(*values[:2])
        matches = [r for r in self.regions if contains(x, y, r['points'])]
        if not matches:
            return dict(result, status='outside_coverage')
        minimum = max(r['minimum_ft'] for r in matches)
        result.update(minimum_ft=minimum, regions=[r['id'] for r in matches])
        # SMAC vectoring minima do not govern established final approach descent.
        # Require capture AND current geometry; phase alone must never hide a deviation.
        level_segment = ils_phase == 'localizer' and self.config.get('suspend_on_tracked_localizer', False)
        if self.config.get('suspend_on_tracked_ils', False) and (level_segment or ils_phase in ('glideslope', 'handoff_ready', 'approach_complete', 'complete')):
            along, cross = self.airport.approach_geometry(x, y)
            glide_alt = self.airport.glide_altitude(along)
            target_alt = self.airport.INTERCEPT_ALT_FT if level_segment else glide_alt
            error = abs(values[2] - target_alt)
            angle = abs((aircraft.get('trk', aircraft.get('hdg', 0)) - self.airport.COURSE + 180) % 360 - 180)
            cfg = self.airport.training
            on_profile = not level_segment or glide_alt >= target_alt - cfg['gs_above_ft']
            if (on_profile and 0 < along <= self.airport.approach['line_length_nm'] and abs(cross) <= cfg['stable_cross_nm']
                    and error <= cfg['stable_alt_ft'] and angle <= cfg['stable_angle_deg']):
                return dict(result, status='approach_suspended')
        deficit = max(0, minimum - values[2])
        return dict(result, status='warning' if deficit > 0 else 'clear', deficit_ft=round(deficit, 1))
