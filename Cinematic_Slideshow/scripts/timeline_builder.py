"""
Universal Timeline Builder for Cinematic Slideshow Agent.
Scans any media directory, extracts dates/metadata, sequences photos & videos for narrative flow,
probes video durations, alternates Ken Burns camera motion vectors, and assigns smooth transitions.
"""
import os
import re
import json
import random
import subprocess
from PIL import Image, ImageOps

def probe_video_duration(path):
    """Probes exact duration of a video file using ffprobe."""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(res.stdout)
        return float(data.get("format", {}).get("duration", 5.0))
    except Exception:
        return 5.0

def scan_directory(source_dir, ignore_prefixes=None):
    """Catalogues photos and videos in source_dir, filtering out generated exports."""
    if ignore_prefixes is None:
        ignore_prefixes = ["summer", "pilot", "slideshow", "temp_"]

    files = sorted(os.listdir(source_dir))
    photos = []
    videos = []
    cover_file = None

    for f in files:
        low = f.lower()
        ext = os.path.splitext(low)[1]
        if low.startswith("cover.") and ext in [".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tif", ".bmp"]:
            cover_file = f
            continue

        if any(low.startswith(p) for p in ignore_prefixes) or "_pilot" in low or "slideshow" in low:
            continue

        full_path = os.path.join(source_dir, f)

        if ext in [".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tif", ".bmp"]:
            try:
                with Image.open(full_path) as img:
                    img_t = ImageOps.exif_transpose(img)
                    w, h = img_t.size
                    orientation = "portrait" if h > w else "landscape"
            except Exception:
                w, h = 3840, 2160
                orientation = "landscape"

            m = re.search(r"\d{8}", f)
            date_str = m.group(0) if m else "20260101"

            photos.append({
                "filename": f,
                "path": full_path,
                "type": "photo",
                "width": w,
                "height": h,
                "orientation": orientation,
                "date": date_str,
                "is_dji": "dji" in low
            })

        elif ext in [".mp4", ".mov", ".mkv"]:
            m = re.search(r"\d{8}", f)
            date_str = m.group(0) if m else "20260101"
            duration = probe_video_duration(full_path)

            videos.append({
                "filename": f,
                "path": full_path,
                "type": "video",
                "date": date_str,
                "duration": duration,
                "is_dji": "dji" in low
            })

    return cover_file, photos, videos

def build_timeline(source_dir, title_center="Vacation 2026", title_date="",
                   title_duration=9.0, photo_hold_min=3.6, photo_hold_max=4.8,
                   untrimmed_videos=True, video_max_dur=6.0, seed=2026):
    """
    Builds the shot-by-shot timeline structured for narrative flow.
    """
    cover_file, photos, videos = scan_directory(source_dir)

    timeline = []

    # 1. Pure Black Lead-in (2.0s)
    timeline.append({
        "shot_id": 0,
        "type": "black_intro",
        "duration": 2.0,
        "transition": "fade",
        "transition_duration": 1.2
    })

    # 2. Title Slide
    if cover_file:
        cover_path = os.path.join(source_dir, cover_file)
    elif photos:
        cover_path = photos[0]["path"]
    else:
        cover_path = ""

    timeline.append({
        "shot_id": 1,
        "type": "title_slide",
        "path": cover_path,
        "filename": os.path.basename(cover_path) if cover_path else "Title",
        "duration": title_duration,
        "motion": "zoom_in_center",
        "transition": "fadewhite",
        "transition_duration": 0.8
    })

    motion_styles = [
        "zoom_in_center",
        "zoom_out_center",
        "pan_left_to_right",
        "push_in_diagonal",
        "zoom_in_center",
        "pan_right_to_left",
        "zoom_out_wide"
    ]

    transitions = [
        "fade",
        "fadewhite",
        "smoothleft",
        "fade",
        "smoothright",
        "fadeblack"
    ]

    # Group into chronological dates
    all_dates = sorted(list(set([p["date"] for p in photos] + [v["date"] for v in videos])))
    rng = random.Random(seed)

    shot_counter = 2
    motion_idx = 0
    trans_idx = 0

    if not all_dates:
        all_dates = ["default"]

    for d in all_dates:
        day_photos = [p for p in photos if p["date"] == d] if d != "default" else list(photos)
        day_videos = [v for v in videos if v["date"] == d] if d != "default" else list(videos)

        rng.shuffle(day_photos)
        rng.shuffle(day_videos)

        combined = []
        p_idx, v_idx = 0, 0
        while p_idx < len(day_photos) or v_idx < len(day_videos):
            for _ in range(rng.randint(1, 2)):
                if p_idx < len(day_photos):
                    combined.append(day_photos[p_idx])
                    p_idx += 1
            if v_idx < len(day_videos):
                combined.append(day_videos[v_idx])
                v_idx += 1

        for item in combined:
            is_photo = item["type"] == "photo"
            if is_photo:
                hold_dur = rng.uniform(photo_hold_min, photo_hold_max)
            else:
                hold_dur = item["duration"] if untrimmed_videos else min(item["duration"], video_max_dur)

            motion = motion_styles[motion_idx % len(motion_styles)]
            motion_idx += 1

            trans = transitions[trans_idx % len(transitions)]
            trans_idx += 1

            timeline.append({
                "shot_id": shot_counter,
                "type": item["type"],
                "filename": item["filename"],
                "path": item["path"],
                "orientation": item.get("orientation", "landscape"),
                "duration": round(hold_dur, 2),
                "motion": motion if is_photo else "native_video",
                "transition": trans,
                "transition_duration": 0.8
            })
            shot_counter += 1

    # Final Dim to Black Outro (2.5s)
    if len(timeline) > 2:
        timeline[-1]["transition"] = "fadeblack"
        timeline[-1]["transition_duration"] = 1.2

    timeline.append({
        "shot_id": shot_counter,
        "type": "black_outro",
        "duration": 2.5,
        "transition": "none",
        "transition_duration": 0.0
    })

    return timeline
