#!/usr/bin/env python3
"""
before_the_move_to_jf.py - Before the Move to JF (Jellyfin) Organization Agent Script

Standardizes movie video files and matching subtitles (.srt) inside subfolders to
"Movie Name - Release Year", moves them to the parent or target folder, and safely
deletes the emptied source folders and residual torrent assets before transfer to Jellyfin.
"""

import os
import sys
import io
import re
import stat
import shutil
import argparse
from typing import Optional, Tuple, List, Dict

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".m4v", ".webm", ".ts"}
SUBTITLE_EXTENSIONS = {".srt"}


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num_bytes) < 1024.0 or unit == "TB":
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"


def clean_title_string(raw_title: str) -> str:
    """Clean scene characters (dots, underscores) and normalize whitespace."""
    title = re.sub(r"[._]", " ", raw_title)
    title = title.strip(" -.")
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def parse_movie_name_and_year(name: str) -> Optional[Tuple[str, str]]:
    """
    Extract Movie Name and 4-digit Year from folder or file name.
    Supports:
      - 'Movie Name (2026) [1080p]...'
      - 'Movie Name (2026)'
      - 'Movie.Name.2026.1080p.WEBRip...'
      - 'Movie Name - 2026'
    """
    # 1. Check parenthesized year: 'Title (YYYY)'
    m = re.match(r"^(.+?)\s*\((\d{4})\)", name)
    if m:
        title = clean_title_string(m.group(1))
        year = m.group(2)
        if title:
            return title, year

    # 2. Check scene format: 'Title.YYYY.' or 'Title YYYY '
    m = re.match(r"^(.+?)[._ -]+((?:19|20)\d{2})(?:[._ -]+.*)?$", name, re.IGNORECASE)
    if m:
        title = clean_title_string(m.group(1))
        year = m.group(2)
        if title and not re.match(r"^\d+$", title):
            return title, year

    return None


def force_remove_path(path: str) -> None:
    """Remove a file or directory tree, clearing read-only attributes if needed."""
    def on_error(func, p, exc_info):
        try:
            os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
            func(p)
        except Exception:
            pass

    if os.path.isdir(path):
        shutil.rmtree(path, onerror=on_error)
    elif os.path.isfile(path):
        try:
            os.remove(path)
        except PermissionError:
            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
            os.remove(path)


def find_matching_subtitle(folder_path: str, video_path: str) -> Optional[str]:
    """Find primary matching srt subtitle in the folder or Subs subdirectory."""
    video_stem = os.path.splitext(os.path.basename(video_path))[0]
    
    # Check directly in the folder for exact base match
    direct_exact = os.path.join(folder_path, f"{video_stem}.srt")
    if os.path.isfile(direct_exact):
        return direct_exact

    # Check for any .srt directly in the folder
    direct_srts = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f)) and f.lower().endswith(".srt")
    ]
    if len(direct_srts) == 1:
        return direct_srts[0]
    elif len(direct_srts) > 1:
        for s in direct_srts:
            if "eng" in s.lower():
                return s
        return direct_srts[0]

    # Check Subs/ or Subtitles/ directory if direct srt was not found
    for sub_dir_name in ["Subs", "subs", "Subtitles", "subtitles"]:
        sub_dir = os.path.join(folder_path, sub_dir_name)
        if os.path.isdir(sub_dir):
            sub_files = [
                os.path.join(sub_dir, f)
                for f in os.listdir(sub_dir)
                if os.path.isfile(os.path.join(sub_dir, f)) and f.lower().endswith(".srt")
            ]
            for s in sub_files:
                basename = os.path.basename(s).lower()
                if basename in ["english.srt", "eng.srt", "en.srt", "sdh.eng.srt"]:
                    return s
            if sub_files:
                return sub_files[0]

    return None


def organize_movies(
    root_dir: str,
    target_dir: Optional[str] = None,
    dry_run: bool = False,
    delete_source: bool = True,
    clean_loose: bool = True,
    verbose: bool = False,
) -> Dict:
    """
    Main organization workflow.
    """
    if not os.path.isdir(root_dir):
        raise FileNotFoundError(f"Root directory not found: {root_dir}")

    dest_dir = target_dir if target_dir else root_dir
    os.makedirs(dest_dir, exist_ok=True)

    stats = {
        "folders_processed": 0,
        "folders_skipped": 0,
        "videos_moved": 0,
        "subtitles_moved": 0,
        "loose_videos_renamed": 0,
        "folders_deleted": 0,
        "bytes_moved": 0,
        "errors": [],
    }

    subdirs = [
        d for d in os.listdir(root_dir)
        if os.path.isdir(os.path.join(root_dir, d))
    ]

    movie_candidates = []
    for d in subdirs:
        folder_path = os.path.join(root_dir, d)
        
        videos = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, f))
            and os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS
        ]
        
        if not videos:
            if verbose:
                print(f"[SKIP] No video files in folder: {d}")
            stats["folders_skipped"] += 1
            continue

        info = parse_movie_name_and_year(d)
        if not info:
            info = parse_movie_name_and_year(os.path.basename(videos[0]))

        if not info:
            print(f"[WARN] Could not parse title/year for folder: {d}")
            stats["folders_skipped"] += 1
            continue

        title, year = info
        main_video = videos[0]
        srt = find_matching_subtitle(folder_path, main_video)

        movie_candidates.append({
            "folder_name": d,
            "folder_path": folder_path,
            "title": title,
            "year": year,
            "video_path": main_video,
            "srt_path": srt,
        })

    grouped: Dict[Tuple[str, str], List[Dict]] = {}
    for item in movie_candidates:
        key = (item["title"].lower(), item["year"])
        grouped.setdefault(key, []).append(item)

    for key, items in grouped.items():
        if len(items) == 1:
            items[0]["target_base"] = f"{items[0]['title']} - {items[0]['year']}"
        else:
            for it in items:
                fname = it["folder_name"].lower()
                if "x265" in fname or "hevc" in fname:
                    it["target_base"] = f"{it['title']} - {it['year']}"
                elif "x264" in fname:
                    it["target_base"] = f"{it['title']} - {it['year']} [x264]"
                elif "720p" in fname:
                    it["target_base"] = f"{it['title']} - {it['year']} [720p]"
                else:
                    it["target_base"] = f"{it['title']} - {it['year']} [alt]"

    for item in movie_candidates:
        base_name = item["target_base"]
        video_src = item["video_path"]
        video_ext = os.path.splitext(video_src)[1]
        video_dst = os.path.join(dest_dir, f"{base_name}{video_ext}")

        srt_src = item["srt_path"]
        srt_dst = os.path.join(dest_dir, f"{base_name}.srt") if srt_src else None

        v_size = os.path.getsize(video_src)
        s_size = os.path.getsize(srt_src) if srt_src else 0

        print(f"\n--- Processing: {item['folder_name']} ---")
        print(f"  Target Video: {os.path.basename(video_dst)} ({format_bytes(v_size)})")
        if srt_src:
            print(f"  Target Subtitle: {os.path.basename(srt_dst)} ({format_bytes(s_size)})")
        else:
            print(f"  Target Subtitle: None")

        if dry_run:
            stats["folders_processed"] += 1
            stats["videos_moved"] += 1
            stats["bytes_moved"] += v_size
            if srt_src:
                stats["subtitles_moved"] += 1
                stats["bytes_moved"] += s_size
            if delete_source:
                stats["folders_deleted"] += 1
            continue

        try:
            if os.path.exists(video_dst) and os.path.abspath(video_src) != os.path.abspath(video_dst):
                raise FileExistsError(f"Destination video already exists: {video_dst}")
            if srt_dst and os.path.exists(srt_dst) and os.path.abspath(srt_src) != os.path.abspath(srt_dst):
                raise FileExistsError(f"Destination subtitle already exists: {srt_dst}")

            shutil.move(video_src, video_dst)
            if not os.path.isfile(video_dst) or os.path.getsize(video_dst) != v_size:
                raise IOError(f"Integrity check failed for {video_dst}")
            stats["videos_moved"] += 1
            stats["bytes_moved"] += v_size

            if srt_src and srt_dst:
                shutil.move(srt_src, srt_dst)
                if not os.path.isfile(srt_dst) or os.path.getsize(srt_dst) != s_size:
                    raise IOError(f"Integrity check failed for {srt_dst}")
                stats["subtitles_moved"] += 1
                stats["bytes_moved"] += s_size

            if delete_source:
                force_remove_path(item["folder_path"])
                stats["folders_deleted"] += 1

            stats["folders_processed"] += 1
            print(f"  [SUCCESS] Moved and cleaned folder.")

        except Exception as e:
            err_msg = f"Error processing {item['folder_name']}: {e}"
            print(f"  [ERROR] {err_msg}", file=sys.stderr)
            stats["errors"].append(err_msg)

    if clean_loose:
        root_files = [
            f for f in os.listdir(root_dir)
            if os.path.isfile(os.path.join(root_dir, f))
            and os.path.splitext(f)[1].lower() in VIDEO_EXTENSIONS
        ]
        for rf in root_files:
            if re.match(r"^.+ - (?:19|20)\d{2}\.[a-zA-Z0-9]+$", rf):
                continue
            info = parse_movie_name_and_year(rf)
            if info:
                title, year = info
                ext = os.path.splitext(rf)[1]
                new_name = f"{title} - {year}{ext}"
                old_path = os.path.join(root_dir, rf)
                new_path = os.path.join(root_dir, new_name)
                if old_path != new_path and not os.path.exists(new_path):
                    print(f"\n[LOOSE FILE] Renaming: {rf} -> {new_name}")
                    if not dry_run:
                        os.rename(old_path, new_path)
                    stats["loose_videos_renamed"] += 1

    return stats


def print_summary(stats: Dict, dry_run: bool) -> None:
    """Print execution summary."""
    prefix = "[DRY-RUN] " if dry_run else ""
    print("\n========================================")
    print(f"       {prefix}EXECUTION SUMMARY")
    print("========================================")
    print(f" Movie folders processed:  {stats['folders_processed']}")
    print(f" Non-movie folders skipped:{stats['folders_skipped']}")
    print(f" Video files moved:        {stats['videos_moved']}")
    print(f" Subtitle files moved:     {stats['subtitles_moved']}")
    print(f" Loose files renamed:      {stats['loose_videos_renamed']}")
    print(f" Folders deleted:          {stats['folders_deleted']}")
    print(f" Total volume transferred: {format_bytes(stats['bytes_moved'])}")
    print(f" Errors encountered:       {len(stats['errors'])}")
    print("========================================\n")


def main():
    parser = argparse.ArgumentParser(
        description="Before the Move to JF - Clean movie titles, subtitles, and folders for Jellyfin."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default="E:\\Movies_tobemoved to Server",
        help="Target movie directory containing folders to organize (default: E:\\Movies_tobemoved to Server)",
    )
    parser.add_argument(
        "--target-dir",
        "-t",
        default=None,
        help="Destination directory where files should be moved (default: same as directory)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Simulate operations and display preview without moving or deleting files",
    )
    parser.add_argument(
        "--no-delete",
        action="store_true",
        help="Do not delete source folders after moving movie files",
    )
    parser.add_argument(
        "--no-clean-loose",
        action="store_true",
        help="Do not rename loose scene video files sitting in root directory",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable detailed logging output",
    )

    args = parser.parse_args()

    print(f"Target Directory: {args.directory}")
    if args.dry_run:
        print("Mode: DRY-RUN (no files will be modified)")

    stats = organize_movies(
        root_dir=args.directory,
        target_dir=args.target_dir,
        dry_run=args.dry_run,
        delete_source=not args.no_delete,
        clean_loose=not args.no_clean_loose,
        verbose=args.verbose,
    )

    print_summary(stats, dry_run=args.dry_run)

    if stats["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
