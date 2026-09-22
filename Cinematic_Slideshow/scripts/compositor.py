"""
High-Resolution Frame Compositor for Cinematic Slideshow Agent.
Handles EXIF auto-orientation, title slide typography (center title + bottom-right date),
dual-layer blurred matching backdrops for vertical and horizontal media,
prominent 30px white borders, and optional letterbox matting.
"""
import os
import subprocess
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

    # Typography sizing proportional to photo height
    center_font_size = int(target_h * 0.055)
    date_font_size = int(target_h * 0.032)

    font_center = get_font("georgiab.ttf", center_font_size)
    font_date = get_font("georgia.ttf", date_font_size)

    bbox_c = font_center.getbbox(title_center) if title_center else (0, 0, 0, 0)
    tw_c, th_c = bbox_c[2] - bbox_c[0], bbox_c[3] - bbox_c[1]
    cx = width // 2
    cy = height // 2
    x_c = cx - tw_c // 2
    y_c = cy - th_c // 2

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
        "x_c": x_c,
        "y_c": y_c,
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
    center_font_size = layout_info.get("center_font_size", 100)
    date_font_size = layout_info.get("date_font_size", 60)
    x_c = layout_info.get("x_c", width // 2)
    y_c = layout_info.get("y_c", height // 2)
    rx = layout_info.get("rx", width - 300)
    ry = layout_info.get("ry", height - 200)

    font_center = get_font("georgiab.ttf", center_font_size)
    font_date = get_font("georgia.ttf", date_font_size)

    total_frames = int(dur * fps)
    f_start1 = int(2.0 * fps)
    f_start2 = int(4.0 * fps)

    # Center text typing duration: ~1.8s (or max 2.0s)
    len1 = len(title_center)
    f_dur1 = int(min(2.0, max(0.8, len1 * 0.05)) * fps) if len1 > 0 else 1

    # Date text typing duration: ~0.7s
    len2 = len(title_date)
    f_dur2 = int(min(1.2, max(0.4, len2 * 0.08)) * fps) if len2 > 0 else 1

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
        if t < 2.0 or (not title_center and not title_date):
            proc.stdin.write(empty_bytes)
            continue

        # Substring for title 1
        if not title_center:
            sub1 = ""
        elif f < f_start1 + f_dur1:
            progress1 = (f - f_start1) / f_dur1
            c1_len = max(1, min(len1, int(round(progress1 * len1))))
            sub1 = title_center[:c1_len]
        else:
            sub1 = title_center

        # Substring for title 2 (starts at t = 4.0s)
        if not title_date or f < f_start2:
            sub2 = ""
        elif f < f_start2 + f_dur2:
            progress2 = (f - f_start2) / f_dur2
            c2_len = max(1, min(len2, int(round(progress2 * len2))))
            sub2 = title_date[:c2_len]
        else:
            sub2 = title_date

        state_key = (sub1, sub2)
        if state_key in cached_bytes:
            proc.stdin.write(cached_bytes[state_key])
        else:
            img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            if sub1:
                draw.text((x_c + 4, y_c + 4), sub1, font=font_center, fill=(0, 0, 0, 230))
                draw.text((x_c, y_c), sub1, font=font_center, fill=(255, 255, 255, 255))
            if sub2:
                draw.text((rx + 3, ry + 3), sub2, font=font_date, fill=(0, 0, 0, 220))
                draw.text((rx, ry), sub2, font=font_date, fill=(245, 235, 210, 255))
            raw = img.tobytes()
            cached_bytes[state_key] = raw
            proc.stdin.write(raw)

    proc.stdin.close()
    proc.wait()
    return output_path

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
    if title_center:
        draw.text((layout_info["x_c"] + 4, layout_info["y_c"] + 4), title_center, font=font_center, fill=(0, 0, 0, 230))
        draw.text((layout_info["x_c"], layout_info["y_c"]), title_center, font=font_center, fill=(255, 255, 255, 255))
    if title_bottom_right:
        draw.text((layout_info["rx"] + 3, layout_info["ry"] + 3), title_bottom_right, font=font_date, fill=(0, 0, 0, 220))
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

