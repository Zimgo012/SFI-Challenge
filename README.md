# SFI Challenge

## Easiest setup on another machine

Install and start Docker with Compose v2.24+, then switch to the shipping branch:

```sh
git checkout feature/ship
./start.sh
```

On Windows, run `.\start.cmd` instead. Defaults are included; no `.env` editing
is needed. Open **http://localhost:5173/dashboard**. The first build takes several minutes.

## About

A freight dispatch system that receives simulated loads, tracks fleet availability,
evaluates bids and bookings, and displays live operations. A separate pricing
model API provides bid advice; the backend handles actual bookings.

```text
sfi_challenge/  Simulated load-board API, orders, terminals, and fleet
backend/        Dispatcher API, business rules, and database
model/          Pricing model API and ML pipeline
frontend/       React dashboard
```

## Run services individually in this checkout

Requires **Python 3.13**, **uv**, and **Node.js 22.12+ / npm**.
Open four terminals at the repository root and run the blocks below in order.
The simulator commands use macOS/Linux paths; on Windows, use `python` and
`.venv\Scripts\python.exe` in place of `python3.13` and `.venv/bin/python`.

First configure `backend/.env` as shown in the [backend guide](backend/README.md).
This checkout's backend dependency requires `project-model/model/` to exist.
For pricing, restore the trained bundle and historical-range artifact into
`model/artifacts/` as described in the [model guide](model/README.md).

### 1. Simulator API

```sh
cd sfi_challenge
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8087
```

Wait for **http://127.0.0.1:8087/health** before starting the backend.

### 2. Backend

```sh
cd backend
uv sync --locked --python 3.13
uv run --locked alembic upgrade head
uv run --locked uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

API docs: **http://127.0.0.1:8000/docs**. Migrations preserve existing data.

### 3. Model API

```sh
cd model
uv sync --locked --extra api --python 3.13
uv run --locked --extra api uvicorn sfi_model.api.app:app --host 127.0.0.1 --port 9000 --workers 1
```

API docs: **http://127.0.0.1:9000/docs**. The backend uses
`MODEL_API_URL=http://127.0.0.1:9000`; start this service before requesting pricing.

### 4. Frontend

```sh
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open **http://127.0.0.1:5173/dashboard**. Local API proxy defaults work as-is.

Stop each service with `Ctrl+C`, starting with the frontend, then backend,
model, and simulator. Starting services does not start an autopilot run.

More details and development commands: [simulator](sfi_challenge/README.md),
[backend](backend/README.md), [model](model/README.md), [frontend](frontend/README.md).
