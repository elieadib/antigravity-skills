#!/usr/bin/env python3
"""
ai_music_splitting_curation.py - Automated AI Music Full-Album Splitting & Curation Pipeline

Processes full-length audio albums (.m4a, .mp3, .flac) or single tracks:
1. Cleans and simplifies album titles by removing YouTube/marketing fluff.
2. Discovers matching official YouTube release using yt-dlp.
3. Extracts tracklists and start times from chapters or description timestamps.
4. Downloads high-res thumbnail and applies smart square cropping for album cover art.
5. Performs sample-accurate silence detection around transitions to refine cut points.
6. Transcodes each track to 128 kb/s MP3 with libmp3lame, complete ID3 tags, and embedded cover art.
7. Organizes into dedicated album folders with <Album>.png and cleans up temporary/source files.
"""

import os
import sys
import argparse
import subprocess
import json
import re
import shutil
import time
from pathlib import Path

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def find_executable(name, extra_paths=None):
    """Finds an executable across system PATH and common installation paths."""
    found = shutil.which(name)
    if found:
        return found
    
    candidates = extra_paths or []
    if sys.platform == "darwin":
        candidates.extend([
            f"/opt/homebrew/bin/{name}",
            f"/usr/local/bin/{name}",
            f"/opt/homebrew/Caskroom/miniconda/base/bin/{name}",
            os.path.expanduser(f"~/miniconda3/bin/{name}"),
            os.path.expanduser(f"~/anaconda3/bin/{name}"),
        ])
    elif sys.platform == "win32":
        candidates.extend([
            rf"C:\ProgramData\chocolatey\bin\{name}.exe",
            rf"C:\ffmpeg\bin\{name}.exe",
            os.path.expanduser(rf"~\AppData\Local\Microsoft\WinGet\Links\{name}.exe"),
            os.path.expanduser(rf"~\miniconda3\Scripts\{name}.exe"),
            os.path.expanduser(rf"~\anaconda3\Scripts\{name}.exe"),
        ])
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None

FFMPEG = find_executable("ffmpeg")
FFPROBE = find_executable("ffprobe")
YT_DLP = find_executable("yt-dlp")

def clean_album_name(raw_name):
    """Strips YouTube video fluff, years, and marketing text to extract clean album title."""
    s = re.sub(r'\.(m4a|mp3|flac|wav|aac)$', '', raw_name, flags=re.I)
    
    # Specific known overrides
    if 'Velvet Static' in s and 'Pacific Blondes' in s:
        return 'Pacific Blondes - Velvet Static'
    if 'Mushroom Music' in s and 'Psychedelic Treehouse' in s:
        return 'Mushroom Music - Psychedelic Treehouse'
    if 'Canyon Ledger' in s:
        return 'Canyon Ledger - Pages from the Quiet Road'
    if 'Beyond the Sleeping Woods' in s:
        return 'Beyond the Sleeping Woods'
    if 'Joshua Echoes' in s:
        return 'Joshua Echoes - The Iron Horizon'
    if 'Northbound Ash' in s:
        return 'Northbound Ash – Weathered Maps'
    if 'OVERDOSE' in s:
        return 'OVERDOSE - Alone'
    if 'Cosmic Soul' in s:
        return 'Cosmic Soul – The Ego Trip Experience'
    if 'THE AGE OF UNREAL' in s:
        return 'THE AGE OF UNREAL'
    if 'The Horizon Still Calls' in s:
        return 'The Horizon Still Calls · Desert Drift'
    if 'The Valley' in s:
        return 'The Valley'
    
    # General patterns
    s = re.sub(r'\[Full Album\]', '', s, flags=re.I)
    s = re.sub(r'\(Full Album\s*\+?\s*LYRICS?\)', '', s, flags=re.I)
    s = re.sub(r'\(Full Album\)', '', s, flags=re.I)
    s = re.sub(r'\(FULL ALBUM\)', '', s, flags=re.I)
    s = re.sub(r'—\s*Full Album\s*\[\d{4}\]', '', s, flags=re.I)
    s = re.sub(r'—\s*Full Album\s*\(\d{4}\)', '', s, flags=re.I)
    s = re.sub(r'•\s*Full Album', '', s, flags=re.I)
    s = re.sub(r'\(vintage progressive rock.*?\)', '', s, flags=re.I)
    s = re.sub(r'\(70s Psychedelic Stoner Space Rock\)', '', s, flags=re.I)
    s = re.sub(r'\(Deluxe Edition\)\s*\(\d{4}\)', '', s, flags=re.I)
    s = re.sub(r'\(\d{4}\)', '', s, flags=re.I)
    s = re.sub(r'19\d{2}s?\s+Trippy Blues\s*-\s*', '', s, flags=re.I)
    s = re.sub(r'19\d{2}\s+Progressive Rock\s*', '', s, flags=re.I)
    s = re.sub(r'19\d{2}\s+Cinematic Psychedelic Rock\s*•?\s*', '', s, flags=re.I)
    s = re.sub(r'19\d{2}\s+Haunting Psychedelic Rock\s*-\s*', '', s, flags=re.I)
    s = re.sub(r'Progressive Rock Album from \d{4}\s*', '', s, flags=re.I)
    s = re.sub(r'19\d{2}s?\s+Progressive Psychedelic Rock inspired Concept Album', '', s, flags=re.I)
    s = re.sub(r'Lost\s+\d{2}s?\s+.*?Album', '', s, flags=re.I)
    s = re.sub(r'Lost\s+\d{4}\s+.*?Album', '', s, flags=re.I)
    s = re.sub(r'\d{4}\s+Vintage\s+.*?Album', '', s, flags=re.I)
    s = re.sub(r'\d{2}s?\s+Psychedelic\s+Space Rock Music', '', s, flags=re.I)
    s = re.sub(r'Psychedelic\s+Progressive Rock for Deep Reflection', '', s, flags=re.I)
    s = re.sub(r'Psychedelic\s+Folk Rock', '', s, flags=re.I)
    s = re.sub(r'Psychedelic\s+Stoner\s+Acid Rock', '', s, flags=re.I)
    s = re.sub(r'Psychedelic\s+Stoner Folk', '', s, flags=re.I)
    s = re.sub(r'Atmospheric\s+Psychedelic Ambient Rock', '', s, flags=re.I)
    s = re.sub(r'Psychedelic\s+Ambient Rock', '', s, flags=re.I)
    s = re.sub(r'Psychedelic\s+Southern\s+Folk Rock', '', s, flags=re.I)
    s = re.sub(r'Atmospheric\s+Stoner Folk', '', s, flags=re.I)
    s = re.sub(r'Brazilian Psychedelic Progressive Rock', '', s, flags=re.I)
    s = re.sub(r'Heavy Psychedelic Rock', '', s, flags=re.I)
    s = re.sub(r'1968 Blues Rock', '', s, flags=re.I)
    s = re.sub(r'70s Folk Rock', '', s, flags=re.I)
    s = re.sub(r'70s Psychedelic Music Vintage Sound', '', s, flags=re.I)
    s = re.sub(r'Psychedelic Rock\s*-\s*', '', s, flags=re.I)
    s = re.sub(r'Progressive Rock', '', s, flags=re.I)
    s = re.sub(r'Debut Album\s+AI Music Project', '', s, flags=re.I)
    s = re.sub(r'A Lost Masterpiece of \x27?70s Rock', '', s, flags=re.I)
    s = re.sub(r'Atmospheric Progressive Rock Journey Through a Forgotten Dream', '', s, flags=re.I)
    s = re.sub(r'Cinematic Rock\s+Heartland Rock', '', s, flags=re.I)
    s = re.sub(r'1978 Progressive Atmospheric Rock', '', s, flags=re.I)
    s = re.sub(r'•', ' ', s)
    s = re.sub(r'｜', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip(' -–•|')
    return s

def smart_crop_square(orig_img_path, dest_img_path):
    """Crops rectangular YouTube thumbnails into clean square album covers."""
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        # Fallback to ffmpeg center crop if PIL is not installed
        subprocess.run([
            FFMPEG, "-y", "-i", orig_img_path,
            "-vf", "crop=min(iw\\,ih):min(iw\\,ih)",
            dest_img_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return

    im = Image.open(orig_img_path).convert('RGB')
    w, h = im.size
    if w == h:
        im.save(dest_img_path)
        return
    
    if w > h:
        arr = np.array(im)
        grad_x = np.abs(arr[:, 1:, :] - arr[:, :-1, :]).sum(axis=2)
        # Check top-left energy
        tl_energy = grad_x[10:min(150, h-10), 10:min(200, w-10)].mean() if w > 700 else 0
        if tl_energy > 40:
            best_x = 0
        else:
            if w >= 800 and h >= 500:
                left_profile = grad_x[100:h-100, 140:260].mean(axis=0)
                peak_idx = int(np.argmax(left_profile)) + 140
                if left_profile.max() > 40:
                    sleeve_center = peak_idx + int(0.41 * h)
                    best_x = max(0, min(w - h, sleeve_center - h // 2))
                else:
                    best_x = (w - h) // 2
            else:
                best_x = (w - h) // 2
        cropped = im.crop((best_x, 0, best_x + h, h))
    else:
        best_y = (h - w) // 2
        cropped = im.crop((0, best_y, w, best_y + w))
        
    cropped.save(dest_img_path)

def process_album(src_file, target_dir, args):
    raw_fn = os.path.basename(src_file)
    sim_name = clean_album_name(raw_fn)
    print(f"\n==================================================")
    print(f"Processing: {sim_name}")
    print(f"  Source File: {raw_fn}")
    
    if args.dry_run:
        print("  [DRY-RUN] Would process album, search YouTube, and split tracks.")
        return True

    work_dir = Path("/tmp") / f"curation_{abs(hash(sim_name)) % 100000}"
    work_dir.mkdir(parents=True, exist_ok=True)
    local_audio = work_dir / "audio.m4a"

    try:
        # Step 1: Copy to local fast storage
        print("  Step 1: Staging audio file...")
        shutil.copyfile(src_file, local_audio)

        # Measure duration
        probe = subprocess.run([
            FFPROBE, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(local_audio)
        ], capture_output=True, text=True, check=True)
        total_dur = float(probe.stdout.strip())
        print(f"  Audio duration: {total_dur:.2f}s ({int(total_dur//60)}m {total_dur%60:.1f}s)")

        # Step 2: Query YouTube
        print(f"  Step 2: Querying YouTube for '{sim_name}'...")
        cmd_yt = [YT_DLP, f"ytsearch1:{sim_name}", "-j", "--skip-download"]
        res_yt = subprocess.run(cmd_yt, capture_output=True, text=True)
        yt_data = {}
        if res_yt.returncode == 0 and res_yt.stdout.strip():
            try:
                yt_data = json.loads(res_yt.stdout.strip().splitlines()[0])
            except Exception:
                pass

        video_id = yt_data.get("id")
        artist = yt_data.get("uploader") or yt_data.get("channel") or "Various Artists"
        print(f"  Matched Release: '{yt_data.get('title', sim_name)}' (Artist: {artist})")

        # Step 3: Extract Tracklist
        tracks = []
        if total_dur < 480.0:
            clean_title = re.sub(r'\s*\(.*?\)', '', sim_name)
            clean_title = re.sub(r'Official Music Video\s*-\s*', '', clean_title, flags=re.I).strip(' -–')
            tracks.append({"start": 0.0, "title": clean_title})
            print(f"  Single-track item: '{clean_title}'")
        elif yt_data.get("chapters") and len(yt_data["chapters"]) >= 2:
            for c in yt_data["chapters"]:
                tracks.append({"start": float(c["start_time"]), "title": c["title"].strip()})
            print(f"  Loaded {len(tracks)} tracks from YouTube chapters.")
        else:
            desc = yt_data.get("description", "")
            for line in desc.splitlines():
                m = re.search(r'(?:\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?)\s*[-–—:]?\s*(.+)', line)
                if m:
                    ts_str, t_name = m.group(1), m.group(2).strip()
                    if len(t_name) > 1 and not any(kw in t_name.lower() for kw in ['subscribe', 'http', 'album', 'listen', 'spotify', 'apple']):
                        parts = [int(p) for p in ts_str.split(':')]
                        sec = parts[0]*60 + parts[1] if len(parts)==2 else parts[0]*3600 + parts[1]*60 + parts[2]
                        tracks.append({"start": float(sec), "title": t_name})
            tracks = sorted(tracks, key=lambda x: x["start"])
            if len(tracks) >= 2:
                print(f"  Extracted {len(tracks)} tracks from description.")
            else:
                print("  Detecting tracks via silence analysis...")
                cmd_sil = [
                    FFMPEG, "-i", str(local_audio), "-af", "silencedetect=noise=-20dB:d=0.3",
                    "-f", "null", "-"
                ]
                res_sil = subprocess.run(cmd_sil, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
                detected = [0.0]
                for l in res_sil.stderr.splitlines():
                    if "silence_end:" in l:
                        m = re.search(r"silence_end:\s*([\d\.]+)\s*\|\s*silence_duration:\s*([\d\.]+)", l)
                        if m:
                            end_t, dur_s = float(m.group(1)), float(m.group(2))
                            mid_t = end_t - (dur_s / 2.0)
                            if mid_t > detected[-1] + 90.0 and mid_t < total_dur - 45.0:
                                detected.append(round(mid_t, 2))
                for i, st in enumerate(detected):
                    tracks.append({"start": st, "title": f"{sim_name} (Part {i+1})"})
                print(f"  Silence detection generated {len(tracks)} tracks.")

        # Clean track titles
        for t in tracks:
            t["title"] = re.sub(r'^Track\s*\d+\s*[-–—:]\s*', '', t["title"], flags=re.I)
            t["title"] = re.sub(r'^\d+[\.\s-]+\s*', '', t["title"])
            t["title"] = t["title"].strip(' -–"\'')
            if not t["title"]:
                t["title"] = f"Track {len(tracks)}"

        # Step 4: Download and crop cover art
        cover_png = work_dir / f"{sim_name}.png"
        if video_id:
            thumb_base = work_dir / "thumb"
            subprocess.run([
                YT_DLP, "--write-thumbnail", "--skip-download", "--convert-thumbnails", "png",
                "-o", str(thumb_base), f"https://www.youtube.com/watch?v={video_id}"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            orig_png = work_dir / "thumb.png"
            if orig_png.exists():
                smart_crop_square(str(orig_png), str(cover_png))
                print("  Extracted and cropped square cover art.")

        if not cover_png.exists():
            from PIL import Image
            im = Image.new('RGB', (700, 700), color=(25, 25, 30))
            im.save(str(cover_png))

        # Step 5: Refine silence boundaries
        print("  Step 4: Refining silence boundaries...")
        split_points = [0.0]
        for i in range(1, len(tracks)):
            t = tracks[i]["start"]
            cmd_silence = [
                FFMPEG, "-ss", str(max(0, t - 10)), "-to", str(min(total_dur, t + 10)),
                "-i", str(local_audio), "-af", "silencedetect=noise=-20dB:d=0.2",
                "-f", "null", "-"
            ]
            res_sil = subprocess.run(cmd_silence, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
            silences = []
            for line in res_sil.stderr.splitlines():
                if "silence_start:" in line:
                    m = re.search(r"silence_start:\s*([\d\.]+)", line)
                    if m: silences.append({"start": float(m.group(1))})
                elif "silence_end:" in line:
                    m = re.search(r"silence_end:\s*([\d\.]+)\s*\|\s*silence_duration:\s*([\d\.]+)", line)
                    if m and silences and "end" not in silences[-1]:
                        silences[-1]["end"] = float(m.group(1))
                        silences[-1]["dur"] = float(m.group(2))
            offset = max(0, t - 10)
            if silences:
                best = min(silences, key=lambda s: abs((s["start"] + s.get("end", s["start"]))/2 - 10.0))
                mid = (best["start"] + best.get("end", best["start"])) / 2.0 + offset
                split_points.append(round(mid, 2))
            else:
                split_points.append(round(t, 2))
        split_points.append(round(total_dur, 2))

        # Step 6: Encode MP3s
        print(f"  Step 5: Encoding {len(tracks)} tracks to {args.bitrate} MP3...")
        created_mp3s = []
        total_t = len(tracks)
        for i in range(total_t):
            t_num = i + 1
            st, en = split_points[i], split_points[i+1]
            title = tracks[i]["title"]
            mp3_fn = f"{sim_name}_Track{t_num:02d}.mp3"
            mp3_path = work_dir / mp3_fn

            cmd_enc = [
                FFMPEG, "-y",
                "-ss", str(st), "-to", str(en),
                "-i", str(local_audio),
                "-i", str(cover_png),
                "-map", "0:a", "-map", "1:0",
                "-c:a", "libmp3lame", "-b:a", args.bitrate,
                "-ar", str(args.sample_rate),
                "-c:v:0", "copy",
                "-id3v2_version", "3",
                "-metadata:s:v", "title=Album cover",
                "-metadata:s:v", "comment=Cover (front)",
                "-metadata", f"title={title}",
                "-metadata", f"artist={artist}",
                "-metadata", f"album={sim_name}",
                "-metadata", f"track={t_num}/{total_t}",
                str(mp3_path)
            ]
            subprocess.run(cmd_enc, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            sz_mb = mp3_path.stat().st_size / (1024*1024)
            created_mp3s.append((mp3_path, title, sz_mb))
            print(f"    Track {t_num:02d}/{total_t:02d}: {title[:35]:35s} | {sz_mb:5.2f} MB")

        # Step 7: Move to Destination Directory
        dest_dir = Path(target_dir) / sim_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Step 6: Moving assets to {dest_dir}...")
        for mp3_p, _, _ in created_mp3s:
            shutil.move(str(mp3_p), str(dest_dir / mp3_p.name))
        shutil.copyfile(str(cover_png), str(dest_dir / f"{sim_name}.png"))

        # Step 8: Clean up source files
        if not args.keep_source:
            if os.path.exists(src_file):
                os.remove(src_file)
                print(f"    Removed source file: {raw_fn}")
            for cand in [f"{sim_name}.mp3", f"{raw_fn[:-4]}.mp3"]:
                cand_p = Path(target_dir) / cand
                if cand_p.exists():
                    cand_p.unlink()

        print(f"  SUCCESS: {sim_name} completed successfully!\n")
        return True

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

def main():
    parser = argparse.ArgumentParser(
        description="AI_Music_Splitting_Curation: Automated Full-Album Splitting, MP3 Conversion & Curation Pipeline"
    )
    parser.add_argument("path", nargs="?", default=".", help="Target folder containing audio files or individual file")
    parser.add_argument("-b", "--bitrate", default="128k", help="MP3 audio bitrate (default: 128k)")
    parser.add_argument("-r", "--sample-rate", type=int, default=44100, help="Audio sample rate (default: 44100)")
    parser.add_argument("--keep-source", action="store_true", help="Keep source audio files after processing")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Preview proposed actions without modifying files")
    args = parser.parse_args()

    if not FFMPEG or not FFPROBE:
        sys.exit("Error: ffmpeg and ffprobe are required. Please install them or ensure they are on PATH.")
    if not YT_DLP:
        sys.exit("Error: yt-dlp is required. Please install yt-dlp or ensure it is on PATH.")

    target = Path(args.path).resolve()
    if target.is_file():
        files = [target]
        base_dir = target.parent
    elif target.is_dir():
        files = sorted([p for p in target.iterdir() if p.suffix.lower() in ['.m4a', '.mp3', '.flac']])
        base_dir = target
    else:
        sys.exit(f"Error: Target path does not exist: {target}")

    print(f"==================================================")
    print(f"AI MUSIC SPLITTING & CURATION PIPELINE")
    print(f"Target Directory: {base_dir}")
    print(f"Target Bitrate:   {args.bitrate}")
    print(f"Audio Files:      {len(files)}")
    print(f"Mode:             {'DRY-RUN (Simulating)' if args.dry_run else 'ACTIVE'}")
    print(f"==================================================")

    for idx, f in enumerate(files, 1):
        try:
            process_album(str(f), str(base_dir), args)
        except Exception as e:
            print(f"Error processing {f.name}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
