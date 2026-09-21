"""
High-Resolution Frame Compositor for Cinematic Slideshow Agent.
Handles EXIF auto-orientation, title slide typography (center title + bottom-right date),
dual-layer blurred matching backdrops for vertical and horizontal media,
prominent 30px white borders, and optional letterbox matting.
"""
import os
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
    Prepares title slide layers adhering to the white box rule:
    1. bg_output_path: Blurred, dimmed 4K matching background.
    2. fg_output_path: Resized cover photo with atmospheric dimming and elegant typography.
    Returns: (target_w, target_h)
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

    draw = ImageDraw.Draw(fg_rgba, "RGBA")

    # Typography sizing proportional to photo height
    center_font_size = int(target_h * 0.055)
    date_font_size = int(target_h * 0.032)

    font_center = get_font("georgiab.ttf", center_font_size)
    font_date = get_font("georgia.ttf", date_font_size)

    bbox_c = font_center.getbbox(title_center)
    tw_c, th_c = bbox_c[2] - bbox_c[0], bbox_c[3] - bbox_c[1]
    cx = target_w // 2
    cy = target_h // 2

    # Drop shadow & title text
    draw.text((cx - tw_c // 2 + 4, cy - th_c // 2 + 4), title_center, font=font_center, fill=(0, 0, 0, 230))
    draw.text((cx - tw_c // 2, cy - th_c // 2), title_center, font=font_center, fill=(255, 255, 255, 255))

    if title_bottom_right:
        bbox_d = font_date.getbbox(title_bottom_right)
        tw_d, th_d = bbox_d[2] - bbox_d[0], bbox_d[3] - bbox_d[1]
        rx = target_w - tw_d - int(target_w * 0.04)
        ry = target_h - th_d - int(target_h * 0.05)

        draw.text((rx + 3, ry + 3), title_bottom_right, font=font_date, fill=(0, 0, 0, 220))
        draw.text((rx, ry), title_bottom_right, font=font_date, fill=(245, 235, 210, 255))

    fg_rgba.convert("RGB").save(fg_output_path, quality=95)
    return target_w, target_h

def create_title_slide(cover_path, output_path, width=3840, height=2160,
                       title_center="Vacation 2026", title_bottom_right="",
                       border_px=30, letterbox_bars=0, margin=80):
    """
    Creates a static composite title slide with prominent 30px white border,
    80px blurred background margin, and elegant typography.
    """
    bg_tmp = output_path + ".bg.jpg"
    fg_tmp = output_path + ".fg.jpg"
    target_w, target_h = prepare_title_layers(
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

