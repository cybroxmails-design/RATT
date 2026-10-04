"""RATT Services page: configure SMTP (email verification) and Paystack (payments).

Secrets are saved to %APPDATA%\\RATT\\services.json (per-user, outside the source
code). Leaving a field blank keeps the value that is already saved.
"""
import threading
import tkinter as tk
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ratt.app import RattApp

from ratt.ui.styles import *
from ratt.config import config


class ServicesDialog:
    """In-window page for SMTP + payment API setup."""

    def __init__(self, root: tk.Tk, app: 'RattApp'):
        self.root = root
        self.app = app
        self.dialog: Optional[tk.Frame] = None
        self.entries = {}

    def show(self):
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.lift()
            return
        from ratt import api_config as cfg

        self.dialog = self.app.new_window("services")
        self.dialog.title("RATT - Configure Services")
        body = tk.Frame(self.dialog, bg=BG_PRIMARY, padx=24, pady=16)
        body.pack(fill=tk.BOTH, expand=True)

        status = cfg.get_config_status()

        def section(title, ok, ok_text, bad_text):
            row = tk.Frame(body, bg=BG_PRIMARY)
            row.pack(fill=tk.X, pady=(10, 4))
            tk.Label(row, text=title, font=FONT_HEADING, fg=LOGO_CYAN, bg=BG_PRIMARY).pack(side=tk.LEFT)
            tk.Label(row, text=ok_text if ok else bad_text, font=FONT_SMALL,
                     fg=SUCCESS if ok else "#FFC107", bg=BG_PRIMARY).pack(side=tk.RIGHT)

        def field(key, label, secret=False, hint=""):
            tk.Label(body, text=label, font=FONT_SMALL, fg=TEXT_SECONDARY,
                     bg=BG_PRIMARY).pack(anchor=tk.W, pady=(6, 2))
            e = tk.Entry(body, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
                         insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
                         highlightbackground=BORDER, highlightthickness=1,
                         show="\u2022" if secret else "")
            e.pack(fill=tk.X, ipady=5)
            if secret:
                if cfg.get_value(key):
                    tk.Label(body, text="(saved - leave blank to keep)", font=FONT_SMALL,
                             fg=TEXT_MUTED, bg=BG_PRIMARY).pack(anchor=tk.W)
            else:
                e.insert(0, cfg.get_value(key))
            if hint:
                tk.Label(body, text=hint, font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_PRIMARY).pack(anchor=tk.W)
            self.entries[key] = e

        # --- SMTP ---
        section("Email (SMTP)", status["smtp"], "connected", "not configured")
        tk.Label(body, text="Sends the 6-digit sign-up verification code to the user's email.",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_PRIMARY, wraplength=480,
                 justify=tk.LEFT).pack(anchor=tk.W)
        field("SMTP_HOST", "SMTP server", hint="e.g. smtp.gmail.com, smtp.zoho.com, smtp.sendgrid.net")
        field("SMTP_PORT", "Port (587 for STARTTLS)")
        field("SMTP_USER", "Username / sender address")
        field("SMTP_PASS", "Password or app password", secret=True)
        field("SMTP_FROM", "From (optional)", hint='e.g. RATT by Cybrox.Inc <noreply@yourdomain.com>')

        # --- Paystack ---
        section("Payments (Paystack)", status["payment"], status["payment_mode"],
                "DEMO - no real charges")
        tk.Label(body, text="Mobile Money + cards in GHS through Paystack's hosted checkout.",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_PRIMARY, wraplength=480,
                 justify=tk.LEFT).pack(anchor=tk.W)
        field("PAYSTACK_PUBLIC_KEY", "Public key (pk_test_... or pk_live_...)", secret=True)
        field("PAYSTACK_SECRET_KEY", "Secret key (sk_test_... or sk_live_...)", secret=True)
        tk.Label(body,
                 text="Security note: the secret key is stored on this PC only. For a public release,\n"
                      "keep it on your own server and have RATT call that server instead.",
                 font=FONT_SMALL, fg="#FFC107", bg=BG_PRIMARY, justify=tk.LEFT).pack(anchor=tk.W, pady=(6, 0))

        # --- Translation (optional) ---
        section("Translation (optional)", bool(cfg.get_value("GOOGLE_TRANSLATE_KEY")),
                "Google Cloud", "free web service")
        tk.Label(body, text="Translate works out of the box. Add a Google Cloud Translation API key\n"
                            "for higher volume and a supported, reliable service.",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_PRIMARY, justify=tk.LEFT).pack(anchor=tk.W)
        field("GOOGLE_TRANSLATE_KEY", "Google Cloud Translation API key", secret=True)

        self.msg = tk.Label(body, text="", font=FONT_SMALL, fg=SUCCESS, bg=BG_PRIMARY,
                            wraplength=480, justify=tk.LEFT)
        self.msg.pack(anchor=tk.W, pady=(10, 0))

        row = tk.Frame(body, bg=BG_PRIMARY)
        row.pack(fill=tk.X, pady=(6, 0))
        tk.Button(row, text="Save", font=FONT_HEADING, fg=LOGO_DARK, bg=LOGO_BLUE,
                  relief=tk.FLAT, padx=18, pady=6, cursor="hand2",
                  command=self._save).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(row, text="Send test email to me", font=FONT_BODY, fg=TEXT_PRIMARY, bg=BG_HOVER,
                  relief=tk.FLAT, padx=12, pady=6, cursor="hand2",
                  command=self._test_email).pack(side=tk.LEFT)

    def _save(self):
        from ratt import api_config as cfg
        cfg.save_services({k: e.get() for k, e in self.entries.items()})
        pk, sk = cfg.get_value("PAYSTACK_PUBLIC_KEY"), cfg.get_value("PAYSTACK_SECRET_KEY")
        problems = []
        if pk and not pk.startswith("pk_"):
            problems.append("Public key should start with pk_")
        if sk and not sk.startswith("sk_"):
            problems.append("Secret key should start with sk_")
        st = cfg.get_config_status()
        self.msg.config(
            text=("Saved.  Email: " + ("connected" if st["smtp"] else "not configured") +
                  "  |  Payments: " + st["payment_mode"] +
                  ("\n" + "; ".join(problems) if problems else "")),
            fg="#FFC107" if problems else SUCCESS)

    def _test_email(self):
        from ratt import api_config as cfg
        if not cfg.smtp_configured():
            self.msg.config(text="Save your SMTP settings first.", fg="#FFC107")
            return
        to = config.user.email
        self.msg.config(text=f"Sending test email to {to}...", fg=TEXT_SECONDARY)
        box = {}

        def work():
            try:
                from ratt.email_verification import _send_real_email
                _send_real_email(to, "RATT user", "TEST",
                                 "<p>RATT email is working.</p>", "RATT email is working.")
                box["ok"] = True
            except Exception as e:  # noqa
                box["err"] = str(e)

        threading.Thread(target=work, daemon=True).start()

        def poll():
            try:
                if not (self.dialog and self.dialog.winfo_exists()):
                    return
            except tk.TclError:
                return
            if "ok" in box:
                self.msg.config(text=f"Test email sent to {to}.", fg=SUCCESS)
            elif "err" in box:
                self.msg.config(text=f"Failed: {box['err']}", fg=ERROR)
            else:
                self.dialog.after(200, poll)
        poll()

    def dismiss(self):
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog = None
