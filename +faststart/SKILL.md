---
name: "+faststart"
description: >-
  Losslessly optimizes MP4, MOV, and M4V videos for progressive web streaming (+faststart),
  repairs unplayable web streams (10-bit H.264 -> 8-bit, PCM -> AAC, caps extreme >35Mbps bitrates,
  fixes mistagged 8-bit smpte2084 HDR VUI to bt709) while strictly preserving all AV1 streams untouched,
  and automatically generates 8s poster thumbnails (.jpg) and 4s muted 480p hover micro-previews (.preview.mp4).
  Use whenever the user asks to add faststart, web-optimize videos, repair video codecs/audio streams for web,
  generate video hover previews/posters, or run +faststart across video folders or media libraries.
---

# +faststart (`+faststart`)

The ultimate web streaming and codec optimization suite for MP4, MOV, and M4V video collections. Combines binary-fast lossless `+faststart` metadata relocation, intelligent browser codec normalization (with strict AV1 preservation), and automated web gallery derivative generation (8s posters and 4s hover micro-previews).

---

## Why +faststart & Codec Normalization are Essential for Web Video

Standard video encoders (Premiere, DaVinci Resolve, smartphone recording apps, and legacy tools) frequently create media files with attributes that severely impair or completely break web browser playback:

1. **Missing `+faststart` (moov at end-of-file)**:
   - *Problem*: Web browsers must download the entire video before playback can begin. A 100 MB video stalls for several seconds before frame 1 renders.
   - *Solution*: `+faststart` moves the `moov` atom to the very first bytes of the file, enabling instant progressive playback and millisecond timeline seeking.
2. **Unplayable 10-bit H.264 (`High 10` / `yuv420p10le`)**:
   - *Problem*: Web browsers (Chrome, Firefox, Safari on Windows/Android) lack hardware decoders for 10-bit H.264 and freeze completely with a black screen or decoding error.
   - *Solution*: Transcodes the video stream to universal 8-bit H.264 `High` profile (`yuv420p`) with pristine quality (`CRF 20`).
3. **Uncompressed PCM Audio in MP4 (`pcm_s16le`)**:
   - *Problem*: Web browsers cannot decode raw uncompressed PCM audio inside MP4 containers, resulting in completely silent playback.
   - *Solution*: Remuxes the audio track to high-fidelity AAC (`160 kbps`) while copying the video stream bit-for-bit with zero re-encoding.
4. **Extreme Bitrate Outliers (`>35 Mbps`)**:
   - *Problem*: Uncapped 4K phone recordings (e.g. 55 Mbps) choke cellular data connections and trigger high memory usage on mobile devices.
   - *Solution*: Normalizes extreme outliers to standard web-optimized bitrates (`CRF 21`, `-maxrate 12M`, `-bufsize 24M`).
5. **Mis-tagged 8-bit `smpte2084` HDR VUI Signaling**:
   - *Problem*: Standard SDR 8-bit videos incorrectly flagged with HDR transfer characteristics display washed-out gray tones on web players.
   - *Solution*: Losslessly updates bitstream VUI and container `colr` atoms to standard `bt709` without touching video pixels.
6. **Strict AV1 Stream Preservation**:
   - *Rule*: Modern `AV1` video streams are **always preserved bit-for-bit** (`-c:v copy`), only applying `+faststart` when needed without touching AV1 video encoding.
7. **Web Gallery Derivative Generation**:
   - *Poster Frame*: Extracts an 8-second poster thumbnail (`.jpg`) to replace black intro frames.
   - *Hover Micro-Preview*: Generates a 4-second `480p` `15fps` muted `+faststart` micro-clip (`<name>.preview.mp4`, ~70–120 KB) enabling instantaneous zero-delay video hover playback in web portfolio grids.

---

## Core Capabilities & Flags

| Flag | Mode | Description |
| :--- | :--- | :--- |
| *(default)* | **Lossless `+faststart`** | Binary header check (`moov < mdat`). Relocates `moov` index in `<1s` per video with `-c copy -movflags +faststart`. Skips already-optimized files. |
| `--repair` / `--normalize` | **Codec & Stream Repair** | Normalizes 10-bit H.264, PCM audio, extreme bitrates, and mis-tagged HDR while strictly keeping all AV1 streams untouched. |
| `--previews` | **Derivative Generation** | Generates 8s poster `.jpg` and 4s muted `480p` `.preview.mp4` hover loops in `Video_Thumbs/`. |
| `--all` / `--full` | **Complete Web Suite** | Runs `+faststart` + stream repair + AV1 preservation + 8s poster and 4s hover micro-preview generation in one pass. |
| `-r` / `--recursive` | **Recursive Traversal** | Recursively scans all subfolders, automatically skipping internal thumbnail and git caches. |
| `-d` / `--dry-run` | **Preview / Audit** | Inspects videos and outputs an actionable plan without modifying any files on disk. |
| `-f` / `--force` | **Force Re-process** | Forces re-muxing even if the binary header confirms `moov` is already at the start. |

---

## CLI Usage & Commands

The core script is located at [faststart.py](./scripts/faststart.py). Shell wrappers [faststart.sh](./faststart.sh) (Mac/Linux) and [faststart.bat](./faststart.bat) (Windows) are provided for convenience.

### 1. Default: Lossless `+faststart` Across a Library (`-r`)
```bash
python3 "$HOME/.gemini/config/skills/+faststart/scripts/faststart.py" "/path/to/media/library" -r
```

### 2. Full Suite: `+faststart` + Stream Repair + 4s Hover Previews (`--all`)
```bash
python3 "$HOME/.gemini/config/skills/+faststart/scripts/faststart.py" "/path/to/media/library" -r --all
```
*(Or via bash shortcut: `bash "$HOME/.gemini/config/skills/+faststart/faststart.sh" "/path/to/media/library" -r --all`)*

### 3. Stream & Codec Repair Only (`--repair`)
Fixes 10-bit H.264, PCM audio, extreme bitrates, and HDR tags while strictly preserving AV1:
```bash
python3 "$HOME/.gemini/config/skills/+faststart/scripts/faststart.py" "/path/to/media/library" -r --repair
```

### 4. Generate 8s Posters & 4s Hover Previews Only (`--previews`)
```bash
python3 "$HOME/.gemini/config/skills/+faststart/scripts/faststart.py" "/path/to/media/library" -r --previews
```

### 5. Dry-Run Audit (`-d`)
Inspects what needs optimization or repair without touching disk:
```bash
python3 "$HOME/.gemini/config/skills/+faststart/scripts/faststart.py" "/path/to/media/library" -r --all -d
```

### 6. Single Video Optimization
```bash
python3 "$HOME/.gemini/config/skills/+faststart/scripts/faststart.py" "/path/to/video.mp4" --all
```

---

## Platform Launchers

### On macOS / Linux:
```bash
"$HOME/.gemini/config/skills/+faststart/faststart.sh" "/path/to/folder" -r --all
```

### On Windows:
```cmd
"%USERPROFILE%\.gemini\config\skills\+faststart\faststart.bat" "C:\path\to\folder" -r --all
```

---

## Technical Verification

To inspect whether a video file has `moov` located before `mdat` using Python:
```bash
python3 -c "
with open('video.mp4', 'rb') as f:
    while True:
        hdr = f.read(8)
        if len(hdr) < 8: break
        sz = int.from_bytes(hdr[:4], 'big')
        name = hdr[4:8].decode('latin1', errors='ignore')
        if name == 'moov':
            print('VERIFIED: moov is at start of file (+faststart active)')
            break
        elif name == 'mdat':
            print('UNOPTIMIZED: mdat precedes moov')
            break
        if sz == 1: sz = int.from_bytes(f.read(8), 'big')
        elif sz <= 8: break
        f.seek(sz - 8, 1)
"
```
