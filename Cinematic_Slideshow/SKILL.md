---
name: Cinematic_Slideshow
description: >-
  Transforms any collection of vacation photos and videos into a high-end, cinematic 4K UHD slideshow video.
  Features dynamic 2.5D Ken Burns effects (alternating zoom/pan directions), visible 30px white borders on photos
  and videos, dual-layer blurred matching backdrops leaving an 80px blurred background margin, custom title sequences
  (centered title + bottom-right date), smooth transitions (cross-dissolves, light leaks, whip pans, film fades),
  untrimmed full-duration video preservation, hardware-accelerated rendering (NVIDIA NVENC, Intel QSV, AMD AMF, Apple VideoToolbox, CPU fallback),
  and unified Mediterranean filmic color grading. ALWAYS ask the user what text to add on the 1st Cover/title photo
  (Centered Event Text and bottom-right Date Text) before rendering. Use whenever the user requests to create a slideshow,
  vacation video, photo montage, cinematic video from photos and videos, or compile travel media into a movie.
---

# Cinematic Slideshow Agent

A production-grade, hardware-accelerated video production utility and workflow that transforms any folder of photos and videos into a cinematic 4K UHD widescreen movie.

Designed to run seamlessly across all PCs (automatically selecting NVIDIA NVENC, Intel QuickSync, AMD AMF, or CPU encoding without configuration).

---

## ⚠️ MANDATORY WORKFLOW RULE: Cover / Title Photo Customization

**CRITICAL INSTRUCTION FOR AGENTS - ALWAYS PROMPT THE USER**:
Before initiating ANY slideshow render (whether running a pilot preview or the full master slideshow), the agent **MUST ALWAYS ASK THE USER** what text to add on the 1st Cover / Title photo:
1. **Centered Event Text**: A title/phrase describing the event (e.g., *"Summer 2026 - 2 weeks in Crete"*, *"Tuscany Roadtrip 2026"*, *"Family Holidays in Spain"*).
2. **Bottom-Right Date Text**: The date or date range of the event (e.g., *"Aug 2026"*, *"August 10 – 24, 2026"*, *"July 2026"*).

**NEVER** guess, auto-generate, or infer these texts without explicitly asking the user and confirming their choice first!

---

## Capabilities & Features

- **Universal Multi-PC Hardware Acceleration**:
  - Automatically probes available video encoders: **NVIDIA NVENC** (`h264_nvenc`), **Intel QuickSync** (`h264_qsv`), **AMD AMF** (`h264_amf`), or optimized CPU (`libx264`). Runs at maximum speed on any desktop or laptop without manual setup.
- **Dynamic 2.5D Ken Burns Effects**:
  - Continuous camera motion on every still photograph: slow push-ins, pull-outs, vista pans, corner-to-subject drifts, and wide landscape reveals.
  - Alternates zoom/pan vectors between consecutive shots to maintain dynamic visual rhythm.
- **Visible 30px White Borders**:
  - Automatically applies a crisp 30px white border to all photographs and video files.
  - Insets media with an 80px margin leaving a blurred matching backdrop so the border is never cut off by display edges or TV overscan.
- **Dual-Layer Compositing for Portrait Photos & Vertical/Pillarboxed Videos**:
  - Automatically detects media dimensions and orientation (portrait, landscape, square, smartphone rotation metadata tags, and pillarboxed vertical videos recorded inside 16:9 containers).
  - Automatically crops hardcoded black pillarbox bars and composites the centered, bordered photo or video over a synchronized, Gaussian-blurred (&sigma;=35), dimmed background layer of the same media leaving an 80px blurred background margin, completely eliminating black pillarbox bars on widescreen displays.
- **Customizable Cinematic Title Sequence**:
  - Opens with a 2.0-second pure black screen.
  - Smoothly dissolves into the title slide using `Cover.jpg` (or first photo) with slow push-in.
  - Displays large centered main title with soft drop shadow and bottom-right secondary date/location text.
  - Configurable duration (default 9.0s).
- **Untrimmed Video Support**:
  - By default preserves 100% of original video recordings without arbitrary cutting. Optional `--trim-videos N` flag available for fast highlight reels.
- **Audio Crossfades**:
  - Standardizes all audio to 48.0 kHz stereo AAC with gentle volume fade-ins and fade-outs between video audio and silent photo moments.
- **Smooth Transition Suite**:
  - Gentle cross-dissolves (`fade`), subtle warm light leaks (`fadewhite`), directional whip-pans (`smoothleft`, `smoothright`), and soft film dips to black (`fadeblack`).
  - Concludes with a 2.5-second gradual fade to black.
- **Warm Filmic Color Grading**:
  - Subtle S-curve contrast, warm golden sunlight highlights, deep azure sea enhancement, lifted shadows, and fine 35mm organic film grain.

---

## CLI Usage & Commands

The core script is located at [slideshow_maker.py](./scripts/slideshow_maker.py).

### 1. Basic Generation (Full 16:9 4K UHD, Untrimmed Videos)
Generate a 4K slideshow from a folder of photos and videos:
```powershell
python "$HOME/.gemini/config/skills/Cinematic_Slideshow/scripts/slideshow_maker.py" "E:\My_Photos\2026_08_Crête" --title "Summer 2026 - 2 weeks in Crete" --date "Aug 2026"
```

### 2. Fast Pilot Preview (5 Shots)
Quickly test and review a 5-shot preview (intro, title slide, portrait photo, video, landscape photo, outro) in seconds:
```powershell
python "$HOME/.gemini/config/skills/Cinematic_Slideshow/scripts/slideshow_maker.py" "E:\My_Photos\2026_08_Crête" --pilot
```

### 3. Custom Output Path
Specify an explicit output filename:
```powershell
python "$HOME/.gemini/config/skills/Cinematic_Slideshow/scripts/slideshow_maker.py" "D:\Photos\Italy_Roadtrip" --title "Road Trip Through Tuscany" --date "June 2026" -o "D:\Videos\Tuscany_2026_4K.mp4"
```

### 4. Cinematic Letterbox (2.39:1 Anamorphic Scope)
Apply 2.39:1 anamorphic scope matte bars (3840x1606 active area with 277px top/bottom bars):
```powershell
python "$HOME/.gemini/config/skills/Cinematic_Slideshow/scripts/slideshow_maker.py" "E:\My_Photos\2026_08_Crête" --title "Crete 2026" --letterbox
```

### 5. Fast Highlight Reel (Trim Videos to 5 Seconds)
Trim long videos to punchy 5-second action clips:
```powershell
python "$HOME/.gemini/config/skills/Cinematic_Slideshow/scripts/slideshow_maker.py" "D:\Photos\Ski_Trip_2026" --title "Alps Winter 2026" --trim-videos 5.0
```

### 6. 1080p Resolution
Render in 1080p Full HD (1920x1080) for lightweight sharing or low-power PCs:
```powershell
python "$HOME/.gemini/config/skills/Cinematic_Slideshow/scripts/slideshow_maker.py" "C:\Photos\Family_Event" --res 1080p
```

---

## Options Reference

| Flag | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `source_dir` | Positional | *Required* | Path to folder containing photos and videos |
| `-o`, `--output` | String | `source_dir/<Title>.mp4` | Explicit output destination file |
| `--title` | String | Clean folder name | Main center title text on title slide |
| `--date` | String | `""` | Bottom-right date/subtitle on title slide |
| `--title-dur` | Float | `9.0` | Title slide hold duration in seconds |
| `--res` | `4k` / `1080p` | `4k` | Output video resolution |
| `--fps` | Int | `24` | Video frame rate (24 or 60) |
| `--letterbox` | Flag | Off (16:9 full) | Enables 2.39:1 anamorphic letterbox matte bars |
| `--border` | Int | `30` | White border thickness in pixels |
| `--margin` | Int | `80` | Margin around media box leaving blurred background in pixels |
| `--shuffle` | Flag | On (True) | Randomly shuffle photos and videos across the timeline |
| `--no-shuffle` | Flag | Off | Arrange photos and videos chronologically by date |
| `--seed` | Int | `None` | Optional random seed for reproducible shuffle sequences |
| `--trim-videos` | Float | `None` (untrimmed) | Trims videos to maximum N seconds if set |
| `--pilot` | Flag | Off | Renders a fast 5-shot test preview |
| `--clear-cache` | Flag | Off | Clears intermediate render caches before rendering |

---

## Requirements & Dependencies

- **Python**: 3.10 or higher
- **FFmpeg**: Must be installed and accessible in `PATH`
- **Pillow**: `pip install Pillow`
