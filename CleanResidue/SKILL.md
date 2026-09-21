---
name: CleanResidue
description: >-
  Recursively scans music directories, cleans non-audio residue files (artwork, logs, cue sheets,
  videos, text, and non-target files), preserves designated audio formats (default: mp3, m4a, flac),
  and prunes empty directories. Supports preview dry-runs, configurable format preservation,
  and disk space reclamation reporting. Use whenever the user requests to clean residue,
  purge non-music files, or keep only specific audio formats in a music library or folder.
---

# CleanResidue Skill

Autonomous utility and workflow to clean non-audio residue files from music directories while preserving specified audio formats (defaults to `.mp3`, `.m4a`, and `.flac`), with automatic pruning of empty directories and detailed disk space reclamation reporting.

## Capabilities & Features

- **Safe Audio Format Retention**: Keeps only designated audio extensions (defaults to `.mp3`, `.m4a`, `.flac`).
- **Configurable Extension Whitelist**: Easily add or change preserved formats (e.g. `--keep mp3,m4a,flac,wav,aac`).
- **Residue Purging**: Eliminates album art (`.jpg`, `.png`, `.tif`), cue sheets (`.cue`), rip logs (`.log`, `.accurip`), scene info (`.nfo`), text files (`.txt`, `.url`), videos (`.mp4`, `.vob`), and system files (`desktop.ini`, `Thumbs.db`).
- **Empty Directory Pruning**: Automatically traverses subdirectories bottom-up to prune folders left empty after residue removal (e.g. `Scans/`, `Artwork/`, `Covers/`, `Subs/`).
- **Safe Read-Only Attribute Handling**: Clears Windows read-only/system file attributes to ensure smooth deletion without permissions errors.
- **Dry-Run Preview**: Accurately counts files, calculates disk space that would be reclaimed, and previews operations without deleting any data.
- **Detailed Execution Reporting**: Outputs clean breakdowns of kept vs. deleted files by extension, reclaimed storage, and operation duration.

## CLI Usage & Commands

The tool is implemented in pure Python (standard library only) and located at [clean_residue.py](./scripts/clean_residue.py).

### 1. Dry-Run Preview (Recommended Before Deleting)
Scan target directory, simulate deletion, and display storage reclamation without touching files:
```powershell
python "$HOME/.gemini/config/skills/CleanResidue/scripts/clean_residue.py" --dry-run "<TARGET_DIRECTORY>"
```
*(Or in Command Prompt: `python "%USERPROFILE%\.gemini\config\skills\CleanResidue\scripts\clean_residue.py" --dry-run "<TARGET_DIRECTORY>"`)*

### 2. Execute Cleanup (Default: Keeps mp3, m4a, flac & prunes empty folders)
```powershell
python "$HOME/.gemini/config/skills/CleanResidue/scripts/clean_residue.py" "<TARGET_DIRECTORY>"
```

### 3. Custom Audio Formats to Preserve
Specify which formats to keep (comma-separated):
```powershell
python "$HOME/.gemini/config/skills/CleanResidue/scripts/clean_residue.py" --keep mp3,flac,m4a,wav,ogg "<TARGET_DIRECTORY>"
```

### 4. Retain Empty Directories (Do Not Prune)
If you want to remove residue files but keep empty folders:
```powershell
python "$HOME/.gemini/config/skills/CleanResidue/scripts/clean_residue.py" --no-prune "<TARGET_DIRECTORY>"
```

### 5. Verbose Logging
Show every deleted file and pruned directory during execution:
```powershell
python "$HOME/.gemini/config/skills/CleanResidue/scripts/clean_residue.py" -v "<TARGET_DIRECTORY>"
```
