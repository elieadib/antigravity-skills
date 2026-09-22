"""
High-Resolution Frame Compositor for Cinematic Slideshow Agent.
Handles EXIF auto-orientation, title slide typography (center title + bottom-right date),
dual-layer blurred matching backdrops for vertical and horizontal media,
prominent 30px white borders, and optional letterbox matting.
"""
import os
import subprocess
import wave
import struct
import random
import math
from PIL import Image, ImageOps, ImageFilter, ImageDraw, ImageFont

def get_font(font_name="georgiab.ttf", size=100):
    """Safely retrieves a font across Windows, macOS, and Linux or falls back gracefully."""
    font_paths = [
        # Windows
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", font_name),
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arialbd.ttf"),
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf"),
        # macOS
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()

def create_black_frame(width, height, output_path):
    """Creates a pure black frame at target resolution."""
    canvas = Image.new("RGB", (width, height), (0, 0, 0))
    canvas.save(output_path, quality=95)
    return output_path

def wrap_text_to_lines(text, font, max_width):
    """Wraps text into balanced lines if it exceeds max_width."""
    if not text:
        return []
    if "\n" in text:
        return text.split("\n")
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    if tw <= max_width:
        return [text]
    words = text.split(" ")
    if len(words) <= 1:
        return [text]
    best_split = 1
    min_diff = float("inf")
    for i in range(1, len(words)):
        l1 = " ".join(words[:i])
        l2 = " ".join(words[i:])
        w1 = font.getbbox(l1)[2] - font.getbbox(l1)[0]
        w2 = font.getbbox(l2)[2] - font.getbbox(l2)[0]
        if w1 <= max_width and w2 <= max_width:
            diff = abs(w1 - w2)
            if diff < min_diff:
                min_diff = diff
                best_split = i
    if min_diff < float("inf"):
        return [" ".join(words[:best_split]), " ".join(words[best_split:])]
    lines = []
    curr = []
    for w in words:
        test = " ".join(curr + [w])
        if (font.getbbox(test)[2] - font.getbbox(test)[0]) <= max_width:
            curr.append(w)
        else:
            if curr:
                lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))
    return lines

def prepare_title_layers(cover_path, bg_output_path, fg_output_path,
                         width=3840, height=2160, title_center="Vacation 2026",
                         title_bottom_right="", border_px=30, blur_radius=35,
                         letterbox_bars=0, margin=80):
    """
    Prepares title slide layers:
    1. bg_output_path: Blurred, dimmed 4K matching background.
    2. fg_output_path: Resized clean cover photo with atmospheric tone (no baked text).
    Returns: (target_w, target_h, layout_info)
    """
    img = Image.open(cover_path).convert("RGB")
    img = ImageOps.exif_transpose(img)
    iw, ih = img.size

    active_h = height - (2 * letterbox_bars)

    # 1. Background
    bg_scale = max(width / iw, height / ih)
    bg_w, bg_h = int(iw * bg_scale), int(ih * bg_scale)
    bg = img.resize((bg_w, bg_h), Image.Resampling.BILINEAR)
    x0 = (bg_w - width) // 2
    y0 = (bg_h - height) // 2
    bg_cropped = bg.crop((x0, y0, x0 + width, y0 + height))
    bg_blurred = bg_cropped.filter(ImageFilter.BoxBlur(blur_radius))

    is_portrait = ih > iw
    dim_factor = 0.65 if is_portrait else 0.45
    bg_dimmed = Image.eval(bg_blurred, lambda val: int(val * dim_factor))

    if letterbox_bars > 0:
        draw = ImageDraw.Draw(bg_dimmed)
        draw.rectangle([0, 0, width, letterbox_bars], fill="black")
        draw.rectangle([0, height - letterbox_bars, width, height], fill="black")

    bg_dimmed.save(bg_output_path, quality=95)

    # 2. Foreground sizing (80px margin around the white box)
    max_box_w = width - (2 * margin)
    max_box_h = active_h - (2 * margin)
    max_fg_w = max(100, max_box_w - (border_px * 2))
    max_fg_h = max(100, max_box_h - (border_px * 2))
    scale = min(max_fg_w / iw, max_fg_h / ih)

    target_w = (int(iw * scale) // 2) * 2
    target_h = (int(ih * scale) // 2) * 2

    fg_resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

    # Subtle dark overlay over cover image for typography contrast
    overlay = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 75))
    fg_rgba = fg_resized.convert("RGBA")
    fg_rgba.paste(overlay, (0, 0), overlay)

    # Save clean foreground photo (without baked text)
    fg_rgba.convert("RGB").save(fg_output_path, quality=95)

    # Typography sizing proportional to photo height (50% bigger)
    center_font_size = int(target_h * 0.0825)
    date_font_size = int(target_h * 0.048)

    font_center = get_font("georgiab.ttf", center_font_size)
    font_date = get_font("georgia.ttf", date_font_size)

    lines_center = wrap_text_to_lines(title_center, font_center, int(target_w * 0.88))
    line_positions = []
    if lines_center:
        line_heights = []
        for line in lines_center:
            bb = font_center.getbbox(line)
            line_heights.append(bb[3] - bb[1])
        line_spacing = int(center_font_size * 0.25)
        total_text_h = sum(line_heights) + line_spacing * (len(lines_center) - 1)
        y_curr = (height - total_text_h) // 2
        for idx, line in enumerate(lines_center):
            bb = font_center.getbbox(line)
            lw = bb[2] - bb[0]
            lx = (width - lw) // 2
            line_positions.append({
                "text": line,
                "x": lx,
                "y": y_curr,
                "w": lw,
                "h": line_heights[idx]
            })
            y_curr += line_heights[idx] + line_spacing

    photo_x2 = (width + target_w) // 2
    photo_y2 = (height + target_h) // 2
    if title_bottom_right:
        bbox_d = font_date.getbbox(title_bottom_right)
        tw_d, th_d = bbox_d[2] - bbox_d[0], bbox_d[3] - bbox_d[1]
        rx = photo_x2 - tw_d - int(target_w * 0.04)
        ry = photo_y2 - th_d - int(target_h * 0.05)
    else:
        rx, ry, tw_d, th_d = 0, 0, 0, 0

    layout_info = {
        "target_w": target_w,
        "target_h": target_h,
        "center_font_size": center_font_size,
        "date_font_size": date_font_size,
        "line_positions": line_positions,
        "x_c": line_positions[0]["x"] if line_positions else width // 2,
        "y_c": line_positions[0]["y"] if line_positions else height // 2,
        "rx": rx,
        "ry": ry,
        "title_center": title_center,
        "title_date": title_bottom_right
    }

    return target_w, target_h, layout_info

def generate_typewriter_overlay(output_path, layout_info, dur=9.0, fps=24, width=3840, height=2160):
    """
    Generates an RGBA transparent QuickTime video (.mov) with character-by-character
    typewriter animation for the title slide:
    - t = 0.0s to 2.0s: Pure transparent (clean photo displayed).
    - t = 2.0s: 1st text (centered) begins typing character-by-character.
    - t = 4.0s: 2nd text (bottom-right date) begins typing character-by-character (2s after 1st text).
    - t > typing: Both texts held with elegant drop shadow until transition.
    """
    title_center = layout_info.get("title_center", "")
    title_date = layout_info.get("title_date", "")
    center_font_size = layout_info.get("center_font_size", 150)
    date_font_size = layout_info.get("date_font_size", 90)
    line_positions = layout_info.get("line_positions", [])
    if not line_positions and title_center:
        line_positions = [{
            "text": title_center,
            "x": layout_info.get("x_c", width // 2),
            "y": layout_info.get("y_c", height // 2)
        }]
    rx = layout_info.get("rx", width - 300)
    ry = layout_info.get("ry", height - 200)

    font_center = get_font("georgiab.ttf", center_font_size)
    font_date = get_font("georgia.ttf", date_font_size)

    total_frames = int(dur * fps)
    f_start1 = int(2.0 * fps)
    f_start2 = int(4.0 * fps)

    # Center text typing duration: exactly 2.0s
    total_chars1 = sum(len(lp["text"]) for lp in line_positions)
    f_dur1 = int(2.0 * fps) if total_chars1 > 0 else 1

    # Date text typing duration: exactly 2.0s
    len2 = len(title_date)
    f_dur2 = int(2.0 * fps) if len2 > 0 else 1

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{width}x{height}", "-r", str(fps),
        "-i", "-",
        "-c:v", "qtrle",
        output_path
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    empty_bytes = Image.new("RGBA", (width, height), (0, 0, 0, 0)).tobytes()
    cached_bytes = {}

    for f in range(total_frames):
        t = f / fps
        if t < 2.0 or (not line_positions and not title_date):
            proc.stdin.write(empty_bytes)
            continue

        # Substrings for title 1 lines
        if not line_positions:
            typed_lines = []
        elif f < f_start1:
            typed_lines = [""] * len(line_positions)
        elif f < f_start1 + f_dur1:
            progress1 = (f - f_start1) / f_dur1
            c1_len = max(1, min(total_chars1, int(round(progress1 * total_chars1))))
            chars_left = c1_len
            typed_lines = []
            for lp in line_positions:
                ltxt = lp["text"]
                if chars_left <= 0:
                    typed_lines.append("")
                elif chars_left >= len(ltxt):
                    typed_lines.append(ltxt)
                    chars_left -= len(ltxt)
                else:
                    typed_lines.append(ltxt[:chars_left])
                    chars_left = 0
        else:
            typed_lines = [lp["text"] for lp in line_positions]

        # Substring for title 2 (starts at t = 4.0s)
        if not title_date or f < f_start2:
            sub2 = ""
        elif f < f_start2 + f_dur2:
            progress2 = (f - f_start2) / f_dur2
            c2_len = max(1, min(len2, int(round(progress2 * len2))))
            sub2 = title_date[:c2_len]
        else:
            sub2 = title_date

        state_key = (tuple(typed_lines), sub2)
        if state_key in cached_bytes:
            proc.stdin.write(cached_bytes[state_key])
        else:
            img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            for idx, lp in enumerate(line_positions):
                sub = typed_lines[idx] if idx < len(typed_lines) else ""
                if sub:
                    draw.text((lp["x"] + 5, lp["y"] + 5), sub, font=font_center, fill=(0, 0, 0, 230))
                    draw.text((lp["x"], lp["y"]), sub, font=font_center, fill=(255, 255, 255, 255))
            if sub2:
                draw.text((rx + 4, ry + 4), sub2, font=font_date, fill=(0, 0, 0, 220))
                draw.text((rx, ry), sub2, font=font_date, fill=(245, 235, 210, 255))
            raw = img.tobytes()
            cached_bytes[state_key] = raw
            proc.stdin.write(raw)

    proc.stdin.close()
    proc.wait()
    return output_path

def generate_typewriter_audio(audio_output_path, title_center, title_date, dur=9.0, sr=48000):
    """
    Generates an authentic 48kHz stereo WAV soundtrack for the typewriter title slide:
    - 0.0s - 2.0s: Silence while cover photo push-in begins.
    - 2.0s - 4.0s: Mechanical key strokes & spacebar sounds typing Centered Event Text (2.0s duration).
      At 4.02s: Carriage return bell ding!
    - 4.0s - 6.0s: Mechanical key strokes & spacebar sounds typing Bottom-Right Date Text (2.0s duration).
      At 6.02s: Carriage return bell ding!
    - 6.0s - end: Silence with natural bell resonance decay.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.path.dirname(script_dir), "resources", "audio"),
        os.path.join(script_dir, "resources", "audio"),
        r"C:\Users\eliea\.gemini\config\skills\Cinematic_Slideshow\resources\audio",
        r"D:\GoogleDrive\Antigravity\skills\Cinematic_Slideshow\resources\audio"
    ]
    audio_dir = ""
    for d in candidates:
        if os.path.exists(d):
            audio_dir = d
            break

    def load_wav(name):
        if not audio_dir:
            return [], []
        p = os.path.join(audio_dir, name)
        if not os.path.exists(p):
            return [], []
        try:
            with wave.open(p, 'rb') as w:
                n = w.getnframes()
                ch = w.getnchannels()
                raw = w.readframes(n)
                s = struct.unpack(f'<{n * ch}h', raw)
                if ch == 2:
                    return [x / 32768.0 for x in s[0::2]], [x / 32768.0 for x in s[1::2]]
                else:
                    l = [x / 32768.0 for x in s]
                    return l, list(l)
        except Exception as e:
            print(f"Warning: Could not load {name}: {e}")
            return [], []

    key_l, key_r = load_wav('typewriter_key.wav')
    spc_l, spc_r = load_wav('typewriter_space.wav')
    bel_l, bel_r = load_wav('typewriter_bell.wav')

    total_samples = int(dur * sr)
    out_l = [0.0] * total_samples
    out_r = [0.0] * total_samples

    def overlay(samples_l, samples_r, start_sec, gain=1.0, pan=0.0):
        if not samples_l:
            return
        start_idx = int(start_sec * sr)
        if start_idx >= total_samples:
            return
        g_l = gain * 0.5 * (1.0 - pan)
        g_r = gain * 0.5 * (1.0 + pan)
        limit = min(len(samples_l), total_samples - start_idx)
        for i in range(limit):
            out_l[start_idx + i] += samples_l[i] * g_l
            out_r[start_idx + i] += samples_r[i] * g_r

    # Text 1: Centered Event Text
    # Starts at t = 2.0s, duration = 2.0s
    len1 = len(title_center) if title_center else 0
    if len1 > 0 and key_l:
        step1 = 2.0 / len1
        for i, ch in enumerate(title_center):
            t = 2.0 + i * step1
            pan = -0.25 + 0.50 * (i / max(1, len1 - 1))
            vol = random.uniform(0.75, 0.95)
            if ch == ' ' and spc_l:
                overlay(spc_l, spc_r, t, gain=vol * 0.85, pan=pan)
            else:
                overlay(key_l, key_r, t, gain=vol, pan=pan)
        # Carriage bell at completion of Text 1
        if bel_l:
            overlay(bel_l, bel_r, 4.02, gain=0.90, pan=0.30)

    # Text 2: Date Text at bottom-right
    # Starts at t = 4.0s, duration = 2.0s
    len2 = len(title_date) if title_date else 0
    if len2 > 0 and key_l:
        step2 = 2.0 / len2
        for i, ch in enumerate(title_date):
            t = 4.0 + i * step2
            pan = 0.20 + 0.30 * (i / max(1, len2 - 1))
            vol = random.uniform(0.75, 0.95)
            if ch == ' ' and spc_l:
                overlay(spc_l, spc_r, t, gain=vol * 0.85, pan=pan)
            else:
                overlay(key_l, key_r, t, gain=vol, pan=pan)
        # Carriage bell at completion of Text 2
        if bel_l:
            overlay(bel_l, bel_r, 6.02, gain=0.90, pan=0.45)

    # Normalize/clamp and write 16-bit stereo WAV
    max_amp = max(max(abs(x) for x in out_l) if out_l else 0.0,
                  max(abs(x) for x in out_r) if out_r else 0.0,
                  1.0)
    norm_factor = 0.92 / max_amp if max_amp > 0.92 else 1.0

    packed = bytearray()
    for i in range(total_samples):
        sl = int(max(-1.0, min(1.0, out_l[i] * norm_factor)) * 32767)
        sr_ = int(max(-1.0, min(1.0, out_r[i] * norm_factor)) * 32767)
        packed.extend(struct.pack('<hh', sl, sr_))

    os.makedirs(os.path.dirname(os.path.abspath(audio_output_path)), exist_ok=True)
    with wave.open(audio_output_path, 'wb') as out_wav:
        out_wav.setnchannels(2)
        out_wav.setsampwidth(2)
        out_wav.setframerate(sr)
        out_wav.writeframes(packed)
    return audio_output_path

def create_title_slide(cover_path, output_path, width=3840, height=2160,
                       title_center="Vacation 2026", title_bottom_right="",
                       border_px=30, letterbox_bars=0, margin=80):
    """
    Creates a static composite title slide with prominent 30px white border,
    80px blurred background margin, and elegant typography.
    """
    bg_tmp = output_path + ".bg.jpg"
    fg_tmp = output_path + ".fg.jpg"
    target_w, target_h, layout_info = prepare_title_layers(
        cover_path, bg_tmp, fg_tmp, width, height, title_center,
        title_bottom_right, border_px, 35, letterbox_bars, margin
    )
    bg = Image.open(bg_tmp)
    fg = Image.open(fg_tmp)
    bordered = ImageOps.expand(fg, border=border_px, fill="white")
    canvas = bg.copy()
    fg_x = (width - bordered.width) // 2
    fg_y = (height - bordered.height) // 2
    canvas.paste(bordered, (fg_x, fg_y))

    # Draw final text on canvas for static slide
    draw = ImageDraw.Draw(canvas)
    font_center = get_font("georgiab.ttf", layout_info["center_font_size"])
    font_date = get_font("georgia.ttf", layout_info["date_font_size"])
    line_positions = layout_info.get("line_positions", [])
    if line_positions:
        for lp in line_positions:
            draw.text((lp["x"] + 5, lp["y"] + 5), lp["text"], font=font_center, fill=(0, 0, 0, 230))
            draw.text((lp["x"], lp["y"]), lp["text"], font=font_center, fill=(255, 255, 255, 255))
    elif title_center:
        draw.text((layout_info["x_c"] + 5, layout_info["y_c"] + 5), title_center, font=font_center, fill=(0, 0, 0, 230))
        draw.text((layout_info["x_c"], layout_info["y_c"]), title_center, font=font_center, fill=(255, 255, 255, 255))
    if title_bottom_right:
        draw.text((layout_info["rx"] + 4, layout_info["ry"] + 4), title_bottom_right, font=font_date, fill=(0, 0, 0, 220))
        draw.text((layout_info["rx"], layout_info["ry"]), title_bottom_right, font=font_date, fill=(245, 235, 210, 255))

    canvas.save(output_path, quality=95)
    try:
        os.remove(bg_tmp)
        os.remove(fg_tmp)
    except Exception:
        pass
    return output_path

def process_photo(photo_path, output_path, width=3840, height=2160, border_px=30, blur_radius=35, letterbox_bars=0):
    """
    Composites a photo with prominent 30px white border over a matching blurred, dimmed background.
    Supports both horizontal and vertical photos, ensuring the border is always visible.
    """
    img = Image.open(photo_path).convert("RGB")
    img = ImageOps.exif_transpose(img)
    iw, ih = img.size

    active_h = height - (2 * letterbox_bars)

    # 1. Background: scaled to fill canvas, heavily blurred, dimmed
    bg_scale = max(width / iw, height / ih)
    bg_w, bg_h = int(iw * bg_scale), int(ih * bg_scale)
    bg = img.resize((bg_w, bg_h), Image.Resampling.BILINEAR)
    x0 = (bg_w - width) // 2
    y0 = (bg_h - height) // 2
    bg_cropped = bg.crop((x0, y0, x0 + width, y0 + height))
    bg_blurred = bg_cropped.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    is_portrait = ih > iw
    dim_factor = 0.65 if is_portrait else 0.45
    bg_dimmed = Image.eval(bg_blurred, lambda val: int(val * dim_factor))

    # 2. Foreground sizing: leaves exactly 80px of blurred background
    margin = 80
    max_box_w = width - (2 * margin)
    max_box_h = active_h - (2 * margin)
    max_fg_w = max(100, max_box_w - (border_px * 2))
    max_fg_h = max(100, max_box_h - (border_px * 2))
    scale = min(max_fg_w / iw, max_fg_h / ih)

    fg_w, fg_h = int(iw * scale), int(ih * scale)
    fg_resized = img.resize((fg_w, fg_h), Image.Resampling.LANCZOS)
    fg_bordered = ImageOps.expand(fg_resized, border=border_px, fill="white")

    canvas = bg_dimmed.copy()
    fg_x = (width - fg_bordered.width) // 2
    fg_y = (height - fg_bordered.height) // 2
    canvas.paste(fg_bordered, (fg_x, fg_y))

    if letterbox_bars > 0:
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([0, 0, width, letterbox_bars], fill="black")
        draw.rectangle([0, height - letterbox_bars, width, height], fill="black")

    canvas.save(output_path, quality=95)
    return output_path

def prepare_photo_layers(photo_path, bg_output_path, fg_output_path,
                         width=3840, height=2160, border_px=30, blur_radius=35,
                         letterbox_bars=0, margin=80):
    """
    Prepares:
    1. bg_output_path: Blurred, dimmed 4K background matching the photo.
    2. fg_output_path: Clean, EXIF-oriented RGB JPEG for Ken Burns rendering.
    Returns: (target_w, target_h) - the exact dimensions for Ken Burns output inside the border.
    """
    img = Image.open(photo_path).convert("RGB")
    img = ImageOps.exif_transpose(img)
    iw, ih = img.size

    active_h = height - (2 * letterbox_bars)

    # 1. Background: scaled to fill canvas, heavily blurred, dimmed
    bg_scale = max(width / iw, height / ih)
    bg_w, bg_h = int(iw * bg_scale), int(ih * bg_scale)
    bg = img.resize((bg_w, bg_h), Image.Resampling.BILINEAR)
    x0 = (bg_w - width) // 2
    y0 = (bg_h - height) // 2
    bg_cropped = bg.crop((x0, y0, x0 + width, y0 + height))
    bg_blurred = bg_cropped.filter(ImageFilter.BoxBlur(blur_radius))

    is_portrait = ih > iw
    dim_factor = 0.65 if is_portrait else 0.45
    bg_dimmed = Image.eval(bg_blurred, lambda val: int(val * dim_factor))

    if letterbox_bars > 0:
        draw = ImageDraw.Draw(bg_dimmed)
        draw.rectangle([0, 0, width, letterbox_bars], fill="black")
        draw.rectangle([0, height - letterbox_bars, width, height], fill="black")

    bg_dimmed.save(bg_output_path, quality=95)

    # 2. Compute exact target dimensions leaving margin px of blurred background
    max_box_w = width - (2 * margin)
    max_box_h = active_h - (2 * margin)
    max_fg_w = max(100, max_box_w - (border_px * 2))
    max_fg_h = max(100, max_box_h - (border_px * 2))
    scale = min(max_fg_w / iw, max_fg_h / ih)

    target_w = (int(iw * scale) // 2) * 2
    target_h = (int(ih * scale) // 2) * 2

    # 3. Save EXIF-oriented photo as clean JPEG for ffmpeg zoompan
    max_dim = max(iw, ih)
    if max_dim > 4500:
        fg_scale = 4500 / max_dim
        img_for_ffmpeg = img.resize((int(iw * fg_scale), int(ih * fg_scale)), Image.Resampling.LANCZOS)
        img_for_ffmpeg.save(fg_output_path, quality=95)
    else:
        img.save(fg_output_path, quality=95)

    return target_w, target_h

