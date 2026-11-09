import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import WeatherStrip from '../src/components/WeatherStrip';

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it('shows stale station readings and reveals the raw report on hover or focus', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({
    icao: 'VOCB', status: 'ok', report: { obsTime: Date.now() / 1000 - 3660,
      wdir: 'VRB', wspd: 3, temp: 26, visibility: '5 km', wxString: '-RA',
      altim: 1016, rawOb: 'sample raw METAR' },
  }) })));
  render(<WeatherStrip icao="VOCB" />);
  await screen.findByText(/Stale · 61 min ago/);
  expect(screen.getByText('light rain')).toBeDefined();
  expect(screen.queryByRole('tooltip')).toBeNull();
  const info = screen.getByRole('button', {name: 'Weather details'});
  fireEvent.mouseEnter(info);
  expect(screen.getByRole('tooltip').textContent).toContain('sample raw METAR');
  fireEvent.mouseLeave(info);
  expect(screen.queryByRole('tooltip')).toBeNull();
  fireEvent.focus(info);
  expect(screen.getByRole('tooltip')).toBeDefined();
  fireEvent.keyDown(info, {key: 'Escape'});
  expect(screen.queryByRole('tooltip')).toBeNull();
});
