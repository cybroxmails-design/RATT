"""Cybrox Account Sign-In, Web Portal Links & Subscription Overview."""
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ratt.app import RattApp

from ratt.config import config, open_cybrox_web, validate_user_name, UserTier
from ratt.ui.styles import *


class SignupDialog:
    """Account management dialog connecting RATT with the Cybrox web portal."""

    def __init__(self, root: tk.Tk, app: "RattApp"):
        self.root = root
        self.app = app
        self.dialog: Optional[tk.Toplevel] = None

    def show(self):
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.lift()
            self.dialog.focus_force()
            return

        self.dialog = self.app.new_window("signup")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=BG_PRIMARY)
        self.dialog.transient(self.root)
        self.dialog.grab_set()

        if config.user.is_logged_in:
            self._build_account_view()
        else:
            self._build_login_view()

    def _build_login_view(self):
        """Primary Sign-In view with direct links to the Cybrox website for Sign-Up & Password Reset."""
        for widget in self.dialog.winfo_children():
            widget.destroy()

        self.dialog.title("RATT \u2014 Sign In")
        self.dialog.geometry("420x540")

        header = tk.Frame(self.dialog, bg=LOGO_BLUE, pady=18, padx=24)
        header.pack(fill=tk.X)
        tk.Label(
            header, text=f"{config.APP_NAME} v{config.VERSION}", font=(FONT_FAMILY, 20, "bold"),
            fg=LOGO_DARK, bg=LOGO_BLUE
        ).pack()
        tk.Label(
            header, text="Sign in with your Cybrox account",
            font=FONT_BODY, fg=LOGO_NAVY, bg=LOGO_BLUE
        ).pack(pady=(4, 0))

        body = tk.Frame(self.dialog, bg=BG_PRIMARY, padx=32, pady=18)
        body.pack(fill=tk.BOTH, expand=True)

        # Cybrox Web Portal Banner
        web_box = tk.Frame(body, bg=BG_SECONDARY, padx=12, pady=10)
        web_box.pack(fill=tk.X, pady=(0, 14))
        web_box.configure(highlightbackground=BORDER, highlightthickness=1)
        tk.Label(
            web_box,
            text="Account creation (Sign-Up), Sign-In, Password Changes,\n"
                 "and Profile Name updates are managed on the Cybrox website:",
            font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(0, 6))

        web_btns = tk.Frame(web_box, bg=BG_SECONDARY)
        web_btns.pack(fill=tk.X)
        tk.Button(
            web_btns, text="Sign Up / Sign In", font=FONT_SMALL,
            fg=LOGO_DARK, bg=LOGO_BLUE, activebackground=LOGO_CYAN,
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2",
            command=lambda: open_cybrox_web(config.CYBROX_SIGNUP_URL)
        ).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(
            web_btns, text="Change Password", font=FONT_SMALL,
            fg=TEXT_PRIMARY, bg=BG_HOVER, activebackground=BG_ACTIVE,
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2",
            command=lambda: open_cybrox_web(config.CYBROX_PASSWORD_URL)
        ).pack(side=tk.LEFT)

        tk.Label(
            body, text="Email Address", font=FONT_BODY,
            fg=TEXT_SECONDARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(4, 4))
        self.login_email = tk.Entry(
            body, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            highlightbackground=BORDER, highlightthickness=1
        )
        self.login_email.pack(fill=tk.X, ipady=7)

        tk.Label(
            body, text="Password", font=FONT_BODY,
            fg=TEXT_SECONDARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(12, 4))
        self.login_password = tk.Entry(
            body, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            show="\u2022", highlightbackground=BORDER, highlightthickness=1
        )
        self.login_password.pack(fill=tk.X, ipady=7)

        login_btn = tk.Button(
            body, text="Sign In to RATT", font=FONT_HEADING,
            fg=TEXT_PRIMARY, bg=ACCENT, activebackground=ACCENT_HOVER,
            relief=tk.FLAT, pady=10, cursor="hand2",
            command=self._on_do_login
        )
        login_btn.pack(fill=tk.X, pady=(18, 8))
        self.login_password.bind("<Return>", lambda e: self._on_do_login())

        div_frame = tk.Frame(body, bg=BG_PRIMARY)
        div_frame.pack(fill=tk.X, pady=6)
        tk.Frame(div_frame, bg=BORDER, height=1).pack(fill=tk.X, side=tk.LEFT, expand=True)
        tk.Label(div_frame, text=" or ", font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_PRIMARY).pack(side=tk.LEFT)
        tk.Frame(div_frame, bg=BORDER, height=1).pack(fill=tk.X, side=tk.LEFT, expand=True)

        tk.Button(
            body, text="New to RATT? Register / Activate Cybrox Account", font=FONT_SMALL,
            fg=ACCENT, bg=BG_PRIMARY, activebackground=BG_PRIMARY,
            activeforeground=ACCENT_HOVER, relief=tk.FLAT, cursor="hand2",
            command=self._build_signup_view
        ).pack()

        self.login_email.focus_set()

    def _build_signup_view(self):
        """Register / sync a Cybrox account with RATT."""
        for widget in self.dialog.winfo_children():
            widget.destroy()

        self.dialog.title("RATT \u2014 Cybrox Account Registration")
        self.dialog.geometry("420x580")

        header = tk.Frame(self.dialog, bg=LOGO_BLUE, pady=18, padx=24)
        header.pack(fill=tk.X)
        tk.Label(
            header, text=f"{config.APP_NAME} v{config.VERSION}", font=(FONT_FAMILY, 20, "bold"),
            fg=LOGO_DARK, bg=LOGO_BLUE
        ).pack()
        tk.Label(
            header, text="Register your Cybrox account",
            font=FONT_BODY, fg=LOGO_NAVY, bg=LOGO_BLUE
        ).pack(pady=(4, 0))

        body = tk.Frame(self.dialog, bg=BG_PRIMARY, padx=32, pady=16)
        body.pack(fill=tk.BOTH, expand=True)

        tk.Button(
            body, text="Open Cybrox Sign-Up Page",
            font=FONT_SMALL, fg=LOGO_DARK, bg=LOGO_BLUE, activebackground=LOGO_CYAN,
            relief=tk.FLAT, pady=6, cursor="hand2",
            command=lambda: open_cybrox_web(config.CYBROX_SIGNUP_URL)
        ).pack(fill=tk.X, pady=(0, 12))

        tk.Label(
            body, text="Profile Name (letters & numbers only)", font=FONT_BODY,
            fg=TEXT_SECONDARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 4))
        self.name_entry = tk.Entry(
            body, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            highlightbackground=BORDER, highlightthickness=1
        )
        self.name_entry.pack(fill=tk.X, ipady=7)
        self.name_entry.bind("<KeyPress>", self._on_name_keypress)

        tk.Label(
            body, text="Email Address", font=FONT_BODY,
            fg=TEXT_SECONDARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(12, 4))
        self.email_entry = tk.Entry(
            body, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            highlightbackground=BORDER, highlightthickness=1
        )
        self.email_entry.pack(fill=tk.X, ipady=7)

        tk.Label(
            body, text="Password", font=FONT_BODY,
            fg=TEXT_SECONDARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(12, 4))
        self.password_entry = tk.Entry(
            body, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            show="\u2022", highlightbackground=BORDER, highlightthickness=1
        )
        self.password_entry.pack(fill=tk.X, ipady=7)

        tk.Label(
            body, text="Confirm Password", font=FONT_BODY,
            fg=TEXT_SECONDARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(12, 4))
        self.confirm_entry = tk.Entry(
            body, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            show="\u2022", highlightbackground=BORDER, highlightthickness=1
        )
        self.confirm_entry.pack(fill=tk.X, ipady=7)

        signup_btn = tk.Button(
            body, text="Create & Activate Account", font=FONT_HEADING,
            fg=TEXT_PRIMARY, bg=ACCENT, activebackground=ACCENT_HOVER,
            relief=tk.FLAT, pady=10, cursor="hand2",
            command=self._on_signup
        )
        signup_btn.pack(fill=tk.X, pady=(18, 8))

        login_btn = tk.Button(
            body, text="Already have a Cybrox account? Sign In", font=FONT_SMALL,
            fg=ACCENT, bg=BG_PRIMARY, activebackground=BG_PRIMARY,
            activeforeground=ACCENT_HOVER, relief=tk.FLAT, cursor="hand2",
            command=self._build_login_view
        )
        login_btn.pack()
        self.name_entry.focus_set()

    def _build_account_view(self):
        """Signed-in account overview with Cybrox Web Portal profile/password actions."""
        self.dialog.title("RATT \u2014 My Cybrox Account")
        self.dialog.geometry("420x580")

        header = tk.Frame(self.dialog, bg=LOGO_BLUE, pady=18, padx=24)
        header.pack(fill=tk.X)
        tk.Label(
            header, text=f"Welcome, {config.user.display_name}!",
            font=(FONT_FAMILY, 16, "bold"), fg=LOGO_DARK, bg=LOGO_BLUE
        ).pack()
        tk.Label(
            header, text=config.user.email,
            font=FONT_BODY, fg=LOGO_NAVY, bg=LOGO_BLUE
        ).pack(pady=(4, 0))

        body = tk.Frame(self.dialog, bg=BG_PRIMARY, padx=28, pady=16)
        body.pack(fill=tk.BOTH, expand=True)

        # Cybrox Web Account Management section
        tk.Label(
            body, text="CYBROX WEB ACCOUNT MANAGEMENT", font=FONT_HEADING,
            fg=TEXT_PRIMARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 6))

        web_frame = tk.Frame(body, bg=BG_SECONDARY, padx=14, pady=12)
        web_frame.pack(fill=tk.X, pady=(0, 14))
        web_frame.configure(highlightbackground=BORDER, highlightthickness=1)

        tk.Label(
            web_frame,
            text="Manage your profile name, password, and account credentials\n"
                 "on the Cybrox website:",
            font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY, justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(0, 8))

        btn_row = tk.Frame(web_frame, bg=BG_SECONDARY)
        btn_row.pack(fill=tk.X)
        tk.Button(
            btn_row, text="Change Profile Name", font=FONT_SMALL,
            fg=LOGO_DARK, bg=LOGO_BLUE, activebackground=LOGO_CYAN,
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2",
            command=lambda: open_cybrox_web(config.CYBROX_PROFILE_URL)
        ).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(
            btn_row, text="Change Password", font=FONT_SMALL,
            fg=TEXT_PRIMARY, bg=BG_HOVER, activebackground=BG_ACTIVE,
            relief=tk.FLAT, padx=10, pady=4, cursor="hand2",
            command=lambda: open_cybrox_web(config.CYBROX_PASSWORD_URL)
        ).pack(side=tk.LEFT)

        # Current Plan section
        tk.Label(
            body, text="YOUR PLAN", font=FONT_HEADING,
            fg=TEXT_PRIMARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 6))

        plan_frame = tk.Frame(body, bg=BG_SECONDARY, padx=16, pady=14)
        plan_frame.pack(fill=tk.X, pady=(0, 14))
        plan_frame.configure(highlightbackground=BORDER, highlightthickness=1)

        if config.is_enterprise:
            plan_name, plan_color = "Enterprise Plan", "#CE93D8"
            plan_desc = f"{config.user.company_name or 'Your company'}  |  up to {config.user.max_workers:,} workers"
        elif config.is_premium:
            plan_name, plan_color = "Premium Plan", SUCCESS
            plan_desc = f"{config.max_slots:,} clipboard slots"
        elif config.has_paid_tier and config.user.is_subscription_expired:
            plan_name, plan_color = f"{config.user.tier.value.title()} Plan (Expired)", ERROR
            plan_desc = f"Limited to {config.MAX_SLOTS_BASIC} clipboard slots until renewed"
        else:
            plan_name, plan_color = "Basic Plan (Free)", TEXT_SECONDARY
            plan_desc = f"Limited to {config.MAX_SLOTS_BASIC} clipboard slots"

        tk.Label(
            plan_frame, text=plan_name, font=(FONT_FAMILY, 14, "bold"),
            fg=plan_color, bg=BG_SECONDARY
        ).pack(anchor=tk.W)
        tk.Label(
            plan_frame, text=plan_desc, font=FONT_BODY,
            fg=TEXT_SECONDARY, bg=BG_SECONDARY
        ).pack(anchor=tk.W, pady=(4, 0))

        if config.has_paid_tier and config.user.subscription_expiry is not None:
            days = config.user.days_until_expiry
            if config.user.subscription_expiry <= datetime.now():
                cd_text, cd_fg = "Subscription EXPIRED - renew now", ERROR
            else:
                cd_text = (f"{days} day{'s' if days != 1 else ''} remaining "
                           f"(until {config.user.subscription_expiry:%d %b %Y})")
                cd_fg = "#FFC107" if days <= 30 else LOGO_CYAN
            tk.Label(plan_frame, text=cd_text, font=(FONT_FAMILY, 9, "bold"),
                     fg=cd_fg, bg=BG_SECONDARY).pack(anchor=tk.W, pady=(6, 0))

        trial_note = "" if config.is_premium else f" ({config.user.trial_days_remaining} days left)"
        features = [
            (f"Clipboard slots ({config.max_slots:,})", True),
            ("Images, Vector Diagrams (SVG) & Unformatted Links", True),
            ("Documents & Media Files (.docx, .xls, .pdf, .mp4, etc.)", config.is_premium),
            ("Android & iOS (iPhone/iPad) Virtual Keyboard Sync", config.is_premium),
            (f"Share & Mirror{trial_note}", config.is_premium or config.user.is_trial_active),
            ("Translation (9 languages)", config.is_premium),
            ("Team accounts (up to 3,000 workers)", config.is_enterprise),
        ]

        for feature, available in features:
            icon = "[+]" if available else "[x]"
            fg = TEXT_PRIMARY if available else TEXT_MUTED
            tk.Label(
                plan_frame, text=f"  {icon}  {feature}",
                font=FONT_SMALL, fg=fg, bg=BG_SECONDARY
            ).pack(anchor=tk.W, pady=1)

        def _action(text, bg, fg, cmd):
            tk.Button(body, text=text, font=FONT_HEADING, fg=fg, bg=bg,
                      activebackground=bg, relief=tk.FLAT, pady=8, cursor="hand2",
                      command=cmd).pack(fill=tk.X, pady=(0, 8))

        if not config.has_paid_tier:
            _action(f"Upgrade to Premium  (USD {config.PRICE_USD_PER_10_SLOTS:.2f} / 10 slots)", SUCCESS, TEXT_PRIMARY,
                    lambda: self.app._open_payment("premium"))
            _action(f"Upgrade to Enterprise  (USD {config.PRICE_USD_ENTERPRISE:.2f} / month)",
                    "#7B1FA2", TEXT_PRIMARY, lambda: self.app._open_payment("enterprise"))
        elif config.user.tier == UserTier.PREMIUM:
            _action("Renew Premium", LOGO_BLUE, LOGO_DARK, lambda: self.app._open_payment("premium"))
            _action(f"Upgrade to Enterprise  (USD {config.PRICE_USD_ENTERPRISE:.2f} / month)",
                    "#7B1FA2", TEXT_PRIMARY, lambda: self.app._open_payment("enterprise"))
        else:
            _action("Renew Enterprise", LOGO_BLUE, LOGO_DARK, lambda: self.app._open_payment("enterprise"))

        if config.has_paid_tier:
            tk.Button(
                body, text="Switch to Basic Plan", font=FONT_SMALL,
                fg=TEXT_MUTED, bg=BG_HOVER, activebackground=BG_ACTIVE,
                relief=tk.FLAT, pady=4, cursor="hand2",
                command=self._on_downgrade
            ).pack(fill=tk.X, pady=(0, 10))

        logout_btn = tk.Button(
            body, text="Sign Out", font=FONT_BODY,
            fg=TEXT_PRIMARY, bg=ERROR, activebackground="#D32F2F",
            relief=tk.FLAT, pady=8, cursor="hand2",
            command=self._on_logout
        )
        logout_btn.pack(fill=tk.X, pady=(4, 0))

    @staticmethod
    def _on_name_keypress(event):
        """Block typing special characters in the profile name field (letters, numbers, and spaces allowed)."""
        ch = event.char
        if not ch or ord(ch) < 32:
            return None
        # Allow Ctrl/Alt shortcuts (e.g. Ctrl+A, Ctrl+C, Ctrl+V)
        if event.state & 0x4:
            return None
        if ch.isalnum() or ch == " ":
            return None
        return "break"

    def _on_signup(self):
        raw_name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()

        valid_name, name_or_err = validate_user_name(raw_name)
        if not valid_name:
            messagebox.showwarning("Invalid Profile Name", name_or_err, parent=self.dialog)
            return
        name = name_or_err
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            messagebox.showwarning("Invalid Email", "Please enter a valid email address.", parent=self.dialog)
            return
        if len(password) < 6:
            messagebox.showwarning("Weak Password", "Password must be at least 6 characters.", parent=self.dialog)
            return
        if password != confirm:
            messagebox.showwarning("Password Mismatch", "Passwords do not match.", parent=self.dialog)
            return
        if config.account_exists(email):
            messagebox.showinfo(
                "Account Exists",
                "An account with this email address already exists.\nPlease sign in with your password.",
                parent=self.dialog
            )
            self._build_login_view()
            return

        pw_salt, pw_hash = config.hash_password(password)
        config.register_account(email, name, pw_salt, pw_hash)

        messagebox.showinfo(
            "Cybrox Account Active",
            f"Welcome to RATT, {name}!\n\n"
            "Your Cybrox account is active. You can manage your profile name\n"
            "and password anytime on the Cybrox website.",
            parent=self.dialog
        )

        self.dialog.destroy()
        self.dialog = None
        self.app.rebuild_ui()

    def _on_login(self):
        self._build_login_view()

    def _on_do_login(self):
        email = self.login_email.get().strip()
        password = self.login_password.get()

        if not email or "@" not in email or "." not in email.split("@")[-1]:
            messagebox.showwarning("Invalid Email", "Please enter a valid email address.", parent=self.dialog)
            return
        if not password:
            messagebox.showwarning("Missing Password", "Please enter your password.", parent=self.dialog)
            return

        success, msg = config.authenticate_user(email, password)
        if not success:
            messagebox.showerror("Sign-In Failed", msg, parent=self.dialog)
            self.login_password.delete(0, tk.END)
            return

        messagebox.showinfo("Signed In", msg, parent=self.dialog)
        self.dialog.destroy()
        self.dialog = None
        self.show()
        self.app.rebuild_ui()

    def _on_downgrade(self):
        if messagebox.askyesno(
            "Downgrade?",
            "Are you sure you want to switch to the Basic plan?\n\n"
            "You will lose access to extra slots, file routing, mobile keyboard sync, and translation.",
            parent=self.dialog
        ):
            config.user.tier = UserTier.BASIC
            config.user.premium_slots = 0
            config.user.subscription_expiry = None
            config.user.last_renewal_alert = None
            config.save_session()

            self.dialog.destroy()
            self.dialog = None
            self.show()
            self.app.rebuild_ui()

    def _on_logout(self):
        if messagebox.askyesno("Sign Out?", "Are you sure you want to sign out?", parent=self.dialog):
            config.save_session()
            config.clear_session()
            config.user.email = ""
            config.user.display_name = "User"
            config.user.is_logged_in = False
            config.user.tier = UserTier.BASIC
            config.user.premium_slots = 0
            config.user.connections.clear()
            config.user.workers.clear()
            config.user.company_name = ""
            config.user.created_at = None
            config.user.subscription_expiry = None
            config.user.last_renewal_alert = None
            try:
                self.app.clipboard_manager.clear_all()
            except Exception:
                pass

            self.dialog.destroy()
            self.dialog = None
            self.app.rebuild_ui()

    def dismiss(self):
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog = None
