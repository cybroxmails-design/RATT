"""RATT Main Window - Clipboard Viewer & Manager."""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ratt.app import RattApp

from ratt.ui.styles import *
from ratt.config import config


class MainWindow:
    """Main clipboard viewer/manager window."""
    
    def __init__(self, root: tk.Tk, app: 'RattApp'):
        self.root = root
        self.app = app
        self.window: Optional[tk.Toplevel] = None
        self._is_visible = False
    
    def show(self):
        """Show or create the main window."""
        if self.window is None or not self.window.winfo_exists():
            self._create_window()
        else:
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()
        self._is_visible = True
        self.refresh()
    
    def hide(self):
        """Hide the window."""
        if self.window and self.window.winfo_exists():
            self.window.withdraw()
        self._is_visible = False
    
    def toggle(self):
        """Toggle window visibility."""
        if self._is_visible:
            self.hide()
        else:
            self.show()
    
    def refresh(self):
        """Refresh the slot display."""
        if not self.window or not self.window.winfo_exists():
            return
        
        # Clear existing slot widgets
        for widget in self.slots_frame.winfo_children():
            widget.destroy()
        
        slots = self.app.clipboard_manager.get_all_slots()
        available = self.app.clipboard_manager.get_available_slot_numbers()
        
        for slot_num in available:
            slot = slots.get(slot_num)
            self._create_slot_widget(slot_num, slot)
        
        # Update status bar
        tier_text = "Premium" if config.is_premium else "Basic"
        slot_count = len(slots)
        self.status_label.config(
            text=f"  {config.APP_NAME} v{config.VERSION}  |  {tier_text} ({config.max_slots} slots)  |  {slot_count} slot(s) in use"
        )
    
    def _create_window(self):
        """Create the main window."""
        self.window = tk.Toplevel(self.root)
        self.window.title(f"{config.APP_NAME} — Clipboard Manager")
        self.window.geometry("600x700")
        self.window.minsize(500, 400)
        self.window.configure(bg=BG_PRIMARY)
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        
        # Try to set icon
        try:
            self.window.iconbitmap("assets/ratt_icon.ico")
        except Exception:
            pass
        
        # Header
        header = tk.Frame(self.window, bg=BG_SECONDARY, pady=10, padx=16)
        header.pack(fill=tk.X)
        
        # Left side: title
        title_frame = tk.Frame(header, bg=BG_SECONDARY)
        title_frame.pack(side=tk.LEFT)
        
        title_label = tk.Label(
            title_frame, text=f"{config.APP_NAME}",
            font=FONT_TITLE, fg=ACCENT, bg=BG_SECONDARY
        )
        title_label.pack(side=tk.LEFT)
        
        subtitle = tk.Label(
            title_frame, text="Rapid Access To Text",
            font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY
        )
        subtitle.pack(side=tk.LEFT, padx=(10, 0))
        
        # Right side: toolbar buttons
        btn_frame = tk.Frame(header, bg=BG_SECONDARY)
        btn_frame.pack(side=tk.RIGHT)
        
        # Help button
        help_btn = tk.Button(
            btn_frame, text="?", font=(FONT_FAMILY, 11, "bold"),
            fg=TEXT_PRIMARY, bg="#2196F3", activebackground="#1976D2",
            relief=tk.FLAT, width=3, pady=2, cursor="hand2",
            command=lambda: self.app.show_help()
        )
        help_btn.pack(side=tk.LEFT, padx=3)
        
        # Account / Sign Up button
        account_text = config.user.email if config.user.is_logged_in else "Sign Up"
        account_bg = SUCCESS if config.user.is_logged_in else ACCENT
        account_btn = tk.Button(
            btn_frame, text=account_text, font=FONT_SMALL,
            fg=TEXT_PRIMARY, bg=account_bg, activebackground=ACCENT_HOVER,
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2",
            command=lambda: self.app.show_signup_dialog()
        )
        account_btn.pack(side=tk.LEFT, padx=3)
        
        # Settings button
        settings_btn = tk.Button(
            btn_frame, text="⚙", font=(FONT_FAMILY, 14),
            fg=TEXT_SECONDARY, bg=BG_SECONDARY, activebackground=BG_HOVER,
            relief=tk.FLAT, width=3, pady=0, cursor="hand2",
            command=lambda: self.app.show_settings()
        )
        settings_btn.pack(side=tk.LEFT, padx=3)
        
        # Separator line
        tk.Frame(self.window, bg=BORDER, height=1).pack(fill=tk.X)
        
        # Second toolbar row: Refresh and Clear All
        toolbar = tk.Frame(self.window, bg=BG_PRIMARY, pady=6, padx=16)
        toolbar.pack(fill=tk.X)
        
        refresh_btn = tk.Button(
            toolbar, text="Refresh", font=FONT_SMALL,
            fg=TEXT_PRIMARY, bg=BG_HOVER, activebackground=BG_ACTIVE,
            relief=tk.FLAT, padx=12, pady=3, cursor="hand2",
            command=self.refresh
        )
        refresh_btn.pack(side=tk.LEFT, padx=2)
        
        clear_all_btn = tk.Button(
            toolbar, text="Clear All", font=FONT_SMALL,
            fg=TEXT_PRIMARY, bg=ERROR, activebackground="#D32F2F",
            relief=tk.FLAT, padx=12, pady=3, cursor="hand2",
            command=self._on_clear_all
        )
        clear_all_btn.pack(side=tk.LEFT, padx=2)
        
        # Tier badge in toolbar
        tier_text = "⭐ Premium" if config.is_premium else "Basic"
        tier_color = SUCCESS if config.is_premium else TEXT_MUTED
        tier_badge = tk.Label(
            toolbar, text=tier_text, font=FONT_SMALL,
            fg=tier_color, bg=BG_PRIMARY
        )
        tier_badge.pack(side=tk.RIGHT, padx=4)
        
        # Scrollable slots area
        canvas_frame = tk.Frame(self.window, bg=BG_PRIMARY)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        self.canvas = tk.Canvas(canvas_frame, bg=BG_PRIMARY, highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.slots_frame = tk.Frame(self.canvas, bg=BG_PRIMARY)
        self.slots_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        self.canvas.create_window((0, 0), window=self.slots_frame, anchor=tk.NW, tags="frame")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig("frame", width=e.width))
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        
        # Status bar
        status_bar = tk.Frame(self.window, bg=BG_SECONDARY, pady=6)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = tk.Label(
            status_bar, text="", font=FONT_SMALL,
            fg=TEXT_SECONDARY, bg=BG_SECONDARY, anchor=tk.W
        )
        self.status_label.pack(fill=tk.X, padx=8)
    
    def _create_slot_widget(self, slot_num: int, slot):
        """Create a widget for a single slot."""
        color = get_slot_color(slot_num)
        
        frame = tk.Frame(self.slots_frame, bg=BG_SECONDARY, pady=8, padx=12)
        frame.pack(fill=tk.X, pady=3, padx=4)
        frame.configure(highlightbackground=BORDER, highlightthickness=1)
        
        # Left: color indicator + slot number
        left = tk.Frame(frame, bg=BG_SECONDARY)
        left.pack(side=tk.LEFT, fill=tk.Y)
        
        indicator = tk.Canvas(left, width=6, height=40, bg=color, highlightthickness=0)
        indicator.pack(side=tk.LEFT, padx=(0, 8))
        
        num_label = tk.Label(
            left, text=f"#{slot_num}", font=FONT_HEADING,
            fg=color, bg=BG_SECONDARY, width=3
        )
        num_label.pack(side=tk.LEFT)
        
        # Middle: content
        mid = tk.Frame(frame, bg=BG_SECONDARY)
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        
        if slot and not slot.is_empty:
            action_icon = "📋" if slot.action.value == "copy" else "✂️"
            preview_text = f"{action_icon} {slot.preview}"
            time_text = slot.timestamp.strftime("%H:%M:%S") if slot.timestamp else ""
            char_text = f"{slot.char_count} chars"
            
            preview = tk.Label(
                mid, text=preview_text, font=FONT_BODY,
                fg=TEXT_PRIMARY, bg=BG_SECONDARY, anchor=tk.W
            )
            preview.pack(fill=tk.X)
            
            meta = tk.Label(
                mid, text=f"{time_text}  •  {char_text}",
                font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_SECONDARY, anchor=tk.W
            )
            meta.pack(fill=tk.X)
            
            # Bind double-click to view full content
            for w in [frame, left, mid, preview, meta, num_label]:
                w.bind("<Double-Button-1>", lambda e, s=slot_num: self._view_slot_content(s))
        else:
            empty_label = tk.Label(
                mid, text="(empty)", font=FONT_BODY,
                fg=TEXT_MUTED, bg=BG_SECONDARY, anchor=tk.W
            )
            empty_label.pack(fill=tk.X)
        
        # Right: action buttons
        right = tk.Frame(frame, bg=BG_SECONDARY)
        right.pack(side=tk.RIGHT)
        
        if slot and not slot.is_empty:
            paste_btn = tk.Button(
                right, text="Paste", font=FONT_SMALL,
                fg=TEXT_PRIMARY, bg=ACCENT, activebackground=ACCENT_HOVER,
                relief=tk.FLAT, padx=8, pady=2, cursor="hand2",
                command=lambda s=slot_num: self._on_paste(s)
            )
            paste_btn.pack(side=tk.LEFT, padx=2)
            
            clear_btn = tk.Button(
                right, text="✕", font=FONT_SMALL,
                fg=TEXT_SECONDARY, bg=BG_HOVER, activebackground=BG_ACTIVE,
                relief=tk.FLAT, padx=6, pady=2, cursor="hand2",
                command=lambda s=slot_num: self._on_clear(s)
            )
            clear_btn.pack(side=tk.LEFT, padx=2)
    
    def _view_slot_content(self, slot_num: int):
        """Show full content of a slot in a popup."""
        slot = self.app.clipboard_manager.get_slot(slot_num)
        if not slot or slot.is_empty:
            return
        
        popup = tk.Toplevel(self.window)
        popup.title(f"Slot #{slot_num} Content")
        popup.geometry("500x400")
        popup.configure(bg=BG_PRIMARY)
        popup.transient(self.window)
        
        header = tk.Label(
            popup, text=f"Slot #{slot_num} — {slot.char_count} characters",
            font=FONT_HEADING, fg=ACCENT, bg=BG_PRIMARY, pady=8
        )
        header.pack(fill=tk.X)
        
        text_widget = scrolledtext.ScrolledText(
            popup, font=FONT_MONO, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, selectbackground=ACCENT,
            relief=tk.FLAT, padx=10, pady=10, wrap=tk.WORD
        )
        text_widget.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        text_widget.insert(tk.END, slot.content)
        text_widget.config(state=tk.DISABLED)
    
    def _on_paste(self, slot_num: int):
        """Handle paste button click."""
        result = self.app.clipboard_manager.paste_from_slot(slot_num)
        if result:
            self.app.show_notification(f"Slot #{slot_num} copied to clipboard")
    
    def _on_clear(self, slot_num: int):
        """Handle clear button click."""
        self.app.clipboard_manager.clear_slot(slot_num)
        self.refresh()
    
    def _on_clear_all(self):
        """Handle clear all button click."""
        if messagebox.askyesno("Clear All", "Are you sure you want to clear all clipboard slots?", parent=self.window):
            self.app.clipboard_manager.clear_all()
            self.refresh()
    
    def destroy(self):
        """Destroy the window."""
        if self.window and self.window.winfo_exists():
            self.window.destroy()
        self.window = None
