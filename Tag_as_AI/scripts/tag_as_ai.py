#!/usr/bin/env python3
"""
tag_as_ai.py - Automated AI Audio Metadata & Genre Tagging Utility
Recursively audits music libraries and standardizes audio metadata to tag tracks as AI-generated music.

Supported Formats:
  - MP3  (ID3v2.3 TCON genre frame, TIT1 grouping, COMM comment)
  - FLAC (Vorbis GENRE, GROUPING, COMMENT comments)
  - M4A  (MP4 (c)gen genre, (c)grp grouping, (c)cmt comment)

Features:
  - Sets Genre to designated AI genre (default: 'AI_Rock', or custom e.g. 'AI_Jazz', 'AI_Music')
  - Supports --prefix-existing to convert existing genre (e.g. 'Rock' -> 'AI_Rock', 'Prog' -> 'AI_Prog')
  - Supports optional AI grouping (--grouping) and provenance comments (--comment)
  - Fully preserves existing album artwork (APIC / Picture / covr) and all other metadata tags
  - Supports recursive directory processing or individual audio files
  - Robust Windows long-path handling (\\\\?\\ prefix)
  - Safe dry-run mode (--dry-run) for previewing changes before modifying tags
"""

import os
import sys
import argparse
from pathlib import Path
from collections import Counter

# Set UTF-8 encoding on standard output if supported
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Auto-locate mutagen from virtual environments if not in system python
try:
    import mutagen
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    from mutagen.id3 import ID3, TCON, TIT1, COMM, ID3NoHeaderError
except ImportError:
    user_home = Path.home()
    py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    candidate_venv_paths = [
        str(user_home / ".gemini" / "antigravity" / "scratch" / ".venv" / "Lib" / "site-packages"),
        str(user_home / ".gemini" / "antigravity" / "scratch" / ".venv" / "lib" / py_ver / "site-packages"),
        str(user_home / ".venv" / "Lib" / "site-packages"),
        str(user_home / ".venv" / "lib" / py_ver / "site-packages"),
        os.path.expandvars(r"%APPDATA%\Python\Python314\site-packages"),
        os.path.expandvars(r"%APPDATA%\Python\Python313\site-packages"),
        os.path.expandvars(r"%APPDATA%\Python\Python312\site-packages"),
        os.path.expandvars(r"%APPDATA%\Python\Python311\site-packages"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python314\Lib\site-packages"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python313\Lib\site-packages"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python312\Lib\site-packages"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python311\Lib\site-packages"),
    ]
    for vp in candidate_venv_paths:
        if os.path.isdir(vp) and vp not in sys.path:
            sys.path.insert(0, vp)
    try:
        import mutagen
        from mutagen.mp3 import MP3
        from mutagen.flac import FLAC
        from mutagen.mp4 import MP4
        from mutagen.id3 import ID3, TCON, TIT1, COMM, ID3NoHeaderError
    except ImportError:
        print(
            "Error: 'mutagen' library is required to read and write audio tags.\n"
            "Please install it using: pip install mutagen",
            file=sys.stderr
        )
        sys.exit(1)

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".m4a"}


def get_current_genre(file_path: str) -> str:
    """Extracts current genre string from audio tags, or empty string if not found."""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".mp3":
            try:
                audio = MP3(file_path)
                if audio.tags and "TCON" in audio.tags:
                    genres = audio.tags["TCON"].genres
                    if genres:
                        return str(genres[0]).strip()
                    text = audio.tags["TCON"].text
                    if text:
                        return str(text[0]).strip()
            except Exception:
                try:
                    tags = ID3(file_path)
                    if "TCON" in tags:
                        genres = tags["TCON"].genres
                        if genres:
                            return str(genres[0]).strip()
                        text = tags["TCON"].text
                        if text:
                            return str(text[0]).strip()
                except Exception:
                    pass

        elif ext == ".flac":
            audio = FLAC(file_path)
            genres = audio.get("genre", [])
            if genres:
                return str(genres[0]).strip()

        elif ext == ".m4a":
            audio = MP4(file_path)
            genres = audio.get("\xa9gen", [])
            if genres:
                return str(genres[0]).strip()
    except Exception:
        pass

    return ""


def determine_target_genre(current_genre: str, default_genre: str, prefix_existing: bool) -> str:
    """
    Computes the target genre:
    - If prefix_existing is True and current_genre is non-empty:
        prefixes with 'AI_' (ensuring no duplicate prefix).
    - Otherwise, returns default_genre.
    """
    if prefix_existing and current_genre:
        cleaned = current_genre.strip()
        # Avoid duplicate prefixes like AI_AI_Rock, AI - AI_Rock, etc.
        if cleaned.upper().startswith("AI_"):
            return cleaned
        if cleaned.upper().startswith("AI - "):
            return f"AI_{cleaned[5:].strip()}"
        if cleaned.upper().startswith("AI-"):
            return f"AI_{cleaned[3:].strip()}"
        return f"AI_{cleaned}"
    
    return default_genre


def set_audio_metadata(file_path: str, genre: str, grouping: str = None, comment: str = None) -> bool:
    """Updates the genre, grouping, and comment tags while preserving artwork and other metadata."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".flac":
        try:
            audio = FLAC(file_path)
            audio["genre"] = [genre]
            if grouping:
                audio["grouping"] = [grouping]
            if comment:
                audio["comment"] = [comment]
            audio.save()
            return True
        except Exception as e:
            print(f"    [Error] Failed updating FLAC {os.path.basename(file_path)}: {e}", file=sys.stderr)
            return False

    elif ext == ".mp3":
        try:
            try:
                audio = MP3(file_path)
                if audio.tags is None:
                    audio.add_tags()
                audio.tags.delall("TCON")
                audio.tags.add(TCON(encoding=3, text=[genre]))
                if grouping:
                    audio.tags.delall("TIT1")
                    audio.tags.add(TIT1(encoding=3, text=[grouping]))
                if comment:
                    audio.tags.delall("COMM")
                    audio.tags.add(COMM(encoding=3, lang="eng", desc="", text=[comment]))
                audio.save(v2_version=3)
                return True
            except Exception:
                try:
                    tags = ID3(file_path)
                except ID3NoHeaderError:
                    tags = ID3()
                tags.delall("TCON")
                tags.add(TCON(encoding=3, text=[genre]))
                if grouping:
                    tags.delall("TIT1")
                    tags.add(TIT1(encoding=3, text=[grouping]))
                if comment:
                    tags.delall("COMM")
                    tags.add(COMM(encoding=3, lang="eng", desc="", text=[comment]))
                tags.save(file_path, v2_version=3)
                return True
        except Exception as e:
            print(f"    [Error] Failed updating MP3 {os.path.basename(file_path)}: {e}", file=sys.stderr)
            return False

    elif ext == ".m4a":
        try:
            m4 = MP4(file_path)
            m4["\xa9gen"] = [genre]
            if grouping:
                m4["\xa9grp"] = [grouping]
            if comment:
                m4["\xa9cmt"] = [comment]
            m4.save()
            return True
        except Exception as e:
            print(f"    [Error] Failed updating M4A {os.path.basename(file_path)}: {e}", file=sys.stderr)
            return False

    return False


def collect_target_files(scan_root: str):
    """
    Collects audio files mapped by directory.
    Supports single file or recursive directory traversal.
    """
    folders_map = {}
    if os.path.isfile(scan_root):
        ext = os.path.splitext(scan_root)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            parent = os.path.dirname(scan_root)
            folders_map[parent] = [scan_root]
        return folders_map

    for root, _, files in os.walk(scan_root):
        audio_in_dir = [
            os.path.join(root, f) for f in files
            if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS
        ]
        if audio_in_dir:
            folders_map[root] = sorted(audio_in_dir)

    return folders_map


def process_tag_as_ai(
    target_path: str,
    genre: str = "AI_Rock",
    prefix_existing: bool = False,
    grouping: str = None,
    comment: str = None,
    dry_run: bool = False
) -> bool:
    """Main execution function to scan and tag audio files as AI."""
    norm_path = os.path.abspath(target_path)
    if os.name == "nt" and not norm_path.startswith("\\\\?\\"):
        scan_root = "\\\\?\\" + norm_path
    else:
        scan_root = norm_path

    if not os.path.exists(scan_root):
        print(f"Error: Target path '{target_path}' does not exist.", file=sys.stderr)
        return False

    folders_map = collect_target_files(scan_root)
    total_audio_files = sum(len(f_list) for f_list in folders_map.values())

    print("=" * 65)
    print("TAG AS AI - AUDIO METADATA & GENRE CURATOR")
    print(f"Target Path:      {norm_path}")
    print(f"Target Genre:     {genre}")
    print(f"Prefix Existing:  {'Enabled (e.g. Rock -> AI_Rock)' if prefix_existing else 'Disabled'}")
    if grouping:
        print(f"Grouping Tag:     {grouping}")
    if comment:
        print(f"Comment Tag:      {comment}")
    print(f"Mode:             {'DRY-RUN (Preview Only)' if dry_run else 'ACTIVE (Modifying Audio Tags)'}")
    print(f"Discovered:       {len(folders_map)} folders ({total_audio_files} audio files)")
    print("=" * 65)

    if total_audio_files == 0:
        print("\nNo supported audio files (.mp3, .flac, .m4a) found.")
        return True

    stats = {
        "total_files": total_audio_files,
        "updated": 0,
        "failed": 0,
        "unchanged": 0,
        "genres_assigned": Counter()
    }

    for folder_path, audio_files in sorted(folders_map.items()):
        folder_display = folder_path.replace("\\\\?\\", "")
        folder_name = os.path.basename(folder_display) or folder_display
        folder_counts = Counter()

        print(f"\n[Folder] {folder_name} ({len(audio_files)} tracks)")

        for af in audio_files:
            current_g = get_current_genre(af)
            target_g = determine_target_genre(current_g, genre, prefix_existing)

            # Check if tag is already identical and no extra tags requested
            is_already_set = (current_g == target_g and grouping is None and comment is None)

            if dry_run:
                stats["updated"] += 1
                stats["genres_assigned"][target_g] += 1
                folder_counts[target_g] += 1
            else:
                success = set_audio_metadata(af, target_g, grouping=grouping, comment=comment)
                if success:
                    stats["updated"] += 1
                    stats["genres_assigned"][target_g] += 1
                    folder_counts[target_g] += 1
                else:
                    stats["failed"] += 1

        summary_parts = [f"{g}: {count}" for g, count in folder_counts.items()]
        summary_str = ", ".join(summary_parts) if summary_parts else "None"
        if dry_run:
            print(f"  -> [DRY-RUN] Would update {len(audio_files)} tracks ({summary_str})")
        else:
            print(f"  -> Genre tags updated ({summary_str})")

    print("\n" + "=" * 65)
    print("TAG AS AI EXECUTION SUMMARY")
    print(f"Total audio files scanned:         {stats['total_files']}")
    print(f"Total files updated:               {stats['updated']}")
    if stats["failed"] > 0:
        print(f"Total files failed:                {stats['failed']}")
    print(f"\nGenre Tag Distribution ({sum(stats['genres_assigned'].values())} tracks):")
    for g, count in stats["genres_assigned"].most_common():
        print(f"  • {g:24s}: {count:5d} tracks")
    print("=" * 65)
    return stats["failed"] == 0


def main():
    parser = argparse.ArgumentParser(
        description="Tag music files and folders as AI-generated music (ID3, Vorbis, MP4)."
    )
    parser.add_argument("path", help="Path to music folder or individual audio file")
    parser.add_argument(
        "--genre", "-g",
        default="AI_Rock",
        help="Target AI Genre tag (default: 'AI_Rock', e.g. 'AI_Pop', 'AI_Music', 'AI_Jazz')"
    )
    parser.add_argument(
        "--prefix-existing", "-p",
        action="store_true",
        help="Prefix existing genre tag with 'AI_' (e.g. 'Rock' -> 'AI_Rock', 'Progressive Rock' -> 'AI_Progressive Rock')"
    )
    parser.add_argument(
        "--grouping",
        default=None,
        help="Optional Content Grouping tag (e.g. 'AI Music' or 'Suno')"
    )
    parser.add_argument(
        "--comment", "-c",
        default=None,
        help="Optional comment tag (e.g. 'AI Generated Music' or generation model notes)"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Preview tag updates without modifying files"
    )

    args = parser.parse_args()

    success = process_tag_as_ai(
        target_path=args.path,
        genre=args.genre,
        prefix_existing=args.prefix_existing,
        grouping=args.grouping,
        comment=args.comment,
        dry_run=args.dry_run
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
