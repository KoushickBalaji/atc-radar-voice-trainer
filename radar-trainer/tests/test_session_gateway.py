"""Gateway contracts without BlueSky or provider calls. Real engines: check_hosted_sessions.py."""
import asyncio
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import session_gateway as gateway


def test_default_limit_is_two_and_configured_limit_cannot_exceed_five(monkeypatch):
    monkeypatch.delenv('ATC_MAX_SESSIONS', raising=False)
    async def exercise():
        default = gateway.Sessions()
        maximum = gateway.Sessions(limit=100)
        try:
            assert default.limit == 2
            assert maximum.limit == 5
        finally:
            await default.close()
            await maximum.close()
    asyncio.run(exercise())


def test_concurrent_creation_caps_at_five_and_reserves_unique_slots(monkeypatch):
    processes = []
    class Process:
        def __init__(self, *args, **kwargs):
            self.done = False
            self.args, self.kwargs = args, kwargs
            processes.append(self)
        def poll(self):
            return 0 if self.done else None
    monkeypatch.setattr(gateway.subprocess, 'Popen', Process)

    async def exercise():
        manager = gateway.Sessions(limit=5)
        await manager.client.aclose()
        async def transport(request):
            await asyncio.sleep(.01)
            return httpx.Response(200, json={'sim_alive': True, 'airport_id':'VOCB', 'aircraft':[{'id':'AFR123'}]})
        manager.client = httpx.AsyncClient(transport=httpx.MockTransport(transport))
        try:
            results = await asyncio.gather(*(manager.create() for _ in range(8)), return_exceptions=True)
            seats = [r for r in results if isinstance(r, gateway.Seat)]
            assert len(seats) == len(processes) == 5
            assert len({s.token for s in seats}) == len({s.port for s in seats}) == len({s.directory for s in seats}) == 5
            assert all(len(s.token) >= 32 for s in seats)
            errors = [r for r in results if isinstance(r, HTTPException)]
            assert len(errors) == 3 and all(e.status_code == 503 for e in errors)
            assert all(p.kwargs['env']['ATC_BLUESKY_WORKDIR'].startswith(str(manager.root)) for p in processes)
            assert all('127.0.0.1' in p.args[0] for p in processes)
        finally:
            for p in processes:
                p.done = True
            await manager.close()
        assert not manager.root.exists()
    asyncio.run(exercise())


def test_startup_failure_releases_slot_and_directory(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError('launch failed')
    monkeypatch.setattr(gateway.subprocess, 'Popen', fail)
    async def exercise():
        manager = gateway.Sessions()
        try:
            with pytest.raises(HTTPException) as error:
                await manager.create()
            assert error.value.status_code == 503
            assert manager.seats == {}
            assert list(manager.root.iterdir()) == []
        finally:
            await manager.close()
    asyncio.run(exercise())


class FakeSessions:
    def __init__(self):
        self.seats = {}
        self.forwarded = []
        async def transport(request):
            self.forwarded.append(request)
            return httpx.Response(200,json={'owner':request.headers['x-atc-worker-key']})
        self.client = httpx.AsyncClient(transport=httpx.MockTransport(transport))
    async def create(self):
        token = 'token-' + str(len(self.seats))
        seat = SimpleNamespace(token=token, key='private-'+token, url='http://worker',request_lock=asyncio.Lock())
        self.seats[token] = seat
        return seat
    def get(self, token):
        if token not in self.seats:
            raise HTTPException(410,'expired')
        return self.seats[token]
    async def remove(self, token):
        self.seats.pop(token,None)
    async def reap(self):
        await asyncio.sleep(3600)
    async def close(self):
        await self.client.aclose()


def test_requests_are_bound_to_their_session_and_private_routes_blocked():
    with TestClient(gateway.create_app(FakeSessions)) as client:
        a = client.post('/api/session').json()['token']
        b = client.post('/api/session').json()['token']
        for token in [a,b]:
            assert client.get('/api/state',headers={'X-ATC-Session':token}).json()['owner'] == 'private-'+token
        assert client.get('/api/state').status_code == 410
        assert client.get('/api/state',headers={'X-ATC-Session':'guess'}).status_code == 410
        assert client.post('/api/gui/launch',headers={'X-ATC-Session':a}).status_code == 404
        assert client.post('/api/command',headers={'X-ATC-Session':a},json={'text':'RESET'}).status_code == 404
        assert client.post('/api/demo/airport',headers={'X-ATC-Session':a},json={'icao':'VOMM'}).status_code == 400
        assert client.post('/api/session',headers={'Origin':'https://foreign.example'}).status_code == 403
        response = client.post('/api/voice',headers={'X-ATC-Session':a},content=b'x'*(gateway.MAX_BODY+1))
        assert response.status_code == 413
        client.delete('/api/session',headers={'X-ATC-Session':a})
        assert client.get('/api/state',headers={'X-ATC-Session':a}).status_code == 410
        assert client.get('/api/state',headers={'X-ATC-Session':b}).status_code == 200
        assert client.get('/api/state',headers={'X-ATC-Session':b}).headers['cache-control'] == 'no-store'


def test_voice_upload_goes_only_to_own_worker():
    with TestClient(gateway.create_app(FakeSessions)) as client:
        token = client.post('/api/session').json()['token']
        response = client.post('/api/voice',headers={'X-ATC-Session':token},files={'file':('clip.wav',b'RIFF-test','audio/wav')})
        assert response.json() == {'owner':'private-'+token}
        request = client.app.state.sessions.forwarded[-1]
        assert b'RIFF-test' in request.content
        assert request.headers['content-type'].startswith('multipart/form-data;')
        assert 'x-atc-session' not in request.headers
