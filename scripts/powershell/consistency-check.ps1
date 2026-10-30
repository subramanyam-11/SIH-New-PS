# SIH26262 Consistency Check (Windows PowerShell)
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  SIH26262: Executing Consistency Check (Windows PowerShell)" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$env:PYTHONPATH = "backend"
if (Test-Path "backend\.venv\Scripts\python.exe") {
    & "backend\.venv\Scripts\python.exe" "backend\scripts\check_consistency.py"
} else {
    python "backend\scripts\check_consistency.py"
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "Consistency Check failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}
