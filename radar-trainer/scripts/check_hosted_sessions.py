"""Real BlueSky concurrent-session proof; providers point to a closed local port.

No paid APIs. Run with the project venv. Requires psutil for resource measurement.
Writes a JSON report only when --output is supplied. Never prints session tokens.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import httpx
import psutil
from websockets.asyncio.client import connect

ROOT = Path(__file__).resolve().parents[1]


async def run(seconds, users=2):
    env = os.environ.copy()
    env['ATC_MAX_SESSIONS'] = str(users)
    if (ROOT / 'bluesky' / 'cache' / 'navdata.p').is_file():
        env['ATC_NAV_CACHE'] = str(ROOT / 'bluesky' / 'cache')
    for kind in ('STT', 'LLM', 'TTS'):
        env['ATC_' + kind + '_URL'] = 'http://127.0.0.1:9'
        env['ATC_' + kind + '_KEY'] = 'offline-proof'
    with tempfile.TemporaryDirectory(prefix='atc-proof-') as temp:
        with open(Path(temp) / 'gateway.log', 'wb') as log:
            proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'session_gateway:app',
                '--app-dir', str(ROOT / 'src'), '--host', '127.0.0.1', '--port', '18600',
                '--no-access-log', '--log-level', 'warning'], env=env, stdout=log, stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        tokens, sockets, workers = [], [], []
        async with httpx.AsyncClient(base_url='http://127.0.0.1:18600', timeout=110, trust_env=False) as client:
            async def api(token, path, payload=None):
                response = await client.request('GET' if payload is None else 'POST', '/api/' + path,
                                               headers={'X-ATC-Session': token}, json=payload)
                if response.status_code >= 500:
                    print('Gateway error:',response.text)
                    print((Path(temp)/'gateway.log').read_text(errors='replace')[-6000:])
                    for worker in workers:
                        with __import__('contextlib').suppress(Exception):
                            worker_log=Path(worker.cwd())/'worker.log'
                            if worker_log.exists():
                                print(worker_log.read_text(errors='replace')[-3000:])
                response.raise_for_status()
                return response.json()
            try:
                for _ in range(100):
                    if proc.poll() is not None:
                        raise RuntimeError('Proof gateway failed to start; check that port 18600 is free.')
                    try:
                        if (await client.get('/healthz')).is_success:
                            break
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(.2)
                started = time.monotonic()
                results = await asyncio.gather(*(client.post('/api/session') for _ in range(users)))
                for response in results:
                    if response.is_success:
                        tokens.append(response.json()['token'])
                    else:
                        print('Startup response:', response.status_code, response.text)
                assert len(tokens) == users, 'All workers must start successfully'
                startup_s = time.monotonic() - started
                workers = psutil.Process(proc.pid).children(recursive=True)
                engines = [p for p in workers if 'session_worker:app' in p.cmdline() and not p.children()]
                assert len(engines) == users, f'Expected {users} worker interpreters, found {len(engines)}'
                assert (await client.post('/api/session')).status_code == 503, 'Visitor over capacity must be rejected'
                assert (await client.get('/api/state')).status_code == 410
                assert (await client.get('/api/state', headers={'X-ATC-Session':'invalid'})).status_code == 410
                assert (await client.post('/api/gui/launch', headers={'X-ATC-Session':tokens[0]})).status_code == 404
                assert (await client.post('/api/session',headers={'Origin':'https://foreign.example'})).status_code == 403
                for token in tokens:
                    await api(token, 'demo/airport', {'icao':'VOCB','scenario_id':'routine-23'})
                    socket = await connect('ws://127.0.0.1:18600/ws',subprotocols=['atc-session',token],proxy=None)
                    sockets.append(socket)
                await api(tokens[0], 'sim/speed', {'value':4})
                await asyncio.sleep(.5)
                states = await asyncio.gather(*(api(t, 'state') for t in tokens))
                assert [s['speed'] for s in states] == [4]+[1]*(users-1), 'Speed crossed session boundary'
                await api(tokens[0], 'demo/airport', {'icao':'VOCB','scenario_id':'level-changeovers-23'})
                states = await asyncio.gather(*(api(t, 'state') for t in tokens))
                assert [s['traffic']['id'] for s in states] == ['level-changeovers-23'] + ['routine-23']*(users-1)
                # Drain all streams while sampling a short concurrent real-engine soak.
                seen, frames = {}, [0]*users
                async def read(i, ws):
                    async for value in ws:
                        message = json.loads(value)
                        if message.get('type') == 'state':
                            seen[i] = message
                            frames[i] += 1
                readers = [asyncio.create_task(read(i, ws)) for i, ws in enumerate(sockets)]
                await api(tokens[0], 'sim/speed', {'value':1})
                for token in tokens:
                    await api(token, 'sim/resume', {})
                processes = [psutil.Process(proc.pid), *workers]
                for p in processes:
                    p.cpu_percent()
                peak_mb, cpu = 0, []
                for _ in range(seconds):
                    await asyncio.sleep(1)
                    peak_mb = max(peak_mb, sum(p.memory_info().rss for p in processes)/1024**2)
                    cpu.append(sum(p.cpu_percent() for p in processes))
                assert all(not r.done() for r in readers), 'A radar stream dropped during the soak'
                assert all(n >= seconds * 3 for n in frames), 'Radar streams stalled'
                assert [seen[i]['traffic']['id'] for i in range(users)] == ['level-changeovers-23'] + ['routine-23']*(users-1)
                await client.delete('/api/session',headers={'X-ATC-Session':tokens[0]})
                assert (await client.get('/api/state',headers={'X-ATC-Session':tokens[0]})).status_code == 410
                await api(tokens[1], 'sim/pause', {})
                replacement = await client.post('/api/session')
                replacement.raise_for_status()
                fresh = replacement.json()['token']
                assert fresh not in tokens
                tokens.append(fresh)
                assert (await api(fresh,'state')).get('traffic') is None, 'Replacement inherited old traffic'
                assert (await api(tokens[1],'state'))['traffic']['id'] == 'routine-23'
                for r in readers:
                    r.cancel()
                await asyncio.gather(*readers,return_exceptions=True)
                report = dict(passed=True, platform=sys.platform, users=users, startup_seconds=round(startup_s,2),
                    soak_seconds=seconds, peak_total_rss_mb=round(peak_mb,1),
                    simulation_speed='1x for all sessions during soak',
                    mean_cpu_percent_one_core=round(sum(cpu)/len(cpu),1), frames=frames,
                    checks=['separate processes','visitor over capacity rejected','missing/invalid tokens rejected',
                            'cross-origin allocation rejected','private routes blocked','independent scenario/speed/state streams',
                            'no stream loss during soak','deleted token invalidated','fresh replacement','other session survives'],
                    limitations='Local OS, offline providers, not Linux container or hosted capacity proof.')
                return report
            finally:
                for ws in sockets:
                    await ws.close()
                for token in tokens:
                    with __import__('contextlib').suppress(Exception):
                        await client.delete('/api/session',headers={'X-ATC-Session':token})
                with __import__('contextlib').suppress(psutil.Error):
                    workers += psutil.Process(proc.pid).children(recursive=True)
                proc.terminate()
                await asyncio.to_thread(proc.wait,10)
                for worker in workers:
                    with __import__('contextlib').suppress(psutil.NoSuchProcess):
                        worker.kill()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds',type=int,default=60)
    parser.add_argument('--users',type=int,choices=range(2,6),default=2)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    result = asyncio.run(run(args.seconds,args.users))
    print(json.dumps(result,indent=2))
    if args.output:
        args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
