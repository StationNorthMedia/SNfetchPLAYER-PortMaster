# Station North SNfetchPLAYER • PortMaster / dArkOS Edition

<p align="center">
  <img src="sn_logo.png" alt="Station North Logo" width="300" />
</p>

<p align="center">
  <b>Official Retro-Handheld Cyber-Deck & Media Player for dArkOS, ArkOS, AmberELEC, ROCKNIX & PortMaster</b><br>
  <i>Tailored for Rockchip RK3326, RK3566 & Allwinner H700 Handheld Consoles</i>
</p>

---

## 🌟 The 4 Pillars of Station North

Station North SNfetchPLAYER transforms your retro gaming handheld into an authentic, standalone media terminal:

1. 📻 **Radio Mode (Cyber-Deck)**
   - High-fidelity live audio streaming via YouTube and local files.
   - Real-time 32-band spectrum visualizer with dynamic AGC (Automatic Gain Control) and acoustic pink-noise frequency tilt compensation.
   - **Vollbild Zen Mode**: Immersive full-screen visualizer with an auto-hiding 5-button cockpit menu (fades out after 4 seconds of inactivity).

2. 📺 **Television Broadcast (Station North TV)**
   - Continuous music video television broadcasts scaled seamlessly to handheld 4:3 displays.
   - **ASS Subtitle Bauchbinde**: Broadcast-grade lower-third banners powered by `libass` fading in at 0.2s and fading out at 4.8s.
   - **Station IDs & Watermark**: Automatic commercial-style interstitials with a persistent 65% opacity watermark logo.
   - **Dedicated 4-Key Cockpit**: Minimalist, distraction-free control (Play/Pause, Exit, Skip, Repeat One).

3. 📖 **The Chronicles (Lore & Audio Comics)**
   - Interactive comic viewer featuring original Station North artwork and voiceover lore narration.
   - Auto-advancing narration playback with easy page turning via D-Pad.

4. ⚙️ **Settings & Curator Integration**
   - Live playlist switching across curated catalogs (Main Top 100, US HipHop Top 50, US R&B Top 50).
   - Adjustable station jingle rotation intervals (every 1 to 10 tracks, or off).
   - **Station North Curator Support**: Build and curate your own playlists on the Station North Android App, export them as JSON, and drop them into `/playlists/` on your SD card.
   - **Interactive Handbook**: 2-column settings with a scrollable in-game user manual.

---

## 🎮 Controller Layout & Keybindings

Configured natively via `snfetchplayer.gptk` for standard handheld face buttons:

| Button | Primary Action | TV Vollbild | Radio Vollbild | Settings |
|---|---|---|---|---|
| **`[A]`** | Bestätigen / Start | – | Button aktivieren | Ins Handbuch springen |
| **`[B]`** | Zurück / Hauptmenü | **Sofort beenden (0ms)** | Vollbild beenden | Zurück / Menü schließen |
| **`[◄]` / `[►]`** | Navigation / Slider | Vorheriger / Nächster Clip | Vorheriger / Nächster Song | Wert ändern / Spalte wechseln |
| **`[▲]` / `[▼]`** | Navigation | – | – | Zeile wählen / Handbuch scrollen |
| **`[START]`** | Play / Pause | **Video einfrieren / Play** | Play / Pause | – |
| **`[SELECT]`** | **Settings & Handbuch** | – | – | Menü schließen |
| **`[X]`** | Vollbild / Zen Mode | **Repeat One Loop** | OSD aufwecken | Ins Handbuch springen |
| **`[Y]`** | Shuffle / Repeat | **Repeat One Loop** | Shuffle an/aus | – |
| **`[SELECT] + [START]`** | **PortMaster Kill** | Beendet die App sofort | Beendet die App sofort | Beendet die App sofort |

---

## 📦 Installation for PortMaster

### Manual Installation (ZIP)
1. Download `snfetchplayer.zip` from the latest [GitHub Release](https://github.com/StationNorthMedia/SNfetchPLAYER-PortMaster/releases).
2. Extract the archive directly onto your handheld's SD card into the `ports/` directory:
   ```text
   roms/ports/
   ├── SNfetchPLAYER.sh
   └── snfetchplayer/
   ```
3. Refresh your EmulationStation games list.
4. Launch **Station North SNfetchPLAYER** from the **Ports** category!

*Note: Requires an active Wi-Fi connection for live YouTube streams.*

---

## 📁 Custom Playlists & Media
Place your own MP3, FLAC, MP4 or MKV files, or JSON playlists directly into:
```text
/roms/ports/snfetchplayer/playlists/
```
The app will automatically discover and index them via **Settings -> Re-Scan Local Asset Storage**.

---

## 🛠️ Technical Architecture

- **Rendering**: Pygame 2.x on exclusive DirectFB / KMSDRM (`/dev/dri/card0`) with hardware V-Sync.
- **Video Engine**: Low-latency `ffplay` pipeline with custom video filters (`scale`, `crop`, `ass`, `colorchannelmixer`).
- **Audio Extraction**: Dynamic headless resolver via `yt-dlp` and `extractor.py`.
- **Packaging**: Standardized PortMaster specification (`port.json`, `SNfetchPLAYER.sh`, `snfetchplayer.gptk`).

---

## 📄 License & Credits

- **Software**: MIT License © Station North Media
- **Media, Audio Jingles & Artwork**: © Station North Media. All rights reserved.
