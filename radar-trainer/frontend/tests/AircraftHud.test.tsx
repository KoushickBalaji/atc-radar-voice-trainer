import React from 'react';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import AircraftHud from '../src/components/AircraftHud';
import type { Aircraft, NavData } from '../src/types';
import type { SimHub } from '../src/useSim';

vi.mock('../src/components/RadioPanel', () => ({ default: () => <button>Hold to talk</button> }));
afterEach(cleanup);
const nav = { profile: { icao: 'TEST', aircraft: { callsign: 'ARR123' }, approach: { runway: '23' } } } as NavData;
const aircraft = (id: string, overrides: Partial<Aircraft> = {}): Aircraft => ({
  id, type: 'A320', x: 0, y: 0, lat: 0, lon: 0, hdg: 90, trk: 90, alt_ft: 5000, fl: 50,
  gs: 220, cas_kt: 210, vs_fpm: -500, sel_alt_ft: 3000, conflict: false, alert: '', inzone: '', route: [], actwp: 0, ...overrides,
});
function fixture() {
  return { connection: 'connected', state: { sim_alive: true, aircraft: [aircraft('ARR123'), aircraft('VEC456', {
    msaw: { status: 'warning', minimum_ft: 6000, deficit_ft: 1000, regions: [] },
  })], conflicts: [], predicted: [] }, providers: { stt: true, llm: true, tts: false }, refreshHealth: vi.fn(),
  log: [{ id: 1, exchangeId: 1, callsigns: ['ARR123'], exchange: { transcript: 'Descend to three thousand', orders: [], trafscript: ['ALT 3000 accepted'], readback: 'Descending three thousand', rejected: ['Unsupported instruction'] }, kind: 'tx', t: '12:00:00', text: 'Descend to three thousand' },
    { id: 2, exchangeId: 1, kind: 'cmd', t: '12:00:01', text: 'ALT 3000 accepted' },
    { id: 3, exchangeId: 1, kind: 'pilot', t: '12:00:02', text: 'Descending three thousand' },
    { id: 4, exchangeId: 1, kind: 'rej', t: '12:00:03', text: 'Unsupported instruction' }],
  lastExchange: { audio_b64: 'AAAA', tts_error: 'Test audio failure' } } as unknown as SimHub;
}

it('filters live aircraft, updates counts, and keeps warnings and radio independent of the filter', () => {
  const hub = fixture();
  const view = render(<AircraftHud hub={hub} nav={nav} />);
  const list = screen.getByRole('group', { name: 'Aircraft list' });
  expect(within(list).getAllByRole('button')).toHaveLength(2);
  fireEvent.click(screen.getByRole('button', { name: 'Arrivals' }));
  expect(within(list).getAllByRole('button')).toHaveLength(1);
  expect(within(list).getByRole('button', { name: 'Select ARR123' })).toBeTruthy();
  expect(screen.getByText('VEC456 · MSAW — LOW ALTITUDE')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Departures' }));
  expect(within(list).queryAllByRole('button')).toHaveLength(0);
  expect(screen.getByText('No departures.')).toBeTruthy();
  expect(screen.queryByRole('region', { name: 'Selected aircraft details' })).toBeNull();
  expect(screen.getByText('Descending three thousand')).toBeTruthy();
  expect(screen.getByText('ALT 3000 accepted')).toBeTruthy();
  expect(screen.getByText('Unsupported instruction')).toBeTruthy();
  expect(screen.getByLabelText('Replay pilot readback')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Aircraft with alerts' }));
  expect(within(list).getByRole('button', { name: 'Select VEC456' })).toBeTruthy();
  const cleared = { ...hub, state: { ...hub.state, aircraft: [aircraft('ARR123'), aircraft('VEC456')] } };
  view.rerender(<AircraftHud hub={cleared} nav={nav} />);
  expect(screen.getByText('No aircraft with alerts.')).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Aircraft with alerts' }).textContent).toContain('0');
});

it('selects aircraft details without losing list filters and reports stale monitoring', () => {
  const hub = fixture();
  const view = render(<AircraftHud hub={hub} nav={nav} />);
  fireEvent.click(screen.getByRole('button', { name: 'Select ARR123' }));
  const detail = screen.getByRole('region', { name: 'Selected aircraft details' });
  expect(within(detail).getByRole('heading', { name: 'ARR123' })).toBeTruthy();
  expect(within(detail).getByText('3,000 ft')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: /TTS unavailable/ }));
  expect(hub.refreshHealth).toHaveBeenCalledTimes(1);
  view.rerender(<AircraftHud hub={{ ...hub, connection: 'disconnected' }} nav={nav} />);
  expect(screen.getByText('Monitoring unavailable')).toBeTruthy();
  expect(screen.getByText(/Last known data/)).toBeTruthy();
  expect(screen.queryByText('VEC456 · MSAW — LOW ALTITUDE')).toBeNull();
});

it('toggles details on the same row and starts with a single aircraft row', () => {
  render(<AircraftHud hub={fixture()} nav={nav} />);
  const row = screen.getByRole('button', { name: 'Select ARR123' });
  expect(screen.queryByRole('region', { name: 'Selected aircraft details' })).toBeNull();
  expect(screen.queryByText(/Your transmissions, command feedback/)).toBeNull();
  fireEvent.click(row);
  expect(row.getAttribute('aria-expanded')).toBe('true');
  expect(screen.getByRole('region', { name: 'Selected aircraft details' })).toBeTruthy();
  fireEvent.click(row);
  expect(row.getAttribute('aria-expanded')).toBe('false');
  expect(screen.queryByRole('region', { name: 'Selected aircraft details' })).toBeNull();
  fireEvent.click(row);
  expect(screen.getByRole('region', { name: 'Selected aircraft details' })).toBeTruthy();
});

it('uses simulator warnings without treating an outside arrival as an alert', () => {
  const hub = fixture();
  hub.state.aircraft = [aircraft('ARR123', { control_area: { status: 'outside', areas: [], uncertain: [], exit_in_s: null } })];
  const view = render(<AircraftHud hub={hub} nav={nav} />);
  const alerts = screen.getByRole('button', { name: 'Aircraft with alerts' });
  const list = screen.getByRole('group', { name: 'Aircraft list' });
  expect(alerts.textContent).toContain('0');
  expect(within(list).queryByText('ALERT')).toBeNull();
  expect(screen.queryByText(/Outside control area/)).toBeNull();
  expect(screen.queryByText('WARNINGS · FEEDBACK · RADIO')).toBeNull();
  fireEvent.click(alerts);
  expect(screen.getByText('No aircraft with alerts.')).toBeTruthy();
  hub.state.aircraft = [aircraft('ARR123', { control_area: { status: 'inside', areas: ['CTR'], uncertain: [], exit_in_s: 30 } })];
  view.rerender(<AircraftHud hub={hub} nav={nav} />);
  expect(alerts.textContent).toContain('1');
  expect(within(list).getByText('ALERT')).toBeTruthy();
  expect(screen.getByText('ARR123 · Projected airspace exit')).toBeTruthy();
  hub.state.aircraft = [aircraft('ARR123', { msaw: { status: 'warning', minimum_ft: 6000, deficit_ft: 1000, regions: [] } })];
  view.rerender(<AircraftHud hub={hub} nav={nav} />);
  expect(screen.getByText('ARR123 · MSAW — LOW ALTITUDE')).toBeTruthy();
  expect(screen.queryByText('ARR123 · Projected airspace exit')).toBeNull();
});

it('filters grouped exchanges by callsign while retaining every aircraft warning', () => {
  const hub = fixture();
  hub.log.push({ id: 5, t: '12:00:04', kind: 'tx', exchangeId: 5, callsigns: ['VEC456'], exchange: { transcript: 'VEC456 turn left', orders: [], trafscript: ['HDG 180'], readback: 'Turning left', rejected: [] } });
  hub.log.push({ id: 6, t: '12:00:05', kind: 'tx', exchangeId: 6, callsigns: [], exchange: { transcript: '', orders: [], trafscript: [], readback: '', rejected: ['Unclear instruction'] } });
  render(<AircraftHud hub={hub} nav={nav} />);
  expect(screen.getAllByRole('article')).toHaveLength(3);
  expect(screen.queryByRole('group', { name: 'Filter message history' })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Select ARR123' }));
  expect(screen.getByText('Descending three thousand')).toBeTruthy();
  expect(screen.queryByText('VEC456 turn left')).toBeNull();
  expect(screen.queryByText('Unassigned · callsign not identified')).toBeNull();
  expect(screen.getAllByRole('article')).toHaveLength(1);
  expect(screen.getByText('VEC456 · MSAW — LOW ALTITUDE')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Select VEC456' }));
  expect(screen.getByText('VEC456 turn left')).toBeTruthy();
  expect(screen.queryByText('Descending three thousand')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Select VEC456' }));
  expect(screen.getAllByRole('article')).toHaveLength(3);
});
