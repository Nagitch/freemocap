# MUJINA camera FPS experiment

Status: experiment

## Branch management

Keep upstream `main` separate from MUJINA changes. `mujina/main` starts at the
latest upstream release `v2.0.0-alpha.25`; integrate MUJINA work through
`mujina/feature/*` PRs targeting `mujina/main` (or a deliberately introduced
`mujina/develop`). The SkellyCam fork's `mujina/main` starts at the exact
SkellyCam commit pinned by that FreeMoCap release, `26509b06`.

- FreeMoCap: https://github.com/Nagitch/freemocap/issues/1
- SkellyCam: https://github.com/Nagitch/skellycam/issues/1

The FreeMoCap lockfile pins the tested SkellyCam fork commit. After merging the
SkellyCam PR, retain that published commit or update the pin in a separate change;
do not replace it with an unpinned branch dependency.

## Run beside the installed application

Prerequisites: Apple Silicon macOS, Python 3.12, uv, Node.js/npm, C922 cameras and
camera permission for the source Python interpreter. Preserve the USB ports that
were verified to work. Close OBS and the installed FreeMoCap application/server
before accessing cameras. Nothing replaces `/Applications/FreeMoCap.app`.

From this repository:

```sh
uv sync --frozen --python 3.12
cd freemocap-ui
npm ci
cd ..
./tools/mujina/start-dev.sh
```

The launcher uses `.venv/bin/freemocap` explicitly and stores Electron preferences
and FreeMoCap data under ignored `.mujina-data/`. It refuses an occupied 53117
port because upstream's server launcher would otherwise terminate its occupant.
If the UI says Stopped, open the connection dropdown and click **Launch server**.
Click **Connect Cameras**. Open a camera's settings, select **1280 x 720** and
**60 fps**, optionally **Copy to 2 others**, then **Update Settings**. Requested
FPS is not a guarantee of actual throughput. **Device default** leaves the
current driver-selected rate untouched; it does not restore a factory rate.

## P4 validation (2026-11-09 JST)

Existing installed application unchanged. Test runtime: FreeMoCap alpha.25 source,
Python 3.12, OpenCV 4.12, AVFoundation, patched SkellyCam `e3547e4d`.
The API check used port 53119, automatic exposure, one then three C922s, no
recording and no skeleton inference. Each run lasted 25 seconds with the first
5 seconds excluded. Rates use the advance of synchronized capture frame numbers
over wall time, rather than counting every preview message as a capture.

| Cameras | Reported device FPS (each) | Capture frame progression | Preview payload rate |
| --- | --- | --- | --- |
| 1 | 60.00024 | 59.42 FPS | 38.61 FPS |
| 3 | 60.00024 | 58.82 FPS | 40.25 FPS |

Every sampled payload had the expected camera count. [Raw measurements](p4-camera-fps-results.json).
Connecting at 30 FPS and then updating the same three cameras to 60 FPS returned
30.00003 and then 60.00024 for all three. [Update results](p4-camera-fps-update-results.json).
No images or audio were saved. MJPG in the API config is not proof of negotiated
USB compression: AVFoundation may reject FOURCC selection.

The actual source Electron UI was also exercised: launch the explicit source
server, connect three cameras, select 60 FPS, copy to the other two, and update.
All three camera summaries showed 1280x720 / 60.00 FPS and stayed Streaming.
Observed live server FPS was roughly 55-59 and display FPS roughly 30-34.
The installation's pre-existing microphone `Failed to fetch` indicator also
appeared in the source UI; camera settings requests returned HTTP 200.

These results establish camera configuration and short synchronized acquisition,
not exact 60-FPS delivery, long-duration stability, sensor hardware synchronization,
or realtime skeleton-inference performance. Recalibrate after changing capture
settings before evaluating skeleton accuracy.

## Checks and reproduction

```sh
cd freemocap-ui
npm exec --no -- tsc --noEmit
npm exec --no -- vite build
```

SkellyCam: `uv run pytest skellycam/tests/test_requested_framerate.py -q` passed
9 regression cases covering initial setup, rate updates, format/resolution
changes, non-positive rates, rejected requests, and device-reported rates.

For a camera-only API check against a running source server with no other camera
client active:

```sh
.venv/bin/python tools/mujina/verify-camera-fps.py --port 53117 --output .mujina-data/fps-results.json
```

It opens and closes the camera group; use only in a dedicated test session.
The script saves metadata, not frames. The UI build and typecheck passed. Full
application tests and skeleton inference were not run. Upstream CI and dependency
maintenance remain inherited; configure fork CI/Dependabot in a separate scoped
change after this experiment, rather than upgrading dependencies here.
