# Ejecuta pytest con coverage. Falla si gate < 70%.
param([switch]$Open, [switch]$IncludeSlow)

$ErrorActionPreference = "Stop"

if ($IncludeSlow) {
    $markFilter = "not gpu"
} else {
    $markFilter = "not slow and not examples and not gpu and not fastsap"
}

python -m pytest `
    --cov `
    --cov-report=term-missing `
    --cov-report=html `
    --cov-report=xml `
    -q `
    -m "$markFilter"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Coverage gate o tests fallaron" -ForegroundColor Red
    exit 1
}
Write-Host "Coverage OK (gate >=70%)" -ForegroundColor Green
if ($Open) { Start-Process "htmlcov/index.html" }
