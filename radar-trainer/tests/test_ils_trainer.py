import pytest
import coimbatore as cb
from ils_trainer import ILSTrainer


def aircraft(along=9, cross=.05, heading=240, alt=3200, speed=180, vs=0):
    x, y = cb.approach_point(along, cross)
    return dict(id='AFR123', x=x, y=y, hdg=heading, trk=heading,
                alt_ft=alt, cas_kt=speed, gs=speed, vs_fpm=vs)


@pytest.mark.parametrize('change', [dict(heading=cb.COURSE+90), dict(heading=cb.COURSE+180),
    dict(alt=5000), dict(alt=2800), dict(speed=220), dict(along=-8), dict(cross=1)])
def test_bad_intercepts_do_not_capture(change):
    trainer = ILSTrainer()
    trainer.clear_approach()
    trainer.update(aircraft(**change), 1)
    assert trainer.phase not in ('localizer', 'glideslope', 'complete')


def test_capture_from_below_then_stable_descent_completes():
    trainer = ILSTrainer()
    trainer.clear_approach()
    assert trainer.update(aircraft(), 1)
    assert trainer.phase == 'localizer'
    # At the glide path intersection the level aircraft meets GS from below.
    along = (3200 - 1277 - cb.RDH_FT) / (cb.FT_PER_NM * __import__('math').tan(__import__('math').radians(3)))
    trainer.update(aircraft(along=along, cross=0, heading=cb.COURSE), 1)
    assert trainer.phase == 'glideslope'
    for _ in range(10):
        along -= .05
        trainer.update(aircraft(along=along, cross=0, heading=cb.COURSE,
                               alt=cb.glide_altitude(along), vs=-950), 1)
    assert trainer.phase == 'glideslope'
    assert trainer.stable_s >= 10


def test_above_glide_slope_never_captures_and_pause_does_not_score():
    trainer = ILSTrainer()
    trainer.clear_approach()
    trainer.update(aircraft(), 0)
    assert trainer.phase == 'armed'
    trainer.update(aircraft(), 1)
    trainer.update(aircraft(along=5, heading=cb.COURSE), 1)
    assert trainer.phase == 'missed'
    assert trainer.stable_s == 0


def test_manual_vector_overrides_guidance():
    trainer = ILSTrainer()
    trainer.clear_approach()
    trainer.update(aircraft(), 1)
    trainer.manual_command('HDG AFR123 180')
    assert trainer.phase == 'awaiting_clearance'
    assert not trainer.below_seen


def test_nav_aids_and_reference_markers_are_not_outer_middle_beacons():
    nav = cb.nav()
    assert len(nav['navaids']) == 4
    assert nav['approach']['glide_deg'] == 3
    assert [p['name'] for p in nav['approach']['fixes']] == ['IF 11.6D ICMB', 'LOC-only FAF 6.1D']


@pytest.mark.parametrize('skip_request', [False, True])
def test_configured_final_continues_and_flies_missed_approach(skip_request):
    trainer = ILSTrainer()
    trainer.phase = 'glideslope'
    def fly(distance, dt=1):
        return trainer.update(aircraft(along=distance, heading=cb.COURSE, cross=0,
                                       alt=cb.glide_altitude(distance), vs=-900), dt)
    fly(6.2)
    assert trainer.pilot_call is None
    if not skip_request:
        fly(5.99)
        request = trainer.pilot_call
        assert 'confirm contact tower' in request['text']
        fly(3.01)
        assert fly(2.01) and trainer.phase == 'glideslope'
        assert trainer.pilot_call is request
    fly(1.95, dt=0)
    assert trainer.phase == 'glideslope'
    commands = fly(1.95, dt=20)
    assert trainer.phase == 'going_around'
    assert 'going around' in trainer.pilot_call['text']
    assert any(line.startswith('ALT AFR123 ') for line in commands)


def test_request_distances_belong_to_the_airport_profile():
    from airport_profiles import AirportProfile, get_profile
    original = get_profile('VOCB')
    exercise = dict(original.exercise, tower_handover=dict(request_nm=5, go_around_nm=1))
    trainer = ILSTrainer(AirportProfile(dict(original.data, exercise=exercise), original.training))
    trainer.phase = 'glideslope'
    for distance in (5.5, 4.9, 1.5):
        trainer.update(aircraft(along=distance, heading=cb.COURSE, cross=0, alt=cb.glide_altitude(distance)), 1)
        assert trainer.phase == 'glideslope'
        assert bool(trainer.pilot_call) == (distance <= 5)
