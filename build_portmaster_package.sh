#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$SCRIPT_DIR/dist"
STAGING_DIR="$DIST_DIR/staging"
PKG_DIR="$STAGING_DIR/snfetchplayer"

echo "=========================================================="
echo "📦 Baue PortMaster Release-Paket für Station North SNfetchPLAYER..."
echo "=========================================================="

# 1. Altes Verzeichnis leeren
rm -rf "$STAGING_DIR" "$DIST_DIR/snfetchplayer.zip"
mkdir -p "$PKG_DIR" "$PKG_DIR/playlists" "$PKG_DIR/thumbnails"

# 2. PortMaster Root-Dateien
cp "$SCRIPT_DIR/SNfetchPLAYER.sh" "$STAGING_DIR/"
chmod +x "$STAGING_DIR/SNfetchPLAYER.sh"

# 3. Anwendungsdateien kopieren
cp "$SCRIPT_DIR/player.py" "$PKG_DIR/"
cp "$SCRIPT_DIR/ui_dashboard.py" "$PKG_DIR/"
cp "$SCRIPT_DIR/extractor.py" "$PKG_DIR/"
cp "$SCRIPT_DIR/osd_generator.py" "$PKG_DIR/"
cp "$SCRIPT_DIR/snfetchplayer.gptk" "$PKG_DIR/"
cp "$SCRIPT_DIR/sn_logo.png" "$PKG_DIR/"
cp "$SCRIPT_DIR/sprueche.json" "$PKG_DIR/"
cp "$SCRIPT_DIR/playlist.json" "$PKG_DIR/"
cp "$SCRIPT_DIR/port.json" "$PKG_DIR/"
chmod +x "$PKG_DIR"/*.py

# 4. Playlists kopieren
cp -r "$SCRIPT_DIR/playlists/"* "$PKG_DIR/playlists/"

# 5. ZIP-Paket erzeugen (Nutzt Pythons standardmäßiges zipfile-Modul)
mkdir -p "$DIST_DIR"
cd "$STAGING_DIR"
python3 -c "
import zipfile, os
with zipfile.ZipFile('$DIST_DIR/snfetchplayer.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk('.'):
        for f in files:
            if not f.endswith('.pyc') and '__pycache__' not in root:
                filepath = os.path.join(root, f)
                arcname = os.path.relpath(filepath, '.')
                z.write(filepath, arcname)
"

echo "=========================================================="
echo "✅ Fertig! Release-ZIP erstellt unter:"
echo "   $DIST_DIR/snfetchplayer.zip"
echo "Dieses ZIP kann direkt auf die SD-Karte unter /roms/ports/"
echo "entpackt werden oder als GitHub Release hochgeladen werden!"
echo "=========================================================="
