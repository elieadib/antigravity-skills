---
name: Music_Curator
description: >-
  Audits, downloads, and embeds missing album cover art into MP3, FLAC, and M4A tags
  using local cover.jpg or online music databases (iTunes, Deezer, CoverArtArchive),
  and intelligently classifies and updates genre tags into 7 standardized categories
  (Hard Rock, Rock, Female, Progressive Rock, Christmas, Jazz, Latina) or a user-specified genre.
  Use whenever the user asks to check, fix, or add album covers/art, or update/set genre tags on any music folder.
---

# Music Curator

Automated music curation agent that audits music libraries, embeds high-resolution cover art into audio tags, and standardizes genre metadata.

## Core Rules

### 1. Album Cover Art Verification & Embedding
* **Existing Tag Cover Art:** **Do nothing (preserve it intact)**.
* **Missing Cover Art:**
  * **Step A:** Check if a local cover.jpg (or Cover.jpg, cover.png) exists in the folder and embed it into the audio files.
  * **Step B:** If cover.jpg does not exist:
    1. Check sibling tracks in the same folder to reuse existing embedded art.
    2. Extract Band and Album name (from tags or folder name) and search online databases (**iTunes Search API**, **Deezer API**, **Cover Art Archive**).
    3. Download high-resolution art (1000×1000), save it as cover.jpg in the album folder, and embed it into all audio file tags.

### 2. Intelligent Genre Classification (7 Categories)
When running auto-genre detection (--auto-genre or --genre auto), audio files are classified into:

1. **Christmas**: Christmas and holiday albums (matched via holiday keywords in album/folder name).
2. **Latina**: Spanish / Latino rhythm, Flamenco, Salsa, Bossa Nova, Latin Pop/Rock (e.g., ROSALÍA, Paco de Lucía, Buena Vista Social Club).
   * *Custom Rule:* **Santana** is kept in **Rock**.
3. **Jazz**: Jazz, Bebop, Jazz Fusion, Vocal Jazz, Smooth Jazz (e.g., Miles Davis, Chet Baker, Coltrane, Sinatra, Al Di Meola).
4. **Female**: Solo female vocalists across pop, rock, folk, blues, and country (e.g., Norah Jones, Eva Cassidy, Ann Wilson, Carole King, Tori Amos, Adele).
   * *Custom Rule:* **Florence + the Machine** is classified under **Rock**.
5. **Progressive Rock**: Progressive Rock, Symphonic Prog, Space Rock, Neo-Prog (e.g., Pink Floyd, Yes, Genesis, Rush, Marillion, Big Big Train, Riverside).
6. **Hard Rock**: Metal, Heavy Metal, Death Metal, Black Metal, Thrash, Power Metal, Doom, Metalcore, Blues Rock, Hard Rock (e.g., Black Sabbath, Iron Maiden, Metallica, Aerosmith, Alice Cooper, Moonspell).
7. **Rock**: Default category for Rock, Alternative Rock, Classic Rock, Country, Indie Rock, Folk Rock, Pop Rock, Grunge, plus Santana, Florence + the Machine.

---

## Workflow Commands

The skill script is located at [music_curator.py](./scripts/music_curator.py).

### 1. Full Curation (Covers + Intelligent Auto-Genre):
```powershell
python "$HOME/.gemini/config/skills/Music_Curator/scripts/music_curator.py" "<FOLDER_PATH>" --auto-genre
```

### 2. Cover Art Only (Leave Genres As-Is):
```powershell
python "$HOME/.gemini/config/skills/Music_Curator/scripts/music_curator.py" "<FOLDER_PATH>"
```

### 3. Auto-Genre Only (Do Not Touch Cover Art):
```powershell
python "$HOME/.gemini/config/skills/Music_Curator/scripts/music_curator.py" "<FOLDER_PATH>" --no-covers --auto-genre
```

### 4. Custom Fixed Genre (e.g., Hard Rock):
```powershell
python "$HOME/.gemini/config/skills/Music_Curator/scripts/music_curator.py" "<FOLDER_PATH>" --genre "Hard Rock"
```

### 5. Dry-Run Preview (Test without modifying files):
```powershell
python "$HOME/.gemini/config/skills/Music_Curator/scripts/music_curator.py" "<FOLDER_PATH>" --auto-genre --dry-run
```

*(You can also use the local batch launcher: `music-curator.bat "<FOLDER_PATH>" --auto-genre`)*
