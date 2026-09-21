@echo off
setlocal enabledelayedexpansion
title Google Antigravity - Global Skills Installer

echo ==============================================================================
echo        Google Antigravity - Global Skills Sync Setup for All PCs
echo ==============================================================================
echo.

:: 1. Detect directories
set "SOURCE_DIR=%~dp0"
if "%SOURCE_DIR:~-1%"=="\" set "SOURCE_DIR=%SOURCE_DIR:~0,-1%"
set "TARGET_DIR=%USERPROFILE%\.gemini\config\skills"
set "CONFIG_DIR=%USERPROFILE%\.gemini\config"

echo [1/4] Skills Source (Cloud): "!SOURCE_DIR!"
echo       Antigravity Target:    "!TARGET_DIR!"
echo.

:: 2. Ensure parent config directory exists
if not exist "!CONFIG_DIR!" (
    echo [2/4] Creating Antigravity config directory: "!CONFIG_DIR!"
    mkdir "!CONFIG_DIR!" >nul 2>&1
) else (
    echo [2/4] Antigravity config directory found.
)

:: 3. Handle existing target directory / junction
if exist "!TARGET_DIR!" (
    fsutil reparsepoint query "!TARGET_DIR!" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [3/4] Notice: Existing junction detected at target. Refreshing link...
        rmdir "!TARGET_DIR!" >nul 2>&1
    ) else (
        echo [3/4] Backing up existing local skills directory...
        set "BACKUP_DIR=%USERPROFILE%\.gemini\config\skills_backup_%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%"
        set "BACKUP_DIR=!BACKUP_DIR: =0!"
        move "!TARGET_DIR!" "!BACKUP_DIR!" >nul 2>&1
        echo       Local backup saved to: "!BACKUP_DIR!"
    )
)

:: 4. Create Directory Junction
echo [3/4] Linking global skills from OneDrive to Antigravity...
mklink /J "!TARGET_DIR!" "!SOURCE_DIR!"
if !errorlevel! neq 0 (
    echo [ERROR] Failed to create directory junction.
    echo Please make sure you have standard user permissions and try again.
    pause
    exit /b 1
)
echo       Junction created successfully!
echo.

:: 5. Check Python & Audio Dependencies
echo [4/4] Checking environment dependencies...
where python >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo       Found: %%v
    python -c "import mutagen" >nul 2>&1
    if !errorlevel! neq 0 (
        echo       Notice: 'mutagen' library not found. Installing mutagen for music metadata...
        python -m pip install mutagen
    ) else (
        echo       Found: mutagen library installed.
    )
) else (
    echo       [WARNING] Python was not found in PATH. Please install Python 3.10+ to run skill scripts.
)

where ffmpeg >nul 2>&1
if !errorlevel! equ 0 (
    echo       Found: FFmpeg executable available in PATH.
) else (
    echo       Notice: FFmpeg not in PATH. Ensure FFmpeg is installed if you use FLAC splitting/conversion.
)

echo.
echo ==============================================================================
echo [SUCCESS] Global Skills are now active on this PC!
echo.
echo Available Skills:
echo   - CleanResidue            (Purge non-audio residue, keep MP3/M4A/FLAC)
echo   - FLACMove_Convert        (Sync FLAC to NAS, transcode to MP3 128k/190k VBR)
echo   - Music_Curator           (Download/embed album covers, auto-classify genres)
echo   - music-cue-flac-splitter (Losslessly split unsplit FLAC/APE/WAV from CUE)
echo   - music-folder-renamer    (Standardize album folder names)
echo   - music-track-renamer     (Standardize audio track filenames)
echo ==============================================================================
echo.
echo Any changes or new skills added on any PC will now automatically sync here!
echo.
pause
