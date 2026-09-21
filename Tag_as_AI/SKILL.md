---
name: Tag_as_AI
description: >-
  Audits and standardizes audio metadata across music directories or individual tracks to tag
  them as AI-generated music. Sets ID3 (MP3), Vorbis (FLAC), and MP4 (M4A) Genre tags to AI
  genres (default: AI_Rock, or custom e.g. AI_Jazz, AI_Music), supports prefixing existing
  genres with "AI_", and allows adding optional AI grouping and comment markers while safely
  preserving cover art and all other metadata. Supports dry-run previews and recursive directory
  traversal. Use whenever the user asks to tag audio files as AI, set AI genre tags (e.g. AI_Rock),
  mark tracks as AI-generated, or categorize AI music collections.
---

# Tag as AI (`Tag_as_AI`)

Automated music tagging agent and utility that standardizes audio metadata across AI-generated music libraries (e.g., Suno, Udio, custom AI audio models). It sets or prefixes Genre tags, adds optional AI provenance/grouping markers, and strictly preserves existing album cover artwork and track metadata.

## Core Capabilities

1. **Targeted AI Genre Assignment**:
   - Standardizes the `Genre` tag across all tracks in a folder or library.
   - Defaults to **`AI_Rock`**, or accepts any custom AI genre (e.g., `AI_Pop`, `AI_Jazz`, `AI_Progressive Rock`, `AI_Electronic`, `AI_Music`).
2. **Prefix-Existing Mode (`--prefix-existing` / `-p`)**:
   - Reads existing genres and prepends `AI_` (e.g., `Rock` &rarr; `AI_Rock`, `Symphonic Prog` &rarr; `AI_Symphonic Prog`).
   - Automatically prevents duplicate prefixes (`AI_AI_Rock` &rarr; `AI_Rock`).
   - Falls back to the target genre if the file currently has no genre tag.
3. **Multi-Format Metadata Support**:
   - **MP3**: Standard ID3v2.3 `TCON` (Genre), `TIT1` (Grouping), `COMM` (Comment).
   - **FLAC**: Vorbis comments `GENRE`, `GROUPING`, `COMMENT`.
   - **M4A / AAC**: MP4 tags `©gen` (Genre), `©grp` (Grouping), `©cmt` (Comment).
4. **Non-Destructive & Safe**:
   - **Embedded Cover Art & Audio Streams**: Kept 100% intact.
   - **Track Metadata**: Preserves Artist, Album, Title, Year, Track Number, Disc Number.
5. **Dry-Run Preview (`--dry-run` / `-d`)**:
   - Previews all proposed tag modifications per directory without altering files on disk.

---

## Workflow Commands

The core script is located at [tag_as_ai.py](./scripts/tag_as_ai.py). A convenient batch launcher [tag-as-ai.bat](./tag-as-ai.bat) is also available.

### 1. Default AI Tagging (Sets Genre to `AI_Rock`):
```powershell
python "$HOME/.gemini/config/skills/Tag_as_AI/scripts/tag_as_ai.py" "<FOLDER_PATH>"
```

### 2. Custom AI Genre (e.g., `AI_Jazz`, `AI_Pop`, `AI_Music`):
```powershell
python "$HOME/.gemini/config/skills/Tag_as_AI/scripts/tag_as_ai.py" "<FOLDER_PATH>" --genre "AI_Jazz"
```

### 3. Prefix Existing Genre with `AI_` (e.g., `Rock` &rarr; `AI_Rock`):
```powershell
python "$HOME/.gemini/config/skills/Tag_as_AI/scripts/tag_as_ai.py" "<FOLDER_PATH>" --prefix-existing
```

### 4. Tag with AI Grouping and Provenance Notes:
```powershell
python "$HOME/.gemini/config/skills/Tag_as_AI/scripts/tag_as_ai.py" "<FOLDER_PATH>" --genre "AI_Rock" --grouping "AI Music" --comment "Generated via Suno AI"
```

### 5. Dry-Run Preview (Safe Verification):
```powershell
python "$HOME/.gemini/config/skills/Tag_as_AI/scripts/tag_as_ai.py" "<FOLDER_PATH>" --dry-run
```

*(You can also use the local batch launcher: `tag-as-ai.bat "<FOLDER_PATH>" --genre "AI_Rock"`)*

---

## CLI Options Reference

| Flag | Short | Default | Description |
| :--- | :--- | :--- | :--- |
| `path` | | *(Required)* | Target folder, music library root, or individual audio file. |
| `--genre` | `-g` | `AI_Rock` | Specific AI genre string to apply. |
| `--prefix-existing` | `-p` | `False` | Prefix existing genre tag with `AI_` instead of overwriting with default. |
| `--grouping` | | `None` | Optional Content Grouping tag (e.g. `AI Music`). |
| `--comment` | `-c` | `None` | Optional Comment tag specifying provenance or model notes. |
| `--dry-run` | `-d` | `False` | Simulate the process and display changes without writing to files. |
