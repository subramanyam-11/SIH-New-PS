# SIH26262 Safe Packaging Script for Windows PowerShell
$ErrorActionPreference = "Stop"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "             SIH26262 SAFE GIT-BASED RELEASE PACKAGING               " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$TargetTag = "HEAD"
if ($args.Count -gt 0) {
    $TargetTag = $args[0]
}

$OutputFile = "sih26262_release.zip"

Write-Host "Creating clean release archive via git archive ($TargetTag)..." -ForegroundColor Yellow
git archive --format=zip --output=$OutputFile $TargetTag
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to create git archive." -ForegroundColor Red
    exit $LASTEXITCODE
}

$VenvPython = "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    $VenvPython = "python"
}

Write-Host "Verifying package integrity..." -ForegroundColor Yellow
& $VenvPython scripts\verify_package.py $OutputFile
if ($LASTEXITCODE -ne 0) {
    Write-Host "Package verification failed." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n✓ Safe release package created: $OutputFile" -ForegroundColor Green
