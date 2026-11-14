import math
import pytest
from airport_profiles import get_profile, available
from ils_trainer import ILSTrainer
from simple_demo import validate


@pytest.mark.parametrize('icao,level,heading,runway,length', [
    ('VOCB',3200,225.72,'23',2990), ('VOML',2400,238.39,'24',2330)])
def test_shared_engine_uses_selected_airport(icao,level,heading,runway,length):
    p=get_profile(icao)
    nav=p.nav()
    assert p.INTERCEPT_ALT_FT == level and p.COURSE == heading
    assert nav['approach']['runway'] == runway
    a,b=nav['runways'][0]['ends']
    assert math.hypot(b['x']-a['x'],b['y']-a['y'])*1852 == pytest.approx(length,abs=15)
    def aircraft(along, alt, vs=0):
        x,y=p.approach_point(along)
        return dict(x=x,y=y,hdg=heading,trk=heading,alt_ft=alt,cas_kt=180,gs=190,vs_fpm=vs)
    trainer=ILSTrainer(p)
    trainer.clear_approach(3200)
    trainer.update(aircraft(9,level),1)
    assert trainer.phase == 'localizer'
    along=(level-p.threshold['elevation_ft']-p.RDH_FT)/(p.FT_PER_NM*math.tan(math.radians(p.GLIDE_ANGLE)))
    trainer.update(aircraft(along,level),1)
    assert trainer.phase == 'glideslope'
    for _ in range(10):
        along-=.05
        trainer.update(aircraft(along,p.glide_altitude(along),-950),1)
    assert trainer.phase == ('glideslope' if icao == 'VOCB' else 'handoff_ready')
    assert trainer.airport.ICAO == icao


def test_mangaluru_chart_reference_datums_and_command_altitude():
    p=get_profile('VOML')
    assert [p.LAT,p.LON] == pytest.approx([12.962061111,74.889786111])
    assert p.data['elevation_ft']==318 and p.RDH_FT==54
    aids=p.navaids()
    for fix,ref,distance in zip(p.approach_nav()['fixes'],[aids[0],aids[2]],[13,6.5]):
        assert math.hypot(fix['x']-ref['x'],fix['y']-ref['y']) == pytest.approx(distance)
    orders=[dict(callsign='AFR123',action='ALT',value=2400)]
    text = 'Air France one two three, descend two thousand four hundred feet'
    assert validate(text,orders,[dict(id='AFR123',hdg=253)],p) is None
    assert validate(text,orders,[dict(id='AFR123',hdg=253)],get_profile('VOCB'))


def test_unknown_profile_cannot_resolve_arbitrary_path():
    assert {'VOCB','VOML'} <= {a['icao'] for a in available()}
    with pytest.raises(ValueError):
        get_profile('../../.env')


def test_manual_override_preserves_selected_profile():
    p=get_profile('VOML')
    trainer=ILSTrainer(p)
    trainer.clear_approach(3200)
    trainer.phase='localizer'
    trainer.manual_command('HDG AFR123 270')
    assert trainer.phase=='awaiting_clearance' and trainer.airport is p
