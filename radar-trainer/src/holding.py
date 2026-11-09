"""Published, timed holding patterns. Guidance advances on the aircraft's simulation tick."""
import json
import math
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'data' / 'holds'


def load_patterns(airport):
    path = DATA / f'{airport.ICAO}.json'
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    patterns = {}
    for p in data['patterns']:
        if (data['icao'] != airport.ICAO or p['id'] in patterns or not p['source']
                or p['turn'] not in ('left', 'right') or len(p['position']) != 2
                or not 0 <= p['inbound_magnetic_deg'] <= 360 or
                min(p['minimum_ft'], p['leg_seconds'], p['max_kias']) <= 0):
            raise ValueError(f'Invalid holding pattern in {path.name}')
        patterns[p['id']] = p
    return patterns


def delta(angle):
    return (angle + 180) % 360 - 180


def entry_for(arrival, inbound, direction):
    relative = ((arrival - inbound) * direction) % 360
    if 110 <= relative < 180:
        return 'teardrop'
    if 180 <= relative < 290:
        return 'parallel'
    return 'direct'


class HoldingFlight:
    def __init__(self, airport, pattern, altitude, expected=None):
        self.pattern = pattern
        self.fix = airport.to_nm(*pattern['position'])
        self.course = (pattern['inbound_magnetic_deg'] + pattern['variation_east_deg']) % 360
        self.direction = 1 if pattern['turn'] == 'right' else -1
        self.altitude = altitude
        self.expected = expected
        self.speed = None
        self.phase = 'to fix'
        self.entry = None
        self.entry_leg = False
        self.circuits = 0
        self.elapsed = 0
        self.last_targets = {}

    def brief(self):
        return dict(fix=self.pattern['fix'], phase=self.phase, entry=self.entry, circuits=self.circuits,
                    altitude_ft=self.altitude, expected=self.expected, max_kias=self.pattern['max_kias'],
                    minimum_ft=self.pattern['minimum_ft'])

    def update(self, ac, dt):
        if dt <= 0:
            return []
        dx, dy = ac['x'] - self.fix[0], ac['y'] - self.fix[1]
        angle = math.radians(self.course)
        along = dx * math.sin(angle) + dy * math.cos(angle)
        cross = dx * math.cos(angle) - dy * math.sin(angle)
        track = ac.get('trk', ac['hdg'])
        bearing = math.degrees(math.atan2(-dx, -dy))
        if self.phase == 'to fix' and math.hypot(dx, dy) <= .16:
            self.entry = entry_for(track, self.course, self.direction)
            self.entry_leg = self.entry != 'direct'
            self.phase = 'turn outbound'
        if self.phase == 'inbound' and along >= -.08 and abs(cross) < .4 and abs(delta(track-self.course)) < 35:
            if not self.entry_leg:
                self.circuits += 1
            self.entry_leg = False
            self.phase = 'turn outbound'

        outbound = self.course + 180
        if self.entry_leg and self.entry == 'teardrop':
            outbound -= self.direction * 30
        inbound = self.course - max(-40, min(40, math.degrees(math.atan2(cross, 1.2))))
        drift = max(-25, min(25, delta(track-ac['hdg'])))
        target = bearing - drift
        if self.phase == 'to fix':
            # If the fix lies inside the turn circle, extend straight until a
            # tangent to the fix is possible instead of orbiting the station.
            speed = (ac.get('gs') or ac.get('cas_kt') or self.pattern['max_kias']) * 1852 / 3600
            radius = speed**2 / (9.81 * math.tan(math.radians(20))) / 1852
            side = 1 if delta(bearing-track) >= 0 else -1
            heading = math.radians(track)
            cx = dx + side * radius * math.cos(heading)
            cy = dy - side * radius * math.sin(heading)
            if math.hypot(cx, cy) < radius and abs(delta(bearing-track)) > 25:
                target = ac['hdg']
        elif self.phase.startswith('turn'):
            turning_out = self.phase == 'turn outbound'
            destination = (outbound if turning_out else inbound) - drift
            direction = self.direction
            if self.entry_leg and turning_out:
                direction = 1 if delta(destination-ac['hdg']) >= 0 else -1
            remaining = (direction * (destination-ac['hdg'])) % 360
            if min(remaining, 360-remaining) < 7:
                self.phase = 'outbound' if turning_out else 'inbound'
                self.elapsed = 0
                target = destination
            else:
                # BlueSky takes the shortest turn to each selected heading.
                target = ac['hdg'] + direction * min(65, remaining)
        elif self.phase == 'outbound':
            target = outbound - drift
            if along <= 0:
                self.elapsed += dt
            if self.elapsed >= self.pattern['leg_seconds']:
                self.phase = 'turn inbound'
        elif self.phase == 'inbound':
            target = inbound - drift

        if self.speed is None:
            self.speed = min(ac.get('cas_kt') or self.pattern['max_kias'], self.pattern['max_kias'])
        targets = dict(HDG=round(target % 360, 1), ALT=self.altitude, SPD=self.speed)
        commands = [f"{axis} {ac['id']} {value}" for axis, value in targets.items()
                    if self.last_targets.get(axis) != value]
        self.last_targets = targets
        return commands
