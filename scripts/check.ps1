$ErrorActionPreference = "Stop"

Write-Host "Backend: lint + tests"
Set-Location F:\FeeDesk\apps\api
& F:\FeeDesk\.venv\Scripts\ruff.exe check app tests
& F:\FeeDesk\.venv\Scripts\python.exe -m pytest -q

Write-Host "Frontend: typecheck + build"
Set-Location F:\FeeDesk\apps\web
npm run typecheck
$env:NODE_OPTIONS = "--max-old-space-size=1024"
npm run build
