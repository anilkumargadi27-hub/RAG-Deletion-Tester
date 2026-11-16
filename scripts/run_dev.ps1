# PowerShell Startup Script for ForgetCheck (Windows)
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " ForgetCheck — RAG Deletion & Access-Revocation Tester   " -ForegroundColor Cyan
Write-Host " Tagline: Check what your AI can still reveal after access changes." -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Activate virtual environment
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "[1/4] Activating Python virtual environment (.venv)..." -ForegroundColor Green
    & .venv\Scripts\Activate.ps1
} else {
    Write-Host "Error: .venv not found. Run python -m venv .venv and install requirements." -ForegroundColor Red
    exit 1
}

# 2. Seed database
Write-Host "[2/4] Initializing and seeding demo data..." -ForegroundColor Green
$env:PYTHONPATH = "."
python scripts/seed_demo.py

# 3. Build frontend if needed
if (-not (Test-Path "frontend\dist\index.html")) {
    Write-Host "[3/4] Building production frontend assets..." -ForegroundColor Green
    Push-Location frontend
    npm run build
    Pop-Location
} else {
    Write-Host "[3/4] Production frontend build verified." -ForegroundColor Green
}

# 4. Start FastAPI server (serves API and React frontend on port 8000)
$port = if ($env:PORT) { $env:PORT } else { "8000" }
Write-Host "[4/4] Starting ForgetCheck server on http://localhost:$port..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Local URLs:" -ForegroundColor Yellow
Write-Host " - Web Application: http://localhost:$port" -ForegroundColor Green
Write-Host " - Health Check:    http://localhost:$port/health" -ForegroundColor Green
Write-Host " - API Specs:       http://localhost:$port/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Initial Demo Accounts:" -ForegroundColor Yellow
Write-Host " - Admin:   admin   / Admin@ForgetCheck2026!" -ForegroundColor White
Write-Host " - Auditor: auditor / Auditor@ForgetCheck2026!" -ForegroundColor White
Write-Host " - Member:  member  / Member@ForgetCheck2026!" -ForegroundColor White
Write-Host ""

uvicorn backend.app.main:app --host 127.0.0.1 --port $port
