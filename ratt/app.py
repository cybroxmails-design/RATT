"""RATT Application Controller.

Central coordinator that initializes and connects all RATT modules.
Uses root Tk window as the main window for reliable button handling.
"""
import tkinter as tk
from tkinter import messagebox
import threading
import sys
import os
from datetime import datetime
from typing import Optional

from ratt.config import config
from ratt.clipboard_manager import ClipboardManager
from ratt.encryption import EncryptionManager
from ratt.sync import SyncManager
from ratt.translation import TranslationManager
from ratt.ui.styles import *


class RattApp:
    """Main RATT application."""
    
    def __init__(self):
        """Initialize all application components."""
        # Create the root window - this IS the main window
        self.root = tk.Tk()
        self.root.title(f"{config.APP_NAME} \u2014 Rapid Access To Text")
        self.root.geometry("620x700")
        self.root.minsize(500, 400)
        self.root.configure(bg=BG_PRIMARY)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Try to set icon
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'ratt_icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass
        
        # Core modules
        self.clipboard_manager = ClipboardManager(config)
        self.encryption = EncryptionManager()
        self.sync_manager = SyncManager()
        self.translation = TranslationManager()
        
        # Notification popup
        self._notification_popup: Optional[tk.Toplevel] = None
        
        # Page instance cache (one page at a time, repeated clicks ignored)
        self._dialogs = {}  # key -> dialog instance
        self._page = None
        self._page_key = None
        self._slots_alive = False
        self._scroll_canvas = None
        self._show_requested = False
        self._pending_actions = []
        self.root.bind_all("<MouseWheel>", self._on_wheel)
        
        # Connect clipboard change listener
        self.clipboard_manager.add_listener(self._on_clipboard_changed)
        
        # Build the main UI
        self._build_ui()
        
        # Check renewal alert after UI is ready
        self.root.after(2000, self._check_renewal_alert)
    
    # ========== LAYOUT: header (navigation) + content + status bar ==========

    def _build_ui(self):
        """Build the window frame. Pages (Slots, Account, Settings, Help...) are
        swapped inside `self.content` - no separate pop-up windows."""
        for widget in self.root.winfo_children():
            widget.destroy()
        self._page = None
        self._page_key = None
        self._slots_alive = False
        self._scroll_canvas = None

        self._build_header()

        status_bar = tk.Frame(self.root, bg=BG_SECONDARY, pady=6)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_label = tk.Label(
            status_bar, text="", font=FONT_SMALL,
            fg=TEXT_SECONDARY, bg=BG_SECONDARY, anchor=tk.W
        )
        self.status_label.pack(fill=tk.X, padx=8)

        self.content = tk.Frame(self.root, bg=BG_PRIMARY)
        self.content.pack(fill=tk.BOTH, expand=True)
        self.show_home()

    def _build_header(self):
        header = tk.Frame(self.root, bg=BG_SECONDARY, pady=8, padx=16)
        header.pack(fill=tk.X)

        title_frame = tk.Frame(header, bg=BG_SECONDARY)
        title_frame.pack(side=tk.LEFT)
        try:
            from PIL import Image, ImageTk
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'ratt_icon.png')
            if os.path.exists(logo_path):
                img = Image.open(logo_path).resize((36, 36), Image.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(img)
                tk.Label(title_frame, image=self._logo_img, bg=BG_SECONDARY).pack(side=tk.LEFT, padx=(0, 8))
        except Exception:
            pass
        tk.Label(title_frame, text="RATT", font=FONT_TITLE,
                 fg=LOGO_CYAN, bg=BG_SECONDARY).pack(side=tk.LEFT)
        tk.Label(title_frame, text="Rapid Access To Text", font=FONT_SMALL,
                 fg=TEXT_SECONDARY, bg=BG_SECONDARY).pack(side=tk.LEFT, padx=(10, 0))

        # Navigation tabs (one click switches the page inside this window)
        nav = tk.Frame(header, bg=BG_SECONDARY)
        nav.pack(side=tk.RIGHT)
        self._nav = {}

        def add(key, text, cmd):
            b = tk.Button(nav, text=text, font=FONT_SMALL, relief=tk.FLAT, bd=0,
                          padx=12, pady=5, cursor="hand2", command=cmd)
            b.pack(side=tk.LEFT, padx=2)
            self._nav[key] = b

        if config.user.is_logged_in:
            add("home", "Slots", self.show_home)
            add("account", config.user.display_name[:14] or "Account", self._open_signup)
            add("settings", "Settings", self._open_settings)
        else:
            add("account", "Sign Up", self._open_signup)
        add("help", "Help", self._open_help)
        self._set_nav("home")

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

    def _set_nav(self, active):
        for key, b in getattr(self, "_nav", {}).items():
            try:
                if key == active:
                    b.config(bg=LOGO_BLUE, fg=LOGO_DARK, activebackground=LOGO_CYAN,
                             font=(FONT_FAMILY, 9, "bold"))
                else:
                    b.config(bg=BG_HOVER, fg=TEXT_PRIMARY, activebackground=BG_ACTIVE,
                             font=FONT_SMALL)
            except tk.TclError:
                pass

    # ---------- page management ----------

    _NAV_FOR = {"help": "help", "settings": "settings", "services": "settings",
                "signup": "account", "payment": "account"}

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()
        self._page = None
        self._page_key = None
        self._slots_alive = False
        self._scroll_canvas = None

    def _home_if_empty(self):
        """Return to the home view if a page was closed and nothing replaced it."""
        try:
            if self._page is None and not self._slots_alive and self.content.winfo_exists():
                self.show_home()
        except tk.TclError:
            pass

    def show_home(self):
        """Slots view (or the sign-up gate when not logged in)."""
        self._clear_content()
        self._set_nav("home")
        if not config.user.is_logged_in:
            self._build_signup_gate(self.content)
        else:
            self._build_slots_view(self.content)

    def new_window(self, key, scroll=True):
        """Create an in-window page (replaces the old pop-up Toplevel).
        Opening another page replaces this one, so duplicates are impossible."""
        from ratt.ui.embedded import EmbeddedPage
        self.root.deiconify()
        self.root.lift()
        self._clear_content()

        container = tk.Frame(self.content, bg=BG_PRIMARY)
        container.pack(fill=tk.BOTH, expand=True)
        self._page = container
        self._page_key = key

        bar = tk.Frame(container, bg=BG_SECONDARY, padx=10, pady=6)
        bar.pack(fill=tk.X)
        tk.Button(bar, text="\u2190 Back", font=FONT_SMALL, fg=LOGO_DARK, bg=LOGO_BLUE,
                  activebackground=LOGO_CYAN, relief=tk.FLAT, bd=0, padx=10, pady=3,
                  cursor="hand2", command=self.show_home).pack(side=tk.LEFT)
        title_label = tk.Label(bar, text="", font=FONT_HEADING, fg=LOGO_CYAN, bg=BG_SECONDARY)
        title_label.pack(side=tk.LEFT, padx=12)

        body = tk.Frame(container, bg=BG_PRIMARY)
        body.pack(fill=tk.BOTH, expand=True)
        if scroll:
            canvas = tk.Canvas(body, bg=BG_PRIMARY, highlightthickness=0)
            sb = tk.Scrollbar(body, orient=tk.VERTICAL, command=canvas.yview)
            page = EmbeddedPage(canvas, container, self)
            win = canvas.create_window((0, 0), window=page, anchor="n")

            def on_canvas(e):
                canvas.itemconfig(win, width=min(e.width, 560))
                canvas.coords(win, e.width // 2, 0)
            canvas.bind("<Configure>", on_canvas)
            page.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.configure(yscrollcommand=sb.set)
            sb.pack(side=tk.RIGHT, fill=tk.Y)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self._scroll_canvas = canvas
        else:
            page = EmbeddedPage(body, container, self)
            page.pack(fill=tk.BOTH, expand=True)
        page.title_label = title_label
        self._set_nav(self._NAV_FOR.get(key))
        return page

    def set_scroll_canvas(self, canvas):
        """Pages that bring their own scrolling canvas register it here."""
        self._scroll_canvas = canvas

    def _on_wheel(self, event):
        c = getattr(self, "_scroll_canvas", None)
        if c is not None:
            try:
                c.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                pass

    # ---------- home: slots view ----------

    def _build_slots_view(self, parent):
        toolbar = tk.Frame(parent, bg=BG_PRIMARY, pady=6, padx=16)
        toolbar.pack(fill=tk.X)

        tk.Button(
            toolbar, text="Refresh", font=FONT_SMALL,
            fg=TEXT_PRIMARY, bg=BG_HOVER, activebackground=BG_ACTIVE,
            relief=tk.FLAT, padx=12, pady=3, cursor="hand2",
            command=self._refresh_slots
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            toolbar, text="Clear All", font=FONT_SMALL,
            fg=TEXT_PRIMARY, bg=ERROR, activebackground="#D32F2F",
            relief=tk.FLAT, padx=12, pady=3, cursor="hand2",
            command=self._clear_all
        ).pack(side=tk.LEFT, padx=2)

        from ratt.config import UserTier
        tier_labels = {
            UserTier.BASIC: ("Basic", TEXT_MUTED),
            UserTier.PREMIUM: ("Premium", SUCCESS),
            UserTier.ENTERPRISE: ("Enterprise", "#CE93D8"),
        }
        tier_text, tier_color = tier_labels.get(config.user.tier, ("Basic", TEXT_MUTED))
        tk.Label(toolbar, text=tier_text, font=FONT_SMALL,
                 fg=tier_color, bg=BG_PRIMARY).pack(side=tk.RIGHT, padx=4)

        self._build_renewal_strip(parent)

        canvas_frame = tk.Frame(parent, bg=BG_PRIMARY)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self.canvas = tk.Canvas(canvas_frame, bg=BG_PRIMARY, highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.slots_frame = tk.Frame(self.canvas, bg=BG_PRIMARY)
        self.slots_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.slots_frame, anchor=tk.NW, tags="frame")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig("frame", width=e.width))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._scroll_canvas = self.canvas
        self._slots_alive = True
        self._refresh_slots()

    # ---------- renewal countdown strip ----------

    @staticmethod
    def _renewal_style(days, expired):
        """(background, text colour) by urgency."""
        if expired or days <= 7:
            return "#E53935", "#FFFFFF"
        if days <= 30:
            return "#FFC107", LOGO_DARK
        return LOGO_BLUE, LOGO_DARK

    def _renewal_text(self):
        user = config.user
        tier = user.tier.value.title()
        days = user.days_until_expiry
        expired = user.subscription_expiry <= datetime.now()
        if expired:
            return f"{tier} plan EXPIRED - renew to keep your slots", days, True
        return (f"{tier} plan: {days} day{'s' if days != 1 else ''} remaining before renewal",
                days, False)

    def _build_renewal_strip(self, parent):
        user = config.user
        if not (config.is_premium and user.renewal_alert_needed):
            return
        text, days, expired = self._renewal_text()
        bg, fg = self._renewal_style(days, expired)
        strip = tk.Frame(parent, bg=bg, padx=12, pady=6)
        strip.pack(fill=tk.X, padx=8, pady=(0, 4))
        tk.Label(strip, text=text, font=(FONT_FAMILY, 9, "bold"), fg=fg, bg=bg).pack(side=tk.LEFT)
        tk.Button(strip, text="Renew now", font=FONT_SMALL, fg=bg, bg=fg,
                  activebackground=fg, relief=tk.FLAT, bd=0, padx=10, pady=2, cursor="hand2",
                  command=lambda: self._open_payment(user.tier.value)).pack(side=tk.RIGHT)

    def _build_signup_gate(self, parent):
        """Sign-up / log-in required screen (all tiers must sign up)."""
        gate = tk.Frame(parent, bg=BG_PRIMARY)
        gate.pack(fill=tk.BOTH, expand=True)

        try:
            from PIL import Image, ImageTk
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'ratt_logo.png')
            if os.path.exists(logo_path):
                img = Image.open(logo_path).resize((160, 160), Image.LANCZOS)
                self._gate_logo = ImageTk.PhotoImage(img)
                tk.Label(gate, image=self._gate_logo, bg=BG_PRIMARY).pack(pady=(40, 10))
        except Exception:
            tk.Label(gate, text="RATT", font=(FONT_FAMILY, 48, "bold"),
                     fg=LOGO_CYAN, bg=BG_PRIMARY).pack(pady=(40, 10))

        tk.Label(gate, text="RATT", font=(FONT_FAMILY, 28, "bold"),
                 fg=LOGO_CYAN, bg=BG_PRIMARY).pack()
        tk.Label(gate, text="Rapid Access To Text", font=FONT_BODY,
                 fg=TEXT_SECONDARY, bg=BG_PRIMARY).pack(pady=(0, 4))
        tk.Label(gate, text="by Cybrox.Inc", font=FONT_SMALL,
                 fg=TEXT_MUTED, bg=BG_PRIMARY).pack(pady=(0, 30))
        tk.Label(gate, text="Create a free account to start using RATT.",
                 font=FONT_BODY, fg=TEXT_PRIMARY, bg=BG_PRIMARY).pack(pady=(0, 4))
        tk.Label(gate, text="All users (Basic, Premium, Enterprise) must sign up and verify their email.",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_PRIMARY).pack(pady=(0, 24))
        tk.Button(gate, text="Create Free Account / Log In",
                  font=(FONT_FAMILY, 12, "bold"),
                  fg=LOGO_DARK, bg=LOGO_BLUE, activebackground=LOGO_CYAN,
                  relief=tk.FLAT, padx=24, pady=10, cursor="hand2",
                  command=self._open_signup).pack()
        tk.Label(gate, text="Free  |  No credit card required  |  Upgrade anytime",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_PRIMARY).pack(pady=(12, 0))

    def _refresh_slots(self):
        """Refresh the clipboard slot display (only when the slots view is showing)."""
        slots = self.clipboard_manager.get_all_slots()
        if self._slots_alive:
            try:
                for widget in self.slots_frame.winfo_children():
                    widget.destroy()
                available = self.clipboard_manager.get_available_slot_numbers()
                for slot_num in available:
                    self._create_slot_widget(slot_num, slots.get(slot_num))
            except tk.TclError:
                pass

        tier_text = config.user.tier.value.title()
        try:
            self.status_label.config(
                text=f"  {config.APP_NAME} v{config.VERSION} by {config.PUBLISHER}  |  "
                     f"{tier_text} ({config.max_slots:,} slots)  |  {len(slots)} slot(s) in use"
            )
        except (tk.TclError, AttributeError):
            pass

    def _create_slot_widget(self, slot_num, slot):
        """Create a widget for a single clipboard slot."""
        color = get_slot_color(slot_num)
        is_empty = not slot or slot.is_empty
        
        # Darken the slot color for empty slots (mix with black)
        def dim_color(hex_color, factor=0.3):
            """Return a dimmed version of a hex color."""
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            r = int(r * factor)
            g = int(g * factor)
            b = int(b * factor)
            return f"#{r:02X}{g:02X}{b:02X}"
        
        if is_empty:
            slot_bg = "#181818"
            border_color = "#2A2A2A"
            indicator_color = dim_color(color, 0.35)
            num_color = dim_color(color, 0.4)
        else:
            slot_bg = BG_SECONDARY
            border_color = BORDER
            indicator_color = color
            num_color = color
        
        frame = tk.Frame(self.slots_frame, bg=slot_bg, pady=8, padx=12)
        frame.pack(fill=tk.X, pady=3, padx=4)
        frame.configure(highlightbackground=border_color, highlightthickness=1)
        
        # Left: color indicator + slot number
        left = tk.Frame(frame, bg=slot_bg)
        left.pack(side=tk.LEFT, fill=tk.Y)
        
        indicator = tk.Canvas(left, width=6, height=40, bg=indicator_color, highlightthickness=0)
        indicator.pack(side=tk.LEFT, padx=(0, 8))
        
        tk.Label(
            left, text=f"#{slot_num}", font=FONT_HEADING,
            fg=num_color, bg=slot_bg, width=3
        ).pack(side=tk.LEFT)
        
        # Middle: content
        mid = tk.Frame(frame, bg=slot_bg)
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        
        if not is_empty:
            action_icon = "[COPY]" if slot.action.value == "copy" else "[CUT]"
            preview_text = f"{action_icon} {slot.preview}"
            time_text = slot.timestamp.strftime("%H:%M:%S") if slot.timestamp else ""
            char_text = f"{slot.char_count} chars"
            
            tk.Label(
                mid, text=preview_text, font=FONT_BODY,
                fg=TEXT_PRIMARY, bg=slot_bg, anchor=tk.W
            ).pack(fill=tk.X)
            
            tk.Label(
                mid, text=f"{time_text}  |  {char_text}",
                font=FONT_SMALL, fg=TEXT_MUTED, bg=slot_bg, anchor=tk.W
            ).pack(fill=tk.X)
        else:
            tk.Label(
                mid, text="Empty", font=(FONT_FAMILY, 11, "italic"),
                fg="#3A3A3A", bg=slot_bg, anchor=tk.W
            ).pack(fill=tk.X)
            tk.Label(
                mid, text=f"Ctrl+C then {slot_num if slot_num < 10 else 0} to save here",
                font=FONT_SMALL, fg="#2E2E2E", bg=slot_bg, anchor=tk.W
            ).pack(fill=tk.X)
        
        # Right: action buttons (only for filled slots)
        right = tk.Frame(frame, bg=slot_bg)
        right.pack(side=tk.RIGHT)
        
        if not is_empty:
            tk.Button(
                right, text="Paste", font=FONT_SMALL,
                fg=TEXT_PRIMARY, bg=ACCENT, activebackground=ACCENT_HOVER,
                relief=tk.FLAT, padx=8, pady=2, cursor="hand2",
                command=lambda s=slot_num: self._paste_slot(s)
            ).pack(side=tk.LEFT, padx=2)
            
            tk.Button(
                right, text="X", font=FONT_SMALL,
                fg=TEXT_SECONDARY, bg=BG_HOVER, activebackground=BG_ACTIVE,
                relief=tk.FLAT, padx=6, pady=2, cursor="hand2",
                command=lambda s=slot_num: self._clear_slot(s)
            ).pack(side=tk.LEFT, padx=2)
    
    def _paste_slot(self, slot_num):
        """Paste from a slot."""
        result = self.clipboard_manager.paste_from_slot(slot_num)
        if result:
            self.show_notification(f"Pasted from Slot #{slot_num}")
    
    def _clear_slot(self, slot_num):
        """Clear a slot."""
        self.clipboard_manager.clear_slot(slot_num)
        self._refresh_slots()
    
    def _clear_all(self):
        """Clear all slots."""
        if messagebox.askyesno("Clear All", "Clear all clipboard slots?", parent=self.root):
            self.clipboard_manager.clear_all()
            self._refresh_slots()
    
    def copy_to_slot(self, slot_num):
        """Copy current clipboard content to a slot."""
        success = self.clipboard_manager.copy_to_slot(slot_num)
        if success:
            self.show_notification(f"Copied to Slot #{slot_num}")
            self._refresh_slots()
    
    def cut_to_slot(self, slot_num):
        """Cut current clipboard content to a slot."""
        success = self.clipboard_manager.cut_to_slot(slot_num)
        if success:
            self.show_notification(f"Cut to Slot #{slot_num}")
            self._refresh_slots()
    
    def paste_from_slot(self, slot_num):
        """Paste content from a slot."""
        result = self.clipboard_manager.paste_from_slot(slot_num)
        if result:
            self.show_notification(f"Pasted from Slot #{slot_num}")

    # ========== OPEN PAGES (one page at a time, repeated clicks ignored) ==========

    def _open_dialog(self, key: str, dialog_class, *args):
        """Show a page in the main window. Clicking the same button again does
        nothing (no duplicates); another button replaces the current page."""
        inst = self._dialogs.get(key)
        if inst is not None and self._page_key == key:
            try:
                if inst.dialog and inst.dialog.winfo_exists():
                    return
            except Exception:
                pass
        inst = dialog_class(self.root, self, *args)
        self._dialogs[key] = inst
        inst.show()

    def _open_help(self):
        from ratt.ui.help_dialog import HelpDialog
        self._open_dialog("help", HelpDialog)

    def _open_signup(self):
        from ratt.ui.signup_dialog import SignupDialog
        self._open_dialog("signup", SignupDialog)

    def _open_settings(self):
        from ratt.ui.settings_dialog import SettingsDialog
        self._open_dialog("settings", SettingsDialog)

    def _open_payment(self, plan="premium"):
        from ratt.ui.payment_dialog import PaymentDialog
        self._dialogs.pop("payment", None)
        self._open_dialog("payment", PaymentDialog, plan)

    def _open_services(self):
        from ratt.ui.services_dialog import ServicesDialog
        self._open_dialog("services", ServicesDialog)

    def show_share_dialog(self):
        from ratt.ui.share_dialog import ShareDialog
        self._open_dialog("share", ShareDialog)

    def show_mirror_dialog(self):
        from ratt.ui.mirror_dialog import MirrorDialog
        self._open_dialog("mirror", MirrorDialog)

    def show_translate_dialog(self):
        from ratt.ui.translate_dialog import TranslateDialog
        self._open_dialog("translate", TranslateDialog)

    def show_main_window(self):
        """Show the main window (bring to front)."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self._refresh_slots()

    # Aliases
    def show_settings(self): self._open_settings()
    def show_help(self): self._open_help()
    def show_signup_dialog(self): self._open_signup()

    def show_popup(self):
        """Show the clipboard popup menu (one at a time)."""
        from ratt.ui.clipboard_popup import ClipboardPopup
        if not hasattr(self, '_clipboard_popup'):
            self._clipboard_popup = ClipboardPopup(self.root, self)
        self._clipboard_popup.show_at_cursor()

    def rebuild_ui(self):
        """Rebuild the main UI (called after tier change, login, etc)."""
        self._dialogs.clear()
        self._build_ui()
        # Update context menu to reflect new slot count
        self._update_context_menu()

    # ========== RENEWAL ALERT ==========

    def _check_renewal_alert(self):
        """Renewal reminder: starts 3 months before expiry, repeats every 30 days
        (daily in the last 7 days), always showing the days remaining."""
        try:
            user = config.user
            if user.is_logged_in and config.is_premium and user.should_show_renewal_alert():
                text, days, expired = self._renewal_text()
                bg, fg = self._renewal_style(days, expired)
                self._show_renewal_banner(text, bg, fg)
                user.last_renewal_alert = datetime.now()
                config.save_session()
                if self._slots_alive:      # refresh the countdown strip
                    self.show_home()
        except Exception:
            pass
        self.root.after(6 * 3600 * 1000, self._check_renewal_alert)   # re-check every 6h

    def _show_renewal_banner(self, message, bg, fg):
        """Small non-blocking reminder (auto-dismisses)."""
        banner = tk.Toplevel(self.root)
        banner.overrideredirect(True)
        banner.attributes("-topmost", True)
        banner.configure(bg=bg)

        f = tk.Frame(banner, bg=bg, padx=20, pady=12)
        f.pack(fill=tk.BOTH, expand=True)
        tk.Label(f, text="Subscription renewal", font=(FONT_FAMILY, 11, "bold"),
                 fg=fg, bg=bg).pack(anchor=tk.W)
        tk.Label(f, text=message, font=FONT_BODY, fg=fg, bg=bg,
                 justify=tk.LEFT, wraplength=330).pack(anchor=tk.W, pady=(2, 8))
        row = tk.Frame(f, bg=bg)
        row.pack(fill=tk.X)
        tier = config.user.tier.value
        tk.Button(row, text="Renew now", font=FONT_SMALL, fg=bg, bg=fg, relief=tk.FLAT,
                  padx=12, pady=4, cursor="hand2",
                  command=lambda: [banner.destroy(), self._open_payment(tier)]).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(row, text="Dismiss", font=FONT_SMALL, fg=fg, bg=bg, relief=tk.FLAT,
                  padx=8, pady=4, cursor="hand2", command=banner.destroy).pack(side=tk.LEFT)

        banner.update_idletasks()
        w, h = max(banner.winfo_reqwidth(), 380), banner.winfo_reqheight()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        banner.geometry(f"{w}x{h}+{sw - w - 20}+{sh - h - 80}")
        banner.after(15000, lambda: banner.destroy() if banner.winfo_exists() else None)

    # ========== DYNAMIC CONTEXT MENU ==========

    def _update_context_menu(self):
        """Update right-click menu to reflect current slots and filled status."""
        try:
            from ratt.context_menu_updater import update_context_menu
            update_context_menu(config, self.clipboard_manager)
        except Exception:
            pass

    # ========== NOTIFICATIONS ==========

    def show_notification(self, message, duration=2000, is_error=False):
        """Show a brief notification popup."""
        if self._notification_popup and self._notification_popup.winfo_exists():
            self._notification_popup.destroy()

        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.attributes("-alpha", 0.92)

        bg_color = ERROR if is_error else BG_SECONDARY

        frame = tk.Frame(popup, bg=bg_color, padx=16, pady=10,
                        highlightbackground=ACCENT, highlightthickness=1)
        frame.pack()

        tk.Label(frame, text=message, font=FONT_BODY,
                 fg=TEXT_PRIMARY, bg=bg_color).pack()

        popup.update_idletasks()
        screen_w = popup.winfo_screenwidth()
        screen_h = popup.winfo_screenheight()
        popup_w = popup.winfo_reqwidth()
        popup_h = popup.winfo_reqheight()

        x = screen_w - popup_w - 20
        y = screen_h - popup_h - 80
        popup.geometry(f"+{x}+{y}")

        self._notification_popup = popup
        popup.after(duration, lambda: popup.destroy() if popup.winfo_exists() else None)

    def _on_close(self):
        """Handle window close - minimize to tray."""
        self.root.withdraw()

    def quit(self):
        """Quit the application completely."""
        self.clipboard_manager.clear_all()
        self.encryption.destroy()
        self.sync_manager.disconnect()
        self.root.quit()
        self.root.destroy()

    def _on_clipboard_changed(self):
        """Handle clipboard slot changes — refresh UI and update context menu."""
        try:
            self.root.after(0, self._refresh_slots)
            self.root.after(500, self._update_context_menu)
        except Exception:
            pass

    # ========== SINGLE INSTANCE + RIGHT-CLICK ACTIONS ==========

    # Actions the right-click menu may request (validated before use)
    ALLOWED_ACTIONS = ("open", "copy", "cut", "paste", "translate", "share", "mirror", "popup")

    def start_instance_listener(self, server_sock):
        """A second launch (double-clicking the logo again, or a right-click menu
        item) pings this instance instead of opening another RATT."""
        import re
        import threading

        def serve():
            while True:
                try:
                    conn, _ = server_sock.accept()
                except OSError:
                    return
                try:
                    conn.settimeout(1)
                    parts = conn.recv(128).decode("ascii", "ignore").split()
                    if parts and parts[0] == "SHOW":
                        self._show_requested = True
                    elif (len(parts) >= 2 and parts[0] == "ACTION"
                          and parts[1] in self.ALLOWED_ACTIONS
                          and all(re.fullmatch(r"[A-Za-z0-9\-]{1,10}", a) for a in parts[2:4])):
                        self._pending_actions.append((parts[1], parts[2:4]))
                except Exception:
                    pass
                finally:
                    conn.close()

        threading.Thread(target=serve, daemon=True).start()
        self._poll_show_request()

    def _poll_show_request(self):
        if self._show_requested:
            self._show_requested = False
            self.show_main_window()
        while self._pending_actions:
            action, args = self._pending_actions.pop(0)
            try:
                self.run_action(action, args)
            except Exception:
                pass
        self.root.after(300, self._poll_show_request)

    # ---- action runner (Tk thread starts it; clipboard/keyboard work runs in a thread) ----

    def _notify_async(self, message, is_error=False):
        try:
            self.root.after(0, lambda: self.show_notification(message, is_error=is_error))
        except Exception:
            pass

    def _send_keys(self, combo):
        """Send a keystroke to the document in front, without RATT's own hotkey
        listener mistaking it for a user chord."""
        import keyboard
        hl = getattr(self, "hotkey_listener", None)
        if hl is not None:
            hl.ignore_for(0.9)
        keyboard.send(combo)

    def run_action(self, action, args):
        """Run an action chosen from the right-click menu or popup."""
        if action == "open":
            self.show_main_window()
            return
        if not config.user.is_logged_in:
            self.show_main_window()
            self.show_notification("Sign up to start using RATT", is_error=True)
            return
        if action in ("share", "mirror"):
            if not config.user.is_trial_active:
                self.show_main_window()
                self.show_notification(f"Your 7-day {action} trial has ended - upgrade to continue", is_error=True)
            elif action == "share":
                self.show_share_dialog()
            else:
                self.show_mirror_dialog()
            return
        if action == "popup":
            self.show_popup()
            return

        import threading
        slot = int(args[0]) if args and args[0].isdigit() else None
        if action in ("copy", "cut", "paste"):
            if slot is None or slot > config.max_slots:
                self.show_notification("That slot is not available on your plan", is_error=True)
                return
            target = self._grab_to_slot if action != "paste" else self._paste_into_document
            threading.Thread(target=target, args=(action, slot), daemon=True).start()
        elif action == "translate" and args:
            self.translate_active_slot(args[0])

    def _grab_to_slot(self, action, slot, delay=0.3):
        """Copy/cut the highlighted text in the front document into a slot."""
        import time
        import pyperclip
        time.sleep(delay)                      # let the menu close, focus return
        try:
            old = pyperclip.paste()
        except Exception:
            old = ""
        marker = f"__ratt_{time.time()}__"
        pyperclip.copy(marker)
        self._send_keys("ctrl+c" if action == "copy" else "ctrl+x")
        text = marker
        for _ in range(15):                    # wait up to 1.5 s for the app to answer
            time.sleep(0.1)
            text = pyperclip.paste()
            if text != marker:
                break
        if text == marker or not text:
            pyperclip.copy(old)
            self._notify_async("Highlight some text first", is_error=True)
            return
        fn = self.clipboard_manager.copy_to_slot if action == "copy" else self.clipboard_manager.cut_to_slot
        if fn(slot, text):
            self._notify_async(f"{'Copied' if action == 'copy' else 'Cut'} to Slot #{slot}")

    def _paste_into_document(self, action, slot, delay=0.3):
        import time
        time.sleep(delay)
        text = self.clipboard_manager.paste_from_slot(slot)
        if not text:
            self._notify_async(f"Slot #{slot} is empty", is_error=True)
            return
        time.sleep(0.15)
        self._send_keys("ctrl+v")
        self._notify_async(f"Pasted from Slot #{slot}")

    def translate_active_slot(self, lang_code, delay=0.3):
        """Translate the active slot's text and paste the translation into the
        document in front. (Premium / Enterprise.)"""
        import threading
        if not config.is_premium:
            self.show_main_window()
            self.show_notification("Translate is for Premium and Enterprise users", is_error=True)
            return
        from ratt.config import TRANSLATE_LANGUAGES
        name = dict(TRANSLATE_LANGUAGES).get(lang_code, lang_code)
        slot = self.clipboard_manager.active_slot()
        if slot is None:
            self.show_notification("Copy something to a slot first", is_error=True)
            return
        text = self.clipboard_manager.get_slot(slot).content
        self.show_notification(f"Translating Slot #{slot} to {name}...", duration=1500)

        def work():
            import time
            import pyperclip
            from ratt.translation import TranslationError
            time.sleep(delay)
            try:
                out = self.translation.translate(text, lang_code)
            except TranslationError as e:
                self._notify_async(str(e), is_error=True)
                return
            pyperclip.copy(out)
            time.sleep(0.15)
            self._send_keys("ctrl+v")
            self._notify_async(f"Pasted {name} translation of Slot #{slot}")

        threading.Thread(target=work, daemon=True).start()

    def run(self):
        """Start the application."""
        try:
            from ratt.tray_icon import TrayIcon
            self.tray_icon = TrayIcon(self.root, self)
            self.tray_icon.start()
        except Exception:
            pass

        try:
            from ratt.hotkey_listener import HotkeyListener
            self.hotkey_listener = HotkeyListener()
            self.hotkey_listener.on_copy_to_slot = lambda s: self.root.after(0, self.copy_to_slot, s)
            self.hotkey_listener.on_cut_to_slot = lambda s: self.root.after(0, self.cut_to_slot, s)
            self.hotkey_listener.on_paste_from_slot = lambda s: self.root.after(0, self.paste_from_slot, s)
            self.hotkey_listener.on_popup_requested = lambda: self.root.after(0, self.show_popup)
            self.hotkey_listener.start()
        except Exception:
            pass

        # Initial context menu update to reflect current slot count
        self.root.after(1000, self._update_context_menu)

        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass

