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

# Auto-Registrierung in EmulationStation gamelist.xml (Screenshot, Beschreibung & Metadaten)
GAMELIST_XML="$(dirname "$GAMEDIR")/gamelist.xml"
if [ -f "$GAMELIST_XML" ] && [ -f "$GAMEDIR/gameinfo.xml" ]; then
  if ! grep -q "SNfetchPLAYER.sh" "$GAMELIST_XML"; then
    python3 -c "
import xml.etree.ElementTree as ET
try:
    g_tree = ET.parse('$GAMELIST_XML')
    g_root = g_tree.getroot()
    i_tree = ET.parse('$GAMEDIR/gameinfo.xml')
    for g in i_tree.getroot().findall('game'):
        g_root.append(g)
    g_tree.write('$GAMELIST_XML', encoding='utf-8', xml_declaration=True)
except Exception:
    pass
" 2>/dev/null || true
  fi
fi

# Logging aktivieren
> "$GAMEDIR/log.txt" && exec > >(tee "$GAMEDIR/log.txt") 2>&1

export HOME="$GAMEDIR"
export SDL_GAMECONTROLLERCONFIG="$sdl_controllerconfig"

# Gamepad-to-Keyboard Mapping starten
if [ -n "$GPTOKEYB" ]; then
  $GPTOKEYB "python3" -c "$GAMEDIR/snfetchplayer.gptk" &
fi

# Cursor ausblenden
printf "\033[?25l" > /dev/tty0 2>/dev/null || true

# SNfetchPLAYER Queue Player sofort starten (In-App Asset Sync im Splash Screen)
python3 "$GAMEDIR/player.py" "$@"

# Aufräumen & sauber zurück zu EmulationStation
if [ -n "$ESUDOKILL" ]; then
  $ESUDOKILL $(pidof gptokeyb) 2>/dev/null || true
fi
printf "\033[?25h" > /dev/tty0 2>/dev/null || true

if type pm_finish >/dev/null 2>&1; then
  pm_finish
fi
