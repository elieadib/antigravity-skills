#!/usr/bin/env python3
"""
+faststart: Ultimate Web Streaming & Codec Optimizer for MP4/MOV/M4V
1. Relocates 'moov' atom metadata to the start of files (+faststart) for instant web playback.
2. Preserves all AV1 streams bit-for-bit without transcoding.
3. Automatically repairs unplayable web codecs:
   - Transcodes unplayable 10-bit H.264 (High 10 / yuv420p10le) -> universal 8-bit yuv420p
   - Remuxes unplayable uncompressed PCM audio (pcm_s16le) -> clean AAC (160k)
   - Normalizes extreme bitrate outliers (>35 Mbps) to web-friendly 8-bit H.264
   - Losslessly fixes mistagged 8-bit smpte2084 HDR VUI and container colr atoms -> bt709
   - Normalizes orientation metadata
4. Generates web gallery derivatives in Video_Thumbs/:
   - 8-second poster frame (.jpg)
   - 4-second 480p 15fps muted hover micro-preview (.preview.mp4)
5. Preserves all original timestamps (atime/mtime) and uses safe atomic writes.
"""

import sys
import os
import argparse
import subprocess
import shutil
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Ensure common binary paths are in PATH
for extra_bin in ["/opt/homebrew/bin", "/usr/local/bin", os.path.expanduser("~/.local/bin")]:
    if os.path.exists(extra_bin) and extra_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{extra_bin}:{os.environ.get('PATH', '')}"

SUPPORTED_EXTENSIONS = ('.mp4', '.mov', '.m4v')

def is_faststart_enabled(filepath):
    """
    Checks if the 'moov' atom is placed before the 'mdat' atom in an MP4/MOV/M4V file.
    Returns True if faststart is enabled, False otherwise.
    """
    try:
        with open(filepath, 'rb') as f:
            moov_pos = None
            mdat_pos = None
            pos = 0
            size_total = os.path.getsize(filepath)
            while pos + 8 <= size_total:
                f.seek(pos)
                header = f.read(16)
                if len(header) < 8:
                    break
                size = int.from_bytes(header[:4], 'big')
                name = header[4:8].decode('latin1', errors='ignore')

                if name == 'moov':
                    moov_pos = pos
                elif name == 'mdat':
                    mdat_pos = pos

                if size == 1 and len(header) >= 16:
                    size = int.from_bytes(header[8:16], 'big')
                elif size == 0:
                    size = size_total - pos

                if size < 8:
                    break

                pos += size
                if moov_pos is not None and mdat_pos is not None:
                    break

            return (moov_pos is not None and mdat_pos is not None and moov_pos < mdat_pos)
    except Exception:
        return False

def probe_video(filepath):
    """Probes video technical stream details using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_streams",
            "-show_format",
            "-of", "json",
            filepath
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)

        v_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)

        if not v_stream:
            return None

        # Bitrate
        fmt = data.get("format", {})
        bit_rate = int(fmt.get("bit_rate") or v_stream.get("bit_rate") or 0)
        duration = float(fmt.get("duration") or v_stream.get("duration") or 0.0)

        # Rotation
        rotation = 0
        tags = v_stream.get("tags", {})
        if "rotate" in tags:
            try:
                rotation = int(tags["rotate"])
            except ValueError:
                pass
        for sd in v_stream.get("side_data_list", []):
            if "rotation" in sd:
                try:
                    rotation = int(sd["rotation"])
                except ValueError:
                    pass

        return {
            "v_codec": (v_stream.get("codec_name") or "").lower(),
            "profile": v_stream.get("profile") or "",
            "pix_fmt": v_stream.get("pix_fmt") or "",
            "color_transfer": v_stream.get("color_transfer") or "",
            "width": int(v_stream.get("width") or 0),
            "height": int(v_stream.get("height") or 0),
            "a_codec": (a_stream.get("codec_name") or "none").lower() if a_stream else "none",
            "bit_rate": bit_rate,
            "duration": duration,
            "rotation": rotation,
            "faststart": is_faststart_enabled(filepath)
        }
    except Exception:
        return None

def collect_video_files(target_path, recursive=False):
    """Collects all MP4/MOV/M4V video files, ignoring internal thumbnail caches."""
    if os.path.isfile(target_path):
        if target_path.lower().endswith(SUPPORTED_EXTENSIONS) and not os.path.basename(target_path).startswith('.'):
            return [os.path.abspath(target_path)]
        return []

    video_files = []
    skip_dirs = {"video_thumbs", "thumbs", "photo_thumbs", ".git", "node_modules"}

    if recursive:
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d.lower() not in skip_dirs and not d.startswith('.')]
            for f in sorted(files):
                if f.lower().endswith(SUPPORTED_EXTENSIONS) and not f.startswith('.'):
                    if not f.endswith(".preview.mp4"):
                        video_files.append(os.path.abspath(os.path.join(root, f)))
    else:
        for f in sorted(os.listdir(target_path)):
            full = os.path.join(target_path, f)
            if os.path.isfile(full) and f.lower().endswith(SUPPORTED_EXTENSIONS) and not f.startswith('.'):
                if not f.endswith(".preview.mp4"):
                    video_files.append(os.path.abspath(full))

    return video_files

def process_file_faststart_only(filepath, dry_run=False, force=False):
    """Losslessly optimizes moov atom positioning without altering codecs."""
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
        "-map_metadata", "0",
        tmp_path
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            if is_faststart_enabled(tmp_path):
                os.utime(tmp_path, (orig_stat.st_atime, orig_stat.st_mtime))
                os.replace(tmp_path, filepath)
                new_size_mb = os.path.getsize(filepath) / (1024 * 1024)
                return 'OPTIMIZED', f"{orig_size_mb:.1f} MB -> {new_size_mb:.1f} MB (faststart active)"
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

def repair_video_stream(filepath, info, dry_run=False):
    """
    Normalizes unplayable streams, audio, extreme bitrates, and mis-tagged HDR
    while strictly keeping all AV1 video streams untouched.
    """
    is_av1 = (info["v_codec"] == "av1")
    is_h264_10bit = (info["v_codec"] == "h264" and ("10" in info["profile"] or "10le" in info["pix_fmt"]))
    is_pcm_audio = info["a_codec"].startswith("pcm_")
    is_extreme_bitrate = (not is_av1 and info["bit_rate"] > 35_000_000)
    is_mistagged_8bit_hdr = (not is_av1 and info["color_transfer"] == "smpte2084" and "10le" not in info["pix_fmt"])
    is_rotated = (not is_av1 and info["rotation"] != 0)
    needs_faststart = not info["faststart"]

    can_lossless_retag_hdr = is_mistagged_8bit_hdr and (info["v_codec"] in ("h264", "hevc"))
    needs_video_transcode = (
        is_h264_10bit or
        is_extreme_bitrate or
        is_rotated or
        (is_mistagged_8bit_hdr and not can_lossless_retag_hdr)
    )
    needs_audio_transcode = is_pcm_audio

    reasons = []
    if is_h264_10bit: reasons.append(f"h264-10bit({info['profile']})")
    if is_rotated: reasons.append(f"rotate({info['rotation']}°)")
    if is_extreme_bitrate: reasons.append(f"high-bitrate({info['bit_rate']/1e6:.1f}Mbps)")
    if is_mistagged_8bit_hdr: reasons.append("8bit-smpte2084->bt709")
    if is_pcm_audio: reasons.append(f"audio({info['a_codec']}->aac)")
    if needs_faststart: reasons.append("+faststart")

    if not needs_video_transcode and not can_lossless_retag_hdr and not needs_audio_transcode and not needs_faststart:
        return 'OPTIMAL', "Stream codecs and +faststart are already optimal"

    if dry_run:
        return 'WOULD_REPAIR', f"Needs repair: [{', '.join(reasons)}]"

    directory, filename = os.path.split(filepath)
    base_name, ext = os.path.splitext(filename)
    tmp_path = os.path.join(directory, f".tmp_repair_{base_name}{ext}")

    orig_stat = os.stat(filepath)

    args = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", filepath,
        "-map", "0:v:0", "-map", "0:a?"
    ]

    if needs_video_transcode:
        # Normalize broken 10-bit or extreme streams to standard 8-bit H.264
        args.extend([
            "-vf", "setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709",
            "-c:v", "libx264",
            "-profile:v", "high",
            "-pix_fmt", "yuv420p",
            "-crf", "21" if is_extreme_bitrate else "20",
            "-maxrate", "12M",
            "-bufsize", "24M",
            "-preset", "fast",
            "-colorspace", "bt709",
            "-color_primaries", "bt709",
            "-color_trc", "bt709"
        ])
    else:
        # Lossless video copy - preserves AV1 and healthy streams bit-for-bit
        args.extend(["-c:v", "copy"])
        if can_lossless_retag_hdr:
            bsf = "hevc_metadata" if info["v_codec"] == "hevc" else "h264_metadata"
            args.extend([
                "-bsf:v", f"{bsf}=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1",
                "-colorspace", "bt709",
                "-color_primaries", "bt709",
                "-color_trc", "bt709"
            ])

    if needs_audio_transcode or (needs_video_transcode and info["a_codec"] not in ("aac", "none")):
        args.extend(["-c:a", "aac", "-b:a", "160k"])
    elif info["a_codec"] != "none":
        args.extend(["-c:a", "copy"])

    args.extend(["-movflags", "+faststart", "-map_metadata", "0", tmp_path])

    try:
        res = subprocess.run(args, capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 1024:
            os.utime(tmp_path, (orig_stat.st_atime, orig_stat.st_mtime))
            os.replace(tmp_path, filepath)
            os.utime(filepath, (orig_stat.st_atime, orig_stat.st_mtime))
            return 'REPAIRED', f"Repaired [{', '.join(reasons)}]"
        else:
            err = res.stderr.strip() if res.stderr else "ffmpeg failed"
            if os.path.exists(tmp_path): os.remove(tmp_path)
            return 'ERROR', f"Repair failed: {err}"
    except Exception as e:
        if os.path.exists(tmp_path): os.remove(tmp_path)
        return 'ERROR', str(e)

def generate_video_derivatives(filepath, info, dry_run=False):
    """
    Generates 8-second poster thumbnail (.jpg) and 4-second 480p 15fps muted
    hover micro-preview (.preview.mp4) in a Video_Thumbs subfolder.
    """
    directory, filename = os.path.split(filepath)
    base_name, _ = os.path.splitext(filename)

    thumbs_dir = os.path.join(directory, "Video_Thumbs")
    poster_path = os.path.join(thumbs_dir, f"{base_name}.jpg")
    preview_path = os.path.join(thumbs_dir, f"{base_name}.preview.mp4")

    poster_exists = os.path.exists(poster_path) and os.path.getsize(poster_path) > 1024
    preview_exists = os.path.exists(preview_path) and os.path.getsize(preview_path) > 1024

    if poster_exists and preview_exists:
        return 'DERIVATIVES_EXIST', "Poster and 4s hover preview already present"

    if dry_run:
        actions = []
        if not poster_exists: actions.append("8s poster (.jpg)")
        if not preview_exists: actions.append("4s micro-preview (.preview.mp4)")
        return 'WOULD_GENERATE', f"Would generate: [{', '.join(actions)}]"

    os.makedirs(thumbs_dir, exist_ok=True)
    orig_stat = os.stat(filepath)
    duration = info.get("duration", 0.0) if info else 0.0

    # 1. Poster thumbnail at 8s
    if not poster_exists:
        poster_ss = 8.0 if duration >= 9.0 else max(0.5, duration * 0.5)
        tmp_poster = f"{poster_path}.tmp_{os.getpid()}.jpg"
        p_cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{poster_ss:.2f}",
            "-i", filepath,
            "-vframes", "1",
            "-vf", "scale='min(720,iw)':-2",
            "-q:v", "2",
            tmp_poster
        ]
        try:
            subprocess.run(p_cmd, check=True, capture_output=True)
            if os.path.exists(tmp_poster) and os.path.getsize(tmp_poster) > 1024:
                os.utime(tmp_poster, (orig_stat.st_atime, orig_stat.st_mtime))
                os.replace(tmp_poster, poster_path)
                os.utime(poster_path, (orig_stat.st_atime, orig_stat.st_mtime))
        except Exception:
            if os.path.exists(tmp_poster):
                try: os.remove(tmp_poster)
                except Exception: pass

    # 2. 4s 480p 15fps muted hover preview
    if not preview_exists:
        prev_ss = 8.0 if duration >= 13.0 else (2.0 if duration >= 6.0 else 0.0)
        prev_dur = min(4.0, max(1.5, duration - prev_ss)) if duration > 0 else 4.0
        tmp_prev = f"{preview_path}.tmp_{os.getpid()}.mp4"
        prev_cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{prev_ss:.2f}",
            "-t", f"{prev_dur:.2f}",
            "-i", filepath,
            "-vf", "scale='min(480,iw)':-2",
            "-r", "15",
            "-an",
            "-c:v", "libx264",
            "-crf", "26",
            "-preset", "fast",
            "-movflags", "+faststart",
            tmp_prev
        ]
        try:
            subprocess.run(prev_cmd, check=True, capture_output=True)
            if os.path.exists(tmp_prev) and os.path.getsize(tmp_prev) > 1024:
                os.utime(tmp_prev, (orig_stat.st_atime, orig_stat.st_mtime))
                os.replace(tmp_prev, preview_path)
                os.utime(preview_path, (orig_stat.st_atime, orig_stat.st_mtime))
        except Exception:
            if os.path.exists(tmp_prev):
                try: os.remove(tmp_prev)
                except Exception: pass

    return 'GENERATED', f"Generated derivatives in {os.path.basename(directory)}/Video_Thumbs"

def main():
    parser = argparse.ArgumentParser(
        description="+faststart: Lossless Web Streaming & Codec Optimizer for MP4/MOV/M4V"
    )
    parser.add_argument("path", help="Path to video file or directory containing videos")
    parser.add_argument("-r", "--recursive", action="store_true", help="Scan directory recursively")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Preview files needing optimization/repair without touching disk")
    parser.add_argument("-f", "--force", action="store_true", help="Force re-processing even if already web-optimized")
    parser.add_argument(
        "--repair", "--normalize", action="store_true",
        help="Repair unplayable web codecs (10-bit H.264 -> 8-bit, PCM -> AAC, cap extreme bitrates, fix HDR VUI) while strictly preserving AV1"
    )
    parser.add_argument(
        "--previews", action="store_true",
        help="Generate 8-second poster frame (.jpg) and 4-second 480p muted hover preview (.preview.mp4) in Video_Thumbs/"
    )
    parser.add_argument(
        "--all", "--full", action="store_true",
        help="Run complete web optimization: +faststart + stream repairs (AV1 preserved) + 8s posters and 4s hover micro-previews"
    )

    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Error: Path not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("Error: 'ffmpeg' and 'ffprobe' must be installed and available in PATH.", file=sys.stderr)
        sys.exit(1)

    files = collect_video_files(args.path, recursive=args.recursive)
    if not files:
        print(f"No MP4/MOV/M4V videos found in '{args.path}'.")
        sys.exit(0)

    do_repair = args.repair or args.all
    do_previews = args.previews or args.all
    do_faststart_only = not do_repair and not do_previews

    mode_title = "LOSSLESS +FASTSTART"
    if args.all:
        mode_title = "FULL SUITE (+faststart, stream repair, AV1 preservation, and 4s hover previews)"
    elif do_repair and do_previews:
        mode_title = "STREAM REPAIR & HOVER PREVIEWS"
    elif do_repair:
        mode_title = "CODEC & STREAM REPAIR (AV1 preserved)"
    elif do_previews:
        mode_title = "POSTER & HOVER MICRO-PREVIEW GENERATION"

    print("=" * 78)
    print(" +faststart: Web Streaming & Video Optimization Suite")
    print(f" Target Path : {args.path}")
    print(f" Total Videos: {len(files)}")
    print(f" Operation   : {mode_title}")
    print(f" Mode        : {'DRY-RUN (Preview)' if args.dry_run else 'ACTIVE'}")
    print("=" * 78)

    stats = {
        'PROCESSED': 0,
        'SKIPPED': 0,
        'REPAIRED': 0,
        'PREVIEWS': 0,
        'ERRORS': 0
    }

    for i, filepath in enumerate(files, start=1):
        filename = os.path.basename(filepath)
        prefix = f"[{i}/{len(files)}]"

        if do_faststart_only:
            status, msg = process_file_faststart_only(filepath, dry_run=args.dry_run, force=args.force)
            if status == 'OPTIMIZED':
                stats['PROCESSED'] += 1
                print(f"{prefix} \033[92m[FASTSTART]\033[0m {filename} - {msg}")
            elif status == 'WOULD_OPTIMIZE':
                stats['PROCESSED'] += 1
                print(f"{prefix} \033[93m[PLAN]\033[0m      {filename} - {msg}")
            elif status == 'ALREADY_FASTSTART':
                stats['SKIPPED'] += 1
                print(f"{prefix} \033[90m[OPTIMAL]\033[0m   {filename} - {msg}")
            else:
                stats['ERRORS'] += 1
                print(f"{prefix} \033[91m[FAIL]\033[0m      {filename} - {msg}")
        else:
            info = probe_video(filepath)
            if not info:
                stats['ERRORS'] += 1
                print(f"{prefix} \033[91m[FAIL]\033[0m      {filename} - Unable to probe video streams")
                continue

            # 1. Stream repair / faststart
            if do_repair:
                status, msg = repair_video_stream(filepath, info, dry_run=args.dry_run)
                if status in ('REPAIRED', 'WOULD_REPAIR'):
                    stats['REPAIRED'] += 1
                    tag = "\033[93m[PLAN]\033[0m" if args.dry_run else "\033[92m[REPAIRED]\033[0m"
                    print(f"{prefix} {tag}   {filename} - {msg}")
                elif status == 'OPTIMAL':
                    stats['SKIPPED'] += 1
                    print(f"{prefix} \033[90m[OPTIMAL]\033[0m    {filename} - {msg}")
                else:
                    stats['ERRORS'] += 1
                    print(f"{prefix} \033[91m[FAIL]\033[0m       {filename} - {msg}")

            # 2. Derivatives
            if do_previews:
                status, msg = generate_video_derivatives(filepath, info, dry_run=args.dry_run)
                if status in ('GENERATED', 'WOULD_GENERATE'):
                    stats['PREVIEWS'] += 1
                    tag = "\033[93m[PLAN]\033[0m" if args.dry_run else "\033[94m[PREVIEW]\033[0m"
                    print(f"{prefix} {tag}    {filename} - {msg}")
                elif status == 'DERIVATIVES_EXIST':
                    print(f"{prefix} \033[90m[PREVIEWS_OK]\033[0m {filename} - {msg}")

    print("\n" + "-" * 78)
    print(" Summary:")
    print(f" - Total files scanned : {len(files)}")
    if do_faststart_only:
        print(f" - +faststart optimized: {stats['PROCESSED']}")
        print(f" - Already optimized   : {stats['SKIPPED']}")
    else:
        print(f" - Repaired streams    : {stats['REPAIRED']}")
        print(f" - Generated previews  : {stats['PREVIEWS']}")
        print(f" - Already optimal     : {stats['SKIPPED']}")
    if stats['ERRORS'] > 0:
        print(f" - Errors encountered  : {stats['ERRORS']}")
    print("-" * 78)

if __name__ == "__main__":
    main()
