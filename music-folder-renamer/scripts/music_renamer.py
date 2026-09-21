# music_renamer.py - Automates music album folder renaming based on audio tags
import os
import sys
import io
import re
import argparse
import time
from collections import Counter

# Ensure UTF-8 output on Windows consoles
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

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
                    user_comment_count = int.from_bytes(data[pos:pos+4], 'little')
                    pos += 4
                    for _ in range(user_comment_count):
                        if pos + 4 > len(data):
                            break
                        c_len = int.from_bytes(data[pos:pos+4], 'little')
                        pos += 4
                        comment_bytes = data[pos:pos+c_len]
                        pos += c_len
                        comment = comment_bytes.decode('utf-8', errors='ignore')
                        if '=' in comment:
                            k, v = comment.split('=', 1)
                            clean_v = v.replace('\x00', '').strip()
                            tags.setdefault(k.upper(), []).append(clean_v)
                    return tags
                if is_last:
                    break
    except Exception:
        pass
    return tags

def decode_id3_text(enc, b):
    try:
        if enc == 0:
            return b.decode('latin1', errors='ignore')
        elif enc == 1:
            return b.decode('utf-16', errors='ignore')
        elif enc == 2:
            return b.decode('utf-16-be', errors='ignore')
        elif enc == 3:
            return b.decode('utf-8', errors='ignore')
    except Exception:
        pass
    return b.decode('latin1', errors='ignore')

def parse_id3v1(fpath):
    tags = {}
    try:
        with open(fpath, 'rb') as f:
            f.seek(-128, os.SEEK_END)
            buf = f.read(128)
            if len(buf) == 128 and buf[:3] == b'TAG':
                artist = buf[33:63].decode('latin1', errors='ignore').replace('\x00', '').strip()
                album = buf[63:93].decode('latin1', errors='ignore').replace('\x00', '').strip()
                year = buf[93:97].decode('latin1', errors='ignore').replace('\x00', '').strip()
                if artist: tags['TPE1'] = [artist]
                if album: tags['TALB'] = [album]
                if year: tags['TYER'] = [year]
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
            if flags & 0x40:
                if major_ver in (3, 4):
                    ext_size = int.from_bytes(tag_data[:4], 'big')
                    pos += ext_size

            while pos + 10 <= len(tag_data):
                frame_id_bytes = tag_data[pos:pos+4]
                pos += 4
                if frame_id_bytes[0] == 0:
                    break
                frame_id = frame_id_bytes.decode('latin1', errors='ignore')
                
                if major_ver == 4:
                    frame_size = (tag_data[pos] << 21) | (tag_data[pos+1] << 14) | (tag_data[pos+2] << 7) | tag_data[pos+3]
                else:
                    frame_size = int.from_bytes(tag_data[pos:pos+4], 'big')
                pos += 4
                pos += 2 # flags
                
                if pos + frame_size > len(tag_data):
                    break
                frame_body = tag_data[pos:pos+frame_size]
                pos += frame_size
                
                if frame_id in ('TPE1', 'TPE2', 'TALB', 'TDRC', 'TYER'):
                    if len(frame_body) > 1:
                        enc = frame_body[0]
                        text = decode_id3_text(enc, frame_body[1:])
                        clean_text = text.replace('\x00', '').strip()
                        if clean_text:
                            tags.setdefault(frame_id, []).append(clean_text)
    except Exception:
        pass
    
    if not tags:
        return parse_id3v1(fpath)
    return tags

def parse_cue(cue_path):
    meta = {}
    try:
        with open(cue_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                m_perf = re.match(r'^PERFORMER\s+"([^"]+)"', line, re.IGNORECASE)
                if m_perf and 'ARTIST' not in meta:
                    meta['ARTIST'] = m_perf.group(1).replace('\x00', '').strip()
                m_title = re.match(r'^TITLE\s+"([^"]+)"', line, re.IGNORECASE)
                if m_title and 'ALBUM' not in meta:
                    meta['ALBUM'] = m_title.group(1).replace('\x00', '').strip()
                m_date = re.match(r'^REM\s+DATE\s+(\d{4})', line, re.IGNORECASE)
                if m_date and 'YEAR' not in meta:
                    meta['YEAR'] = m_date.group(1).replace('\x00', '').strip()
    except Exception:
        pass
    return meta

def clean_tag(val):
    if not val:
        return ""
    # Strip null bytes and surrogate characters
    val = val.replace('\x00', '')
    val = re.sub(r'[\ud800-\udfff]', '', val)
    val = re.sub(r'[\/\\:*?"<>|]', ' - ', val)
    val = re.sub(r'\s+', ' ', val)
    return val.strip(' -').strip()

def to_win_path(p):
    p = os.path.abspath(p)
    if os.name == 'nt' and not p.startswith('\\\\?\\'):
        return '\\\\?\\' + p
    return p

def extract_file_meta(fpath):
    ext = os.path.splitext(fpath)[1].lower()
    artist, album, year = None, None, None
    
    if ext == '.flac':
        tags = parse_flac_vorbis(fpath)
        for k in ('ALBUMARTIST', 'ALBUM ARTIST', 'ARTIST'):
            if k in tags and tags[k]:
                for a in tags[k]:
                    clean_a = a.split(';')[0].replace('\x00', '').strip()
                    if clean_a:
                        artist = clean_a
                        break
                if artist: break
        if 'ALBUM' in tags and tags['ALBUM']:
            for al in tags['ALBUM']:
                c = al.replace('\x00', '').strip()
                if c:
                    album = c
                    break
        for yk in ('DATE', 'YEAR', 'ORIGINALYEAR', 'ORIGINALDATE'):
            if yk in tags and tags[yk]:
                for y in tags[yk]:
                    m = re.search(r'\b(19\d\d|20\d\d)\b', y)
                    if m:
                        year = m.group(1)
                        break
                if year: break
    elif ext == '.mp3':
        tags = parse_id3v2(fpath)
        for k in ('TPE2', 'TPE1'):
            if k in tags and tags[k]:
                for a in tags[k]:
                    clean_a = a.split(';')[0].split('/')[0].replace('\x00', '').strip()
                    if clean_a:
                        artist = clean_a
                        break
                if artist: break
        if 'TALB' in tags and tags['TALB']:
            for al in tags['TALB']:
                c = al.replace('\x00', '').strip()
                if c:
                    album = c
                    break
        for yk in ('TDRC', 'TYER'):
            if yk in tags and tags[yk]:
                for y in tags[yk]:
                    m = re.search(r'\b(19\d\d|20\d\d)\b', y)
                    if m:
                        year = m.group(1)
                        break
                if year: break

    return artist, album, year

def get_folder_metadata(folder_path):
    mp3_files = []
    flac_files = []
    cue_files = []
    sub_album_dirs = []
    
    try:
        for entry in os.scandir(folder_path):
            if entry.is_dir():
                for r, _, fs in os.walk(entry.path):
                    if any(os.path.splitext(f)[1].lower() in ('.mp3', '.flac') for f in fs):
                        sub_album_dirs.append(entry.name)
                        break

        for root, dirs, files in os.walk(folder_path):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                full_p = os.path.join(root, f)
                if ext == '.mp3':
                    mp3_files.append(full_p)
                elif ext == '.flac':
                    flac_files.append(full_p)
                elif ext == '.cue':
                    cue_files.append(full_p)
    except Exception as e:
        return None, f"Error scanning: {e}"

    total_audio = len(mp3_files) + len(flac_files)
    if total_audio == 0:
        return None, "NO_AUDIO_FILES"

    has_mp3 = len(mp3_files) > 0 and (len(mp3_files) >= 2 or len(flac_files) == 0)
    has_flac = len(flac_files) > 0 and (len(flac_files) >= 2 or len(mp3_files) == 0)
    
    if has_mp3 and has_flac:
        fmt_suffix = " - mp3 - Flac"
        fmt_str = "MP3+FLAC"
    elif has_flac:
        fmt_suffix = " - Flac"
        fmt_str = "FLAC"
    else:
        fmt_suffix = " - mp3"
        fmt_str = "MP3"

    artist_counts = Counter()
    album_counts = Counter()
    year_counts = Counter()

    sample_files = []
    if len(flac_files) >= len(mp3_files):
        sample_files = flac_files + mp3_files
    else:
        sample_files = mp3_files + flac_files

    for fp in sample_files:
        art, alb, yr = extract_file_meta(fp)
        if art: artist_counts[art] += 1
        if alb:
            alb = re.sub(r'\s*-\s*(mp3|flac)\s*$', '', alb, flags=re.IGNORECASE)
            album_counts[alb] += 1
        if yr:  year_counts[yr] += 1

    if (not artist_counts or not album_counts or not year_counts) and cue_files:
        for cp in cue_files:
            cmeta = parse_cue(cp)
            if 'ARTIST' in cmeta and not artist_counts:
                artist_counts[cmeta['ARTIST']] += 10
            if 'ALBUM' in cmeta and not album_counts:
                album_counts[cmeta['ALBUM']] += 10
            if 'YEAR' in cmeta and not year_counts:
                year_counts[cmeta['YEAR']] += 10

    folder_name = os.path.basename(folder_path.rstrip(r'\/'))
    if not year_counts:
        m = re.search(r'\b(19\d\d|20\d\d)\b', folder_name)
        if m:
            year_counts[m.group(1)] += 1

    best_artist = artist_counts.most_common(1)[0][0] if artist_counts else ""
    best_album  = album_counts.most_common(1)[0][0] if album_counts else ""
    best_year   = year_counts.most_common(1)[0][0] if year_counts else ""

    return {
        'folder_name': folder_name,
        'artists': [best_artist] if best_artist else [],
        'albums': list(album_counts.keys()),
        'best_album': best_album,
        'years': [best_year] if best_year else [],
        'fmt_suffix': fmt_suffix,
        'fmt_str': fmt_str,
        'sub_album_count': len(sub_album_dirs),
        'mp3_count': len(mp3_files),
        'flac_count': len(flac_files)
    }, "OK"

def process_directory(target_dir, dry_run=False):
    win_base = to_win_path(target_dir)
    if not os.path.isdir(win_base):
        print(f"Error: Directory '{target_dir}' does not exist.")
        return

    subdirs = [os.path.join(win_base, d) for d in os.listdir(win_base) if os.path.isdir(os.path.join(win_base, d))]
    
    audio_subdirs = []
    for s in subdirs:
        for r, _, fs in os.walk(s):
            if any(os.path.splitext(f)[1].lower() in ('.mp3', '.flac') for f in fs):
                audio_subdirs.append(s)
                break

    if len(audio_subdirs) > 0:
        folders_to_process = [os.path.join(win_base, d) for d in os.listdir(win_base) if os.path.isdir(os.path.join(win_base, d))]
    else:
        folders_to_process = [win_base]

    plan = []
    for d in folders_to_process:
        meta, status = get_folder_metadata(d)
        curr_name = os.path.basename(d.rstrip(r'\/'))
        parent_dir = os.path.dirname(d.rstrip(r'\/'))

        if status != "OK":
            plan.append({
                'old_name': curr_name,
                'parent': parent_dir,
                'action': 'SKIP',
                'reason': status,
                'new_name': curr_name,
                'full_path': d
            })
            continue

        art = clean_tag(meta['artists'][0]) if meta['artists'] else ""
        alb = clean_tag(meta['best_album']) if meta['best_album'] else ""
        alb = re.sub(r'\s*-\s*(mp3|flac)\s*$', '', alb, flags=re.IGNORECASE)
        yr  = clean_tag(meta['years'][0]) if meta['years'] else ""
        fmt = meta['fmt_suffix']

        is_discog = ("discography" in curr_name.lower() or 
                     (meta['sub_album_count'] > 1 and len(meta['albums']) > 1))
        
        if is_discog:
            if "restored" in curr_name.lower():
                proposed = f"{art} - Restored{fmt}"
            else:
                proposed = f"{art} - Discography{fmt}"
        elif art and alb and yr:
            proposed = f"{art} - {alb} - {yr}{fmt}"
        elif art and alb:
            proposed = f"{art} - {alb}{fmt}"
        else:
            base_cleaned = re.sub(r'\s*-\s*(mp3|flac)\s*$', '', curr_name, flags=re.IGNORECASE)
            proposed = f"{base_cleaned}{fmt}"

        proposed = re.sub(r'\s+', ' ', proposed).strip()

        is_hires = ('24bit' in curr_name.lower() or '24-' in curr_name.lower() or 'flac-24bit' in curr_name.lower() or '[hi-res]' in curr_name.lower())
        
        is_already = False
        if curr_name.lower() == proposed.lower():
            is_already = True
        elif is_hires and (' - Flac' in proposed or ' - mp3' in proposed):
            prop_hires = proposed.replace(' - Flac', ' [Hi-Res] - Flac').replace(' - mp3', ' [Hi-Res] - mp3')
            if curr_name.lower() == prop_hires.lower():
                proposed = prop_hires
                is_already = True
        elif re.match(re.escape(proposed[:-len(fmt)]) + r'\s*\(\d+\)' + re.escape(fmt) + r'$', curr_name, re.IGNORECASE):
            is_already = True
            proposed = curr_name

        action = 'ALREADY_NAMED' if is_already else 'RENAME'
        plan.append({
            'old_name': curr_name,
            'parent': parent_dir,
            'action': action,
            'new_name': proposed,
            'artist': art,
            'album': alb,
            'year': yr,
            'format': meta['fmt_str'],
            'full_path': d,
            'hires': is_hires
        })

    # Collision disambiguation across plan AND existing disk items
    existing_on_disk = {os.path.basename(p.rstrip(r'\/')).lower() for p in folders_to_process}
    counts = Counter(p['new_name'] for p in plan if p['action'] == 'RENAME')
    allocated_names = {p['old_name'].lower() for p in plan if p['action'] == 'ALREADY_NAMED'}
    
    for p in plan:
        if p['action'] == 'RENAME':
            base_name = p['new_name']
            cand = base_name

            # If hires
            if p.get('hires') and '[Hi-Res]' not in cand:
                cand_hires = cand.replace(' - Flac', ' [Hi-Res] - Flac').replace(' - mp3', ' [Hi-Res] - mp3')
                if cand_hires.lower() not in allocated_names:
                    cand = cand_hires

            # If cand already taken or collided
            if cand.lower() in allocated_names or (counts[base_name] > 1 and cand.lower() in allocated_names):
                num = 2
                while True:
                    suffix_num = f" ({num})"
                    if ' - Flac' in base_name:
                        cand = base_name.replace(' - Flac', f'{suffix_num} - Flac')
                    elif ' - mp3' in base_name:
                        cand = base_name.replace(' - mp3', f'{suffix_num} - mp3')
                    else:
                        cand = f"{base_name}{suffix_num}"
                    if cand.lower() not in allocated_names and not os.path.exists(os.path.join(p['parent'], cand)):
                        break
                    num += 1

            p['new_name'] = cand
            allocated_names.add(cand.lower())

    # Display plan
    mode_str = "[DRY RUN - PREVIEW ONLY]" if dry_run else "[EXECUTION MODE]"
    print(f"\n{mode_str} Processing: {target_dir}")
    print("=" * 75)

    renamed_count = 0
    skipped_count = 0
    error_count = 0

    for p in plan:
        act = p['action']
        old_n = p['old_name']
        new_n = p.get('new_name', old_n)

        if act in ('SKIP', 'ALREADY_NAMED'):
            reason = p.get('reason', 'Already matches pattern')
            print(f"[{act:13}] {old_n} ({reason})")
            skipped_count += 1
            continue

        print(f"[RENAME]       '{old_n}'\n  -->          '{new_n}'")

        if not dry_run:
            old_full = os.path.join(p['parent'], old_n)
            new_full = os.path.join(p['parent'], new_n)
            success = False
            for attempt in range(3):
                try:
                    os.rename(old_full, new_full)
                    success = True
                    renamed_count += 1
                    break
                except Exception as e:
                    time.sleep(1)
                    if attempt == 2:
                        print(f"  [ERROR] Failed to rename '{old_n}': {e}")
                        error_count += 1
        else:
            renamed_count += 1

    print("=" * 75)
    print(f"Total: {len(plan)} | Renamed: {renamed_count} | Skipped: {skipped_count} | Errors: {error_count}\n")

def main():
    parser = argparse.ArgumentParser(description="Music Folder Renamer (BandName - AlbumName - Year - [mp3|Flac])")
    parser.add_argument("folder", help="Path to music folder or parent directory containing music folders")
    parser.add_argument("--dry-run", action="store_true", help="Preview proposed renames without changing files")
    args = parser.parse_args()

    process_directory(args.folder, dry_run=args.dry_run)

if __name__ == '__main__':
    main()
