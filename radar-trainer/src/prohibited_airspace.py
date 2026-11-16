"""Published sector volumes and constant-track, 60-second entry prediction.

Geometry uses the airport's local NM projection, like the radar. Prediction
splits the trajectory at every circle, radial and altitude crossing so even
brief incursions between snapshots are detected. Boundaries are included.
"""
import math


class ProhibitedAirspace:
    def __init__(self, airport):
        self.airport = airport
        self.zones = airport.data.get('prohibited_airspace', [])

    def nav(self):
        result = []
        for zone in self.zones:
            cx, cy = self.airport.to_nm(*zone['center'])
            points = []
            for sector in zone.get('sectors', []):
                start, end, radius = sector
                sweep = (end - start) % 360
                for i in range(math.ceil(sweep * 4) + 1):
                    angle = math.radians(start + sweep * i / math.ceil(sweep * 4))
                    points.append([cx + radius * math.sin(angle), cy + radius * math.cos(angle)])
            extra = {}
            if 'rectangle' in zone:
                rect = zone['rectangle']
                angle = math.radians(rect['bearing_true'])
                u, v = math.sin(angle), math.cos(angle)
                half = rect['runway_length_ft'] / self.airport.FT_PER_NM / 2
                length, width = half + rect['end_clearance_nm'], rect['width_nm'] / 2
                points = [[cx+a*u+b*v, cy+a*v-b*u]
                          for a, b in [(-length,-width), (length,-width), (length,width), (-length,width)]]
                extra['runway'] = [[cx-half*u, cy-half*v], [cx+half*u, cy+half*v]]
            result.append(dict(id=zone['id'], name=zone['name'], ceiling_ft=zone['ceiling_ft'],
                               points=points, label=[cx, cy], source=zone['source'], **extra))
        return result

    def evaluate(self, aircraft):
        alerts = []
        values = [aircraft.get(k) for k in ('lat', 'lon', 'alt_ft')]
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
            return alerts
        px, py = self.airport.to_nm(*values[:2])
        altitude = values[2]
        track = aircraft.get('trk', aircraft.get('hdg', 0))
        speed, climb = aircraft.get('gs', 0), aircraft.get('vs_fpm', 0)
        motion_valid = all(isinstance(v, (int, float)) and math.isfinite(v) for v in (track, speed, climb)) and speed >= 0
        vx = speed * math.sin(math.radians(track)) / 3600 if motion_valid else 0
        vy = speed * math.cos(math.radians(track)) / 3600 if motion_valid else 0
        vz = climb / 60 if motion_valid else 0
        for zone in self.zones:
            cx, cy = self.airport.to_nm(*zone['center'])
            x, y = px - cx, py - cy
            # The trainer's standard-atmosphere snapshots expose alt_ft only.
            # Prefer explicit pressure altitude when a provider supplies it.
            zone_altitude = aircraft.get('pressure_alt_ft', altitude) if zone.get('altitude_reference') == 'STD' else altitude
            if not isinstance(zone_altitude, (int, float)) or not math.isfinite(zone_altitude):
                continue
            rect = zone.get('rectangle')
            if rect:
                angle = math.radians(rect['bearing_true'])
                u, v = math.sin(angle), math.cos(angle)
                along, cross = x*u+y*v, x*v-y*u
                va, vc = vx*u+vy*v, vx*v-vy*u
                half_length = rect['runway_length_ft'] / self.airport.FT_PER_NM / 2 + rect['end_clearance_nm']
                half_width = rect['width_nm'] / 2

            def inside(t):
                xx, yy, alt = x + vx*t, y + vy*t, zone_altitude + vz*t
                if zone.get('ceiling_exclusive') and alt >= zone['ceiling_ft']:
                    return False
                if not 0 <= alt <= zone['ceiling_ft'] + 1e-7:
                    return False
                if rect:
                    return abs(along+va*t) <= half_length+1e-7 and abs(cross+vc*t) <= half_width+1e-7
                bearing = math.degrees(math.atan2(xx, yy)) % 360
                return any(math.hypot(xx, yy) <= r + 1e-7 and
                           ((bearing-start) % 360 <= (end-start) % 360 + 1e-7 or
                            abs((bearing-start+180) % 360-180) < 1e-7)
                           for start, end, r in zone['sectors'])

            if inside(0):
                alerts.append(dict(id=zone['id'], status='inside', entry_in_s=0))
                continue
            if not motion_valid:
                continue
            times = {0.0, 60.0}
            if rect:
                for position, velocity, limit in ((along, va, half_length), (cross, vc, half_width)):
                    if abs(velocity) > 1e-12:
                        times.update(((-limit-position)/velocity, (limit-position)/velocity))
            for start, end, radius in zone.get('sectors', []):
                a, b = vx*vx + vy*vy, 2*(x*vx + y*vy)
                discriminant = b*b - 4*a*(x*x + y*y-radius*radius)
                if a and discriminant >= 0:
                    times.update(((-b-math.sqrt(discriminant))/(2*a), (-b+math.sqrt(discriminant))/(2*a)))
                angle = math.radians(start)
                denominator = vx*math.cos(angle)-vy*math.sin(angle)
                if abs(denominator) > 1e-12:
                    times.add(-(x*math.cos(angle)-y*math.sin(angle))/denominator)
            if vz:
                times.update((-zone_altitude/vz, (zone['ceiling_ft']-zone_altitude)/vz))
            times = sorted(t for t in times if 0 <= t <= 60)
            for i, t in enumerate(times):
                if inside(t) or (i+1 < len(times) and inside((t+times[i+1])/2)):
                    alerts.append(dict(id=zone['id'], status='approaching', entry_in_s=math.ceil(t)))
                    break
        return alerts
