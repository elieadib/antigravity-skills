"""
Universal Render Engine for Cinematic Slideshow Agent.
Detects fastest hardware encoder (NVENC -> QSV -> AMF -> libx264 fallback).
Executes dual-layer video and photo compositing with prominent 30px white borders,
pronounced alternating 2.5D Ken Burns motion, xfade transitions, acrossfade audio, and film grading.
"""
import os
import sys
import json
import subprocess
import compositor

def detect_best_encoder():
    """Detects available hardware video encoders and returns the best option."""
    encoders = [
        ("h264_nvenc", ["-preset", "p6", "-cq", "19"]),
        ("h264_videotoolbox", ["-q:v", "65"]),
        ("h264_qsv", ["-global_quality", "20"]),
        ("h264_amf", ["-quality", "balanced", "-qp_i", "19"]),
        ("libx264", ["-preset", "fast", "-crf", "19"])
    ]
    for enc, extra in encoders:
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=640x360:d=0.1", "-c:v", enc, *extra, "-f", "null", "-"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                return enc, extra
        except Exception:
            pass
    return "libx264", ["-preset", "medium", "-crf", "19"]

def run_cmd(cmd, desc=""):
    """Executes a command line tool with error handling."""
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"\nError during {desc}:")
        print(res.stderr[-800:])
        raise RuntimeError(f"Command failed: {' '.join(cmd[:6])}...")
    return res

def get_video_info(path):
    """Probes video dimensions, duration, rotation, and audio stream,
    detecting whether it is vertical (natively or pillarboxed)."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=codec_type,width,height,duration,tags,side_data_list",
        "-of", "json", path
    ]
    w, h = 3840, 2160
    has_audio = False
    dur = 5.0
    rot = 0
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        for st in streams:
            if st.get("codec_type") == "video":
                w = int(st.get("width", 3840))
                h = int(st.get("height", 2160))
                dur = float(st.get("duration", dur))
                tags = st.get("tags", {})
                if "rotate" in tags:
                    try:
                        rot = int(tags["rotate"])
                    except Exception:
                        pass
                for sd in st.get("side_data_list", []):
                    if "rotation" in sd:
                        try:
                            rot = int(sd["rotation"])
                        except Exception:
                            pass
            elif st.get("codec_type") == "audio":
                has_audio = True
    except Exception:
        pass

    if rot in [90, 270, -90]:
        w, h = h, w

    crop_filter = None
    is_vertical = h > w

    # If container is horizontal (w > h), check if it has hardcoded black pillarbox bars
    if not is_vertical and w > h:
        check_time = min(1.0, dur / 2.0)
        cmd_crop = [
            "ffmpeg", "-ss", f"{check_time:.2f}",
            "-i", path, "-vframes", "10",
            "-vf", "cropdetect=24:16:0", "-f", "null", "-"
        ]
        try:
            res_crop = subprocess.run(cmd_crop, capture_output=True, text=True)
            lines = [l for l in res_crop.stderr.split("\n") if "crop=" in l]
            if lines:
                last = lines[-1]
                idx = last.find("crop=")
                crop_val = last[idx + 5:].split()[0]
                cw, ch, cx, cy = [int(x) for x in crop_val.split(":")]
                if ch > cw * 1.05 and cw < w * 0.85:
                    is_vertical = True
                    crop_filter = f"crop={cw}:{ch}:{cx}:{cy}"
        except Exception:
            pass

    return {
        "width": w, "height": h, "is_vertical": is_vertical,
        "crop_filter": crop_filter, "has_audio": has_audio, "duration": dur
    }

def is_valid_clip(filepath):
    """Checks if clip file exists and is non-empty."""
    return os.path.exists(filepath) and os.path.getsize(filepath) > 50000

def render_black_clip(shot, out_clip, width, height, fps, encoder, enc_args):
    dur = shot["duration"]
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:r={fps}:d={dur}",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", str(dur),
        "-c:v", encoder, *enc_args,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        out_clip
    ]
    run_cmd(cmd, f"Rendering black clip {out_clip}")

def render_title_clip(shot, out_clip, cache_dir, width, height, fps, encoder, enc_args,
                      title_center, title_date, border_px=30, letterbox_bars=0, margin=80):
    bg_frame = os.path.join(cache_dir, "title_bg.jpg")
    fg_frame = os.path.join(cache_dir, "title_fg.jpg")

    target_w, target_h = compositor.prepare_title_layers(
        shot["path"], bg_frame, fg_frame,
        width=width, height=height, title_center=title_center,
        title_bottom_right=title_date, border_px=border_px,
        blur_radius=35, letterbox_bars=letterbox_bars, margin=margin
    )

    dur = shot["duration"]
    frames = int(dur * fps)
    pad_w = target_w + (border_px * 2)
    pad_h = target_h + (border_px * 2)

    vf = (
        f"[1:v]zoompan=z='min(pzoom+0.0003,1.04)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={target_w}x{target_h}:fps={fps},"
        f"pad={pad_w}:{pad_h}:{border_px}:{border_px}:color=white[bordered];"
        f"[0:v][bordered]overlay=(W-w)/2:(H-h)/2,fps={fps}[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(dur), "-i", bg_frame,
        "-loop", "1", "-t", str(dur), "-i", fg_frame,
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-filter_complex", vf,
        "-map", "[v]",
        "-map", "2:a",
        "-t", str(dur),
        "-c:v", encoder, *enc_args,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        out_clip
    ]
    run_cmd(cmd, f"Rendering title clip {out_clip}")

def render_photo_clip(shot, out_clip, cache_dir, width, height, fps, encoder, enc_args,
                      border_px=30, blur_radius=35, letterbox_bars=0, margin=80):
    shot_id = shot["shot_id"]
    bg_frame = os.path.join(cache_dir, f"bg_{shot_id:03d}.jpg")
    fg_frame = os.path.join(cache_dir, f"fg_{shot_id:03d}.jpg")

    target_w, target_h = compositor.prepare_photo_layers(
        shot["path"], bg_frame, fg_frame,
        width=width, height=height, border_px=border_px,
        blur_radius=blur_radius, letterbox_bars=letterbox_bars, margin=margin
    )

    dur = shot["duration"]
    frames = int(dur * fps)
    motion = shot.get("motion", "zoom_in_center")

    if motion == "zoom_in_center":
        z = 'min(pzoom+0.0019,1.20)'
        x = 'iw/2-(iw/zoom/2)'
        y = 'ih/2-(ih/zoom/2)'
    elif motion in ["zoom_out_center", "zoom_out_wide"]:
        z = 'if(lte(pzoom,1.0),1.20,max(1.01,pzoom-0.0019))'
        x = 'iw/2-(iw/zoom/2)'
        y = 'ih/2-(ih/zoom/2)'
    elif motion == "pan_left_to_right":
        z = '1.16'
        x = f'(iw/2-(iw/zoom/2))+((on/{frames})-0.5)*(iw*0.12)'
        y = 'ih/2-(ih/zoom/2)'
    elif motion == "pan_right_to_left":
        z = '1.16'
        x = f'(iw/2-(iw/zoom/2))-((on/{frames})-0.5)*(iw*0.12)'
        y = 'ih/2-(ih/zoom/2)'
    elif motion == "push_in_diagonal":
        z = 'min(pzoom+0.0018,1.18)'
        x = f'(iw/2-(iw/zoom/2))+((on/{frames})-0.5)*(iw*0.08)'
        y = f'(ih/2-(ih/zoom/2))+((on/{frames})-0.5)*(iw*0.08)'
    else:
        z = 'min(pzoom+0.0019,1.20)'
        x = 'iw/2-(iw/zoom/2)'
        y = 'ih/2-(ih/zoom/2)'

    pad_w = target_w + (border_px * 2)
    pad_h = target_h + (border_px * 2)

    vf = (
        f"[1:v]zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={target_w}x{target_h}:fps={fps},"
        f"pad={pad_w}:{pad_h}:{border_px}:{border_px}:color=white[bordered];"
        f"[0:v][bordered]overlay=(W-w)/2:(H-h)/2,fps={fps}[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(dur), "-i", bg_frame,
        "-loop", "1", "-t", str(dur), "-i", fg_frame,
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-filter_complex", vf,
        "-map", "[v]",
        "-map", "2:a",
        "-t", str(dur),
        "-c:v", encoder, *enc_args,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        out_clip
    ]
    run_cmd(cmd, f"Rendering photo clip {out_clip}")

def render_video_clip(shot, out_clip, width, height, fps, encoder, enc_args, border_px=30, margin=80):
    dur = shot["duration"]
    path = shot["path"]
    info = get_video_info(path)

    max_box_w = width - (2 * margin)
    max_box_h = height - (2 * margin)
    fg_w = max(100, max_box_w - (border_px * 2))
    fg_h = max(100, max_box_h - (border_px * 2))

    pre_crop = f"{info['crop_filter']}," if info.get("crop_filter") else ""

    filter_str = (
        f"[0:v]{pre_crop}split=2[fg][bg];"
        f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},boxblur=35:3,eq=brightness=-0.35[blurred];"
        f"[fg]scale={fg_w}:{fg_h}:force_original_aspect_ratio=decrease,pad=iw+{border_px*2}:ih+{border_px*2}:{border_px}:{border_px}:color=white[bordered];"
        f"[blurred][bordered]overlay=(W-w)/2:(H-h)/2,fps={fps}[v]"
    )

    fade_out_start = max(0, dur - 0.5)

    if info["has_audio"]:
        af = f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo,afade=t=in:ss=0:d=0.5,afade=t=out:st={fade_out_start:.2f}:d=0.5[a]"
        inputs = ["-i", path]
        fc = f"{filter_str};{af}"
    else:
        inputs = ["-i", path, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        fc = filter_str

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", fc,
        "-map", "[v]",
        "-map", "[a]" if info["has_audio"] else "1:a",
        "-t", str(dur),
        "-c:v", encoder, *enc_args,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        out_clip
    ]
    run_cmd(cmd, f"Rendering video clip {out_clip}")

def stitch_batch(clips, transitions, out_file, encoder, enc_args, apply_grade=False):
    """Stitches a list of clips together using xfade and acrossfade."""
    if len(clips) == 1:
        cmd = ["ffmpeg", "-y", "-i", clips[0], "-c", "copy", out_file]
        run_cmd(cmd, f"Copying single clip to {out_file}")
        return

    inputs = []
    for c in clips:
        inputs.extend(["-i", c])

    durations = []
    for c in clips:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", c],
            capture_output=True, text=True
        )
        data = json.loads(res.stdout)
        durations.append(float(data["format"]["duration"]))

    v_nodes = ["[0:v]"]
    a_nodes = ["[0:a]"]
    filter_parts = []

    cum_duration = durations[0]
    td = 0.8

    for i in range(len(clips) - 1):
        trans = transitions[i] if i < len(transitions) else "fade"
        if trans not in ["fade", "fadewhite", "smoothleft", "smoothright", "fadeblack"]:
            trans = "fade"

        offset = cum_duration - td
        next_v = f"[v{i+1}]"
        next_a = f"[a{i+1}]"

        prev_v = v_nodes[-1]
        prev_a = a_nodes[-1]

        v_filter = f"{prev_v}[{i+1}:v]xfade=transition={trans}:duration={td}:offset={offset:.3f}{next_v}"
        a_filter = f"{prev_a}[{i+1}:a]acrossfade=d={td}{next_a}"

        filter_parts.append(v_filter)
        filter_parts.append(a_filter)

        v_nodes.append(next_v)
        a_nodes.append(next_a)

        cum_duration = cum_duration + durations[i+1] - td

    final_v = v_nodes[-1]
    final_a = a_nodes[-1]

    if apply_grade:
        color_grade = "colorbalance=rs=0.03:gs=0.01:bs=-0.02:rm=0.03:gm=0.01:bm=-0.02,eq=contrast=1.04:saturation=1.08,noise=alls=3:allf=t+u"
        filter_parts.append(f"{final_v}{color_grade}[outv]")
        map_v = "[outv]"
    else:
        map_v = final_v

    full_filter = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", full_filter,
        "-map", map_v, "-map", final_a,
        "-c:v", encoder, *enc_args,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        out_file
    ]
    run_cmd(cmd, f"Stitching batch to {out_file}")

def render_movie(timeline, output_file, temp_dir, width=3840, height=2160, fps=24,
                 border_px=30, letterbox_bars=0, title_center="Vacation 2026", title_date="", margin=80):
    """Orchestrates clip rendering, chunk stitching, and final movie creation."""
    encoder, enc_args = detect_best_encoder()
    print(f"Using video encoder: {encoder} {enc_args}")

    clips_dir = os.path.join(temp_dir, "clips")
    cache_dir = os.path.join(temp_dir, "cache")
    os.makedirs(clips_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    rendered_clips = []
    transitions = []
    total = len(timeline)

    print(f"Rendering {total} shots with {border_px}px white border and dynamic Ken Burns...")
    for idx, shot in enumerate(timeline):
        s_id = shot["shot_id"]
        s_type = shot["type"]
        out_clip = os.path.join(clips_dir, f"clip_{s_id:03d}.mp4")

        print(f"[{idx+1}/{total}] Shot #{s_id} ({s_type}, dur={shot.get('duration')}s): {shot.get('filename', 'solid')}")

        if not is_valid_clip(out_clip):
            if s_type == "black_intro" or s_type == "black_outro":
                render_black_clip(shot, out_clip, width, height, fps, encoder, enc_args)
            elif s_type == "title_slide":
                render_title_clip(shot, out_clip, cache_dir, width, height, fps, encoder, enc_args, title_center, title_date, border_px, letterbox_bars, margin=margin)
            elif s_type == "photo":
                render_photo_clip(shot, out_clip, cache_dir, width, height, fps, encoder, enc_args, border_px, 35, letterbox_bars, margin=margin)
            elif s_type == "video":
                render_video_clip(shot, out_clip, width, height, fps, encoder, enc_args, border_px, margin=margin)
        else:
            print(f"  -> Reusing cached clip: {os.path.basename(out_clip)}")

        rendered_clips.append(out_clip)
        if idx < total - 1:
            transitions.append(shot.get("transition", "fade"))

    if len(rendered_clips) <= 12:
        print("\nStitching clips into final movie...")
        stitch_batch(rendered_clips, transitions, output_file, encoder, enc_args, apply_grade=True)
    else:
        print("\nStitching in chunks...")
        chunk_size = 10
        chunk_files = []
        chunk_transitions = []

        for i in range(0, len(rendered_clips), chunk_size):
            c_clips = rendered_clips[i:i+chunk_size]
            c_trans = transitions[i:i+chunk_size-1]
            c_out = os.path.join(temp_dir, f"chunk_{i//chunk_size:02d}.mp4")
            print(f"Stitching Chunk {i//chunk_size + 1}/{(len(rendered_clips)+chunk_size-1)//chunk_size} ({len(c_clips)} clips)...")
            stitch_batch(c_clips, c_trans, c_out, encoder, enc_args, apply_grade=False)
            chunk_files.append(c_out)
            if i + chunk_size < len(rendered_clips):
                chunk_transitions.append(transitions[i+chunk_size-1])

        print("\nStitching chunks into master output with film grade...")
        stitch_batch(chunk_files, chunk_transitions, output_file, encoder, enc_args, apply_grade=True)

    print(f"\n=======================================================")
    print(f"SUCCESS! Slideshow successfully rendered at {width}x{height}:")
    print(f"{output_file}")
    print(f"=======================================================")
    return output_file
