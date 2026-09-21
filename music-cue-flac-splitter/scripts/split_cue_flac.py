#!/usr/bin/env python3
"""
split_cue_flac.py - Autonomous Music CUE Splitter Agent
Scans music directories for unsplit big audio files (FLAC, APE, WAV) accompanied by CUE sheets,
losslessly splits them into individual FLAC tracks with embedded Vorbis metadata,
verifies track durations and integrity, and safely handles original image files.
"""

import os
import sys
import re
import glob
import shutil
import argparse
import subprocess
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')
    except Exception:
        pass

COMMON_FFMPEG_PATHS = [
    r"C:\Program Files\DownloadHelper CoApp\ffmpeg.exe",
    r"C:\Program Files\Subtitle Edit\ffmpeg\ffmpeg.exe",
    r"C:\Program Files\AI Video to SRT\resources\backend\bin\ffmpeg.exe",
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    r"C:\tools\ffmpeg\bin\ffmpeg.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"),
    os.path.expanduser(r"~\scoop\shims\ffmpeg.exe"),
    "ffmpeg.exe",
    "ffmpeg"
]

COMMON_FFPROBE_PATHS = [
    r"C:\Program Files\DownloadHelper CoApp\ffprobe.exe",
    r"C:\Program Files\Subtitle Edit\ffmpeg\ffprobe.exe",
    r"C:\Program Files\AI Video to SRT\resources\backend\bin\ffprobe.exe",
    r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
    r"C:\tools\ffmpeg\bin\ffprobe.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffprobe.exe"),
    os.path.expanduser(r"~\scoop\shims\ffprobe.exe"),
    "ffprobe.exe",
    "ffprobe"
]

def find_executable(name, common_paths):
    which = shutil.which(name)
    if which:
        return which
    for p in common_paths:
        if os.path.exists(p):
            return p
    return None

FFMPEG_BIN = find_executable('ffmpeg', COMMON_FFMPEG_PATHS)
FFPROBE_BIN = find_executable('ffprobe', COMMON_FFPROBE_PATHS)

def sanitize_filename(name):
    clean = re.sub(r'[<>:"/\\|?*]', '_', name)
    clean = re.sub(r'\s+', ' ', clean).strip(' .')
    return clean

def get_audio_duration(file_path, ffprobe_bin):
    if not ffprobe_bin or not os.path.exists(ffprobe_bin):
        return None
    cmd = [
        ffprobe_bin, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            return float(res.stdout.strip())
    except Exception:
        pass
    return None

def parse_cue(cue_path):
    content = None
    for enc in ['utf-8-sig', 'utf-8', 'cp1252', 'latin1']:
        try:
            with open(cue_path, 'r', encoding=enc) as f:
                content = f.read()
            break
        except Exception:
            continue
            
    if not content:
        return None

    album_info = {
        'cue_path': cue_path,
        'artist': '',
        'title': '',
        'date': '',
        'genre': '',
        'referenced_file': '',
        'tracks': []
    }

    current_track = None
    in_track = False

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        if not in_track:
            if line.startswith('REM DATE'):
                m = re.search(r'REM DATE\s+["\']?(\d+)["\']?', line, re.I)
                if m: album_info['date'] = m.group(1)
            elif line.startswith('REM GENRE'):
                m = re.search(r'REM GENRE\s+["\']?(.*?)["\']?$', line, re.I)
                if m: album_info['genre'] = m.group(1).strip('"\'')
            elif line.startswith('PERFORMER'):
                m = re.search(r'PERFORMER\s+["\']?(.*?)["\']?$', line, re.I)
                if m: album_info['artist'] = m.group(1).strip('"\'')
            elif line.startswith('TITLE'):
                m = re.search(r'TITLE\s+["\']?(.*?)["\']?$', line, re.I)
                if m: album_info['title'] = m.group(1).strip('"\'')
            elif line.startswith('FILE'):
                m = re.search(r'FILE\s+["\']?(.*?)["\']?\s+(?:WAVE|FLAC|MP3|APE)', line, re.I)
                if m: album_info['referenced_file'] = m.group(1).strip('"\'')
        
        if line.startswith('TRACK'):
            m = re.search(r'TRACK\s+(\d+)\s+AUDIO', line, re.I)
            if m:
                if current_track:
                    album_info['tracks'].append(current_track)
                in_track = True
                current_track = {
                    'number': int(m.group(1)),
                    'title': '',
                    'artist': '',
                    'index01': None,
                    'index00': None
                }
        elif in_track:
            if line.startswith('TITLE'):
                m = re.search(r'TITLE\s+["\']?(.*?)["\']?$', line, re.I)
                if m:
                    t_title = m.group(1).strip('"\'')
                    t_title = re.sub(r'^\d{1,2}[\.\s\-]+\s*', '', t_title)
                    current_track['title'] = t_title
            elif line.startswith('PERFORMER'):
                m = re.search(r'PERFORMER\s+["\']?(.*?)["\']?$', line, re.I)
                if m:
                    current_track['artist'] = m.group(1).strip('"\'')
            elif line.startswith('INDEX 01'):
                m = re.search(r'INDEX 01\s+(\d+):(\d+):(\d+)', line, re.I)
                if m:
                    mm, ss, ff = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    current_track['index01'] = mm * 60.0 + ss + (ff / 75.0)
            elif line.startswith('INDEX 00'):
                m = re.search(r'INDEX 00\s+(\d+):(\d+):(\d+)', line, re.I)
                if m:
                    mm, ss, ff = int(m.group(1)), int(m.group(2)), int(m.group(3))
                    current_track['index00'] = mm * 60.0 + ss + (ff / 75.0)

    if current_track:
        album_info['tracks'].append(current_track)

    return album_info

def process_album_folder(folder_path, ffmpeg_bin, ffprobe_bin, dry_run=False, original_action='archive'):
    cues = glob.glob(os.path.join(folder_path, "*.cue"))
    if not cues:
        return 'no_cue'

    best_cue = None
    for c in cues:
        if c.lower().endswith('.flac.cue'):
            best_cue = c
            break
    if not best_cue:
        best_cue = cues[0]

    cue_data = parse_cue(best_cue)
    if not cue_data or not cue_data['tracks']:
        return 'invalid_cue'

    total_tracks = len(cue_data['tracks'])
    if total_tracks <= 1:
        return 'single_track_cue'

    audio_files = []
    for ext in ['*.flac', '*.ape', '*.wav']:
        for f in glob.glob(os.path.join(folder_path, ext)):
            if not os.path.basename(f).startswith('_') and '_original_unsplit' not in f:
                audio_files.append(f)

    flac_files = [f for f in audio_files if f.lower().endswith('.flac')]
    if len(flac_files) >= total_tracks:
        return 'already_split'

    big_audio = None
    ref_base = os.path.splitext(cue_data['referenced_file'])[0].lower() if cue_data['referenced_file'] else ""
    for f in audio_files:
        f_base = os.path.splitext(os.path.basename(f))[0].lower()
        if ref_base and (ref_base == f_base or f_base in ref_base or ref_base in f_base):
            big_audio = f
            break
    if not big_audio and len(audio_files) == 1:
        big_audio = audio_files[0]

    if not big_audio or not os.path.exists(big_audio):
        return 'no_big_audio'

    total_duration = get_audio_duration(big_audio, ffprobe_bin)
    if not total_duration:
        return 'duration_failed'

    size_mb = os.path.getsize(big_audio) / 1024 / 1024
    print(f"\n{'='*70}")
    print(f"Folder: {folder_path}")
    print(f"Source: {os.path.basename(big_audio)} ({size_mb:.2f} MB, {total_duration:.2f}s)")
    print(f"CUE:    {os.path.basename(best_cue)} ({total_tracks} tracks)")
    print(f"Album:  {cue_data['artist']} - {cue_data['title']} ({cue_data['date']})")
    print(f"{'='*70}")

    created_tracks = []
    for i, track in enumerate(cue_data['tracks']):
        track_num = track['number']
        start_sec = track['index01']
        if start_sec is None:
            print(f"  [-] Track {track_num} missing INDEX 01. Aborting album.")
            return 'missing_index'

        if i + 1 < total_tracks:
            next_start = cue_data['tracks'][i + 1]['index01']
            end_sec = next_start
        else:
            end_sec = total_duration

        track_artist = track['artist'] or cue_data['artist']
        track_title = track['title'] or f"Track {track_num:02d}"
        clean_title = sanitize_filename(track_title)
        
        out_filename = f"{track_num:02d} - {clean_title}.flac"
        out_path = os.path.join(folder_path, out_filename)

        print(f"  Track {track_num:02d}/{total_tracks:02d}: [{start_sec:07.2f} -> {end_sec:07.2f}] '{track_title}' -> {out_filename}")

        if dry_run:
            continue

        cmd = [
            ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{start_sec:.6f}",
            "-to", f"{end_sec:.6f}",
            "-i", big_audio,
            "-c:a", "flac",
            "-metadata", f"title={track_title}",
            "-metadata", f"artist={track_artist}",
            "-metadata", f"album_artist={cue_data['artist']}",
            "-metadata", f"album={cue_data['title']}",
            "-metadata", f"track={track_num}/{total_tracks}",
            "-metadata", f"date={cue_data['date']}",
            "-metadata", f"genre={cue_data['genre']}",
            out_path
        ]

        res = subprocess.run(cmd)
        if res.returncode != 0 or not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
            print(f"  [-] Failed to extract track {track_num}!")
            return 'track_extract_failed'

        created_tracks.append(out_path)

    if dry_run:
        return 'dry_run_success'

    split_duration_sum = 0.0
    for t_file in created_tracks:
        sz = os.path.getsize(t_file)
        dur = get_audio_duration(t_file, ffprobe_bin) or 0.0
        split_duration_sum += dur
        if sz < 10000 or dur < 1.0:
            print(f"  [-] Track suspiciously small/short: {t_file}")
            return 'track_corrupt'

    dur_diff = abs(split_duration_sum - total_duration)
    print(f"  [+] Verified {len(created_tracks)} tracks. Total duration: {split_duration_sum:.2f}s (Diff: {dur_diff:.2f}s)")

    if original_action == 'delete':
        print(f"  [+] Deleting original big file: {os.path.basename(big_audio)}")
        os.remove(big_audio)
    elif original_action == 'archive':
        archive_dir = os.path.join(folder_path, "_original_unsplit")
        os.makedirs(archive_dir, exist_ok=True)
        dest = os.path.join(archive_dir, os.path.basename(big_audio))
        print(f"  [+] Archiving original big file to: {dest}")
        shutil.move(big_audio, dest)
    else:
        print(f"  [*] Preserving original big file in place: {os.path.basename(big_audio)}")

    print(f"[SUCCESS] {cue_data['title']} split into {total_tracks} tracks.")
    return 'success'

def main():
    parser = argparse.ArgumentParser(description="Autonomous Music CUE Splitter Agent")
    parser.add_argument('path', help="Directory or album folder to scan")
    parser.add_argument('--dry-run', action='store_true', help="Preview operations without writing audio files")
    parser.add_argument('--delete-originals', action='store_true', help="Delete original big files after split and verification")
    parser.add_argument('--keep-originals', action='store_true', help="Keep original big files in place alongside split tracks")
    parser.add_argument('--ffmpeg', default=FFMPEG_BIN, help="Custom path to ffmpeg executable")
    parser.add_argument('--ffprobe', default=FFPROBE_BIN, help="Custom path to ffprobe executable")

    args = parser.parse_args()

    if not args.ffmpeg or not os.path.exists(args.ffmpeg):
        print("[-] ffmpeg executable not found. Please specify with --ffmpeg <PATH>")
        sys.exit(1)
    if not args.ffprobe or not os.path.exists(args.ffprobe):
        print("[-] ffprobe executable not found. Please specify with --ffprobe <PATH>")
        sys.exit(1)

    target_path = os.path.abspath(args.path)
    if not os.path.exists(target_path):
        print(f"[-] Target path does not exist: {target_path}")
        sys.exit(1)

    if args.delete_originals:
        orig_action = 'delete'
    elif args.keep_originals:
        orig_action = 'keep'
    else:
        orig_action = 'archive'

    candidate_folders = set()
    for root, dirs, files in os.walk(target_path):
        if any(f.lower().endswith('.cue') for f in files):
            candidate_folders.add(root)

    print(f"Found {len(candidate_folders)} folders containing CUE files in {target_path}")

    stats = {
        'success': 0,
        'dry_run_success': 0,
        'already_split': 0,
        'no_big_audio': 0,
        'skipped': 0,
        'failed': 0
    }

    for folder in sorted(candidate_folders):
        res = process_album_folder(folder, args.ffmpeg, args.ffprobe, dry_run=args.dry_run, original_action=orig_action)
        if res in ('success', 'dry_run_success'):
            stats[res] += 1
        elif res == 'already_split':
            stats['already_split'] += 1
        elif res in ('no_big_audio', 'no_cue', 'single_track_cue'):
            stats['no_big_audio'] += 1
        else:
            stats['failed'] += 1

    print(f"\n{'='*70}")
    print("SUMMARY:")
    print(f"  Successfully split: {stats['success'] + stats['dry_run_success']}")
    print(f"  Already split:      {stats['already_split']}")
    print(f"  No big file / Skip: {stats['no_big_audio']}")
    print(f"  Failed:             {stats['failed']}")
    print(f"{'='*70}")

if __name__ == '__main__':
    main()
