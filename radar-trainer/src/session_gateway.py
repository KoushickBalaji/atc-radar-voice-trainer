"""Single-host preview gateway. Each seat owns an entire Python process.

Run exactly ONE gateway process/replica. Tokens are capabilities, not user accounts.
No simulator or provider clients are imported into this process.
"""
import asyncio
import contextlib
import json
import logging
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field

import httpx
import psutil
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from websockets.asyncio.client import connect

ROOT = Path(__file__).resolve().parents[1]
LOG = logging.getLogger('atc.sessions')
MAX_BODY = 4 * 1024 * 1024  # ~2 minutes of 16 kHz mono WAV; reject oversized uploads.
READ_PATHS = {'health', 'nav', 'demo', 'state', 'exercise/report', 'weather/observation/VOCB'}
WRITE_PATHS = {'health/refresh', 'demo/airport', 'demo/reset', 'demo/go-around',
               'sim/pause', 'sim/resume', 'sim/speed', 'voice'}


@dataclass
class Seat:
    token: str
    port: int
    key: str
    directory: Path
    process: subprocess.Popen | None = None
    ready: bool = False
    retired: bool = False
    attached: int = 0
    last_seen: float = field(default_factory=time.monotonic)
    connection: WebSocket | None = None
    request_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def url(self):
        return f'http://127.0.0.1:{self.port}'


class Sessions:
    def __init__(self, limit=None, base_port=None, startup_timeout=90, detached_timeout=90):
        self.limit = min(5, max(1, int(os.environ.get('ATC_MAX_SESSIONS', '2')) if limit is None else limit))
        self.base_port = base_port or int(os.environ.get('ATC_WORKER_BASE_PORT', '18080'))
        self.startup_timeout = startup_timeout
        self.detached_timeout = detached_timeout
        self.seats = {}
        self.lock = asyncio.Lock()
        self.root = Path(tempfile.mkdtemp(prefix='radar-atc-sessions-')).resolve()
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(90, connect=2), trust_env=False)
        self.stopping = False

    def get(self, token):
        seat = self.seats.get(token or '')
        if not seat or not seat.ready or seat.retired or seat.process.poll() is not None:
            raise HTTPException(410, 'This exercise has ended. Start a fresh exercise.')
        seat.last_seen = time.monotonic()
        return seat

    async def create(self):
        async with self.lock:
            if self.stopping or len(self.seats) >= self.limit:
                raise HTTPException(503, f'All {self.limit} practice places are in use. Please try again shortly.', headers={'Retry-After': '30'})
            token = secrets.token_urlsafe(32)
            used = {s.port for s in self.seats.values()}
            port = next(p for p in range(self.base_port, self.base_port + self.limit) if p not in used)
            directory = Path(tempfile.mkdtemp(prefix='worker-', dir=self.root)).resolve()
            seat = Seat(token, port, secrets.token_urlsafe(32), directory)
            self.seats[token] = seat  # Reserve BEFORE launching; concurrent creates cannot exceed capacity.
        try:
            # Static navigation cache is safe to COPY; never share writable runtime state.
            cache = os.environ.get('ATC_NAV_CACHE')
            if cache and (Path(cache) / 'navdata.p').is_file():
                target = directory / 'bluesky' / 'cache'
                target.mkdir(parents=True)
                await asyncio.to_thread(shutil.copy2, Path(cache) / 'navdata.p', target / 'navdata.p')
            env = os.environ.copy()
            env.update(ATC_WORKER_KEY=seat.key, ATC_SIMPLE_DEMO='1', ATC_AIRPORT='VOCB',
                       ATC_BLUESKY_WORKDIR=str(directory / 'bluesky'), MPLCONFIGDIR=str(directory / 'mpl'),
                       PYTHONUNBUFFERED='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
            # No shell. Each process has private files and a loopback-only port.
            with (directory / 'worker.log').open('wb') as log:
                seat.process = subprocess.Popen(
                    [sys.executable, '-m', 'uvicorn', 'session_worker:app', '--app-dir', str(ROOT / 'src'),
                     '--host', '127.0.0.1', '--port', str(port), '--no-access-log', '--log-level', 'warning'],
                    cwd=directory, env=env, stdout=log, stderr=log,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            deadline = time.monotonic() + self.startup_timeout
            while time.monotonic() < deadline:
                if seat.process.poll() is not None:
                    raise RuntimeError('Worker stopped during startup')
                try:
                    response = await self.client.get(seat.url + '/api/state', headers={'X-ATC-Worker-Key': seat.key}, timeout=2)
                    snapshot = response.json() if response.status_code == 200 else {}
                    if snapshot.get('sim_alive') is True and snapshot.get('airport_id') == 'VOCB' and snapshot.get('aircraft'):
                        seat.ready = True
                        seat.last_seen = time.monotonic()
                        LOG.info('Practice worker ready on slot %s', port - self.base_port + 1)
                        return seat
                except (httpx.HTTPError, ValueError):
                    pass
                await asyncio.sleep(.25)
            raise RuntimeError('Simulator startup timed out')
        except BaseException as exc:
            await self.remove(token)
            if isinstance(exc, asyncio.CancelledError):
                raise
            LOG.warning('Worker startup failed: %s', type(exc).__name__)
            raise HTTPException(503, 'The simulator could not start. Please try again shortly.') from exc

    async def remove(self, token):
        # Keep the slot reserved until the old process has actually exited.
        async with self.lock:
            seat = self.seats.get(token)
            if not seat:
                return
            seat.ready = False
            if seat.connection:
                with contextlib.suppress(Exception):
                    await seat.connection.close(code=4001)
            if seat.process and seat.process.poll() is None:
                def terminate_tree():
                    # Windows venv launchers may add a child interpreter. Retire both.
                    with contextlib.suppress(psutil.NoSuchProcess):
                        parent = psutil.Process(seat.process.pid)
                        processes = parent.children(recursive=True) + [parent]
                        for process in processes:
                            with contextlib.suppress(psutil.NoSuchProcess):
                                process.terminate()
                        _, alive = psutil.wait_procs(processes, timeout=5)
                        for process in alive:
                            with contextlib.suppress(psutil.NoSuchProcess):
                                process.kill()
                        psutil.wait_procs(alive, timeout=5)
                    seat.process.wait(timeout=5)
                await asyncio.to_thread(terminate_tree)
            # Only delete the freshly generated worker directory inside our own root.
            if seat.directory.resolve().parent == self.root:
                await asyncio.to_thread(shutil.rmtree, seat.directory, True)
            self.seats.pop(token, None)

    async def reap(self):
        while True:
            await asyncio.sleep(2)
            now = time.monotonic()
            for token, seat in list(self.seats.items()):
                dead = seat.process is not None and seat.process.poll() is not None
                abandoned = seat.ready and not seat.attached and now - seat.last_seen > self.detached_timeout
                if dead or abandoned or seat.retired:
                    await self.remove(token)

    async def close(self):
        self.stopping = True
        for token in list(self.seats):
            await self.remove(token)
        await self.client.aclose()
        # Root was created by mkdtemp and contains only workers created above.
        with contextlib.suppress(OSError):
            self.root.rmdir()


def same_origin(connection):
    origin = connection.headers.get('origin')
    if origin:
        from urllib.parse import urlsplit
        if urlsplit(origin).netloc != connection.headers.get('host'):
            raise HTTPException(403, 'Cross-origin requests are not allowed.')


def create_app(manager_factory=Sessions):
    @contextlib.asynccontextmanager
    async def lifespan(app):
        app.state.sessions = manager_factory()
        reaper = asyncio.create_task(app.state.sessions.reap())
        try:
            yield
        finally:
            reaper.cancel()
            await asyncio.gather(reaper, return_exceptions=True)
            await app.state.sessions.close()

    app = FastAPI(title='radar ATC preview', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware('http')
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/healthz')
    async def health():
        return {'ok': True}

    @app.post('/api/session')
    async def new_session(request: Request):
        same_origin(request)
        seat = await request.app.state.sessions.create()
        return {'token': seat.token}

    @app.delete('/api/session')
    async def end_session(request: Request):
        same_origin(request)
        await request.app.state.sessions.remove(request.headers.get('x-atc-session'))
        return {'ok': True}

    @app.api_route('/api/{path:path}', methods=['GET', 'POST'])
    async def proxy(path: str, request: Request):
        same_origin(request)
        allowed = READ_PATHS if request.method == 'GET' else WRITE_PATHS
        if path not in allowed:
            raise HTTPException(404, 'Not available in the public preview.')
        sessions = request.app.state.sessions
        seat = sessions.get(request.headers.get('x-atc-session'))
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_BODY:
                raise HTTPException(413, 'Transmission too long. Please use a shorter instruction.')
        if path == 'demo/airport':
            try:
                payload = json.loads(body)
                valid = payload.get('icao') == 'VOCB' and payload.get('scenario_id') in {'routine-23', 'level-changeovers-23'}
            except (ValueError, AttributeError):
                valid = False
            if not valid:
                raise HTTPException(400, 'Choose one of the Coimbatore preview exercises.')
        if request.method == 'POST' and seat.request_lock.locked():
            raise HTTPException(409, 'Please wait for the current instruction to finish.')
        async def forward():
            try:
                result = await sessions.client.request(request.method, seat.url + '/api/' + path,
                    content=bytes(body), headers={'X-ATC-Worker-Key': seat.key,
                    'Content-Type': request.headers.get('content-type', 'application/json')})
            except httpx.HTTPError as exc:
                raise HTTPException(502, 'The simulation service did not respond. Please start a fresh exercise.') from exc
            return Response(result.content, status_code=result.status_code,
                            media_type=result.headers.get('content-type', 'application/json'))
        if request.method == 'POST':
            async with seat.request_lock:
                return await forward()
        return await forward()

    @app.websocket('/ws')
    async def websocket(ws: WebSocket):
        try:
            same_origin(ws)
            protocols = ws.scope.get('subprotocols', [])
            token = protocols[1] if len(protocols) == 2 and protocols[0] == 'atc-session' else None
            seat = ws.app.state.sessions.get(token)
            if seat.attached:
                raise HTTPException(409, 'This session already has a radar connection.')
        except HTTPException:
            await ws.close(code=1008)
            return
        seat.attached += 1
        seat.connection = ws
        try:
            async with connect(f'ws://127.0.0.1:{seat.port}/ws',
                additional_headers={'X-ATC-Worker-Key': seat.key}, max_size=16 * 1024 * 1024,
                ping_interval=20, ping_timeout=20, proxy=None) as upstream:
                await ws.accept(subprotocol='atc-session')
                async def to_browser():
                    async for message in upstream:
                        await asyncio.wait_for(ws.send_text(message), 10)
                async def from_browser():
                    while True:
                        message = await ws.receive_text()
                        if len(message) > 128:
                            break
                        await upstream.send(message)
                tasks = [asyncio.create_task(to_browser()), asyncio.create_task(from_browser())]
                try:
                    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                finally:
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
        except (WebSocketDisconnect, OSError, TimeoutError):
            pass
        except Exception:
            LOG.warning('Radar connection ended on slot %s', seat.port - ws.app.state.sessions.base_port + 1)
        finally:
            seat.attached -= 1
            seat.retired = True  # A disconnected capability can never resume its old engine.
            seat.connection = None
            seat.last_seen = time.monotonic()
            with contextlib.suppress(Exception):
                await ws.close(code=4001)

    dist = ROOT / 'frontend' / 'dist'
    if dist.is_dir():
        app.mount('/', StaticFiles(directory=dist, html=True), name='web')
    return app


app = create_app()
