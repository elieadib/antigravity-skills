#!/usr/bin/env python3
"""
rename_tracks.py - Autonomous Music Track Renamer Agent
Renames MP3 and FLAC audio files to: "BandName - AlbumName - TrackName.<ext>"
Works with or without mutagen (built-in ID3v1/ID3v2 & FLAC Vorbis parsers).
"""

import os
import sys
import re
import stat
import argparse
from pathlib import Path
from collections import defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import mutagen
    HAVE_MUTAGEN = True
except ImportError:
    HAVE_MUTAGEN = False

AUDIO_EXTS = {".mp3", ".flac"}

# --- Pure Python Audio Metadata Parsers (Zero Dependencies) ---

def parse_flac_vorbis(fpath):
    tags = {}
    try:
        with open(fpath, 'rb') as f:
            if f.read(4) != b'fLaC':
                return tags
            while True:
                header = f.read(4)
                if len(header) < 4:
                    break
                is_last = bool(header[0] & 0x80)
                block_type = header[0] & 0x7F
                length = int.from_bytes(header[1:4], 'big')
                data = f.read(length)
                if block_type == 4: # VORBIS_COMMENT
                    vendor_len = int.from_bytes(data[0:4], 'little')
                    pos = 4 + vendor_len
                    if pos + 4 <= len(data):
                        comment_count = int.from_bytes(data[pos:pos+4], 'little')
                        pos += 4
                        for _ in range(comment_count):
                            if pos + 4 > len(data):
                                break
                            c_len = int.from_bytes(data[pos:pos+4], 'little')
                            pos += 4
                            comment_bytes = data[pos:pos+c_len]
                            pos += c_len
                            try:
                                comment = comment_bytes.decode('utf-8', errors='replace')
                                if '=' in comment:
                                    k, v = comment.split('=', 1)
                                    tags.setdefault(k.lower(), []).append(v.strip())
                            except Exception:
                                pass
                    return tags
                if is_last:
                    break
    except Exception:
        pass
    return tags

def decode_id3_text(enc, b):
    try:
        if enc == 0:
            return b.decode('latin1', errors='replace').rstrip('\x00')
        elif enc == 1:
            return b.decode('utf-16', errors='replace').rstrip('\x00')
        elif enc == 2:
            return b.decode('utf-16-be', errors='replace').rstrip('\x00')
        elif enc == 3:
            return b.decode('utf-8', errors='replace').rstrip('\x00')
    except Exception:
        pass
    return b.decode('latin1', errors='replace').rstrip('\x00')

def parse_id3v1(fpath):
    tags = {}
    try:
        with open(fpath, 'rb') as f:
            f.seek(-128, os.SEEK_END)
            buf = f.read(128)
            if len(buf) == 128 and buf[:3] == b'TAG':
                title = buf[3:33].decode('latin1', errors='replace').strip('\x00').strip()
                artist = buf[33:63].decode('latin1', errors='replace').strip('\x00').strip()
                album = buf[63:93].decode('latin1', errors='replace').strip('\x00').strip()
                if title: tags['title'] = [title]
                if artist: tags['artist'] = [artist]
                if album: tags['album'] = [album]
    except Exception:
        pass
    return tags

def parse_id3v2(fpath):
    tags = {}
    try:
        with open(fpath, 'rb') as f:
            header = f.read(10)
            if len(header) < 10 or header[:3] != b'ID3':
                return parse_id3v1(fpath)
            major_ver = header[3]
            flags = header[5]
            tag_size = (header[6] << 21) | (header[7] << 14) | (header[8] << 7) | header[9]
            tag_data = f.read(tag_size)

            pos = 0
            if flags & 0x40 and major_ver in (3, 4):
                ext_size = int.from_bytes(tag_data[:4], 'big')
                pos += ext_size

            frame_map = {
                'TIT2': 'title', 'TT2': 'title',
                'TPE1': 'artist', 'TP1': 'artist',
                'TPE2': 'albumartist', 'TP2': 'albumartist',
                'TALB': 'album', 'TAL': 'album',
            }

            while pos + 10 <= len(tag_data):
                frame_id_bytes = tag_data[pos:pos+4]
                pos += 4
                if frame_id_bytes[0] == 0:
                    break
                frame_id = frame_id_bytes.decode('latin1', errors='replace')
                if major_ver == 4:
                    b = tag_data[pos:pos+4]
                    frame_size = (b[0] << 21) | (b[1] << 14) | (b[2] << 7) | b[3]
                else:
                    frame_size = int.from_bytes(tag_data[pos:pos+4], 'big')
                pos += 4
                flags_bytes = tag_data[pos:pos+2]
                pos += 2
                frame_content = tag_data[pos:pos+frame_size]
                pos += frame_size

                if frame_id in frame_map and len(frame_content) > 1:
                    enc = frame_content[0]
                    text = decode_id3_text(enc, frame_content[1:])
                    key = frame_map[frame_id]
                    tags.setdefault(key, []).append(text.strip())

        if not tags:
            return parse_id3v1(fpath)
    except Exception:
        return parse_id3v1(fpath)
    return tags

def get_audio_tags(file_path):
    ext = file_path.suffix.lower()
    art, alb, tit = None, None, None

    if HAVE_MUTAGEN:
        try:
            t = mutagen.File(file_path, easy=True)
            if t:
                art = t.get("artist", [None])[0] or t.get("albumartist", [None])[0]
                alb = t.get("album", [None])[0]
                tit = t.get("title", [None])[0]
                return art, alb, tit
        except Exception:
            pass

    raw_tags = {}
    if ext == ".flac":
        raw_tags = parse_flac_vorbis(file_path)
    elif ext == ".mp3":
        raw_tags = parse_id3v2(file_path)

    art = raw_tags.get("artist", [None])[0] or raw_tags.get("albumartist", [None])[0]
    alb = raw_tags.get("album", [None])[0]
    tit = raw_tags.get("title", [None])[0]

    return art, alb, tit

# --- Sanitization & Fallback Logic ---

def sanitize(s):
    if not s:
        return ""
    s = str(s)
    s = s.replace('\ufffd', "'")
    s = s.replace('/', '-').replace('\\', '-')
    s = s.replace(':', ' -')
    s = re.sub(r'[<>"|?*]', '', s)
    s = re.sub(r'[\x00-\x1f\x7f]', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip('. ')

def clean_track_title_from_filename(filename, artist=None, album=None):
    stem = Path(filename).stem
    # Remove leading track numbers: e.g. "01 - ", "01. ", "01.", "01 ", "01-"
    stem = re.sub(r'^\d+[\s.-]+', '', stem).strip()
    
    # Check if already prefixed by "Artist - Album - "
    if artist and album:
        p_art = sanitize(artist).lower()
        p_alb = sanitize(album).lower()
        pattern = rf'^{re.escape(p_art)}\s*-\s*{re.escape(p_alb)}\s*-\s*(.+)$'
        m = re.match(pattern, stem, re.IGNORECASE)
        if m:
            return m.group(1).strip()
            
    if artist:
        p_art = sanitize(artist).lower()
        pattern = rf'^{re.escape(p_art)}\s*-\s*(.+)$'
        m = re.match(pattern, stem, re.IGNORECASE)
        if m:
            return m.group(1).strip()
            
    return stem.strip()

def parse_folder_name(folder_name):
    parts = [p.strip() for p in folder_name.split(' - ')]
    artist = parts[0] if len(parts) > 0 else "Unknown Artist"
    album = parts[1] if len(parts) > 1 else parts[0]
    return artist, album

def get_album_and_artist_from_path(root_path):
    p = Path(root_path)
    parent_name = p.name
    m_year = re.match(r'^\d{4}\s*-\s*(.+)$', parent_name)
    if m_year:
        album = m_year.group(1).strip()
        grandparent = p.parent.name
        art, _ = parse_folder_name(grandparent)
        return art, album

    if parent_name.upper() in ["CD1", "CD2", "CD3", "DISC 1", "DISC 2"]:
        grandparent = p.parent.name
        return parse_folder_name(grandparent)

    return parse_folder_name(parent_name)

# --- Core Renamer Agent ---

def process_music_directory(base_dir, dry_run=False, pattern="{artist} - {album} - {title}", update_cue=True):
    base_dir = Path(base_dir).resolve()
    if not base_dir.exists():
        print(f"Error: Directory does not exist: {base_dir}")
        return False

    print("=" * 60)
    print(f"🎵 Music Track Renamer Agent")
    print(f"Target Directory: {base_dir}")
    print(f"Mode: {'[DRY RUN - PREVIEW ONLY]' if dry_run else '[LIVE EXECUTION]'}")
    print(f"Engine: {'Mutagen + Built-in Fallback' if HAVE_MUTAGEN else 'Built-in Pure Python Engine'}")
    print("=" * 60)

    all_planned = []
    
    for root, dirs, files in os.walk(base_dir):
        audio_files = [f for f in files if os.path.splitext(f)[1].lower() in AUDIO_EXTS]
        if not audio_files:
            continue

        folder_artists = []
        folder_albums = []
        file_tags = {}

        for f in audio_files:
            file_path = Path(root) / f
            art, alb, tit = get_audio_tags(file_path)
            file_tags[f] = (art, alb, tit)
            if art: folder_artists.append(art)
            if alb: folder_albums.append(alb)

        f_art, f_alb = get_album_and_artist_from_path(root)
        best_artist = max(set(folder_artists), key=folder_artists.count) if folder_artists else f_art
        best_album = max(set(folder_albums), key=folder_albums.count) if folder_albums else f_alb

        folder_planned = defaultdict(list)
        for f in sorted(audio_files):
            file_path = Path(root) / f
            ext = file_path.suffix.lower()
            art, alb, tit = file_tags.get(f, (None, None, None))

            final_artist = art if art else best_artist
            final_album = alb if alb else best_album
            final_title = tit if tit else clean_track_title_from_filename(f, final_artist, final_album)
            if not final_title:
                final_title = file_path.stem

            clean_art = sanitize(final_artist)
            clean_alb = sanitize(final_album)
            clean_tit = sanitize(final_title)

            if not clean_art: clean_art = "Unknown Artist"
            if not clean_alb: clean_alb = "Unknown Album"
            if not clean_tit: clean_tit = "Unknown Track"

            target_base = pattern.format(artist=clean_art, album=clean_alb, title=clean_tit)
            target_name = f"{target_base}{ext}"
            folder_planned[target_name].append((file_path, f))

        for target_name, sources in folder_planned.items():
            for idx, (src_path, orig_name) in enumerate(sources):
                if len(sources) == 1:
                    final_name = target_name
                else:
                    stem = Path(target_name).stem
                    final_name = f"{stem} ({idx + 1}){src_path.suffix.lower()}"
                all_planned.append((src_path, Path(root) / final_name))

    print(f"\nDiscovered {len(all_planned)} audio files.")

    renamed_count = 0
    already_correct = 0
    errors = []
    cue_updated = 0

    for idx, (src, dst) in enumerate(all_planned, start=1):
        if src.resolve() == dst.resolve() and src.name == dst.name:
            already_correct += 1
            continue

        if dry_run:
            renamed_count += 1
            print(f"[{renamed_count}] Would rename in '{src.parent.name}':\n  '{src.name}'\n  -> '{dst.name}'\n")
            continue

        try:
            try:
                os.chmod(src, stat.S_IWRITE)
            except Exception:
                pass

            old_name = src.name
            if src.name.lower() == dst.name.lower():
                temp_name = src.parent / f"__temp_ren_{idx}_{src.name}"
                src.rename(temp_name)
                temp_name.rename(dst)
            else:
                final_dst = dst
                c = 2
                while final_dst.exists() and final_dst.resolve() != src.resolve():
                    stem = dst.stem
                    final_dst = dst.parent / f"{stem} ({c}){dst.suffix}"
                    c += 1
                src.rename(final_dst)
                dst = final_dst

            renamed_count += 1
            print(f"[{renamed_count}] Renamed in '{src.parent.name}':\n  '{old_name}' -> '{dst.name}'")

            if update_cue:
                for cue_file in src.parent.glob("*.cue"):
                    try:
                        for enc in ["utf-8", "cp1252", "latin-1"]:
                            try:
                                cue_text = cue_file.read_text(encoding=enc)
                                if old_name in cue_text:
                                    cue_text = cue_text.replace(old_name, dst.name)
                                    cue_file.write_text(cue_text, encoding=enc)
                                    cue_updated += 1
                                    print(f"  -> Updated CUE reference in {cue_file.name}")
                                break
                            except UnicodeDecodeError:
                                continue
                    except Exception as cue_e:
                        print(f"  -> Warning: failed to update CUE: {cue_e}")

        except Exception as e:
            errors.append((src, dst, str(e)))
            print(f"Error renaming '{src}' to '{dst}': {e}")

    print("\n" + "=" * 60)
    print("RENAME SUMMARY")
    print(f"Total files checked: {len(all_planned)}")
    print(f"Files {'to rename' if dry_run else 'renamed'}:     {renamed_count}")
    print(f"Already matching:    {already_correct}")
    print(f"Errors encountered:  {len(errors)}")
    if not dry_run and update_cue:
        print(f"CUE sheets updated:  {cue_updated}")
    print("=" * 60)
    return len(errors) == 0

def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Music Track Renamer Agent: renames MP3/FLAC files to 'BandName - AlbumName - TrackName.<ext>'"
    )
    parser.add_argument("directory", help="Path to music folder to process")
    parser.add_argument("--dry-run", action="store_true", help="Preview planned changes without renaming")
    parser.add_argument("--pattern", default="{artist} - {album} - {title}", help="Naming pattern (default: '{artist} - {album} - {title}')")
    parser.add_argument("--no-cue", action="store_true", help="Do not update .cue files")

    args = parser.parse_args()
    success = process_music_directory(
        args.directory,
        dry_run=args.dry_run,
        pattern=args.pattern,
        update_cue=not args.no_cue
    )
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
