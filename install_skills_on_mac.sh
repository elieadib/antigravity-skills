#!/bin/bash
set -e

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.gemini/config"
TARGET_DIR="$CONFIG_DIR/skills"

echo "=============================================================================="
echo "       Google Antigravity - Global Skills Sync Setup for Mac"
echo "=============================================================================="
echo ""
echo "[1/4] Skills Source (Google Drive): $SOURCE_DIR"
echo "      Antigravity Target:       $TARGET_DIR"
echo ""

mkdir -p "$CONFIG_DIR"

if [ -L "$TARGET_DIR" ]; then
    echo "[2/4] Refreshing existing symlink..."
    rm "$TARGET_DIR"
elif [ -d "$TARGET_DIR" ]; then
    BACKUP_DIR="$CONFIG_DIR/skills_backup_$(date +%Y%m%d_%H%M%S)"
    echo "[2/4] Backing up existing local skills to: $BACKUP_DIR"
    mv "$TARGET_DIR" "$BACKUP_DIR"
fi

echo "[3/4] Creating symlink to Google Drive skills..."
ln -s "$SOURCE_DIR" "$TARGET_DIR"

cat << JSON_EOF > "$CONFIG_DIR/skills.json"
{
  "entries": [
    {
      "path": "$SOURCE_DIR"
    }
  ]
}
JSON_EOF

echo "[4/4] Checking dependencies..."
if command -v python3 &>/dev/null; then
    echo "      Python found: $(which python3)"
    python3 -c "import PIL" 2>/dev/null || pip3 install Pillow
else
    echo "      Warning: python3 not found."
fi

if command -v ffmpeg &>/dev/null; then
    echo "      FFmpeg found: $(which ffmpeg)"
else
    echo "      Warning: ffmpeg not found in PATH."
fi

echo ""
echo "=============================================================================="
echo " [SUCCESS] Global Skills are now active on this Mac!"
echo "=============================================================================="
