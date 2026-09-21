---
name: music-folder-renamer
description: >-
  Extracts Band name, Album name, and Year from MP3 and FLAC audio tags, and renames
  music folders to the standard pattern: "BandName - AlbumName - Year - mp3" or
  "BandName - AlbumName - Year - Flac". Use whenever the user requests to rename,
  clean up, or organize music directories based on audio metadata.
---

# Music Folder Renamer

Automates the inspection of audio metadata (ID3v1/ID3v2 for MP3, Vorbis Comments for FLAC, and CUE sheets) and safely renames album directories.

## Workflow

The core script is located at [music_renamer.py](./scripts/music_renamer.py).

To preview or rename any music folder (or a directory containing multiple music album folders):

1. **Dry-Run Preview (Optional):**
   ```powershell
   python "$HOME/.gemini/config/skills/music-folder-renamer/scripts/music_renamer.py" --dry-run "<FOLDER_PATH>"
   ```

2. **Execute Renaming:**
   ```powershell
   python "$HOME/.gemini/config/skills/music-folder-renamer/scripts/music_renamer.py" "<FOLDER_PATH>"
   ```

## Naming Standards Applied

- Single album folder: `<Band> - <Album> - <Year> - <Format>`
- Audio format suffix:
  - `- mp3` if folder contains `.mp3` files
  - `- Flac` if folder contains `.flac` files
  - `- mp3 - Flac` if both formats are present
- Multi-album sets / discographies: `<Band> - Discography - <Format>` or `<Band> - Restored - <Format>`
- Collision avoidance: Appends `[Hi-Res]` or unique discriminator if multiple versions of the same album exist
- Illegal filename characters (`\ / : * ? " < > |`) are cleaned and standardized
