"""RATT Application Controller.

Central coordinator that initializes and connects all RATT modules.
Uses root Tk window as the main window for reliable button handling.
"""
import os
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from typing import Optional

from ratt import instance
from ratt.actions import ActionRunner
from ratt.clipboard_manager import ClipboardManager
from ratt.config import config
from ratt.daemon_link import DaemonLink
from ratt.translation import TranslationManager
from ratt.ui.styles import *

MAX_RENDERED_SLOTS = 100


class RattApp:
    """Main RATT application."""
    
    def __init__(self):
        """Initialize all application components."""
        # Create the root window - this IS the main window
        self.root = tk.Tk()
        self.root.title(f"{config.APP_NAME} v{config.VERSION} \u2014 Rapid Access To Text")
        self.root.geometry("680x720")
        self.root.minsize(480, 400)
        self.root.configure(bg=BG_PRIMARY)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # RATT blue icon in the title bar AND the taskbar
        try:
            assets = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
            icon_path = os.path.join(assets, 'ratt_icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(default=icon_path)
            png_path = os.path.join(assets, 'ratt_icon.png')
            if os.path.exists(png_path):
                self._taskbar_icon = tk.PhotoImage(file=png_path)   # keep a reference
                self.root.iconphoto(True, self._taskbar_icon)
        except Exception:
            pass
        
        # Core modules
        self.clipboard_manager = ClipboardManager(config)
        self.translation = TranslationManager()
        self.actions = ActionRunner(self)      # right-click menu, popup and hotkey actions
        self.daemon = DaemonLink(self)         # native helper: hotkeys + key injection
        
        # Notification popup
        self._notification_popup: Optional[tk.Toplevel] = None
        
        # Page instance cache (one page at a time, repeated clicks ignored)
        self._dialogs = {}  # key -> dialog instance
        self._page = None
        self._page_key = None
        self._slots_alive = False
        self._scroll_canvas = None
        self._show_requested = False   # the next three are filled by other threads and
        self._last_show_req = 0.0
        self._pending_actions = []     # handled on the Tk thread by _poll()
        self._clip_dirty = False
        self._notify_queue = []
        self._upgrade_queue = []
        self._toggle_btn: Optional[tk.Button] = None
        self.root.bind_all("<MouseWheel>", self._on_wheel)
        self.root.bind_all("<Control-Alt-p>", lambda e: self.toggle_ratt())
        self.root.bind_all("<Control-Alt-P>", lambda e: self.toggle_ratt())
        
        # Connect clipboard change listener
        self.clipboard_manager.app = self
        self.clipboard_manager.add_listener(self._on_clipboard_changed)
        
        # Start background receiver for mobile -> PC sync on port 49211
        try:
            from ratt.hal import android_bridge
            android_bridge.start_pc_sync_receiver(self.clipboard_manager, port=49211)
            self._start_android_auto_sync()
        except Exception:
            pass
        
        # Build the main UI
        self._build_ui()

        # Immediately register/refresh the Explorer right-click menu on startup
        self._update_context_menu()
        
        # Tk-thread poll: menu actions, slot changes, notifications from worker threads
        self.root.after(150, self._poll)

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
        header = tk.Frame(self.root, bg=BG_SECONDARY, pady=8, padx=12)
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

        brand_col = tk.Frame(title_frame, bg=BG_SECONDARY)
        brand_col.pack(side=tk.LEFT)
        tk.Label(
            brand_col, text=f"{config.APP_NAME} v{config.VERSION}",
            font=(FONT_FAMILY, 15, "bold"), fg=LOGO_CYAN, bg=BG_SECONDARY,
            anchor=tk.W, pady=0
        ).pack(anchor=tk.W)
        tk.Label(
            brand_col, text="Rapid Access To Text",
            font=(FONT_FAMILY, 8), fg=TEXT_SECONDARY, bg=BG_SECONDARY,
            anchor=tk.W, pady=0
        ).pack(anchor=tk.W)

        # Modern ON/OFF Toggle Switch right next to the title:
        # [ ● ON  ] with a Cyan glow when active
        # [   OFF ●] in muted slate-grey when paused
        self._toggle_btn = tk.Button(
            title_frame,
            text="[ \u25cf ON  ]" if config.enabled else "[   OFF \u25cf]",
            font=(FONT_FAMILY, 9, "bold"),
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.toggle_ratt,
        )
        self._toggle_btn.pack(side=tk.LEFT, padx=(10, 0))
        self._update_toggle_ui()

        # Navigation tabs (packed on the right so all buttons including Help are always visible)
        nav = tk.Frame(header, bg=BG_SECONDARY)
        nav.pack(side=tk.RIGHT)
        self._nav = {}

        def add(key, text, cmd):
            b = tk.Button(nav, text=text, font=FONT_SMALL, relief=tk.FLAT, bd=0,
                          padx=10, pady=5, cursor="hand2", command=cmd)
            b.pack(side=tk.LEFT, padx=2)
            self._nav[key] = b

        if config.user.is_logged_in:
            add("home", "Slots", self.show_home)
            add("account", config.user.display_name[:12] or "Account", self._open_signup)
            add("settings", "Settings", self._open_settings)
        else:
            add("account", "Sign In", self._open_signup)
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

    def _update_toggle_ui(self):
        """Update the header ON/OFF toggle button styling (Cyan glow when ON, Slate-Grey when OFF)."""
        btn = getattr(self, "_toggle_btn", None)
        if not btn:
            return
        try:
            if config.enabled:
                btn.config(
                    text="[ \u25cf ON  ]",
                    fg=LOGO_CYAN,
                    bg="#00384D",
                    activebackground="#005270",
                    activeforeground="#FFFFFF",
                    highlightbackground=LOGO_CYAN,
                    highlightcolor=LOGO_CYAN,
                    highlightthickness=2,
                )
            else:
                btn.config(
                    text="[   OFF \u25cf]",
                    fg="#94A3B8",
                    bg="#2D3748",
                    activebackground="#334155",
                    activeforeground="#CBD5E1",
                    highlightbackground="#475569",
                    highlightcolor="#475569",
                    highlightthickness=1,
                )
        except tk.TclError:
            pass

    def set_ratt_enabled(self, enabled: bool):
        """Enable (ON) or Pause (OFF) RATT, completely releasing or restoring native keyboard & mouse."""
        config.enabled = bool(enabled)
        self._update_toggle_ui()
        # Immediately release or re-integrate native hotkeys in the daemon
        try:
            self.daemon.sync_now()
        except Exception:
            pass
        # Release or re-integrate the Explorer right-click mouse context menu
        self._update_context_menu()
        # Update the System Tray icon color (Cyan vs Grey/Amber) and menu item
        if hasattr(self, "tray_icon") and self.tray_icon:
            try:
                self.tray_icon.update_state()
            except Exception:
                pass
        self._refresh_slots()
        if config.enabled:
            self.show_notification("RATT is ON \u2014 Keyboard & Mouse integrated (Ctrl+Alt+P to pause)")
        else:
            self.show_notification(
                "RATT is OFF \u2014 Native Keyboard & Mouse completely released (Ctrl+Alt+P to resume)",
                duration=3000,
            )

    def toggle_ratt(self):
        """Toggle RATT between ON (Active) and OFF (Paused — Keyboard & Mouse released)."""
        self.set_ratt_enabled(not config.enabled)

    # ---------- page management ----------

    _NAV_FOR = {"help": "help", "settings": "settings",
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
            canvas = tk.Canvas(body, bg=BG_PRIMARY, highlightthickness=0, bd=0)
            sb = tk.Scrollbar(body, orient=tk.VERTICAL, command=canvas.yview)
            page = EmbeddedPage(canvas, container, self)
            win = canvas.create_window((0, 0), window=page, anchor=tk.NW)

            def _sync_layout(_event=None):
                try:
                    cw = max(canvas.winfo_width(), 1)
                    ch = max(canvas.winfo_height(), 1)
                    req_h = max(page.winfo_reqheight(), ch)
                    canvas.coords(win, 0, 0)
                    canvas.itemconfig(win, width=cw)
                    canvas.configure(scrollregion=(0, 0, cw, req_h))
                    canvas.xview_moveto(0.0)
                except tk.TclError:
                    pass

            canvas.bind("<Configure>", _sync_layout)
            page.bind("<Configure>", _sync_layout)
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
        android_btn = tk.Button(
            toolbar, text="Android Sync", font=FONT_SMALL,
            fg=TEXT_PRIMARY, bg="#2E7D32" if config.is_premium else BG_HOVER,
            activebackground="#388E3C" if config.is_premium else BG_ACTIVE,
            relief=tk.FLAT, padx=12, pady=3, cursor="hand2",
            command=self._on_android_sync_btn
        )
        android_btn.pack(side=tk.LEFT, padx=2)
        android_btn.bind("<Button-3>", lambda e: self._prompt_pair_android())
        ios_btn = tk.Button(
            toolbar, text="iOS Sync", font=FONT_SMALL,
            fg=TEXT_PRIMARY, bg="#0277BD",
            activebackground="#0288D1",
            relief=tk.FLAT, padx=12, pady=3, cursor="hand2",
            command=self._on_ios_sync_btn
        )
        ios_btn.pack(side=tk.LEFT, padx=2)
        ios_btn.bind("<Button-3>", lambda e: self._prompt_pair_android())

        from ratt.hal import android_bridge
        pc_ip, _ = android_bridge.get_wifi_network_info()
        pc_ip_str = pc_ip or "127.0.0.1"
        ip_badge = tk.Button(
            toolbar,
            text=f"PC IP: {pc_ip_str}",
            font=(FONT_FAMILY, 9, "bold"),
            fg="#39FF14",
            bg="#0D1F17",
            activebackground="#133024",
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._copy_and_show_pc_ip,
        )
        ip_badge.pack(side=tk.LEFT, padx=(6, 2))

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

        self.canvas = tk.Canvas(canvas_frame, bg=BG_PRIMARY, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.slots_frame = tk.Frame(self.canvas, bg=BG_PRIMARY)
        self._slots_win = self.canvas.create_window((0, 0), window=self.slots_frame, anchor=tk.NW, tags="frame")

        def _sync_slots_canvas(event=None):
            if not getattr(self, "_slots_alive", False) or not hasattr(self, "canvas") or not self.canvas.winfo_exists():
                return
            try:
                cw = 0
                if event and getattr(event, "widget", None) == self.canvas:
                    cw = event.width
                if cw <= 1:
                    cw = self.canvas.winfo_width()
                if cw <= 1 and hasattr(self, "root"):
                    cw = self.root.winfo_width() - 28
                cw = max(cw, 320)

                ch = max(self.canvas.winfo_height(), 1)
                req_h = max(self.slots_frame.winfo_reqheight(), ch)

                self.canvas.coords(self._slots_win, 0, 0)
                self.canvas.itemconfig(self._slots_win, width=cw)
                self.canvas.configure(scrollregion=(0, 0, cw, req_h))
                self.canvas.xview_moveto(0.0)

                new_cols = 2 if cw >= 950 else 1
                if new_cols != getattr(self, "_current_slot_cols", 1):
                    self._current_slot_cols = new_cols
                    self._refresh_slots()
            except tk.TclError:
                pass

        def _on_slots_frame_configure(event=None):
            if not getattr(self, "_slots_alive", False) or not hasattr(self, "canvas") or not self.canvas.winfo_exists():
                return
            try:
                cw = self.canvas.winfo_width()
                if cw <= 1 and hasattr(self, "root"):
                    cw = self.root.winfo_width() - 28
                cw = max(cw, 320)
                ch = max(self.canvas.winfo_height(), 1)
                req_h = max(self.slots_frame.winfo_reqheight(), ch)
                self.canvas.configure(scrollregion=(0, 0, cw, req_h))
            except tk.TclError:
                pass

        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind("<Configure>", _sync_slots_canvas)
        self.slots_frame.bind("<Configure>", _on_slots_frame_configure)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._scroll_canvas = self.canvas
        self._slots_alive = True
        self._refresh_slots()
        self.root.after_idle(_sync_slots_canvas)
        self.root.after(100, _sync_slots_canvas)

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
        if not (config.has_paid_tier and user.renewal_alert_needed):
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
            tk.Label(gate, text=f"{config.APP_NAME} v{config.VERSION}", font=(FONT_FAMILY, 48, "bold"),
                     fg=LOGO_CYAN, bg=BG_PRIMARY).pack(pady=(40, 10))

        tk.Label(gate, text=f"{config.APP_NAME} v{config.VERSION}", font=(FONT_FAMILY, 28, "bold"),
                 fg=LOGO_CYAN, bg=BG_PRIMARY).pack()
        tk.Label(gate, text="Rapid Access To Text", font=FONT_BODY,
                 fg=TEXT_SECONDARY, bg=BG_PRIMARY).pack(pady=(0, 4))
        tk.Label(gate, text="by Cybrox", font=FONT_SMALL,
                 fg=TEXT_MUTED, bg=BG_PRIMARY).pack(pady=(0, 30))
        tk.Label(gate, text="Sign in with your Cybrox account to start using RATT.",
                 font=FONT_BODY, fg=TEXT_PRIMARY, bg=BG_PRIMARY).pack(pady=(0, 4))
        tk.Label(gate, text="Sign-up, sign-in, password changes, and profile name updates are available on the Cybrox website.",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_PRIMARY).pack(pady=(0, 20))
        tk.Button(gate, text="Sign In / Activate Account",
                  font=(FONT_FAMILY, 12, "bold"),
                  fg=LOGO_DARK, bg=LOGO_BLUE, activebackground=LOGO_CYAN,
                  relief=tk.FLAT, padx=24, pady=10, cursor="hand2",
                  command=self._open_signup).pack()
        from ratt.config import open_cybrox_web
        tk.Button(gate, text="Sign Up / Sign In",
                  font=FONT_SMALL, fg=ACCENT, bg=BG_PRIMARY, activebackground=BG_PRIMARY,
                  activeforeground=ACCENT_HOVER, relief=tk.FLAT, cursor="hand2",
                  command=lambda: open_cybrox_web(config.CYBROX_SIGNUP_URL)).pack(pady=(8, 0))
        tk.Label(gate, text="Free Basic Plan  |  No credit card required  |  Upgrade anytime",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_PRIMARY).pack(pady=(8, 0))

    def _refresh_slots(self):
        """Refresh the clipboard slot display (only when the slots view is showing)."""
        slots = self.clipboard_manager.get_all_slots()
        cols = getattr(self, "_current_slot_cols", 1)
        if self._slots_alive:
            try:
                for widget in self.slots_frame.winfo_children():
                    widget.destroy()

                # Responsive column weight configuration
                if cols == 2:
                    self.slots_frame.columnconfigure(0, weight=1, uniform="slot_col")
                    self.slots_frame.columnconfigure(1, weight=1, uniform="slot_col")
                else:
                    try:
                        self.slots_frame.tk.call('grid', 'columnconfigure', self.slots_frame._w, 0, '-uniform', '')
                        self.slots_frame.tk.call('grid', 'columnconfigure', self.slots_frame._w, 1, '-uniform', '')
                    except tk.TclError:
                        pass
                    self.slots_frame.columnconfigure(0, weight=1)
                    self.slots_frame.columnconfigure(1, weight=0)

                total_slots = config.max_slots
                base_slots = list(range(1, min(total_slots, MAX_RENDERED_SLOTS) + 1))
                extra_filled = [s for s in sorted(slots.keys()) if s > MAX_RENDERED_SLOTS and s <= total_slots]
                to_render = base_slots + extra_filled[:MAX_RENDERED_SLOTS]

                if cols == 2:
                    for idx, slot_num in enumerate(to_render):
                        r = idx // 2
                        c = idx % 2
                        self._create_slot_widget(slot_num, slots.get(slot_num), row=r, col=c)
                else:
                    for idx, slot_num in enumerate(to_render):
                        self._create_slot_widget(slot_num, slots.get(slot_num), row=None, col=None)

                if total_slots > MAX_RENDERED_SLOTS:
                    lbl = tk.Label(
                        self.slots_frame,
                        text=f"Showing slots 1\u2013{MAX_RENDERED_SLOTS} (plus any filled slots). "
                             f"Slots {MAX_RENDERED_SLOTS + 1}\u2013{total_slots:,} are ready via Ctrl+C/X/V + slot number.",
                        font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_PRIMARY, pady=8
                    )
                    if cols == 2:
                        lbl.grid(row=(len(to_render) + 1) // 2, column=0, columnspan=2, sticky="ew")
                    else:
                        lbl.pack(fill=tk.X, pady=8)

                # Ensure canvas window and scrollregion match current width
                if getattr(self, "_slots_alive", False) and hasattr(self, "canvas") and hasattr(self, "_slots_win"):
                    cw = max(self.canvas.winfo_width(), 320)
                    ch = max(self.canvas.winfo_height(), 1)
                    req_h = max(self.slots_frame.winfo_reqheight(), ch)
                    self.canvas.coords(self._slots_win, 0, 0)
                    self.canvas.itemconfig(self._slots_win, width=cw)
                    self.canvas.configure(scrollregion=(0, 0, cw, req_h))
            except tk.TclError:
                pass

        tier_text = config.user.tier.value.title()
        state_badge = "ON (Active)" if config.enabled else "OFF (Keyboard & Mouse Released \u2014 Ctrl+Alt+P)"
        from ratt.hal import android_bridge
        pc_ip, _ = android_bridge.get_wifi_network_info()
        ip_display = f"PC IP: {pc_ip}  |  " if pc_ip else ""
        try:
            self.status_label.config(
                text=f"  {ip_display}{config.APP_NAME} v{config.VERSION} [{state_badge}]  |  "
                     f"{tier_text} ({config.max_slots:,} slots)  |  {len(slots)} slot(s) in use",
                fg=TEXT_SECONDARY if config.enabled else "#FFC107",
            )
        except (tk.TclError, AttributeError):
            pass

    def _create_slot_widget(self, slot_num, slot, row=None, col=None):
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
        
        frame = tk.Frame(self.slots_frame, bg=slot_bg, pady=7, padx=10)
        if row is not None and col is not None:
            frame.grid(row=row, column=col, sticky="nsew", padx=6, pady=3)
        else:
            frame.pack(fill=tk.X, expand=True, padx=6, pady=3)
        frame.configure(highlightbackground=border_color, highlightthickness=1)
        
        # Left: color indicator + slot number
        left = tk.Frame(frame, bg=slot_bg)
        left.pack(side=tk.LEFT, fill=tk.Y)
        
        indicator = tk.Canvas(left, width=5, height=36, bg=indicator_color, highlightthickness=0)
        indicator.pack(side=tk.LEFT, padx=(0, 6))
        
        tk.Label(
            left, text=f"#{slot_num}", font=FONT_HEADING,
            fg=num_color, bg=slot_bg, width=3
        ).pack(side=tk.LEFT)
        
        # Right: action buttons packed FIRST so they are ALWAYS visible even on small/compact screens
        right = tk.Frame(frame, bg=slot_bg)
        right.pack(side=tk.RIGHT, padx=(4, 0))
        
        if not is_empty:
            tk.Button(
                right, text="Paste", font=FONT_SMALL,
                fg=TEXT_PRIMARY, bg=ACCENT, activebackground=ACCENT_HOVER,
                relief=tk.FLAT, padx=7, pady=2, cursor="hand2",
                command=lambda s=slot_num: self._paste_slot(s)
            ).pack(side=tk.LEFT, padx=2)
            
            tk.Button(
                right, text="X", font=FONT_SMALL,
                fg=TEXT_SECONDARY, bg=BG_HOVER, activebackground=BG_ACTIVE,
                relief=tk.FLAT, padx=5, pady=2, cursor="hand2",
                command=lambda s=slot_num: self._clear_slot(s)
            ).pack(side=tk.LEFT, padx=2)

        # Middle: content
        mid = tk.Frame(frame, bg=slot_bg)
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)
        
        if not is_empty:
            act_val = getattr(getattr(slot, "action", None), "value", "copy")
            action_icon = "[COPY]" if act_val == "copy" else "[CUT]"
            type_badge = f"[{getattr(slot, 'type_badge', 'TEXT')}]"
            raw_preview = getattr(slot, "preview", "") or ""
            
            # Format preview preserving file extension if present
            if "." in raw_preview and len(raw_preview) > 65:
                parts = raw_preview.rsplit(".", 1)
                if len(parts) == 2 and 1 <= len(parts[1]) <= 6 and not (" " in parts[1]):
                    name, ext = parts
                    display_preview = name[:55] + "..." + "." + ext
                else:
                    display_preview = raw_preview[:65] + "..."
            else:
                display_preview = (raw_preview[:65] + "...") if len(raw_preview) > 68 else raw_preview

            preview_text = f"{action_icon} {type_badge} {display_preview}"
            time_text = slot.timestamp.strftime("%H:%M:%S") if getattr(slot, "timestamp", None) else ""
            size_text = getattr(slot, "size_label", f"{getattr(slot, 'char_count', 0)} chars")
            
            tk.Label(
                mid, text=preview_text, font=FONT_BODY,
                fg=TEXT_PRIMARY, bg=slot_bg, anchor=tk.W
            ).pack(fill=tk.X)
            
            tk.Label(
                mid, text=f"{time_text}  |  {size_text}  |  Inert Guard",
                font=FONT_SMALL, fg=TEXT_MUTED, bg=slot_bg, anchor=tk.W
            ).pack(fill=tk.X)
        else:
            tk.Label(
                mid, text="Empty", font=(FONT_FAMILY, 10, "italic"),
                fg="#4A4A4A", bg=slot_bg, anchor=tk.W
            ).pack(fill=tk.X)
            tk.Label(
                mid, text=f"Ctrl+C then {slot_num if slot_num < 10 else 0} to save text, image or file",
                font=FONT_SMALL, fg="#333333", bg=slot_bg, anchor=tk.W
            ).pack(fill=tk.X)
    
    def _paste_slot(self, slot_num):
        """Paste from a slot."""
        from ratt.clipboard_manager import SlotAction, SlotContentType
        slot_obj = self.clipboard_manager.get_slot(slot_num)
        result = self.clipboard_manager.paste_from_slot(slot_num)
        if result:
            if slot_obj and slot_obj.content_type == SlotContentType.FILES:
                target_dir = None
                if hasattr(self, "daemon") and self.daemon:
                    exp_folder, _ = self.daemon.query_explorer_context(None)
                    if exp_folder and os.path.isdir(exp_folder):
                        target_dir = exp_folder
                if not target_dir:
                    from tkinter import filedialog
                    target_dir = filedialog.askdirectory(
                        title=f"Select Destination Folder to Paste Slot #{slot_num} File(s)",
                        parent=self.root,
                    )
                if target_dir and os.path.isdir(target_dir):
                    from ratt.actions import _safe_copy_or_move_files
                    is_cut = slot_obj.action == SlotAction.CUT
                    ok, msg = _safe_copy_or_move_files(slot_obj.files, target_dir, is_cut=is_cut)
                    if ok:
                        if is_cut:
                            self.clipboard_manager.clear_slot(slot_num)
                            self._refresh_slots()
                        self.show_notification(f"Slot #{slot_num}: {msg}")
                    else:
                        self.show_notification(msg, is_error=True)
                    return
            self.show_notification(f"Pasted from Slot #{slot_num}")
        elif self.clipboard_manager.last_error:
            err = self.clipboard_manager.last_error
            if err.startswith("UPGRADE_REQUIRED:"):
                self.request_upgrade(err.split("UPGRADE_REQUIRED:", 1)[1].strip())
            else:
                self.show_notification(err, is_error=True)
    
    def _clear_slot(self, slot_num):
        """Clear a slot."""
        self.clipboard_manager.clear_slot(slot_num)
        self._refresh_slots()
    
    def _clear_all(self):
        """Clear all slots."""
        if messagebox.askyesno("Clear All", "Clear all clipboard slots?", parent=self.root):
            self.clipboard_manager.clear_all()
            self._refresh_slots()

    def _show_android_pair_dialog(self, initial_ip: str = "", err_msg: Optional[str] = None):
        """Show a unified secure PC <-> Android PIN pairing dialog (works in either direction)."""
        from ratt.hal import android_bridge
        import threading
        import tkinter as tk

        pc_ip, gw_ip = android_bridge.get_wifi_network_info()
        current_ip = initial_ip or android_bridge.get_paired_android_ip()
        default_ip = current_ip if current_ip and current_ip not in ("127.0.0.1", "localhost") else (gw_ip or "")
        pc_pin = android_bridge.generate_pairing_pin()

        dlg = tk.Toplevel(self.root)
        dlg.title("Pair iPhone (iOS) or Android Phone — Wi-Fi Sync")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.resizable(True, True)

        # Pack bottom buttons and status bar FIRST so they can NEVER be clipped at any DPI scaling
        bottom_bar = tk.Frame(dlg, padx=18, pady=12, bg="#f1f5f9")
        bottom_bar.pack(side="bottom", fill="x")

        pair_btn = tk.Button(
            bottom_bar,
            text="Pair Now",
            width=14,
            bg="#0284c7",
            fg="white",
            activebackground="#0369a1",
            activeforeground="white",
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        )
        close_btn = tk.Button(bottom_bar, text="Close", command=dlg.destroy, width=10, font=("Segoe UI", 10))
        pair_btn.pack(side="right", padx=(8, 0))
        close_btn.pack(side="right")

        status_var = tk.StringVar(value="Enter the Phone 6-Digit PIN shown on Android, then click Pair Now (or press Enter).")
        status_lbl = tk.Label(
            dlg,
            textvariable=status_var,
            fg="#0369a1",
            font=("Segoe UI", 9, "bold"),
            justify="left",
            anchor="w",
            wraplength=500,
            padx=18,
            pady=4,
        )
        status_lbl.pack(side="bottom", fill="x")

        frame = tk.Frame(dlg, padx=18, pady=12)
        frame.pack(side="top", fill="both", expand=True)

        if err_msg:
            tk.Label(
                frame,
                text=f"Pairing required ({err_msg})",
                fg="#b91c1c",
                font=("Segoe UI", 9, "bold"),
                justify="left",
                anchor="w",
                wraplength=500,
            ).pack(fill="x", pady=(0, 8))

        info_text = (
            f"THIS PC IP ADDRESS:  {pc_ip or '127.0.0.1'}   |   PC PIN (Android):  {pc_pin}\n\n"
            f"• Option A (From iPhone / iOS): On iPhone RATT -> tap 'Pair with PC',\n"
            f"  enter PC IP: {pc_ip or '<your-pc-ip>'} and tap 'Save & Pair Now'.\n"
            f"• Option B (From Android): On Android RATT -> tap 'Pair with PC',\n"
            f"  enter PC IP: {pc_ip or '<your-pc-ip>'} and PC PIN: {pc_pin}.\n"
            f"• Option C (From PC): Enter your iPhone or Android IP below and click 'Pair Now':"
        )
        tk.Label(frame, text=info_text, font=("Segoe UI", 9, "bold"), justify="left", anchor="w", wraplength=500).pack(fill="x", pady=(0, 10))

        row1 = tk.Frame(frame)
        row1.pack(fill="x", pady=4)
        tk.Label(row1, text="Phone IP Address:", width=18, anchor="w", font=("Segoe UI", 9, "bold")).pack(side="left")
        ip_var = tk.StringVar(value=default_ip)
        ip_entry = tk.Entry(row1, textvariable=ip_var, width=28, font=("Consolas", 10))
        ip_entry.pack(side="left", fill="x", expand=True)

        row2 = tk.Frame(frame)
        row2.pack(fill="x", pady=4)
        tk.Label(row2, text="Android PIN (opt):", width=18, anchor="w", font=("Segoe UI", 9, "bold")).pack(side="left")
        pin_var = tk.StringVar(value="")
        pin_entry = tk.Entry(row2, textvariable=pin_var, width=28, font=("Consolas", 10))
        pin_entry.pack(side="left", fill="x", expand=True)

        def on_pair_now(_event=None):
            target_ip = ip_var.get().strip()
            entered_pin = pin_var.get().strip()
            if not target_ip:
                status_var.set("Please enter your iPhone or Android Phone's IP address.")
                return
            android_bridge.set_paired_android_ip(target_ip)
            if entered_pin == pc_pin:
                status_var.set("That is the PC PIN. For iPhone leave PIN blank; for Android enter the Phone's PIN.")
                return
            pair_btn.config(state="disabled", text="Pairing...")
            status_var.set(f"Pairing with {target_ip} (port 49211 / 49210)...")

            def _do_pair():
                ok, msg = android_bridge.pair_with_android_device(target_ip, pin=entered_pin)
                def _finish():
                    if not dlg.winfo_exists():
                        return
                    pair_btn.config(state="normal", text="Pair Now")
                    if ok:
                        dlg.destroy()
                        self.show_notification(msg)
                        if "iPhone" in msg or "iOS" in msg:
                            self.root.after(150, self._on_ios_sync_btn)
                        else:
                            self.root.after(150, self._on_android_sync_btn)
                    else:
                        status_lbl.config(fg="#b91c1c")
                        status_var.set(msg)
                self.root.after(0, _finish)

            threading.Thread(target=_do_pair, daemon=True).start()

        pair_btn.config(command=on_pair_now)
        for widget in (dlg, ip_entry, pin_entry):
            widget.bind("<Return>", on_pair_now)
            widget.bind("<KP_Enter>", on_pair_now)

        dlg.minsize(520, 380)
        dlg.geometry("560x420")
        pin_entry.focus_set()

    def _prompt_pair_android(self):
        """Allow user to pair securely with Android using a 6-digit Pairing PIN."""
        self._show_android_pair_dialog()

    def _on_android_sync_btn(self):
        """Handle Android Sync button click from the main toolbar."""
        import sys
        if not sys.platform.startswith("win") and not config.is_premium:
            from ratt.clipboard_manager import UPGRADE_CROSS_SYNC_MSG
            self.request_upgrade(UPGRADE_CROSS_SYNC_MSG.split("UPGRADE_REQUIRED:", 1)[1].strip())
            return
        from ratt.hal import android_bridge
        paired_ip = android_bridge.get_paired_android_ip()
        if not paired_ip or paired_ip in ("127.0.0.1", "localhost"):
            from tkinter import simpledialog
            ip = simpledialog.askstring(
                "Pair Android Phone",
                "Enter the Phone IP Address shown on your RATT phone screen (e.g. 192.168.100.X):",
                parent=self.root
            )
            if ip and ip.strip():
                android_bridge.set_paired_android_ip(ip.strip())
                paired_ip = ip.strip()
            else:
                return

        # 1. Pull slots from Phone
        import json
        import urllib.request
        pulled_count = 0
        cleared_count = 0
        cleared_slots = []
        phone_slots = {}
        pull_err = None
        try:
            url = f"http://{paired_ip}:49210/get_all_slots"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "RATT-PC", "X-RATT-Token": android_bridge.get_pc_sync_token()},
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                raw_resp = resp.read().decode("utf-8")
                data = json.loads(raw_resp)
                phone_slots = data.get("slots", {})
                cleared_slots = [int(x) for x in data.get("cleared_slots", []) if str(x).isdigit()]
                for s_num in cleared_slots:
                    cur_slot = self.clipboard_manager.get_slot(s_num)
                    if cur_slot and not cur_slot.is_empty:
                        self.clipboard_manager.clear_slot(s_num)
                        cleared_count += 1
                from ratt.clipboard_manager import SlotContentType
                for slot_str, content in phone_slots.items():
                    try:
                        s_num = int(slot_str)
                        if s_num in range(1, 11):
                            if s_num in cleared_slots:
                                continue
                            cur_slot = self.clipboard_manager.get_slot(s_num)
                            # Never overwrite or clear rich files or images on PC via general mobile pull
                            if cur_slot and cur_slot.content_type in (SlotContentType.FILES, SlotContentType.IMAGE, SlotContentType.DIAGRAM):
                                continue
                            elif content:
                                self.clipboard_manager.copy_to_slot(s_num, text=content)
                                pulled_count += 1
                    except Exception:
                        pass
        except Exception as e:
            pull_err = str(e)
            # Automatic Hotspot fallback: if paired_ip failed, try the detected Wi-Fi Hotspot Gateway
            pc_ip, gw_ip = android_bridge.get_wifi_network_info()
            if gw_ip and gw_ip != paired_ip:
                try:
                    url = f"http://{gw_ip}:49210/get_all_slots"
                    req = urllib.request.Request(
                        url,
                        headers={"User-Agent": "RATT-PC", "X-RATT-Token": android_bridge.get_pc_sync_token()},
                    )
                    with urllib.request.urlopen(req, timeout=4.0) as resp:
                        raw_resp = resp.read().decode("utf-8")
                        data = json.loads(raw_resp)
                        phone_slots = data.get("slots", {})
                        cleared_slots = [int(x) for x in data.get("cleared_slots", []) if str(x).isdigit()]
                        for s_num in cleared_slots:
                            cur_slot = self.clipboard_manager.get_slot(s_num)
                            if cur_slot and not cur_slot.is_empty:
                                self.clipboard_manager.clear_slot(s_num)
                                cleared_count += 1
                        from ratt.clipboard_manager import SlotContentType
                        for slot_str, content in phone_slots.items():
                            try:
                                s_num = int(slot_str)
                                if s_num in range(1, 11):
                                    if s_num in cleared_slots:
                                        continue
                                    cur_slot = self.clipboard_manager.get_slot(s_num)
                                    if cur_slot and cur_slot.content_type in (SlotContentType.FILES, SlotContentType.IMAGE, SlotContentType.DIAGRAM):
                                        continue
                                    if content:
                                        self.clipboard_manager.copy_to_slot(s_num, text=content)
                                        pulled_count += 1
                            except Exception:
                                pass
                        pull_err = None
                        paired_ip = gw_ip
                        android_bridge.set_paired_android_ip(gw_ip)
                except Exception:
                    pass

            if pull_err:
                self._show_android_pair_dialog(initial_ip=gw_ip or paired_ip, err_msg=pull_err)
                return

        # 2. Push PC slots to Phone if phone slot is empty or different
        pc_slots = self.clipboard_manager.get_all_slots()
        pushed_count = 0
        for slot_num, slot_obj in pc_slots.items():
            if slot_num in cleared_slots:
                continue
            if slot_obj and not slot_obj.is_empty:
                slot_str = str(slot_num)
                phone_content = phone_slots.get(slot_str, "")
                pc_content = slot_obj.content or slot_obj.preview or ""
                if not phone_content or phone_content != pc_content:
                    try:
                        if self.clipboard_manager.copy_to_android(slot_num):
                            pushed_count += 1
                    except Exception:
                        pass

        # 3. Inject Slot 1 into Windows clipboard
        slot1 = self.clipboard_manager.get_slot(1)
        if slot1 and not slot1.is_empty:
            try:
                from ratt.hal import win32
                win32.write_clipboard_bundle(slot1.get_bundle())
            except Exception:
                pass

        self._refresh_slots()
        self.daemon.sync_now()

        if pulled_count > 0 or cleared_count > 0 or pushed_count > 0:
            details = []
            if pulled_count > 0:
                details.append(f"Pulled {pulled_count}")
            if cleared_count > 0:
                details.append(f"Cleared {cleared_count}")
            if pushed_count > 0:
                details.append(f"Pushed {pushed_count}")
            self.show_notification(
                f"Sync Complete! {', '.join(details)} with Phone ({paired_ip})."
            )
        elif phone_slots:
            self.show_notification(f"Synced with Phone ({paired_ip}): All slots are up to date.")
        elif pull_err:
            self.show_notification(f"Phone ({paired_ip}) connection failed ({pull_err}). Make sure RATT is open on your phone and on the same Wi-Fi.", is_error=True)
        else:
            self.show_notification(
                f"Connected to Phone ({paired_ip}), but no slots contain data yet. Copy text on Phone or PC to start syncing!"
            )

    def _copy_and_show_pc_ip(self):
        """Copy this PC's LAN IPv4 address to the clipboard and open the Phone Pairing dialog."""
        from ratt.hal import android_bridge
        pc_ip, _ = android_bridge.get_wifi_network_info()
        ip_str = pc_ip or "127.0.0.1"
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(ip_str)
        except Exception:
            pass
        self.show_notification(f"PC IP ({ip_str}) copied! Enter this IP in RATT on your iPhone or Android.")
        self._show_android_pair_dialog()

    def _on_ios_sync_btn(self):
        """Handle iOS Sync button click from the main toolbar (two-way Wi-Fi sync on port 49211)."""
        from ratt.hal import android_bridge
        import json
        import urllib.request

        paired_ip = android_bridge.get_paired_android_ip()
        if not paired_ip or paired_ip in ("127.0.0.1", "localhost"):
            self._show_android_pair_dialog()
            return

        pulled_count = 0
        pushed_count = 0
        phone_slots = {}
        try:
            url = f"http://{paired_ip}:49211/get_all_slots"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "RATT-PC", "X-RATT-Token": android_bridge.get_pc_sync_token()},
            )
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                phone_slots = data.get("slots", {})
                from ratt.clipboard_manager import SlotContentType
                for slot_str, content in phone_slots.items():
                    if str(slot_str).isdigit():
                        s_num = int(slot_str)
                        if 1 <= s_num <= 10 and content:
                            cur_slot = self.clipboard_manager.get_slot(s_num)
                            if cur_slot and cur_slot.content_type in (SlotContentType.FILES, SlotContentType.IMAGE, SlotContentType.DIAGRAM):
                                continue
                            self.clipboard_manager.copy_to_slot(s_num, text=content)
                            pulled_count += 1
        except Exception as e:
            self._show_android_pair_dialog(initial_ip=paired_ip, err_msg=str(e))
            return

        pc_slots = self.clipboard_manager.get_all_slots()
        for slot_num, slot_obj in pc_slots.items():
            if 1 <= slot_num <= 10 and slot_obj and not slot_obj.is_empty:
                pc_content = slot_obj.content or slot_obj.preview or ""
                if pc_content and phone_slots.get(str(slot_num), "") != pc_content:
                    try:
                        payload = json.dumps({
                            "action": "SYNC_TO_PHONE",
                            "slot_id": slot_num,
                            "content": pc_content,
                            "timestamp": time.time(),
                            "nonce": f"{int(time.time()*1000)}_{slot_num}",
                        }).encode("utf-8")
                        req = urllib.request.Request(
                            f"http://{paired_ip}:49211/sync_slot",
                            data=payload,
                            headers={
                                "Content-Type": "application/json",
                                "User-Agent": "RATT-PC",
                                "X-RATT-Token": android_bridge.get_pc_sync_token(),
                            },
                            method="POST",
                        )
                        with urllib.request.urlopen(req, timeout=2.5) as _:
                            pushed_count += 1
                    except Exception:
                        pass

        self._refresh_slots()
        self.show_notification(
            f"iPhone (iOS) Sync Complete ({paired_ip}): Pulled {pulled_count}, Pushed {pushed_count} slot(s)."
        )
    
    def copy_to_slot(self, slot_num):
        """Copy current clipboard content to a slot."""
        success = self.clipboard_manager.copy_to_slot(slot_num)
        if success:
            self.show_notification(f"Copied to Slot #{slot_num}")
            self._refresh_slots()
        elif self.clipboard_manager.last_error:
            err = self.clipboard_manager.last_error
            if err.startswith("UPGRADE_REQUIRED:"):
                self.request_upgrade(err.split("UPGRADE_REQUIRED:", 1)[1].strip())
            else:
                self.show_notification(err, is_error=True)
    
    def cut_to_slot(self, slot_num):
        """Cut current clipboard content to a slot."""
        success = self.clipboard_manager.cut_to_slot(slot_num)
        if success:
            self.show_notification(f"Cut to Slot #{slot_num}")
            self._refresh_slots()
        elif self.clipboard_manager.last_error:
            err = self.clipboard_manager.last_error
            if err.startswith("UPGRADE_REQUIRED:"):
                self.request_upgrade(err.split("UPGRADE_REQUIRED:", 1)[1].strip())
            else:
                self.show_notification(err, is_error=True)

    def request_upgrade(self, reason: str):
        """Display an upgrade request when a Basic user attempts a Premium/Enterprise feature."""
        self.show_notification(reason, duration=4500, is_error=True)
        try:
            self.show_main_window()
            want_upgrade = messagebox.askyesno(
                "Upgrade to Premium / Enterprise",
                f"{reason}\n\nWould you like to upgrade to Premium or Enterprise now?",
                parent=self.root,
            )
            if want_upgrade:
                self._open_payment("premium")
        except Exception:
            pass

    def request_upgrade_async(self, reason: str):
        """Queue an upgrade prompt from any worker thread for the Tk main loop."""
        self._upgrade_queue.append(reason)
    
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

    def show_share_dialog(self):
        if not config.is_premium:
            self.request_upgrade("Account Sharing (copy/cut/paste across different RATT accounts) is limited to Premium and Enterprise subscribers.")
            return
        from ratt.ui.share_dialog import ShareDialog
        self._open_dialog("share", ShareDialog)

    def show_mirror_dialog(self):
        if not config.is_premium:
            self.request_upgrade("Device Mirroring across RATT devices is limited to Premium and Enterprise subscribers.")
            return
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
        try:
            self.root.attributes("-topmost", True)
            self.root.after(120, lambda: self.root.attributes("-topmost", False))
        except Exception:
            pass
        self._refresh_slots()

    # Aliases
    def show_settings(self): self._open_settings()
    def show_help(self): self._open_help()
    def show_signup_dialog(self): self._open_signup()

    def _popup(self):
        from ratt.ui.clipboard_popup import ClipboardPopup
        if not hasattr(self, '_clipboard_popup'):
            self._clipboard_popup = ClipboardPopup(self.root, self)
        return self._clipboard_popup

    def show_popup(self):
        """Show the clipboard popup menu (one at a time)."""
        self._popup().show_at_cursor()

    def show_translate_picker(self, code):
        """Ask which slot to translate into the chosen language."""
        self._popup().show_translate_picker(code)

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
            if user.is_logged_in and config.has_paid_tier and user.should_show_renewal_alert():
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

    def _start_android_auto_sync(self):
        """Active background daemon that auto-polls paired phone for slot changes every 1.5s.
        Instantly detects and reflects slot clearances and new copies, guaranteeing real-time
        cross-platform synchronization even if incoming ports are firewalled.
        """
        import threading, time, urllib.request, json
        from ratt.hal import android_bridge

        def _worker():
            while True:
                time.sleep(1.5)
                try:
                    paired_ip = android_bridge.get_paired_android_ip()
                    if not paired_ip or paired_ip in ("127.0.0.1", "localhost"):
                        continue
                    url = f"http://{paired_ip}:49210/get_all_slots"
                    req = urllib.request.Request(
                        url,
                        headers={"User-Agent": "RATT-PC-AutoSync", "X-RATT-Token": android_bridge.get_pc_sync_token()},
                    )
                    with urllib.request.urlopen(req, timeout=1.2) as resp:
                        raw = resp.read().decode("utf-8")
                        data = json.loads(raw)
                        phone_slots = data.get("slots", {})
                        cleared_slots = [int(x) for x in data.get("cleared_slots", []) if str(x).isdigit()]
                        changed = False
                        for c_slot in cleared_slots:
                            try:
                                cur = self.clipboard_manager.get_slot(c_slot)
                                if cur and not cur.is_empty:
                                    self.clipboard_manager.clear_slot(c_slot)
                                    changed = True
                            except Exception:
                                pass
                        for s_num in range(1, 11):
                            if s_num in cleared_slots:
                                continue
                            s_str = str(s_num)
                            if s_str in phone_slots:
                                p_content = phone_slots[s_str]
                                cur = self.clipboard_manager.get_slot(s_num)
                                from ratt.clipboard_manager import SlotContentType
                                if p_content:
                                    # Phone has new/different content -> pull to PC
                                    if not cur or cur.content != p_content:
                                        if not (cur and cur.content_type in (SlotContentType.FILES, SlotContentType.IMAGE, SlotContentType.DIAGRAM)):
                                            self.clipboard_manager.copy_to_slot(s_num, text=p_content)
                                            changed = True
                        if changed:
                            self._clip_dirty = True
                            try:
                                self.root.after(0, self._refresh_slots)
                            except Exception:
                                pass
                except Exception:
                    pass

        t = threading.Thread(target=_worker, daemon=True, name="RattAndroidAutoSync")
        t.start()

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
        """Quit the application completely and release all hooks and resources."""
        try:
            if hasattr(self, "tray_icon") and self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        try:
            if hasattr(self, "daemon") and self.daemon:
                self.daemon.send_command("QUIT")
        except Exception:
            pass
        try:
            self.clipboard_manager.clear_all()
        except Exception:
            pass
        try:
            self.root.quit()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def _on_clipboard_changed(self):
        """Slots changed (may be called from any thread): flag it; the Tk thread
        refreshes the slot list and right-click menu on its next poll."""
        self._clip_dirty = True

    # ========== REQUESTS FROM OTHER THREADS AND PROCESSES ==========

    def queue_action(self, action, args):
        """Ask the Tk thread to run an action (safe to call from any thread)."""
        self._pending_actions.append((action, list(args)))

    def notify_async(self, message, is_error=False):
        """Show a notification from any thread; the Tk thread displays it on its next poll."""
        self._notify_queue.append((message, is_error))

    def request_show(self):
        """A second launch of RATT asks the running one to come to the front."""
        now = time.time()
        if now - getattr(self, "_last_show_req", 0.0) >= 1.0:
            self._last_show_req = now
            self._show_requested = True

    def _poll(self):
        # Always check for background context menu action handed over from another process
        consumed_action = False
        try:
            appdata = os.environ.get("APPDATA", "")
            if appdata:
                p_file = os.path.join(appdata, "RATT", "pending_action.txt")
                if os.path.exists(p_file):
                    with open(p_file, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read().strip()
                    try:
                        os.remove(p_file)
                    except Exception:
                        pass
                    if content:
                        tokens = content.split("\t")
                        self.queue_action(tokens[0], tokens[1:])
                        consumed_action = True
        except Exception:
            pass
        if self._show_requested:
            self._show_requested = False
            if not consumed_action:
                self.show_main_window()
        if self._clip_dirty:
            self._clip_dirty = False
            self._refresh_slots()
            self._update_context_menu()
        while self._notify_queue:
            message, is_error = self._notify_queue.pop(0)
            self.show_notification(message, is_error=is_error)
        while self._upgrade_queue:
            reason = self._upgrade_queue.pop(0)
            self.request_upgrade(reason)
        while self._pending_actions:
            action, args = self._pending_actions.pop(0)
            try:
                self.actions.run(action, args)
            except Exception as error:
                from ratt import native
                native.log("app", f"action {action} {args} failed: {error!r}")
        self.daemon.tick()
        self.root.after(150, self._poll)

    def run(self):
        """Start the application."""
        try:
            from ratt.tray_icon import TrayIcon
            self.tray_icon = TrayIcon(self.root, self)
            self.tray_icon.start()
        except Exception:
            pass

        instance.watch_for_show(self.request_show)

        # Initial context menu update to reflect current slot count
        self.root.after(1000, self._update_context_menu)

        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
