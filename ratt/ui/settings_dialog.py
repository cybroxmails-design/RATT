"""Settings and Cybrox account management page."""
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ratt.app import RattApp

from ratt.config import config, open_cybrox_web, UserTier
from ratt.ui.styles import *


class SettingsDialog:
    """In-window settings page for subscription, Cybrox web account, and shortcuts."""

    def __init__(self, root: tk.Tk, app: "RattApp"):
        self.root = root
        self.app = app
        self.dialog: Optional[tk.Toplevel] = None

    def show(self):
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.lift()
            return

        self.dialog = self.app.new_window("settings")
        self.dialog.title("RATT \u2014 Settings")
        self.dialog.geometry("450x560")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=BG_PRIMARY)
        self.dialog.transient(self.root)

        header = tk.Frame(self.dialog, bg=BG_SECONDARY, pady=12, padx=16)
        header.pack(fill=tk.X)
        tk.Label(
            header, text="Settings", font=FONT_TITLE,
            fg=ACCENT, bg=BG_SECONDARY
        ).pack(anchor=tk.W)

        body = tk.Frame(self.dialog, bg=BG_PRIMARY, padx=24, pady=16)
        body.pack(fill=tk.BOTH, expand=True)

        # -- About --
        self._add_section_header(body, "About")
        info_frame = tk.Frame(body, bg=BG_SECONDARY, padx=12, pady=8)
        info_frame.pack(fill=tk.X, pady=(0, 14))
        info_frame.configure(highlightbackground=BORDER, highlightthickness=1)

        tk.Label(
            info_frame, text=f"{config.APP_NAME} v{config.VERSION} ({config.VERSION_FULL})",
            font=FONT_HEADING, fg=ACCENT, bg=BG_SECONDARY
        ).pack(anchor=tk.W)
        tk.Label(
            info_frame, text=f"Published by {config.PUBLISHER}",
            font=FONT_BODY, fg=TEXT_PRIMARY, bg=BG_SECONDARY
        ).pack(anchor=tk.W)
        tk.Label(
            info_frame, text="Rapid Access To Text, Rich Media & Files",
            font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY
        ).pack(anchor=tk.W)

        # -- Cybrox Account & Profile (Website Portal) --
        self._add_section_header(body, "Cybrox Account & Profile")
        account_frame = tk.Frame(body, bg=BG_SECONDARY, padx=12, pady=12)
        account_frame.pack(fill=tk.X, pady=(0, 14))
        account_frame.configure(highlightbackground=BORDER, highlightthickness=1)

        if config.user.is_logged_in:
            tk.Label(
                account_frame, text=f"Profile Name: {config.user.display_name}",
                font=FONT_HEADING, fg=LOGO_CYAN, bg=BG_SECONDARY
            ).pack(anchor=tk.W)
            tk.Label(
                account_frame, text=f"Email: {config.user.email}",
                font=FONT_SMALL, fg=TEXT_PRIMARY, bg=BG_SECONDARY
            ).pack(anchor=tk.W, pady=(2, 6))
        else:
            tk.Label(
                account_frame, text="Not signed in",
                font=FONT_HEADING, fg=WARNING, bg=BG_SECONDARY
            ).pack(anchor=tk.W, pady=(0, 4))

        tk.Label(
            account_frame,
            text="Sign-up, sign-in, password changes, and profile name updates are\n"
                 "managed on the Cybrox website:",
            font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(0, 8))

        web_row1 = tk.Frame(account_frame, bg=BG_SECONDARY)
        web_row1.pack(fill=tk.X, pady=(0, 6))
        tk.Button(
            web_row1, text="Sign Up / Sign In", font=FONT_SMALL,
            fg=LOGO_DARK, bg=LOGO_BLUE, activebackground=LOGO_CYAN,
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2",
            command=lambda: open_cybrox_web(config.CYBROX_SIGNIN_URL)
        ).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(
            web_row1, text="Change Password", font=FONT_SMALL,
            fg=TEXT_PRIMARY, bg=BG_HOVER, activebackground=BG_ACTIVE,
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2",
            command=lambda: open_cybrox_web(config.CYBROX_PASSWORD_URL)
        ).pack(side=tk.LEFT)

        web_row2 = tk.Frame(account_frame, bg=BG_SECONDARY)
        web_row2.pack(fill=tk.X)
        tk.Button(
            web_row2, text="Change Profile Name", font=FONT_SMALL,
            fg=TEXT_PRIMARY, bg=BG_HOVER, activebackground=BG_ACTIVE,
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2",
            command=lambda: open_cybrox_web(config.CYBROX_PROFILE_URL)
        ).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(
            web_row2, text="Account Session in RATT", font=FONT_SMALL,
            fg=TEXT_PRIMARY, bg=ACCENT, activebackground=ACCENT_HOVER,
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2",
            command=self.app._open_signup
        ).pack(side=tk.LEFT)

        # -- Subscription --
        self._add_section_header(body, "Subscription")
        tier_frame = tk.Frame(body, bg=BG_SECONDARY, padx=12, pady=12)
        tier_frame.pack(fill=tk.X, pady=(0, 14))
        tier_frame.configure(highlightbackground=BORDER, highlightthickness=1)

        tier_names = {
            UserTier.BASIC: "Basic",
            UserTier.PREMIUM: "Premium",
            UserTier.ENTERPRISE: "Enterprise",
        }
        tier_colors = {
            UserTier.BASIC: TEXT_SECONDARY,
            UserTier.PREMIUM: SUCCESS,
            UserTier.ENTERPRISE: "#CE93D8",
        }

        current = tier_names.get(config.user.tier, "Basic")
        color = tier_colors.get(config.user.tier, TEXT_SECONDARY)

        tk.Label(
            tier_frame, text=f"Current Plan: {current}",
            font=FONT_HEADING, fg=color, bg=BG_SECONDARY
        ).pack(anchor=tk.W)
        tk.Label(
            tier_frame, text=f"Clipboard Slots: {config.max_slots:,}",
            font=FONT_BODY, fg=TEXT_PRIMARY, bg=BG_SECONDARY
        ).pack(anchor=tk.W, pady=(4, 0))

        if config.is_enterprise:
            tk.Label(
                tier_frame, text=f"Company: {config.user.company_name}",
                font=FONT_BODY, fg=TEXT_PRIMARY, bg=BG_SECONDARY
            ).pack(anchor=tk.W)
            tk.Label(
                tier_frame, text=f"Workers: {len(config.user.workers)}/{config.user.max_workers}",
                font=FONT_BODY, fg=TEXT_PRIMARY, bg=BG_SECONDARY
            ).pack(anchor=tk.W)

        if config.is_premium and not config.is_enterprise:
            tk.Label(
                tier_frame, text=f"Connections: {len(config.user.connections)}",
                font=FONT_BODY, fg=TEXT_PRIMARY, bg=BG_SECONDARY
            ).pack(anchor=tk.W)

        features = [
            (f"Multi-clipboard (slots 1-{config.MAX_SLOTS_BASIC})", True),
            ("Images, Diagrams (SVG) & Unformatted Links", True),
            ("ON / OFF Native Keyboard & Mouse Release (Ctrl+Alt+P)", True),
            ("Custom slots (10-50,000)", config.is_premium),
            ("Document & Media File Copy/Cut/Paste", config.is_premium),
            ("Android Floating Assist Overlay (Keep Samsung/Gboard)", config.is_premium),
            ("iOS (iPhone/iPad) Slot Palette Extension (Globe Icon)", config.is_premium),
            ("Share & Mirror", True),
            ("Translation (9 languages)", config.is_premium),
            ("Team sharing & worker management (up to 3,000)", config.is_enterprise),
        ]

        for feature, available in features:
            icon = "[+]" if available else "[x]"
            fg = TEXT_PRIMARY if available else TEXT_MUTED
            tk.Label(
                tier_frame, text=f"  {icon}  {feature}",
                font=FONT_SMALL, fg=fg, bg=BG_SECONDARY
            ).pack(anchor=tk.W)

        if config.has_paid_tier and config.user.subscription_expiry is not None:
            days = config.user.days_until_expiry
            expired = config.user.subscription_expiry <= datetime.now()
            if expired:
                txt, fg = "Subscription EXPIRED - renew to keep your plan", ERROR
            else:
                txt = (f"{days} day{'s' if days != 1 else ''} remaining  "
                       f"(renews by {config.user.subscription_expiry:%d %b %Y})")
                fg = "#FFC107" if days <= 30 else LOGO_CYAN
            tk.Label(tier_frame, text=txt, font=(FONT_FAMILY, 9, "bold"),
                     fg=fg, bg=BG_SECONDARY).pack(anchor=tk.W, pady=(8, 0))

        btn_row = tk.Frame(tier_frame, bg=BG_SECONDARY)
        btn_row.pack(anchor=tk.W, pady=(8, 0))

        def _btn(text, bg, fg, cmd):
            tk.Button(btn_row, text=text, font=FONT_BODY, fg=fg, bg=bg, relief=tk.FLAT,
                      padx=12, pady=4, cursor="hand2", command=cmd).pack(side=tk.LEFT, padx=(0, 6))

        if config.user.tier == UserTier.BASIC:
            _btn("Upgrade to Premium", SUCCESS, TEXT_PRIMARY, lambda: self.app._open_payment("premium"))
            _btn("Upgrade to Enterprise", "#7B1FA2", TEXT_PRIMARY, lambda: self.app._open_payment("enterprise"))
        elif config.user.tier == UserTier.PREMIUM:
            _btn("Renew", LOGO_BLUE, LOGO_DARK, lambda: self.app._open_payment("premium"))
            _btn("Upgrade to Enterprise", "#7B1FA2", TEXT_PRIMARY, lambda: self.app._open_payment("enterprise"))
            _btn("Switch to Basic", WARNING, LOGO_DARK, self._toggle_tier)
        else:
            _btn("Renew", LOGO_BLUE, LOGO_DARK, lambda: self.app._open_payment("enterprise"))
            _btn("Switch to Basic", WARNING, LOGO_DARK, self._toggle_tier)

        # -- Keyboard Shortcuts --
        self._add_section_header(body, "Keyboard Shortcuts")
        hotkey_frame = tk.Frame(body, bg=BG_SECONDARY, padx=12, pady=8)
        hotkey_frame.pack(fill=tk.X)
        hotkey_frame.configure(highlightbackground=BORDER, highlightthickness=1)

        shortcuts = [
            ("Ctrl+C, then 1-0", "Copy text/image/diagram/file to slot"),
            ("Ctrl+X, then 1-0", "Cut text/image/diagram/file to slot"),
            ("Ctrl+V, then 1-0", "Paste from slot"),
            ("Ctrl+Shift+R", "Open RATT popup"),
            ("Ctrl+Alt+P", "Toggle RATT ON / OFF (Release Keyboard)"),
            ("Win+Shift+Pause", "Emergency Toggle ON / OFF"),
        ]

        for keys, desc in shortcuts:
            row = tk.Frame(hotkey_frame, bg=BG_SECONDARY)
            row.pack(fill=tk.X, pady=1)
            tk.Label(
                row, text=keys, font=FONT_MONO,
                fg=ACCENT, bg=BG_SECONDARY, width=22, anchor=tk.W
            ).pack(side=tk.LEFT)
            tk.Label(
                row, text=desc, font=FONT_SMALL,
                fg=TEXT_SECONDARY, bg=BG_SECONDARY, anchor=tk.W
            ).pack(side=tk.LEFT)

    def _add_section_header(self, parent: tk.Frame, text: str):
        tk.Label(
            parent, text=text, font=FONT_HEADING,
            fg=TEXT_PRIMARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 4))

    def _toggle_tier(self):
        if config.user.tier == UserTier.BASIC:
            self.dialog.destroy()
            self.dialog = None
            from ratt.ui.payment_dialog import PaymentDialog
            payment = PaymentDialog(self.root, self.app, plan="premium")
            payment.show()
        else:
            plan_name = "Premium" if config.user.tier == UserTier.PREMIUM else "Enterprise"
            if messagebox.askyesno(
                "Downgrade?",
                f"Switch from {plan_name} to Basic?\n\n"
                "You will lose access to extra slots,\n"
                "translation, connections, and team features.",
                parent=self.dialog
            ):
                config.user.tier = UserTier.BASIC
                config.user.premium_slots = 0
                config.user.max_workers = 0
                config.user.workers.clear()
                config.user.connections.clear()
                config.user.company_name = ""
                config.user.subscription_expiry = None
                config.user.last_renewal_alert = None
                config.save_session()

                self.dialog.destroy()
                self.dialog = None
                self.app.rebuild_ui()

    def dismiss(self):
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog = None
