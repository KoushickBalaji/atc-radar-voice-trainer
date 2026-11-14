# radar ATC public preview readiness

> Implementation update, 12 November 2026: the isolation gateway and worker processes are now implemented, with a default limit of **two** concurrent sessions following resource measurement. See [the current deployment guide](RENDER_DEPLOYMENT.md) for validation results and remaining Linux/hosting checks. The assessment below records the earlier UI-only stage; mobile work is now deferred.

Assessment: 12 November 2026. UI preparation only; no deployment, backend changes, authentication changes, or airport configuration changes.

## Decision

The entry flow is implemented. The existing server is **not ready for independent public visitors**. A single backend instance currently shares its simulation, radio state and broadcasts with all clients. Hosting the frontend alone does not fix this.

The agreed reconnect policy is **start a fresh isolated session**, with a clear restart notice. Persisting or restoring the previous exercise is not required. Stable connections during an ordinary exercise remain required; routine platform timeouts should not repeatedly restart practice.

## What the UI now does

- Opens on a tower-themed welcome page with Start, About and Tutorial.
- Offers Coimbatore only, followed by its two existing scenarios.
- Imports `data/traffic/VOCB.json` read-only at build time for scenario identifiers, traffic and full briefing text. The backend data remains the source; rebuild after changing it.
- Shows a scenario list alongside the selected briefing, traffic roster and exercise assumptions.
- Sends the airport/scenario selection only after confirmation, then pauses before mounting the simulator.
- Provides in-app back buttons and a confirmation before leaving the simulator. Leaving pauses the exercise; launching again resets it. Reload/close warns while the simulator is open. Screen navigation is local React state, not separately addressable routes.
- Uses one screenshot of the real UI with deterministic example traffic, highlighting six areas in sequence. It is an instructional illustration, not evidence of a live engine run.
- Adapts the new entry screens to narrow viewports. The radar workspace has not been redesigned for mobile.
- Retains the existing `?advanced=1` interface. The normal preview flow hides the simulator's airport/exercise dropdowns and returns users to the briefing to change exercise. Other airports and their configs remain intact.

## Deployment blockers and proposed next implementation

### Visitor isolation

Owning sources:

- `src/atc_app.py`: module-level `SIM`, `EX`, `_event_q`, `_radio_lock`, `_voice_evidence` and `MGR`; `_broadcaster` sends the same simulation and radio events to connected clients. Selection, reset, voice and control endpoints operate on this shared state.
- `src/bluesky_runtime.py`: module-level `_BS` and the imported BlueSky module own one initialized runtime. Multiple `SimManager` objects in one process would not establish independent engines.
- `frontend/src/useSim.ts`: connects to a same-origin `/ws`, retries after disconnect, and currently assumes that it is reconnecting to the existing shared engine.

Recommended next design: a session gateway that allocates an isolated worker process/container per active visitor. Bind **all** REST commands, voice requests, state and WebSocket events to that worker through an opaque session capability. This is anonymous session routing, not a user login system. Keep work directories, radio queues and pending audio isolated too. Do not trust a client-supplied arbitrary worker identifier as access authority.

On disconnect/reconnect, retire the old worker after a bounded cleanup period, discard its pending transmissions, allocate a new worker, and show a restart notice before starting the new exercise. Browser tabs should receive independent sessions as well. Limit concurrent workers and clean up abandoned sessions so public traffic cannot create unlimited simulations or provider calls.

### Hosting fit

The Vite frontend can be built with `npm ci` and `npm run build`, producing `frontend/dist`. A Vercel project rooted at `radar-trainer/frontend` still needs the repository's `data/traffic/VOCB.json` available during the build, because briefing data is imported from outside the frontend directory. Verify monorepo build access before deploying. No Vercel deployment configuration or project was created in this task.

Current official Vercel documentation supports WebSockets, including FastAPI. However, connections close at function maximum duration, and a new connection may land on another instance. The current in-process BlueSky simulation and separate REST/WS requests therefore need explicit ownership and routing; WebSocket support alone is not sufficient.

My recommendation is Vercel for the frontend, with a continuously running session gateway and isolated BlueSky workers on a suitable process/container host. An all-Vercel worker design needs a separate feasibility check for runtime lifecycle and process isolation. Fresh sessions on reconnect remove persistence work but do not remove session ownership or connection-duration constraints.

Sources checked during this assessment:

- [Vercel WebSockets: lifecycle, reconnects and instance state](https://vercel.com/docs/functions/websockets)
- [Vercel Functions limits](https://vercel.com/docs/functions/limitations)

The frontend currently uses same-origin `/api/*` and `/ws`; the Vite development proxy targets local port 8000. Production needs a verified routing arrangement for both HTTP and WebSocket traffic. Local proxy settings do not configure Vercel. Keep provider keys server-side. No authentication UI is proposed or added.

### Release evidence still needed

1. Two independent browser contexts: different scenarios, instructions, pause/reset actions and radio exchanges must never affect the other session.
2. Disconnect/reconnect one visitor: only that visitor gets a fresh exercise and restart notice; no stale audio or commands reach it.
3. Run a complete exercise and a longer soak with several simultaneous visitors; record disconnect reasons, heartbeat gaps, worker failures, memory and provider latency. Test beyond the hosting platform's configured connection limits.
4. Verify HTTPS microphone permission, recording and readback playback on real devices, and failure/retry behaviour when providers or workers are unavailable.
5. Verify public-preview worker cleanup, concurrency limits and provider spend controls. These are service capacity controls, not a login requirement.

These are pre-release tests for the later backend/hosting work. They have not been claimed as passing in this frontend-only task.

## Verification of this UI change

- TypeScript check and Vite production build passed; both local image assets are included in `frontend/dist/onboarding`.
- All 26 frontend unit tests passed, including scenario selection, launch failure/retry, one-image tutorial progression, and cancellation/confirmation of exit.
- Headless Edge checks passed for the welcome-to-simulator flow with intercepted API/WebSocket fixtures, no entry-page simulation requests, Coimbatore-only selection, launch/pause, exit, tutorial progression and absence of horizontal overflow at 390px and 768px. Rendered desktop and narrow-screen captures were inspected; a tutorial CSS naming collision and retained scroll position were corrected.
- The existing browser push-to-talk regression passed through the new entry flow using synthetic audio, including upload and microphone cleanup behaviour.
- No live BlueSky/voice-provider run, physical microphone check, real mobile-device test, public hosting test or concurrent-user isolation test was performed for this change.

## Mobile effort

Rough engineering estimates, not commitments; assume one developer familiar with this codebase and access to real iOS/Android test devices. Deployment isolation work is separate.

| Scope | Incremental effort | What changes |
| --- | --- | --- |
| Welcome, airport, briefing, About and tutorial | Included in this UI work | Responsive layouts; screenshot scales down, so full desktop details are naturally smaller. |
| Usable tablet simulator, preferably landscape | About 2–4 working days | Touch panning/selection, panel sizing, comfortable controls, portrait fallback and audio checks. |
| Comfortable phone simulator | About 5–8 working days | Radar/traffic/radio view switching, persistent push-to-talk, touch gestures, readable labels, safe-area layout and real-device audio/orientation testing. |

Code evidence: the workspace currently reserves a 410px console on desktop and stacks it below the radar under 1100px; the canvas interaction is primarily mouse/wheel based. The radio already has pointer handlers, which helps, but does not establish real-device audio reliability. A phone experience therefore needs interaction design, not just CSS shrinking.

Recommendation: use desktop/laptop for the first professional feedback sessions, allow the entry screens to work on phones, and decide on a tablet/phone workspace after the first feedback round.

## Assets

`frontend/public/onboarding/tower.webp` is an optimized copy of an image generated with the built-in Image Generation tool. It is a generic tower illustration, not a photograph of Coimbatore.

Generation prompt: “Photorealistic editorial architectural photograph for an air traffic control simulator welcome screen. Wide landscape 16:9 composition. An elegant airport control tower on the right third, seen from ground level at blue hour, warm amber light inside the glass cab, runway and distant low hills along the bottom, deep slate blue sky with generous clean dark negative space on the left for interface text. Restrained professional aviation mood, realistic architecture, subtle atmospheric haze, crisp detail, no people, no lettering, no logos, no interface elements. Generic airport, do not claim to depict a real airport.”

`frontend/public/onboarding/radar-walkthrough.png` is a browser capture of the existing simulator UI with deterministic traffic fixtures and real Coimbatore navigation data. It does not invoke live voice services.
