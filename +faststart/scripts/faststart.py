#!/usr/bin/env python3
"""
+faststart: Lossless MP4/MOV Web Streaming Optimizer
Relocates the MP4/MOV 'moov' atom metadata to the beginning of the file using
`ffmpeg -c copy -movflags +faststart` to enable instant progressive web playback.
"""

import sys
import os
import argparse
import subprocess
import shutil

SUPPORTED_EXTENSIONS = ('.mp4', '.mov', '.m4v')

def is_faststart_enabled(filepath):
    """
    Checks if the 'moov' atom is placed before the 'mdat' atom in an MP4/MOV file.
    Returns True if faststart is enabled, False otherwise.
    """
    try:
        with open(filepath, 'rb') as f:
            moov_pos = None
            mdat_pos = None
            pos = 0
            while True:
                f.seek(pos)
                header = f.read(8)
                if len(header) < 8:
                    break
                size = int.from_bytes(header[:4], 'big')
                name = header[4:8].decode('latin1', errors='ignore')
                
                if name == 'moov':
                    moov_pos = pos
                elif name == 'mdat':
                    mdat_pos = pos
                
                if size == 1:
                    # 64-bit size
                    size = int.from_bytes(f.read(8), 'big')
                elif size == 0:
                    # Atom extends to end of file
                    break
                
                if size < 8:
                    break
                    
                pos += size
                if moov_pos is not None and mdat_pos is not None:
                    break
                    
            return (moov_pos is not None and mdat_pos is not None and moov_pos < mdat_pos)
    except Exception:
        return False

def collect_video_files(target_path, recursive=False):
    """Collects all MP4/MOV video files from a target file or folder."""
    if os.path.isfile(target_path):
        if target_path.lower().endswith(SUPPORTED_EXTENSIONS):
            return [os.path.abspath(target_path)]
        return []
    
    video_files = []
    if recursive:
        for root, _, files in os.walk(target_path):
            for f in sorted(files):
                if f.lower().endswith(SUPPORTED_EXTENSIONS) and not f.startswith('.'):
                    video_files.append(os.path.abspath(os.path.join(root, f)))
    else:
        for f in sorted(os.listdir(target_path)):
            if f.lower().endswith(SUPPORTED_EXTENSIONS) and not f.startswith('.'):
                video_files.append(os.path.abspath(os.path.join(target_path, f)))
                
    return video_files

def process_file(filepath, dry_run=False, force=False):
    """
    Optimizes a single video file for faststart streaming.
    Returns: ('OPTIMIZED' | 'ALREADY_FASTSTART' | 'ERROR'), message
    """
    already_fast = is_faststart_enabled(filepath)
    if already_fast and not force:
        return 'ALREADY_FASTSTART', "Already web-optimized (moov before mdat)"
    
    if dry_run:
        return 'WOULD_OPTIMIZE', "Needs +faststart optimization"

    directory, filename = os.path.split(filepath)
    base_name, ext = os.path.splitext(filename)
    tmp_path = os.path.join(directory, f".tmp_faststart_{base_name}{ext}")

    orig_stat = os.stat(filepath)
    orig_size_mb = orig_stat.st_size / (1024 * 1024)

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", filepath,
        "-c", "copy",
        "-movflags", "+faststart",
        tmp_path
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            if is_faststart_enabled(tmp_path):
                # Preserve original timestamps
                os.utime(tmp_path, (orig_stat.st_atime, orig_stat.st_mtime))
                # Atomically replace
                os.replace(tmp_path, filepath)
                new_size_mb = os.path.getsize(filepath) / (1024 * 1024)
                return 'OPTIMIZED', f"{orig_size_mb:.2f} MB -> {new_size_mb:.2f} MB (faststart active)"
            else:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                return 'ERROR', "Output verification failed: moov atom was not placed at start"
        else:
            err_msg = res.stderr.strip() if res.stderr else "Unknown ffmpeg error"
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return 'ERROR', f"ffmpeg failed: {err_msg}"
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return 'ERROR', str(e)

def main():
    parser = argparse.ArgumentParser(
        description="+faststart: Optimize MP4 and MOV videos for instant web streaming"
    )
    parser.add_argument("path", help="Path to video file or directory containing videos")
    parser.add_argument("-r", "--recursive", action="store_true", help="Scan directory recursively")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Preview files needing optimization without altering them")
    parser.add_argument("-f", "--force", action="store_true", help="Force re-processing even if already web-optimized")

    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Error: Path not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    # Check ffmpeg availability
    if not shutil.which("ffmpeg"):
        print("Error: 'ffmpeg' command not found in PATH. Please install ffmpeg.", file=sys.stderr)
        sys.exit(1)

    files = collect_video_files(args.path, recursive=args.recursive)
    if not files:
        print(f"No MP4/MOV videos found in '{args.path}'.")
        sys.exit(0)

    print("=" * 78)
    print(" +faststart: Web Streaming MP4/MOV Optimizer")
    print(f" Target Path : {args.path}")
    print(f" Total Videos: {len(files)}")
    print(f" Mode        : {'DRY-RUN (Preview)' if args.dry_run else 'ACTIVE (Lossless Remux)'}")
    print("=" * 78)

    stats = {
        'OPTIMIZED': 0,
        'WOULD_OPTIMIZE': 0,
        'ALREADY_FASTSTART': 0,
        'ERROR': 0
    }

    for i, filepath in enumerate(files, start=1):
        filename = os.path.basename(filepath)
        status, msg = process_file(filepath, dry_run=args.dry_run, force=args.force)
        stats[status] = stats.get(status, 0) + 1

        prefix = f"[{i}/{len(files)}]"
        if status == 'OPTIMIZED':
            print(f"{prefix} \033[92m[DONE]\033[0m   {filename} - {msg}")
        elif status == 'WOULD_OPTIMIZE':
            print(f"{prefix} \033[93m[PLAN]\033[0m   {filename} - {msg}")
        elif status == 'ALREADY_FASTSTART':
            print(f"{prefix} \033[90m[SKIP]\033[0m   {filename} - {msg}")
        else:
            print(f"{prefix} \033[91m[FAIL]\033[0m   {filename} - {msg}")

    print("\n" + "-" * 78)
    print(" Summary:")
    print(f" - Total files scanned: {len(files)}")
    if args.dry_run:
        print(f" - Needs optimization : {stats.get('WOULD_OPTIMIZE', 0)}")
        print(f" - Already optimized  : {stats.get('ALREADY_FASTSTART', 0)}")
    else:
        print(f" - Successfully optimized: {stats.get('OPTIMIZED', 0)}")
        print(f" - Already web-optimized : {stats.get('ALREADY_FASTSTART', 0)}")
        print(f" - Errors               : {stats.get('ERROR', 0)}")
    print("-" * 78)

if __name__ == "__main__":
    main()
