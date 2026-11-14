"""Bounded ILS capture exercise. Geometry/guidance approximation, not avionics.

The controller must explicitly clear the selected ILS before automatic capture. The controller
supplies vectors, level and speed. Training tolerances are not chart minima.
"""
import math
from uuid import uuid4
from readback import callsign_telephony
from airport_profiles import get_profile
from missed_approach import MissedApproach
from holding import HoldingFlight

TOO_HIGH = 'Unable, too high for approach.'

MISSED_END = ('missed_finished', 'missed_fix_altitude')


class ILSTrainer:
    def __init__(self, airport=None, callsign=None, route_entry=False):
        self.route_entry = route_entry
        self.airport = airport or get_profile()
        self.cfg = self.airport.training
        self.callsign = callsign or self.airport.exercise['start']['callsign']
        self.phase = 'awaiting_clearance'
        self.go_around_on_handoff = False
        self.repeat_after_missed = False
        self.retry_ready = False
        self.assigned_altitude = None
        self.tower_reminder_sent = False
        self.landing_cleared = False
        self.below_seen = False
        self.stable_s = 0.0
        self.guidance_s = 1.0
        self.missed = MissedApproach(self.airport)
        self.handover = self.airport.exercise.get('tower_handover')
        self.pilot_call = None
        if self.handover is not None:
            if not (self.missed.plan and self.airport.tower and
                    0 < self.handover['go_around_nm'] < self.handover['request_nm'] <= self.airport.approach['line_length_nm']):
                raise ValueError('Tower handover training requires ordered final distances, a tower and a modeled missed approach')
        self.hold = None
        self.hold_after_missed = False
        self.status = {'phase': self.phase, 'message': 'Issue an explicit ILS approach clearance before capture.'}

    def clear_approach(self, altitude_ft):
        if altitude_ft is None:
            return 'Aircraft altitude unavailable.'
        if altitude_ft >= 5000 and (self.assigned_altitude is None or self.assigned_altitude >= 5000):
            return TOO_HIGH
        if self.phase == 'awaiting_clearance':
            self.phase = 'armed'

    def clear_landing(self):
        self.landing_cleared = True
        self.pilot_call = None
        if self.phase == 'handoff_ready':
            self.phase = 'complete'

    def announce(self, phrase):
        self.pilot_call = dict(id=uuid4().hex, callsign=self.callsign,
                               text=f'{callsign_telephony(self.callsign)}, {phrase}.')

    def start_go_around(self):
        self.go_around_on_handoff = False
        self.assigned_altitude = None
        self.landing_cleared = False
        self.repeat_after_missed = True
        self.phase = 'going_around'
        self.pilot_call = None

    def manual_command(self, line):
        parts = line.upper().split()
        if len(parts) < 3 or parts[1] != self.callsign:
            return
        axis = parts[0]
        if axis == 'ALT':
            self.assigned_altitude = float(parts[2])
        if axis == 'HDG' and (self.hold or self.phase == 'going_around') or (
                axis in ('HDG', 'ALT') and self.phase in ('localizer', 'glideslope')):
            retry = self.retry_ready or bool(self.hold) or self.phase == 'going_around'
            keep_missed = self.phase != 'going_around' and not self.hold_after_missed
            missed, armed, level = self.missed, self.go_around_on_handoff, self.assigned_altitude
            self.__init__(self.airport, self.callsign, self.route_entry)
            if keep_missed:
                self.missed, self.go_around_on_handoff = missed, armed
            self.assigned_altitude = level
            self.retry_ready = retry
        elif self.hold:
            if axis == 'ALT':
                self.hold.altitude = self.assigned_altitude
            elif axis == 'SPD':
                self.hold.speed = float(parts[2])
        elif self.phase == 'going_around' and axis in ('ALT', 'SPD'):
            self.missed.assign(axis, float(parts[2]), conditional=False)

    def start_hold(self, pattern, altitude, expected=None):
        self.pilot_call = None
        self.hold_after_missed = self.hold_after_missed or self.phase in ('going_around','missed_finished')
        self.assigned_altitude = altitude
        self.hold = HoldingFlight(self.airport, pattern, altitude, expected)
        self.phase = 'holding'
        if self.hold_after_missed:
            self.go_around_on_handoff = False

    def update(self, ac, dt):
        if self.phase == 'going_around':
            self.phase, message, commands = self.missed.update(ac)
            pattern = self.airport.holds.get(self.missed.plan.get('hold_id'))
            if self.phase == 'missed_finished' and pattern:
                altitude = self.missed.overrides.get('ALT', self.missed.plan['legs'][-1]['alt_ft'])
                if altitude >= pattern['minimum_ft']:
                    self.start_hold(pattern, altitude)
                    self.announce('holding, request vectors for another approach')
                    return self.update(ac, dt)
                self.phase = 'missed_fix_altitude'
                message = 'Assigned altitude below the published holding minimum. Exercise paused.'
            if self.repeat_after_missed and self.phase in MISSED_END:
                self.__init__(self.airport, self.callsign, self.route_entry)
                self.retry_ready = True
                self.announce('request vectors for another approach')
                message = 'Missed approach complete. Vector the aircraft for another attempt and issue a fresh ILS clearance.'
                commands = []
            self.status = dict(phase=self.phase, message=message, missed_approach=self.missed.brief(), go_around_on_handoff=self.go_around_on_handoff)
            return commands
        if self.hold:
            commands = self.hold.update(ac, dt)
            message = f"{self.callsign} Â· {self.hold.pattern['fix']} Â· {self.hold.phase}"
            self.status = dict(phase=self.phase, message=message, holding=self.hold.brief(),
                               missed_approach=self.missed.brief())
            return commands
        if self.phase in MISSED_END:
            return []
        cb, cfg = self.airport, self.cfg
        along, cross = cb.approach_geometry(ac['x'], ac['y'])
        angle = abs((ac.get('trk', ac['hdg']) - cb.COURSE + 180) % 360 - 180)
        gs_alt = cb.glide_altitude(along)
        error = ac['alt_ft'] - gs_alt
        speed = ac.get('cas_kt') or 0
        speed_ok = cfg['speed_min_kt'] <= speed <= cfg['speed_max_kt']
        level_ok = abs(ac['alt_ft'] - cb.INTERCEPT_ALT_FT) <= cfg['altitude_tolerance_ft'] and abs(ac.get('vs_fpm', 0)) <= cfg['level_vs_max_fpm']
        commands = []
        if dt > 0 and self.phase not in ('handoff_ready', 'approach_complete', 'complete', 'missed'):
            continuing_final = self.handover and self.phase == 'glideslope'
            vectoring = (self.route_entry or self.retry_ready) and self.phase in ('awaiting_clearance', 'armed')
            if not vectoring and not continuing_final and (along < cfg['miss_distance_nm'] or ac['alt_ft'] < cb.exercise['pre_capture_floor_ft'] and self.phase != 'glideslope'):
                self.phase = 'missed'
            if self.phase == 'armed':
                if (cfg['localizer_min_nm'] <= along <= cfg['localizer_max_nm'] and abs(cross) <= cfg['localizer_cross_nm'] and angle <= cfg['intercept_max_deg']
                        and level_ok and speed_ok and error < -cfg['below_margin_ft']):
                    self.phase = 'localizer'
                    self.announce('localizer established, request landing clearance')
                    self.below_seen = True
            if self.phase in ('localizer', 'glideslope'):
                if abs(cross) > cfg['track_loss_nm'] or angle > cfg['track_loss_deg']:
                    self.pilot_call = None
                    self.phase = 'missed'
                elif self.phase == 'localizer':
                    if error < -cfg['below_margin_ft']:
                        self.below_seen = True
                    if self.below_seen and -cfg['gs_below_ft'] <= error <= cfg['gs_above_ft'] and abs(cross) <= cfg['stable_cross_nm'] and angle <= cfg['stable_angle_deg'] and speed_ok:
                        self.phase = 'glideslope'
                    elif error > cfg['above_miss_ft']:
                        self.phase = 'missed'  # Never capture from above.
            if self.phase in ('localizer', 'glideslope'):
                self.guidance_s += dt
                if self.guidance_s >= cfg['guidance_interval_s']:
                    self.guidance_s = 0
                    correction = max(-cfg['max_correction_deg'], min(cfg['max_correction_deg'], math.degrees(math.atan2(cross, cfg['lookahead_nm']))))
                    commands.append(f"HDG {self.callsign} {cb.COURSE + correction:.2f}")
                    if self.phase == 'glideslope':
                        feed = ac.get('gs', speed) * cb.FT_PER_NM / 60 * math.tan(math.radians(cb.GLIDE_ANGLE))
                        descent = max(cfg['min_descent_fpm'], min(cfg['max_descent_fpm'], feed + error * cfg['vertical_gain']))
                        commands.append(f"ALT {self.callsign} {cb.threshold['elevation_ft'] + cfg['guidance_target_height_ft']} {-descent:.0f}")
                stable = (self.phase == 'glideslope' and abs(cross) <= cfg['stable_cross_nm'] and angle <= cfg['stable_angle_deg']
                          and abs(error) <= cfg['stable_alt_ft'] and speed_ok and ac.get('vs_fpm', 0) < -200)
                self.stable_s = self.stable_s + dt if stable else 0
                if self.handover and self.phase == 'glideslope':
                    if along <= self.handover['go_around_nm']:
                        if self.landing_cleared:
                            self.phase = 'complete'
                            commands = []
                        else:
                            self.start_go_around()
                            self.announce('going around, no tower handover received')
                            return self.update(ac, dt)
                    if along <= self.handover['request_nm'] and not self.landing_cleared and not self.tower_reminder_sent:
                        self.tower_reminder_sent = True
                        self.announce('confirm contact tower')
                elif self.stable_s >= cfg['stable_seconds']:
                    self.phase = 'complete' if self.landing_cleared else ('handoff_ready' if cb.tower else 'approach_complete')
                    commands = []
        messages = {
            'awaiting_clearance': 'ILS not cleared. Vector the aircraft and issue an explicit ILS approach clearance with the runway.',
            'handoff_ready': f'Stable ILS tracking achieved. Training pause: contact {cb.tower["name"]} on {cb.tower["frequency_mhz"]} MHz.' if cb.tower else '',
            'approach_complete': 'Stable tracking achieved. Tower handoff unavailable: no verified channel configured.',
            'armed': f"Vector to final: intercept {cfg['localizer_min_nm']}â€“{cfg['localizer_max_nm']} NM out, â‰¤{cfg['intercept_max_deg']}Â°, level at {cb.INTERCEPT_ALT_FT:,} ft, {cfg['speed_min_kt']}â€“{cfg['speed_max_kt']} kt.",
            'localizer': f'Localizer captured. Pilot tracking final; maintain {cb.INTERCEPT_ALT_FT:,} ft to meet glide slope from below.',
            'glideslope': 'Glide slope captured. Pilot descending; establishing stable tracking.',
            'complete': 'Radar approach exercise complete.',
            'missed': 'Capture not achieved or tracking lost. Exercise paused; reset to try again.',
        }
        message = messages[self.phase]
        if self.landing_cleared and self.phase in ('localizer', 'glideslope'):
            message += ' Landing clearance received.'
        elif self.handover and self.phase == 'glideslope':
            message = 'Glide slope captured. Issue tower handover.'
        if self.retry_ready and self.phase == 'awaiting_clearance':
            message = 'Vector the aircraft for another attempt and issue a fresh ILS clearance.'
        if self.go_around_on_handoff:
            message += ' Go-around armed: tower handoff will start a missed approach instead of ending the exercise.'
        self.status = {'phase': self.phase, 'message': message, 'go_around_on_handoff': self.go_around_on_handoff,
                       'missed_approach': self.missed.brief(),
                       'along_nm': round(along, 2), 'cross_nm': round(cross, 3),
                       'intercept_deg': round(angle, 1), 'glide_alt_ft': round(gs_alt),
                       'glide_error_ft': round(error), 'speed_ok': speed_ok,
                       'level_ok': level_ok, 'stable_s': round(self.stable_s, 1)}
        return commands
