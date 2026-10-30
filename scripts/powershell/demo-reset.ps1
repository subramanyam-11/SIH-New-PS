# SIH26262 Demo Reset (Windows PowerShell)
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  SIH26262: Executing Demo Reset (Windows PowerShell)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$env:PYTHONPATH = "backend"
if (Test-Path "backend\.venv\Scripts\python.exe") {
    & "backend\.venv\Scripts\python.exe" "backend\scripts\demo_reset.py"
} else {
    python "backend\scripts\demo_reset.py"
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "Demo Reset failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}
