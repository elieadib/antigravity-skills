---
name: Before_the_Move_to_JF
description: >-
  Prepares movie video files and matching subtitles (.srt) before moving them to Jellyfin (JF) or
  media servers. Scans directories containing movie folders, standardizes movie files and subtitles
  to "Movie Name - Release Year", moves both files to the root/target directory, and safely cleans
  emptied source folders and residual torrent assets. Supports preview dry-runs, collision avoidance,
  and standalone video cleanup. Use whenever the user asks to prepare movies before moving to Jellyfin / JF,
  clean up or organize movies for server transfer, or standardize movie and subtitle names.
---

# Before the Move to JF (Jellyfin Movie Organizer)

Automated utility and workflow to prepare downloaded movies and subtitle assets before ingesting them into Jellyfin (`JF`) or media servers. It parses movie titles and release years from folder and file names, pairs video files with matching subtitles, moves them cleanly to the target library directory, and eliminates residual torrent metadata, covers, and empty folders.

## Capabilities & Features

- **Jellyfin-Ready Naming**: Renames video and primary subtitle files to the standardized pattern: `"Movie Name - Release Year.ext"` (e.g., `Inception - 2010.mp4` and `Inception - 2010.srt`).
- **Intelligent Title & Year Parsing**: Extracts clean movie titles and 4-digit release years from standard release formats (e.g. `Movie Name (2026) [1080p] [WEBRip]...`) and scene formats (e.g. `Movie.Name.2026.1080p...`).
- **Subtitle Auto-Pairing**: Automatically detects and pairs matching primary `.srt` files in the folder or inside `Subs/` subdirectories (prioritizing English/SDH).
- **Collision Avoidance**: Identifies duplicate releases of the same movie (e.g., x265 vs x264), preserving the primary release cleanly and applying non-destructive tags (e.g. `[x264]`) to prevent overwriting.
- **Integrity Verification**: Verifies file size and existence at destination before removing any source folders.
- **Torrent Residue Purging**: Deletes emptied source folders and residual torrent clutter (`.jpg`, `.txt`, `.nfo`, and auxiliary language subtitle folders).
- **Non-Movie Protection**: Automatically skips non-movie directories (such as music albums or document folders) that do not contain video files.
- **Loose Video Cleanup**: Automatically detects and standardizes loose scene-named video files sitting directly in the intake root directory.
- **Dry-Run Preview**: Full simulation mode (`--dry-run`) allowing you to audit proposed renames and moves before modifying any data.

---

## CLI Usage & Commands

The core script is located at [before_the_move_to_jf.py](./scripts/before_the_move_to_jf.py). A batch launcher is also provided at [before-the-move-to-jf.bat](./before-the-move-to-jf.bat).

### 1. Dry-Run Preview (Recommended Before Execution)
Simulate all renaming, moves, and folder cleanups without modifying any files:
```powershell
python "$HOME/.gemini/config/skills/Before_the_Move_to_JF/scripts/before_the_move_to_jf.py" --dry-run "E:\Movies_tobemoved to Server"
```

### 2. Execute Organization on Target Directory
Process all folders in the directory, move clean files to the root, and delete source folders:
```powershell
python "$HOME/.gemini/config/skills/Before_the_Move_to_JF/scripts/before_the_move_to_jf.py" "E:\Movies_tobemoved to Server"
```
*(Or via batch shortcut: `& "$HOME\.gemini\config\skills\Before_the_Move_to_JF\before-the-move-to-jf.bat" "E:\Movies_tobemoved to Server"`)*

### 3. Move Directly to Jellyfin Library / Server Destination
Organize files from a download/staging folder and move them straight into a Jellyfin intake or server folder:
```powershell
python "$HOME/.gemini/config/skills/Before_the_Move_to_JF/scripts/before_the_move_to_jf.py" "E:\Downloads" --target-dir "\\elieserver\wd_14T\Movies-tobe_watched"
```

### 4. Keep Source Folders (Do Not Delete)
Move and rename files without deleting the source folders:
```powershell
python "$HOME/.gemini/config/skills/Before_the_Move_to_JF/scripts/before_the_move_to_jf.py" --no-delete "<FOLDER_PATH>"
```

### 5. Verbose Output
Display detailed information about every inspection step and skipped folder:
```powershell
python "$HOME/.gemini/config/skills/Before_the_Move_to_JF/scripts/before_the_move_to_jf.py" --verbose "<FOLDER_PATH>"
```
