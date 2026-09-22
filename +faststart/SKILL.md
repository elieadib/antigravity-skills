---
name: "+faststart"
description: >-
  Losslessly optimizes MP4 and MOV videos for progressive web streaming by relocating
  the 'moov' atom metadata to the beginning of the file using 'ffmpeg -c copy -movflags +faststart'.
  Prevents buffering delays, enables instant video playback and seeking in web browsers, and safely
  preserves all original video streams, audio quality, and timestamps. Supports batch directory processing,
  recursive subfolder scans, and dry-run previews. Use whenever the user asks to add faststart, web-optimize
  videos, enable progressive streaming, or run ffmpeg faststart on videos or video folders.
---

# +faststart (`+faststart`)

Lossless MP4 and MOV web-streaming optimizer that relocates container metadata (the `moov` atom) from the end of the file to the beginning. This allows web browsers, mobile devices, and video players to start playing and seeking immediately without having to download the entire file first.

## Why +faststart is Essential for Web Video

When video encoding tools (like XviD4PSP, DaVinci Resolve, Premiere, or standard FFmpeg) export an MP4 or MOV file, they typically write the media frames (`mdat` atom) first and append the index (`moov` atom) at the very end.

* **Without +faststart:** A web browser cannot begin playing the video until it reads the `moov` atom at the very end of the file. For a 100 MB video, the user has to wait for 100 MB to download before 1 second of video can play.
* **With +faststart:** The `moov` index is moved to the first few bytes of the file. The browser reads the metadata in milliseconds and starts playing immediately while downloading the rest progressively in the background.

---

## Core Capabilities

1. **100% Lossless Stream Copy (`-c copy`)**:
   - Zero re-encoding. Video frames, audio tracks, color profiles, and resolution remain bit-for-bit identical.
   - Operates at extreme speeds (typically 50x–200x realtime, taking less than 1 second per video).
2. **Safe Atomic Replacement**:
   - Muxes to a temporary file, verifies the new file's integrity and `moov` position, preserves original file creation/modification timestamps (`mtime`), and replaces the original file atomically.
3. **Smart Skip Logic**:
   - Uses binary header scanning to detect if `moov` already precedes `mdat`. Videos that are already optimized are skipped automatically, saving time on repeated runs.
4. **Format Support**:
   - Supports `.mp4`, `.mov`, and `.m4v` video files.
5. **Dry-Run & Recursive Traversal**:
   - Inspects single files or full directory trees (`--recursive`), reporting which videos need optimization without touching disk.

---

## Usage & Commands

The core script is located at [faststart.py](./scripts/faststart.py). Shell wrappers [faststart.sh](./faststart.sh) (Mac/Linux) and [faststart.bat](./faststart.bat) (Windows) are provided for convenience.

### 1. Optimize All Videos in a Folder (Non-Recursive)
```bash
python3 "$HOME/.gemini/config/skills/+faststart/scripts/faststart.py" "/path/to/video/folder"
```

### 2. Optimize an Entire Library Recursively (`-r` / `--recursive`)
```bash
python3 "$HOME/.gemini/config/skills/+faststart/scripts/faststart.py" "/path/to/media/library" -r
```

### 3. Preview Videos Needing Optimization (`-d` / `--dry-run`)
```bash
python3 "$HOME/.gemini/config/skills/+faststart/scripts/faststart.py" "/path/to/video/folder" -d
```

### 4. Optimize a Single Video File
```bash
python3 "$HOME/.gemini/config/skills/+faststart/scripts/faststart.py" "/path/to/video.mp4"
```

### 5. Force Re-Processing (`-f` / `--force`)
```bash
python3 "$HOME/.gemini/config/skills/+faststart/scripts/faststart.py" "/path/to/video.mp4" -f
```

---

## Platform Launchers

### On macOS / Linux:
```bash
"$HOME/.gemini/config/skills/+faststart/faststart.sh" "/path/to/folder"
```

### On Windows:
```cmd
"%USERPROFILE%\.gemini\config\skills\+faststart\faststart.bat" "C:\path\to\folder"
```

---

## Technical Verification

To inspect whether a video file has `moov` located before `mdat`:
```bash
python3 -c "
with open('video.mp4', 'rb') as f:
    while True:
        hdr = f.read(8)
        if len(hdr) < 8: break
        sz = int.from_bytes(hdr[:4], 'big')
        name = hdr[4:8].decode('latin1', errors='ignore')
        print(name, sz)
        if sz == 1: sz = int.from_bytes(f.read(8), 'big')
        elif sz <= 8: break
        f.seek(sz - 8, 1)
"
```
If `moov` appears before `mdat`, the video is verified for instant web streaming.
