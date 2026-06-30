# demo.ps1
# PowerShell script to orchestrate the Qolyx Phase 11 Demo on Windows.

$oldEAP = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== QOLYX DEMO - Starting ===" -ForegroundColor Cyan

# 1. Check if Docker is running, and start it if not
$dockerRunning = $false
& docker info >$null 2>&1
if ($LASTEXITCODE -eq 0) {
    $dockerRunning = $true
}

if (-not $dockerRunning) {
    Write-Host "[*] Docker is not running. Attempting to start Docker Desktop..." -ForegroundColor Yellow
    if (Test-Path "C:\Program Files\Docker\Docker\Docker Desktop.exe") {
        Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        Write-Host "[...] Launching Docker Desktop. Waiting for daemon to start (this may take up to 90s)..." -ForegroundColor Yellow
        $dockerTimeout = 90
        $dockerElapsed = 0
        while ($dockerElapsed -lt $dockerTimeout) {
            Start-Sleep -Seconds 5
            $dockerElapsed += 5
            & docker info >$null 2>&1
            if ($LASTEXITCODE -eq 0) {
                $dockerRunning = $true
                break
            }
        }
    }
}

$ErrorActionPreference = "Stop"

if (-not $dockerRunning) {
    Write-Error "ERROR: Docker daemon is not running. Please ensure Docker Desktop is started and ready."
    Exit 1
} else {
    Write-Host "[SUCCESS] Docker is running and ready!" -ForegroundColor Green
}

# 2. Start services and force build
Write-Host "[*] Starting services in the background (building if needed)..." -ForegroundColor Yellow
docker compose --env-file .env -f infra/compose.yaml up -d --build

# 3. Wait for services to be healthy
Write-Host "[...] Waiting for Qolyx Backend to become healthy..." -ForegroundColor Yellow
$timeout = 120
$elapsed = 0
$healthy = $false
while ($elapsed -lt $timeout) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method Get
        if ($response -ne $null) {
            $healthy = $true
            break
        }
    } catch {
        # Backend not ready yet
    }
    Start-Sleep -Seconds 2
    $elapsed += 2
}

if ($healthy) {
    Write-Host "[SUCCESS] Backend is healthy!" -ForegroundColor Green
} else {
    Write-Warning "[WARNING] Backend did not report healthy in 120 seconds. Proceeding anyway..."
}

# 4. Run the demo setup inside the backend container
Write-Host "[*] Running demo setup (seeding data, running dbt, calculating scores, executing scenarios)..." -ForegroundColor Yellow
docker compose -f infra/compose.yaml exec qolyx-backend python -m demo.demo_runner

# 5. Pause Airflow DAGs to prevent periodic execution interference
Write-Host "[*] Pausing Airflow DAGs..." -ForegroundColor Yellow
try {
    docker compose -f infra/compose.yaml exec qolyx-airflow airflow dags pause qolyx_finnhub_ingestion
    docker compose -f infra/compose.yaml exec qolyx-airflow airflow dags pause qolyx_fda_ingestion
    docker compose -f infra/compose.yaml exec qolyx-airflow airflow dags pause qolyx_github_ingestion
} catch {
    Write-Warning "[WARNING] Failed to pause some Airflow DAGs. Continuing..."
}

# 6. Open dashboard in the default browser
Write-Host "[*] Opening browser to Qolyx Dashboard..." -ForegroundColor Yellow
Start-Process "http://localhost:5173"

# 7. Display the demo summary
Write-Host "[*] Displaying Qolyx Demo Summary:" -ForegroundColor Yellow
docker compose -f infra/compose.yaml exec qolyx-backend python -m demo.demo_summary

Write-Host "[SUCCESS] DEMO COMPLETE!" -ForegroundColor Green
