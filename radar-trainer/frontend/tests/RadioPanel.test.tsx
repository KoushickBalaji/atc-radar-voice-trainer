import React from 'react';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import RadioPanel from '../src/components/RadioPanel';
import type { SimHub } from '../src/useSim';
import { RadioMic } from '../src/audio';
import { queueRadio, resetRadioChannel } from '../src/radioChannel';

afterEach(() => { cleanup(); resetRadioChannel(); vi.restoreAllMocks(); vi.useRealTimers(); });

it.each([false, true])('offers the same on/off radio toggle in compact=%s layout', compact => {
  const setRadioNoise = vi.fn();
  const hub = { connection: 'disconnected', state: { sim_alive: false }, providers: { stt: false },
    lastExchange: null, radioNoise: true, setRadioNoise, pushLog: vi.fn() } as unknown as SimHub;
  const view = render(<RadioPanel hub={hub} compact={compact} />);
  const toggle = screen.getByRole('switch', { name: 'Pilot radio effect' }) as HTMLInputElement;
  expect(toggle.checked).toBe(true);
  fireEvent.click(toggle);
  expect(setRadioNoise).toHaveBeenCalledWith(false);
  view.rerender(<RadioPanel hub={{ ...hub, radioNoise: false }} compact={compact} />);
  expect(toggle.checked).toBe(false);
});

it('rejects a busy key press, never auto-starts it, and holds pilot audio while talking', async () => {
  vi.useFakeTimers();
  const begin = vi.spyOn(RadioMic.prototype, 'begin').mockResolvedValue();
  vi.spyOn(RadioMic.prototype, 'arm').mockResolvedValue();
  vi.spyOn(RadioMic.prototype, 'finish').mockResolvedValue(null);
  vi.spyOn(RadioMic.prototype, 'close').mockImplementation(() => {});
  const hub = { connection: 'connected', state: { sim_alive: true }, providers: { stt: true },
    lastExchange: null, radioNoise: true, setRadioNoise: vi.fn(), pushLog: vi.fn() } as unknown as SimHub;
  render(<RadioPanel hub={hub} />);
  await act(async () => { fireEvent.keyDown(window, { code: 'KeyV' }); });
  fireEvent.keyUp(window, { code: 'KeyV' });
  let finish!: () => void;
  act(() => { void queueRadio(() => new Promise<void>(resolve => { finish = resolve; })); });
  expect(screen.getByRole('button', { name: /Frequency busy/ })).toBeTruthy();
  fireEvent.keyDown(window, { code: 'KeyV' });
  expect(begin).not.toHaveBeenCalled();
  await act(async () => { finish(); });
  await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
  fireEvent.keyDown(window, { code: 'KeyV', repeat: true });
  expect(begin).not.toHaveBeenCalled();
  fireEvent.keyUp(window, { code: 'KeyV' });
  await act(async () => { fireEvent.keyDown(window, { code: 'KeyV' }); });
  expect(begin).toHaveBeenCalledOnce();
  const pilot = vi.fn(async () => {});
  act(() => { void queueRadio(pilot); });
  await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
  expect(pilot).not.toHaveBeenCalled();
  await act(async () => { fireEvent.keyUp(window, { code: 'KeyV' }); });
  await act(async () => { await vi.advanceTimersByTimeAsync(1999); });
  expect(pilot).not.toHaveBeenCalled();
  await act(async () => { await vi.advanceTimersByTimeAsync(1); });
  expect(pilot).toHaveBeenCalledOnce();
});
