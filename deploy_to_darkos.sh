#!/bin/bash
set -e

DEVICE_IP="192.168.1.225"
REMOTE_USER="ark"
REMOTE_TARGET="/roms/ports/snfetchplayer"
REMOTE_LAUNCHER="/roms/ports/SNfetchPLAYER.sh"

echo "=========================================================="
echo "🚀 Deploye SNfetchPLAYER v4.0 (Die 4-Säulen-Edition) auf dArkOS ($DEVICE_IP)..."
echo "=========================================================="

# 1. Zielordner erstellen
ssh $REMOTE_USER@$DEVICE_IP "mkdir -p $REMOTE_TARGET $REMOTE_TARGET/thumbnails $REMOTE_TARGET/playlists"

# 2. Python-Dateien, Scripte und Konfiguration synchronisieren
scp extractor.py osd_generator.py ui_dashboard.py sprueche.json playlist.json player.py snfetchplayer.gptk sn_logo.png $REMOTE_USER@$DEVICE_IP:$REMOTE_TARGET/

# 3. Playlisten synchronisieren
scp -r playlists/* $REMOTE_USER@$DEVICE_IP:$REMOTE_TARGET/playlists/

# 4. Launcher-Skript kopieren und Rechte setzen
scp SNfetchPLAYER.sh $REMOTE_USER@$DEVICE_IP:$REMOTE_LAUNCHER
ssh $REMOTE_USER@$DEVICE_IP "chmod +x $REMOTE_LAUNCHER $REMOTE_TARGET/*.py"

echo "=========================================================="
echo "✅ Deployment von SNfetchPLAYER v4.0 erfolgreich!"
echo "Du kannst die App direkt am Handheld unter 'Ports' starten."
echo "=========================================================="
