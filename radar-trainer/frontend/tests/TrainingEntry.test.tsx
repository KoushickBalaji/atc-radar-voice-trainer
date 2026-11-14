import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import TrainingEntry from '../src/TrainingEntry';
import { api } from '../src/api';

vi.mock('../src/SimpleApp', () => ({ default: ({onExit}: {onExit: () => void}) => <button onClick={onExit}>Leave simulator</button> }));
vi.mock('../src/api', () => ({ api: { pause: vi.fn(async () => ({})) } }));
vi.mock('../src/session', () => ({ beginSession: vi.fn(async () => {}), endSession: vi.fn(async () => {}), hasSession: () => false, sessionFetch: (...args: Parameters<typeof fetch>) => fetch(...args) }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.clearAllMocks(); });
function briefing() {
  render(<TrainingEntry />);
  fireEvent.click(screen.getByRole('button', { name: 'Start', exact: true }));
  expect(screen.getAllByRole('option').map(o => o.textContent)).toEqual(['Coimbatore (VOCB)']);
  fireEvent.click(screen.getByRole('button', { name: 'Select scenario', exact: true }));
}
it('does not contact the simulation until confirmation and loads the chosen scenario before pausing', async () => {
  const fetcher = vi.fn(async () => ({ok:true, json:async () => ({airport:{icao:'VOCB'}})}));
  vi.stubGlobal('fetch', fetcher);
  briefing();
  expect(screen.queryByRole('button', { name: /SCENARIO 02/ })).toBeNull();
  expect(screen.getByRole('button', { name: /SCENARIO 01/ }).getAttribute('aria-pressed')).toBe('true');
  expect(fetcher).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', {name:/Enter simulator/}));
  await screen.findByRole('button', { name: 'Leave simulator' });
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({icao:'VOCB', scenario_id:'routine-23'});
  expect(api.pause).toHaveBeenCalledTimes(1);
});
it('preserves selection and offers retry when launching fails', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => ({ok:false,json:async()=>({detail:'Wait for the current transmission to finish.'})})));
  briefing();
  fireEvent.click(screen.getByRole('button', {name:/Enter simulator/}));
  expect((await screen.findByRole('alert')).textContent).toContain('Wait for the current transmission');
  expect(screen.getByRole('button', {name:/SCENARIO 01/}).getAttribute('aria-pressed')).toBe('true');
  expect(api.pause).not.toHaveBeenCalled();
});
it('uses one tutorial image as the highlighted step changes', () => {
  render(<TrainingEntry />);
  fireEvent.click(screen.getByRole('button', {name:'Tutorial'}));
  const image = screen.getByRole('img');
  fireEvent.click(screen.getByRole('button', {name:'Next',exact:true}));
  expect(screen.getByRole('heading',{name:'Traffic and aircraft details'})).toBeTruthy();
  expect(screen.getByRole('img')).toBe(image);
  fireEvent.click(screen.getByRole('button',{name:'Welcome',exact:true}));
  expect(screen.getByRole('button',{name:'Start',exact:true})).toBeTruthy();
});
it('keeps the simulator on cancelled exit and pauses before confirmed exit', async () => {
  vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({airport:{icao:'VOCB'}})})));
  const confirm = vi.spyOn(window,'confirm').mockReturnValue(false);
  briefing();
  fireEvent.click(screen.getByRole('button',{name:/Enter simulator/}));
  fireEvent.click(await screen.findByRole('button',{name:'Leave simulator'}));
  expect(api.pause).toHaveBeenCalledTimes(1);
  confirm.mockReturnValue(true);
  fireEvent.click(screen.getByRole('button',{name:'Leave simulator'}));
  await waitFor(()=>expect(screen.getByRole('heading',{name:'Choose your exercise.'})).toBeTruthy());
  expect(api.pause).toHaveBeenCalledTimes(2);
});
