---
name: Movie_Organizer
description: >-
  Scans directories containing movie folders, standardizes movie video files (.mp4, .mkv, .avi, etc.)
  and matching subtitles (.srt) to "Movie Name - Release Year", moves them to the parent or target
  directory, and safely deletes emptied source folders and residual torrent assets. Supports preview
  dry-runs, collision detection, and standalone video file cleanup. Use whenever the user asks to
  clean up, rename, organize, or flatten movie folders or video libraries.
---

# Movie Organizer Agent

Automated utility and workflow to clean, standardize, and organize movie libraries. It parses movie titles and release years from folder and file names, pairs video files with matching subtitles, moves them to the parent or destination directory, and cleans up residual torrent metadata and empty folders.

## Capabilities & Features

- **Intelligent Title & Year Parsing**: Extracts clean movie titles and 4-digit release years from standard folder formats (e.g. `Movie Name (2026) [1080p] [WEBRip]...`) and scene formats (e.g. `Movie.Name.2026.1080p...`).
- **Standardized Naming**: Renames video and primary subtitle files to the clean pattern: `"Movie Name - Release Year.ext"`.
- **Subtitle Auto-Pairing**: Automatically detects matching primary `.srt` files in the folder or inside `Subs/` subdirectories (prioritizing English/SDH).
- **Collision Avoidance**: Intelligently identifies duplicate releases of the same movie (e.g., x265 vs x264), preserving the primary release cleanly and applying non-destructive tags (e.g. `[x264]`) to prevent overwrites.
- **Integrity Verification**: Verifies file size and existence at destination before removing any source folders.
- **Residual Purging**: Deletes emptied source folders and non-essential torrent residue (e.g. `WWW.YIFY-TORRENTS.COM.jpg`, `YTS.GG - Official site.jpg`, info `.txt` files, and auxiliary language subtitle folders).
- **Non-Movie Protection**: Automatically skips non-movie directories (such as music albums or document folders) that do not contain video files.
- **Loose Video Cleanup**: Automatically detects and standardizes loose scene-named video files sitting directly in the target root directory.
- **Dry-Run Preview**: Full simulation mode (`--dry-run`) allowing you to audit proposed renames and moves before modifying anything.

---

## CLI Usage & Commands

The core script is implemented in Python (standard library only) at [movie_organizer.py](./scripts/movie_organizer.py).

### 1. Dry-Run Preview (Recommended Before Execution)
Simulate all renaming, moves, and folder cleanups without touching any files:
```powershell
python "$HOME/.gemini/config/skills/Movie_Organizer/scripts/movie_organizer.py" --dry-run "E:\Movies_tobemoved to Server"
```

### 2. Execute Organization on Target Directory
Process all folders in the directory, move clean files to the root, and delete source folders:
```powershell
python "$HOME/.gemini/config/skills/Movie_Organizer/scripts/movie_organizer.py" "E:\Movies_tobemoved to Server"
```

### 3. Move to a Separate Destination Directory
Organize files from a source directory and move them to a different library or server folder:
```powershell
python "$HOME/.gemini/config/skills/Movie_Organizer/scripts/movie_organizer.py" "E:\Downloads" --target-dir "E:\Movies-tobe_watched"
```

### 4. Keep Source Folders (Do Not Delete)
Move and rename files without deleting the source folders:
```powershell
python "$HOME/.gemini/config/skills/Movie_Organizer/scripts/movie_organizer.py" --no-delete "E:\Movies_tobemoved to Server"
```

### 5. Verbose Output
Display detailed information about every skipped folder and inspection step:
```powershell
python "$HOME/.gemini/config/skills/Movie_Organizer/scripts/movie_organizer.py" --verbose "E:\Movies_tobemoved to Server"
```
