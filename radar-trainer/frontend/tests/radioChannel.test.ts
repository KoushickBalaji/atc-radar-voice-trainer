import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { acquireMicrophone, queueRadio, resetRadioChannel } from '../src/radioChannel';

beforeEach(() => vi.useFakeTimers());
afterEach(() => { resetRadioChannel(); vi.useRealTimers(); });

it('preserves FIFO and waits for completion plus two seconds; mic cannot interrupt', async () => {
  let finish!: () => void;
  const first = queueRadio(() => new Promise<void>(resolve => { finish = resolve; }));
  const second = vi.fn(async () => {});
  const third = vi.fn(async () => {});
  void queueRadio(second); void queueRadio(third);
  expect(acquireMicrophone()).toBeNull();
  await vi.advanceTimersByTimeAsync(10000);
  expect(second).not.toHaveBeenCalled();
  finish(); await first;
  await vi.advanceTimersByTimeAsync(1999);
  expect(second).not.toHaveBeenCalled();
  expect(acquireMicrophone()).toBeNull();
  await vi.advanceTimersByTimeAsync(1);
  expect(second).toHaveBeenCalledOnce();
  expect(third).not.toHaveBeenCalled();
  await vi.advanceTimersByTimeAsync(2000);
  expect(third).toHaveBeenCalledOnce();
});

it('holds pilot calls until PTT release and requires a fresh mic acquisition', async () => {
  const release = acquireMicrophone()!;
  const pilot = vi.fn(async () => {});
  void queueRadio(pilot);
  await vi.advanceTimersByTimeAsync(10000);
  expect(pilot).not.toHaveBeenCalled();
  release(); release();
  await vi.advanceTimersByTimeAsync(1999);
  expect(pilot).not.toHaveBeenCalled();
  await vi.advanceTimersByTimeAsync(1);
  expect(pilot).toHaveBeenCalledOnce();
  await vi.advanceTimersByTimeAsync(2000);
  expect(acquireMicrophone()).toBeTypeOf('function');
});

it('recovers from failed playback and drops pending work on reset', async () => {
  const failed = queueRadio(async () => { throw new Error('audio'); });
  await expect(failed).rejects.toThrow('audio');
  const pending = vi.fn(async () => {});
  const completion = queueRadio(pending);
  resetRadioChannel();
  await completion;
  await vi.advanceTimersByTimeAsync(2000);
  expect(pending).not.toHaveBeenCalled();
  expect(acquireMicrophone()).toBeTypeOf('function');
});

it('ignores stale release callbacks after a reset', async () => {
  const oldRelease = acquireMicrophone()!;
  resetRadioChannel();
  const newRelease = acquireMicrophone()!;
  oldRelease();
  const pilot = vi.fn(async () => {});
  void queueRadio(pilot);
  await vi.advanceTimersByTimeAsync(3000);
  expect(pilot).not.toHaveBeenCalled();
  newRelease();
  await vi.advanceTimersByTimeAsync(2000);
  expect(pilot).toHaveBeenCalledOnce();
});
