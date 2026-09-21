# install_skills_on_other_pc.ps1 - PowerShell installer for Antigravity Global Skills
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "       Google Antigravity - Global Skills Sync Setup for All PCs" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

$SourceDir = $PSScriptRoot
$ConfigDir = Join-Path $HOME ".gemini\config"
$TargetDir = Join-Path $ConfigDir "skills"

Write-Host "[1/4] Skills Source (Cloud): $SourceDir"
Write-Host "      Antigravity Target:    $TargetDir"
Write-Host ""

# Ensure config directory exists
if (-not (Test-Path $ConfigDir)) {
    Write-Host "[2/4] Creating Antigravity config directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null
} else {
    Write-Host "[2/4] Antigravity config directory exists." -ForegroundColor Green
}

# Handle existing target
if (Test-Path $TargetDir) {
    $item = Get-Item -LiteralPath $TargetDir -Force
    if ($item.Attributes -match "ReparsePoint") {
        Write-Host "[3/4] Refreshing existing junction..." -ForegroundColor Yellow
        cmd /c rmdir "$TargetDir"
    } else {
        $backupDir = Join-Path $ConfigDir ("skills_backup_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
        Write-Host "[3/4] Backing up existing local skills to: $backupDir" -ForegroundColor Yellow
        Move-Item -Path $TargetDir -Destination $backupDir -Force
    }
}

# Create Directory Junction
Write-Host "[3/4] Creating Directory Junction to Google Drive skills..." -ForegroundColor Cyan
cmd /c mklink /J "$TargetDir" "$SourceDir"

if ($LASTEXITCODE -eq 0) {
    Write-Host "      Directory junction established successfully!" -ForegroundColor Green
} else {
    Write-Host "      [ERROR] Could not create junction. Please check permissions." -ForegroundColor Red
}

# Dependencies check
Write-Host ""
Write-Host "[4/4] Checking dependencies..." -ForegroundColor Cyan
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    Write-Host "      Python found: $($python.Source)" -ForegroundColor Green
    python -c "import mutagen" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "      Installing 'mutagen' for audio metadata tagging..." -ForegroundColor Yellow
        python -m pip install mutagen
    } else {
        Write-Host "      Mutagen library is ready." -ForegroundColor Green
    }
    python -c "import PIL" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "      Installing 'Pillow' for cinematic slideshow image processing..." -ForegroundColor Yellow
        python -m pip install Pillow
    } else {
        Write-Host "      Pillow library is ready." -ForegroundColor Green
    }
} else {
    Write-Host "      [WARNING] Python not found. Please install Python 3.10+ from python.org or via winget install Python.Python.3.12" -ForegroundColor Yellow
}

$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ffmpeg) {
    Write-Host "      FFmpeg found: $($ffmpeg.Source)" -ForegroundColor Green
} else {
    Write-Host "      Notice: FFmpeg is not in PATH. Ensure FFmpeg is installed if you use FLAC splitting or transcoding." -ForegroundColor Gray
}

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host " [SUCCESS] Global Skills are now active on this PC!" -ForegroundColor Green
Write-Host "==============================================================================" -ForegroundColor Green
Write-Host ""
