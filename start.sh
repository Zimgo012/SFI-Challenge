#!/usr/bin/env bash
# Launch from any working directory; Docker Compose owns configuration and data.
set -euo pipefail
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

fail() { printf 'Error: %s\n' "$*" >&2; exit 1; }
compose() { docker compose --project-directory "$PROJECT_DIR" -f "$PROJECT_DIR/compose.yaml" "$@"; }

action="${1:-start}"
if [[ "$#" -gt 1 ]]; then fail 'Usage: ./start.sh [start|stop|status|logs|help]'; fi
case "$action" in
    help|-h|--help)
        printf 'Usage: ./start.sh [start|stop|status|logs|help]\nDefault: build and start all services. No .env file is required.\n'
        exit 0 ;;
    start|stop|status|logs) ;;
    *) fail 'Usage: ./start.sh [start|stop|status|logs|help]' ;;
esac

command -v docker >/dev/null 2>&1 || fail 'Install Docker Desktop (or Docker Engine with Compose v2.24+) first.'
version="$(docker compose version --short 2>/dev/null)" || fail 'Docker Compose v2.24+ is required.'
version="${version#v}"
IFS=. read -r major minor rest <<< "$version"
[[ "$major" =~ ^[0-9]+$ && "$minor" =~ ^[0-9]+$ ]] || fail 'Cannot determine the Docker Compose version.'
if (( major < 2 || (major == 2 && minor < 24) )); then fail 'Update Docker Compose to v2.24 or newer.'; fi
docker info >/dev/null 2>&1 || fail 'Docker is not reachable. Start Docker Desktop or your Docker daemon, then retry.'

case "$action" in
    stop) compose down; exit $? ;;
    status) compose ps -a; exit $? ;;
    logs) compose logs -f --tail=100; exit $? ;;
esac

if [[ ! -f sfi_challenge/app/main.py || ! -f sfi_challenge/requirements.txt ]]; then
    command -v git >/dev/null 2>&1 || fail 'Git is required to download the simulator. Install Git, or use a copy containing sfi_challenge/.'
    printf 'Downloading the simulator submodule...\n'
    git submodule update --init --recursive -- sfi_challenge || fail 'Simulator download failed. Check your connection and use a Git clone of this project.'
    [[ -f sfi_challenge/app/main.py && -f sfi_challenge/requirements.txt ]] || fail 'Simulator files are missing. Clone this project with --recurse-submodules.'
fi

compose config --quiet || fail 'Invalid Compose configuration. Check any local .env overrides.'
printf 'Starting SFI Challenge with default settings (optional .env overrides apply).\nThe first build downloads large dependencies and can take several minutes.\n'
if compose up --build -d --wait --wait-timeout 240; then
    printf '\nSFI Challenge is ready:\n'
    for entry in 'frontend 5173 /dashboard Frontend' 'backend 8000 /docs Backend' 'model 9000 /docs Model' 'simulator 8087 /docs Simulator'; do
        read -r service port path label <<< "$entry"
        address="$(compose port "$service" "$port")"
        case "$address" in
            0.0.0.0:*|\[::\]:*) address="localhost:${address##*:}" ;;
        esac
        printf '  %s: http://%s%s\n' "$label" "$address" "$path"
    done
    printf '\nStop: ./start.sh stop\nLogs: ./start.sh logs\n'
else
    result=$?
    printf '\nStartup failed. Recent service logs follow:\n' >&2
    compose ps -a || true
    compose logs --tail=80 || true
    printf '\nFix the reported problem and rerun ./start.sh. Stop containers with ./start.sh stop.\n' >&2
    exit "$result"
fi
