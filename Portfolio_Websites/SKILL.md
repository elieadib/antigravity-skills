---
name: Portfolio_Websites
description: >-
  Audits, enhances, synchronizes, tests, and deploys Elie Adib's portfolio websites
  (Website_Code_Ruben and Website_Code_Elieadib) across local macOS development and Unraid server
  Docker environments. Enforces dual-repo parity, TypeScript verification, RFC 9110 media streaming,
  instant sorting/shuffling, audio playback persistence, and 1-click Unraid deployment workflows.
  Use whenever working on the Ruben or Elieadib website portfolios, deploying updates to Unraid,
  debugging video streaming/thumbnails, or adding portfolio features.
---

# Portfolio Websites Management & Unraid Deployment (`Portfolio_Websites`)

An end-to-end engineering, synchronization, and deployment skill for Elie Adib's portfolio websites:
- **Elieadib Portfolio**: `Website_Code_Elieadib` (`https://github.com/elieadib/Elieadib_website.git`)
- **Ruben Portfolio**: `Website_Code_Ruben` (`https://github.com/elieadib/ruben-media-portfolio.git`)

---

## 1. Golden Rules & Architectural Mandates

### 1.1 Strict Parity Mandate
Whenever applying bug fixes, layout improvements, performance optimizations, or new features to either `Website_Code_Ruben` or `Website_Code_Elieadib`, **always apply them to both repositories** identically (except for branding/name specifics).
Key synchronized areas:
- Video player controls, media lightbox, responsive viewport sizing.
- Media sorting (Date, Size, Alphabetical, Shuffle) & grid display.
- Video thumbnail generation, hover GIF previews, and scanning logic.
- Background audio player, mute controls, and route persistence.
- Docker configuration (`Dockerfile`, `docker-compose.yml`, log rotation).

### 1.2 TypeScript Verification Protocol
Before staging or committing any code in either repository, ALWAYS verify type safety using Node v26:
```bash
PATH="/Users/edib/.nvm/versions/node/v26.7.0/bin:$PATH" npx tsc --noEmit
```
Both projects must return **0 errors** before any git commit or push.

### 1.3 Google Drive Git FileProvider Hydration Guard
When working in local directories under Google Drive CloudStorage (`/Users/edib/Library/CloudStorage/...`):
- Avoid bare, unindexed `git status` or broad file searches across repo roots or `public/assets/`.
- Always stage specific files with path arguments (e.g. `git add app/ components/ lib/`).
- Commit with `--no-status` flag: `git commit --no-status -m "..."`.
- **If `fatal: mmap failed: Operation canceled` occurs**: Run `git fsck --verbose`. This forces macOS FileProvider to hydrate loose git objects into memory, resolving the error immediately.

---

## 2. Core Architectural Patterns

### 2.1 RFC 9110 HTTP Media Range Streaming
Both websites serve high-resolution photos and 4K video clips via `/api/media/[...path]/route.ts`. The streaming implementation must strictly adhere to RFC 9110:
1. **Range Types Supported**:
   - Standard range: `bytes=0-1048575` (start to end inclusive).
   - Open-ended range: `bytes=1048576-` (start to EOF).
   - Suffix byte range: `bytes=-500` (last $N$ bytes of file, crucial for MP4 `moov` atom parsing in browsers).
2. **Response Headers**:
   - `Accept-Ranges: bytes` on both `200 OK` and `206 Partial Content`.
   - `Content-Range: bytes <start>-<end>/<total>` on `206 Partial Content`.
   - Correct `Content-Length` matching chunk size.
3. **Graceful Client Aborts**:
   - Wrap chunk streaming in `try / catch` handling `AbortError` / client disconnects without throwing unhandled server exceptions.

### 2.2 O(1) Thumbnail Routing & Pre-generation
- Never walk or scan the filesystem synchronously inside image/video delivery handlers.
- Cache image thumbnails in `.thumbnails/` or dedicated cache directories with O(1) direct filename/hash mapping.
- Dedicated video thumbnail endpoint `/api/video-thumbnail?path=...` extracts high-quality poster frames via `ffmpeg` asynchronously with disk caching.

### 2.3 Hover GIF / Video Preview Lazy Mounting
- To prevent browser tab freezing from dozens of concurrent video/GIF decoders:
  - Do NOT mount active GIF/video players on all cards simultaneously.
  - Mount hover previews conditionally: `{isHovered && gifThumb ? <img src={gifThumb} /> : <img src={posterThumb} />}`.
  - Immediately unmount and release resources on `onMouseLeave`.

### 2.4 Navigation & Back-Button History Sync
- URL query parameters must reflect active modal state (`?album=<id>&media=<id>`).
- Listen to `popstate` events:
  - When a user clicks a photo/video modal, push or replace URL state.
  - When the user presses the browser "Back" button, close the modal cleanly instead of navigating away from the entire website.

### 2.5 Media Sorting & Shuffle Controls
- In album galleries, provide a "Sort" dropdown beside the "Shuffle" button:
  - **Date**: Sorts by EXIF / file modification timestamp (Newest First / Oldest First).
  - **Size**: Sorts by file byte size (Largest First).
  - **Alphabetical**: Sorts by filename (A-Z).
  - **Shuffle**: Standard Fisher-Yates randomization.

### 2.6 Audio Persistence Across Navigation
- Audio player state (`isPlaying`, `volume`, `isMuted`) persists in browser `localStorage`.
- Automatically pause audio on administrative or `/login` routes, and restore playback state upon returning to media views.

---

## 3. Unraid Server Deployment Workflows

On the Unraid server (`ELIESERVER`), websites run as Docker containers under `/mnt/user/appdata/`.

### Directory Structure on Unraid:
- Elieadib Website: `/mnt/user/appdata/website_elieadib`
- Ruben Website: `/mnt/user/appdata/website_ruben`

---

### Workflow A: Single Chained Terminal Command (All-in-One)
To update in one paste without entering commands line by line:

#### For Elieadib Website:
```bash
cd /mnt/user/appdata/website_elieadib && git config --global --add safe.directory /mnt/user/appdata/website_elieadib && git remote remove origin 2>/dev/null || true && git remote add origin https://<GITHUB_TOKEN>@github.com/elieadib/Elieadib_website.git && git fetch origin main && git reset --hard origin/main && docker compose down && docker compose up -d --build
```

#### For Ruben Website:
```bash
cd /mnt/user/appdata/website_ruben && git config --global --add safe.directory /mnt/user/appdata/website_ruben && git remote remove origin 2>/dev/null || true && git remote add origin https://<GITHUB_TOKEN>@github.com/elieadib/ruben-media-portfolio.git && git fetch origin main && git reset --hard origin/main && docker compose down && docker compose up -d --build
```

---

### Workflow B: Standalone Shell Script (`update.sh`)
Each repository contains an `update.sh` script. On Unraid, update by running a single command:

```bash
bash /mnt/user/appdata/website_elieadib/update.sh
```
or
```bash
bash /mnt/user/appdata/website_ruben/update.sh
```

---

### Workflow C: Unraid "User Scripts" Plugin (1-Click WebGUI)
For the fastest update without opening the Unraid terminal:
1. Open Unraid WebGUI -> **Plugins** -> Install **User Scripts** (from Community Applications).
2. Go to **Settings** -> **User Scripts** -> Click **Add New Script**.
3. Name it: `Update Elieadib Website` (or `Update Ruben Website`).
4. Paste the update script into the editor:
   ```bash
   #!/bin/bash
   set -e
   echo "=== Updating Elieadib Website ==="
   cd /mnt/user/appdata/website_elieadib
   git config --global --add safe.directory /mnt/user/appdata/website_elieadib
   git remote remove origin 2>/dev/null || true
   git remote add origin https://<GITHUB_TOKEN>@github.com/elieadib/Elieadib_website.git
   git fetch origin main
   git reset --hard origin/main
   docker compose down
   docker compose up -d --build
   echo "=== Update Completed Successfully! ==="
   ```
5. Click **Save Changes**.
6. Whenever you want to update the site, simply click **Run Script** in the Unraid GUI!

---

## 4. Docker & Unraid Disk Utilization Protection

To prevent Unraid `docker.img` exhaustion (e.g. "Docker image disk utilization of 74%"):
1. **Container Log Rotation**:
   Ensure `docker-compose.yml` specifies log limits:
   ```yaml
   services:
     web:
       # ...
       logging:
         driver: "json-file"
         options:
           max-size: "10m"
           max-file: "3"
   ```
2. **Periodic Image & Builder Cache Pruning**:
   Run on Unraid terminal or via a scheduled monthly User Script:
   ```bash
   docker system prune -f --volumes
   docker builder prune -f
   ```
