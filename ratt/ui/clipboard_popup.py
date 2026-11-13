"""RATT Clipboard Popup Menu.

Hierarchical floating menu (no borders):
- Open RATT
- Copy to Slot > (colored slots)
- Cut to Slot > (colored slots)
- Paste from Slot > (only filled slots, with colored dots)
- Share (7-day countdown for basic, greyed after)
- Mirror (7-day countdown for basic, greyed after)
- Translate > (Premium/Enterprise only)

All users must be signed up to use features.
"""
import tkinter as tk
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ratt.app import RattApp

from ratt.ui.styles import *
from ratt.config import config, TRANSLATE_LANGUAGES

# Menu colors (no borders)
_BG = "#0D2137"
_BG_H = "#1A3A5C"  # hover
_HEAD = "#0A1929"
_SEP = "#152D45"


class ClipboardPopup:
    """Floating popup menu for clipboard operations."""
    
    def __init__(self, root: tk.Tk, app: 'RattApp'):
        self.root = root
        self.app = app
        self.popup: Optional[tk.Toplevel] = None
        self.submenu: Optional[tk.Toplevel] = None
    
    def show_at_cursor(self):
        self.dismiss()
        
        # Check signup requirement
        if not config.user.is_logged_in:
            self._show_signup_required()
            return
        
        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()
        
        self.popup = tk.Toplevel(self.root)
        self.popup.overrideredirect(True)
        self.popup.attributes("-topmost", True)
        self.popup.configure(bg=_BG)
        
        main = tk.Frame(self.popup, bg=_BG)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Header
        hdr = tk.Frame(main, bg=_HEAD, padx=12, pady=8)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text=f"{config.APP_NAME} v{config.VERSION}", font=(FONT_FAMILY, 13, "bold"),
                 fg="#00BFFF", bg=_HEAD).pack(side=tk.LEFT)
        tier = config.user.tier.value.title()
        tc = {"basic": "#888", "premium": "#4CAF50", "enterprise": "#CE93D8"}
        tk.Label(hdr, text=f"  [{tier}]", font=FONT_SMALL,
                 fg=tc.get(config.user.tier.value, "#888"), bg=_HEAD).pack(side=tk.LEFT)
        
        _sep(main)

        # Open RATT
        _item(main, "Open RATT", self._on_open, icon="#00BFFF")
        _sep(main)

        # Copy to Slot >
        _item(main, "Copy to Slot", None, arrow=True,
              hover=lambda e: self._show_slot_sub("copy"))
        # Cut to Slot >
        _item(main, "Cut to Slot", None, arrow=True,
              hover=lambda e: self._show_slot_sub("cut"))
        _sep(main)

        # Paste from Slot >
        filled = self.app.clipboard_manager.get_all_slots()
        has = len(filled) > 0
        _item(main, "Paste from Slot", None, arrow=has, enabled=has,
              hover=lambda e: self._show_paste_sub() if has else None)
        _sep(main)

        # Share — 7 day countdown for basic
        trial = config.user.is_trial_active
        days = config.user.trial_days_remaining
        if config.is_premium:
            share_lbl = "Share"
            share_ok = True
        elif trial:
            share_lbl = f"Share  ({days} day{'s' if days != 1 else ''} left)"
            share_ok = True
        else:
            share_lbl = "Share  (Trial expired)"
            share_ok = False

        contacts = config.user.all_contacts
        if share_ok and len(contacts) > 0:
            _item(main, share_lbl, None, arrow=True, icon="#2196F3",
                  hover=lambda e: self._show_contact_sub("share"))
        else:
            _item(main, share_lbl, self._on_share, enabled=share_ok, icon="#2196F3")

        # Mirror — same rules
        if config.is_premium:
            mirror_lbl = "Mirror"
            mirror_ok = True
        elif trial:
            mirror_lbl = f"Mirror  ({days} day{'s' if days != 1 else ''} left)"
            mirror_ok = True
        else:
            mirror_lbl = "Mirror  (Trial expired)"
            mirror_ok = False

        if mirror_ok and len(contacts) > 0:
            _item(main, mirror_lbl, None, arrow=True, icon="#9C27B0",
                  hover=lambda e: self._show_contact_sub("mirror"))
        else:
            _item(main, mirror_lbl, self._on_mirror, enabled=mirror_ok, icon="#9C27B0")

        _sep(main)

        # Translate — Premium + Enterprise only
        can_translate = config.is_premium  # True for both premium & enterprise
        _item(main, "Translate", None, arrow=can_translate, enabled=can_translate,
              subtitle="" if can_translate else "(Premium / Enterprise)",
              hover=lambda e: self._show_translate_sub() if can_translate else None,
              icon="#4CAF50")

        _sep(main)

        # Android Keyboard (IME) — Premium + Enterprise only; clicking as Basic prompts upgrade
        can_android = config.is_premium
        _item(main, "Android Keyboard (IME)",
              None if can_android else self._on_android_upgrade,
              arrow=can_android, enabled=True,
              subtitle="" if can_android else "(Premium / Enterprise)",
              hover=lambda e: self._show_android_sub() if can_android else None,
              icon="#A4C639")

        # iOS Keyboard (iPhone) — Premium + Enterprise only; clicking as Basic prompts upgrade
        can_ios = config.is_premium
        _item(main, "iOS Keyboard (iPhone)",
              None if can_ios else self._on_ios_upgrade,
              arrow=can_ios, enabled=True,
              subtitle="" if can_ios else "(Premium / Enterprise)",
              hover=lambda e: self._show_ios_sub() if can_ios else None,
              icon="#00BFFF")

        # Position
        self.popup.update_idletasks()
        pw, ph = self.popup.winfo_reqwidth(), self.popup.winfo_reqheight()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        if x + pw > sw: x = sw - pw
        if y + ph > sh: y = sh - ph
        self.popup.geometry(f"+{x}+{y}")
        self.popup.bind("<Escape>", lambda e: self.dismiss())
        self.popup.bind("<FocusOut>", self._focus_out)
        self.popup.focus_set()

    def show_translate_picker(self, code):
        """Small menu at the cursor: which slot should be translated into this language?"""
        self.dismiss()
        if not config.user.is_logged_in:
            self._show_signup_required()
            return
        if not config.is_premium:
            self.app.show_main_window()
            self.app.show_notification("Translate is for Premium and Enterprise users", is_error=True)
            return
        filled = self.app.clipboard_manager.get_all_slots()
        if not filled:
            self.app.show_notification("No slot has data yet - copy something to a slot first", is_error=True)
            return
        name = dict(TRANSLATE_LANGUAGES).get(code, code)
        x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
        self.popup = tk.Toplevel(self.root)
        self.popup.overrideredirect(True)
        self.popup.attributes("-topmost", True)
        self.popup.configure(bg=_BG)
        main = tk.Frame(self.popup, bg=_BG)
        main.pack(fill=tk.BOTH, expand=True)
        tk.Label(main, text=f"Translate to {name} - from which slot?", font=FONT_SMALL,
                 fg="#5599BB", bg=_HEAD, padx=12, pady=8).pack(fill=tk.X)
        _sep(main)
        for num in sorted(filled.keys()):
            self._slot_row(main, num, get_slot_color(num), "translate:" + code,
                           preview=filled[num].preview)
        self.popup.update_idletasks()
        pw, ph = self.popup.winfo_reqwidth(), self.popup.winfo_reqheight()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.popup.geometry(f"+{min(x, sw - pw)}+{min(y, sh - ph)}")
        self.popup.bind("<Escape>", lambda e: self.dismiss())
        self.popup.bind("<FocusOut>", self._focus_out)
        self.popup.focus_force()
        self.popup.after(20000, self.dismiss)      # never leave it hanging around

    def _show_signup_required(self):
        """Show message that signup is required."""
        from tkinter import messagebox
        messagebox.showinfo(
            "Sign Up Required",
            "You must sign up to use RATT features.\n\n"
            "Click the Sign Up button in the RATT window.",
        )
        self.app.show_main_window()

    def _focus_out(self, event):
        focused = self.root.focus_get()
        if self.submenu and focused:
            try:
                if str(focused).startswith(str(self.submenu)):
                    return
            except Exception:
                pass
        self.dismiss()

    # ========== SUBMENUS ==========

    def _open_sub(self, build_fn):
        if self.submenu and self.submenu.winfo_exists():
            self.submenu.destroy()
        self.submenu = tk.Toplevel(self.root)
        self.submenu.overrideredirect(True)
        self.submenu.attributes("-topmost", True)
        self.submenu.configure(bg=_BG)
        inner = tk.Frame(self.submenu, bg=_BG)
        inner.pack(fill=tk.BOTH, expand=True)
        build_fn(inner)
        self.submenu.update_idletasks()
        px = self.popup.winfo_x() + self.popup.winfo_width()
        py = self.popup.winfo_y()
        sw = self.root.winfo_screenwidth()
        sub_w = self.submenu.winfo_reqwidth()
        if px + sub_w > sw:
            px = self.popup.winfo_x() - sub_w
        self.submenu.geometry(f"+{px}+{py}")

    def _show_slot_sub(self, action):
        def build(inner):
            title = "Copy to Slot" if action == "copy" else "Cut to Slot"
            tk.Label(inner, text=title, font=FONT_SMALL,
                     fg="#5599BB", bg=_BG, padx=10, pady=4).pack(anchor=tk.W)
            _sep(inner)
            max_popup_slots = min(config.max_slots, 25)
            for i in range(1, max_popup_slots + 1):
                color = get_slot_color(i)
                slot = self.app.clipboard_manager.get_slot(i)
                has = slot and not slot.is_empty
                self._slot_row(inner, i, color, action,
                               preview=slot.preview if has else None)
            if config.max_slots > max_popup_slots:
                tk.Label(inner, text=f"+ Slots {max_popup_slots + 1}..{config.max_slots:,} via Ctrl+C/X + number",
                         font=FONT_SMALL, fg="#556677", bg=_BG, padx=10, pady=4).pack(anchor=tk.W)
        self._open_sub(build)

    def _show_paste_sub(self):
        def build(inner):
            tk.Label(inner, text="Paste from Slot", font=FONT_SMALL,
                     fg="#5599BB", bg=_BG, padx=10, pady=4).pack(anchor=tk.W)
            _sep(inner)
            filled = self.app.clipboard_manager.get_all_slots()
            for num in sorted(filled.keys()):
                slot = filled[num]
                color = get_slot_color(num)  # Same color as the slot
                self._slot_row(inner, num, color, "paste", preview=slot.preview)
        self._open_sub(build)

    def _show_contact_sub(self, action):
        def build(inner):
            title = "Share with..." if action == "share" else "Mirror with..."
            tk.Label(inner, text=title, font=FONT_SMALL,
                     fg="#5599BB", bg=_BG, padx=10, pady=4).pack(anchor=tk.W)
            _sep(inner)
            # Generate code option
            lbl = "Generate Share Code" if action == "share" else "Generate Mirror Code"
            _contact_row(inner, lbl, None, action, self, is_code=True)
            _sep(inner)
            contacts = config.user.all_contacts
            if contacts:
                for c in contacts:
                    status = " (online)" if c.is_online else ""
                    _contact_row(inner, f"{c.display_name}{status}", c, action, self)
            else:
                tk.Label(inner, text="No connections yet", font=FONT_SMALL,
                         fg="#555", bg=_BG, padx=10, pady=6).pack()
        self._open_sub(build)

    def _show_translate_sub(self):
        def build(inner):
            tk.Label(inner, text="Translate to...", font=FONT_SMALL,
                     fg="#5599BB", bg=_BG, padx=10, pady=4).pack(anchor=tk.W)
            _sep(inner)
            for code, name in TRANSLATE_LANGUAGES:
                f = tk.Frame(inner, bg=_BG, padx=12, pady=4, cursor="hand2")
                f.pack(fill=tk.X)
                tk.Label(f, text=name, font=FONT_BODY, fg=TEXT_PRIMARY, bg=_BG).pack(side=tk.LEFT)
                tk.Label(f, text=code.upper(), font=FONT_SMALL, fg="#556677", bg=_BG).pack(side=tk.RIGHT)
                f.bind("<Enter>", lambda e, fr=f: _hl(fr, True))
                f.bind("<Leave>", lambda e, fr=f: _hl(fr, False))
                f.bind("<Button-1>", lambda e, c=code, n=name: self._on_translate(c, n))
                for w in f.winfo_children():
                    w.bind("<Button-1>", lambda e, c=code, n=name: self._on_translate(c, n))
        self._open_sub(build)

    def _slot_row(self, parent, num, color, action, preview=None):
        f = tk.Frame(parent, bg=_BG, padx=10, pady=3, cursor="hand2")
        f.pack(fill=tk.X)
        # Color dot — SAME color as the slot in the main window
        cv = tk.Canvas(f, width=12, height=12, bg=_BG, highlightthickness=0)
        cv.create_oval(1, 1, 11, 11, fill=color, outline=color)
        cv.pack(side=tk.LEFT, padx=(0, 8))
        # Slot label in matching color
        tk.Label(f, text=f"Slot {num}", font=(FONT_FAMILY, 10, "bold"),
                 fg=color, bg=_BG).pack(side=tk.LEFT)
        if preview:
            prev = preview[:25] + "..." if len(preview) > 25 else preview
            tk.Label(f, text=f"  {prev}", font=FONT_SMALL,
                     fg="#556677", bg=_BG).pack(side=tk.LEFT, padx=(4, 0))
        f.bind("<Enter>", lambda e, fr=f: _hl(fr, True))
        f.bind("<Leave>", lambda e, fr=f: _hl(fr, False))
        f.bind("<Button-1>", lambda e, a=action, s=num: self._on_slot(a, s))
        for w in f.winfo_children():
            w.bind("<Button-1>", lambda e, a=action, s=num: self._on_slot(a, s))

    # ========== ACTIONS ==========

    def _on_open(self):
        self.dismiss()
        self.app.show_main_window()

    def _on_slot(self, action, num):
        self.dismiss()
        if action.startswith("translate:"):
            self.app.actions.translate(action.split(":", 1)[1], num, delay=0.35)
        elif action == "copy":
            self.app.copy_to_slot(num)
        elif action == "cut":
            self.app.cut_to_slot(num)
        elif action == "paste":
            self.app.actions.run("paste", [str(num)])
        elif action in ("android-copy", "android-cut", "android-paste", "ios-copy", "ios-cut", "ios-paste"):
            self.app.actions.run(action, [str(num)])

    def _on_android_upgrade(self):
        from ratt.clipboard_manager import UPGRADE_ANDROID_MSG
        self.dismiss()
        self.app.request_upgrade(UPGRADE_ANDROID_MSG.split("UPGRADE_REQUIRED:", 1)[1].strip())

    def _on_ios_upgrade(self):
        from ratt.clipboard_manager import UPGRADE_IOS_MSG
        self.dismiss()
        self.app.request_upgrade(UPGRADE_IOS_MSG.split("UPGRADE_REQUIRED:", 1)[1].strip())

    def _show_android_sub(self):
        def build(inner):
            tk.Label(inner, text="Android Keyboard (IME)", font=FONT_SMALL,
                     fg="#A4C639", bg=_BG, padx=10, pady=4).pack(anchor=tk.W)
            _sep(inner)
            _item(inner, "Copy Slot #1 to Android", lambda: self._on_slot("android-copy", 1), icon="#A4C639")
            _item(inner, "Cut Slot #1 to Android", lambda: self._on_slot("android-cut", 1), icon="#A4C639")
            _item(inner, "Paste from Android to Slot #1", lambda: self._on_slot("android-paste", 1), icon="#A4C639")
        self._open_sub(build)

    def _show_ios_sub(self):
        def build(inner):
            tk.Label(inner, text="iOS Keyboard (iPhone)", font=FONT_SMALL,
                     fg="#00BFFF", bg=_BG, padx=10, pady=4).pack(anchor=tk.W)
            _sep(inner)
            _item(inner, "Copy Slot #1 to iPhone (iOS)", lambda: self._on_slot("ios-copy", 1), icon="#00BFFF")
            _item(inner, "Cut Slot #1 to iPhone (iOS)", lambda: self._on_slot("ios-cut", 1), icon="#00BFFF")
            _item(inner, "Paste from iPhone (iOS) to Slot #1", lambda: self._on_slot("ios-paste", 1), icon="#00BFFF")
        self._open_sub(build)

    def _on_share(self):
        if not config.user.is_trial_active:
            from tkinter import messagebox
            messagebox.showinfo("Trial Expired",
                "Your 7-day Share trial has expired.\n"
                "Upgrade to Premium or Enterprise to continue.",
                parent=self.popup)
            return
        self.dismiss()
        self.app.show_share_dialog()

    def _on_mirror(self):
        if not config.user.is_trial_active:
            from tkinter import messagebox
            messagebox.showinfo("Trial Expired",
                "Your 7-day Mirror trial has expired.\n"
                "Upgrade to Premium or Enterprise to continue.",
                parent=self.popup)
            return
        self.dismiss()
        self.app.show_mirror_dialog()

    def _on_contact_action(self, action, contact):
        self.dismiss()
        self.app.show_notification(f"{action.title()} with {contact.display_name}...")

    def _on_translate(self, code, name):
        """Language chosen -> ask which slot to translate (Translate > Language > Slot)."""
        def build(inner):
            tk.Label(inner, text=f"Translate to {name} - from slot...", font=FONT_SMALL,
                     fg="#5599BB", bg=_BG, padx=10, pady=4).pack(anchor=tk.W)
            _sep(inner)
            filled = self.app.clipboard_manager.get_all_slots()
            if not filled:
                tk.Label(inner, text="No slot has data yet", font=FONT_SMALL,
                         fg="#555", bg=_BG, padx=10, pady=6).pack()
            for num in sorted(filled.keys()):
                self._slot_row(inner, num, get_slot_color(num), "translate:" + code,
                               preview=filled[num].preview)
        self._open_sub(build)

    def dismiss(self):
        if self.submenu and self.submenu.winfo_exists():
            self.submenu.destroy()
        self.submenu = None
        if self.popup and self.popup.winfo_exists():
            self.popup.destroy()
        self.popup = None


# ========== HELPER FUNCTIONS (no borders) ==========

def _sep(parent):
    """Subtle separator line — no solid border."""
    tk.Frame(parent, bg=_SEP, height=1).pack(fill=tk.X)

def _hl(frame, on):
    """Highlight/unhighlight a row on hover."""
    bg = _BG_H if on else _BG
    frame.configure(bg=bg)
    for w in frame.winfo_children():
        if not isinstance(w, tk.Canvas):
            w.configure(bg=bg)

def _item(parent, text, command, arrow=False, enabled=True,
          subtitle="", hover=None, icon=None):
    """Create a menu item row with no border."""
    fg = TEXT_PRIMARY if enabled else "#555"
    cur = "hand2" if enabled else "arrow"
    f = tk.Frame(parent, bg=_BG, padx=12, pady=5, cursor=cur)
    f.pack(fill=tk.X)
    if icon and enabled:
        cv = tk.Canvas(f, width=8, height=8, bg=_BG, highlightthickness=0)
        cv.create_oval(1, 1, 7, 7, fill=icon, outline="")
        cv.pack(side=tk.LEFT, padx=(0, 6))
    tk.Label(f, text=text, font=FONT_BODY, fg=fg, bg=_BG).pack(side=tk.LEFT)
    if subtitle:
        tk.Label(f, text=f"  {subtitle}", font=FONT_SMALL,
                 fg="#555", bg=_BG).pack(side=tk.LEFT)
    if arrow:
        tk.Label(f, text="\u25b6", font=(FONT_FAMILY, 7),
                 fg="#556677" if enabled else "#333", bg=_BG).pack(side=tk.RIGHT)
    if enabled:
        f.bind("<Enter>", lambda e, fr=f, h=hover: [_hl(fr, True), h(e) if h else None])
        f.bind("<Leave>", lambda e, fr=f: _hl(fr, False))
        if command:
            f.bind("<Button-1>", lambda e, c=command: c())
            for w in f.winfo_children():
                w.bind("<Button-1>", lambda e, c=command: c())

def _contact_row(parent, name, contact, action, popup, is_code=False):
    """Contact row for Share/Mirror submenu."""
    f = tk.Frame(parent, bg=_BG, padx=12, pady=4, cursor="hand2")
    f.pack(fill=tk.X)
    ic = "#FF9800" if is_code else "#00BCD4"
    cv = tk.Canvas(f, width=8, height=8, bg=_BG, highlightthickness=0)
    cv.create_oval(1, 1, 7, 7, fill=ic, outline="")
    cv.pack(side=tk.LEFT, padx=(0, 6))
    tk.Label(f, text=name, font=FONT_BODY, fg=TEXT_PRIMARY, bg=_BG).pack(side=tk.LEFT)
    f.bind("<Enter>", lambda e, fr=f: _hl(fr, True))
    f.bind("<Leave>", lambda e, fr=f: _hl(fr, False))
    if is_code:
        cb = popup._on_share if action == "share" else popup._on_mirror
    else:
        cb = lambda a=action, c=contact: popup._on_contact_action(a, c)
    f.bind("<Button-1>", lambda e, c=cb: c())
    for w in f.winfo_children():
        w.bind("<Button-1>", lambda e, c=cb: c())
