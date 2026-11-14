import {afterEach, expect, it, vi} from 'vitest';
import {beginSession, endSession, expireSession, hasSession, sessionFetch, socketProtocols} from '../src/session';

afterEach(async()=>{ await endSession(); vi.unstubAllGlobals(); });

it('attaches a capability to API and socket requests without storing it in browser storage',async()=>{
  const token='a'.repeat(43);
  const fetcher=vi.fn(async()=>new Response(JSON.stringify({token}),{status:200}));
  vi.stubGlobal('fetch',fetcher);
  await beginSession();
  expect(socketProtocols()).toEqual(['atc-session',token]);
  await sessionFetch('/api/voice',{method:'POST',body:new FormData()});
  const init=fetcher.mock.calls.at(-1)![1] as RequestInit;
  expect(new Headers(init.headers).get('X-ATC-Session')).toBe(token);
  expect(sessionStorage.getItem('atc-session')).toBeNull();
  await endSession();
  expect(hasSession()).toBe(false);
  expect(fetcher.mock.calls.at(-1)![1]).toMatchObject({method:'DELETE',headers:{'X-ATC-Session':token}});
});

it('reports capacity instead of falling back to the shared backend',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({detail:'All five practice places are in use.'}),{status:503})));
  await expect(beginSession()).rejects.toThrow('All five');
  expect(hasSession()).toBe(false);
});

it('allows the original local single-user launcher only on an explicit missing endpoint',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>new Response('{}',{status:404})));
  await beginSession();
  expect(hasSession()).toBe(false);
});

it('invalidates an ended session and notifies the entry screen once',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify({token:'b'.repeat(43)}),{status:200})));
  await beginSession();
  const ended=vi.fn();
  window.addEventListener('atc-session-ended',ended);
  expireSession(); expireSession();
  expect(ended).toHaveBeenCalledTimes(1);
  expect(hasSession()).toBe(false);
  window.removeEventListener('atc-session-ended',ended);
});

it('does not expire a new session when an old request finally returns', async () => {
  let finish!: (response: Response) => void;
  let sequence = 0;
  vi.stubGlobal('fetch',vi.fn(async (path: string, init?: RequestInit) => {
    if(path === '/api/nav') return new Promise<Response>(resolve => { finish = resolve; });
    return new Response(JSON.stringify({token: String(init?.method === 'POST' ? ++sequence : sequence).repeat(43)}),{status:200});
  }));
  await beginSession();
  const oldRequest = sessionFetch('/api/nav');
  await beginSession();
  const current = socketProtocols();
  finish(new Response('{}',{status:410}));
  await oldRequest;
  expect(socketProtocols()).toEqual(current);
  expect(hasSession()).toBe(true);
});
