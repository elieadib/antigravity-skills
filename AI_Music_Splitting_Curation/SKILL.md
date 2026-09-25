---
name: AI_Music_Splitting_Curation
description: >-
  Splits, curates, and converts full-length AI-generated music albums (.m4a, .mp3, .flac) or single
  tracks into individually tracked, tagged 128 kb/s MP3s with embedded YouTube square cover art
  and dedicated folder organization. Automates album title simplification, YouTube release discovery
  via yt-dlp, chapter/description tracklist extraction, smart 1:1 square artwork cropping,
  sample-accurate silence detection boundary refinement, and cleanup of source/intermediate files.
  Use whenever the user asks to run AI_Music_Splitting_Curation, split AI music, curate an AI album,
  cut an album into tracks, process full-length music files, or extract YouTube album art and
  tracklists for music folders.
---

# AI Music Splitting & Curation (`AI_Music_Splitting_Curation`)

An automated audio curation workflow and standalone utility that transforms full-length AI-generated music albums (e.g. Suno, Udio, custom AI releases) and single tracks into cleanly organized, individual MP3 tracks tagged with official YouTube cover art and tracklists.

---

## Core Capabilities

1. **Title Simplification & Normalization**:
   - Strips metadata and YouTube marketing fluff (e.g., `[Full Album]`, `(1974)`, `Lost 70s Psychedelic Rock`, `4K Surreal Music Video`) to isolate clean Band and Album titles.
2. **Official YouTube Discovery (`yt-dlp`)**:
   - Automatically searches YouTube using the cleaned album title to locate the official channel release.
3. **Tracklist & Timestamp Extraction**:
   - Parses official video **chapters** or timestamped tracklists in video descriptions (`00:00 - Track Title`).
   - Slices continuous audio sessions at natural silence boundaries if no description tracklist exists.
4. **Smart Square Cover Art Cropping**:
   - Downloads the highest-resolution YouTube thumbnail.
   - Detects vinyl/album sleeve mockups or horizontal banners and crops them into a pristine **1:1 square artwork** (`<Album Name>.png`).
5. **Sample-Accurate Silence Detection Boundary Refinement**:
   - Analyzes a $\pm 10\text{s}$ window around track transitions using FFmpeg's `silencedetect` ($-20\text{ dB}$, minimum duration $0.2\text{s}$) to place cuts at the exact silence midpoint.
6. **128 kb/s MP3 Transcoding & ID3 Tagging**:
   - Encodes each track to constant-bitrate MP3 at **128 kb/s** (44.1 kHz stereo) with `libmp3lame`.
   - Embeds the square artwork directly into ID3 tags (`attached_pic` front cover).
   - Writes complete tags: `Title`, `Artist`, `Album`, and `Track Number` (`x/Total`).
7. **Directory Organization & Safe Cleanup**:
   - Moves all converted tracks (`<Album Name>_Track01.mp3`, etc.) and `<Album Name>.png` into a dedicated folder.
   - Cleans up intermediate sliced files, full-album `.mp3` files, and removes the source full-album file once verified.

---

## Workflow Commands

The core script is located at [ai_music_splitting_curation.py](./scripts/ai_music_splitting_curation.py).

### 1. Process an Entire Music Directory (e.g., `Ai_Music`):
```bash
python3 "$HOME/Library/CloudStorage/GoogleDrive-elieadib@gmail.com/My Drive/Antigravity/skills/AI_Music_Splitting_Curation/scripts/ai_music_splitting_curation.py" "/path/to/Ai_Music"
```

### 2. Process a Single Album File:
```bash
python3 "$HOME/Library/CloudStorage/GoogleDrive-elieadib@gmail.com/My Drive/Antigravity/skills/AI_Music_Splitting_Curation/scripts/ai_music_splitting_curation.py" "/path/to/Album.m4a"
```

### 3. Dry-Run Preview (Simulate Without Writing):
```bash
python3 "$HOME/Library/CloudStorage/GoogleDrive-elieadib@gmail.com/My Drive/Antigravity/skills/AI_Music_Splitting_Curation/scripts/ai_music_splitting_curation.py" "/path/to/Ai_Music" --dry-run
```

### 4. Custom MP3 Bitrate (e.g., 192k, 320k):
```bash
python3 "$HOME/Library/CloudStorage/GoogleDrive-elieadib@gmail.com/My Drive/Antigravity/skills/AI_Music_Splitting_Curation/scripts/ai_music_splitting_curation.py" "/path/to/Ai_Music" --bitrate 192k
```

### 5. Keep Original Source Audio Files:
```bash
python3 "$HOME/Library/CloudStorage/GoogleDrive-elieadib@gmail.com/My Drive/Antigravity/skills/AI_Music_Splitting_Curation/scripts/ai_music_splitting_curation.py" "/path/to/Ai_Music" --keep-source
```

---

## CLI Options Reference

| Option | Flag | Default | Description |
| :--- | :--- | :--- | :--- |
| `path` | | `.` | Target music folder containing audio files or individual audio file. |
| `--bitrate` | `-b` | `128k` | Target MP3 encoding bitrate (e.g. `128k`, `192k`, `320k`). |
| `--sample-rate` | `-r` | `44100` | Target audio sample rate in Hz. |
| `--keep-source` | | `False` | Preserve original source audio file after verified track generation. |
| `--dry-run` | `-d` | `False` | Preview actions, YouTube matches, and split points without modifying files. |
