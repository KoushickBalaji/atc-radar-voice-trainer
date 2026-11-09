from copy import deepcopy
import pytest
from airport_profiles import AirportProfile, get_profile
from atc_sim import SimManager


def vectoring_profile():
    original = get_profile('VOCB')
    data = deepcopy(original.data)
    data['approach'] = None
    data['exercise'].update(practice_alt_ft=5000, reference_runway_index=0)
    return AirportProfile(data, original.training)


def test_non_ils_profile_has_no_fabricated_guidance_or_final():
    p = vectoring_profile()
    nav = p.nav()
    assert nav['approach'] is None
    assert nav['profile']['mode'] == 'vectoring'
    assert nav['profile']['approach'] is None
    assert p.COURSE == p.THRESHOLDS[0]['bearing_true']
    assert 'five thousand' in p.info()['examples'][1]
    with pytest.raises(ValueError, match='no modeled ILS'):
        p.glide_altitude(5)
    # Independent SMAC monitoring still works in vectoring mode.
    p.msaw.evaluate(p.aircraft())


def test_simulator_does_not_arm_ils_for_vectoring(monkeypatch):
    p = vectoring_profile()
    monkeypatch.setenv('ATC_SIMPLE_DEMO', '1')
    monkeypatch.setattr('atc_sim.get_profile', lambda _: p)
    sim = SimManager()
    assert sim.airport is p and sim._ils is None
