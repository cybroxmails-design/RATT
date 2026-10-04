"""RATT Help Dialog - Quick Guide for users."""
import tkinter as tk
from tkinter import scrolledtext
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ratt.app import RattApp

from ratt.ui.styles import *
from ratt.config import config


class HelpDialog:
    """Help window with quick guide."""
    
    def __init__(self, root: tk.Tk, app: 'RattApp'):
        self.root = root
        self.app = app
        self.dialog: Optional[tk.Toplevel] = None
    
    def show(self):
        """Show the help dialog."""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.lift()
            self.dialog.focus_force()
            return
        
        self.dialog = self.app.new_window("help")
        self.dialog.title("RATT \u2014 Help & Quick Guide")
        self.dialog.geometry("550x620")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=BG_PRIMARY)
        self.dialog.transient(self.root)
        
        # Header
        header = tk.Frame(self.dialog, bg=BG_SECONDARY, pady=12, padx=16)
        header.pack(fill=tk.X)
        
        tk.Label(
            header, text="? Help & Quick Guide", font=FONT_TITLE,
            fg="#2196F3", bg=BG_SECONDARY
        ).pack(anchor=tk.W)
        
        tk.Label(
            header, text=f"{config.APP_NAME} v{config.VERSION} by {config.PUBLISHER}",
            font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY
        ).pack(anchor=tk.W, pady=(4, 0))
        
        # Scrollable content
        content_frame = tk.Frame(self.dialog, bg=BG_PRIMARY, padx=16, pady=8)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        text = scrolledtext.ScrolledText(
            content_frame, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            padx=16, pady=16, wrap=tk.WORD, cursor="arrow"
        )
        text.pack(fill=tk.BOTH, expand=True)
        
        # Insert help content
        guide_text = self._get_guide_text()
        
        # Configure tags for formatting
        text.tag_configure("title", font=(FONT_FAMILY, 14, "bold"), foreground=ACCENT)
        text.tag_configure("heading", font=(FONT_FAMILY, 11, "bold"), foreground="#2196F3")
        text.tag_configure("key", font=("Consolas", 10, "bold"), foreground="#4CAF50")
        text.tag_configure("note", font=(FONT_FAMILY, 9, "italic"), foreground=TEXT_MUTED)
        text.tag_configure("body", font=FONT_BODY, foreground=TEXT_PRIMARY)
        text.tag_configure("bullet", font=FONT_BODY, foreground=TEXT_SECONDARY, lmargin1=20, lmargin2=35)
        
        # Title
        text.insert(tk.END, "Welcome to RATT!\n", "title")
        text.insert(tk.END, "Rapid Access To Text by Cybrox.Inc\n\n", "note")
        
        # Getting Started
        text.insert(tk.END, "GETTING STARTED\n", "heading")
        text.insert(tk.END, "RATT lets you save multiple copied texts into separate slots\n", "body")
        text.insert(tk.END, "and paste them individually whenever you need.\n\n", "body")
        
        # Copy
        text.insert(tk.END, "HOW TO COPY TO A SLOT\n", "heading")
        text.insert(tk.END, "1. Select and copy text anywhere (", "body")
        text.insert(tk.END, "Ctrl+C", "key")
        text.insert(tk.END, ")\n", "body")
        text.insert(tk.END, "2. Within 2 seconds, press a number key ", "body")
        text.insert(tk.END, "1-9", "key")
        text.insert(tk.END, " or ", "body")
        text.insert(tk.END, "0", "key")
        text.insert(tk.END, " (for slot 10)\n", "body")
        text.insert(tk.END, "3. The text is saved to that slot!\n\n", "body")
        
        # Cut
        text.insert(tk.END, "HOW TO CUT TO A SLOT\n", "heading")
        text.insert(tk.END, "1. Select and cut text anywhere (", "body")
        text.insert(tk.END, "Ctrl+X", "key")
        text.insert(tk.END, ")\n", "body")
        text.insert(tk.END, "2. Within 2 seconds, press a number key ", "body")
        text.insert(tk.END, "1-9", "key")
        text.insert(tk.END, " or ", "body")
        text.insert(tk.END, "0", "key")
        text.insert(tk.END, "\n\n", "body")
        
        # Paste
        text.insert(tk.END, "HOW TO PASTE FROM A SLOT\n", "heading")
        text.insert(tk.END, "1. Press ", "body")
        text.insert(tk.END, "Ctrl+V", "key")
        text.insert(tk.END, " then within 2 seconds press a number\n", "body")
        text.insert(tk.END, "2. The saved text from that slot is pasted!\n\n", "body")
        
        # Popup Menu
        text.insert(tk.END, "QUICK POPUP MENU\n", "heading")
        text.insert(tk.END, "Press ", "body")
        text.insert(tk.END, "Ctrl+Shift+R", "key")
        text.insert(tk.END, " anywhere to open the RATT popup menu.\n", "body")
        text.insert(tk.END, "From here you can copy, cut, paste, share, or mirror.\n\n", "body")
        
        # System Tray
        text.insert(tk.END, "SYSTEM TRAY\n", "heading")
        text.insert(tk.END, "\u2022 Look for the orange R icon near your clock\n", "bullet")
        text.insert(tk.END, "\u2022 Right-click it for the full menu\n", "bullet")
        text.insert(tk.END, "\u2022 Left-click to open this window\n\n", "bullet")
        
        # Keyboard Shortcuts
        text.insert(tk.END, "KEYBOARD SHORTCUTS\n", "heading")
        text.insert(tk.END, "Ctrl+C, then 1-0", "key")
        text.insert(tk.END, "    Copy to slot\n", "body")
        text.insert(tk.END, "Ctrl+X, then 1-0", "key")
        text.insert(tk.END, "    Cut to slot\n", "body")
        text.insert(tk.END, "Ctrl+V, then 1-0", "key")
        text.insert(tk.END, "    Paste from slot\n", "body")
        text.insert(tk.END, "Ctrl+Shift+R", "key")
        text.insert(tk.END, "         Open popup menu\n\n", "body")
        
        # Tiers
        text.insert(tk.END, "BASIC vs PREMIUM\n", "heading")
        text.insert(tk.END, "\u2022 Basic: 2 clipboard slots\n", "bullet")
        text.insert(tk.END, "\u2022 Premium: 10 clipboard slots + Translation\n", "bullet")
        text.insert(tk.END, "\u2022 Sign up and upgrade in the app header\n\n", "bullet")
        
        # Share & Mirror
        text.insert(tk.END, "SHARE & MIRROR\n", "heading")
        text.insert(tk.END, "\u2022 Share: Send clipboard contents to another user\n", "bullet")
        text.insert(tk.END, "\u2022 Mirror: Display text on another user's screen (read-only)\n", "bullet")
        text.insert(tk.END, "\u2022 Both use verification codes for security\n\n", "bullet")
        
        # Security
        text.insert(tk.END, "SECURITY\n", "heading")
        text.insert(tk.END, "\u2022 All data is encrypted with AES-256\n", "bullet")
        text.insert(tk.END, "\u2022 All clipboard data is erased when you close RATT\n", "bullet")
        text.insert(tk.END, "\u2022 End-to-end encryption for sharing (Phase 2)\n\n", "bullet")
        
        # Footer
        text.insert(tk.END, f"\u00a9 2026 {config.PUBLISHER}. All rights reserved.\n", "note")
        
        text.config(state=tk.DISABLED)
        
        # Close button
        close_btn = tk.Button(
            self.dialog, text="Got it!", font=FONT_HEADING,
            fg=TEXT_PRIMARY, bg="#2196F3", activebackground="#1976D2",
            relief=tk.FLAT, pady=8, cursor="hand2",
            command=self.dismiss
        )
        close_btn.pack(fill=tk.X, padx=16, pady=(0, 12))
    
    def _get_guide_text(self) -> str:
        """Get the guide text content."""
        return ""  # Content is inserted with tags above
    
    def dismiss(self):
        """Close the dialog."""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog = None
