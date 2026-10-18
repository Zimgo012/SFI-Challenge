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

Open **http://localhost:5173/dashboard**. Defaults work without configuration.
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
