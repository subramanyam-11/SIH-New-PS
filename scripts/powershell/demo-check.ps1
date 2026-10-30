# SIH26262 Demo Check (Windows PowerShell)
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  SIH26262: Executing Demo Check Rehearsal (Windows PowerShell)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$env:PYTHONPATH = "backend"
if (Test-Path "backend\.venv\Scripts\python.exe") {
    & "backend\.venv\Scripts\python.exe" "backend\scripts\demo_check.py"
} else {
    python "backend\scripts\demo_check.py"
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "Demo Check failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}
