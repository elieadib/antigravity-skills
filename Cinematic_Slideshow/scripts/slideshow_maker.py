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
    parser.add_argument("--trim-videos", type=float, default=None, help="Trim videos to max N seconds (default: untrimmed)")
    parser.add_argument("--pilot", action="store_true", help="Render a fast 5-shot preview pilot movie")
    parser.add_argument("--pilot-shots", type=int, default=5, help="Number of content shots in pilot (default: 5)")
    parser.add_argument("--pilot-offset", type=int, default=0, help="Offset index for pilot shot selection to test different photos (default: 0)")
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

    untrimmed = args.trim_videos is None
    timeline = timeline_builder.build_timeline(
        source_dir=source_dir,
        title_center=title_center,
        title_date=title_date,
        title_duration=args.title_dur,
        untrimmed_videos=untrimmed,
        video_max_dur=args.trim_videos or 6.0
    )

    if args.pilot:
        print(f"Creating Pilot Preview playlist ({args.pilot_shots} shots, offset={args.pilot_offset})...")
        pilot_shots = [timeline[0], timeline[1]]
        content_shots = [s for s in timeline[2:-1] if s.get("type") in ["photo", "video"]]
        portraits = [s for s in content_shots if s.get("type") == "photo" and s.get("orientation") == "portrait"]
        videos = [s for s in content_shots if s.get("type") == "video"]
        landscapes = [s for s in content_shots if s.get("type") == "photo" and s.get("orientation") == "landscape"]

        # 1. Prioritize 1 portrait photo (using offset)
        if portraits:
            p_idx = args.pilot_offset % len(portraits)
            pilot_shots.append(portraits[p_idx])

        # 2. Prioritize 1 video (if present)
        if videos:
            v_idx = args.pilot_offset % len(videos)
            pilot_shots.append(videos[v_idx])

        # 3. Fill remaining slots with landscapes starting from offset * 3
        l_start = (args.pilot_offset * 3) % len(landscapes) if landscapes else 0
        l_candidates = landscapes[l_start:] + landscapes[:l_start]
        for s in l_candidates:
            if len(pilot_shots) >= args.pilot_shots + 1:
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
