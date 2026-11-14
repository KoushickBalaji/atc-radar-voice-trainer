"""Private, single-session copy of the existing simulator. Never expose this port."""
import os
import secrets

from starlette.responses import JSONResponse
from atc_app import app as simulator


class PrivateWorker:
    def __init__(self, app):
        self.app = app
        self.key = os.environ['ATC_WORKER_KEY'].encode()

    async def __call__(self, scope, receive, send):
        if scope['type'] in ('http', 'websocket'):
            headers = dict(scope['headers'])
            if not secrets.compare_digest(headers.get(b'x-atc-worker-key', b''), self.key):
                if scope['type'] == 'websocket':
                    await send({'type': 'websocket.close', 'code': 1008})
                else:
                    await JSONResponse({'detail': 'Private worker'}, status_code=403)(scope, receive, send)
                return
        await self.app(scope, receive, send)


app = PrivateWorker(simulator)
