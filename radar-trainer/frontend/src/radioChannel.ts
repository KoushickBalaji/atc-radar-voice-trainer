import { useSyncExternalStore } from 'react';

// One frequency per browser tab, shared by pilots, replay and controller PTT.
type Job = { run: () => Promise<void>; current: () => boolean; resolve: () => void; reject: (e: unknown) => void };
const listeners = new Set<() => void>();
let queue: Job[] = [];
let owner: symbol | null = null;
let gap: ReturnType<typeof setTimeout> | undefined;
const busy = () => owner !== null || gap !== undefined || queue.length > 0;
const notify = () => listeners.forEach(listener => listener());
const subscribe = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; };
export const useFrequencyBusy = () => useSyncExternalStore(subscribe, busy, () => false);

function release(token: symbol) {
  if (owner !== token) return;
  owner = null;
  gap = setTimeout(() => { gap = undefined; pump(); notify(); }, 2000);
  notify();
}

function pump() {
  if (owner || gap !== undefined) return;
  let job: Job | undefined;
  while ((job = queue.shift())) {
    if (!job.current()) { job.resolve(); continue; }
    const token = owner = Symbol('pilot');
    const active = job;
    notify();
    void (async () => {
      try { await active.run(); active.resolve(); }
      catch (error) { active.reject(error); }
      finally { release(token); }
    })();
    return;
  }
  notify();
}

export function queueRadio(run: () => Promise<void>, current = () => true): Promise<void> {
  return new Promise((resolve, reject) => { queue.push({ run, current, resolve, reject }); pump(); notify(); });
}

/** Busy presses are discarded; a new press is required when free. */
export function acquireMicrophone(): (() => void) | null {
  if (busy()) return null;
  const token = owner = Symbol('controller');
  notify();
  return () => release(token);
}

export function resetRadioChannel() {
  if (gap !== undefined) clearTimeout(gap);
  gap = undefined;
  owner = null;
  const abandoned = queue;
  queue = [];
  abandoned.forEach(job => job.resolve());
  notify();
}
