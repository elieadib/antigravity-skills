# Antigravity Global Skills (Cloud Synced)

This repository holds your global skills for **Google Antigravity**, synchronized automatically across all your PCs using **Google Drive**.

## Included Skills

1. **Cinematic_Slideshow**: Transforms vacation photos and videos into high-end, cinematic 4K UHD slideshow movies with dynamic 2.5D Ken Burns effects, 30px white borders, dual-layer blurred matching backdrops leaving an 80px blurred background margin, custom title sequences, smooth transitions, and multi-platform hardware acceleration (Apple Silicon VideoToolbox, NVIDIA NVENC, Intel QSV, AMD AMF, CPU).
2. **CleanResidue**: Recursively scans music directories, cleans non-audio residue files (artwork, logs, cue sheets, videos, text), preserves designated audio formats (`mp3`, `m4a`, `flac`), and prunes empty directories.
3. **FLACMove_Convert**: Synchronizes FLAC album folders to a NAS or backup destination using multi-threaded Robocopy, converts MP3 files to VBR 128 kbps, converts FLAC files to MP3 VBR 190 kbps with metadata and cover art preservation, and safely deletes original FLAC files after verified conversion.
4. **Before_the_Move_to_JF**: Prepares movie video files and matching subtitles (.srt) before moving them to Jellyfin (JF) or media servers. Scans directories containing movie folders, standardizes movie files and subtitles to `Movie Name - Release Year`, moves both files to the root/target directory, and safely cleans emptied source folders and residual torrent assets.
5. **Music_Curator**: Audits, downloads, and embeds missing album cover art into MP3, FLAC, and M4A tags using local `cover.jpg` or online music databases (iTunes, Deezer, CoverArtArchive), and intelligently classifies and updates genre tags into 7 standardized categories.
6. **music-cue-flac-splitter**: Recursively scans music directories for unsplit big FLAC, APE, or WAV audio files paired with CUE sheets, losslessly splits them into individual FLAC tracks with embedded Vorbis metadata, and verifies sample-accurate durations.
7. **music-folder-renamer**: Extracts Band name, Album name, and Year from MP3 and FLAC audio tags, and standardizes album folder names to `BandName - AlbumName - Year - mp3` or `BandName - AlbumName - Year - Flac`.
8. **music-track-renamer**: Extracts Band name, Album name, and Track name from MP3 and FLAC audio tags, and standardizes all music filenames inside every folder to `BandName - AlbumName - TrackName`.
9. **Tag_as_AI**: Audits and standardizes audio metadata across music directories or individual tracks to tag them as AI-generated music. Sets Genre tags to designated AI genres (default: `AI_Rock`, or custom e.g. `AI_Jazz`), supports prefixing existing genres with `AI_`, and allows optional AI grouping and comment markers while preserving artwork and audio metadata intact.
10. **+faststart**: Losslessly optimizes MP4, MOV, and M4V videos for instant progressive web streaming by moving the `moov` atom metadata index to the beginning of the file (`ffmpeg -c copy -movflags +faststart`), eliminating initial buffering delays and enabling instant playback across web browsers and mobile devices.
11. **All_Six_Skills_Music_Library**: Executes the end-to-end 6-skill music library processing pipeline in order: 1. Music_folder_Renamer, 2. Rename-tracks, 3. Music_Curator, 4. Split-cue-flac, 5. CleanResidue, and 6. FLACMove_Convert. Standardizes album folder and track names, audits and embeds cover art, applies intelligent genre tagging, losslessly splits CUE/FLAC albums, purges non-audio residue, syncs FLACs to NAS via multi-threaded Robocopy, downsamples MP3s to 128k VBR, transcodes FLACs to 190k VBR with safe deletion, and updates folder suffixes to `- mp3`.
12. **AI_Music_Splitting_Curation**: Splits, curates, and converts full-length AI-generated music albums (.m4a, .mp3, .flac) or single tracks into individually tracked, tagged 128 kb/s MP3s with embedded YouTube square cover art and dedicated folder organization. Automates album title simplification, YouTube release discovery via yt-dlp, chapter/description tracklist extraction, smart 1:1 square artwork cropping, sample-accurate silence detection boundary refinement, and cleanup of source/intermediate files.

---

## How to Enable on Any PC / Mac (1-Click Setup)

### On Windows:
1. Ensure Google Drive is signed in and has finished syncing the `Antigravity` folder (typically `G:\My Drive\Antigravity\skills`).
2. Navigate to: `My Drive\Antigravity\skills`
3. Double-click **`install_skills_on_other_pc.bat`** (or run `install_skills_on_other_pc.ps1` in PowerShell).

### On Mac:
1. Ensure Google Drive is signed in and syncing.
2. Run in Terminal:
   ```bash
   bash "$HOME/Library/CloudStorage/GoogleDrive-elieadib@gmail.com/My Drive/Antigravity/skills/install_skills_on_mac.sh"
   ```

### Automatic Two-Way Sync
Any changes, enhancements, or new skills created on **any** of your computers are immediately saved directly to this Google Drive folder and will automatically sync across all your machines!
