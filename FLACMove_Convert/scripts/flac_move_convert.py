"""
Music FLAC Sync & Transcoder
============================
Automates:
1. Syncing FLAC album folders to a NAS or backup destination via multi-threaded Robocopy.
2. Converting existing MP3 files to VBR 128 kbps (-q:a 5) with atomic in-place replacement.
3. Converting FLAC files to MP3 VBR 190 kbps (-q:a 2) with safe deletion of original FLACs.
4. Preserving ID3v2 tags and embedded album cover art.
5. Renaming folders from "- Flac" to "- mp3" once all FLAC files have been converted.
"""

import os
import sys
import time
import shutil
import argparse
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure UTF-8 output on Windows consoles to support non-ASCII album / artist names
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_FFMPEG_PATHS = [
    r"C:\Program Files\DownloadHelper CoApp\ffmpeg.exe",
    r"C:\Program Files\Subtitle Edit\ffmpeg\ffmpeg.exe",
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    r"C:\tools\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files\Topaz Labs LLC\Topaz Video\ffmpeg.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"),
    os.path.expanduser(r"~\scoop\shims\ffmpeg.exe"),
    "ffmpeg.exe",
    "ffmpeg",
]


def find_ffmpeg(custom_path=None):
    if custom_path and os.path.isfile(custom_path):
        return custom_path
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    for candidate in DEFAULT_FFMPEG_PATHS:
        if os.path.isfile(candidate):
            return candidate
    return None


def log_msg(msg):
    ts = time.strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{ts} {msg}", flush=True)


def cleanup_temp_files(root_dir):
    cleaned = 0
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            if fname.endswith(".tmp_conv.mp3"):
                p = os.path.join(dirpath, fname)
                try:
                    os.remove(p)
                    cleaned += 1
                except Exception:
                    pass
    if cleaned > 0:
        log_msg(f"Cleaned up {cleaned} leftover temporary conversion files.")


# =========================================================================
# Action 1: Sync FLAC Folders via Robocopy
# =========================================================================
def sync_flac_folders(source_dir, dest_dir, pattern="*- Flac*", threads=16, dry_run=False):
    log_msg("=" * 60)
    log_msg(f"ACTION: Sync FLAC Folders")
    log_msg(f"  Source:      {source_dir}")
    log_msg(f"  Destination: {dest_dir}")
    log_msg(f"  Filter:      {pattern}")
    log_msg(f"  Threads:     {threads}")
    if dry_run:
        log_msg("  MODE:        DRY-RUN (Preview only)")
    log_msg("=" * 60)

    if not os.path.isdir(source_dir):
        log_msg(f"ERROR: Source directory does not exist: {source_dir}")
        return False

    if not dry_run and not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)

    # Find matching directories
    import fnmatch
    matching_folders = []
    for item in os.listdir(source_dir):
        full_path = os.path.join(source_dir, item)
        if os.path.isdir(full_path) and fnmatch.fnmatch(item, pattern):
            matching_folders.append((item, full_path))

    matching_folders.sort(key=lambda x: x[0])
    total = len(matching_folders)
    log_msg(f"Found {total} folders matching '{pattern}' in source.")

    if total == 0:
        return True

    success_count = 0
    skipped_count = 0
    failed_count = 0
    start_time = time.time()

    for idx, (folder_name, source_path) in enumerate(matching_folders, 1):
        target_path = os.path.join(dest_dir, folder_name)

        if dry_run:
            exists = os.path.exists(target_path)
            status = "EXISTS (will sync)" if exists else "NEW (will copy)"
            log_msg(f"[{idx}/{total}] [DRY-RUN] {status}: {folder_name}")
            continue

        folder_start = time.time()
        cmd = [
            "robocopy", source_path, target_path,
            "/E", "/R:2", "/W:5", f"/MT:{threads}", "/NP", "/NFL", "/NDL"
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        duration = time.time() - folder_start
        exit_code = res.returncode

        if exit_code == 0:
            skipped_count += 1
            status = f"UP-TO-DATE ({duration:.1f}s)"
        elif exit_code < 8:
            success_count += 1
            status = f"COPIED ({duration:.1f}s)"
        else:
            failed_count += 1
            status = f"FAILED (code {exit_code}, {duration:.1f}s)"

        log_msg(f"[{idx}/{total}] {status} - {folder_name}")

    elapsed_min = (time.time() - start_time) / 60.0
    log_msg("-" * 60)
    if dry_run:
        log_msg(f"DRY-RUN COMPLETE: {total} matching folders found.")
    else:
        log_msg(f"SYNC COMPLETE: {total} processed in {elapsed_min:.2f} mins. "
                f"(Copied: {success_count}, Up-to-date: {skipped_count}, Failed: {failed_count})")
    return failed_count == 0


# =========================================================================
# Action 2: Convert MP3 files to VBR 128 kbps (-q:a 5)
# =========================================================================
def _convert_single_mp3(ffmpeg_bin, src_path, quality, timeout):
    tmp_path = src_path + ".tmp_conv.mp3"
    cmd = [
        ffmpeg_bin, "-y",
        "-i", src_path,
        "-map", "0:a",
        "-map", "0:v?",
        "-c:a", "libmp3lame",
        "-q:a", str(quality),
        "-c:v", "copy",
        "-map_metadata", "0",
        "-id3v2_version", "3",
        tmp_path
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=timeout)
        if res.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            os.replace(tmp_path, src_path)
            return True, None
        else:
            # Fallback without video stream if cover art was corrupted
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except Exception: pass
            cmd_fallback = [
                ffmpeg_bin, "-y",
                "-i", src_path,
                "-map", "0:a",
                "-c:a", "libmp3lame",
                "-q:a", str(quality),
                "-map_metadata", "0",
                "-id3v2_version", "3",
                tmp_path
            ]
            res2 = subprocess.run(cmd_fallback, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=timeout)
            if res2.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                os.replace(tmp_path, src_path)
                return True, None
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except Exception: pass
            err = res.stderr.decode("utf-8", errors="ignore")[-200:] if res.stderr else "Conversion failed"
            return False, err
    except Exception as e:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except Exception: pass
        return False, str(e)


def convert_mp3_files(source_dir, ffmpeg_bin, quality=5, workers=8, timeout=300, dry_run=False):
    log_msg("=" * 60)
    log_msg("ACTION: Convert MP3 to VBR 128 kbps")
    log_msg(f"  Target Directory: {source_dir}")
    log_msg(f"  Quality Preset:   -q:a {quality} (~128-130 kbps VBR)")
    log_msg(f"  Workers:          {workers}")
    if dry_run:
        log_msg("  MODE:             DRY-RUN (Preview only)")
    log_msg("=" * 60)

    cleanup_temp_files(source_dir)

    mp3_files = []
    for dirpath, _, filenames in os.walk(source_dir):
        for fname in filenames:
            if fname.lower().endswith(".mp3") and not fname.endswith(".tmp_conv.mp3"):
                mp3_files.append(os.path.join(dirpath, fname))

    total = len(mp3_files)
    log_msg(f"Found {total} MP3 files to convert.")
    if total == 0:
        return True

    if dry_run:
        for idx, f in enumerate(mp3_files[:10], 1):
            log_msg(f"[{idx}/{total}] [DRY-RUN] Would convert: {f}")
        if total > 10:
            log_msg(f"... and {total - 10} more files.")
        return True

    start_time = time.time()
    completed = 0
    success = 0
    failed = 0
    last_log = time.time()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_convert_single_mp3, ffmpeg_bin, f, quality, timeout): f for f in mp3_files}
        for fut in as_completed(futures):
            completed += 1
            f = futures[fut]
            try:
                ok, err = fut.result()
                if ok:
                    success += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

            now = time.time()
            if completed % 50 == 0 or completed == total or (now - last_log >= 15):
                last_log = now
                elapsed = now - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                rem_sec = (total - completed) / rate if rate > 0 else 0
                log_msg(f"[MP3] [{completed}/{total}] {completed*100.0/total:5.1f}% | "
                        f"Success: {success} | Failed: {failed} | "
                        f"{rate:4.1f} files/s | Rem: {rem_sec/60:4.1f} min")

    elapsed_min = (time.time() - start_time) / 60.0
    log_msg(f"MP3 CONVERSION COMPLETE: {total} files in {elapsed_min:.2f} mins. (Success: {success}, Failed: {failed})")
    return failed == 0


# =========================================================================
# Action 3: Convert FLAC to MP3 VBR 190 kbps (-q:a 2) & Safe Delete
# =========================================================================
def _convert_single_flac(ffmpeg_bin, src_path, quality, delete_flac, timeout):
    base, _ = os.path.splitext(src_path)
    dst_path = base + ".mp3"
    tmp_path = base + ".tmp_conv.mp3"
    cmd = [
        ffmpeg_bin, "-y",
        "-i", src_path,
        "-map", "0:a",
        "-map", "0:v?",
        "-c:a", "libmp3lame",
        "-q:a", str(quality),
        "-c:v", "copy",
        "-map_metadata", "0",
        "-id3v2_version", "3",
        tmp_path
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=timeout)
        if res.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            os.replace(tmp_path, dst_path)
            if delete_flac:
                try:
                    os.remove(src_path)
                except Exception as e:
                    return True, f"Converted, but failed to delete flac: {e}"
            return True, None
        else:
            # Fallback without video stream if cover art was corrupted
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except Exception: pass
            cmd_fallback = [
                ffmpeg_bin, "-y",
                "-i", src_path,
                "-map", "0:a",
                "-c:a", "libmp3lame",
                "-q:a", str(quality),
                "-map_metadata", "0",
                "-id3v2_version", "3",
                tmp_path
            ]
            res2 = subprocess.run(cmd_fallback, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=timeout)
            if res2.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                os.replace(tmp_path, dst_path)
                if delete_flac:
                    try:
                        os.remove(src_path)
                    except Exception as e:
                        return True, f"Converted, but failed to delete flac: {e}"
                return True, None
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except Exception: pass
            err = res.stderr.decode("utf-8", errors="ignore")[-200:] if res.stderr else "Conversion failed"
            return False, err
    except Exception as e:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except Exception: pass
        return False, str(e)


def convert_flac_files(source_dir, ffmpeg_bin, quality=2, delete_flac=True, workers=8, timeout=300, dry_run=False):
    log_msg("=" * 60)
    log_msg("ACTION: Convert FLAC to MP3 VBR 190 kbps")
    log_msg(f"  Target Directory: {source_dir}")
    log_msg(f"  Quality Preset:   -q:a {quality} (~190 kbps VBR)")
    log_msg(f"  Delete Original:  {delete_flac}")
    log_msg(f"  Workers:          {workers}")
    if dry_run:
        log_msg("  MODE:             DRY-RUN (Preview only)")
    log_msg("=" * 60)

    cleanup_temp_files(source_dir)

    flac_files = []
    for dirpath, _, filenames in os.walk(source_dir):
        for fname in filenames:
            if fname.lower().endswith(".flac"):
                flac_files.append(os.path.join(dirpath, fname))

    total = len(flac_files)
    log_msg(f"Found {total} FLAC files to convert.")
    if total == 0:
        return True

    if dry_run:
        for idx, f in enumerate(flac_files[:10], 1):
            action = "convert & delete" if delete_flac else "convert & keep"
            log_msg(f"[{idx}/{total}] [DRY-RUN] Would {action}: {f}")
        if total > 10:
            log_msg(f"... and {total - 10} more files.")
        return True

    start_time = time.time()
    completed = 0
    success = 0
    failed = 0
    last_log = time.time()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_convert_single_flac, ffmpeg_bin, f, quality, delete_flac, timeout): f for f in flac_files}
        for fut in as_completed(futures):
            completed += 1
            f = futures[fut]
            try:
                ok, err = fut.result()
                if ok:
                    success += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

            now = time.time()
            if completed % 50 == 0 or completed == total or (now - last_log >= 15):
                last_log = now
                elapsed = now - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                rem_sec = (total - completed) / rate if rate > 0 else 0
                log_msg(f"[FLAC] [{completed}/{total}] {completed*100.0/total:5.1f}% | "
                        f"Success: {success} | Failed: {failed} | "
                        f"{rate:4.1f} files/s | Rem: {rem_sec/60:4.1f} min")

    elapsed_min = (time.time() - start_time) / 60.0
    log_msg(f"FLAC CONVERSION COMPLETE: {total} files in {elapsed_min:.2f} mins. (Success: {success}, Failed: {failed})")
    return failed == 0


# =========================================================================
# Action 4: Rename Folder Suffix from "- Flac" to "- mp3"
# =========================================================================
def rename_flac_folders(source_dir, dry_run=False):
    log_msg("=" * 60)
    log_msg("ACTION: Rename Folders from '- Flac' to '- mp3'")
    log_msg(f"  Target Directory: {source_dir}")
    if dry_run:
        log_msg("  MODE:             DRY-RUN (Preview only)")
    log_msg("=" * 60)

    renamed = 0
    skipped_flacs_remain = 0

    # Scan top-level directories
    for item in os.listdir(source_dir):
        dir_path = os.path.join(source_dir, item)
        if not os.path.isdir(dir_path):
            continue

        if item.endswith(" - Flac") or item.endswith(" - FLAC") or item.endswith(" - flac"):
            # Check if any .flac files remain inside
            has_flac = False
            for _, _, files in os.walk(dir_path):
                if any(f.lower().endswith(".flac") for f in files):
                    has_flac = True
                    break

            if has_flac:
                skipped_flacs_remain += 1
                continue

            # Determine new name
            if item.endswith(" - Flac"):
                new_name = item[:-7] + " - mp3"
            elif item.endswith(" - FLAC"):
                new_name = item[:-7] + " - mp3"
            else:
                new_name = item[:-7] + " - mp3"

            new_path = os.path.join(source_dir, new_name)

            if dry_run:
                log_msg(f"[DRY-RUN] Rename: '{item}' -> '{new_name}'")
                renamed += 1
            else:
                if os.path.exists(new_path):
                    log_msg(f"WARNING: Target folder already exists, skipping: {new_name}")
                    continue
                try:
                    os.rename(dir_path, new_path)
                    renamed += 1
                    log_msg(f"Renamed: '{item}' -> '{new_name}'")
                except Exception as e:
                    log_msg(f"ERROR renaming '{item}': {e}")

    log_msg(f"FOLDER RENAMING COMPLETE: Renamed {renamed} folders. (Skipped with remaining FLACs: {skipped_flacs_remain})")


# =========================================================================
# Main CLI Entry Point
# =========================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Music FLAC Sync & Transcoder: Sync FLACs to NAS/backup, convert MP3 to 128k VBR, convert FLAC to 190k VBR, and safely delete original FLACs."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # sync-flac
    p_sync = subparsers.add_parser("sync-flac", help="Sync FLAC folders to destination using multi-threaded Robocopy.")
    p_sync.add_argument("source", help="Source directory containing music folders")
    p_sync.add_argument("dest", help="Destination backup/NAS directory")
    p_sync.add_argument("--filter", default="*- Flac*", help="Folder pattern filter (default: '*- Flac*')")
    p_sync.add_argument("--threads", type=int, default=16, help="Robocopy thread count (default: 16)")
    p_sync.add_argument("--dry-run", action="store_true", help="Preview without copying")

    # convert-mp3
    p_cmp3 = subparsers.add_parser("convert-mp3", help="Convert all MP3 files to VBR 128 kbps.")
    p_cmp3.add_argument("source", help="Directory to search and convert MP3 files")
    p_cmp3.add_argument("--quality", type=int, default=5, help="LAME VBR quality preset (default: 5 = ~128k)")
    p_cmp3.add_argument("--workers", type=int, default=8, help="Worker concurrency (default: 8)")
    p_cmp3.add_argument("--timeout", type=int, default=300, help="File timeout in seconds (default: 300)")
    p_cmp3.add_argument("--ffmpeg", help="Custom path to ffmpeg.exe")
    p_cmp3.add_argument("--dry-run", action="store_true", help="Preview without converting")

    # convert-flac
    p_cflac = subparsers.add_parser("convert-flac", help="Convert all FLAC files to MP3 VBR 190 kbps and delete original FLACs.")
    p_cflac.add_argument("source", help="Directory to search and convert FLAC files")
    p_cflac.add_argument("--quality", type=int, default=2, help="LAME VBR quality preset (default: 2 = ~190k)")
    p_cflac.add_argument("--keep-flac", action="store_true", help="Keep original FLAC files instead of deleting")
    p_cflac.add_argument("--workers", type=int, default=8, help="Worker concurrency (default: 8)")
    p_cflac.add_argument("--timeout", type=int, default=300, help="File timeout in seconds (default: 300)")
    p_cflac.add_argument("--ffmpeg", help="Custom path to ffmpeg.exe")
    p_cflac.add_argument("--dry-run", action="store_true", help="Preview without converting or deleting")

    # rename-folders
    p_rn = subparsers.add_parser("rename-folders", help="Rename folders from '- Flac' to '- mp3' when no FLACs remain.")
    p_rn.add_argument("source", help="Root directory containing album folders")
    p_rn.add_argument("--dry-run", action="store_true", help="Preview without renaming")

    # all
    p_all = subparsers.add_parser("all", help="Run full pipeline: sync-flac -> convert-mp3 -> convert-flac -> rename-folders.")
    p_all.add_argument("source", help="Source directory containing music folders")
    p_all.add_argument("dest", help="Destination backup/NAS directory for FLAC sync")
    p_all.add_argument("--filter", default="*- Flac*", help="Folder pattern filter (default: '*- Flac*')")
    p_all.add_argument("--threads", type=int, default=16, help="Robocopy thread count (default: 16)")
    p_all.add_argument("--mp3-quality", type=int, default=5, help="MP3 VBR quality preset (default: 5 = ~128k)")
    p_all.add_argument("--flac-quality", type=int, default=2, help="FLAC->MP3 VBR quality preset (default: 2 = ~190k)")
    p_all.add_argument("--keep-flac", action="store_true", help="Keep original FLAC files instead of deleting")
    p_all.add_argument("--workers", type=int, default=8, help="Worker concurrency (default: 8)")
    p_all.add_argument("--timeout", type=int, default=300, help="File timeout in seconds (default: 300)")
    p_all.add_argument("--no-rename", action="store_true", help="Do not rename folder suffixes to '- mp3'")
    p_all.add_argument("--ffmpeg", help="Custom path to ffmpeg.exe")
    p_all.add_argument("--dry-run", action="store_true", help="Preview without modifying files")

    args = parser.parse_args()

    ffmpeg_bin = None
    if args.command in ("convert-mp3", "convert-flac", "all"):
        custom_ff = getattr(args, "ffmpeg", None)
        ffmpeg_bin = find_ffmpeg(custom_ff)
        if not ffmpeg_bin:
            log_msg("ERROR: ffmpeg executable not found. Please specify via --ffmpeg or ensure it is in PATH.")
            sys.exit(1)

    if args.command == "sync-flac":
        sync_flac_folders(args.source, args.dest, pattern=args.filter, threads=args.threads, dry_run=args.dry_run)

    elif args.command == "convert-mp3":
        convert_mp3_files(args.source, ffmpeg_bin, quality=args.quality, workers=args.workers, timeout=args.timeout, dry_run=args.dry_run)

    elif args.command == "convert-flac":
        convert_flac_files(args.source, ffmpeg_bin, quality=args.quality, delete_flac=(not args.keep_flac), workers=args.workers, timeout=args.timeout, dry_run=args.dry_run)

    elif args.command == "rename-folders":
        rename_flac_folders(args.source, dry_run=args.dry_run)

    elif args.command == "all":
        log_msg("Starting Full End-to-End Pipeline...")
        sync_flac_folders(args.source, args.dest, pattern=args.filter, threads=args.threads, dry_run=args.dry_run)
        convert_mp3_files(args.source, ffmpeg_bin, quality=args.mp3_quality, workers=args.workers, timeout=args.timeout, dry_run=args.dry_run)
        convert_flac_files(args.source, ffmpeg_bin, quality=args.flac_quality, delete_flac=(not args.keep_flac), workers=args.workers, timeout=args.timeout, dry_run=args.dry_run)
        if not args.no_rename:
            rename_flac_folders(args.source, dry_run=args.dry_run)
        log_msg("Pipeline execution completed.")


if __name__ == "__main__":
    main()