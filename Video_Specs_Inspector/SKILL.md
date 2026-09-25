---
name: Video_Specs_Inspector
description: >-
  Inspects video files in a specified directory (or single file) and generates a structured
  specs table detailing Video Bitrate (kbits/sec), Audio Bitrate (kbit/s), Resolution, Video & Audio
  Codecs, FPS, Duration, and File Size. Supports recursive directory scanning, multi-threaded ffprobe
  analysis, flexible sorting, and multiple output formats (Markdown table, CLI border table, CSV, JSON).
  Use whenever the user asks to inspect video specs, list video bitrates, check audio bitrates, get video
  resolutions or codecs, build a video metadata table, or audit video files in a folder.
---

# Video Specs Inspector (`Video_Specs_Inspector`)

A high-performance media analysis skill that scans any directory or video collection and compiles a clean, detailed technical table providing video bitrate, audio bitrate, resolution, codecs, frame rate, duration, and file size.

---

## Key Capabilities

1. **Precision Bitrate Extraction**:
   - Accurately reports Video Bitrate (`kb/s`) and Audio Bitrate (`kb/s`).
   - Uses multi-tier fallback calculation (stream bit_rate -> container BPS tags -> stream byte/duration calculation -> container demux approximation) so bitrates are never missing even when container headers omit explicit bitrate tags.
2. **Codec Identification**:
   - Identifies and formats video codecs (e.g. `H.264 / AVC`, `H.265 / HEVC`, `AV1`, `VP9`, `ProRes`, 10-bit profiles) and audio codecs (e.g. `AAC`, `AC-3 Dolby Digital`, `E-AC-3 DD+`, `DTS`, `FLAC`, `MP3`, `Opus`, channel layouts like `stereo`, `5.1`).
3. **Multi-Threaded Probing**:
   - Rapid parallel inspection with `ThreadPoolExecutor` and `ffprobe` for near-instant scanning of large movie libraries and video directories.
4. **Flexible Output Formats**:
   - **Markdown Table** (default): Formatted for chat displays, GitHub, Notion, and Markdown documents.
   - **Bordered Terminal Table (`--format table`)**: Clean ASCII/Unicode table formatted for command-line consoles.
   - **CSV Export (`--csv` or `--format csv`)**: Easy spreadsheet export for Excel and Google Sheets.
   - **JSON Export (`--json` or `--format json`)**: Programmatic JSON schema for pipelines and automation.
5. **Intelligent Sorting & Filtering**:
   - Sort by video bitrate (`--sort vbitrate`), audio bitrate (`--sort abitrate`), resolution (`--sort resolution`), file size (`--sort size`), duration (`--sort duration`), or name (`--sort name`).
   - Filter out small clips or samples using `--min-size` (e.g. `--min-size 10MB`).
   - Recursively scan subfolders with `-r` / `--recursive`.

---

## CLI Usage & Commands

The core script is located at [scripts/video_specs_inspector.py](./scripts/video_specs_inspector.py). Shell wrappers [video-specs-inspector.sh](./video-specs-inspector.sh) (Mac/Linux) and [video-specs-inspector.bat](./video-specs-inspector.bat) (Windows) are provided for convenience.

### 1. Inspect All Videos in a Directory (Markdown Table Output)
```bash
python3 "$HOME/.gemini/config/skills/Video_Specs_Inspector/scripts/video_specs_inspector.py" "/path/to/video/folder"
```
*(Or via bash shortcut: `bash "$HOME/.gemini/config/skills/Video_Specs_Inspector/video-specs-inspector.sh" "/path/to/video/folder"`)*

### 2. Recursive Scan Across All Subdirectories (`-r`)
```bash
python3 "$HOME/.gemini/config/skills/Video_Specs_Inspector/scripts/video_specs_inspector.py" "/path/to/video/folder" -r
```

### 3. Display as a Terminal Bordered Table
```bash
python3 "$HOME/.gemini/config/skills/Video_Specs_Inspector/scripts/video_specs_inspector.py" "/path/to/video/folder" --format table
```

### 4. Sort by Video Bitrate (Highest to Lowest)
```bash
python3 "$HOME/.gemini/config/skills/Video_Specs_Inspector/scripts/video_specs_inspector.py" "/path/to/video/folder" --sort vbitrate --reverse
```

### 5. Export Directly to a CSV or Markdown File
```bash
# Export to CSV
python3 "$HOME/.gemini/config/skills/Video_Specs_Inspector/scripts/video_specs_inspector.py" "/path/to/video/folder" --csv "/path/to/report.csv"

# Export to Markdown file
python3 "$HOME/.gemini/config/skills/Video_Specs_Inspector/scripts/video_specs_inspector.py" "/path/to/video/folder" --md "/path/to/report.md"
```

### 6. Inspect a Single Video File
```bash
python3 "$HOME/.gemini/config/skills/Video_Specs_Inspector/scripts/video_specs_inspector.py" "/path/to/movie.mp4"
```

---

## Column Breakdown

| Column | Description | Example |
| :--- | :--- | :--- |
| **File Name** | Name of the video file | `Sample_Movie.mp4` |
| **Resolution** | Dimensions and common resolution tag | `1920x1080 (1080p)` / `3840x2160 (4K UHD)` |
| **Video Codec** | Video compression codec and bit depth | `H.264 / AVC`, `H.265 / HEVC 10-bit` |
| **Video (kb/s)** | Video stream bitrate in kbits/sec | `4,520 kb/s` |
| **Audio Codec** | Audio codec and channel layout | `AAC (stereo)`, `AC-3 (Dolby Digital) (5.1)` |
| **Audio (kb/s)** | Audio stream bitrate in kbit/s | `320 kb/s` |
| **FPS** | Frame rate in frames per second | `23.98 fps`, `60 fps` |
| **Duration** | Formatted playback duration | `01:42:15` |
| **Size** | Human-readable file size | `1.4 GB` |

---

## Agent Guidelines

When the user asks to inspect videos in a folder:
1. Ask the user for the folder path if not provided.
2. Execute `video_specs_inspector.py` targeting that directory.
3. Render the resulting Markdown table directly into your response.
4. If the user asks for CSV, file export, or specific sorting (e.g. find lowest/highest bitrate videos), pass the corresponding flags (`--csv`, `--sort vbitrate`, etc.).
