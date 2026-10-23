#!/bin/bash
set -e

DEVICE_IP="192.168.1.225"
REMOTE_USER="ark"
REMOTE_TARGET="/roms/ports/snfetchplayer"
REMOTE_LAUNCHER="/roms/ports/SNfetchPLAYER.sh"

echo "=========================================================="
echo "🚀 Deploye SNfetchPLAYER (Handheld Restoration) auf dArkOS ($DEVICE_IP)..."
echo "=========================================================="

# 0. Laufende Hintergrund-Reste auf Handheld beenden
echo "🧹 Beende eventuell hängende Instanzen auf dem Handheld..."
ssh -o BatchMode=yes -o ConnectTimeout=5 $REMOTE_USER@$DEVICE_IP "killall -9 ffplay python3 2>/dev/null || true"

# 1. Zielordner erstellen
ssh -o BatchMode=yes -o ConnectTimeout=5 $REMOTE_USER@$DEVICE_IP "mkdir -p $REMOTE_TARGET $REMOTE_TARGET/thumbnails $REMOTE_TARGET/playlists $REMOTE_TARGET/assets $REMOTE_TARGET/assets/ui"

# 2. Python-Dateien, Scripte und Konfiguration synchronisieren
echo "📦 Kopiere Core-Dateien..."
scp -o BatchMode=yes -o ConnectTimeout=5 extractor.py osd_generator.py ui_dashboard.py sprueche.json playlist.json player.py snfetchplayer.gptk sn_logo.png screenshot.png cover.png gameinfo.xml port.json $REMOTE_USER@$DEVICE_IP:$REMOTE_TARGET/

# 3. Assets synchronisieren (inklusive UI-Cassette, Comics, Jingles)
echo "🎨 Synchronisiere Assets..."
rsync -avz --exclude='*.git*' assets/ $REMOTE_USER@$DEVICE_IP:$REMOTE_TARGET/assets/

# 4. Playlisten synchronisieren
echo "🎵 Synchronisiere Playlists..."
rsync -avz playlists/ $REMOTE_USER@$DEVICE_IP:$REMOTE_TARGET/playlists/

# 5. Launcher-Skript kopieren und Rechte setzen
echo "⚙️ Kopiere Launcher & setze Berechtigungen..."
scp -o BatchMode=yes -o ConnectTimeout=5 SNfetchPLAYER.sh $REMOTE_USER@$DEVICE_IP:$REMOTE_LAUNCHER
ssh -o BatchMode=yes -o ConnectTimeout=5 $REMOTE_USER@$DEVICE_IP "chmod +x $REMOTE_LAUNCHER $REMOTE_TARGET/*.py && rm -rf $REMOTE_TARGET/python_3.11.cache $REMOTE_TARGET/pylib 2>/dev/null || true"

echo "=========================================================="
echo "✅ Deployment erfolgreich abgeschlossen!"
echo "Starte SNfetchPLAYER jetzt am Handheld unter 'Ports'!"
echo "=========================================================="
