import math
import os
import subprocess
import sys
from pathlib import Path
import coimbatore as cb
import pytest


def test_chart_coordinates_and_runway_dimensions():
    nav = cb.nav()
    assert nav['center'] == pytest.approx([11.0269111111, 77.0418027778])
    runway = nav['runways'][0]
    a, b = runway['ends']
    assert [a['name'], b['name']] == ['05', '23']
    assert [a['elevation_ft'], b['elevation_ft']] == [1330, 1277]
    assert runway['length_m'] == 2990 and runway['width_m'] == 45
    # Local projection is approximate; check endpoint separation against chart.
    assert math.hypot(b['x'] - a['x'], b['y'] - a['y']) * 1852 == pytest.approx(2990, abs=15)
    bearing = math.degrees(math.atan2(b['x'] - a['x'], b['y'] - a['y']))
    assert bearing == pytest.approx(a['bearing_true'], abs=0.3)
    assert nav['sector'] == []  # no invented Reims boundary at VOCB


def test_aircraft_placement_and_simulator_share_airport_origin():
    root = Path(__file__).resolve().parents[1]
    code = '''import atc_sim, coimbatore as cb
a = cb.aircraft()
x, y = atc_sim.to_nm(a['lat'], a['lon'])
along, cross = cb.approach_geometry(x, y)
from airport_profiles import get_profile
from entry_area import entry_position
entry = entry_position(get_profile('VOCB'))
assert abs(along - entry['along_nm']) < 1e-6 and abs(cross - entry['cross_nm']) < 1e-6
assert atc_sim.to_nm(cb.LAT, cb.LON) == (0, 0)
assert atc_sim.from_nm(x, y) == (a['lat'], a['lon'])
'''
    subprocess.run([sys.executable, '-c', code], cwd=root,
                   env={**os.environ, 'ATC_SIMPLE_DEMO': '1', 'ATC_AIRPORT': 'VOCB', 'PYTHONPATH': str(root / 'src')}, check=True)
