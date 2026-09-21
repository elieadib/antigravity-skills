#!/usr/bin/env python3
# clean_residue.py - Clean residue files from music directories while keeping target audio formats
import os
import sys
import io
import stat
import time
import argparse
from collections import defaultdict

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num_bytes) < 1024.0 or unit == "TB":
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"


def force_remove_file(filepath: str) -> None:
    """Remove a file, clearing read-only attributes if needed."""
    try:
        os.remove(filepath)
    except PermissionError:
        try:
            os.chmod(filepath, stat.S_IWRITE | stat.S_IREAD)
            os.remove(filepath)
        except Exception as e:
            raise e


def scan_and_clean(
    root_dir: str,
    keep_exts: set[str],
    dry_run: bool = False,
    prune_empty_dirs: bool = True,
    verbose: bool = False,
) -> dict:
    """Recursively scan root_dir, delete non-keep files, and prune empty folders."""
    if not os.path.exists(root_dir):
        raise FileNotFoundError(f"Target directory does not exist: {root_dir}")

    stats = {
        "total_files": 0,
        "keep_files": 0,
        "delete_files": 0,
        "bytes_kept": 0,
        "bytes_deleted": 0,
        "deleted_by_ext": defaultdict(lambda: {"count": 0, "bytes": 0}),
        "kept_by_ext": defaultdict(lambda: {"count": 0, "bytes": 0}),
        "empty_dirs_pruned": 0,
        "errors": [],
    }

    files_to_delete = []

    print(f"[*] Scanning '{root_dir}'...")
    start_time = time.time()

    # Pass 1: Scan all files
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            stats["total_files"] += 1
            fpath = os.path.join(dirpath, fname)
            try:
                fsize = os.path.getsize(fpath)
            except OSError:
                fsize = 0

            _, ext = os.path.splitext(fname)
            ext_lower = ext.lower() if ext else "(no extension)"

            if ext_lower in keep_exts:
                stats["keep_files"] += 1
                stats["bytes_kept"] += fsize
                stats["kept_by_ext"][ext_lower]["count"] += 1
                stats["kept_by_ext"][ext_lower]["bytes"] += fsize
            else:
                stats["delete_files"] += 1
                stats["bytes_deleted"] += fsize
                stats["deleted_by_ext"][ext_lower]["count"] += 1
                stats["deleted_by_ext"][ext_lower]["bytes"] += fsize
                files_to_delete.append((fpath, fsize))

    # Pass 2: Delete residue files
    if not dry_run:
        print(f"[*] Deleting {len(files_to_delete)} residue files...")
        for fpath, _ in files_to_delete:
            try:
                force_remove_file(fpath)
                if verbose:
                    print(f"  [DELETED] {fpath}")
            except Exception as e:
                stats["errors"].append((fpath, str(e)))
                print(f"  [ERROR] Failed to delete {fpath}: {e}", file=sys.stderr)
    else:
        print(f"[DRY RUN] Would delete {len(files_to_delete)} residue files.")

    # Pass 3: Prune empty directories (bottom-up)
    if prune_empty_dirs:
        if not dry_run:
            for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
                try:
                    if not os.listdir(dirpath) and os.path.abspath(dirpath) != os.path.abspath(root_dir):
                        try:
                            os.rmdir(dirpath)
                            stats["empty_dirs_pruned"] += 1
                            if verbose:
                                print(f"  [PRUNED DIR] {dirpath}")
                        except PermissionError:
                            os.chmod(dirpath, stat.S_IWRITE | stat.S_IREAD)
                            os.rmdir(dirpath)
                            stats["empty_dirs_pruned"] += 1
                            if verbose:
                                print(f"  [PRUNED DIR] {dirpath}")
                except Exception as e:
                    stats["errors"].append((dirpath, str(e)))
        else:
            # Estimate empty directories in dry-run
            retained_dirs = set()
            for dirpath, _, filenames in os.walk(root_dir):
                for fname in filenames:
                    _, ext = os.path.splitext(fname)
                    if ext.lower() in keep_exts:
                        curr = os.path.abspath(dirpath)
                        while curr and curr != os.path.abspath(root_dir):
                            retained_dirs.add(curr)
                            parent = os.path.dirname(curr)
                            if parent == curr:
                                break
                            curr = parent

            for dirpath, _, _ in os.walk(root_dir, topdown=False):
                abs_p = os.path.abspath(dirpath)
                if abs_p != os.path.abspath(root_dir) and abs_p not in retained_dirs:
                    stats["empty_dirs_pruned"] += 1
                    if verbose:
                        print(f"  [WOULD PRUNE DIR] {dirpath}")

    stats["elapsed_seconds"] = time.time() - start_time
    return stats


def print_report(stats: dict, dry_run: bool, keep_exts: set[str]) -> None:
    """Display detailed summary report."""
    mode_str = "[DRY RUN PREVIEW]" if dry_run else "[EXECUTION REPORT]"
    print("\n" + "=" * 60)
    print(f"  CleanResidue - {mode_str}")
    print("=" * 60)
    print(f"Target extensions to keep: {', '.join(sorted(keep_exts))}")
    print(f"Total files scanned:       {stats['total_files']:,}")
    print(f"Files to KEEP:             {stats['keep_files']:,} ({format_bytes(stats['bytes_kept'])})")
    action_verb = "Files to DELETE" if dry_run else "Files DELETED"
    print(f"{action_verb}:           {stats['delete_files']:,} ({format_bytes(stats['bytes_deleted'])})")
    dir_verb = "Empty dirs to prune" if dry_run else "Empty dirs pruned"
    print(f"{dir_verb}:        {stats['empty_dirs_pruned']:,}")
    print(f"Elapsed time:              {stats['elapsed_seconds']:.2f}s")

    if stats["kept_by_ext"]:
        print("\n--- Audio Files Kept by Extension ---")
        for ext, data in sorted(stats["kept_by_ext"].items(), key=lambda x: -x[1]["count"]):
            print(f"  {ext:<16} : {data['count']:>6,} files ({format_bytes(data['bytes'])})")

    if stats["deleted_by_ext"]:
        header = "--- Residue to Delete by Extension ---" if dry_run else "--- Residue Deleted by Extension ---"
        print(f"\n{header}")
        for ext, data in sorted(stats["deleted_by_ext"].items(), key=lambda x: -x[1]["bytes"]):
            print(f"  {ext:<16} : {data['count']:>6,} files ({format_bytes(data['bytes'])})")

    if stats["errors"]:
        print(f"\n[WARNING] {len(stats['errors'])} errors occurred:")
        for path, err in stats["errors"][:10]:
            print(f"  - {path}: {err}")
        if len(stats["errors"]) > 10:
            print(f"  ... and {len(stats['errors']) - 10} more.")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Clean residue files from music directories while keeping target audio formats (default: .mp3, .m4a, .flac)."
    )
    parser.add_argument("target", help="Path to target directory to scan and clean.")
    parser.add_argument(
        "--keep",
        "-k",
        default="mp3,m4a,flac",
        help="Comma-separated list of extensions to keep (e.g. 'mp3,m4a,flac'). Defaults to 'mp3,m4a,flac'.",
    )
    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Preview changes without deleting any files or directories.",
    )
    parser.add_argument(
        "--no-prune",
        action="store_true",
        help="Do not prune empty directories after deleting residue files.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed per-file deletion and directory pruning logs.",
    )

    args = parser.parse_args()

    keep_list = [ext.strip().lower() for ext in args.keep.split(",") if ext.strip()]
    keep_exts = {ext if ext.startswith(".") else f".{ext}" for ext in keep_list}

    target_dir = os.path.abspath(args.target)
    if not os.path.isdir(target_dir):
        print(f"Error: Target path '{target_dir}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    stats = scan_and_clean(
        root_dir=target_dir,
        keep_exts=keep_exts,
        dry_run=args.dry_run,
        prune_empty_dirs=not args.no_prune,
        verbose=args.verbose,
    )

    print_report(stats, dry_run=args.dry_run, keep_exts=keep_exts)

    if stats["errors"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
