# Docker guide

Run the simulator, trained pricing model, dispatcher and React frontend together
with Docker Engine/Desktop and Docker Compose **v2.24 or newer**. No host Python,
Node or uv installation is needed. The stack uses `sfi_challenge/`, `backend/`, `frontend/`
and the backend's declared model dependency at `model/`.
The older launch guides refer to an external simulator checkout; Docker uses
the simulator included in this repository instead.

## Run on this or another computer

1. Clone this project with its simulator submodule, then enter the project:

   ```sh
   git clone --recurse-submodules <YOUR_PROJECT_URL>
   cd sfi-challenge
   ```

   If you already cloned without submodules, run:

   ```sh
   git submodule update --init --recursive
   ```

   The simulator uses a public HTTPS URL, so no custom SSH configuration is
   needed. The small frozen model bundle and historical-range artifact under
   `model/artifacts/` are included with this version; no training or separate
   artifact download is needed.
2. Start Docker Desktop (or Docker Engine), then run Compose from the repository root:

   ```sh
   docker compose up --build -d --wait --wait-timeout 240
   ```

   The initial image build downloads dependencies and can take several minutes;
   the readiness timeout starts after the builds. The locked PyTorch Linux
   dependencies are large, so allow several GB of Docker disk space. They use
   the existing lockfile and require no GPU. No model training happens at startup.
   The loader accepts PyTorch platform suffixes such as `+cu130`/`+cpu` for the
   same release, preserving dependency-release and artifact-integrity checks.
3. Open **http://localhost:5173/dashboard**. API docs are on ports 8000
   (dispatcher), 9000 (model), and 8087 (simulator).

No `.env` file or credentials are required for the demo. Compose loads working
defaults from the root `.env.example`, seeds the simulator, and applies database
migrations. It creates an empty history directory if needed; optional historical
CSV import is disabled by default. Local Python/Node setup and service URLs
are handled inside Docker.

The simulator seeds a fresh database. Migrations run once as a separate job on
each Compose launch, before one dispatcher process starts. Existing rows are
preserved. The frontend waits for board synchronization, terminal and fleet data;
the model check requires a successful neural-network prediction, not just OpenAPI.
The `migrate` container exiting with code 0 is expected.

## Model API

The model is a separate HTTP service built from the root `model/` directory;
the `project-model/` worktree is excluded from Docker builds. The backend's
editable dependency also points to `../model`, so local and Docker runs use
the same source.

With the default ports, open **http://localhost:9000/docs** or
**http://localhost:9000/openapi.json**. Model endpoints include:

- `POST /api/v1/predict-bid` for neural-network bid advice.
- `POST /api/v1/manual-mode/evaluate` for manual bid analysis.
- `POST /api/v1/autopilot/evaluate` and `/api/v1/autopilot/analyze-batch`
  for explicitly enabled, authenticated autopilot decisions.

The dispatcher calls `http://model:9000` on the Docker network. `MODEL_PORT`
changes the host-facing port without changing that internal address.
Check actual prediction readiness with:

```sh
docker compose exec model python /app/docker/healthcheck.py model
```

This sends a supported prediction and verifies positive prices and the expected
model version. An OpenAPI response by itself does not prove the model loaded.

## Configuration

To customize the demo, create a local configuration once:

```sh
cp .env.example .env
```

If `.env` already exists, edit it rather than overwriting it. The root
`.env.example` supplies defaults; `.env` overrides them. Existing `backend/.env`
and frontend env files are excluded from Docker images and are not used by the
stack. Local `.env` files stay ignored by Git.

Edit `.env`, then rerun `docker compose up -d --wait --wait-timeout 240`.
Compose recreates services whose configuration changed. No rebuild is needed for
runtime settings. Simulator speed/settings changed in the UI reset on restart.

| Setting | Purpose |
| --- | --- |
| `FRONTEND_PORT`, `BACKEND_PORT`, `SIMULATOR_PORT`, `MODEL_PORT` | Host ports; defaults 5173, 8000, 8087 and 9000 |
| `BIND_ADDRESS` | Default `127.0.0.1`; use `0.0.0.0` for access from other machines |
| `COMPOSE_PROJECT_NAME` | Stack and volume namespace; change for an independent instance |
| `MODEL_ARTIFACTS_DIR` | Host directory containing model `models/` and `baselines/`, mounted read-only |
| `MODEL_BUNDLE_NAME`, `MODEL_RANGE_NAME`, `MODEL_EXPECTED_VERSION` | Artifact names and expected prediction version |
| `BACKEND_HISTORY_DIR` | Host directory mounted read-only as `/history` |
| `HISTORY_CSV_PATH` | Empty to disable import; otherwise a container path under `/history` |
| `SIMULATION_SPEED`, `ORDER_INTERVAL_SECONDS`, `ORDER_TTL_SIM_MINUTES` | Demo speed, offer arrival interval and offer lifetime |
| `BOARD_WEBSOCKET_ENABLED`, `BOARD_SYNC_INTERVAL_SECONDS` | Dispatcher synchronization settings |

To import your own historical CSV, put it in `BACKEND_HISTORY_DIR` and set
`HISTORY_CSV_PATH=/history/historical_shipments.csv`. Leave this empty for the
self-contained demo.

The example includes fleet sizing, bidding and model policy options. Any additional
backend/model environment setting can be added to the same file. Compose fixes
the internal service URLs and SQLite paths so changing host ports does not break
container networking. SQLite lives in named volumes. Use a Compose override file
if you need an external board/model or a different database layout.

For a separate configuration, copy the example to `.env.docker.local`, set
`SFI_ENV_FILE=.env.docker.local` inside it, and use this flag for every command:

```sh
docker compose --env-file .env.docker.local up --build -d --wait --wait-timeout 240
```

`--env-file` controls Compose substitutions; `SFI_ENV_FILE` selects the settings
injected into Python containers. Shell variables override Compose substitutions.
Do not put credentials in frontend `VITE_*` settings. Live autopilot defaults
to disabled; enable it explicitly with matching backend/model tokens and the
enable/kill controls documented in `.env.example`. A service launch does
not start or resume an autopilot run.

The frontend runs the documented Vite demo server to retain local simulator
Settings controls and WebSocket proxying. Browser requests stay on the frontend
origin, including when accessed from another machine; container DNS names are
used only by the proxies. For public production hosting, use a built static
frontend with a reverse proxy and configure access controls separately.

## Manage the stack

```sh
docker compose ps -a
docker compose logs -f --tail=100
docker compose logs model backend migrate
docker compose down
```

`down` stops the stack and preserves named volumes. Runtime data is not included
in an image or copied automatically to another machine. The default model
artifacts come with the project. Copy custom model artifacts, optional history
files and configuration separately; back up/restore the named
volumes too if you need the existing operational state. The simulator's generated
history is persisted in its own volume.

For a **fresh demo that discards both databases and simulator history**, stop the
stack and back up its volumes first, then explicitly run:

```sh
docker compose down --volumes
docker compose up -d --wait --wait-timeout 240
```

Host model artifacts and backend historical CSVs remain intact. Refresh the
browser after a full reset.

To transfer prebuilt images to a matching CPU architecture without rebuilding:

```sh
docker compose build
docker image save -o sfi-images.tar sfi-challenge-python:local sfi-challenge-simulator:local sfi-challenge-frontend:local
# On the destination, alongside this repo, configuration and model artifacts:
docker image load -i sfi-images.tar
docker compose up --no-build -d --wait --wait-timeout 240
```

For a different CPU architecture, build on the destination machine. If startup
fails, inspect `docker compose ps -a` and the failing service's logs. Missing or
incompatible model artifacts fail readiness; restore the matching bundle and
lockfile. A configured missing/invalid history CSV fails dispatcher startup.
After fixing settings, rerun `up`; a readiness timeout leaves containers available
for inspection, and `docker compose down` stops them.
