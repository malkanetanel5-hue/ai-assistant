# Run from the repo root: .\start-frontend.ps1
Set-Location frontend

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing npm dependencies..."
    npm install
}

Write-Host "Starting Electron + Vite dev server..."
$env:NODE_ENV = "development"
npm run dev
