"""Published missed approach exercise. Positions use the airport's local NM frame."""
import json
import math
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'data' / 'missed_approaches'


def procedure_for(airport):
    approach = airport.approach or {}
    if not approach.get('procedure_id'):
        return None
    path = DATA / f'{airport.ICAO}.json'
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    if data['icao'] != airport.ICAO:
        raise ValueError('Missed approach airport mismatch')
    matches = [p for p in data['procedures'] if
               (p['runway'],p['approach_id']) == (approach['runway'],approach['procedure_id'])]
    if len(matches) > 1:
        raise ValueError('Duplicate runway and approach variant')
    if not matches:
        return None
    p = matches[0]
    if 'hold_id' in p:
        hold = airport.holds.get(p['hold_id'])
        if not hold or hold['fix'] != p['legs'][-1].get('fix') or p['fixes'][hold['fix']] != hold['position']:
            raise ValueError('Missed approach has an invalid holding pattern reference')
    if not p['legs'] or p['legs'][-1]['type'] != 'direct' or not p['source']:
        raise ValueError('Missed procedure must end at a documented fix')
    for leg in p['legs']:
        if leg['type'] not in ('straight','radial','direct') or leg['alt_ft'] <= 0:
            raise ValueError('Unsupported missed approach leg')
        if leg['type'] != 'straight' and (leg['fix'] not in p['fixes'] or leg['turn'] not in ('left','right')):
            raise ValueError('Invalid missed approach fix or turn')
    return p


class MissedApproach:
    def __init__(self, airport):
        self.airport = airport
        self.plan = procedure_for(airport)
        self.overrides = {}
        self.index = 0
        self.turn_established = False
        self.direct_entry_heading = None
        self.last_targets = {}
        self.start_alt = None
        self.climb_only = False

    def assign(self, axis, value, *, conditional):
        self.overrides[axis] = value
        if axis == 'ALT':
            self.climb_only = conditional

    def brief(self):
        if not self.plan:
            return None
        return dict(name=self.plan['name'], source=self.plan['source'], approach_id=self.plan['approach_id'], runway=self.plan['runway'],
                    legs=[leg['label'] for leg in self.plan['legs']], max_kias=self.plan['max_kias'],
                    overrides=dict(self.overrides))

    def update(self, ac):
        plan = self.plan
        if self.start_alt is None:
            self.start_alt = ac['alt_ft']
        leg = plan['legs'][self.index]
        along, cross = self.airport.approach_geometry(ac['x'], ac['y'])
        kind = leg['type']
        course = self.airport.COURSE
        reached = False
        result = None
        if kind == 'straight':
            # If triggered early, continue inbound on the selected final track.
            # From the initial vectoring position this intercept is a training approximation.
            if along > 0:
                course += max(-25,min(25,math.degrees(math.atan2(cross,2.5))))
            reached = (not leg.get('past_threshold') or along <= 0) and ac['alt_ft'] >= leg['alt_ft']
        else:
            fx, fy = self.airport.to_nm(*plan['fixes'][leg['fix']])
            dx, dy = ac['x']-fx, ac['y']-fy
            extend = False
            if kind == 'radial':
                angle = math.radians(leg['course_true'])
                cross = dx*math.cos(angle)-dy*math.sin(angle)
                outbound = dx*math.sin(angle)+dy*math.cos(angle)
                course = leg['course_true']-max(-30,min(30,math.degrees(math.atan2(cross,2))))
                reached = (outbound > 0 and abs(cross) < .35 and
                           abs((ac['trk']-leg['course_true']+180)%360-180) <= 12 and ac['alt_ft'] >= leg['alt_ft'])
            else:
                course = math.degrees(math.atan2(-dx,-dy)) % 360
                if self.direct_entry_heading is None:
                    self.direct_entry_heading = ac['hdg']
                # On an early/high go-around CCB can be inside the aircraft's
                # turn circle. Continuous direct pursuit then orbits the fix.
                # Start the published turn, then extend its tangent as needed
                # to give the simulated aircraft room to intercept the fix.
                direction = -1 if leg['turn'] == 'left' else 1
                speed_ms = ac.get('gs',ac.get('cas_kt',185)) * 1852 / 3600
                radius = speed_ms**2 / (9.81*math.tan(math.radians(20))) / 1852
                hdg = math.radians(ac['hdg'])
                cx = dx + direction*radius*math.cos(hdg)
                cy = dy - direction*radius*math.sin(hdg)
                turned = (direction*(ac['hdg']-self.direct_entry_heading))%360
                extend = not self.turn_established and turned >= 60 and math.hypot(cx,cy) < radius+.15
                inbound_error = abs((ac['trk']-course+180)%360-180)
                # CCB is close to the runway. An outbound pass near the VOR
                # must not count as returning to it on the final leg.
                reached = self.turn_established and inbound_error < 45 and math.hypot(dx,dy) <= .5
            # Issue intermediate headings to force the published turn direction
            # until established. BlueSky's ordinary HDG command takes the shortest turn.
            direction = -1 if leg['turn'] == 'left' else 1
            remaining = (direction*(course-ac['hdg'])) % 360
            if min(remaining,360-remaining) < 10:
                self.turn_established = True
            if extend and not self.turn_established:
                course = ac['hdg']
            elif not self.turn_established:
                course = ac['hdg'] + direction*min(70,remaining)
        if reached and 'HDG' not in self.overrides:
            if self.index + 1 < len(plan['legs']):
                self.index += 1
                self.turn_established = False
                return self.update(ac)
            target_alt = self.overrides.get('ALT',leg['alt_ft'])
            result = 'missed_finished' if abs(ac['alt_ft']-target_alt) <= 100 else 'missed_fix_altitude'
        targets = {'HDG':round(course%360,1), 'ALT':round(max(self.start_alt,leg['alt_ft'])),
                   'SPD':min(plan['max_kias'],self.last_targets.get('SPD', ac.get('cas_kt') or plan['max_kias']))}
        targets.update(self.overrides)
        if self.climb_only and 'ALT' in self.overrides:
            # An advance climb instruction can be below an early trigger altitude.
            # Never convert that climb into a descent.
            targets['ALT'] = max(self.start_alt, targets['ALT'])
            if targets['ALT'] != self.overrides['ALT']:
                msg_alt = ' Already above the assigned climb altitude at go-around; maintain altitude for ATC.'
            else:
                msg_alt = ''
        else:
            msg_alt = ''
        lines = [f"{axis} {ac['id']} {value}" for axis,value in targets.items() if self.last_targets.get(axis) != value]
        self.last_targets = targets
        msg = leg['label'] if 'HDG' not in self.overrides else 'Following the ATC heading. Continue vectoring by voice.'
        if result:
            msg = ('Reached the holding fix at the assigned altitude. Exercise complete.' if result=='missed_finished'
                   else 'Reached the holding fix outside the assigned altitude tolerance. Exercise paused.')
        return result or 'going_around', msg+msg_alt, lines

