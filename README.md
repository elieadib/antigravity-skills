# Antigravity Global Skills (Cloud Synced)

This repository holds your global skills for **Google Antigravity**, synchronized automatically across all your PCs using **OneDrive**.

## Included Skills

1. **Cinematic_Slideshow**: Transforms vacation photos and videos into high-end, cinematic 4K UHD slideshow movies with dynamic 2.5D Ken Burns effects, 30px white borders, dual-layer blurred matching backdrops leaving an 80px margin, custom title sequences, smooth transitions, and multi-platform hardware acceleration (Apple Silicon VideoToolbox, NVIDIA NVENC, Intel QSV, AMD AMF, CPU).
2. **CleanResidue**: Recursively scans music directories, cleans non-audio residue files (artwork, logs, cue sheets, videos, text), preserves designated audio formats (`mp3`, `m4a`, `flac`), and prunes empty directories.
3. **FLACMove_Convert**: Synchronizes FLAC album folders to a NAS or backup destination using multi-threaded Robocopy, converts MP3 files to VBR 128 kbps, converts FLAC files to MP3 VBR 190 kbps with metadata and cover art preservation, and safely deletes original FLAC files after verified conversion.
4. **Movie_Organizer**: Scans movie directories, standardizes video files and matching subtitles to `Movie Name - Release Year`, moves them to target folders, and safely cleans residual torrent assets.
5. **Music_Curator**: Audits, downloads, and embeds missing album cover art into MP3, FLAC, and M4A tags using local `cover.jpg` or online music databases (iTunes, Deezer, CoverArtArchive), and intelligently classifies and updates genre tags into 7 standardized categories.
6. **music-cue-flac-splitter**: Recursively scans music directories for unsplit big FLAC, APE, or WAV audio files paired with CUE sheets, losslessly splits them into individual FLAC tracks with embedded Vorbis metadata, and verifies sample-accurate durations.
7. **music-folder-renamer**: Extracts Band name, Album name, and Year from MP3 and FLAC audio tags, and standardizes album folder names to `BandName - AlbumName - Year - mp3` or `BandName - AlbumName - Year - Flac`.
8. **music-track-renamer**: Extracts Band name, Album name, and Track name from MP3 and FLAC audio tags, and standardizes all music filenames inside every folder to `BandName - AlbumName - TrackName`.

---

## How to Enable on Any PC / Mac (1-Click Setup)

### On Windows:
1. Ensure OneDrive is signed in and has finished syncing the `Antigravity` folder.
2. Navigate to: `OneDrive\Antigravity\skills`
3. Double-click **`install_skills_on_other_pc.bat`** (or run `install_skills_on_other_pc.ps1` in PowerShell).

### On Mac:
1. Ensure OneDrive is signed in and syncing.
2. Run in Terminal:
   ```bash
   bash "$HOME/Library/CloudStorage/OneDrive-Personal/Antigravity/skills/install_skills_on_mac.sh"
   ```

### Automatic Two-Way Sync
Any changes, enhancements, or new skills created on **any** of your computers are immediately saved directly to this OneDrive folder and will automatically sync across all your machines!
