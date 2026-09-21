---
name: music-cue-flac-splitter
description: >-
  Scans music folders for unsplit big FLAC, APE, or WAV audio files paired with CUE sheets,
  losslessly splits them into individual FLAC tracks with embedded Vorbis metadata,
  verifies sample-accurate durations, and safely manages original files. Use whenever the
  user asks to split FLACs/CUE sheets, scan for unsplit audio, or split albums into individual tracks.
---

# Music CUE & FLAC Splitter Agent

Autonomous agent that scans music libraries, detects unsplit big audio files (FLAC, APE, WAV) accompanied by `.cue` sheets, losslessly splits them into individual FLAC tracks with rich Vorbis metadata tags, and verifies playback integrity.

## Capabilities & Architecture

- **Automatic Scanning**: Detects album folders containing `.cue` sheets with single large audio files.
- **Multi-Format Support**: Handles `.flac`, `.ape`, and `.wav` unsplit sources.
- **Lossless Sample-Accurate Splitting**: Converts CUE sector indices (`mm:ss:ff`) to exact fractional seconds and splits using FFmpeg native FLAC decoding/encoding.
- **Vorbis Comment Tagging**: Automatically embeds `Title`, `Artist`, `Album Artist`, `Album`, `Track Number/Total`, `Date`, and `Genre`.
- **Title Sanitization**: Cleans redundant track number prefixes (e.g. `01. `) and strips Windows-illegal characters (`< > : " / \ | ? *`).
- **Data Safety**:
  - Default: Archives original big files to `_original_unsplit/` inside the album folder.
  - Optional: `--delete-originals` to free disk space immediately upon verified split.
- **Duration Verification**: Audits the sum of track durations against the original audio duration down to sub-second precision.

## Workflow & Commands

The core script is located at [split_cue_flac.py](./scripts/split_cue_flac.py).

To scan and split any music directory (single album or multi-album library):

1. **Dry-Run Preview (Preview tracks and split intervals without writing):**
   ```powershell
   python "$HOME/.gemini/config/skills/music-cue-flac-splitter/scripts/split_cue_flac.py" --dry-run "<FOLDER_PATH>"
   ```

2. **Execute Splitting (Safely archives original big files to `_original_unsplit/`):**
   ```powershell
   python "$HOME/.gemini/config/skills/music-cue-flac-splitter/scripts/split_cue_flac.py" "<FOLDER_PATH>"
   ```

3. **Execute Splitting with Automatic Original Deletion (Frees disk space):**
   ```powershell
   python "$HOME/.gemini/config/skills/music-cue-flac-splitter/scripts/split_cue_flac.py" --delete-originals "<FOLDER_PATH>"
   ```

4. **Execute Splitting and Keep Originals Alongside:**
   ```powershell
   python "$HOME/.gemini/config/skills/music-cue-flac-splitter/scripts/split_cue_flac.py" --keep-originals "<FOLDER_PATH>"
   ```
