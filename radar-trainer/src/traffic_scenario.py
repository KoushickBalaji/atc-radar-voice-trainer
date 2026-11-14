"""Repeatable airport exercises. Only the simulation thread mutates a run."""
import json
import math
from pathlib import Path
from typing import Annotated, Literal, Union
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator
from ils_trainer import ILSTrainer
from holding import TERMINAL_SEPARATION_FT
from readback import callsign_telephony, pilot_report, num_words

DATA = Path(__file__).resolve().parents[1] / 'data' / 'traffic'


class Flight(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    callsign: str = Field(pattern=r'^[A-Z][A-Z0-9]{2,11}$')
    type: str = Field(pattern=r'^[A-Z0-9]{2,4}$')
    at_s: float = Field(ge=0)


class Arrival(Flight):
    role: Literal['arrival']
    along_nm: float | None = Field(default=None, gt=0)
    route: str | None = None
    hold_id: str | None = None
    via: str | None = None
    route_distance_nm: float | None = Field(default=None, gt=0)
    entry_alt_ft: int | None = Field(default=None, gt=0)
    cross_nm: float = 0
    speed_kt: float = Field(gt=0)
    contact_fl: int | None = Field(default=None, ge=1, le=180)
    station: str | None = None
    frequency: str | None = Field(default=None, pattern=r'^1[123]\d\.\d{3}$')

    @model_validator(mode='after')
    def validate_start(self):
        if self.contact_fl is not None and (not self.route or not self.station or not self.frequency or self.entry_alt_ft is None or self.entry_alt_ft < self.contact_fl*100):
            raise ValueError('Level-based approach transfer needs route entry, station, frequency and a higher entry level.')
        if self.route:
            if not self.via or self.entry_alt_ft is None or self.along_nm is not None or self.cross_nm:
                raise ValueError('Route entry needs a route, inbound branch and training entry altitude.')
        elif self.along_nm is None or self.via or self.hold_id or self.entry_alt_ft is not None or self.route_distance_nm is not None:
            raise ValueError('Final entry requires an along-track distance.')
        return self


class Outbound(Flight):
    station: str = Field(min_length=1)
    frequency: str = Field(pattern=r'^1[123]\d\.\d{3}$')


class Departure(Outbound):
    role: Literal['departure']
    runway: str
    climb_ft: int = Field(gt=0)
    roll_s: float = Field(default=32, gt=0)
    rotation_kt: float = Field(default=145, gt=0)
    climb_speed_kt: float = Field(default=190, gt=0)
    transfer_agl_ft: float = Field(default=500, gt=0)
    transfer_fl: int | None = Field(default=None, ge=1, le=180)
    departure_heading: float = Field(ge=0, le=360)


class Overflight(Outbound):
    role: Literal['overflight']
    initial_station: str | None = Field(default=None, min_length=1)
    transfer_required: bool = True
    x_nm: float
    y_nm: float
    heading: float = Field(ge=0, le=360)
    alt_ft: float = Field(gt=0)
    speed_kt: float = Field(gt=0)
    area: str
    lead_s: float = Field(gt=0)


class Scenario(BaseModel):
    id: str
    title: str
    brief: str
    flights: list[Annotated[Union[Arrival, Departure, Overflight], Field(discriminator='role')]] = Field(min_length=1)


def catalogue(airport):
    path = DATA / (airport.ICAO + '.json')
    scenarios = {}
    for raw in json.loads(path.read_text(encoding='utf-8')) if path.exists() else []:
        spec = Scenario(**raw)
        if spec.id in scenarios or len({f.callsign for f in spec.flights}) != len(spec.flights):
            raise ValueError('Scenario IDs and flight callsigns must be unique.')
        if any(isinstance(f, Arrival) for f in spec.flights) and not (airport.approach and airport.tower):
            continue
        for f in spec.flights:
            if isinstance(f, Departure) and f.transfer_fl and f.climb_ft < f.transfer_fl*100:
                raise ValueError('Departure cleared level must reach the configured transfer level.')
            if isinstance(f, Arrival) and f.route:
                airport.ats_routes.entry(f.route, f.via, f.route_distance_nm)
            if isinstance(f, Departure) and f.runway not in {r['name'] for r in airport.THRESHOLDS}:
                raise ValueError(f'Unknown departure runway {f.runway}')
            if isinstance(f, Overflight) and not any(a['id'] == f.area for a in airport.control_areas.areas):
                raise ValueError(f'Unknown transit volume {f.area}')
        scenarios[spec.id] = spec
    return scenarios


class TrafficRun:
    def __init__(self, airport, spec):
        self.airport = airport
        self.spec = spec
        self.elapsed = 0.0
        self.flights = {f.callsign: f for f in spec.flights}
        self.phase = dict.fromkeys(self.flights, 'scheduled')
        self.approaches = {f.callsign: ILSTrainer(airport, f.callsign, route_entry=bool(f.route))
                           for f in spec.flights if isinstance(f, Arrival)}
        self.calls = []
        self.roll_start = {}
        self.last_ils_call = {}
        self.entered = set()
        self.transit_instructions = set()
        self.overdue = set()
        self.approach_contacted = set()
        self.contact_requested = set()
        # Start unattended arrivals at separated levels in expected fix-arrival order.
        self.pending_holds = {}
        self.release_levels = {}
        arrivals = []
        for f in spec.flights:
            if isinstance(f, Arrival) and f.route:
                entry = airport.ats_routes.entry(f.route, f.via, f.route_distance_nm)
                if f.hold_id:
                    pattern = airport.holds[f.hold_id]
                else:
                    matches = [p for p in airport.holds.values() if p['fix'] == entry['inbound'][-1]]
                    if len(matches) != 1:
                        continue
                    pattern = matches[0]
                if entry['inbound'][-1] != pattern['fix']:
                    raise ValueError(f'{f.callsign}: route must terminate at the holding fix')
                eta = f.at_s + 3600 * entry['remaining_nm'] / f.speed_kt
                arrivals.append((eta, f.callsign))
                self.pending_holds[f.callsign] = pattern
        highest = {}
        for _, cs in sorted(arrivals):
            pattern = self.pending_holds[cs]
            fix = pattern['fix']
            level = max(self.flights[cs].entry_alt_ft, pattern['minimum_ft'],
                        highest.get(fix, 0) + TERMINAL_SEPARATION_FT)
            if level > 18000:
                raise ValueError(f'{cs}: holding stack exceeds the exercise altitude limit')
            self.release_levels[cs] = highest[fix] = level

    def announce(self, flight, text):
        self.calls.append(dict(id=uuid4().hex, callsign=flight.callsign, text=text))

    def runway(self, flight):
        return next(r for r in self.airport.THRESHOLDS if r['name'] == flight.runway)

    def ground_state(self, f, now):
        r = self.runway(f)
        angle = math.radians(r['bearing_true'])
        # Model a constant acceleration roll along the runway until rotation.
        elapsed = max(0, min(f.roll_s, now - self.roll_start.get(f.callsign, now)))
        speed = f.rotation_kt * elapsed / f.roll_s
        distance = speed * elapsed / 7200
        x, y = self.airport.to_nm(r['lat'], r['lon'])
        lat, lon = self.airport.from_nm(x + distance * math.sin(angle), y + distance * math.cos(angle))
        return dict(id=f.callsign, type=f.type, lat=lat, lon=lon, hdg=r['bearing_true'],
                    alt_ft=r['elevation_ft'], tas_kt=speed)

    def schedule(self, now, create, command):
        ground = []
        for cs, f in self.flights.items():
            if now >= f.at_s and self.phase[cs] == 'scheduled':
                spoken = callsign_telephony(cs)
                if isinstance(f, Departure):
                    self.phase[cs] = 'ready'
                    self.announce(f, f'{self.airport.NAME} Tower, {spoken}, ready runway {f.runway}.')
                elif isinstance(f, Arrival):
                    if f.route:
                        routes = self.airport.ats_routes
                        entry = routes.entry(f.route, f.via, f.route_distance_nm)
                        lat, lon = self.airport.from_nm(entry['x'], entry['y'])
                        altitude = self.release_levels.get(cs, f.entry_alt_ft)
                        create(cs, f.type, lat, lon, entry['heading'], altitude, f.speed_kt)
                        for fix in entry['inbound']:
                            lat, lon = routes.fixes[fix]
                            command(f'ADDWPT {cs} {lat:.7f},{lon:.7f}')
                        command(f'LNAV {cs} ON')
                        level = 'flight level ' + num_words(f'{round(altitude/100):03d}') if f.contact_fl else f'{altitude} feet'
                        position = f"on {f.route} from {entry['outside']} inbound to {entry['inbound'][0]}, maintaining {level}"
                    else:
                        lat, lon = self.airport.from_nm(*self.airport.approach_point(f.along_nm, f.cross_nm))
                        create(cs, f.type, lat, lon, self.airport.COURSE, self.airport.INTERCEPT_ALT_FT, f.speed_kt)
                        position = f'{f.along_nm:g} miles final, maintaining {self.airport.INTERCEPT_ALT_FT} feet'
                    self.phase[cs] = 'awaiting_clearance'
                    station = 'Training Control' if f.contact_fl else self.airport.NAME + ' Approach'
                    self.announce(f, f'{station}, {spoken}, {position}, assigned speed {num_words(round(f.speed_kt))} knots.')
                else:
                    lat, lon = self.airport.from_nm(f.x_nm, f.y_nm)
                    create(cs, f.type, lat, lon, f.heading, f.alt_ft, f.speed_kt)
                    self.phase[cs] = 'inbound'
            if self.phase[cs] in ('ready', 'rolling'):
                state = self.ground_state(f, now)
                if self.phase[cs] == 'rolling' and now - self.roll_start[cs] >= f.roll_s:
                    create(cs, f.type, state['lat'], state['lon'], state['hdg'], state['alt_ft'], f.rotation_kt)
                    command(f'ALT {cs} {f.climb_ft}')
                    command(f'SPD {cs} {f.climb_speed_kt}')
                    command(f'HDG {cs} {f.departure_heading}')
                    self.phase[cs] = 'climbing'
                else:
                    ground.append(state)
        return ground

    def update(self, ac, dt, command):
        cs = ac['id']
        f = self.flights[cs]
        if isinstance(f, Arrival):
            if f.contact_fl and cs not in self.approach_contacted and cs not in self.contact_requested and ac['alt_ft'] <= f.contact_fl*100:
                self.contact_requested.add(cs)
                self.announce(f, f'{callsign_telephony(cs)}, confirm frequency change to {f.station}.')
            trainer = self.approaches[cs]
            pattern = self.pending_holds.get(cs)
            if pattern and dt > 0 and ac['actwp'] == len(ac['route']) - 1:
                fix = self.airport.to_nm(*pattern['position'])
                if math.dist((ac['x'], ac['y']), fix) <= 2:
                    trainer.start_hold(pattern, self.release_levels[cs])
                    del self.pending_holds[cs]
            for line in trainer.update(ac, dt):
                command(line)
            self.phase[cs] = trainer.phase
            if trainer.pilot_call and self.last_ils_call.get(cs) != trainer.pilot_call['id']:
                self.calls.append(trainer.pilot_call)
                self.last_ils_call[cs] = trainer.pilot_call['id']
            ac['ils'] = trainer.status
        elif isinstance(f, Overflight):
            volume = next(a for a in self.airport.control_areas.areas if a['id'] == f.area)
            inside = volume['name'] in self.airport.control_areas.evaluate(ac)['areas']
            if inside and cs not in self.entered:
                self.entered.add(cs)
                self.phase[cs] = 'transiting'
                self.announce(f, pilot_report(ac, ['position', 'level', 'heading'], f.initial_station or self.airport.NAME + ' Tower'))
            if cs in self.entered:
                if not f.transfer_required:
                    if not inside:
                        self.phase[cs] = 'complete'
                elif not inside:
                    self.overdue.add(cs)
                due = f.transfer_required and (not inside or self.airport.control_areas.project_exit(ac, f.lead_s, volume['name']) is not None)
                if due and self.phase[cs] == 'transiting':
                    self.request_contact(f)
                elif not due and self.phase[cs] == 'handoff_requested':
                    self.phase[cs] = 'transiting'
        elif self.phase[cs] == 'climbing' and ac['alt_ft'] >= (f.transfer_fl*100 if f.transfer_fl else self.runway(f)['elevation_ft'] + f.transfer_agl_ft):
            self.request_contact(f)
        ac.update(role=f.role, phase=self.phase[cs])

    def accept_vector(self, cs, fields):
        if self.phase.get(cs) in ('ready','rolling','complete','scheduled','inbound'):
            return False
        if isinstance(self.flights.get(cs), Overflight):
            self.transit_instructions.add(cs)
        pattern = self.pending_holds.get(cs)
        if pattern and len(fields) >= 3:
            axis = fields[0].upper()
            if axis == 'ALT' and float(fields[2]) >= pattern['minimum_ft']:
                self.release_levels[cs] = float(fields[2])
            elif axis in ('HDG', 'ALT') or (axis == 'SPD' and float(fields[2]) > pattern['max_kias']):
                del self.pending_holds[cs]
        return True

    def request_contact(self, f):
        self.phase[f.callsign] = 'handoff_requested'
        self.announce(f, f'{callsign_telephony(f.callsign)}, confirm frequency change to {f.station}.')

    def procedure(self, order, now, aircraft):
        import approach_radio
        cs = order['callsign']
        f = self.flights.get(cs)
        phase = self.phase.get(cs)
        if not f or phase in ('scheduled', 'complete'):
            return 'This aircraft is not on your frequency.'
        action = order['action']
        if action == 'TAKEOFF':
            if not isinstance(f, Departure) or phase != 'ready' or order['runway'] != f.runway:
                return 'Takeoff requires a ready departure on the specified runway.'
            for other in aircraft:
                if other['id'] == cs:
                    continue
                # Exercise runway protection in addition to the controller's separation judgment.
                if self.phase.get(other['id']) == 'rolling' and self.flights[other['id']].runway == f.runway:
                    return 'Runway occupied by another departure.'
                if other['id'] in self.approaches and f.runway == self.airport.approach['runway']:
                    along, cross = self.airport.approach_geometry(other['x'], other['y'])
                    if -0.5 <= along <= 4 and abs(cross) < 1:
                        return 'Arrival on short final. Hold position.'
            self.roll_start[cs] = now
            self.phase[cs] = 'rolling'
        elif action == 'CONTACT_UNIT':
            if isinstance(f, Arrival) and f.contact_fl:
                if cs not in self.contact_requested or cs in self.approach_contacted:
                    return 'Approach transfer has not been coordinated at the training level.'
                if order['station'].casefold() != f.station.casefold() or order['frequency'] != f.frequency:
                    return 'Receiving station or channel does not match the coordinated transfer.'
                ac = next((a for a in aircraft if a['id'] == cs), None)
                if ac is None:
                    return 'Aircraft unavailable.'
                self.approach_contacted.add(cs)
                self.announce(f, pilot_report(ac, ['position','level','cleared_level'], f.station))
                return None
            if not isinstance(f, Outbound) or phase != 'handoff_requested':
                return 'The receiving unit has not accepted transfer.'
            if isinstance(f, Overflight) and cs not in self.transit_instructions:
                return 'Issue the transit aircraft an onward heading, speed or level before transfer.'
            if order['station'].casefold() != f.station.casefold() or order['frequency'] != f.frequency:
                return 'Receiving station or channel does not match the coordinated transfer.'
            self.phase[cs] = 'complete'
        elif cs in self.approaches and action in ('CLEAR_ILS', 'CONTACT_TOWER', 'CLEAR_LAND'):
            error = approach_radio.validate(order, self.airport, self.approaches[cs].phase, cs)
            if error:
                return error
            if action == 'CLEAR_ILS':
                altitude = next((a['alt_ft'] for a in aircraft if a['id'] == cs), None)
                error = self.approaches[cs].clear_approach(altitude)
                if error:
                    return error
                self.pending_holds.pop(cs, None)
            elif action == 'CLEAR_LAND':
                self.approaches[cs].clear_landing()
                self.phase[cs] = self.approaches[cs].phase
            else:
                self.approaches[cs].phase = self.phase[cs] = 'complete'
        else:
            return 'This procedure is unavailable for this flight in the mixed exercise.'
        return None

    def status(self):
        return dict(id=self.spec.id, title=self.spec.title, brief=self.spec.brief,
                    flights=[dict(callsign=cs, role=f.role, phase=self.phase[cs], overdue=cs in self.overdue) for cs,f in self.flights.items()],
                    complete=all(p == 'complete' for p in self.phase.values()))

