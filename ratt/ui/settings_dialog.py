"""RATT Settings Dialog."""
import tkinter as tk
from tkinter import messagebox
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ratt.app import RattApp

from ratt.ui.styles import *
from ratt.config import config, UserTier


class SettingsDialog:
    """Settings and account management dialog."""
    
    def __init__(self, root: tk.Tk, app: 'RattApp'):
        self.root = root
        self.app = app
        self.dialog: Optional[tk.Toplevel] = None
    
    def show(self):
        """Show the settings dialog."""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.lift()
            return
        
        self.dialog = self.app.new_window("settings")
        self.dialog.title("RATT — Settings")
        self.dialog.geometry("450x500")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=BG_PRIMARY)
        self.dialog.transient(self.root)
        
        # Header
        header = tk.Frame(self.dialog, bg=BG_SECONDARY, pady=12, padx=16)
        header.pack(fill=tk.X)
        
        tk.Label(
            header, text="⚙️ Settings", font=FONT_TITLE,
            fg=ACCENT, bg=BG_SECONDARY
        ).pack(anchor=tk.W)
        
        # Body
        body = tk.Frame(self.dialog, bg=BG_PRIMARY, padx=24, pady=16)
        body.pack(fill=tk.BOTH, expand=True)
        
        # --- App Info ---
        self._add_section_header(body, "About")
        
        info_frame = tk.Frame(body, bg=BG_SECONDARY, padx=12, pady=8)
        info_frame.pack(fill=tk.X, pady=(0, 16))
        info_frame.configure(highlightbackground=BORDER, highlightthickness=1)
        
        tk.Label(
            info_frame, text=f"{config.APP_NAME} v{config.VERSION}",
            font=FONT_HEADING, fg=ACCENT, bg=BG_SECONDARY
        ).pack(anchor=tk.W)
        
        tk.Label(
            info_frame, text=f"by {config.PUBLISHER}",
            font=FONT_BODY, fg=TEXT_PRIMARY, bg=BG_SECONDARY
        ).pack(anchor=tk.W)
        
        tk.Label(
            info_frame, text="Rapid Access To Text",
            font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY
        ).pack(anchor=tk.W)
        
        # --- User Tier ---
        self._add_section_header(body, "Subscription")
        
        tier_frame = tk.Frame(body, bg=BG_SECONDARY, padx=12, pady=12)
        tier_frame.pack(fill=tk.X, pady=(0, 16))
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
            ("Multi-clipboard (slots 1-2)", True),
            ("Custom slots (10-50,000)", config.is_premium),
            ("Share & Mirror", True),
            ("Translation (9 languages)", config.is_premium),
            ("Team sharing", config.is_enterprise),
            ("Worker management (up to 3,000)", config.is_enterprise),
        ]
        
        for feature, available in features:
            icon = "[+]" if available else "[x]"
            fg = TEXT_PRIMARY if available else TEXT_MUTED
            tk.Label(
                tier_frame, text=f"  {icon}  {feature}",
                font=FONT_SMALL, fg=fg, bg=BG_SECONDARY
            ).pack(anchor=tk.W)
        
        # Subscription countdown
        if config.is_premium and config.user.subscription_expiry is not None:
            from datetime import datetime
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

        # Plan actions
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

        # --- Services (SMTP + payments) ---
        self._add_section_header(body, "Services")
        svc_frame = tk.Frame(body, bg=BG_SECONDARY, padx=12, pady=10)
        svc_frame.pack(fill=tk.X, pady=(0, 16))
        try:
            from ratt.api_config import get_config_status
            st = get_config_status()
        except Exception:
            st = {"smtp": False, "payment": False, "payment_mode": "unknown", "smtp_host": ""}
        tk.Label(svc_frame,
                 text=("Email (SMTP): " + (f"connected ({st['smtp_host']})" if st["smtp"] else "not configured - codes shown on screen")),
                 font=FONT_SMALL, fg=SUCCESS if st["smtp"] else "#FFC107", bg=BG_SECONDARY).pack(anchor=tk.W)
        tk.Label(svc_frame, text=f"Payments (Paystack): {st['payment_mode']}",
                 font=FONT_SMALL, fg=SUCCESS if st["payment"] else "#FFC107", bg=BG_SECONDARY).pack(anchor=tk.W, pady=(2, 6))
        tk.Button(svc_frame, text="Configure Services", font=FONT_BODY, fg=LOGO_DARK, bg=LOGO_BLUE,
                  relief=tk.FLAT, padx=12, pady=4, cursor="hand2",
                  command=self.app._open_services).pack(anchor=tk.W)
        

        # --- Hotkeys ---
        self._add_section_header(body, "Keyboard Shortcuts")
        
        hotkey_frame = tk.Frame(body, bg=BG_SECONDARY, padx=12, pady=8)
        hotkey_frame.pack(fill=tk.X, pady=(0, 16))
        hotkey_frame.configure(highlightbackground=BORDER, highlightthickness=1)
        
        shortcuts = [
            ("Ctrl+C, then 1-0", "Copy to slot"),
            ("Ctrl+X, then 1-0", "Cut to slot"),
            ("Ctrl+V, then 1-0", "Paste from slot"),
            ("Ctrl+Shift+R", "Open RATT popup"),
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
        
        # --- Account (Stub) ---
        self._add_section_header(body, "Account (Phase 2)")
        
        account_frame = tk.Frame(body, bg=BG_SECONDARY, padx=12, pady=8)
        account_frame.pack(fill=tk.X)
        account_frame.configure(highlightbackground=BORDER, highlightthickness=1)
        
        tk.Label(
            account_frame, text="Login and account management will be\navailable in Phase 2 with cloud sync.",
            font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_SECONDARY, justify=tk.LEFT
        ).pack(anchor=tk.W)
    
    def _add_section_header(self, parent: tk.Frame, text: str):
        """Add a section header label."""
        tk.Label(
            parent, text=text, font=FONT_HEADING,
            fg=TEXT_PRIMARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 4))
    
    def _toggle_tier(self):
        """Handle tier upgrade/downgrade."""
        if config.user.tier == UserTier.BASIC:
            # Open payment dialog (default to premium tab)
            self.dialog.destroy()
            self.dialog = None
            from ratt.ui.payment_dialog import PaymentDialog
            payment = PaymentDialog(self.root, self.app, plan="premium")
            payment.show()
        else:
            # Downgrade from Premium or Enterprise
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
        """Close the dialog."""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog = None
