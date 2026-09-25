#!/usr/bin/env python3
"""
Video Specs Inspector (video_specs_inspector.py)
------------------------------------------------
Scans a target directory (or individual video file) and generates a clean,
comprehensive table containing:
  - File Name
  - Resolution (Width x Height + Tag)
  - Video Codec
  - Video Bitrate in kbits/sec (kbps)
  - Audio Codec
  - Audio Bitrate in kbit/s (kbps)
  - FPS (Frame Rate)
  - Duration (HH:MM:SS)
  - File Size

Supports Markdown, Terminal Table, CSV, and JSON output formats.
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv',
    '.webm', '.m4v', '.ts', '.m2ts', '.mts', '.vob',
    '.3gp', '.ogv', '.rmvb', '.divx', '.f4v'
}

FRIENDLY_VIDEO_CODECS = {
    'h264': 'H.264 / AVC',
    'hevc': 'H.265 / HEVC',
    'av1': 'AV1',
    'vp9': 'VP9',
    'vp8': 'VP8',
    'prores': 'Apple ProRes',
    'mpeg4': 'MPEG-4',
    'mpeg2video': 'MPEG-2',
    'mjpeg': 'MJPEG',
    'theora': 'Theora',
    'vc1': 'VC-1',
    'wmv3': 'WMV3'
}

FRIENDLY_AUDIO_CODECS = {
    'aac': 'AAC',
    'ac3': 'AC-3 (Dolby Digital)',
    'eac3': 'E-AC-3 (DD+)',
    'dts': 'DTS',
    'flac': 'FLAC',
    'mp3': 'MP3',
    'opus': 'Opus',
    'vorbis': 'Vorbis',
    'truehd': 'Dolby TrueHD',
    'pcm_s16le': 'PCM 16-bit',
    'pcm_s24le': 'PCM 24-bit',
    'pcm_s32le': 'PCM 32-bit',
    'pcm_f32le': 'PCM 32-bit Float',
    'alac': 'ALAC'
}


def find_ffprobe():
    """Locates ffprobe executable across common paths and PATH."""
    probe = shutil.which('ffprobe')
    if probe:
        return probe
    candidates = [
        '/opt/homebrew/bin/ffprobe',
        '/usr/local/bin/ffprobe',
        '/usr/bin/ffprobe',
        r'C:\ffmpeg\bin\ffprobe.exe',
        r'C:\Program Files\ffmpeg\bin\ffprobe.exe',
        os.path.expanduser('~/bin/ffprobe')
    ]
    for c in candidates:
        if os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return None


def format_duration(seconds):
    """Converts seconds into HH:MM:SS or MM:SS."""
    if seconds is None:
        return "N/A"
    try:
        sec = float(seconds)
        if sec < 0:
            return "N/A"
        m, s = divmod(int(sec), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
    except (ValueError, TypeError):
        return "N/A"


def format_size(bytes_num):
    """Converts bytes to human readable string (KB, MB, GB)."""
    if bytes_num is None:
        return "N/A"
    try:
        b = float(bytes_num)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if b < 1024.0:
                if unit in ['MB', 'GB', 'TB']:
                    return f"{b:.1f} {unit}"
                return f"{int(b)} {unit}"
            b /= 1024.0
        return f"{b:.1f} PB"
    except (ValueError, TypeError):
        return "N/A"


def parse_fps(fps_str):
    """Parses fractional frame rate (e.g. 24000/1001 or 30/1) to readable string."""
    if not fps_str or fps_str == '0/0':
        return "N/A"
    try:
        if '/' in fps_str:
            num, den = fps_str.split('/')
            val = float(num) / float(den)
            return f"{val:.2f}".rstrip('0').rstrip('.') + " fps"
        return f"{float(fps_str):.2f}".rstrip('0').rstrip('.') + " fps"
    except Exception:
        return fps_str


def get_resolution_tag(width, height):
    """Returns friendly label for common video resolutions."""
    if not width or not height:
        return ""
    w, h = int(width), int(height)
    if w >= 3840 or h >= 2160:
        return " (4K UHD)"
    if w >= 2560 or h >= 1440:
        return " (1440p)"
    if w >= 1920 or h >= 1080:
        return " (1080p)"
    if w >= 1280 or h >= 720:
        return " (720p)"
    if h == 480 or h == 576:
        return " (SD)"
    return ""


def probe_video_file(file_path, ffprobe_bin):
    """Probes a single video file and returns extracted technical specs."""
    file_path = str(file_path)
    file_name = os.path.basename(file_path)
    try:
        file_size = os.path.getsize(file_path)
    except OSError:
        file_size = 0

    record = {
        'file_name': file_name,
        'file_path': file_path,
        'file_size': file_size,
        'file_size_str': format_size(file_size),
        'resolution': 'N/A',
        'width': 0,
        'height': 0,
        'v_codec': 'N/A',
        'v_bitrate_kbps': None,
        'v_bitrate_str': 'N/A',
        'a_codec': 'None',
        'a_bitrate_kbps': None,
        'a_bitrate_str': 'N/A',
        'fps_str': 'N/A',
        'fps_val': 0.0,
        'duration_sec': None,
        'duration_str': 'N/A',
        'error': None
    }

    cmd = [
        ffprobe_bin,
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        file_path
    ]

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        if proc.returncode != 0:
            record['error'] = f"ffprobe exit code {proc.returncode}"
            return record

        data = json.loads(proc.stdout)
    except subprocess.TimeoutExpired:
        record['error'] = "ffprobe timeout (30s)"
        return record
    except Exception as e:
        record['error'] = str(e)
        return record

    streams = data.get('streams', [])
    fmt = data.get('format', {})

    # Extract overall duration
    duration = None
    if fmt.get('duration'):
        try:
            duration = float(fmt['duration'])
        except (ValueError, TypeError):
            pass

    # Video streams (filter out attached image covers / posters)
    video_streams = [
        s for s in streams
        if s.get('codec_type') == 'video' and not s.get('disposition', {}).get('attached_pic')
    ]
    # Audio streams
    audio_streams = [s for s in streams if s.get('codec_type') == 'audio']

    # Process Video Stream
    if video_streams:
        v = video_streams[0]
        raw_v_codec = v.get('codec_name', '').lower()
        friendly_v_codec = FRIENDLY_VIDEO_CODECS.get(raw_v_codec, raw_v_codec.upper() if raw_v_codec else 'Unknown')
        
        # Check profile / 10-bit
        pix_fmt = v.get('pix_fmt', '')
        bits = v.get('bits_per_raw_sample')
        if '10' in pix_fmt or bits == '10':
            friendly_v_codec += ' 10-bit'

        record['v_codec'] = friendly_v_codec

        width = v.get('width', 0)
        height = v.get('height', 0)
        record['width'] = width
        record['height'] = height
        if width and height:
            tag = get_resolution_tag(width, height)
            record['resolution'] = f"{width}x{height}{tag}"

        # FPS
        fps_raw = v.get('r_frame_rate') or v.get('avg_frame_rate')
        record['fps_str'] = parse_fps(fps_raw)
        try:
            if '/' in fps_raw:
                n, d = fps_raw.split('/')
                record['fps_val'] = float(n) / float(d) if float(d) != 0 else 0.0
            else:
                record['fps_val'] = float(fps_raw)
        except Exception:
            record['fps_val'] = 0.0

        # Video stream duration fallback
        if duration is None and v.get('duration'):
            try:
                duration = float(v['duration'])
            except (ValueError, TypeError):
                pass

        # Video Bitrate calculation (kbits/sec)
        v_bitrate_num = None
        is_approx = False

        # 1. Direct stream bit_rate
        if v.get('bit_rate') and str(v['bit_rate']).isdigit() and int(v['bit_rate']) > 0:
            v_bitrate_num = int(v['bit_rate'])
        
        # 2. Stream tags BPS
        if v_bitrate_num is None:
            tags = v.get('tags', {})
            bps = tags.get('BPS') or tags.get('BPS-eng') or tags.get('bps')
            if bps and str(bps).isdigit() and int(bps) > 0:
                v_bitrate_num = int(bps)
        
        # 3. Stream tags NUMBER_OF_BYTES & duration
        if v_bitrate_num is None and duration and duration > 0:
            tags = v.get('tags', {})
            num_bytes = tags.get('NUMBER_OF_BYTES') or tags.get('NUMBER_OF_BYTES-eng')
            if num_bytes and str(num_bytes).isdigit():
                v_bitrate_num = int((int(num_bytes) * 8) / duration)

        # 4. Container fallback (format bitrate minus audio bitrates)
        if v_bitrate_num is None and fmt.get('bit_rate') and str(fmt['bit_rate']).isdigit():
            container_bps = int(fmt['bit_rate'])
            # Sum audio stream bitrates if available
            audio_bps_sum = 0
            for a_s in audio_streams:
                if a_s.get('bit_rate') and str(a_s['bit_rate']).isdigit():
                    audio_bps_sum += int(a_s['bit_rate'])
                else:
                    a_tags = a_s.get('tags', {})
                    a_bps = a_tags.get('BPS') or a_tags.get('BPS-eng')
                    if a_bps and str(a_bps).isdigit():
                        audio_bps_sum += int(a_bps)
            
            if container_bps > audio_bps_sum and audio_bps_sum > 0:
                v_bitrate_num = container_bps - audio_bps_sum
                is_approx = True
            elif container_bps > 0:
                v_bitrate_num = container_bps
                is_approx = True

        if v_bitrate_num and v_bitrate_num > 0:
            kbps = round(v_bitrate_num / 1000)
            record['v_bitrate_kbps'] = kbps
            prefix = "~" if is_approx else ""
            record['v_bitrate_str'] = f"{prefix}{kbps:,} kb/s"
        else:
            record['v_bitrate_str'] = "N/A"

    # Process Audio Streams
    if audio_streams:
        audio_codecs = []
        audio_bitrates_kbps = []
        audio_bitrates_str = []

        for idx, a in enumerate(audio_streams):
            raw_a_codec = a.get('codec_name', '').lower()
            friendly_a_codec = FRIENDLY_AUDIO_CODECS.get(raw_a_codec, raw_a_codec.upper() if raw_a_codec else 'Unknown')
            
            # Channels
            channels = a.get('channels')
            layout = a.get('channel_layout')
            if layout:
                friendly_a_codec += f" ({layout})"
            elif channels:
                friendly_a_codec += f" ({channels}ch)"

            audio_codecs.append(friendly_a_codec)

            # Audio bitrate
            a_bitrate_num = None
            if a.get('bit_rate') and str(a['bit_rate']).isdigit() and int(a['bit_rate']) > 0:
                a_bitrate_num = int(a['bit_rate'])
            else:
                a_tags = a.get('tags', {})
                a_bps = a_tags.get('BPS') or a_tags.get('BPS-eng') or a_tags.get('bps')
                if a_bps and str(a_bps).isdigit() and int(a_bps) > 0:
                    a_bitrate_num = int(a_bps)
                elif duration and duration > 0:
                    num_bytes = a_tags.get('NUMBER_OF_BYTES') or a_tags.get('NUMBER_OF_BYTES-eng')
                    if num_bytes and str(num_bytes).isdigit():
                        a_bitrate_num = int((int(num_bytes) * 8) / duration)

            if a_bitrate_num and a_bitrate_num > 0:
                a_kbps = round(a_bitrate_num / 1000)
                audio_bitrates_kbps.append(a_kbps)
                audio_bitrates_str.append(f"{a_kbps:,} kb/s")
            else:
                audio_bitrates_str.append("N/A")

        # Format combined audio info
        if len(audio_streams) == 1:
            record['a_codec'] = audio_codecs[0]
            record['a_bitrate_str'] = audio_bitrates_str[0]
            if audio_bitrates_kbps:
                record['a_bitrate_kbps'] = audio_bitrates_kbps[0]
        else:
            record['a_codec'] = f"{audio_codecs[0]} [+{len(audio_streams)-1} trk]"
            record['a_bitrate_str'] = f"{audio_bitrates_str[0]} [+{len(audio_streams)-1} trk]"
            if audio_bitrates_kbps:
                record['a_bitrate_kbps'] = audio_bitrates_kbps[0]
    else:
        record['a_codec'] = "None"
        record['a_bitrate_str'] = "-"
        record['a_bitrate_kbps'] = 0

    record['duration_sec'] = duration
    record['duration_str'] = format_duration(duration)

    return record


def scan_directory(target_path, recursive=False, min_size_bytes=0):
    """Discovers all video files in target directory or returns single file."""
    p = Path(target_path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Path does not exist: {target_path}")

    if p.is_file():
        if p.suffix.lower() in VIDEO_EXTENSIONS:
            return [p]
        else:
            return [p]  # Try probing anyway if explicitly given

    video_files = []
    if recursive:
        for root, _, files in os.walk(p):
            for f in sorted(files):
                if f.startswith('.'):
                    continue
                ext = Path(f).suffix.lower()
                if ext in VIDEO_EXTENSIONS:
                    full_p = Path(root) / f
                    if min_size_bytes > 0:
                        try:
                            if full_p.stat().st_size < min_size_bytes:
                                continue
                        except OSError:
                            continue
                    video_files.append(full_p)
    else:
        for item in sorted(p.iterdir()):
            if item.name.startswith('.'):
                continue
            if item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS:
                if min_size_bytes > 0:
                    try:
                        if item.stat().st_size < min_size_bytes:
                            continue
                    except OSError:
                        continue
                video_files.append(item)

    return video_files


def render_markdown_table(records, show_summary=True):
    """Generates standard GitHub flavored Markdown table."""
    headers = [
        "File Name",
        "Resolution",
        "Video Codec",
        "Video (kb/s)",
        "Audio Codec",
        "Audio (kb/s)",
        "FPS",
        "Duration",
        "Size"
    ]
    alignments = [":---", ":---:", ":---:", "---:", ":---:", "---:", "---:", "---:", "---:"]

    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(alignments) + " |")

    for r in records:
        row = [
            r['file_name'],
            r['resolution'],
            r['v_codec'],
            r['v_bitrate_str'],
            r['a_codec'],
            r['a_bitrate_str'],
            r['fps_str'],
            r['duration_str'],
            r['file_size_str']
        ]
        lines.append("| " + " | ".join(row) + " |")

    if show_summary and records:
        total_files = len(records)
        total_size = sum(r['file_size'] for r in records)
        durations = [r['duration_sec'] for r in records if r['duration_sec'] is not None]
        total_duration = sum(durations) if durations else None
        v_bitrates = [r['v_bitrate_kbps'] for r in records if r['v_bitrate_kbps']]
        avg_v_bitrate = round(sum(v_bitrates) / len(v_bitrates)) if v_bitrates else None

        summary_rows = [
            f"**Total Videos**: {total_files}",
            f"**Total Size**: {format_size(total_size)}",
            f"**Total Duration**: {format_duration(total_duration)}",
        ]
        if avg_v_bitrate:
            summary_rows.append(f"**Average Video Bitrate**: {avg_v_bitrate:,} kb/s")

        lines.append("")
        lines.append("### Summary Statistics")
        for s in summary_rows:
            lines.append(f"- {s}")

    return "\n".join(lines)


def render_terminal_table(records, show_summary=True):
    """Generates a bordered ASCII/Unicode table for clean CLI display."""
    headers = [
        "File Name",
        "Resolution",
        "Video Codec",
        "Video (kb/s)",
        "Audio Codec",
        "Audio (kb/s)",
        "FPS",
        "Duration",
        "Size"
    ]

    raw_rows = []
    for r in records:
        raw_rows.append([
            r['file_name'],
            r['resolution'],
            r['v_codec'],
            r['v_bitrate_str'],
            r['a_codec'],
            r['a_bitrate_str'],
            r['fps_str'],
            r['duration_str'],
            r['file_size_str']
        ])

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in raw_rows:
        for idx, cell in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(str(cell)))

    # Truncate filename width if overly wide (> 45 chars)
    if col_widths[0] > 45:
        col_widths[0] = 45

    def fit_cell(val, width, align='left'):
        val_str = str(val)
        if len(val_str) > width:
            val_str = val_str[:width - 3] + "..."
        if align == 'right':
            return val_str.rjust(width)
        elif align == 'center':
            return val_str.center(width)
        return val_str.ljust(width)

    aligns = ['left', 'center', 'center', 'right', 'center', 'right', 'right', 'right', 'right']

    sep_line = "+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+"
    header_line = "| " + " | ".join([fit_cell(h, col_widths[i], aligns[i]) for i, h in enumerate(headers)]) + " |"

    output_lines = [sep_line, header_line, sep_line]
    for row in raw_rows:
        row_str = "| " + " | ".join([fit_cell(cell, col_widths[i], aligns[i]) for i, cell in enumerate(row)]) + " |"
        output_lines.append(row_str)
    output_lines.append(sep_line)

    if show_summary and records:
        total_files = len(records)
        total_size = sum(r['file_size'] for r in records)
        durations = [r['duration_sec'] for r in records if r['duration_sec'] is not None]
        total_duration = sum(durations) if durations else None
        v_bitrates = [r['v_bitrate_kbps'] for r in records if r['v_bitrate_kbps']]
        avg_v_bitrate = round(sum(v_bitrates) / len(v_bitrates)) if v_bitrates else None

        output_lines.append("")
        output_lines.append(f"Summary: {total_files} videos | Total Size: {format_size(total_size)} | Total Duration: {format_duration(total_duration)}" +
                            (f" | Avg Video Bitrate: {avg_v_bitrate:,} kb/s" if avg_v_bitrate else ""))

    return "\n".join(output_lines)


def render_csv(records):
    """Generates standard CSV content."""
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "File Name",
        "Path",
        "Resolution",
        "Width",
        "Height",
        "Video Codec",
        "Video Bitrate (kbps)",
        "Audio Codec",
        "Audio Bitrate (kbps)",
        "FPS",
        "Duration",
        "Duration Seconds",
        "Size",
        "Size Bytes"
    ])
    for r in records:
        writer.writerow([
            r['file_name'],
            r['file_path'],
            r['resolution'],
            r['width'],
            r['height'],
            r['v_codec'],
            r['v_bitrate_kbps'] or "",
            r['a_codec'],
            r['a_bitrate_kbps'] or "",
            r['fps_str'],
            r['duration_str'],
            r['duration_sec'] or "",
            r['file_size_str'],
            r['file_size']
        ])
    return output.getvalue()


def parse_min_size(size_str):
    """Parses size string like '10MB', '500KB' into integer bytes."""
    if not size_str:
        return 0
    size_str = size_str.strip().upper()
    try:
        if size_str.endswith('GB'):
            return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
        if size_str.endswith('MB'):
            return int(float(size_str[:-2]) * 1024 * 1024)
        if size_str.endswith('KB'):
            return int(float(size_str[:-2]) * 1024)
        if size_str.endswith('B'):
            return int(size_str[:-1])
        return int(size_str)
    except ValueError:
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Inspect video files in a directory and generate a detailed specs table (Video kbps, Audio kbps, Resolution, Codec)."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to directory containing video files (or a single video file). Default: current directory."
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively scan subdirectories for video files."
    )
    parser.add_argument(
        "--format",
        choices=["md", "table", "csv", "json"],
        default="md",
        help="Output format: 'md' (Markdown, default), 'table' (CLI border table), 'csv', or 'json'."
    )
    parser.add_argument(
        "-o", "--output",
        help="Write output table directly to the specified file path."
    )
    parser.add_argument(
        "--csv",
        help="Shortcut to export results directly to a CSV file path."
    )
    parser.add_argument(
        "--md",
        help="Shortcut to export results directly to a Markdown (.md) file path."
    )
    parser.add_argument(
        "--sort",
        choices=["name", "vbitrate", "abitrate", "resolution", "size", "duration", "fps"],
        default="name",
        help="Sort column (default: name)."
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Reverse sort order."
    )
    parser.add_argument(
        "--min-size",
        help="Minimum file size to include (e.g. '1MB', '500KB')."
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Omit the summary statistics block."
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=4,
        help="Number of concurrent worker threads for ffprobe (default: 4)."
    )

    args = parser.parse_args()

    ffprobe_bin = find_ffprobe()
    if not ffprobe_bin:
        sys.stderr.write("Error: ffprobe is not installed or not found in PATH.\n")
        sys.stderr.write("Please install ffmpeg (brew install ffmpeg on macOS or download ffmpeg on Windows).\n")
        sys.exit(1)

    min_size_bytes = parse_min_size(args.min_size)

    try:
        video_files = scan_directory(args.path, recursive=args.recursive, min_size_bytes=min_size_bytes)
    except FileNotFoundError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    if not video_files:
        sys.stderr.write(f"No video files found in: {args.path}\n")
        sys.exit(0)

    # Multi-threaded ffprobe analysis
    records = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        future_to_file = {executor.submit(probe_video_file, f, ffprobe_bin): f for f in video_files}
        for future in as_completed(future_to_file):
            try:
                rec = future.result()
                records.append(rec)
            except Exception as exc:
                f = future_to_file[future]
                sys.stderr.write(f"Warning: Failed to inspect {f}: {exc}\n")

    # Sorting
    if args.sort == 'name':
        records.sort(key=lambda r: r['file_name'].lower(), reverse=args.reverse)
    elif args.sort == 'vbitrate':
        records.sort(key=lambda r: r['v_bitrate_kbps'] or 0, reverse=args.reverse)
    elif args.sort == 'abitrate':
        records.sort(key=lambda r: r['a_bitrate_kbps'] or 0, reverse=args.reverse)
    elif args.sort == 'resolution':
        records.sort(key=lambda r: (r['width'] * r['height']), reverse=args.reverse)
    elif args.sort == 'size':
        records.sort(key=lambda r: r['file_size'], reverse=args.reverse)
    elif args.sort == 'duration':
        records.sort(key=lambda r: r['duration_sec'] or 0.0, reverse=args.reverse)
    elif args.sort == 'fps':
        records.sort(key=lambda r: r['fps_val'], reverse=args.reverse)

    # Determine output format and render
    output_format = args.format
    if args.csv:
        output_format = "csv"
    elif args.md:
        output_format = "md"

    show_summary = not args.no_summary

    if output_format == "csv":
        result_text = render_csv(records)
    elif output_format == "json":
        result_text = json.dumps(records, indent=2)
    elif output_format == "table":
        result_text = render_terminal_table(records, show_summary=show_summary)
    else:  # md (default)
        result_text = render_markdown_table(records, show_summary=show_summary)

    # Handle file outputs
    target_output_file = args.output or args.csv or args.md
    if target_output_file:
        out_path = Path(target_output_file).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as out_f:
            out_f.write(result_text)
            if not result_text.endswith('\n'):
                out_f.write('\n')
        print(f"Results written to: {out_path}")
        # Also print to terminal if user requested output file
        print(result_text)
    else:
        print(result_text)


if __name__ == "__main__":
    main()
