#!/usr/bin/env python3
"""
Cinematic Slideshow Maker CLI.
Transforms any collection of photos and videos into a high-end, cinematic 4K UHD video slideshow.
"""
import os
import sys
import argparse
import timeline_builder
import render_engine
import random

def derive_default_title(folder_path):
    """Infers an elegant title from folder name if none is provided."""
    import re
    folder_name = os.path.basename(os.path.normpath(folder_path))
    clean = re.sub(r"^\d+[\s_-]*", "", folder_name)
    clean = clean.replace("_", " ").strip()
    return clean or folder_name.replace("_", " ").strip()

def main():
    parser = argparse.ArgumentParser(description="High-End Cinematic 4K Photo & Video Slideshow Generator")
    parser.add_argument("source_dir", help="Path to folder containing photos and videos")
    parser.add_argument("-o", "--output", default=None, help="Output MP4 file path (defaults to source_dir/<Title>.mp4)")
    parser.add_argument("--title", default=None, help="Center title text on title slide")
    parser.add_argument("--date", default="", help="Bottom-right date text on title slide (e.g., 'Aug 2026')")
    parser.add_argument("--title-dur", type=float, default=9.0, help="Duration of title slide in seconds (default: 9.0)")
    parser.add_argument("--res", choices=["4k", "1080p"], default="4k", help="Output resolution (default: 4k)")
    parser.add_argument("--fps", type=int, default=24, help="Frame rate (default: 24)")
    parser.add_argument("--letterbox", action="store_true", help="Apply 2.39:1 anamorphic letterbox matte bars")
    parser.add_argument("--border", type=int, default=30, help="White border thickness in pixels (default: 30)")
    parser.add_argument("--margin", type=int, default=80, help="Margin around media box leaving blurred background (default: 80)")
    parser.add_argument("--shuffle", action="store_true", default=True, help="Randomly shuffle photos and videos throughout the slideshow (default: True)")
    parser.add_argument("--no-shuffle", dest="shuffle", action="store_false", help="Sort photos and videos chronologically by date")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible shuffling (default: None for fresh random selection)")
    parser.add_argument("--trim-videos", type=float, default=None, help="Trim videos to max N seconds (default: untrimmed)")
    parser.add_argument("--pilot", action="store_true", help="Render a fast 5-shot preview pilot movie")
    parser.add_argument("--pilot-shots", type=int, default=5, help="Number of content shots in pilot (default: 5)")
    parser.add_argument("--pilot-offset", type=int, default=0, help="Offset index for pilot shot selection to test different photos (default: 0)")
    parser.add_argument("--captions", default=None, help="JSON string or path to JSON file mapping filename -> caption")
    parser.add_argument("--shot-order", default=None, help="Comma-separated filenames or path to JSON/text file with shot sequence")
    parser.add_argument("--clear-cache", action="store_true", help="Clear temporary render cache before processing")
    parser.add_argument("--temp-dir", default=None, help="Custom temporary cache directory")

    args = parser.parse_args()

    source_dir = os.path.abspath(args.source_dir)
    if not os.path.isdir(source_dir):
        print(f"Error: Source directory does not exist: {source_dir}")
        sys.exit(1)

    title_center = args.title or derive_default_title(source_dir)
    title_date = args.date

    # Resolution
    if args.res == "4k":
        width, height = 3840, 2160
    else:
        width, height = 1920, 1080

    letterbox_bars = int(height * 0.128) if args.letterbox else 0

    output_file = args.output
    if not output_file:
        safe_title = "".join(c for c in title_center if c.isalnum() or c in " -_").strip()
        output_file = os.path.join(source_dir, f"{safe_title}.mp4")

    temp_dir = args.temp_dir or os.path.join(source_dir, "temp_slideshow_render")

    if args.clear_cache and os.path.exists(temp_dir):
        import shutil
        print("Clearing temporary render cache...")
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("================================================================")
    print("      CINEMATIC 4K SLIDESHOW GENERATOR")
    print("================================================================")
    print(f"Source Folder:  {source_dir}")
    print(f"Title:          {title_center} | {title_date}")
    print(f"Resolution:     {width}x{height} @ {args.fps} fps")
    print(f"Letterbox:      {'2.39:1 Anamorphic Scope' if args.letterbox else 'Full 16:9 Widescreen'}")
    print(f"Video Mode:     {'Untrimmed (Full Duration)' if args.trim_videos is None else f'Trimmed to {args.trim_videos}s'}")
    print(f"Output File:    {output_file}")
    print("================================================================\n")

    captions_map = None
    if args.captions:
        if os.path.exists(args.captions):
            import json
            with open(args.captions, "r", encoding="utf-8") as f:
                captions_map = json.load(f)
        else:
            import json
            try:
                captions_map = json.loads(args.captions)
            except Exception:
                pass
        if isinstance(captions_map, dict) and "captions" in captions_map:
            captions_map = captions_map["captions"]

    custom_order = None
    if args.shot_order:
        if os.path.exists(args.shot_order):
            import json
            try:
                with open(args.shot_order, "r", encoding="utf-8") as f:
                    custom_order = json.load(f)
            except Exception:
                with open(args.shot_order, "r", encoding="utf-8") as f:
                    custom_order = [line.strip() for line in f if line.strip()]
        else:
            custom_order = [x.strip() for x in args.shot_order.split(",") if x.strip()]
        if isinstance(custom_order, dict) and "order" in custom_order:
            custom_order = custom_order["order"]

    untrimmed = args.trim_videos is None
    timeline = timeline_builder.build_timeline(
        source_dir=source_dir,
        title_center=title_center,
        title_date=title_date,
        title_duration=args.title_dur,
        untrimmed_videos=untrimmed,
        video_max_dur=args.trim_videos or 6.0,
        seed=args.seed,
        shuffle=args.shuffle if not custom_order else False,
        captions=captions_map,
        custom_order=custom_order
    )

    if args.pilot:
        print(f"Creating Pilot Preview playlist ({args.pilot_shots} shots, shuffle={args.shuffle})...")
        pilot_shots = [timeline[0], timeline[1]]
        content_shots = [s for s in timeline[2:-1] if s.get("type") in ["photo", "video"]]

        if custom_order:
            pilot_shots.extend(content_shots[:args.pilot_shots])
        elif args.shuffle:
            portraits = [s for s in content_shots if s.get("type") == "photo" and s.get("orientation") == "portrait"]
            videos = [s for s in content_shots if s.get("type") == "video"]
            landscapes = [s for s in content_shots if s.get("type") == "photo" and s.get("orientation") == "landscape"]

            rng = random.Random(args.seed) if args.seed is not None else random.Random()

            # 1. Pick 1 random portrait if available
            if portraits:
                pilot_shots.append(rng.choice(portraits))

            # 2. Pick 1 random video if available
            if videos:
                pilot_shots.append(rng.choice(videos))

            # 3. Fill remaining slots with random landscapes without repetition
            remaining_count = max(0, (args.pilot_shots + 2) - len(pilot_shots))
            avail_landscapes = [s for s in landscapes if s not in pilot_shots]
            if avail_landscapes:
                take_count = min(remaining_count, len(avail_landscapes))
                pilot_shots.extend(rng.sample(avail_landscapes, take_count))
        else:
            portraits = [s for s in content_shots if s.get("type") == "photo" and s.get("orientation") == "portrait"]
            videos = [s for s in content_shots if s.get("type") == "video"]
            landscapes = [s for s in content_shots if s.get("type") == "photo" and s.get("orientation") == "landscape"]

            # Deterministic offset-based picking
            if portraits:
                p_idx = args.pilot_offset % len(portraits)
                pilot_shots.append(portraits[p_idx])

            if videos:
                v_idx = args.pilot_offset % len(videos)
                pilot_shots.append(videos[v_idx])

            l_start = (args.pilot_offset * 3) % len(landscapes) if landscapes else 0
            l_candidates = landscapes[l_start:] + landscapes[:l_start]
            for s in l_candidates:
                if len(pilot_shots) >= args.pilot_shots + 2:
                    break
                if s not in pilot_shots:
                    pilot_shots.append(s)

        if len(pilot_shots) > 2:
            pilot_shots[-1]["transition"] = "fadeblack"
            pilot_shots[-1]["transition_duration"] = 1.2

        pilot_shots.append(timeline[-1])
        for idx, shot in enumerate(pilot_shots):
            shot["shot_id"] = idx

        timeline = pilot_shots
        root, ext = os.path.splitext(output_file)
        suffix = f"_Pilot{args.pilot_offset + 1}" if args.pilot_offset > 0 else "_Pilot"
        output_file = f"{root}{suffix}{ext}"

    render_engine.render_movie(
        timeline=timeline,
        output_file=output_file,
        temp_dir=temp_dir,
        width=width,
        height=height,
        fps=args.fps,
        border_px=args.border,
        letterbox_bars=letterbox_bars,
        title_center=title_center,
        title_date=title_date,
        margin=args.margin
    )

if __name__ == "__main__":
    main()
