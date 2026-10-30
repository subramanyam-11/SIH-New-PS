# SIH26262 Comprehensive Final Release Check for Windows PowerShell
$ErrorActionPreference = "Stop"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "             SIH26262 COMPREHENSIVE FINAL RELEASE CHECK             " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$VenvPython = "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    $VenvPython = "python"
}

Write-Host "`n[Step 1/7] Running Pytest Test Suite (96 tests)..." -ForegroundColor Yellow
Push-Location backend
& $VenvPython -m pytest -v
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Write-Host "`n[Step 2/7] Scanning Codebase for Secrets..." -ForegroundColor Yellow
& $VenvPython backend\scripts\scan_secrets.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[Step 3/7] Performing Demo Reset (0h offset, seeds, rule eval)..." -ForegroundColor Yellow
& $VenvPython backend\scripts\demo_reset.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[Step 4/7] Executing 8-Step Demo Check Continuous Story..." -ForegroundColor Yellow
& $VenvPython backend\scripts\demo_check.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[Step 5/7] Executing 7-Point Cross-System Consistency Audit..." -ForegroundColor Yellow
& $VenvPython backend\scripts\check_consistency.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[Step 6/7] Verifying Cryptographic Audit Chain Integrity..." -ForegroundColor Yellow
$env:PYTHONPATH = "backend"
& $VenvPython backend\scripts\verify_audit_chain.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[Step 7/7] Validating Frontend Production Build..." -ForegroundColor Yellow
Push-Location frontend
npm run build
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Write-Host "`n======================================================================" -ForegroundColor Green
Write-Host "  ✓ ALL 7 FINAL CHECKS PASSED WITH ZERO ERRORS (RELEASE READY v1.0)  " -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
