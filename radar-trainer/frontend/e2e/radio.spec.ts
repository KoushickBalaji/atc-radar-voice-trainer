import { expect, test } from '@playwright/test';

test('PTT captures onset audio before keydown, uploads once per release, and releases the mic', async ({ page }) => {
  const uploads: Buffer[] = [];
  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/api/voice') {
      const multipart = route.request().postDataBuffer()!;
      const i = multipart.indexOf('RIFF');
      expect(i).toBeGreaterThan(0);
      uploads.push(multipart.subarray(i, i + 8 + multipart.readUInt32LE(i + 4)));
    }
    await route.fulfill({ json: path.includes('health') ? { providers: { stt: true } }
      : path === '/api/demo' ? { airports: [] }
      : path === '/api/nav' ? { waypoints: [], airports: [], fixes: [], routes: [], sector: [], range_nm: 25, center: [0,0] } : {} });
  });
  await page.routeWebSocket('**/ws', ws => {
    const state = { type: 'state', t: 0, aircraft: [], conflicts: [], predicted: [], sim_alive: true };
    ws.send(JSON.stringify(state));
    const tick = setInterval(() => ws.send(JSON.stringify(state)), 500);
    ws.onClose(() => clearInterval(tick));
  });
  // Browser audio graph with a known signal; no physical mic and no provider calls.
  await page.addInitScript(() => {
    const probe = window as typeof window & { signal: ConstantSourceNode; track: MediaStreamTrack; opens: number };
    probe.opens = 0;
    window.addEventListener('keydown', e => {
      if (e.code === 'KeyV' && probe.signal) probe.signal.offset.value = -0.4;
    }, { capture: true });
    navigator.mediaDevices.getUserMedia = async () => {
      probe.opens++;
      const ctx = new AudioContext();
      const dest = ctx.createMediaStreamDestination();
      probe.signal = ctx.createConstantSource();
      probe.signal.offset.value = 0.4;
      probe.signal.connect(dest); probe.signal.start(); await ctx.resume();
      probe.track = dest.stream.getAudioTracks()[0];
      return dest.stream;
    };
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Enable microphone' }).click();
  const ready = page.getByRole('button', { name: 'Hold to talk · V' });
  await expect(ready).toBeVisible();
  expect(uploads).toHaveLength(0);
  await page.keyboard.down('v');
  await expect(page.getByRole('button', { name: 'LISTENING…' })).toBeVisible();
  await page.waitForTimeout(320); // feed more than one look-back window
  expect(uploads).toHaveLength(0);
  await page.keyboard.up('v');
  await expect(ready).toBeVisible();
  expect(uploads).toHaveLength(1);
  const sample = (wav: Buffer, ms: number) => wav.readInt16LE(44 + ms * 16 * 2);
  expect(uploads[0].readUInt32LE(24)).toBe(16000);
  expect(sample(uploads[0], 70)).toBeGreaterThan(3000);
  expect(uploads[0].readInt16LE(uploads[0].length - 2)).toBeLessThan(-3000);
  await page.keyboard.down('v');
  await page.waitForTimeout(200);
  await page.keyboard.up('v');
  await expect(ready).toBeVisible();
  expect(uploads).toHaveLength(2);
  expect(sample(uploads[1], 70)).toBeLessThan(-3000);
  await page.getByRole('button', { name: 'Switch mic off' }).click();
  expect(await page.evaluate(() => [(window as any).opens, (window as any).track.readyState])).toEqual([1, 'ended']);
  await page.getByRole('button', { name: 'Enable microphone' }).click();
  await expect(ready).toBeVisible();
  await page.keyboard.down('v');
  await page.evaluate(() => window.dispatchEvent(new Event('blur')));
  await page.keyboard.up('v');
  await expect(page.getByRole('button', { name: 'Enable microphone' })).toBeVisible();
  expect(uploads).toHaveLength(2);
  expect(await page.evaluate(() => (window as any).track.readyState)).toBe('ended');
});
