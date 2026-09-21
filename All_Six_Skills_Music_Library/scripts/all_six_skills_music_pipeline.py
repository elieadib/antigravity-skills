#!/usr/bin/env python3
"""
all_six_skills_music_pipeline.py - Master Orchestrator for Complete Music Library Processing
=============================================================================================
Orchestrates the 6 music library management skills in the defined order:
  1. Music_folder_Renamer   - Standardizes album folder names to 'Band - Album - Year - Format'
  2. Rename-tracks          - Renames audio files to 'Band - Album - TrackName.ext'
  3. Music_Curator          - Audits/embeds album cover art & classifies genres into 7 categories
  4. Split-cue-flac         - Losslessly splits unsplit CUE/FLAC albums (with post-split standardization)
  5. CleanResidue           - Purges loose artwork, logs, CUEs, and prunes empty directories
  6. FLACMove_Convert       - Mirrors FLACs to NAS via Robocopy, downsamples MP3s, transcodes FLACs, renames to - mp3

Supports:
  - Full end-to-end execution
  - Dry-run preview mode (--dry-run)
  - Step range execution (--step N, --from-step N)
  - Automatic post-split track renaming & cover embedding for any CUE albums
  - Resilient high-res audio transcoding timeout and concurrency configuration
"""

import os
import sys
import io
import time
import argparse
import subprocess
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_SOURCE_PATH = r"G:\mp3-RawG"
DEFAULT_NAS_DEST = r"V:\NetGear-NAS-3-HDD1\My_FLAC_Collections\My_FLAC_Collections"


def get_skills_root():
    """Locate the root directory containing sibling skill folders."""
    # Priority 1: Relative to this script (inside All_Six_Skills_Music_Library/scripts)
    candidate = Path(__file__).resolve().parent.parent.parent
    if (candidate / "CleanResidue").is_dir() and (candidate / "FLACMove_Convert").is_dir():
        return candidate
    # Priority 2: Standard global config path
    global_path = Path.home() / ".gemini" / "config" / "skills"
    if global_path.is_dir():
        return global_path
    return candidate


def build_environment():
    """Prepare environment variables with virtualenv site-packages if available."""
    env = os.environ.copy()
    candidate_venvs = [
        str(Path.home() / ".gemini" / "antigravity" / "scratch" / ".venv" / "Lib" / "site-packages"),
        str(Path.home() / ".venv" / "Lib" / "site-packages"),
        os.path.expandvars(r"%APPDATA%\Python\Python313\site-packages"),
        os.path.expandvars(r"%APPDATA%\Python\Python312\site-packages"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python312\Lib\site-packages"),
    ]
    extra_paths = [p for p in candidate_venvs if os.path.isdir(p)]
    if extra_paths:
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join(extra_paths + ([existing] if existing else []))
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def log_header(title):
    print("\n" + "=" * 75, flush=True)
    ts = time.strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{ts} {title}", flush=True)
    print("=" * 75, flush=True)


def run_command_live(cmd, env=None, cwd=None):
    """Execute command streaming stdout and stderr in real time."""
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=cwd,
    )
    for line in proc.stdout:
        print(line, end="", flush=True)
    proc.wait()
    return proc.returncode


class MusicPipelineRunner:
    def __init__(self, source_dir, nas_dest, dry_run=False, keep_flac=False,
                 workers=8, timeout=600, auto_genre=True):
        self.source_dir = os.path.abspath(source_dir)
        self.nas_dest = os.path.abspath(nas_dest) if nas_dest else None
        self.dry_run = dry_run
        self.keep_flac = keep_flac
        self.workers = workers
        self.timeout = timeout
        self.auto_genre = auto_genre

        self.skills_root = get_skills_root()
        self.env = build_environment()
        self.python_bin = sys.executable

        # Resolve script paths
        self.script_folder_renamer = self.skills_root / "music-folder-renamer" / "scripts" / "music_renamer.py"
        self.script_track_renamer  = self.skills_root / "music-track-renamer" / "scripts" / "rename_tracks.py"
        self.script_curator        = self.skills_root / "Music_Curator" / "scripts" / "music_curator.py"
        self.script_cue_splitter   = self.skills_root / "music-cue-flac-splitter" / "scripts" / "split_cue_flac.py"
        self.script_clean_residue  = self.skills_root / "CleanResidue" / "scripts" / "clean_residue.py"
        self.script_flac_move      = self.skills_root / "FLACMove_Convert" / "scripts" / "flac_move_convert.py"

        self._validate_scripts()

    def _validate_scripts(self):
        scripts = [
            ("music-folder-renamer", self.script_folder_renamer),
            ("music-track-renamer", self.script_track_renamer),
            ("Music_Curator", self.script_curator),
            ("music-cue-flac-splitter", self.script_cue_splitter),
            ("CleanResidue", self.script_clean_residue),
            ("FLACMove_Convert", self.script_flac_move),
        ]
        missing = [name for name, p in scripts if not p.is_file()]
        if missing:
            raise FileNotFoundError(f"Missing required skill scripts under {self.skills_root}: {missing}")

    def step_1_folder_renamer(self):
        log_header("STEP 1 / 6: Music Folder Renamer")
        cmd = [self.python_bin, str(self.script_folder_renamer)]
        if self.dry_run:
            cmd.append("--dry-run")
        cmd.append(self.source_dir)
        return run_command_live(cmd, env=self.env) == 0

    def step_2_rename_tracks(self):
        log_header("STEP 2 / 6: Rename Audio Tracks")
        cmd = [self.python_bin, str(self.script_track_renamer)]
        if self.dry_run:
            cmd.append("--dry-run")
        cmd.append(self.source_dir)
        return run_command_live(cmd, env=self.env) == 0

    def step_3_music_curator(self):
        log_header("STEP 3 / 6: Music Curator (Cover Art & Intelligent Genre)")
        cmd = [self.python_bin, str(self.script_curator), self.source_dir]
        if self.auto_genre:
            cmd.append("--auto-genre")
        if self.dry_run:
            cmd.append("--dry-run")
        return run_command_live(cmd, env=self.env) == 0

    def step_4_split_cue_flac(self):
        log_header("STEP 4 / 6: Split CUE / FLAC Albums")
        # Find candidate CUE albums before splitting to know if follow-up polish is needed
        cues_before = []
        for root, _, files in os.walk(self.source_dir):
            if any(f.lower().endswith(".cue") for f in files):
                cues_before.append(root)

        cmd = [self.python_bin, str(self.script_cue_splitter)]
        if self.dry_run:
            cmd.append("--dry-run")
        else:
            cmd.append("--delete-originals")
        cmd.append(self.source_dir)
        res = run_command_live(cmd, env=self.env)
        if res != 0:
            return False

        # If any CUE album was split and not dry-run, run track renamer and music curator
        # on those folders so newly extracted tracks match library standards before residue purging
        if cues_before and not self.dry_run:
            print("\n[INFO] Running post-split polish on newly split albums...", flush=True)
            for album_folder in cues_before:
                if os.path.isdir(album_folder):
                    print(f"  -> Polishing split album: {os.path.basename(album_folder)}")
                    run_command_live([self.python_bin, str(self.script_track_renamer), album_folder], env=self.env)
                    run_command_live([self.python_bin, str(self.script_curator), album_folder, "--auto-genre"], env=self.env)

        return True

    def step_5_clean_residue(self):
        log_header("STEP 5 / 6: Clean Non-Audio Residue")
        cmd = [self.python_bin, str(self.script_clean_residue)]
        if self.dry_run:
            cmd.append("--dry-run")
        cmd.append(self.source_dir)
        return run_command_live(cmd, env=self.env) == 0

    def step_6_flac_move_convert(self):
        log_header("STEP 6 / 6: FLACMove_Convert (NAS Sync, Transcode & Suffix Update)")
        if not self.nas_dest:
            print("[ERROR] NAS destination path must be provided for FLACMove_Convert.", flush=True)
            return False

        cmd = [
            self.python_bin, str(self.script_flac_move),
            "all",
            self.source_dir,
            self.nas_dest,
            "--workers", str(self.workers),
            "--timeout", str(self.timeout),
        ]
        if self.keep_flac:
            cmd.append("--keep-flac")
        if self.dry_run:
            cmd.append("--dry-run")

        return run_command_live(cmd, env=self.env) == 0

    def run_all(self, start_step=1, end_step=6):
        start_time = time.time()
        print("=" * 75, flush=True)
        print("🎵 ALL SIX SKILLS - MUSIC LIBRARY PIPELINE", flush=True)
        print(f"Source:      {self.source_dir}", flush=True)
        print(f"NAS Dest:    {self.nas_dest or '(None specified)'}", flush=True)
        print(f"Mode:        {'[DRY RUN - PREVIEW ONLY]' if self.dry_run else '[LIVE EXECUTION]'}", flush=True)
        print(f"Steps:       {start_step} through {end_step}", flush=True)
        print("=" * 75, flush=True)

        if not os.path.isdir(self.source_dir):
            print(f"[ERROR] Source directory does not exist: {self.source_dir}", flush=True)
            return False

        steps = [
            (1, "Music_folder_Renamer", self.step_1_folder_renamer),
            (2, "Rename-tracks", self.step_2_rename_tracks),
            (3, "Music_Curator", self.step_3_music_curator),
            (4, "Split-cue-flac", self.step_4_split_cue_flac),
            (5, "CleanResidue", self.step_5_clean_residue),
            (6, "FLACMove_Convert", self.step_6_flac_move_convert),
        ]

        step_results = {}
        for num, name, func in steps:
            if num < start_step or num > end_step:
                step_results[name] = "SKIPPED"
                continue
            ok = func()
            step_results[name] = "SUCCESS" if ok else "FAILED"
            if not ok:
                print(f"\n[ERROR] Step {num} ({name}) failed. Aborting pipeline.", flush=True)
                break

        elapsed = (time.time() - start_time) / 60.0
        log_header("PIPELINE SUMMARY REPORT")
        for num, name, _ in steps:
            status = step_results.get(name, "NOT REACHED")
            print(f"  Step {num}: {name:<25} [{status}]")
        print(f"\nTotal Pipeline Duration: {elapsed:.2f} minutes")
        print("=" * 75, flush=True)
        return all(res in ("SUCCESS", "SKIPPED") for res in step_results.values())


def main():
    parser = argparse.ArgumentParser(
        description="Master Orchestrator for All Six Music Skills: Folder Renaming, Track Renaming, Curation, CUE Splitting, Residue Purging, and NAS Backup & Transcoding."
    )
    parser.add_argument("source", nargs="?", default=DEFAULT_SOURCE_PATH,
                        help=f"Source directory containing music folders (default: '{DEFAULT_SOURCE_PATH}')")
    parser.add_argument("--dest-nas", default=DEFAULT_NAS_DEST,
                        help=f"Destination NAS folder for FLAC backup (default: '{DEFAULT_NAS_DEST}')")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview proposed operations without modifying files")
    parser.add_argument("--step", type=int, choices=[1, 2, 3, 4, 5, 6],
                        help="Run only a single specific step (1-6)")
    parser.add_argument("--from-step", type=int, default=1, choices=[1, 2, 3, 4, 5, 6],
                        help="Start execution from a specific step (default: 1)")
    parser.add_argument("--keep-flac", action="store_true",
                        help="Convert FLACs without deleting local originals in step 6")
    parser.add_argument("--workers", type=int, default=8,
                        help="Parallel worker threads for audio conversion (default: 8)")
    parser.add_argument("--timeout", type=int, default=600,
                        help="Timeout in seconds per file for FLAC transcoding (default: 600s)")
    parser.add_argument("--no-auto-genre", action="store_true",
                        help="Do not auto-detect and update genre tags in step 3")

    args = parser.parse_args()

    start_step = args.step if args.step else args.from_step
    end_step = args.step if args.step else 6

    runner = MusicPipelineRunner(
        source_dir=args.source,
        nas_dest=args.dest_nas,
        dry_run=args.dry_run,
        keep_flac=args.keep_flac,
        workers=args.workers,
        timeout=args.timeout,
        auto_genre=(not args.no_auto_genre),
    )

    success = runner.run_all(start_step=start_step, end_step=end_step)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
