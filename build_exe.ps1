param(
    [string]$Version = "2.1.0",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SpecFile = Join-Path $ProjectRoot "pos_system.spec"
$DistDir = Join-Path $ProjectRoot "dist"
$BuildDir = Join-Path $ProjectRoot "build"
$DistAppDir = Join-Path $DistDir "pos_system"
$ExePath = Join-Path $DistAppDir "pos_system.exe"
$DatabasePath = Join-Path $ProjectRoot "pos_database.db"
$DistDatabasePath = Join-Path $DistAppDir "pos_database.db"
$BackupDir = Join-Path $ProjectRoot "backups"
$ReleaseRoot = Join-Path $ProjectRoot "release"
$ReleaseDir = Join-Path $ReleaseRoot "AnnaBeauty_POS_v$Version"
$ReleaseExePath = Join-Path $ReleaseDir "AnnaBeauty_POS.exe"
$ReleaseReadmePath = Join-Path $ReleaseDir "README.txt"

Set-Location $ProjectRoot

Write-Host "== AnnaBeauty POS EXE build ==" -ForegroundColor Cyan
Write-Host "Project: $ProjectRoot"
Write-Host "Version: $Version"
Write-Host "Build type: onedir"

if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw "Version must use X.Y.Z format, for example: .\build_exe.ps1 -Version 2.1.0"
}

if (-not (Test-Path $SpecFile)) {
    throw "Missing PyInstaller spec file: $SpecFile"
}

if (-not (Test-Path (Join-Path $ProjectRoot "pos_system.py"))) {
    throw "Missing pos_system.py in project folder."
}

$DependencyCheck = @'
import importlib.util
import sys
modules = ['PyInstaller', 'fpdf', 'openpyxl', 'win32print', 'win32ui']
missing = [name for name in modules if importlib.util.find_spec(name) is None]
if missing:
    print(', '.join(missing))
    sys.exit(1)
'@
$MissingDependencies = python -c $DependencyCheck
if ($LASTEXITCODE -ne 0) {
    throw "Missing build dependencies: $MissingDependencies. Install with: python -m pip install -r requirements.txt"
}

if ($Clean) {
    Write-Host "Cleaning old build output..." -ForegroundColor Yellow
    if (Test-Path $BuildDir) {
        Remove-Item -LiteralPath $BuildDir -Recurse -Force
    }
    if (Test-Path $DistDir) {
        Remove-Item -LiteralPath $DistDir -Recurse -Force
    }
}

if (Test-Path $DatabasePath) {
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupPath = Join-Path $BackupDir "pos_database_$timestamp.db"
    Copy-Item -LiteralPath $DatabasePath -Destination $backupPath -Force
    Write-Host "Database backup before build: $backupPath" -ForegroundColor Green
}
else {
    Write-Host "pos_database.db not found, skipping pre-build backup." -ForegroundColor Yellow
}

Write-Host "Running PyInstaller..." -ForegroundColor Cyan
python -m PyInstaller --noconfirm $SpecFile
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

if (-not (Test-Path $ExePath)) {
    throw "Build finished but exe was not found: $ExePath"
}

if (Test-Path $DatabasePath) {
    Copy-Item -LiteralPath $DatabasePath -Destination $DistDatabasePath -Force
    Write-Host "Copied database: $DistDatabasePath"
}
else {
    Write-Host "No starter database copied. App will create a new database next to exe if needed." -ForegroundColor Yellow
}

foreach ($dirname in @("reports", "exports", "receipts", "backups", "logs")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $DistAppDir $dirname) | Out-Null
}

Write-Host "Creating release folder..." -ForegroundColor Cyan
if (Test-Path $ReleaseDir) {
    Remove-Item -LiteralPath $ReleaseDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

Copy-Item -Path (Join-Path $DistAppDir "*") -Destination $ReleaseDir -Recurse -Force
$releaseOriginalExe = Join-Path $ReleaseDir "pos_system.exe"
if (Test-Path $releaseOriginalExe) {
    Move-Item -LiteralPath $releaseOriginalExe -Destination $ReleaseExePath -Force
}

if (Test-Path $DistDatabasePath) {
    Copy-Item -LiteralPath $DistDatabasePath -Destination (Join-Path $ReleaseDir "pos_database.db") -Force
}
elseif (Test-Path $DatabasePath) {
    Copy-Item -LiteralPath $DatabasePath -Destination (Join-Path $ReleaseDir "pos_database.db") -Force
}

if (Test-Path (Join-Path $ProjectRoot "icon.ico")) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "icon.ico") -Destination (Join-Path $ReleaseDir "icon.ico") -Force
}

foreach ($dirname in @("reports", "exports", "receipts", "backups", "logs")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $ReleaseDir $dirname) | Out-Null
}

$readme = @"
AnnaBeauty POS v$Version
Build type: onedir

1. How to run
- Open AnnaBeauty_POS.exe from this folder.
- Keep the whole release folder together. Do not copy only the exe file.
- Runtime files stay ready in this folder, so startup is faster.

2. Data
- Main database file: pos_database.db next to AnnaBeauty_POS.exe.
- The app does not use current working directory to find the database.
- If pos_database.db does not exist, the app only creates/copies it in the exe folder.

3. Data folders
- reports/: PDF reports
- exports/: CSV/Excel exports
- receipts/: receipts
- backups/: database backups
- logs/: application logs

4. Build dependencies
- Install with: python -m pip install -r requirements.txt
- Includes: PyInstaller, fpdf2, openpyxl, pywin32

5. Quick exe test
- Open the app and check Sales, Management, and Reports tabs.
- Test database backup, PDF export, and CSV export.
- If openpyxl was installed during build, test Excel export.
- Check logs/app.log if there is an error.
"@
Set-Content -LiteralPath $ReleaseReadmePath -Value $readme -Encoding UTF8

Write-Host ""
Write-Host "Build succeeded:" -ForegroundColor Green
Write-Host $ExePath
Write-Host "Release folder:" -ForegroundColor Green
Write-Host $ReleaseDir
Write-Host ""
Write-Host "Run the app from the release folder so database/reports/exports/receipts/backups/logs stay next to exe."
