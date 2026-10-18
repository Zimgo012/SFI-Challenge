param(
    [ValidateSet('start', 'stop', 'status', 'logs', 'help')]
    [string]$Action = 'start'
)

$ErrorActionPreference = 'Stop'

function Invoke-Compose {
    & docker compose --project-directory $PSScriptRoot -f (Join-Path $PSScriptRoot 'compose.yaml') @args
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed (exit $LASTEXITCODE)." }
}

if ($Action -eq 'help') {
    Write-Host 'Usage: .\start.cmd [start|stop|status|logs|help]'
    Write-Host 'Default: build and start all services. No .env file is required.'
    exit 0
}

Push-Location $PSScriptRoot
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Install Docker Desktop first, then start it and retry.'
    }
    $version = & docker compose version --short
    if ($LASTEXITCODE -ne 0 -or $version -notmatch '^v?(\d+)\.(\d+)') {
        throw 'Docker Compose v2.24 or newer is required.'
    }
    if ([int]$Matches[1] -lt 2 -or ([int]$Matches[1] -eq 2 -and [int]$Matches[2] -lt 24)) {
        throw 'Update Docker Compose to v2.24 or newer.'
    }
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) { throw 'Docker is not reachable. Start Docker Desktop or your Docker daemon, then retry.' }

    switch ($Action) {
        'stop' { Invoke-Compose down; exit 0 }
        'status' { Invoke-Compose ps -a; exit 0 }
        'logs' { Invoke-Compose logs -f --tail=100; exit 0 }
    }

    if (-not (Test-Path 'sfi_challenge/app/main.py') -or -not (Test-Path 'sfi_challenge/requirements.txt')) {
        if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
            throw 'Git is required to download the simulator. Install Git, or use a copy containing sfi_challenge/.'
        }
        Write-Host 'Downloading the simulator submodule...'
        & git submodule update --init --recursive -- sfi_challenge
        if ($LASTEXITCODE -ne 0) { throw 'Simulator download failed. Check your connection and use a Git clone of this project.' }
        if (-not (Test-Path 'sfi_challenge/app/main.py') -or -not (Test-Path 'sfi_challenge/requirements.txt')) {
            throw 'Simulator files are missing. Clone this project with --recurse-submodules.'
        }
    }

    Invoke-Compose config --quiet
    Write-Host 'Starting SFI Challenge with default settings (optional .env overrides apply).'
    Write-Host 'The first build downloads large dependencies and can take several minutes.'
    try {
        Invoke-Compose up --build -d --wait --wait-timeout 240
    } catch {
        Write-Host 'Startup failed. Recent service logs follow:'
        try { Invoke-Compose ps -a; Invoke-Compose logs --tail=80 } catch { Write-Host $_.Exception.Message }
        throw 'Fix the reported problem and rerun start.cmd. Stop containers with start.cmd stop.'
    }

    Write-Host "`nSFI Challenge is ready:"
    foreach ($service in @(
        @{ Name = 'frontend'; Port = '5173'; Path = '/dashboard' },
        @{ Name = 'backend'; Port = '8000'; Path = '/docs' },
        @{ Name = 'model'; Port = '9000'; Path = '/docs' },
        @{ Name = 'simulator'; Port = '8087'; Path = '/docs' }
    )) {
        $address = (Invoke-Compose port $service.Name $service.Port | Out-String).Trim()
        $address = $address -replace '^(0\.0\.0\.0|\[::\]):', 'localhost:'
        Write-Host ("  {0}: http://{1}{2}" -f $service.Name, $address, $service.Path)
    }
    Write-Host "`nStop: .\start.cmd stop`nLogs: .\start.cmd logs"
} catch {
    Write-Host ("Error: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}
