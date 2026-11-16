"""Opening transmissions must wait for Start, including the local startup aircraft."""
from types import SimpleNamespace

from airport_profiles import get_profile


def test_single_aircraft_opening_waits_for_resume(monkeypatch):
    import atc_sim

    sim = atc_sim.SimManager()
    sim.airport = get_profile('VOCB')
    sim._ils = None
    ac = sim.airport.aircraft()
    ac['id'] = ac['callsign']
    sim._meta[ac['id']] = {'type': ac['type']}
    monkeypatch.setattr(atc_sim.bsk, 'state', lambda: [ac])
    monkeypatch.setattr(atc_sim.bsk, 'bs', lambda: SimpleNamespace(sim=SimpleNamespace(simt=0)))
    monkeypatch.setattr(sim, '_enrich', lambda aircraft: None)
    monkeypatch.setattr(sim, '_analyze_cd', lambda: ([], []))

    # Also exercise a fresh airport selection/reset after a previous flight.
    for _ in range(2):
        sim.pause()
        sim._radio_calls.clear()
        sim._meta[ac['id']].pop('initial_contact', None)
        for _ in range(3):
            sim._update_snapshot(True, 1)
            assert sim.snapshot()['aircraft']
            assert sim.snapshot()['traffic_calls'] == []
            assert not sim._meta[ac['id']].get('initial_contact')

        sim.resume()
        sim._update_snapshot(sim._paused, 1)
        calls = sim.snapshot()['traffic_calls']
        assert len(calls) == 1 and calls[0]['callsign'] == 'AFR123'
        sim.pause()
        sim._update_snapshot(True, 1)
        assert sim.snapshot()['traffic_calls'] == calls
        sim.resume()
        sim._update_snapshot(False, 1)
        assert sim.snapshot()['traffic_calls'] == calls
