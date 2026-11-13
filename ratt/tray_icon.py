"""RATT System Tray Icon: the RATT logo near the clock with a small menu (pystray).

Dynamically reflects the ON/OFF toggle state:
  - Active (ON): Cyan RATT icon + menu option "Pause RATT (Release Keyboard)"
  - Paused (OFF): Grey/Amber RATT icon + menu option "Resume RATT"
"""
import os
import threading

import pystray
from PIL import Image, ImageDraw
from pystray import Menu, MenuItem

from ratt import native
from ratt.config import config


def _build_tray_image(enabled: bool) -> Image.Image:
    """Create the system tray icon: Cyan when active (ON), Grey/Amber when paused (OFF)."""
    icon_path = os.path.join(native.assets_dir(), "ratt_icon.png")
    try:
        base = Image.open(icon_path).convert("RGBA").resize((64, 64), Image.LANCZOS)
    except Exception:
        base = Image.new("RGBA", (64, 64), (0, 191, 255, 255))

    if enabled:
        # Active Cyan icon with a crisp Cyan status dot in the bottom-right corner
        out = base.copy()
        draw = ImageDraw.Draw(out)
        draw.ellipse((44, 44, 62, 62), fill=(0, 229, 255, 255), outline=(10, 25, 41, 255), width=2)
        return out

    # Paused state: convert icon body to muted Slate-Grey and draw an Amber pause badge
    pixels = base.load()
    w, h = base.size
    paused = Image.new("RGBA", (w, h))
    p_px = paused.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            lum = int(0.299 * r + 0.587 * g + 0.114 * b)
            # Slate-grey tint (#64748B / #94A3B8)
            sr = min(255, int(lum * 0.55 + 45))
            sg = min(255, int(lum * 0.60 + 52))
            sb = min(255, int(lum * 0.68 + 64))
            p_px[x, y] = (sr, sg, sb, a)

    draw = ImageDraw.Draw(paused)
    # Amber badge (#FFC107 / #FF9800) in bottom-right corner indicating paused state
    draw.ellipse((42, 42, 62, 62), fill=(255, 179, 0, 255), outline=(30, 41, 59, 255), width=2)
    draw.rectangle((48, 47, 51, 57), fill=(30, 41, 59, 255))
    draw.rectangle((53, 47, 56, 57), fill=(30, 41, 59, 255))
    return paused


class TrayIcon:
    def __init__(self, root, app):
        self.root = root
        self.app = app
        self._icon = None

    def start(self):
        """Run the tray icon in a background thread."""
        image = _build_tray_image(config.enabled)
        title = self._tray_title()
        self._icon = pystray.Icon("RATT", image, title, self._build_menu())
        threading.Thread(target=self._icon.run, daemon=True).start()

    def _tray_title(self) -> str:
        state_str = "ON (Active)" if config.enabled else "OFF (Paused — Keyboard Released)"
        return f"RATT v{config.VERSION} \u2014 {state_str}"

    def update_state(self):
        """Refresh the tray icon color (Cyan vs Grey/Amber), tooltip, and menu text."""
        if not self._icon:
            return
        try:
            self._icon.icon = _build_tray_image(config.enabled)
            self._icon.title = self._tray_title()
            self._icon.update_menu()
        except Exception:
            pass

    def stop(self):
        if self._icon:
            self._icon.stop()

    def _build_menu(self):
        return Menu(
            MenuItem(
                lambda item: f"RATT v{config.VERSION} \u2014 {'ON (Active)' if config.enabled else 'OFF (Paused)'}",
                None,
                enabled=False,
            ),
            MenuItem(
                lambda item: "Pause RATT (Release Keyboard)" if config.enabled else "Resume RATT",
                self._on_tk(self.app.toggle_ratt),
            ),
            Menu.SEPARATOR,
            MenuItem("Open RATT", self._on_tk(self.app.show_main_window), default=True),
            MenuItem("Slots menu", self._on_tk(self.app.show_popup)),
            Menu.SEPARATOR,
            MenuItem("Share", self._on_tk(self.app.show_share_dialog)),
            MenuItem("Mirror", self._on_tk(self.app.show_mirror_dialog)),
            MenuItem("Translate", self._on_tk(self.app.show_translate_dialog)),
            Menu.SEPARATOR,
            MenuItem("Settings", self._on_tk(self.app.show_settings)),
            MenuItem("Exit", self._on_tk(self.app.quit)),
        )

    def _on_tk(self, function):
        """Menu handler that runs `function` on the Tk thread (pystray calls from its own)."""
        return lambda *_: self.root.after(0, function)
