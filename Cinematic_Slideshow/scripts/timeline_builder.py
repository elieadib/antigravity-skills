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

def probe_video_meta(path):
    """Probes exact duration and creation_time of a video file using ffprobe."""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration:format_tags=creation_time:stream_tags=creation_time", "-of", "json", path]
    dur = 5.0
    creation_time = None
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(res.stdout)
        dur = float(data.get("format", {}).get("duration", 5.0))
        ct = data.get("format", {}).get("tags", {}).get("creation_time")
        if not ct and data.get("streams"):
            ct = data["streams"][0].get("tags", {}).get("creation_time")
        if ct:
            clean_ct = ct.replace("T", " ").split(".")[0].rstrip("Z")
            creation_time = clean_ct
    except Exception:
        pass
    return dur, creation_time

def scan_directory(source_dir, ignore_prefixes=None):
    """Catalogues photos and videos in source_dir, filtering out generated exports."""
    if ignore_prefixes is None:
        ignore_prefixes = ["summer", "pilot", "slideshow", "temp_", "photos of our"]

    from datetime import datetime

    files = sorted(os.listdir(source_dir))
    photos = []
    videos = []
    cover_file = None

    for f in files:
        low = f.lower()
        ext = os.path.splitext(low)[1]
        if "cover" in low and ext in [".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tif", ".bmp"]:
            cover_file = f
            continue

        if any(low.startswith(p) for p in ignore_prefixes) or "_pilot" in low or "slideshow" in low:
            continue

        # Filter out existing rendered slideshow movies (full renders or pilots)
        if ext in [".mp4", ".mov", ".mkv"]:
            # Only filter out final rendered movies or test clips, not numbered source clips
            is_rendered = False
            for k in ["mariage de maria et hugo", "10 days in the azores", "2 weeks in crete", "_slideshow", "_rendered", "_master", "_web"]:
                if k in low:
                    is_rendered = True
                    break
            if is_rendered and not re.search(r"casa_\d+", low):
                continue

        full_path = os.path.join(source_dir, f)

        if ext in [".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tif", ".bmp"]:
            meta_time = None
            try:
                with Image.open(full_path) as img:
                    img_t = ImageOps.exif_transpose(img)
                    w, h = img_t.size
                    orientation = "portrait" if h > w else "landscape"
                    exif = img._getexif()
                    if exif:
                        raw_dt = exif.get(36867) or exif.get(306) or exif.get(36868)
                        if raw_dt:
                            meta_time = str(raw_dt).strip().replace(":", "-", 2)
            except Exception:
                w, h = 3840, 2160
                orientation = "landscape"

            if not meta_time:
                try:
                    meta_time = datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    meta_time = "2026-01-01 00:00:00"

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
                "meta_time": meta_time,
                "is_dji": "dji" in low
            })

        elif ext in [".mp4", ".mov", ".mkv"]:
            m = re.search(r"\d{8}", f)
            date_str = m.group(0) if m else "20260101"
            duration, creation_time = probe_video_meta(full_path)
            if not creation_time:
                try:
                    creation_time = datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    creation_time = "2026-01-01 00:00:00"

            videos.append({
                "filename": f,
                "path": full_path,
                "type": "video",
                "date": date_str,
                "meta_time": creation_time,
                "duration": duration,
                "is_dji": "dji" in low
            })

    return cover_file, photos, videos

def build_timeline(source_dir, title_center="Vacation 2026", title_date="",
                   title_duration=9.0, photo_hold_min=3.0, photo_hold_max=3.0,
                   untrimmed_videos=True, video_max_dur=6.0, seed=None, shuffle=False,
                   captions=None, custom_order=None, photo_dur=3.0):
    """
    Builds the shot-by-shot timeline structured for narrative flow.
    By default (shuffle=False), all assets are sequenced strictly chronologically by metadata timestamps.
    If custom_order is provided, media is sequenced according to that list.
    If shuffle=True, photos and videos are picked randomly across the entire album.
    Photos hold for 3.0 seconds by default; videos remain untrimmed at full duration.
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
        "zoom_in_upper",
        "zoom_out_upper",
        "zoom_in_diagonal_left",
        "zoom_out_diagonal_right",
        "zoom_in_wide",
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

    rng = random.Random(seed) if seed is not None else random.Random()
    shot_counter = 2
    motion_idx = 0
    trans_idx = 0

    if custom_order:
        item_by_name = {p["filename"]: p for p in (photos + videos)}
        combined = []
        for name in custom_order:
            clean_name = os.path.basename(name).strip()
            found = item_by_name.get(clean_name)
            if not found:
                for k, v in item_by_name.items():
                    if k.lower() == clean_name.lower() or os.path.splitext(k.lower())[0] == os.path.splitext(clean_name.lower())[0]:
                        found = v
                        break
            if found and found not in combined:
                combined.append(found)
    elif shuffle:
        # Pick photos and videos completely randomly across the entire folder
        shuffled_photos = list(photos)
        shuffled_videos = list(videos)
        rng.shuffle(shuffled_photos)
        rng.shuffle(shuffled_videos)

        combined = []
        p_idx, v_idx = 0, 0
        while p_idx < len(shuffled_photos) or v_idx < len(shuffled_videos):
            take_photos = rng.randint(2, 4) if shuffled_videos else len(shuffled_photos)
            for _ in range(take_photos):
                if p_idx < len(shuffled_photos):
                    combined.append(shuffled_photos[p_idx])
                    p_idx += 1
            if v_idx < len(shuffled_videos):
                combined.append(shuffled_videos[v_idx])
                v_idx += 1
    else:
        # Sort chronologically by metadata timestamp, with natural filename sequence as tiebreaker
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

        all_media = sorted(photos + videos, key=lambda item: (
            item.get("meta_time") or "9999",
            natural_sort_key(item.get("filename", ""))
        ))
        # Avoid repeating the cover photo immediately if it was used for the title slide
        combined = []
        for item in all_media:
            if item.get("path") == cover_path and not cover_file:
                continue # Already shown in full glory as the opening title slide
            combined.append(item)

    for item in combined:
        is_photo = item["type"] == "photo"
        if is_photo:
            if photo_dur is not None:
                hold_dur = float(photo_dur)
            else:
                hold_dur = rng.uniform(photo_hold_min, photo_hold_max)
        else:
            hold_dur = item["duration"] if untrimmed_videos else min(item["duration"], video_max_dur)

        motion = motion_styles[motion_idx % len(motion_styles)]
        motion_idx += 1

        trans = transitions[trans_idx % len(transitions)]
        trans_idx += 1

        caption_text = ""
        if captions:
            if item["filename"] in captions:
                caption_text = captions[item["filename"]]
            elif os.path.basename(item["path"]) in captions:
                caption_text = captions[os.path.basename(item["path"])]
            else:
                for k, v in captions.items():
                    if k.lower() == item["filename"].lower():
                        caption_text = v
                        break

        timeline.append({
            "shot_id": shot_counter,
            "type": item["type"],
            "filename": item["filename"],
            "path": item["path"],
            "caption": caption_text,
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
