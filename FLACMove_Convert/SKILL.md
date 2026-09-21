---
name: FLACMove_Convert
description: >-
  Synchronizes FLAC album folders to a NAS or backup destination using multi-threaded Robocopy,
  converts MP3 files to VBR 128 kbps, converts FLAC files to MP3 VBR 190 kbps with metadata
  and cover art preservation, and safely deletes original FLAC files after verified conversion.
  Use whenever the user asks to sync or backup FLACs to a NAS, convert MP3/FLAC bitrates, downsample audio,
  or perform end-to-end music library format optimization.
---

# FLACMove_Convert Agent

Autonomous agent that orchestrates music library synchronization, audio transcoding, ID3 tag and cover art preservation, and safe storage optimization.

## Core Capabilities

1. **High-Performance FLAC Backup & Sync:**
   - Scans library for album folders containing `"- Flac"` (or customizable filter patterns).
   - Multi-threaded mirroring/copying via Windows `robocopy` (`/MT:16 /E /R:2 /W:5`).
   - Non-destructive synchronization: safely detects existing files and skips redundant transfers.

2. **MP3 Downsampling (VBR 128 kbps):**
   - Transcodes all `*.mp3` files to LAME VBR preset `-q:a 5` (~128–130 kbps).
   - Atomic replacement: writes to temporary files first, verifies integrity, and replaces originals in-place.
   - Preserves all ID3v2 tags and embedded album art (`-c:v copy`).

3. **FLAC Transcoding & Safe Deletion (VBR 190 kbps):**
   - Transcodes `*.flac` files to MP3 using LAME VBR preset `-q:a 2` (~190 kbps, standard V2 quality).
   - Preserves all Vorbis tags mapped into ID3v2.3 tags and embedded front cover images.
   - **Data Safety Rule:** Original `.flac` files are deleted **only after** verifying that the output `.mp3` was created with a non-zero size and FFmpeg returned exit code 0.

4. **Intelligent Folder Renaming:**
   - Automatically updates album folder suffixes from `"- Flac"` to `"- mp3"` once all FLAC files inside the folder have been converted to MP3.

5. **Dry-Run Mode (`--dry-run`):**
   - Preview all file operations, transfers, and renames before committing changes.

---

## Workflow Commands

The skill script is located at [flac_move_convert.py](./scripts/flac_move_convert.py).

### 1. Full Pipeline (`all`)
Runs the complete sequence: Sync FLACs to NAS -> Convert MP3s to 128k -> Convert FLACs to 190k & delete original FLACs -> Rename folder suffixes.
```powershell
python "$HOME/.gemini/config/skills/FLACMove_Convert/scripts/flac_move_convert.py" all "<SOURCE_FOLDER>" "<DEST_NAS_FOLDER>"
```
*Optional flags:*
- `--dry-run`: Preview without modifying files.
- `--workers 8`: Adjust conversion concurrency (default: 8).
- `--keep-flac`: Convert FLACs without deleting the originals.
- `--no-rename`: Skip renaming folder suffixes.

### 2. Sync FLAC Folders to Destination (`sync-flac`)
Backs up all matching FLAC album folders to a target location (NAS, external drive, or secondary collection).
```powershell
python "$HOME/.gemini/config/skills/FLACMove_Convert/scripts/flac_move_convert.py" sync-flac "<SOURCE_FOLDER>" "<DEST_NAS_FOLDER>"
```
*Optional flags:*
- `--filter "*- Flac*"`: Change matching pattern (default: `*- Flac*`).
- `--threads 16`: Number of robocopy threads (default: 16).
- `--dry-run`: Preview matching folders without copying.

### 3. Convert MP3s to VBR 128 kbps (`convert-mp3`)
Scans a directory recursively and converts all existing MP3 files to VBR 128 kbps.
```powershell
python "$HOME/.gemini/config/skills/FLACMove_Convert/scripts/flac_move_convert.py" convert-mp3 "<SOURCE_FOLDER>"
```
*Optional flags:*
- `--quality 5`: LAME VBR quality preset (default: 5 = ~128–130 kbps).
- `--workers 8`: Parallel worker threads (default: 8).
- `--dry-run`: Preview files that will be converted.

### 4. Convert FLACs to MP3 VBR 190 kbps & Delete Originals (`convert-flac`)
Scans for FLAC files, converts to MP3 VBR 190 kbps, and deletes the FLAC once verified.
```powershell
python "$HOME/.gemini/config/skills/FLACMove_Convert/scripts/flac_move_convert.py" convert-flac "<SOURCE_FOLDER>"
```
*Optional flags:*
- `--quality 2`: LAME VBR quality preset (default: 2 = ~190 kbps).
- `--keep-flac`: Keep original FLAC files instead of deleting them.
- `--workers 8`: Parallel worker threads (default: 8).
- `--dry-run`: Preview files that will be converted and deleted.

### 5. Rename Folders to `- mp3` (`rename-folders`)
Scans folder names ending in `"- Flac"`, verifies that no FLAC files remain, and renames to `"- mp3"`.
```powershell
python "$HOME/.gemini/config/skills/FLACMove_Convert/scripts/flac_move_convert.py" rename-folders "<SOURCE_FOLDER>"
```
*Optional flags:*
- `--dry-run`: Preview proposed folder renames.