#!/bin/bash
# PORTMASTER: SNfetchPLAYER.sh

XDG_DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}

if [ -d "/opt/system/Tools/PortMaster/" ]; then
  controlfolder="/opt/system/Tools/PortMaster"
elif [ -d "/opt/tools/PortMaster/" ]; then
  controlfolder="/opt/tools/PortMaster"
elif [ -d "$XDG_DATA_HOME/PortMaster/" ]; then
  controlfolder="$XDG_DATA_HOME/PortMaster"
else
  controlfolder="/roms/ports/PortMaster"
fi

[ -f "$controlfolder/control.txt" ] && source "$controlfolder/control.txt"
[ -f "${controlfolder}/mod_${CFW_NAME}.txt" ] && source "${controlfolder}/mod_${CFW_NAME}.txt"
get_controls 2>/dev/null || true

GAMEDIR="/$directory/ports/snfetchplayer"
[ ! -d "$GAMEDIR" ] && GAMEDIR="/roms/ports/snfetchplayer"

cd "$GAMEDIR"

# Logging aktivieren
> "$GAMEDIR/log.txt" && exec > >(tee "$GAMEDIR/log.txt") 2>&1

export HOME="$GAMEDIR"
export SDL_GAMECONTROLLERCONFIG="$sdl_controllerconfig"

# Gamepad-to-Keyboard Mapping starten
if [ -n "$GPTOKEYB" ]; then
  $GPTOKEYB "python3" -c "$GAMEDIR/snfetchplayer.gptk" &
fi

# -------------------------------------------------------------------
# FIRST-LAUNCH ASSET CHECK: Downloads media pack from GitHub if missing
# -------------------------------------------------------------------
ASSET_URL="https://github.com/StationNorthMedia/SNfetchPLAYER-PortMaster/releases/download/v4.0.0/snfetchplayer-assets.zip"

if [ ! -d "$GAMEDIR/assets/tv_ids" ] || [ ! -f "$GAMEDIR/assets/catalog_manifest.json" ]; then
  echo "=========================================================="
  echo "🚀 STATION NORTH: Initial Asset Setup"
  echo "Downloading 480p Video IDs, Jingles & Comic Lore..."
  echo "=========================================================="

  if [ -e "/dev/tty0" ]; then
    printf "\033c" > /dev/tty0
    echo "" > /dev/tty0
    echo " ==========================================================" > /dev/tty0
    echo "   STATION NORTH SNfetchPLAYER (PortMaster Edition)" > /dev/tty0
    echo " ==========================================================" > /dev/tty0
    echo "  [INITIAL SETUP] Downloading media assets from GitHub..." > /dev/tty0
    echo "  - 42 TV Station IDs (480p Handheld Edition)" > /dev/tty0
    echo "  - 174 Station Jingles & Soundtracks" > /dev/tty0
    echo "  - The Chronicles (Audio & Comic Lore)" > /dev/tty0
    echo " ----------------------------------------------------------" > /dev/tty0
    echo "  Please wait (Requires active Wi-Fi connection)..." > /dev/tty0
    echo " ==========================================================" > /dev/tty0
  fi

  mkdir -p "$GAMEDIR/assets"
  if curl -# -L "$ASSET_URL" -o "$GAMEDIR/assets.zip"; then
    echo "Extracting assets..."
    unzip -o -q "$GAMEDIR/assets.zip" -d "$GAMEDIR/"
    rm -f "$GAMEDIR/assets.zip"
    echo "✅ Assets successfully installed!"
  else
    echo "⚠️ Download failed. Please check Wi-Fi connection!"
  fi
fi

# Cursor ausblenden
printf "\033[?25l" > /dev/tty0 2>/dev/null || true

# SNfetchPLAYER Queue Player starten
python3 "$GAMEDIR/player.py" "$@"

# Aufräumen & sauber zurück zu EmulationStation
if [ -n "$ESUDOKILL" ]; then
  $ESUDOKILL $(pidof gptokeyb) 2>/dev/null || true
fi
printf "\033[?25h" > /dev/tty0 2>/dev/null || true

if type pm_finish >/dev/null 2>&1; then
  pm_finish
fi
