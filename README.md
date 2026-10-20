# SFI Challenge

A freight dispatch demo with a simulated load board, fleet management, bid pricing,
and booking workflows. A React dashboard shows live updates; a separate model API
provides pricing advice.

## Run

Install and start Docker with Compose v2.24+, then run from the project root:

```sh
./start.sh        # macOS / Linux
```

```powershell
.\start.cmd      # Windows
```

Open **http://localhost:5173/dashboard**. All operational features, including
autopilot, are enabled by default.
Use Run in the dashboard to start autopilot; service startup creates no run.
The launcher downloads a missing simulator (requires Git), builds the services,
applies migrations, and waits for readiness. The first build takes several minutes.

Use `stop`, `status`, or `logs` after either launcher command. Stopping preserves data.

## Structure

```text
backend/        FastAPI dispatcher, fleet, and booking logic
frontend/       React dashboard
model/          Pricing API and trained model artifacts
sfi_challenge/  Load-board simulator (Git submodule)
docker/         Dockerfiles and readiness checks
compose.yaml    Service configuration
start.*         Launchers for macOS, Linux, and Windows
.env.example    Default settings; optional overrides in .env
```

For direct Docker commands and configuration, see [DOCKER.md](DOCKER.md).

## Optional environment configuration

Defaults work without configuration. To customize them, copy the root template
once (PowerShell: `Copy-Item .env.example .env`):

```sh
cp .env.example .env
```

If `.env` already exists, edit it instead of overwriting it. You can keep only the
settings you want to override; missing application settings use `.env.example`.
Use lowercase `true`/`false` for switches. Example overrides:

```dotenv
FRONTEND_PORT=5180
SIMULATION_SPEED=5
ORDER_INTERVAL_SECONDS=10
```

Apply changes by rerunning `./start.sh` or `.\start.cmd`. A plain container restart
does not load changed environment values. Keep local `.env` files out of Git.
The tables below document every setting in the root `.env.example`; defaults
refer to the Docker demo, not standalone Python processes.

### Docker and service addresses

| Variable | Default | Description |
| --- | --- | --- |
| `COMPOSE_PROJECT_NAME` | `sfi-challenge` | Stack and named-volume namespace. Change it to run an independent instance. |
| `BIND_ADDRESS` | `127.0.0.1` | Host interface for published ports. `127.0.0.1` is local access; `0.0.0.0` listens on all host interfaces. |
| `FRONTEND_PORT` | `5173` | Host port for the dashboard. |
| `BACKEND_PORT` | `8000` | Host port for the dispatcher API and `/docs`. |
| `SIMULATOR_PORT` | `8087` | Host port for the external load-board API. |
| `MODEL_PORT` | `9000` | Host port for the model API and `/docs`. |

### Model artifacts and history files

| Variable | Default | Description |
| --- | --- | --- |
| `MODEL_ARTIFACTS_DIR` | `./model/artifacts` | Host directory containing `models/` and `baselines/`; mounted read-only into model and backend containers. |
| `MODEL_BUNDLE_NAME` | `freight-rpm-v1` | Model directory under `MODEL_ARTIFACTS_DIR/models/`. |
| `MODEL_RANGE_NAME` | `historical-range-v1.json` | Historical pricing-range file under `MODEL_ARTIFACTS_DIR/baselines/`. |
| `MODEL_EXPECTED_VERSION` | `freight-rpm-v1` | Model version the prediction readiness check must return. |
| `BACKEND_HISTORY_DIR` | `./backend/data` | Host directory mounted read-only as `/history` for a custom CSV. |
| `HISTORY_CSV_PATH` | `/board-history/historical_shipments.csv` | Container CSV path. Default imports simulator history; use `/history/historical_shipments.csv` for your own file, or leave empty to disable import. |

### Simulator

| Variable | Default | Description |
| --- | --- | --- |
| `SIMULATION_SPEED` | `10` | Simulation clock multiplier; `1` is real time. |
| `ORDER_INTERVAL_SECONDS` | `5` | Wall-clock seconds between newly generated offers. |
| `ORDER_TTL_SIM_MINUTES` | `10` | Simulated minutes an open offer remains bookable. |
| `UNITS_PER_TERMINAL` | `8` | Number of fleet units seeded per terminal. |
| `HISTORY_ROWS` | `2500` | Number of historical records generated when no historical CSV exists. |
| `BID_WIN_PROBABILITY` | `0.45` | Simulated bid award probability, from `0` to `1`. |
| `BID_DECISION_SIM_MINUTES` | `3` | Simulated minutes before a submitted bid is decided. |
| `MAX_WEIGHT_LBS` | `44000` | Maximum allowed shipment weight in pounds, used by the simulator and dispatcher. |

Fleet/history seeding settings apply when new simulator data is created.
Restarting services preserves existing database and history volumes.

### Synchronization and logs

| Variable | Default | Description |
| --- | --- | --- |
| `BOARD_WEBSOCKET_ENABLED` | `true` | Enable live order ingestion over the board WebSocket. REST synchronization remains available when false. |
| `BOARD_SYNC_INTERVAL_SECONDS` | `30` | Wall-clock interval between REST reconciliation passes. |
| `SIMULATION_CLOCK_SYNC_INTERVAL_SECONDS` | `0.25` | Wall-clock interval between simulator clock refreshes. |
| `LOG_LIVE_ORDERS_VERBOSE` | `false` | Enable detailed live-order diagnostic logging. |

### Dispatch eligibility and economics

| Variable | Default | Description |
| --- | --- | --- |
| `MAX_PICKUP_MOVE_MILES` | `100` | Alternate pickup/deadhead distance limit in miles; `MAX_DEADHEAD_MILES` takes precedence when both are set. |
| `MAX_DEADHEAD_MILES` | `100` | Maximum allowed empty travel to pickup, in miles. Set this value to change the effective limit. |
| `MIN_EXPECTED_MARGIN_PCT` | `15` | Minimum expected gross margin percentage when margin checks are enabled. |
| `MIN_EXPECTED_MARGIN_USD` | `0` | Minimum expected gross profit in dollars when margin checks are enabled. |
| `ENFORCE_MARGIN` | `true` | Enforce the configured profitability thresholds during dispatch evaluation. |
| `MIN_PICKUP_LEAD_MINUTES` | `0` | Minimum simulated lead time before pickup. |
| `PICKUP_BUFFER_MINUTES` | `0` | Extra minutes reserved before pickup in timing and scheduling calculations. |
| `ASSUMED_TRAVEL_SPEED_MPH` | `45` | Travel speed used to estimate driving time, in miles per hour. |
| `MAX_FLEET_SNAPSHOT_AGE_SECONDS` | `120` | Maximum acceptable age of fleet availability data, in seconds. |
| `TURNAROUND_MINUTES` | `30` | Simulated turnaround time after delivery before a unit is available again. |

### Recommendation ranking

| Variable | Default | Description |
| --- | --- | --- |
| `RANK_EMPTY_MILES_WEIGHT` | `0.60` | Weight assigned to reducing empty travel. |
| `RANK_CONTINUITY_WEIGHT` | `0.25` | Weight assigned to route/assignment continuity. |
| `RANK_UTILIZATION_WEIGHT` | `0.15` | Weight assigned to fleet utilization. |
| `RANK_UTILIZATION_HORIZON_HOURS` | `24` | Utilization planning window in hours; accepts `1`–`168`. |
| `RANK_PROFIT_WEIGHT` | `0.40` | Weight assigned to the estimated hourly-profit score. |
| `RANK_PROFIT_TARGET_PER_HOUR` | `100` | Dollar-per-hour target used to scale the profit ranking score. |

Ranking weights are normalized; they do not have to sum to one. Each weight
is between `0` and `1`, and their total must be positive.

### Planning estimates and historical comparisons

| Variable | Default | Description |
| --- | --- | --- |
| `OPPORTUNITY_COST_ENABLED` | `true` | Include estimated opportunity cost in planning views. |
| `OPPORTUNITY_COST_PER_HOUR` | `25` | Dollar-per-hour rate used for opportunity-cost estimates. |
| `POSITIONING_VALUE_ENABLED` | `true` | Include estimated value of a unit’s destination position. |
| `POSITIONING_CREDIT_FRACTION` | `0.25` | Fraction of the estimated positioning benefit credited to a plan; `0`–`1`. |
| `POSITIONING_MAX_CREDIT` | `500` | Maximum positioning credit in dollars. |
| `HISTORICAL_MIN_SAMPLES` | `5` | Minimum comparable historical records required for historical estimates. |
| `HISTORICAL_LOOKBACK_DAYS` | `365` | Historical comparison window in days. |
| `HISTORICAL_ORIGIN_RADIUS_MILES` | `100` | Origin radius used when finding comparable historical shipments. |

Opportunity and positioning values are planning estimates; they do not replace
the cash-margin checks required for booking.

### Pricing advice and fallback

| Variable | Default | Description |
| --- | --- | --- |
| `MODEL_API_TIMEOUT_SECONDS` | `10` | Timeout for model price-analysis requests; greater than `0`, at most `120` seconds. |
| `MODEL_MAX_REFERENCE_DEVIATION_PCT` | `25` | Percentage deviation that triggers a warning when comparing a manual bid with pricing references. |
| `SFI_PRICING_FALLBACK_MODE` | `baseline` | `baseline` permits verified baseline advice when model pricing is unavailable; `review` returns unavailable advice for review. |
| `SFI_PRICING_UNSEEN_CATEGORY_ACTION` | `baseline` | For unsupported categories, allow `baseline` advice or require `review`. |
| `SFI_PRICING_MODEL_BLOCKED` | `false` | `true` blocks neural-model serving; the configured fallback policy then applies. |

### Autopilot and authentication

| Variable | Default | Description |
| --- | --- | --- |
| `AUTOPILOT_LIVE_ENABLED` | `true` | Allow the backend to execute explicitly started live autopilot runs. |
| `AUTOPILOT_KILL_SWITCH` | `false` | `true` blocks backend live autopilot execution. |
| `SFI_AUTOPILOT_LIVE_ENABLED` | `true` | Enable authenticated live decision endpoints in the model service. |
| `SFI_AUTOPILOT_KILL_SWITCH` | `false` | `true` blocks model live autopilot decisions. |
| `MODEL_AUTOPILOT_LIVE_TOKEN` | Empty (automatic) | Backend service token. Leave empty for automatic Docker provisioning; custom tokens must have at least 32 ASCII characters without whitespace. |
| `SFI_AUTOPILOT_LIVE_TOKEN` | Empty (automatic) | Model service token. Leave empty for automatic provisioning; when setting both tokens manually, their values must match. |
| `SFI_AUTOPILOT_ORDER_TYPES` | `open_bid,fixed_rate` | Comma-separated enabled order types: `open_bid`, `fixed_rate`, or both. |
| `SFI_AUTOPILOT_CLOCK_MODE` | `simulation` | `simulation` requires simulation clock metadata; `wall` expects no simulation clock; `either` accepts either contract. |

Autopilot starts only when you click **Run** or call its start API. Both enable
flags must be true and both kill switches false. Normal profitability, freshness,
and capacity checks still apply. Docker generates one shared token when the token
fields are empty, stores it in the `service-auth` volume, and reuses it on restart.
Tokens stay in the Python services and must not be placed in frontend variables.

### Advanced Docker overrides

These optional Compose variables are not required in `.env.example`:

| Variable | Default | Description |
| --- | --- | --- |
| `SFI_ENV_FILE` | `.env` | Optional application override file. For `.env.custom`, put `SFI_ENV_FILE=.env.custom` inside it and use `docker compose --env-file .env.custom up --build -d --wait --wait-timeout 240`. |
| `SFI_PYTHON_IMAGE` | `sfi-challenge-python:local` | Shared backend/model/migration image tag. |
| `SFI_SIMULATOR_IMAGE` | `sfi-challenge-simulator:local` | Simulator image tag. |
| `SFI_FRONTEND_IMAGE` | `sfi-challenge-frontend:local` | Frontend image tag. |

Host paths are relative to the project root unless absolute. Changing host ports
does not change internal service URLs. Compose sets the database paths, model
monitoring path, token-file path, and service URLs explicitly; changing those
requires a Compose override rather than only an `.env` entry. A different
`COMPOSE_PROJECT_NAME` uses separate volumes; existing data is not copied.

See [DOCKER.md](DOCKER.md) for direct Compose commands and data management.
