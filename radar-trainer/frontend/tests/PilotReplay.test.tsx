import React from 'react';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import PilotReplay from '../src/components/PilotReplay';
import { playB64Wav } from '../src/audio';
import { acquireMicrophone, resetRadioChannel } from '../src/radioChannel';

vi.mock('../src/audio', () => ({ playB64Wav: vi.fn(async () => {}) }));
afterEach(() => { cleanup(); resetRadioChannel(); vi.useRealTimers(); vi.clearAllMocks(); });

it('queues replay behind the controller and uses the selected radio effect', async () => {
  vi.useFakeTimers();
  const release = acquireMicrophone()!;
  render(<PilotReplay audio="sample" radioNoise={false} />);
  fireEvent.click(screen.getByRole('button', { name: 'Replay pilot readback' }));
  expect(playB64Wav).not.toHaveBeenCalled();
  expect((screen.getByRole('button') as HTMLButtonElement).disabled).toBe(true);
  act(() => release());
  await act(async () => { await vi.advanceTimersByTimeAsync(1999); });
  expect(playB64Wav).not.toHaveBeenCalled();
  await act(async () => { await vi.advanceTimersByTimeAsync(1); });
  expect(playB64Wav).toHaveBeenCalledWith('sample', undefined, false);
});
