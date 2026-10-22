#!/usr/bin/env python3
"""
Station North SNfetchPLAYER - dArkOS Handheld Edition v5.0 (Nord Master Edition)
Authentic 4-Pillar Multimedia & Broadcast Engine:
1. Splash Screen: Mode portal with live asset statistics and instant loading feedback.
2. Radio Mode: High-Fidelity Studio Dashboard with 340x340 Album Art, Live 32-Band FFT Visualizer,
   5-Button Pastel Cockpit, Up-Next Broadcast Preview, and Queen's Directive Lore.
3. TV Mode: 4:3 Display Fill for retro YouTube videos, 65% logo watermark, uninterrupted playback,
   and floating 5-button OSD appearing only on manual user interactions.
4. The Chronicles: Audiovisual Comic & Voice Narration (Comic panel on left, Narrative + Audio on right).
5. Settings & Extraction Engine: Playlist selection, ALSA / Backlight sliders, and system diagnostics.

Unified Controls (Front Buttons Only):
- [A] / [Start] = Confirm / Play / Pause
- [B]           = Back / Exit to Main Menu
- [X]           = Fullscreen TV Toggle (Mint nord7)
- [Y]           = Repeat / Loop Current Song Toggle (Gold nord13)
- [◄/►]         = Previous / Next Song Skip (Peach nord12 / Lavender nord15)
- [▲/▼]         = Navigation
- [Select]      = Settings Menu
"""

import sys
import os
import json
import time
import math
import random
import threading
import subprocess
import signal
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Audio output for ffplay / ALSA
os.environ["SDL_AUDIODRIVER"] = "alsa"
import pygame

pygame.display.init()
pygame.font.init()

from extractor import get_stream
from osd_generator import generate_osd_ass

# =============================================================================
# ARCTIC ICE & NORD DESIGN SYSTEM (OFFICIAL SPECIFICATION)
# =============================================================================
# Polar Night (Dark Base Surfaces)
NORD0 = (46, 52, 64)       # #2e3440 - Base App Background
NORD1 = (59, 66, 82)       # #3b4252 - Elevated Cards, Panels & Modals
NORD2 = (67, 76, 94)       # #434c5e - Card Borders, Outlines & Subtle Dividers
NORD3 = (76, 86, 106)      # #4c566a - Inconspicuous Elements & Guides

# Snow Storm (Text & Typography)
NORD4 = (216, 222, 233)    # #d8dee9 - Body Text & Secondary Labels
NORD5 = (229, 233, 240)    # #e5e9f0 - Elevated Body Text
NORD6 = (236, 239, 244)    # #eceff4 - Prominent Headlines, Titles & Snow White

# Frost (Arctic Water Accents)
NORD7 = (143, 188, 187)    # #8fbcbb - Frozen Polar Water / Mint (Button 1: Fullscreen [X])
NORD8 = (136, 192, 208)    # #88c0d0 - Station North Clear Ice Cyan (Primary Accent)
NORD9 = (129, 161, 193)    # #81a1c1 - Arctic Waters Blue (Button 3: Play/Pause [Start])
NORD10 = (94, 129, 172)    # #5e81ac - Deep Arctic Ocean Blue

# Aurora (Highlights & Status)
NORD11 = (191, 97, 106)    # #bf616a - Error / Offline / Low Battery Red
NORD12 = (208, 135, 112)   # #d08770 - Aurora Peach / Terracotta (Button 2: Prev Track [◄])
NORD13 = (235, 203, 139)   # #ebcb8b - Aurora Gold / Amber (Button 5: Repeat Track Toggle [Y])
NORD14 = (163, 190, 140)   # #a3be8c - Aurora Green / Live On Air / Battery Good
NORD15 = (180, 142, 173)   # #b48ead - Aurora Lavender / Purple (Button 4: Next Track [►])

# Aliases for compatibility
COLOR_BG            = NORD0
COLOR_BAR_BG        = (36, 41, 51)
COLOR_CARD_BG       = NORD0
COLOR_CARD_SURFACE  = NORD1
COLOR_CARD_BORDER   = NORD2
COLOR_SELECTION     = NORD1
COLOR_TEXT_SNOW     = NORD6
COLOR_TEXT_FROST    = NORD9
COLOR_TEXT_MUTED    = NORD4
COLOR_ACCENT_CYAN   = NORD8
COLOR_ACCENT_TEAL   = NORD7
COLOR_ACCENT_GOLD   = NORD13
COLOR_ACCENT_GREEN  = NORD14
COLOR_ACCENT_RED    = NORD11

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768

# Core States
STATE_SPLASH       = 0
STATE_RADIO        = 1
STATE_TV           = 2
STATE_CHRONICLES   = 3
STATE_SETTINGS     = 4

# =============================================================================
# PERSISTENT SHUFFLE & QUEUE MANAGER (TRUE RANDOMIZATION & REPEAT LOOP)
# =============================================================================
class ShuffleQueueManager:
    """Manages non-repeating shuffle queues across sessions and handles single-track repeat"""
    def __init__(self, state_file: str = "shuffle_state.json"):
        base_dir = Path("/roms/ports/snfetchplayer") if Path("/roms/ports/snfetchplayer").exists() else Path(".")
        self.state_file = base_dir / state_file
        self.is_repeat_mode: bool = False
        self.shuffle_queue: List[int] = []
        self.history: List[int] = []
        self.total_playlist_len: int = 0
        self.current_playlist_id: str = "default"

    def init_playlist(self, playlist_len: int, playlist_id: str = "default"):
        self.total_playlist_len = playlist_len
        self.current_playlist_id = playlist_id
        saved = self._load_state()

        if saved and saved.get("playlist_id") == playlist_id and saved.get("queue"):
            self.shuffle_queue = [x for x in saved["queue"] if x < playlist_len]
            self.history = [x for x in saved.get("history", []) if x < playlist_len]
            self.is_repeat_mode = saved.get("repeat", False)
            if not self.shuffle_queue:
                self.reshuffle()
        else:
            self.reshuffle()

    def reshuffle(self):
        if self.total_playlist_len <= 0:
            self.shuffle_queue = [0]
            return
        deck = list(range(self.total_playlist_len))
        random.shuffle(deck)
        self.shuffle_queue = deck
        self.history = []
        self._save_state()

    def get_current_idx(self) -> int:
        if not self.shuffle_queue:
            self.reshuffle()
        return self.shuffle_queue[0] if self.shuffle_queue else 0

    def get_up_next_idx(self) -> Optional[int]:
        if self.is_repeat_mode:
            return self.get_current_idx()
        if len(self.shuffle_queue) > 1:
            return self.shuffle_queue[1]
        return None

    def advance_next(self) -> int:
        """Advances to next random track in queue, or stays on current track if repeat is on"""
        if self.is_repeat_mode:
            return self.get_current_idx()
        if self.shuffle_queue:
            played = self.shuffle_queue.pop(0)
            self.history.append(played)
        if not self.shuffle_queue:
            self.reshuffle()
        self._save_state()
        return self.get_current_idx()

    def step_prev(self) -> int:
        """Returns to previously played track from history"""
        if self.history:
            prev = self.history.pop()
            self.shuffle_queue.insert(0, prev)
            self._save_state()
            return prev
        return self.get_current_idx()

    def toggle_repeat(self) -> bool:
        self.is_repeat_mode = not self.is_repeat_mode
        self._save_state()
        return self.is_repeat_mode

    def _save_state(self):
        try:
            data = {
                "playlist_id": self.current_playlist_id,
                "queue": self.shuffle_queue,
                "history": self.history[-50:],
                "repeat": self.is_repeat_mode
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    def _load_state(self) -> Optional[Dict]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

# =============================================================================
# SYSTEM TELEMETRY & HARDWARE MANAGER
# =============================================================================
class HardwareManager:
    @staticmethod
    def get_battery_info() -> Tuple[int, bool]:
        cap_file = Path("/sys/class/power_supply/battery/capacity")
        stat_file = Path("/sys/class/power_supply/battery/status")
        capacity = 85
        is_charging = False
        if cap_file.exists():
            try:
                capacity = int(cap_file.read_text().strip())
            except Exception:
                pass
        if stat_file.exists():
            try:
                is_charging = "charging" in stat_file.read_text().strip().lower()
            except Exception:
                pass
        return capacity, is_charging

    @staticmethod
    def get_wifi_status() -> bool:
        wlan_file = Path("/sys/class/net/wlan0/operstate")
        if wlan_file.exists():
            try:
                return "up" in wlan_file.read_text().strip().lower()
            except Exception:
                pass
        return True

    @staticmethod
    def get_time_str() -> str:
        return time.strftime("%H:%M")

    @staticmethod
    def get_master_volume() -> int:
        try:
            res = subprocess.run(["amixer", "sget", "Playback"], capture_output=True, text=True, timeout=1)
            for line in res.stdout.splitlines():
                if "[" in line and "%]" in line:
                    part = line.split("[")[1].split("%]")[0]
                    return int(part)
        except Exception:
            pass
        return 80

    @staticmethod
    def set_master_volume(pct: int):
        pct = max(0, min(100, pct))
        try:
            subprocess.run(["amixer", "sset", "Playback", f"{pct}%"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    @staticmethod
    def get_brightness() -> int:
        b_file = Path("/sys/class/backlight/backlight/brightness")
        m_file = Path("/sys/class/backlight/backlight/max_brightness")
        if b_file.exists() and m_file.exists():
            try:
                curr = int(b_file.read_text().strip())
                max_b = int(m_file.read_text().strip())
                return int((curr / max_b) * 100)
            except Exception:
                pass
        return 75

    @staticmethod
    def set_brightness(pct: int):
        pct = max(10, min(100, pct))
        b_file = Path("/sys/class/backlight/backlight/brightness")
        m_file = Path("/sys/class/backlight/backlight/max_brightness")
        if b_file.exists() and m_file.exists():
            try:
                max_b = int(m_file.read_text().strip())
                val = int((pct / 100.0) * max_b)
                b_file.write_text(str(val))
            except Exception:
                pass

# =============================================================================
# INTEGRATED 32-BAND FFT VISUALIZER
# =============================================================================
try:
    import numpy as np
except ImportError:
    np = None

class IntegratedVisualizer:
    def __init__(self, num_bars: int = 40):
        self.num_bars = num_bars
        self.heights = [14.0] * num_bars
        self.target_heights = [14.0] * num_bars
        self.last_update = time.time()
        self.has_real_audio = False
        self.last_audio_feed = 0.0
        self.peak_energy = 15000.0  # Adaptiver Dynamik-Baseline-Wert (AGC)

    def feed_pcm(self, pcm_bytes: bytes):
        """Processes raw 16-bit PCM mono 22050Hz chunk and computes balanced 40-band FFT"""
        if not np or len(pcm_bytes) < 256:
            return

        try:
            samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
            n = len(samples)
            window = np.hanning(n)
            fft_vals = np.abs(np.fft.rfft(samples * window))
            num_bins = len(fft_vals)
            if num_bins < self.num_bars:
                return

            indices = np.logspace(0, np.log10(num_bins - 1), self.num_bars + 1).astype(int)
            raw_bands = []
            for i in range(self.num_bars):
                start = indices[i]
                end = max(start + 1, indices[i+1])
                # Frequenz-Kompensation (Musik hat natuerlich viel mehr Bass als Hoehen)
                tilt = 1.0 + (i / float(self.num_bars)) * 3.5
                raw_val = float(np.mean(fft_vals[start:end])) * tilt
                raw_bands.append(raw_val)

            # Adaptives AGC (Automatic Gain Control) - verhindert dauerhaftes Anschlagen
            max_in_frame = max(raw_bands) if raw_bands else 1.0
            if max_in_frame > self.peak_energy:
                self.peak_energy = self.peak_energy * 0.75 + max_in_frame * 0.25
            else:
                self.peak_energy = max(2000.0, self.peak_energy * 0.965 + max_in_frame * 0.035)

            # Dynamische Skalierung mit Power-Kurve (gamma=0.6) fuer lebendige Bewegung
            bands = []
            for raw_val in raw_bands:
                ratio = min(1.0, max(0.0, raw_val / max(1.0, self.peak_energy)))
                curve = ratio ** 0.6
                h = 14.0 + 185.0 * curve
                bands.append(h)

            self.target_heights = bands
            self.has_real_audio = True
            self.last_audio_feed = time.time()
        except Exception:
            pass

    def update(self, is_active: bool = True):
        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # Use real FFT if audio was fed within last 0.35s
        if is_active and self.has_real_audio and (now - self.last_audio_feed) < 0.35:
            for i in range(self.num_bars):
                # Snappy attack, smooth decay
                if self.target_heights[i] > self.heights[i]:
                    self.heights[i] += (self.target_heights[i] - self.heights[i]) * min(1.0, dt * 26.0)
                else:
                    self.heights[i] += (self.target_heights[i] - self.heights[i]) * min(1.0, dt * 11.0)
        else:
            # Idle gentle decay
            for i in range(self.num_bars):
                self.heights[i] += (14.0 - self.heights[i]) * min(1.0, dt * 6.0)

    def draw(self, surface: pygame.Surface, x: int, y: int, width: int, max_h: int = 220):
        bar_gap = 7
        total_gaps = (self.num_bars - 1) * bar_gap
        bar_w = max(6, int((width - total_gaps) / self.num_bars))
        scale = max_h / 220.0

        for i in range(self.num_bars):
            bx = x + i * (bar_w + bar_gap)
            bh = int(min(max_h, self.heights[i] * scale))
            by = y + max_h - bh

            # Pill bar body (Arctic slate-blue pill matching mockup)
            bar_col = (112, 146, 176)
            pygame.draw.rect(surface, bar_col, (bx, by, bar_w, bh), border_radius=bar_w // 2)

            # Cap / Bead color across spectrum (Green -> Gold -> Peach -> Red)
            ratio = i / float(self.num_bars)
            if ratio < 0.25:
                cap_col = NORD14 # Green (Bass)
            elif ratio < 0.50:
                cap_col = NORD13 # Gold/Amber (Mid-Low)
            elif ratio < 0.75:
                cap_col = NORD12 # Peach (Mid-High)
            else:
                cap_col = NORD11 # Red (Treble)

            # Bead circle right on top of pill
            cap_radius = bar_w // 2 + 1
            cap_cx = bx + bar_w // 2
            cap_cy = by
            pygame.draw.circle(surface, cap_col, (cap_cx, cap_cy), cap_radius)

# =============================================================================
# THUMBNAIL CACHE & GENERATOR
# =============================================================================
class ThumbnailManager:
    def __init__(self, default_size=(340, 340)):
        self.default_size = default_size
        self.cache: Dict[Tuple[str, int, int], pygame.Surface] = {}
        self.lock = threading.Lock()

    def get_thumbnail(self, youtube_id: str, title: str, size: Optional[Tuple[int, int]] = None) -> pygame.Surface:
        sz = size or self.default_size
        cache_key = (youtube_id, sz[0], sz[1])
        with self.lock:
            if cache_key in self.cache:
                return self.cache[cache_key]

        candidate_paths = [
            Path(f"thumbnails/{youtube_id}.jpg"),
            Path(f"/roms/ports/snfetchplayer/thumbnails/{youtube_id}.jpg"),
            Path(f"/tmp/sn_thumb_{youtube_id}.jpg")
        ]

        for p in candidate_paths:
            if p.exists():
                try:
                    raw = pygame.image.load(str(p))
                    surf = raw.convert() if pygame.display.get_surface() else raw
                    w, h = surf.get_size()
                    target_ratio = sz[0] / float(sz[1])
                    src_ratio = w / float(h)
                    if src_ratio > target_ratio:
                        new_w = int(h * target_ratio)
                        cx = (w - new_w) // 2
                        cropped = surf.subsurface((cx, 0, new_w, h))
                    else:
                        new_h = int(w / target_ratio)
                        cy = (h - new_h) // 2
                        cropped = surf.subsurface((0, cy, w, new_h))
                    scaled = pygame.transform.smoothscale(cropped, sz)
                    res = self._round_corners(scaled, radius=16, size=sz)
                    with self.lock:
                        self.cache[cache_key] = res
                    return res
                except Exception:
                    pass

        threading.Thread(target=self._fetch_thumb, args=(youtube_id,), daemon=True).start()
        return self._create_placeholder(title, size=sz)

    def _fetch_thumb(self, youtube_id: str):
        local_path = Path(f"/roms/ports/snfetchplayer/thumbnails/{youtube_id}.jpg")
        if not local_path.parent.exists():
            local_path = Path(f"/tmp/sn_thumb_{youtube_id}.jpg")
        url = f"https://img.youtube.com/vi/{youtube_id}/hqdefault.jpg"
        try:
            subprocess.run(["curl", "-s", "-L", url, "-o", str(local_path)], timeout=5)
        except Exception:
            pass

    def _round_corners(self, surf: pygame.Surface, radius: int, size: Tuple[int, int]) -> pygame.Surface:
        mask = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, *size), border_radius=radius)
        res = surf.copy().convert_alpha()
        res.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        return res

    def _create_placeholder(self, title: str, size: Tuple[int, int]) -> pygame.Surface:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(surf, NORD1, (0, 0, *size), border_radius=14)
        pygame.draw.rect(surf, NORD2, (0, 0, *size), width=2, border_radius=14)

        cx, cy = size[0] // 2, size[1] // 2
        for r in range(25, min(size) // 2, 20):
            pygame.draw.circle(surf, NORD2, (cx, cy), r, width=1)

        pygame.draw.circle(surf, NORD0, (cx, cy), 32)
        pygame.draw.circle(surf, NORD8, (cx, cy), 32, width=2)
        return surf

# =============================================================================
# SENDER CONTENT MANAGER (RANDOM JINGLES & TV IDENT ROTATION)
# =============================================================================
class StationContentManager:
    """Manages randomized Radio Jingles and TV Station IDs with persistent 2:1 rotation"""
    def __init__(self):
        self.jingles: List[Path] = []
        self.tv_ids: List[Path] = []
        self.jingle_pool: List[Path] = []
        self.tv_id_pool: List[Path] = []
        self.tracks_since_last_station = 0
        self.rotation_interval = 2
        self._scan_station_assets()

    def _scan_station_assets(self):
        base_dirs = [Path("assets"), Path("/roms/ports/snfetchplayer/assets"), Path(".")]
        for b in base_dirs:
            j_dir = b / "jingles"
            if j_dir.exists():
                self.jingles = sorted(list(j_dir.glob("*.mp3")) + list(j_dir.glob("*.m4a")))
            t_dir = b / "tv_ids"
            if t_dir.exists():
                self.tv_ids = sorted(list(t_dir.glob("*.mp4")) + list(t_dir.glob("*.mkv")))
            if self.jingles or self.tv_ids:
                break

    def should_play_station_content(self) -> bool:
        if self.rotation_interval <= 0:
            return False
        return self.tracks_since_last_station >= self.rotation_interval

    def get_next_jingle(self) -> Optional[Path]:
        if not self.jingles:
            self._scan_station_assets()
        if not self.jingles:
            return None
        if not self.jingle_pool:
            self.jingle_pool = list(self.jingles)
            random.shuffle(self.jingle_pool)
        return self.jingle_pool.pop(0)

    def get_next_tv_id(self) -> Optional[Path]:
        if not self.tv_ids:
            self._scan_station_assets()
        if not self.tv_ids:
            return None
        if not self.tv_id_pool:
            self.tv_id_pool = list(self.tv_ids)
            random.shuffle(self.tv_id_pool)
        return self.tv_id_pool.pop(0)

    def reset_counter(self):
        self.tracks_since_last_station = 0

    def increment_counter(self):
        self.tracks_since_last_station += 1

# =============================================================================
# MAIN DASHBOARD APPLICATION
# =============================================================================
class SNfetchDashboard:
    def __init__(self):
        self.state = STATE_SPLASH
        self.previous_state = STATE_RADIO

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Station North • SNfetchPLAYER v5.0")
        self.clock = pygame.time.Clock()

        # Fonts
        self.font_hero = self._load_font(32, bold=True)
        self.font_title = self._load_font(22, bold=True)
        self.font_body = self._load_font(17, bold=True)
        self.font_artist = self._load_font(16)
        self.font_quote = self._load_font(14, italic=True)
        self.font_badge = self._load_font(13, bold=True)
        self.font_small = self._load_font(13, bold=True)

        # Subsystems
        self.hardware = HardwareManager()
        self.visualizer = IntegratedVisualizer(num_bars=40)
        self.thumb_mgr = ThumbnailManager(default_size=(984, 440))
        self.station_mgr = StationContentManager()
        self.shuffle_mgr = ShuffleQueueManager()
        self.logo_img = self._load_logo()
        self.logo_large = self._load_large_logo()

        # Playlists
        self.available_playlists: List[Dict[str, str]] = []
        self.radio_playlist_idx = 0
        self.tv_playlist_idx = 0
        self.playlist: List[Dict] = []
        self._discover_playlists()

        # Quotes / Lore
        self.quotes: List[str] = []
        self.current_quote = "The lights are low, the bass is heavy. Station North."
        self._load_quotes()

        # The Chronicles
        self.chronicles_data: List[Dict] = []
        self.chronicles_idx = 0
        self.chronicles_img_cache: Dict[str, pygame.Surface] = {}
        self.chronicles_proc: Optional[subprocess.Popen] = None
        self.chronicles_playing = False
        self._load_chronicles()

        # UI State & Focus Cursor
        self.splash_cursor = 0
        self.cockpit_focus_idx = 2 # Default focused button: Play/Pause (idx 2)
        self.current_idx = 0
        self.cursor_idx = 0

        self.is_playing = False
        self.is_radio_zen_mode = False
        self.radio_osd_visible = True
        self.radio_osd_last_interaction = 0.0
        self.is_station_drop = False
        self.station_drop_title = ""
        self.playback_start_time = 0.0
        self.track_duration = 210.0
        self.audio_proc: Optional[subprocess.Popen] = None

        self.is_resolving = False
        self.resolve_target_idx = -1
        self.resolve_thread: Optional[threading.Thread] = None

        self.settings_cursor = 0
        self.settings_column = 0  # 0 = Left Settings, 1 = Right Handbook
        self.settings_guide_scroll_y = 0
        self.settings_guide_max_scroll = 220
        self.settings_feedback_msg = ""
        self.settings_feedback_time = 0.0

        # Load default Radio Playlist
        self._load_active_playlist(is_tv=False)

    def _load_font(self, size: int, bold=False, italic=False) -> pygame.font.Font:
        try:
            for name in ["dejavusans", "freesans", "arial", "helvetica", "sans"]:
                f = pygame.font.SysFont(name, size, bold=bold, italic=italic)
                if f:
                    return f
        except Exception:
            pass
        return pygame.font.Font(None, size)

    def _load_logo(self) -> Optional[pygame.Surface]:
        paths = [Path("sn_logo.png"), Path("/roms/ports/snfetchplayer/sn_logo.png")]
        for p in paths:
            if p.exists():
                try:
                    img = pygame.image.load(str(p))
                    if pygame.display.get_surface():
                        img = img.convert_alpha()
                    img.set_alpha(166)  # 65% opacity
                    return pygame.transform.smoothscale(img, (46, 29))
                except Exception:
                    pass
        return None

    def _load_large_logo(self) -> Optional[pygame.Surface]:
        paths = [Path("sn_logo.png"), Path("/roms/ports/snfetchplayer/sn_logo.png")]
        for p in paths:
            if p.exists():
                try:
                    img = pygame.image.load(str(p))
                    if pygame.display.get_surface():
                        img = img.convert_alpha()
                    img.set_alpha(166)
                    return pygame.transform.smoothscale(img, (200, 126))
                except Exception:
                    pass
        return None

    def _discover_playlists(self):
        self.available_playlists = []
        dirs_to_check = [
            Path("assets/playlists"),
            Path("playlists"),
            Path("/roms/ports/snfetchplayer/assets/playlists"),
            Path("/roms/ports/snfetchplayer/playlists"),
            Path(".")
        ]
        found_paths = {}

        for d in dirs_to_check:
            if d.exists():
                for p in d.glob("*.json"):
                    name = p.stem.lower()
                    if name in ["sprueche", "settings", "chronicles_data", "extractor_rules", "shuffle_state", "catalog_manifest"]:
                        continue
                    if name not in found_paths:
                        found_paths[name] = p

        labels = {
            "main_top100": "Station North • Main Top 100",
            "us_hiphop_top50": "Station North • US Hip-Hop Top 50",
            "us_rnb_top50": "Station North • US R&B Top 50",
            "playlist": "Station North • Essential Selection"
        }

        for key in ["main_top100", "us_hiphop_top50", "us_rnb_top50"]:
            if key in found_paths:
                self.available_playlists.append({"title": labels[key], "path": str(found_paths[key].resolve())})

        for key, p in found_paths.items():
            if key not in ["main_top100", "us_hiphop_top50", "us_rnb_top50"]:
                title = labels.get(key, f"Playlist: {p.stem.upper()}")
                self.available_playlists.append({"title": title, "path": str(p.resolve())})

        if not self.available_playlists:
            self.available_playlists.append({"title": "Station North • Standard", "path": "playlist.json"})

    def _load_active_playlist(self, is_tv: bool = False):
        idx = self.tv_playlist_idx if is_tv else self.radio_playlist_idx
        if not self.available_playlists:
            self._discover_playlists()
        if idx >= len(self.available_playlists):
            idx = 0
        item = self.available_playlists[idx]
        try:
            with open(item["path"], "r", encoding="utf-8") as f:
                self.playlist = json.load(f)
        except Exception:
            self.playlist = []

        self.shuffle_mgr.init_playlist(len(self.playlist), playlist_id=item["title"])
        self.current_idx = self.shuffle_mgr.get_current_idx()
        self.cursor_idx = self.current_idx

    def _load_quotes(self):
        for q_path in [Path("sprueche.json"), Path("/roms/ports/snfetchplayer/sprueche.json")]:
            if q_path.exists():
                try:
                    with open(q_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.quotes = [q.get("text", "") for q in data if "text" in q]
                    break
                except Exception:
                    pass
        self._update_quote()

    def _update_quote(self):
        if self.quotes:
            self.current_quote = random.choice(self.quotes)

    def _load_chronicles(self):
        paths = [
            Path("assets/comic/chronicles_data.json"),
            Path("/roms/ports/snfetchplayer/assets/comic/chronicles_data.json")
        ]
        for p in paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        self.chronicles_data = json.load(f)
                    break
                except Exception:
                    pass

    def get_asset_stats(self) -> Tuple[int, int, int, int, float]:
        j_count = len(self.station_mgr.jingles)
        t_count = len(self.station_mgr.tv_ids)
        c_count = len(self.chronicles_data)
        total = j_count + t_count + c_count
        expected = 174 + 42 + 98
        pct = min(100.0, (total / expected) * 100.0) if expected > 0 else 0.0
        return j_count, t_count, c_count, total, pct

    def show_loading_screen(self, title="STATION NORTH // LOADING...", subtitle="Initializing Audio Stream..."):
        if not pygame.display.get_init():
            pygame.display.init()
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.mouse.set_visible(False)

        self.screen.fill(NORD0)
        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2 - 40
        if self.logo_large:
            self.screen.blit(self.logo_large, (cx - 100, cy - 80))

        t_surf = self._load_font(28, bold=True).render(title, True, NORD8)
        self.screen.blit(t_surf, (cx - t_surf.get_width() // 2, cy + 60))

        s_surf = self._load_font(18).render(subtitle, True, NORD4)
        self.screen.blit(s_surf, (cx - s_surf.get_width() // 2, cy + 104))

        pbar_w = 400
        pbar_x = (SCREEN_WIDTH - pbar_w) // 2
        pbar_y = cy + 148
        pygame.draw.rect(self.screen, COLOR_BAR_BG, (pbar_x, pbar_y, pbar_w, 8), border_radius=4)
        pygame.draw.rect(self.screen, NORD8, (pbar_x, pbar_y, int(pbar_w * 0.75), 8), border_radius=4)

        pygame.display.flip()

    # --- AUDIO CONTROLS (RADIO MODE) ---
    def stop_audio(self):
        if self.audio_proc and self.audio_proc.poll() is None:
            self.audio_proc.terminate()
            try:
                self.audio_proc.wait(timeout=0.4)
            except Exception:
                self.audio_proc.kill()
        self.audio_proc = None
        self.is_playing = False

    def _audio_spectrum_reader(self, proc: subprocess.Popen):
        chunk_size = 2048  # 1024 16-bit mono samples (~46ms @ 22.05kHz)
        try:
            while proc and proc.poll() is None and self.is_playing:
                data = proc.stdout.read(chunk_size)
                if not data:
                    break
                self.visualizer.feed_pcm(data)
        except Exception:
            pass

    def trigger_play_track_async(self, idx: int):
        if self.is_resolving:
            return
        self.resolve_target_idx = idx
        self.is_resolving = True
        self.resolve_thread = threading.Thread(target=self._resolve_and_play_worker, args=(idx,), daemon=True)
        self.resolve_thread.start()

    def _resolve_and_play_worker(self, idx: int):
        try:
            if idx < 0 or idx >= len(self.playlist):
                return

            self.stop_audio()

            # 2:1 Rotation Check (unless Repeat mode is on)
            if not self.shuffle_mgr.is_repeat_mode and self.station_mgr.should_play_station_content():
                jingle_path = self.station_mgr.get_next_jingle()
                if jingle_path and jingle_path.exists():
                    self.station_mgr.reset_counter()
                    self.is_station_drop = True
                    self.station_drop_title = f"Station North • ID #{jingle_path.stem}"
                    self.current_idx = idx
                    self.cursor_idx = idx

                    cmd = [
                        "ffmpeg", "-y",
                        "-i", str(jingle_path),
                        "-filter_complex", "[0:a]asplit=2[out1][out2]",
                        "-map", "[out1]", "-f", "alsa", "default",
                        "-map", "[out2]", "-f", "s16le", "-ac", "1", "-ar", "22050", "-"
                    ]
                    self.audio_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    self.is_playing = True
                    self.playback_start_time = time.time()
                    self.track_duration = 12.0
                    threading.Thread(target=self._audio_spectrum_reader, args=(self.audio_proc,), daemon=True).start()
                    self.audio_proc.wait()
                    self.is_station_drop = False

            track = self.playlist[idx]
            yt_id = track.get("youtubeId")
            stream_url, duration = get_stream(yt_id, prefer_audio_only=True)

            if stream_url:
                self.current_idx = idx
                self.cursor_idx = idx
                self._update_quote()

                cmd = [
                    "ffmpeg", "-y",
                    "-i", stream_url,
                    "-filter_complex", "[0:a]asplit=2[out1][out2]",
                    "-map", "[out1]", "-f", "alsa", "default",
                    "-map", "[out2]", "-f", "s16le", "-ac", "1", "-ar", "22050", "-"
                ]
                self.audio_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                self.is_playing = True
                self.playback_start_time = time.time()
                try:
                    self.track_duration = float(duration) if duration and float(duration) > 0 else 210.0
                except (ValueError, TypeError):
                    self.track_duration = 210.0
                threading.Thread(target=self._audio_spectrum_reader, args=(self.audio_proc,), daemon=True).start()
        except Exception as e:
            print(f"Playback error: {e}")
        finally:
            self.is_resolving = False

    # --- VIDEO CONTROLS (TV MODE: 4:3 DISPLAY FILL & FLOATING OSD) ---
    def _get_input_devices(self):
        devices = []
        try:
            import evdev
            for p in evdev.list_devices():
                try:
                    devices.append(evdev.InputDevice(p))
                except Exception:
                    pass
        except Exception:
            pass
        return devices

    def generate_tv_overlay_image(self, track: Dict[str, str], output_path: str = "/tmp/tv_ui_overlay.png") -> str:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 0))  # 100% transparent center where video plays

        # 1. Top Bar
        pygame.draw.rect(overlay, (46, 52, 64, 215), (0, 0, SCREEN_WIDTH, 54))
        pygame.draw.line(overlay, (67, 76, 94, 230), (0, 54), (SCREEN_WIDTH, 54), 1)

        lx = 20
        if self.logo_img:
            l_scaled = pygame.transform.smoothscale(self.logo_img, (32, 32))
            overlay.blit(l_scaled, (lx, 11))
            lx += 42

        title_surf = self._load_font(19, bold=True).render("Station North", True, NORD6)
        overlay.blit(title_surf, (lx, 7))

        sub_surf = self._load_font(12, bold=True).render("SNfetchPLAYER • Television Broadcast", True, NORD8)
        overlay.blit(sub_surf, (lx, 30))

        # Battery & Time
        bat_cap, is_charging = self.hardware.get_battery_info()
        bat_color = NORD14 if bat_cap > 20 else NORD11
        bx, by = 840, 20
        pygame.draw.rect(overlay, bat_color, (bx, by, 22, 14), width=1, border_radius=2)
        pygame.draw.rect(overlay, bat_color, (bx + 22, by + 3, 2, 8))
        fill_w = max(2, int(18 * (bat_cap / 100.0)))
        pygame.draw.rect(overlay, bat_color, (bx + 2, by + 2, fill_w, 10))

        charge_symbol = "⚡ " if is_charging else ""
        bat_surf = self._load_font(12, bold=True).render(f"{charge_symbol}{bat_cap}%", True, bat_color)
        overlay.blit(bat_surf, (bx + 28, 18))

        time_str = self.hardware.get_time_str()
        time_surf = self._load_font(18, bold=True).render(time_str, True, NORD6)
        overlay.blit(time_surf, (940, 16))

        # 2. Lower Card: Title, Artist & 5 Chunky Buttons
        card2_x = 20
        card2_y = 514
        card2_w = 984
        card2_h = 238
        cx = card2_x + card2_w // 2

        pygame.draw.rect(overlay, (46, 52, 64, 225), (card2_x, card2_y, card2_w, card2_h), border_radius=16)
        pygame.draw.rect(overlay, (67, 76, 94, 240), (card2_x, card2_y, card2_w, card2_h), width=2, border_radius=16)

        title = track.get("title", "Unknown Title")
        artist = track.get("artist", "Unknown Artist")

        title_font = self._load_font(26, bold=True)
        if len(title) > 38:
            title_font = self._load_font(22, bold=True)
        t_surf = title_font.render(title, True, NORD6)
        overlay.blit(t_surf, (cx - t_surf.get_width() // 2, card2_y + 16))

        a_surf = self._load_font(17).render(artist, True, NORD4)
        overlay.blit(a_surf, (cx - a_surf.get_width() // 2, card2_y + 48))

        btn_area_x = card2_x + 16
        btn_area_w = card2_w - 32
        btn_y = card2_y + 82
        self.draw_5_button_cockpit(overlay, btn_area_x, btn_y, btn_area_w, height=140)

        pygame.image.save(overlay, output_path)
        return output_path

    def launch_video_playback(self, start_idx: int, manual_trigger: bool = True):
        """Plays fullscreen video with 4:3 display fill and floating OSD on manual skip"""
        self.stop_audio()
        curr_idx = start_idx
        show_osd_this_track = manual_trigger

        import select
        try:
            import evdev
        except ImportError:
            evdev = None

        while True:
            if curr_idx < 0 or curr_idx >= len(self.playlist):
                break

            if not pygame.display.get_init():
                pygame.display.init()
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                pygame.mouse.set_visible(False)

            track = self.playlist[curr_idx]
            track_title = track.get("title", "Title")
            track_artist = track.get("artist", "Artist")

            self.show_loading_screen("STATION NORTH TV", f"Loading Video: {track_artist} - {track_title}")

            # 2:1 Rotation Check (unless Repeat mode is on)
            if not self.shuffle_mgr.is_repeat_mode and self.station_mgr.should_play_station_content():
                tv_id_path = self.station_mgr.get_next_tv_id()
                if tv_id_path and tv_id_path.exists():
                    self.station_mgr.reset_counter()
                    completed = self._play_tv_station_id_fullscreen(tv_id_path)
                    if not completed:
                        break
                    if not pygame.display.get_init():
                        pygame.display.init()
                        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                        pygame.mouse.set_visible(False)
                    self.show_loading_screen("STATION NORTH TV", f"Loading Video: {track_artist} - {track_title}")

            yt_id = track.get("youtubeId")
            stream_url, _ = get_stream(yt_id, prefer_audio_only=False)
            if not stream_url:
                curr_idx = self.shuffle_mgr.advance_next()
                show_osd_this_track = False
                continue

            # Bauchbinde via nativem ASS-Untertitel (blendet sanft ein und nach 4.8s automatisch aus)
            osd_file = generate_osd_ass(track, show_osd=True, is_repeat=self.shuffle_mgr.is_repeat_mode)

            logo_path = "/roms/ports/snfetchplayer/sn_logo.png"
            if not Path(logo_path).exists():
                logo_path = str(Path("sn_logo.png").resolve())

            # 4:3 Display-Fill + 65% Logo Transparenz + Elegante Bauchbinde
            vf_filter = (
                f"crop=ih*4/3:ih:(iw-ih*4/3)/2:0,scale=1024:768 [main]; "
                f"movie={logo_path},scale=120:-1,format=rgba,colorchannelmixer=aa=0.65 [logo]; "
                f"[main][logo] overlay=main_w-overlay_w-25:main_h-overlay_h-25, "
                f"ass='{osd_file}'"
            )

            cmd = [
                "ffplay",
                "-fs",
                "-autoexit",
                "-sync", "audio",
                "-window_title", f"STATION NORTH • {track_artist} - {track_title}",
                "-loglevel", "error",
                "-vf", vf_filter,
                stream_url
            ]

            pygame.display.quit()
            play_start_time = time.time()
            proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL)

            devices = self._get_input_devices()
            action = "AUTO"
            is_paused = False

            while proc.poll() is None:
                if devices and evdev:
                    try:
                        r, _, _ = select.select(devices, [], [], 0.04)
                        should_break = False
                        for dev in r:
                            try:
                                active = dev.active_keys()
                                # Universal PortMaster Kill: SELECT (314 / 15) + START (315 / 25)
                                if (314 in active and 315 in active) or (15 in active and 25 in active):
                                    proc.kill()
                                    sys.exit(0)

                                # Funktion 2: [B] / ESC / Q: Sofortiger Exit & Zurueck zum Menue
                                if any(k in active for k in (305, 1, 14, 16)):
                                    action = "EXIT"
                                    should_break = True
                                    break

                                while True:
                                    event = dev.read_one()
                                    if event is None:
                                        break
                                    if event.type == evdev.ecodes.EV_KEY and event.value == 1:
                                        code = event.code

                                        # Funktion 1: START / P / ENTER -> Play / Pause Toggle
                                        if code in (315, 25, 706, 28):
                                            if is_paused:
                                                os.kill(proc.pid, signal.SIGCONT)
                                                is_paused = False
                                            else:
                                                os.kill(proc.pid, signal.SIGSTOP)
                                                is_paused = True

                                        # Funktion 2: [B] / ESC / Q -> Zurueck / Exit
                                        elif code in (305, 1, 14, 16):
                                            action = "EXIT"
                                            should_break = True
                                            break

                                        # Funktion 3: [►] Steuerkreuz / R1 / Joystick Rechts -> Naechstes Video
                                        elif code in (547, 311, 106):
                                            if is_paused:
                                                os.kill(proc.pid, signal.SIGCONT)
                                            action = "NEXT"
                                            should_break = True
                                            break

                                        # Funktion 3: [◄] Steuerkreuz / L1 / Joystick Links -> Vorheriges Video
                                        elif code in (546, 310, 105):
                                            if is_paused:
                                                os.kill(proc.pid, signal.SIGCONT)
                                            action = "PREV"
                                            should_break = True
                                            break

                                        # Funktion 4: [X] & [Y] -> Repeat-One-Funktion (beide Tasten machen das Gleiche!)
                                        elif code in (307, 33, 308, 21):
                                            self.shuffle_mgr.toggle_repeat()

                                        # D-Pad Oben / Unten abfangen (Verhindert 1-Minuten-Spulen in ffplay)
                                        elif code in (103, 108, 544, 545):
                                            pass

                                    elif event.type == evdev.ecodes.EV_ABS and event.code == 0:
                                        if event.value > 1200:
                                            if is_paused:
                                                os.kill(proc.pid, signal.SIGCONT)
                                            action = "NEXT"
                                            should_break = True
                                            break
                                        elif event.value < -1200:
                                            if is_paused:
                                                os.kill(proc.pid, signal.SIGCONT)
                                            action = "PREV"
                                            should_break = True
                                            break
                            except Exception:
                                pass
                            if should_break:
                                break
                        if should_break:
                            if is_paused:
                                os.kill(proc.pid, signal.SIGCONT)
                            proc.kill()
                            try:
                                proc.wait(timeout=0.3)
                            except Exception:
                                pass
                            break
                    except Exception:
                        time.sleep(0.04)
                else:
                    time.sleep(0.08)

            # Sicherstellen, dass ffplay sofort beendet wird
            if proc.poll() is None:
                proc.kill()
                try:
                    proc.wait(timeout=0.3)
                except Exception:
                    pass

            elapsed = time.time() - play_start_time

            # Check pending events in devices that may have arrived right as ffplay exited
            time.sleep(0.05)
            for dev in devices:
                try:
                    active = dev.active_keys()
                    if any(k in active for k in (305, 307, 1, 33, 706, 16)):
                        action = "EXIT"
                    while True:
                        ev = dev.read_one()
                        if ev is None:
                            break
                        if ev.type == evdev.ecodes.EV_KEY and ev.value == 1:
                            if ev.code in (305, 307, 1, 33, 706, 16):
                                action = "EXIT"
                            elif ev.code in (547, 311, 106):
                                action = "NEXT"
                            elif ev.code in (546, 310, 105):
                                action = "PREV"
                except Exception:
                    pass

            # If it exited quickly (< 8s) and was not a manual skip, it was an early abort
            if action == "AUTO" and elapsed < 8.0:
                action = "EXIT"

            if action == "EXIT":
                self.current_idx = curr_idx
                self.cursor_idx = curr_idx
                break
            elif action == "NEXT" or action == "AUTO":
                self.station_mgr.increment_counter()
                curr_idx = self.shuffle_mgr.advance_next()
                self.current_idx = curr_idx
                self.cursor_idx = curr_idx
                self._update_quote()
                show_osd_this_track = True
            elif action == "PREV":
                curr_idx = self.shuffle_mgr.step_prev()
                self.current_idx = curr_idx
                self.cursor_idx = curr_idx
                self._update_quote()
                show_osd_this_track = True

        if not pygame.display.get_init():
            pygame.display.init()
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.mouse.set_visible(False)
        pygame.display.set_caption("Station North • SNfetchPLAYER v5.0")
        time.sleep(0.12)
        pygame.event.clear()
        self.is_playing = False

    def _play_tv_station_id_fullscreen(self, clip_path: Path) -> bool:
        logo_path = "/roms/ports/snfetchplayer/sn_logo.png"
        if not Path(logo_path).exists():
            logo_path = str(Path("sn_logo.png").resolve())

        # 4:3 Display-Fill + 65% Logo Transparenz unten rechts
        vf_filter = (
            f"crop=ih*4/3:ih:(iw-ih*4/3)/2:0,scale=1024:768 [main]; "
            f"movie={logo_path},scale=120:-1,format=rgba,colorchannelmixer=aa=0.65 [logo]; "
            f"[main][logo] overlay=main_w-overlay_w-25:main_h-overlay_h-25"
        )

        cmd = [
            "ffplay",
            "-fs",
            "-autoexit",
            "-sync", "audio",
            "-window_title", "STATION NORTH TV IDENT",
            "-loglevel", "error",
            "-vf", vf_filter,
            str(clip_path)
        ]
        pygame.display.quit()
        proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL)

        devices = self._get_input_devices()
        interrupted = False
        import select
        try:
            import evdev
        except ImportError:
            evdev = None

        while proc.poll() is None:
            if devices and evdev:
                try:
                    r, _, _ = select.select(devices, [], [], 0.04)
                    should_break = False
                    for dev in r:
                        try:
                            active = dev.active_keys()
                            if (314 in active and 315 in active) or (15 in active and 25 in active):
                                proc.kill()
                                sys.exit(0)

                            if any(k in active for k in (305, 1, 16, 706)):
                                should_break = True
                                interrupted = True
                                break

                            while True:
                                event = dev.read_one()
                                if event is None:
                                    break
                                if event.type == evdev.ecodes.EV_KEY and event.value == 1:
                                    if event.code in (547, 546, 311, 310, 106, 105, 305, 307, 1, 33, 706, 16):
                                        should_break = True
                                        interrupted = True
                                        break
                        except Exception:
                            pass
                        if should_break:
                            break
                    if should_break:
                        proc.kill()
                        try:
                            proc.wait(timeout=0.3)
                        except Exception:
                            pass
                        break
                except Exception:
                    time.sleep(0.04)
            else:
                time.sleep(0.08)

        if proc.poll() is None:
            proc.kill()
            try:
                proc.wait(timeout=0.3)
            except Exception:
                pass
        time.sleep(0.15)
        for dev in devices:
            try:
                while dev.read_one() is not None:
                    pass
            except Exception:
                pass
        return not interrupted

    # --- CHRONICLES AUDIO (FAITH NARRATION) ---
    def stop_chronicles_audio(self):
        if self.chronicles_proc and self.chronicles_proc.poll() is None:
            self.chronicles_proc.terminate()
            try:
                self.chronicles_proc.wait(timeout=0.5)
            except Exception:
                self.chronicles_proc.kill()
        self.chronicles_proc = None
        self.chronicles_playing = False

    def toggle_chronicles_audio(self):
        if self.chronicles_playing:
            self.stop_chronicles_audio()
            return

        if not self.chronicles_data or self.chronicles_idx >= len(self.chronicles_data):
            return

        item = self.chronicles_data[self.chronicles_idx]
        panel_id = item.get("id", self.chronicles_idx + 1)
        audio_name = f"p_{panel_id:03d}.mp3"
        audio_paths = [
            Path("assets/comic/audio") / audio_name,
            Path("/roms/ports/snfetchplayer/assets/comic/audio") / audio_name
        ]
        target_path = None
        for ap in audio_paths:
            if ap.exists():
                target_path = ap
                break

        if target_path:
            self.stop_chronicles_audio()
            cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error", str(target_path)]
            self.chronicles_proc = subprocess.Popen(cmd)
            self.chronicles_playing = True

    # =========================================================================
    # RENDER HELPER: THE 5-BUTTON PASTEL COCKPIT (MATCHING ANDROID APP)
    # =========================================================================
    def draw_5_button_cockpit(self, surface: pygame.Surface, x: int, y: int, width: int, height: int = 138):
        """Draws the massive, chunky 5-button pastel pill cockpit with geometric vector icons and focus ring"""
        num_btn = 5
        gap = 14
        btn_w = (width - (num_btn - 1) * gap) // num_btn

        buttons = [
            {"col": NORD7, "title": "Fullscreen"},
            {"col": NORD12, "title": "Prev Track"},
            {"col": NORD9, "title": "Play/Pause"},
            {"col": NORD15, "title": "Next Track"},
            {"col": NORD13, "title": "Repeat Loop"}
        ]

        for i, btn in enumerate(buttons):
            bx = x + i * (btn_w + gap)
            b_rect = pygame.Rect(bx, y, btn_w, height)
            is_focused = (i == self.cockpit_focus_idx)
            icon_col = NORD0 # Dark Polar Night charcoal

            # 1. Pastel Pill Surface
            pygame.draw.rect(surface, btn["col"], b_rect, border_radius=14)

            # 2. Glowing Android TV Focus Border
            if is_focused:
                pygame.draw.rect(surface, NORD6, (bx - 3, y - 3, btn_w + 6, height + 6), width=3, border_radius=16)
                pygame.draw.rect(surface, NORD8, (bx - 5, y - 5, btn_w + 10, height + 10), width=2, border_radius=18)

            # 3. Active Repeat Border
            if i == 4 and self.shuffle_mgr.is_repeat_mode:
                pygame.draw.rect(surface, NORD6, b_rect, width=3, border_radius=14)

            # 4. Geometric Vector Icons (Centered in Button)
            cx = bx + btn_w // 2
            cy = y + height // 2

            if i == 0:
                # Fullscreen: 4 Expanding Corner Brackets
                d = 16
                arm = 9
                w = 4
                # Top-Left
                pygame.draw.line(surface, icon_col, (cx - d, cy - d), (cx - d + arm, cy - d), w)
                pygame.draw.line(surface, icon_col, (cx - d, cy - d), (cx - d, cy - d + arm), w)
                # Top-Right
                pygame.draw.line(surface, icon_col, (cx + d, cy - d), (cx + d - arm, cy - d), w)
                pygame.draw.line(surface, icon_col, (cx + d, cy - d), (cx + d, cy - d + arm), w)
                # Bottom-Left
                pygame.draw.line(surface, icon_col, (cx - d, cy + d), (cx - d + arm, cy + d), w)
                pygame.draw.line(surface, icon_col, (cx - d, cy + d), (cx - d, cy + d - arm), w)
                # Bottom-Right
                pygame.draw.line(surface, icon_col, (cx + d, cy + d), (cx + d - arm, cy + d), w)
                pygame.draw.line(surface, icon_col, (cx + d, cy + d), (cx + d, cy - d + arm), w)

            elif i == 1:
                # Previous Track: Vertical bar + Left-pointing triangle (|◄)
                pygame.draw.rect(surface, icon_col, (cx - 16, cy - 16, 5, 32), border_radius=1)
                pts = [(cx - 12, cy), (cx + 14, cy - 16), (cx + 14, cy + 16)]
                pygame.draw.polygon(surface, icon_col, pts)

            elif i == 2:
                # Play / Pause
                if self.is_playing:
                    # Pause: Twin vertical bars (||)
                    pygame.draw.rect(surface, icon_col, (cx - 12, cy - 16, 8, 32), border_radius=2)
                    pygame.draw.rect(surface, icon_col, (cx + 4, cy - 16, 8, 32), border_radius=2)
                else:
                    # Play: Right-pointing triangle (▶)
                    pts = [(cx - 10, cy - 16), (cx + 16, cy), (cx - 10, cy + 16)]
                    pygame.draw.polygon(surface, icon_col, pts)

            elif i == 3:
                # Next Track: Triangle pointing right + Vertical bar (►|)
                pts = [(cx - 14, cy - 16), (cx + 12, cy), (cx - 14, cy + 16)]
                pygame.draw.polygon(surface, icon_col, pts)
                pygame.draw.rect(surface, icon_col, (cx + 12, cy - 16, 5, 32), border_radius=1)

            elif i == 4:
                # Repeat Loop
                rx = cx - 18
                ry = cy - 13
                rw = 36
                rh = 26
                lw = 3
                # Top horizontal
                pygame.draw.line(surface, icon_col, (rx, ry), (rx + rw, ry), lw)
                # Right vertical
                pygame.draw.line(surface, icon_col, (rx + rw, ry), (rx + rw, ry + rh), lw)
                # Bottom horizontal
                pygame.draw.line(surface, icon_col, (rx + rw, ry + rh), (rx, ry + rh), lw)
                # Left vertical
                pygame.draw.line(surface, icon_col, (rx, ry + rh), (rx, ry), lw)
                # Arrowhead top right (pointing right)
                pygame.draw.polygon(surface, icon_col, [(rx + rw, ry - 6), (rx + rw + 8, ry), (rx + rw, ry + 6)])
                # Arrowhead bottom left (pointing left)
                pygame.draw.polygon(surface, icon_col, [(rx, ry + rh - 6), (rx - 8, ry + rh), (rx, ry + rh + 6)])

                # "1" inside badge if loop mode is active
                if self.shuffle_mgr.is_repeat_mode:
                    one_surf = self._load_font(14, bold=True).render("1", True, icon_col)
                    surface.blit(one_surf, (cx - one_surf.get_width() // 2, cy - one_surf.get_height() // 2))

    # =========================================================================
    # VECTOR ICON HELPERS FOR SPLASH SCREEN
    # =========================================================================
    def _draw_splash_radio_icon(self, surface: pygame.Surface, cx: int, cy: int, col: Tuple[int, int, int]):
        """Vector Retro Boombox / Radio Tuner icon"""
        bw, bh = 114, 64
        bx, by = cx - bw // 2, cy - bh // 2 + 6
        pygame.draw.rect(surface, col, (bx, by, bw, bh), width=3, border_radius=10)
        # Handle
        hw, hh = 56, 16
        pygame.draw.rect(surface, col, (cx - hw // 2, by - hh + 2, hw, hh), width=3, border_radius=6)
        # Left Speaker
        sp_r = 18
        sp_lx = bx + 28
        sp_ly = by + bh // 2 + 2
        pygame.draw.circle(surface, col, (sp_lx, sp_ly), sp_r, width=3)
        pygame.draw.circle(surface, col, (sp_lx, sp_ly), 6)
        # Right Speaker
        sp_rx = bx + bw - 28
        pygame.draw.circle(surface, col, (sp_rx, sp_ly), sp_r, width=3)
        pygame.draw.circle(surface, col, (sp_rx, sp_ly), 6)
        # Center Cassette Door
        cw, ch = 30, 20
        pygame.draw.rect(surface, col, (cx - cw // 2, by + 12, cw, ch), width=2, border_radius=4)
        pygame.draw.line(surface, col, (cx - 10, by + 22), (cx + 10, by + 22), 2)
        # Antenna
        pygame.draw.line(surface, col, (bx + bw - 14, by), (bx + bw + 18, by - 26), 3)
        pygame.draw.circle(surface, col, (bx + bw + 18, by - 26), 4)

    def _draw_splash_tv_icon(self, surface: pygame.Surface, cx: int, cy: int, col: Tuple[int, int, int]):
        """Vector Retro CRT Television with twin rabbit-ear antennas"""
        tw, th = 114, 68
        tx, ty = cx - tw // 2, cy - th // 2 + 6
        pygame.draw.rect(surface, col, (tx, ty, tw, th), width=3, border_radius=12)
        # CRT Screen
        sw, sh = 72, 52
        sx, sy = tx + 8, ty + 8
        pygame.draw.rect(surface, col, (sx, sy, sw, sh), width=3, border_radius=10)
        # Control dials
        kx = tx + tw - 16
        pygame.draw.circle(surface, col, (kx, ty + 20), 7, width=2)
        pygame.draw.circle(surface, col, (kx, ty + 42), 7, width=2)
        # Rabbit-Ear Antennas
        pygame.draw.line(surface, col, (cx - 12, ty), (cx - 38, ty - 28), 3)
        pygame.draw.circle(surface, col, (cx - 38, ty - 28), 4)
        pygame.draw.line(surface, col, (cx + 12, ty), (cx + 38, ty - 28), 3)
        pygame.draw.circle(surface, col, (cx + 38, ty - 28), 4)
        # Feet
        pygame.draw.line(surface, col, (tx + 18, ty + th), (tx + 12, ty + th + 8), 3)
        pygame.draw.line(surface, col, (tx + tw - 18, ty + th), (tx + tw - 12, ty + th + 8), 3)

    def _draw_splash_chronicles_icon(self, surface: pygame.Surface, cx: int, cy: int, col: Tuple[int, int, int]):
        """Vector Graphic Novel / Open Lore Tome icon"""
        sy_top = cy - 24
        sy_bot = cy + 42
        pygame.draw.line(surface, col, (cx, sy_top), (cx, sy_bot), 3)
        # Left Page
        left_pts = [
            (cx, sy_top),
            (cx - 24, sy_top - 6),
            (cx - 52, sy_top + 2),
            (cx - 52, sy_bot - 4),
            (cx - 24, sy_bot - 10),
            (cx, sy_bot)
        ]
        pygame.draw.lines(surface, col, False, left_pts, 3)
        # Left page text lines
        pygame.draw.line(surface, col, (cx - 42, sy_top + 14), (cx - 12, sy_top + 9), 2)
        pygame.draw.line(surface, col, (cx - 42, sy_top + 24), (cx - 12, sy_top + 19), 2)
        pygame.draw.line(surface, col, (cx - 42, sy_top + 34), (cx - 16, sy_top + 29), 2)

        # Right Page
        right_pts = [
            (cx, sy_top),
            (cx + 24, sy_top - 6),
            (cx + 52, sy_top + 2),
            (cx + 52, sy_bot - 4),
            (cx + 24, sy_bot - 10),
            (cx, sy_bot)
        ]
        pygame.draw.lines(surface, col, False, right_pts, 3)
        # Right page text lines
        pygame.draw.line(surface, col, (cx + 12, sy_top + 9), (cx + 42, sy_top + 14), 2)
        pygame.draw.line(surface, col, (cx + 12, sy_top + 19), (cx + 42, sy_top + 24), 2)
        pygame.draw.line(surface, col, (cx + 16, sy_top + 29), (cx + 42, sy_top + 34), 2)
        # Bookmark ribbon
        pygame.draw.line(surface, col, (cx, sy_bot), (cx + 8, sy_bot + 16), 3)

    # =========================================================================
    # RENDERER 1: SPLASH SCREEN (HAUPTPORTAL - PURE VISUAL ARCADE SELECTOR)
    # =========================================================================
    def draw_splash_screen(self):
        self.screen.fill(NORD0)

        # 1. Logo & Header
        cx = SCREEN_WIDTH // 2
        cy = 82
        if self.logo_large:
            self.screen.blit(self.logo_large, (cx - 100, cy - 58))

        head_s = self._load_font(28, bold=True).render("STATION NORTH", True, NORD6)
        self.screen.blit(head_s, (cx - head_s.get_width() // 2, cy + 72))

        sub_s = self._load_font(15, bold=True).render("SNfetchPLAYER • YOUR TV & RADIO ENGINE", True, NORD8)
        self.screen.blit(sub_s, (cx - sub_s.get_width() // 2, cy + 108))

        # 2. Modus-Karten (Radio: Cyan, TV: Mint, Chronicles: Gold)
        card_w = 296
        card_h = 290
        gap = 24
        total_w = 3 * card_w + 2 * gap
        start_x = (SCREEN_WIDTH - total_w) // 2
        card_y = cy + 146

        modes = [
            {"title": "RADIO", "accent": NORD8, "icon_func": self._draw_splash_radio_icon},
            {"title": "TV", "accent": NORD7, "icon_func": self._draw_splash_tv_icon},
            {"title": "CHRONICLES", "accent": NORD13, "icon_func": self._draw_splash_chronicles_icon}
        ]

        for i, m in enumerate(modes):
            x = start_x + i * (card_w + gap)
            rect = pygame.Rect(x, card_y, card_w, card_h)
            is_sel = (i == self.splash_cursor)
            accent = m["accent"]

            # Background & Borders (Each card has its distinct color identity)
            dim_accent = tuple(int(c * 0.72) for c in accent)
            border_dim = tuple(int(c * 0.45) for c in accent)
            bg_col = NORD1 if is_sel else (36, 42, 54)
            pygame.draw.rect(self.screen, bg_col, rect, border_radius=16)

            if is_sel:
                # Glowing accent border & highlight
                pygame.draw.rect(self.screen, accent, rect, width=3, border_radius=16)
                pygame.draw.rect(self.screen, NORD6, (x - 2, card_y - 2, card_w + 4, card_h + 4), width=1, border_radius=18)
                # Accent Header Stripe
                pygame.draw.rect(self.screen, accent, (x + 20, card_y, card_w - 40, 5), border_radius=2)
            else:
                pygame.draw.rect(self.screen, border_dim, rect, width=2, border_radius=16)

            # Title in card's color
            t_col = accent if is_sel else dim_accent
            mt_surf = self._load_font(28, bold=True).render(m["title"], True, t_col)
            self.screen.blit(mt_surf, (x + (card_w - mt_surf.get_width()) // 2, card_y + 28))

            # Centered Mode Vector Icon in card's color
            cx_box = x + card_w // 2
            cy_box = card_y + 148
            icon_col = accent if is_sel else dim_accent
            m["icon_func"](self.screen, cx_box, cy_box, icon_col)

            # Selected Action Prompt
            if is_sel:
                act_surf = self._load_font(14, bold=True).render("PRESS [A] TO LAUNCH", True, accent)
                self.screen.blit(act_surf, (x + (card_w - act_surf.get_width()) // 2, card_y + 248))

        # 3. Live-Asset-Ladebalken unten
        j_found, t_found, c_found, total_found, pct = self.get_asset_stats()
        bar_w = 640
        bar_x = (SCREEN_WIDTH - bar_w) // 2
        bar_y = card_y + card_h + 26

        pygame.draw.rect(self.screen, COLOR_BAR_BG, (bar_x, bar_y, bar_w, 8), border_radius=4)
        fill_w = max(4, int(bar_w * (pct / 100.0)))
        pygame.draw.rect(self.screen, NORD8, (bar_x, bar_y, fill_w, 8), border_radius=4)

        status_text = f"Local Assets: {j_found}/174 Jingles • {t_found}/42 TV IDs • {c_found}/98 Chronicles ({int(pct)}% Ready)"
        stat_surf = self._load_font(12, bold=True).render(status_text, True, NORD4)
        self.screen.blit(stat_surf, (cx - stat_surf.get_width() // 2, bar_y + 14))

    # =========================================================================
    # RENDERER 2: RADIO ZEN VISUALIZER (FULLSCREEN SPECTRUM ANALYZER)
    # =========================================================================
    def draw_radio_zen_mode(self):
        """Full 1024x768 Zen Visualizer screen for ambient desk listening"""
        self.screen.fill(NORD0)

        # 1. Fullscreen Visualizer across bottom 440px
        self.visualizer.update(is_active=self.is_playing)
        self.visualizer.draw(self.screen, x=32, y=260, width=960, max_h=440)

        # 2. Station North Logo Watermark (top left, proportional un-distorted)
        if self.logo_large:
            orig_w, orig_h = self.logo_large.get_size()
            wm_h = 60
            wm_w = int(wm_h * (orig_w / orig_h))
            wm = pygame.transform.smoothscale(self.logo_large, (wm_w, wm_h))
            wm.set_alpha(180)
            self.screen.blit(wm, (40, 36))

        # Station Title / Clock (top right)
        clock_str = HardwareManager.get_time_str()
        time_s = self._load_font(26, bold=True).render(clock_str, True, NORD4)
        self.screen.blit(time_s, (SCREEN_WIDTH - 44 - time_s.get_width(), 42))

        # 3. Track Info (Centered, Large & Floating)
        track = self.playlist[self.current_idx] if self.current_idx < len(self.playlist) else {}
        title = track.get("title", "Unknown Title")
        artist = track.get("artist", "The Queen's Frequency" if self.is_station_drop else "Unknown Artist")
        if self.is_station_drop:
            title = self.station_drop_title

        cx = SCREEN_WIDTH // 2
        t_font = self._load_font(34, bold=True)
        if len(title) > 30:
            t_font = self._load_font(26, bold=True)
        t_surf = t_font.render(title, True, NORD6)
        self.screen.blit(t_surf, (cx - t_surf.get_width() // 2, 90))

        a_surf = self._load_font(20, bold=True).render(artist, True, NORD8)
        self.screen.blit(a_surf, (cx - a_surf.get_width() // 2, 138))

        # Auto-Hide Check (4.0 Sekunden Inaktivitaet)
        if time.time() - self.radio_osd_last_interaction > 4.0:
            self.radio_osd_visible = False

        if self.radio_osd_visible:
            # Schwebendes On-Screen-Menue (5 Chunky Buttons)
            card_w = 900
            card_h = 136
            card_x = (SCREEN_WIDTH - card_w) // 2
            card_y = 596

            osd_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            pygame.draw.rect(osd_surf, (46, 52, 64, 235), (0, 0, card_w, card_h), border_radius=18)
            pygame.draw.rect(osd_surf, (67, 76, 94, 255), (0, 0, card_w, card_h), width=2, border_radius=18)
            self.screen.blit(osd_surf, (card_x, card_y))

            self.draw_5_button_cockpit(self.screen, card_x + 16, card_y + 14, card_w - 32, height=108)
        else:
            # Dezenter Hinweis wenn ausgeblendet
            hint_s = self._load_font(13).render("ON-SCREEN MENU HIDDEN • PRESS D-PAD TO SHOW • [B] TO EXIT", True, NORD3)
            self.screen.blit(hint_s, (cx - hint_s.get_width() // 2, 738))

    # =========================================================================
    # RENDERER 3: TOP-BAR (STATUSLEISTE MIT FIXIERTEN SLOTS)
    # =========================================================================
    def draw_top_bar(self, custom_title: Optional[str] = None):
        pygame.draw.rect(self.screen, COLOR_BAR_BG, (0, 0, SCREEN_WIDTH, 54))
        pygame.draw.line(self.screen, NORD2, (0, 54), (SCREEN_WIDTH, 54), 1)

        lx = 20
        if self.logo_img:
            orig_w, orig_h = self.logo_img.get_size()
            lh = 30
            lw = int(lh * (orig_w / orig_h))
            l_scaled = pygame.transform.smoothscale(self.logo_img, (lw, lh))
            self.screen.blit(l_scaled, (lx, 12))
            lx += lw + 14

        title_surf = self._load_font(19, bold=True).render("Station North", True, NORD6)
        self.screen.blit(title_surf, (lx, 7))

        sub_surf = self._load_font(12, bold=True).render("SNfetchPLAYER • Your TV & Radio Engine", True, NORD8)
        self.screen.blit(sub_surf, (lx, 30))

        # Statusleiste rechts (WLAN, Batterie & Uhrzeit)
        # 1. WLAN Symbol (Nord8 Cyan wenn aktiv, Nord3 wenn getrennt)
        is_wifi = self.hardware.get_wifi_status()
        wifi_col = NORD8 if is_wifi else NORD3
        wx, wy = 780, 20
        pygame.draw.circle(self.screen, wifi_col, (wx + 10, wy + 16), 2)
        pygame.draw.arc(self.screen, wifi_col, (wx + 5, wy + 9, 10, 10), 0.785, 2.356, 2)
        pygame.draw.arc(self.screen, wifi_col, (wx + 1, wy + 3, 18, 18), 0.785, 2.356, 2)

        # 2. Batterie
        bat_cap, is_charging = self.hardware.get_battery_info()
        bat_color = NORD14 if bat_cap > 20 else NORD11
        bx, by = 835, 20
        pygame.draw.rect(self.screen, bat_color, (bx, by, 22, 14), width=1, border_radius=2)
        pygame.draw.rect(self.screen, bat_color, (bx + 22, by + 3, 2, 8))
        fill_w = max(2, int(18 * (bat_cap / 100.0)))
        pygame.draw.rect(self.screen, bat_color, (bx + 2, by + 2, fill_w, 10))

        charge_symbol = "⚡ " if is_charging else ""
        bat_surf = self._load_font(12, bold=True).render(f"{charge_symbol}{bat_cap}%", True, bat_color)
        self.screen.blit(bat_surf, (bx + 28, 18))

        # 3. Uhrzeit
        time_str = self.hardware.get_time_str()
        time_surf = self._load_font(18, bold=True).render(time_str, True, NORD6)
        self.screen.blit(time_surf, (940, 16))

    # =========================================================================
    # RENDERER 3: RADIO MODE (THE QUEEN'S FREQUENCY - 2-CARD STAGE)
    # =========================================================================
    def draw_radio_dashboard(self):
        self.screen.fill(NORD0)
        self.draw_top_bar(custom_title="Station North")

        track = self.playlist[self.current_idx] if self.current_idx < len(self.playlist) else {}
        title = track.get("title", "Unknown Title")
        artist = track.get("artist", "Unknown Artist")

        # 1. Obere Karte: Visualizer Bühne
        card1_x = 20
        card1_y = 62
        card1_w = 984
        card1_h = 440
        pygame.draw.rect(self.screen, NORD1, (card1_x, card1_y, card1_w, card1_h), border_radius=16)
        pygame.draw.rect(self.screen, NORD2, (card1_x, card1_y, card1_w, card1_h), width=1, border_radius=16)

        cx = card1_x + card1_w // 2

        if self.is_station_drop:
            drop_s = self._load_font(36, bold=True).render("STATION NORTH IDENT", True, NORD8)
            self.screen.blit(drop_s, (cx - drop_s.get_width() // 2, card1_y + 80))
            sub_s = self._load_font(18, bold=True).render("LIVE JINGLE BROADCAST", True, NORD13)
            self.screen.blit(sub_s, (cx - sub_s.get_width() // 2, card1_y + 128))
        else:
            sn_s = self._load_font(58, bold=True).render("SN", True, NORD6)
            self.screen.blit(sn_s, (cx - sn_s.get_width() // 2, card1_y + 44))

            sub_sn = self._load_font(13).render("Station North", True, NORD4)
            self.screen.blit(sub_sn, (cx - sub_sn.get_width() // 2, card1_y + 104))

            stream_s = self._load_font(20, bold=True).render("SN-RADIO AUDIO STREAM", True, NORD8)
            self.screen.blit(stream_s, (cx - stream_s.get_width() // 2, card1_y + 138))

        # Vollbreiter organischer Wellen-Visualizer mit bunten Kappen
        vis_x = card1_x + 14
        vis_w = card1_w - 28
        vis_y = card1_y + 180
        vis_h = 246
        self.visualizer.update(is_active=self.is_playing)
        self.visualizer.draw(self.screen, x=vis_x, y=vis_y, width=vis_w, max_h=vis_h)

        # 2. Untere Karte: Song-Titel, Artist & 5 Große Chunky Buttons
        card2_x = 20
        card2_y = 514
        card2_w = 984
        card2_h = 238
        pygame.draw.rect(self.screen, NORD1, (card2_x, card2_y, card2_w, card2_h), border_radius=16)
        pygame.draw.rect(self.screen, NORD2, (card2_x, card2_y, card2_w, card2_h), width=1, border_radius=16)

        # Song-Titel zentriert
        disp_title = self.station_drop_title if self.is_station_drop else title
        title_font = self._load_font(26, bold=True)
        if len(disp_title) > 38:
            title_font = self._load_font(22, bold=True)
        t_surf = title_font.render(disp_title, True, NORD6)
        self.screen.blit(t_surf, (cx - t_surf.get_width() // 2, card2_y + 16))

        # Interpret zentriert
        disp_artist = "The Queen's Frequency" if self.is_station_drop else artist
        a_surf = self._load_font(17).render(disp_artist, True, NORD4)
        self.screen.blit(a_surf, (cx - a_surf.get_width() // 2, card2_y + 48))

        # 5 Große Chunky Buttons
        btn_area_x = card2_x + 16
        btn_area_w = card2_w - 32
        btn_y = card2_y + 82
        self.draw_5_button_cockpit(self.screen, btn_area_x, btn_y, btn_area_w, height=140)

    # =========================================================================
    # RENDERER 4: TV MODE (TELEVISION BROADCAST - 2-CARD STAGE)
    # =========================================================================
    def draw_tv_dashboard(self):
        self.screen.fill(NORD0)
        self.draw_top_bar(custom_title="Station North")

        track = self.playlist[self.current_idx] if self.current_idx < len(self.playlist) else {}
        title = track.get("title", "Unknown Title")
        artist = track.get("artist", "Unknown Artist")
        yt_id = track.get("youtubeId", "")

        # 1. Obere Karte: Großes Video-Thumbnail & Fullscreen-Trigger
        card1_x = 20
        card1_y = 62
        card1_w = 984
        card1_h = 440
        card1_rect = pygame.Rect(card1_x, card1_y, card1_w, card1_h)

        pygame.draw.rect(self.screen, NORD1, card1_rect, border_radius=16)
        pygame.draw.rect(self.screen, NORD2, card1_rect, width=1, border_radius=16)

        thumb_surf = self.thumb_mgr.get_thumbnail(yt_id, title, size=(card1_w, card1_h))
        self.screen.blit(thumb_surf, (card1_x, card1_y))

        # Dezent abgedunkelter Scrim für maximale Textlesbarkeit
        scrim = pygame.Surface((card1_w, card1_h), pygame.SRCALPHA)
        scrim.fill((0, 0, 0, 85))
        self.screen.blit(scrim, (card1_x, card1_y))

        cx = card1_x + card1_w // 2

        # "PRESS for FULLSCREEN" zentriert
        p_font = self._load_font(36, bold=True)
        f_font = self._load_font(56, bold=True)

        p_sh = p_font.render("PRESS for", True, (15, 18, 24))
        f_sh = f_font.render("FULLSCREEN", True, (15, 18, 24))
        self.screen.blit(p_sh, (cx - p_sh.get_width() // 2 + 2, card1_y + 142))
        self.screen.blit(f_sh, (cx - f_sh.get_width() // 2 + 3, card1_y + 192))

        p_s = p_font.render("PRESS for", True, NORD6)
        f_s = f_font.render("FULLSCREEN", True, NORD6)
        self.screen.blit(p_s, (cx - p_s.get_width() // 2, card1_y + 140))
        self.screen.blit(f_s, (cx - f_s.get_width() // 2, card1_y + 190))

        # SN Wasserzeichen unten rechts
        if self.logo_large:
            wm_w, wm_h = 76, 76
            wm = pygame.transform.smoothscale(self.logo_large, (wm_w, wm_h))
            wm.set_alpha(165)
            self.screen.blit(wm, (card1_x + card1_w - wm_w - 24, card1_y + card1_h - wm_h - 22))
            wm_txt = self._load_font(12, bold=True).render("Station North", True, (220, 220, 220))
            wm_txt.set_alpha(165)
            self.screen.blit(wm_txt, (card1_x + card1_w - wm_txt.get_width() - 24, card1_y + card1_h - 18))

        # 2. Untere Karte: Titel, Artist & 5 Große Chunky Buttons
        card2_x = 20
        card2_y = 514
        card2_w = 984
        card2_h = 238
        pygame.draw.rect(self.screen, NORD1, (card2_x, card2_y, card2_w, card2_h), border_radius=16)
        pygame.draw.rect(self.screen, NORD2, (card2_x, card2_y, card2_w, card2_h), width=1, border_radius=16)

        title_font = self._load_font(26, bold=True)
        if len(title) > 38:
            title_font = self._load_font(22, bold=True)
        t_surf = title_font.render(title, True, NORD6)
        self.screen.blit(t_surf, (cx - t_surf.get_width() // 2, card2_y + 16))

        a_surf = self._load_font(17).render(artist, True, NORD4)
        self.screen.blit(a_surf, (cx - a_surf.get_width() // 2, card2_y + 48))

        btn_area_x = card2_x + 16
        btn_area_w = card2_w - 32
        btn_y = card2_y + 82
        self.draw_5_button_cockpit(self.screen, btn_area_x, btn_y, btn_area_w, height=140)

    def _trigger_cockpit_action(self, idx: int):
        """Executes the action of the focused button (Android TV navigation model)"""
        if idx == 0:
            # Fullscreen Mode [ ]
            if self.state == STATE_RADIO:
                self.is_radio_zen_mode = not self.is_radio_zen_mode
                self.radio_osd_visible = True
                self.radio_osd_last_interaction = time.time()
            elif self.state == STATE_TV:
                self.launch_video_playback(self.current_idx, manual_trigger=True)

        elif idx == 1:
            # Previous Track
            self.current_idx = self.shuffle_mgr.step_prev()
            if self.state == STATE_RADIO:
                self.trigger_play_track_async(self.current_idx)

        elif idx == 2:
            # Play / Pause
            if self.state == STATE_RADIO:
                if self.is_playing:
                    self.stop_audio()
                else:
                    self.trigger_play_track_async(self.current_idx)
            elif self.state == STATE_TV:
                self.launch_video_playback(self.current_idx, manual_trigger=True)

        elif idx == 3:
            # Next Track (increments station jingle counter!)
            self.station_mgr.increment_counter()
            self.current_idx = self.shuffle_mgr.advance_next()
            if self.state == STATE_RADIO:
                self.trigger_play_track_async(self.current_idx)

        elif idx == 4:
            # Repeat Loop Toggle
            self.shuffle_mgr.toggle_repeat()

    # =========================================================================
    # RENDERER 5: THE CHRONICLES (AUDIO-BOX LINKS UNTER BILD, TEXT RECHTS)
    # =========================================================================
    def draw_chronicles_screen(self):
        self.screen.fill(NORD0)
        self.draw_top_bar(custom_title="THE CHRONICLES")

        if not self.chronicles_data:
            msg_s = self.font_hero.render("No Chronicles Data Found (assets/comic)", True, NORD11)
            self.screen.blit(msg_s, ((SCREEN_WIDTH - msg_s.get_width()) // 2, 350))
            self.draw_bottom_bar(custom_controls="[B] Back to Main Menu")
            return

        item = self.chronicles_data[self.chronicles_idx]
        image_name = item.get("image", "")
        chapter_name = item.get("chapter", "Chapter 1")
        text_content = item.get("text", "")
        panel_id = item.get("id", self.chronicles_idx + 1)

        col1_x = 40
        col1_w = 440
        panel_y = 68
        panel_h = 490
        panel_rect = pygame.Rect(col1_x, panel_y, col1_w, panel_h)
        pygame.draw.rect(self.screen, NORD1, panel_rect, border_radius=16)
        pygame.draw.rect(self.screen, NORD2, panel_rect, width=1, border_radius=16)

        if image_name not in self.chronicles_img_cache:
            img_paths = [
                Path("assets/comic") / image_name,
                Path("/roms/ports/snfetchplayer/assets/comic") / image_name
            ]
            loaded_surf = None
            for ip in img_paths:
                if ip.exists():
                    try:
                        raw = pygame.image.load(str(ip))
                        if pygame.display.get_surface():
                            raw = raw.convert()
                        rw, rh = raw.get_size()
                        scale = min((col1_w - 24) / rw, (panel_h - 24) / rh)
                        target_size = (int(rw * scale), int(rh * scale))
                        scaled = pygame.transform.smoothscale(raw, target_size)
                        loaded_surf = scaled
                        break
                    except Exception:
                        pass
            if loaded_surf:
                self.chronicles_img_cache[image_name] = loaded_surf

        if image_name in self.chronicles_img_cache:
            surf = self.chronicles_img_cache[image_name]
            px = col1_x + (col1_w - surf.get_width()) // 2
            py = panel_y + (panel_h - surf.get_height()) // 2
            self.screen.blit(surf, (px, py))

        # Audio Box direkt unter dem Comic-Panel
        abox_y = panel_y + panel_h + 16
        abox_h = 88
        abox_rect = pygame.Rect(col1_x, abox_y, col1_w, abox_h)
        pygame.draw.rect(self.screen, NORD1, abox_rect, border_radius=12)
        pygame.draw.rect(self.screen, NORD8 if self.chronicles_playing else NORD2, abox_rect, width=2 if self.chronicles_playing else 1, border_radius=12)

        astat_text = "❚❚ NARRATION PLAYING" if self.chronicles_playing else "▶ READ ALOUD [A] / [Start]"
        astat_col = NORD14 if self.chronicles_playing else NORD8
        astat_s = self._load_font(16, bold=True).render(astat_text, True, astat_col)
        self.screen.blit(astat_s, (col1_x + 18, abox_y + 16))

        audio_name = f"Voice Audio #{panel_id:03d} • Queen Faith"
        aname_s = self._load_font(14).render(audio_name, True, NORD4)
        self.screen.blit(aname_s, (col1_x + 18, abox_y + 48))

        # Rechte Spalte: Fließtext
        col2_x = 504
        col2_w = 480
        col2_y = 68
        col2_h = 594

        tbox_rect = pygame.Rect(col2_x, col2_y, col2_w, col2_h)
        pygame.draw.rect(self.screen, NORD1, tbox_rect, border_radius=16)
        pygame.draw.rect(self.screen, NORD2, tbox_rect, width=1, border_radius=16)

        c_badge = self._load_font(15, bold=True).render(f"{chapter_name} • Panel {panel_id}/{len(self.chronicles_data)}", True, NORD13)
        self.screen.blit(c_badge, (col2_x + 24, col2_y + 22))

        # Word wrap text
        words = text_content.split()
        lines = []
        cur_line = []
        for w in words:
            test_line = " ".join(cur_line + [w])
            if self.font_body.size(test_line)[0] < (col2_w - 48):
                cur_line.append(w)
            else:
                lines.append(" ".join(cur_line))
                cur_line = [w]
        if cur_line:
            lines.append(" ".join(cur_line))

        ty = col2_y + 68
        for l in lines[:16]:
            lsurf = self.font_body.render(l, True, NORD6)
            self.screen.blit(lsurf, (col2_x + 24, ty))
            ty += 28

        self.draw_bottom_bar(custom_controls="[◄/►] Page / Panel   [A/Start] Read Aloud   [B] Main Menu")

    # =========================================================================
    # RENDERER 6: SETTINGS SCREEN
    # =========================================================================
    def draw_settings_screen(self):
        self.screen.fill(NORD0)
        self.draw_top_bar(custom_title="SETTINGS & ASSET MANAGEMENT")

        # Queen Directives Header Quote (Groesser & Deutlicher)
        q_header = "\"A well-maintained machine rules without interruption. Manage storage & updates.\" — Her Majesty Queen Directives"
        qh_s = self._load_font(14, bold=True).render(q_header, True, NORD13)
        self.screen.blit(qh_s, ((SCREEN_WIDTH - qh_s.get_width()) // 2, 60))

        # --- LINKE SPALTE: EINSTELLUNGEN & REGLER (x=30, w=480) ---
        settings_items = [
            ("Radio Active Playlist", self.available_playlists[self.radio_playlist_idx]["title"] if self.available_playlists else "Standard"),
            ("TV Active Playlist", self.available_playlists[self.tv_playlist_idx]["title"] if self.available_playlists else "Standard"),
            ("Jingle Rotation Frequency", f"Every {self.station_mgr.rotation_interval} Songs" if self.station_mgr.rotation_interval > 0 else "OFF"),
            ("Single-Track Repeat Loop", "ENABLED (Repeat One)" if self.shuffle_mgr.is_repeat_mode else "DISABLED (Shuffle)"),
            ("Master Audio Volume", f"{self.hardware.get_master_volume()}%"),
            ("Screen Backlight Brightness", f"{self.hardware.get_brightness()}%"),
            ("Re-Scan Local Asset Storage", "Press [A] to Trigger")
        ]

        start_y = 82
        row_h = 66
        box_w = 480

        for i, (label, val) in enumerate(settings_items):
            ry = start_y + i * (row_h + 8)
            r_rect = pygame.Rect(30, ry, box_w, row_h)
            is_sel = (i == self.settings_cursor and self.settings_column == 0)

            bg_col = NORD1 if is_sel else (36, 41, 51)
            b_col = NORD8 if is_sel else NORD2
            pygame.draw.rect(self.screen, bg_col, r_rect, border_radius=12)
            pygame.draw.rect(self.screen, b_col, r_rect, width=2 if is_sel else 1, border_radius=12)

            l_col = NORD8 if is_sel else NORD6
            l_surf = self._load_font(18, bold=True).render(label, True, l_col)
            self.screen.blit(l_surf, (r_rect.x + 20, ry + 12))

            val_col = NORD14 if "ENABLED" in val or "%" in val else NORD13
            val_surf = self._load_font(15, bold=True).render(val, True, val_col)
            self.screen.blit(val_surf, (r_rect.x + 20, ry + 36))

            if is_sel:
                pygame.draw.rect(self.screen, NORD8, (34, ry + 6, 6, row_h - 12), border_radius=3)

        if self.settings_feedback_msg and (time.time() - self.settings_feedback_time < 3.0):
            fb_s = self._load_font(14, bold=True).render(self.settings_feedback_msg, True, NORD14)
            self.screen.blit(fb_s, (30 + (box_w - fb_s.get_width()) // 2, start_y + len(settings_items) * (row_h + 8) + 6))

        # --- RECHTE SPALTE: HANDBUCH, TV-STEUERUNG & CURATOR GUIDE (x=530, w=464) ---
        guide_x = 530
        guide_y = 82
        guide_w = 464
        guide_h = 612
        guide_rect = pygame.Rect(guide_x, guide_y, guide_w, guide_h)

        is_guide_focused = (self.settings_column == 1)
        pygame.draw.rect(self.screen, NORD1, guide_rect, border_radius=16)
        pygame.draw.rect(self.screen, NORD8 if is_guide_focused else NORD2, guide_rect, width=2 if is_guide_focused else 1, border_radius=16)

        # Card Header
        gh_s = self._load_font(19, bold=True).render("STATION NORTH HANDBOOK", True, NORD8)
        self.screen.blit(gh_s, (guide_x + 20, guide_y + 14))

        hint_text = "▲/▼ Scrollen • ◄/B Zurück" if is_guide_focused else "[X] oder [A] zum Scrollen"
        hint_col = NORD14 if is_guide_focused else NORD4
        hint_s = self._load_font(13, bold=True).render(hint_text, True, hint_col)
        self.screen.blit(hint_s, (guide_x + guide_w - hint_s.get_width() - 20, guide_y + 18))

        pygame.draw.line(self.screen, NORD2, (guide_x + 18, guide_y + 44), (guide_x + guide_w - 18, guide_y + 44), 1)

        # Scrollbare Inhaltsoberflaeche fuer groessere, perfekt lesbare Schrift
        content_w = guide_w - 36
        content_h = 760
        content_surf = pygame.Surface((content_w, content_h), pygame.SRCALPHA)
        content_surf.fill((0, 0, 0, 0))

        gy = 4

        # Section 1: TV Player Controls (4 Funktionen)
        t_sec = self._load_font(17, bold=True).render("📺 TV-PLAYER (4 FUNKTIONEN):", True, NORD7)
        content_surf.blit(t_sec, (4, gy))
        gy += 28

        ctrl_lines = [
            ("START", "Play / Pause Video (Toggle)"),
            ("B", "Sofortiger Exit & Zurück zum Menü"),
            ("◄ / ►", "Vorheriges / Nächstes Video (D-Pad & Stick)"),
            ("X / Y", "Single-Track Repeat Loop (Repeat One)")
        ]
        for key_btn, key_desc in ctrl_lines:
            kb_s = self._load_font(15, bold=True).render(f"[{key_btn}]", True, NORD13)
            kd_s = self._load_font(15).render(key_desc, True, NORD6)
            content_surf.blit(kb_s, (8, gy))
            content_surf.blit(kd_s, (88, gy))
            gy += 26

        gy += 14
        pygame.draw.line(content_surf, NORD2, (4, gy), (content_w - 4, gy), 1)
        gy += 14

        # Section 2: Eigene Playlists & Medien
        m_sec = self._load_font(17, bold=True).render("📁 EIGENE MEDIEN & LISTEN:", True, NORD12)
        content_surf.blit(m_sec, (4, gy))
        gy += 28

        msg1 = [
            "Eigene Musik, Videos & Playlisten einfach im Ordner",
            "/playlists/ auf der SD-Karte hinterlegen.",
            "Unterstützt YouTube Streams, MP4/MKV Videos",
            "sowie lokale MP3- und FLAC-Audiodateien."
        ]
        for line in msg1:
            ls = self._load_font(15).render(line, True, NORD4)
            content_surf.blit(ls, (8, gy))
            gy += 24

        gy += 14
        pygame.draw.line(content_surf, NORD2, (4, gy), (content_w - 4, gy), 1)
        gy += 14

        # Section 3: Android App & Curator
        c_sec = self._load_font(17, bold=True).render("📱 ANDROID VERSION & CURATOR:", True, NORD14)
        content_surf.blit(c_sec, (4, gy))
        gy += 28

        msg2 = [
            "Die Station North Android-App besitzt einen CURATOR!",
            "Erstelle & kuratiere Playlisten bequem am Smartphone,",
            "um sie direkt per JSON für deinen dArkOS Handheld",
            "zu exportieren und zu synchronisieren."
        ]
        for line in msg2:
            ls = self._load_font(15).render(line, True, NORD4)
            content_surf.blit(ls, (8, gy))
            gy += 24

        gy += 14
        pygame.draw.line(content_surf, NORD2, (4, gy), (content_w - 4, gy), 1)
        gy += 14

        # Section 4: Radio Vollbild OSD
        r_sec = self._load_font(17, bold=True).render("📻 RADIO VOLLBILD ON-SCREEN-MENÜ:", True, NORD8)
        content_surf.blit(r_sec, (4, gy))
        gy += 28

        msg3 = [
            "Mit [ ] / [X] startet der Vollbild-Visualizer.",
            "Das 5-Button-Menü blendet nach 4 Sek. automatisch aus.",
            "Jede Taste weckt das OSD auf • [B] beendet Vollbild."
        ]
        for line in msg3:
            ls = self._load_font(15).render(line, True, NORD4)
            content_surf.blit(ls, (8, gy))
            gy += 24

        # Content auf den Bildschirm clippen
        clip_h = guide_h - 60
        self.settings_guide_max_scroll = max(0, content_h - clip_h + 20)
        self.screen.blit(content_surf, (guide_x + 16, guide_y + 48), area=pygame.Rect(0, self.settings_guide_scroll_y, content_w, clip_h))

        # Vertikaler Scrollbalken auf der rechten Seite der Handbook-Karte
        track_h = clip_h - 16
        pygame.draw.rect(self.screen, (46, 52, 64), (guide_x + guide_w - 12, guide_y + 54, 4, track_h), border_radius=2)
        if self.settings_guide_max_scroll > 0:
            thumb_ratio = clip_h / float(content_h)
            thumb_h = max(24, int(track_h * thumb_ratio))
            scroll_pct = self.settings_guide_scroll_y / float(self.settings_guide_max_scroll)
            thumb_y = guide_y + 54 + int((track_h - thumb_h) * scroll_pct)
            thumb_col = NORD8 if is_guide_focused else NORD2
            pygame.draw.rect(self.screen, thumb_col, (guide_x + guide_w - 13, thumb_y, 6, thumb_h), border_radius=3)

        ctrl_text = "[▲/▼] Scrollen   [◄/B/X] Zurück zu Einstellungen" if is_guide_focused else "[▲/▼] Auswahl   [◄/►] Wert ändern   [X/A] Handbuch lesen   [Select/B] Zurück"
        self.draw_bottom_bar(custom_controls=ctrl_text)

    # =========================================================================
    # RENDERER 7: BOTTOM BAR
    # =========================================================================
    def draw_bottom_bar(self, custom_controls: Optional[str] = None):
        by = SCREEN_HEIGHT - 52
        pygame.draw.rect(self.screen, COLOR_BAR_BG, (0, by, SCREEN_WIDTH, 52))
        pygame.draw.line(self.screen, NORD2, (0, by), (SCREEN_WIDTH, by), 1)

        controls = custom_controls or "[◄/►] Track Skip   [Start] Pause   [X] Fullscreen   [Y] Repeat   [Select] Settings   [B] Back"
        ctrl_surf = self.font_small.render(controls, True, NORD6)
        self.screen.blit(ctrl_surf, (24, by + 16))

        ver_surf = self.font_small.render("Station North • dArkOS Edition v5.0", True, NORD4)
        self.screen.blit(ver_surf, (SCREEN_WIDTH - 24 - ver_surf.get_width(), by + 16))

    # =========================================================================
    # EVENT LOOP & EXECUTION
    # =========================================================================
    def run(self):
        running = True

        while running:
            self.clock.tick(60)

            # Auto-Advance in Radio Mode (shielded while jingle plays or resolver runs)
            if (self.state == STATE_RADIO and self.audio_proc and 
                self.audio_proc.poll() is not None and 
                not self.is_station_drop and not self.is_resolving):
                
                self.station_mgr.increment_counter()
                if not self.shuffle_mgr.is_repeat_mode:
                    self.current_idx = self.shuffle_mgr.advance_next()
                self.trigger_play_track_async(self.current_idx)

            # Auto-Advance in Chronicles
            if self.state == STATE_CHRONICLES and self.chronicles_proc and self.chronicles_proc.poll() is not None:
                self.chronicles_playing = False
                if self.chronicles_idx < len(self.chronicles_data) - 1:
                    self.chronicles_idx += 1
                    self.toggle_chronicles_audio()

            # Universal PortMaster Kill: SELECT (Tab) + START (P)
            keys = pygame.key.get_pressed()
            if (keys[pygame.K_TAB] and keys[pygame.K_p]) or (keys[pygame.K_p] and keys[pygame.K_TAB]):
                self.stop_audio()
                self.stop_chronicles_audio()
                pygame.quit()
                sys.exit(0)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    # Global Settings Toggle [Select] (Tab / S)
                    if event.key in (pygame.K_TAB, pygame.K_s):
                        if self.state == STATE_SETTINGS:
                            self.state = self.previous_state
                        else:
                            self.previous_state = self.state
                            self.state = STATE_SETTINGS
                        continue

                    # --- SPLASH SCREEN ---
                    if self.state == STATE_SPLASH:
                        if event.key in (pygame.K_LEFT, pygame.K_UP):
                            self.splash_cursor = (self.splash_cursor - 1) % 3
                        elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
                            self.splash_cursor = (self.splash_cursor + 1) % 3
                        elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER, pygame.K_p, pygame.K_a):
                            if self.splash_cursor == 0:
                                self.show_loading_screen("RADIO MODE", "Loading Station North Radio...")
                                self.state = STATE_RADIO
                                self._load_active_playlist(is_tv=False)
                                self.trigger_play_track_async(self.current_idx)
                            elif self.splash_cursor == 1:
                                self.show_loading_screen("STATION NORTH TV", "Starting Television Broadcast...")
                                self._load_active_playlist(is_tv=True)
                                self.launch_video_playback(self.current_idx, manual_trigger=True)
                                self.state = STATE_SPLASH
                            elif self.splash_cursor == 2:
                                self.show_loading_screen("THE CHRONICLES", "Loading Comic & Voice Lore...")
                                self.state = STATE_CHRONICLES
                        elif event.key in (pygame.K_ESCAPE, pygame.K_q, pygame.K_BACKSPACE, pygame.K_b):
                            running = False

                    # --- RADIO MODE (ANDROID TV D-PAD FOCUS CURSOR) ---
                    elif self.state == STATE_RADIO:
                        if self.is_radio_zen_mode:
                            # [B] / ESC / Backspace: Vollbild sofort beenden & zurueck zum Dashboard
                            if event.key in (pygame.K_ESCAPE, pygame.K_q, pygame.K_BACKSPACE, pygame.K_b):
                                self.is_radio_zen_mode = False
                                self.radio_osd_visible = True
                                continue

                            # Wenn OSD ausgeblendet war, weckt JEDE Taste (ausser B) das Menue auf
                            if not self.radio_osd_visible:
                                self.radio_osd_visible = True
                                self.radio_osd_last_interaction = time.time()
                                continue

                            # Wenn OSD sichtbar ist, Inaktivitaets-Timer aktualisieren
                            self.radio_osd_last_interaction = time.time()

                            if event.key == pygame.K_LEFT:
                                self.cockpit_focus_idx = (self.cockpit_focus_idx - 1) % 5
                            elif event.key == pygame.K_RIGHT:
                                self.cockpit_focus_idx = (self.cockpit_focus_idx + 1) % 5
                            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER, pygame.K_a):
                                self._trigger_cockpit_action(self.cockpit_focus_idx)
                            elif event.key in (pygame.K_f, pygame.K_x):
                                self.is_radio_zen_mode = False
                            elif event.key in (pygame.K_p, pygame.K_PAUSE):
                                self._trigger_cockpit_action(2)
                            elif event.key == pygame.K_y:
                                self._trigger_cockpit_action(4)
                            continue

                        if event.key == pygame.K_LEFT:
                            self.cockpit_focus_idx = (self.cockpit_focus_idx - 1) % 5
                        elif event.key == pygame.K_RIGHT:
                            self.cockpit_focus_idx = (self.cockpit_focus_idx + 1) % 5
                        elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER, pygame.K_a):
                            self._trigger_cockpit_action(self.cockpit_focus_idx)
                        elif event.key in (pygame.K_ESCAPE, pygame.K_q, pygame.K_BACKSPACE, pygame.K_b):
                            self.stop_audio()
                            self.state = STATE_SPLASH
                        # Secondary physical hotkeys
                        elif event.key in (pygame.K_f, pygame.K_x):
                            self.is_radio_zen_mode = True
                            self.radio_osd_visible = True
                            self.radio_osd_last_interaction = time.time()
                        elif event.key in (pygame.K_p, pygame.K_PAUSE):
                            self._trigger_cockpit_action(2)
                        elif event.key == pygame.K_y:
                            self._trigger_cockpit_action(4)

                    # --- TV MODE (ANDROID TV D-PAD FOCUS CURSOR) ---
                    elif self.state == STATE_TV:
                        if event.key == pygame.K_LEFT:
                            self.cockpit_focus_idx = (self.cockpit_focus_idx - 1) % 5
                        elif event.key == pygame.K_RIGHT:
                            self.cockpit_focus_idx = (self.cockpit_focus_idx + 1) % 5
                        elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER, pygame.K_a):
                            self._trigger_cockpit_action(self.cockpit_focus_idx)
                        elif event.key in (pygame.K_ESCAPE, pygame.K_q, pygame.K_BACKSPACE, pygame.K_b):
                            self.state = STATE_SPLASH
                        # Secondary physical hotkeys: [X] Launches Fullscreen Video
                        elif event.key in (pygame.K_f, pygame.K_x):
                            self.launch_video_playback(self.current_idx, manual_trigger=True)
                        elif event.key in (pygame.K_p, pygame.K_PAUSE):
                            self._trigger_cockpit_action(2)
                        elif event.key == pygame.K_y:
                            self._trigger_cockpit_action(4)

                    # --- CHRONICLES ---
                    elif self.state == STATE_CHRONICLES:
                        if event.key == pygame.K_LEFT:
                            if self.chronicles_idx > 0:
                                self.stop_chronicles_audio()
                                self.chronicles_idx -= 1
                        elif event.key == pygame.K_RIGHT:
                            if self.chronicles_idx < len(self.chronicles_data) - 1:
                                self.stop_chronicles_audio()
                                self.chronicles_idx += 1
                        elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER, pygame.K_p, pygame.K_a):
                            self.toggle_chronicles_audio()
                        elif event.key in (pygame.K_ESCAPE, pygame.K_q, pygame.K_BACKSPACE, pygame.K_b):
                            self.stop_chronicles_audio()
                            self.state = STATE_SPLASH

                    # --- SETTINGS ---
                    elif self.state == STATE_SETTINGS:
                        if self.settings_column == 0:
                            if event.key == pygame.K_UP:
                                self.settings_cursor = (self.settings_cursor - 1) % 7
                            elif event.key == pygame.K_DOWN:
                                self.settings_cursor = (self.settings_cursor + 1) % 7
                            elif event.key == pygame.K_LEFT:
                                self._adjust_setting(delta=-1)
                            elif event.key == pygame.K_RIGHT:
                                self._adjust_setting(delta=1)
                            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER, pygame.K_a):
                                if self.settings_cursor == 6:
                                    self._execute_setting_action()
                                else:
                                    self.settings_column = 1
                            elif event.key in (pygame.K_f, pygame.K_x, pygame.K_y, pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                                self.settings_column = 1
                            elif event.key in (pygame.K_ESCAPE, pygame.K_q, pygame.K_BACKSPACE, pygame.K_b):
                                self.state = self.previous_state
                        else:
                            # Column 1: Handbook scrolling
                            if event.key == pygame.K_UP:
                                self.settings_guide_scroll_y = max(0, self.settings_guide_scroll_y - 36)
                            elif event.key == pygame.K_DOWN:
                                self.settings_guide_scroll_y = min(self.settings_guide_max_scroll, self.settings_guide_scroll_y + 36)
                            elif event.key in (pygame.K_LEFT, pygame.K_b, pygame.K_ESCAPE, pygame.K_q, pygame.K_BACKSPACE, pygame.K_f, pygame.K_x, pygame.K_y, pygame.K_a, pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                                self.settings_column = 0

            if self.state == STATE_SPLASH:
                self.draw_splash_screen()
            elif self.state == STATE_RADIO:
                if self.is_radio_zen_mode:
                    self.draw_radio_zen_mode()
                else:
                    self.draw_radio_dashboard()
            elif self.state == STATE_TV:
                self.draw_tv_dashboard()
            elif self.state == STATE_CHRONICLES:
                self.draw_chronicles_screen()
            elif self.state == STATE_SETTINGS:
                self.draw_settings_screen()

            pygame.display.flip()

        self.stop_audio()
        self.stop_chronicles_audio()
        pygame.quit()
        sys.exit(0)

    # --- SETTINGS LOGIC ---
    def _adjust_setting(self, delta: int):
        if self.settings_cursor == 0:
            if self.available_playlists:
                self.radio_playlist_idx = (self.radio_playlist_idx + delta) % len(self.available_playlists)
                self._load_active_playlist(is_tv=False)
        elif self.settings_cursor == 1:
            if self.available_playlists:
                self.tv_playlist_idx = (self.tv_playlist_idx + delta) % len(self.available_playlists)
                self._load_active_playlist(is_tv=True)
        elif self.settings_cursor == 2:
            self.station_mgr.rotation_interval = max(0, min(10, self.station_mgr.rotation_interval + delta))
        elif self.settings_cursor == 3:
            self.shuffle_mgr.toggle_repeat()
        elif self.settings_cursor == 4:
            curr_v = self.hardware.get_master_volume()
            self.hardware.set_master_volume(curr_v + delta * 5)
        elif self.settings_cursor == 5:
            curr_b = self.hardware.get_brightness()
            self.hardware.set_brightness(curr_b + delta * 5)

    def _execute_setting_action(self):
        if self.settings_cursor == 3:
            rep = self.shuffle_mgr.toggle_repeat()
            self.settings_feedback_msg = f"Single-Track Repeat Loop: {'ON' if rep else 'OFF'}"
            self.settings_feedback_time = time.time()
        elif self.settings_cursor == 6:
            self.station_mgr._scan_station_assets()
            self._discover_playlists()
            j, t, c, tot, _ = self.get_asset_stats()
            self.settings_feedback_msg = f"Asset Storage Synchronized ({tot} items found)!"
            self.settings_feedback_time = time.time()
