---
name: music-track-renamer
description: >-
  Extracts Band name, Album name, and Track name from MP3 and FLAC audio tags, and renames
  all music files inside every folder to the standard pattern: "BandName - AlbumName - TrackName".
  Use whenever the user requests to rename, standardize, clean up, or organize music files or
  audio tracks in any folder based on audio metadata.
---

# Music Track Renamer Agent

Automates extracting audio metadata (ID3v1/ID3v2 for MP3, Vorbis Comments for FLAC) and safely renaming music files across all directories.

## Workflow

The core script is located at [rename_tracks.py](./scripts/rename_tracks.py).

To preview or rename any music folder (or directory containing multiple album folders):

1. **Dry-Run Preview (Recommended first):**
   ```powershell
   python "$HOME/.gemini/config/skills/music-track-renamer/scripts/rename_tracks.py" --dry-run "<FOLDER_PATH>"
   ```

2. **Execute Live Renaming:**
   ```powershell
   python "$HOME/.gemini/config/skills/music-track-renamer/scripts/rename_tracks.py" "<FOLDER_PATH>"
   ```

3. **Or run via CLI shortcut:**
   ```powershell
   rename-tracks "<FOLDER_PATH>"
   rename-tracks --dry-run "<FOLDER_PATH>"
   ```

## Naming Standards Applied

- Pattern: `<BandName> - <AlbumName> - <TrackName>.<ext>`
- Supported formats: `.mp3`, `.flac`
- Intelligent fallbacks:
  - If a file is missing artist/album tags, it falls back to sibling files in the folder or folder structure.
  - If track title tag is missing, it intelligently extracts track title from the filename.
- Collision avoidance: Appends `(2)`, `(3)` if multiple tracks share the same title in an album.
- Safe Windows renaming: Resolves case-only renames via temporary intermediate names and strips illegal characters (`< > : " / \ | ? *`).
- CUE sheets: Automatically updates corresponding `FILE "..." WAVE` references in `.cue` files.
