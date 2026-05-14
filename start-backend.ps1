# Run from the repo root: .\start-backend.ps1
Set-Location backend

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

Write-Host "Activating virtual environment..."
.\.venv\Scripts\Activate.ps1

Write-Host "Installing dependencies..."
pip install -r requirements.txt

Write-Host "Installing Playwright browser (Chromium)..."
playwright install chromium

if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host ""
    Write-Host "⚠  Created backend/.env from example — fill in your API keys before continuing!"
    Write-Host ""
}

Write-Host "Starting FastAPI backend on http://localhost:8000 ..."
uvicorn main:app --reload --port 8000
