# radar ATC feedback deployment

Render demo configuration: **one concurrent exercise on the Free instance**. The launcher default remains two for local development; the Blueprint explicitly sets `ATC_MAX_SESSIONS=1`. Mobile work is deferred.

## What is ready

- One public gateway serves the built frontend and routes API/WebSocket traffic.
- Each visitor gets a separate Python process containing the existing FastAPI/BlueSky simulator, radio state and private working directory. No aircraft/procedure configuration was changed.
- A random capability lives in the browser tab's memory, not cookies or local storage. Two tabs get separate sessions. HTTP sends the capability in `X-ATC-Session`; WebSocket sends it as a subprotocol, not a URL query parameter. Worker ports bind to loopback and require a separate private key.
- Slots are reserved before process startup. A visitor above the configured limit gets a capacity message and Retry-After (the second visitor on Render). Slots are released only after process-tree termination.
- The gateway waits for actual initialized aircraft before reporting ready. Static navigation cache is copied into each private work directory to reduce startup time; no writable simulation state is shared.
- Leaving deletes the worker. A dropped radar connection retires its capability permanently; the UI explains that the exercise ended and returns to the briefing. Enter simulator creates a fresh session. Queued/playing radio audio and microphone capture are cleaned up on exit.
- Crashed/retired workers are reaped every two seconds. An allocated worker with no radar connection is reclaimed after 90 seconds without requests. There is no arbitrary time limit on a connected exercise.
- Unneeded public endpoints (GUI launch, arbitrary text commands, scenario generation, etc.) are not exposed. Airport selection is restricted at the gateway to the two Coimbatore exercises. Existing backend airport data and the standalone launcher are unchanged.

The cap can be adjusted with `ATC_MAX_SESSIONS` (1–5, default 2). Keep **exactly one gateway process and one host instance**. Multiple Uvicorn workers or Render replicas would require shared routing and are intentionally outside this feedback deployment.

## Run locally

From `radar-trainer`:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-hosted.txt
$env:PORT = '8001'
.venv\Scripts\python.exe run_hosted.py
```

Open `http://127.0.0.1:8001`. The launcher accepts `OPENAI_API_KEY` from the environment or the existing parent workspace `.env`. The key is never included in the frontend. The existing `run_openai.py` launcher remains a single-user local tool; do not deploy that entry point publicly.

## Local evidence

The real-engine proof uses offline provider URLs. No paid voice API requests were made.

| Run | Duration | Peak gateway + worker RSS | Mean CPU (100% = one core) | Outcome |
| --- | --- | --- | --- | --- |
| Five sessions, all 1× | 180 seconds | 1,453.5 MB | 151.9% | Independent streams, no stream loss during the soak |
| Two sessions, all 1× | 180 seconds | 626.4 MB | 54.0% | Independent streams, no stream loss during the soak |

These are Windows measurements on this workstation, not capacity guarantees for Linux or Render. Provider latency, real audio, host contention and 2×/4× speed can change resource use. Startup varied with concurrent local work (approximately 10–28 seconds for these runs). Windows logged connection-reset callbacks during deliberate teardown; no stream ended during the measured soak.

Both proofs checked capacity rejection, missing/invalid capabilities, forbidden public routes, cross-origin allocation rejection, independent scenario/speed changes, worker replacement, and continued operation of the other visitor. The two-tab Edge check also passed against real engines: distinct sessions, independent speed, disconnect notice, old capability rejection, fresh restart, both exits, and no page errors.

The production frontend build and all 33 frontend unit tests passed. The backend suite passed with three opt-in tests skipped; the separate real-engine proofs above were run explicitly. No physical microphone or paid-provider call was tested in this implementation round.

`scripts/check_hosted_sessions.py --users 2 --seconds 180` reproduces the engine proof. It requires `psutil` (included in hosted requirements). `--users 5` tests the higher ceiling. Reports are captured in `HOSTED_SESSION_VALIDATION.json`.

## Deployment files

- `Dockerfile`: multi-stage Node frontend build plus CPU-only Python runtime, with prebuilt navigation cache and an unprivileged runtime user.
- `.dockerignore`: excludes local secrets, virtual environments and generated output from the image context.
- `requirements-hosted.txt`: hosting dependencies, including the existing BlueSky version.
- `render.yaml`: one Singapore web service, **Free** compute, one session, `/healthz`, and redeploy after GitHub checks pass.
- Repository-root `.github/workflows/radar-preview.yml`: builds the Linux image and runs the one-user real-engine proof in a container limited to 0.1 CPU and 512 MB with swap disabled. It does not deploy or require provider credentials.

The blueprint paths target the existing repository layout with `radar-trainer/` below the Git root. If publishing this folder as its own repository, change `dockerfilePath` to `./Dockerfile`, `dockerContext` to `.`, and relocate/adapt the workflow paths.

## Before creating the Render service

1. Push the reviewed deployment changes and wait for the Linux container check to pass. This workstation has no Docker, so the constrained check runs in GitHub Actions.
2. Connect the repository to Render and select Blueprint path `radar-trainer/render.yaml` on `main`.
3. Confirm the web service shows **Free**, one instance, and `ATC_MAX_SESSIONS=1`. Supply `OPENAI_API_KEY` as a secret; voice provider usage is separate from free hosting.
4. Deploy and verify microphone recording and pilot audio over HTTPS through a full exercise. Open another browser while the first exercise is active: it should show capacity reached. Exit the first exercise and retry in the second browser.
5. Free services sleep after 15 minutes without inbound traffic and take time to wake. A restart or deployment ends the current exercise. Passing the offline container check does not establish peak memory with real voice providers.

Future pushes to the linked branch can redeploy after CI passes. Deployments end active exercises; avoid pushing during scheduled feedback sessions. No database, saved sessions, login flow, autoscaling or mobile redesign is required for this release.

Reference: [Render Blueprint fields](https://render.com/docs/blueprint-spec), [Docker deployment](https://render.com/docs/docker), [Git integration](https://render.com/docs/git-provider).
