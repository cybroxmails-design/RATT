"""RATT System Tray Icon.

Manages the system tray icon and its context menu.
Uses pystray for system tray integration.
"""
import pystray
from pystray import MenuItem, Menu
from PIL import Image, ImageDraw, ImageFont
import threading
import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import tkinter as tk
    from ratt.app import RattApp


def create_ratt_icon_image(size: int = 64) -> Image.Image:
    """Create a simple RATT icon programmatically."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Orange circle background
    margin = 2
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill='#FF6B00'
    )
    
    # Draw "R" letter
    try:
        font = ImageFont.truetype("arial.ttf", size=int(size * 0.55))
    except (IOError, OSError):
        font = ImageFont.load_default()
    
    # Center the text
    text = "R"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - bbox[1]
    
    draw.text((x, y), text, fill='white', font=font)
    
    return img


class TrayIcon:
    """System tray icon for RATT."""
    
    def __init__(self, root: 'tk.Tk', app: 'RattApp'):
        self.root = root
        self.app = app
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start the tray icon in a background thread."""
        image = self._load_icon()
        menu = self._build_menu()
        
        self._icon = pystray.Icon(
            "RATT",
            image,
            "RATT \u2014 Rapid Access To Text",
            menu
        )
        
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop the tray icon."""
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
    
    def update_menu(self):
        """Update the tray menu (e.g., after tier change)."""
        if self._icon:
            self._icon.menu = self._build_menu()
            try:
                self._icon.update_menu()
            except Exception:
                pass
    
    def _load_icon(self) -> Image.Image:
        """Load or create the tray icon image."""
        # Try to load from file first
        icon_paths = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'ratt_icon.ico'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'ratt_icon.png'),
            'assets/ratt_icon.ico',
            'assets/ratt_icon.png',
        ]
        
        for path in icon_paths:
            if os.path.exists(path):
                try:
                    return Image.open(path)
                except Exception:
                    continue
        
        # Fallback: create icon programmatically
        return create_ratt_icon_image()
    
    def _build_menu(self) -> Menu:
        """Build the system tray context menu."""
        from ratt.config import config
        
        max_slots = config.max_slots
        
        # Build copy submenu
        copy_items = []
        for i in range(1, max_slots + 1):
            slot = self.app.clipboard_manager.get_slot(i)
            label = f"Slot {i}"
            if slot and not slot.is_empty:
                label += f" ({slot.preview[:20]})"
            copy_items.append(
                MenuItem(label, lambda _, s=i: self._schedule(self.app.copy_to_slot, s))
            )
        
        # Build cut submenu
        cut_items = []
        for i in range(1, max_slots + 1):
            slot = self.app.clipboard_manager.get_slot(i)
            label = f"Slot {i}"
            if slot and not slot.is_empty:
                label += f" ({slot.preview[:20]})"
            cut_items.append(
                MenuItem(label, lambda _, s=i: self._schedule(self.app.cut_to_slot, s))
            )
        
        # Build paste submenu
        paste_items = []
        for i in range(1, max_slots + 1):
            slot = self.app.clipboard_manager.get_slot(i)
            has_content = slot is not None and not slot.is_empty
            label = f"Slot {i}"
            if has_content:
                label += f" ({slot.preview[:20]})"
            else:
                label += " (empty)"
            paste_items.append(
                MenuItem(
                    label,
                    lambda _, s=i: self._schedule(self.app.paste_from_slot, s),
                    enabled=has_content
                )
            )
        
        menu = Menu(
            MenuItem(f"RATT v{config.VERSION}", None, enabled=False),
            Menu.SEPARATOR,
            MenuItem("View Clipboard", lambda: self._schedule(self.app.show_main_window)),
            Menu.SEPARATOR,
            MenuItem("📋 Copy to Slot", Menu(*copy_items)),
            MenuItem("✂️ Cut to Slot", Menu(*cut_items)),
            MenuItem("📌 Paste from Slot", Menu(*paste_items)),
            Menu.SEPARATOR,
            MenuItem("🔗 Share", lambda: self._schedule(self.app.show_share_dialog)),
            MenuItem("🪞 Mirror", lambda: self._schedule(self.app.show_mirror_dialog)),
            MenuItem("🌐 Translate", lambda: self._schedule(self.app.show_translate_dialog)),
            Menu.SEPARATOR,
            MenuItem("⚙️ Settings", lambda: self._schedule(self.app.show_settings)),
            MenuItem("❌ Exit", lambda: self._schedule(self.app.quit)),
        )
        
        return menu
    
    def _schedule(self, func, *args):
        """Schedule a function to run on the tkinter main thread."""
        self.root.after(0, lambda: func(*args))
