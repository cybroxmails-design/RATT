"""RATT Sign Up / Account Dialog.

Allows users to create an account and upgrade to Premium.
"""
import tkinter as tk
from tkinter import messagebox
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ratt.app import RattApp

from ratt.ui.styles import *
from ratt.config import config, UserTier


class SignupDialog:
    """Sign up and account management dialog with upgrade option."""
    
    def __init__(self, root: tk.Tk, app: 'RattApp'):
        self.root = root
        self.app = app
        self.dialog: Optional[tk.Toplevel] = None
    
    def show(self):
        """Show the signup/account dialog."""
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
            self._build_signup_view()
    
    def _build_signup_view(self):
        """Build the sign up / login view."""
        self.dialog.title("RATT \u2014 Sign Up")
        self.dialog.geometry("420x580")
        
        # Header
        header = tk.Frame(self.dialog, bg=LOGO_BLUE, pady=20, padx=24)
        header.pack(fill=tk.X)
        
        tk.Label(
            header, text=f"{config.APP_NAME}", font=(FONT_FAMILY, 20, "bold"),
            fg=LOGO_DARK, bg=LOGO_BLUE
        ).pack()
        
        tk.Label(
            header, text="Create your account",
            font=FONT_BODY, fg=LOGO_NAVY, bg=LOGO_BLUE
        ).pack(pady=(4, 0))
        
        # Body
        body = tk.Frame(self.dialog, bg=BG_PRIMARY, padx=32, pady=20)
        body.pack(fill=tk.BOTH, expand=True)
        
        # Display name
        tk.Label(
            body, text="Display Name", font=FONT_BODY,
            fg=TEXT_SECONDARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 4))
        
        self.name_entry = tk.Entry(
            body, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            highlightbackground=BORDER, highlightthickness=1
        )
        self.name_entry.pack(fill=tk.X, ipady=8)
        
        # Email
        tk.Label(
            body, text="Email Address", font=FONT_BODY,
            fg=TEXT_SECONDARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(16, 4))
        
        self.email_entry = tk.Entry(
            body, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            highlightbackground=BORDER, highlightthickness=1
        )
        self.email_entry.pack(fill=tk.X, ipady=8)
        
        # Password
        tk.Label(
            body, text="Password", font=FONT_BODY,
            fg=TEXT_SECONDARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(16, 4))
        
        self.password_entry = tk.Entry(
            body, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            show="\u2022", highlightbackground=BORDER, highlightthickness=1
        )
        self.password_entry.pack(fill=tk.X, ipady=8)
        
        # Confirm Password
        tk.Label(
            body, text="Confirm Password", font=FONT_BODY,
            fg=TEXT_SECONDARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(16, 4))
        
        self.confirm_entry = tk.Entry(
            body, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            show="\u2022", highlightbackground=BORDER, highlightthickness=1
        )
        self.confirm_entry.pack(fill=tk.X, ipady=8)
        
        # Sign Up button
        signup_btn = tk.Button(
            body, text="Create Account", font=FONT_HEADING,
            fg=TEXT_PRIMARY, bg=ACCENT, activebackground=ACCENT_HOVER,
            relief=tk.FLAT, pady=10, cursor="hand2",
            command=self._on_signup
        )
        signup_btn.pack(fill=tk.X, pady=(24, 8))
        
        # Divider
        div_frame = tk.Frame(body, bg=BG_PRIMARY)
        div_frame.pack(fill=tk.X, pady=8)
        tk.Frame(div_frame, bg=BORDER, height=1).pack(fill=tk.X, side=tk.LEFT, expand=True)
        tk.Label(div_frame, text=" or ", font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_PRIMARY).pack(side=tk.LEFT)
        tk.Frame(div_frame, bg=BORDER, height=1).pack(fill=tk.X, side=tk.LEFT, expand=True)
        
        # Login button (secondary)
        login_btn = tk.Button(
            body, text="Already have an account? Log In", font=FONT_SMALL,
            fg=ACCENT, bg=BG_PRIMARY, activebackground=BG_PRIMARY,
            activeforeground=ACCENT_HOVER, relief=tk.FLAT, cursor="hand2",
            command=self._on_login
        )
        login_btn.pack()
        
        self.name_entry.focus_set()
    
    def _build_account_view(self):
        """Build the logged-in account view with upgrade option."""
        self.dialog.title("RATT \u2014 My Account")
        self.dialog.geometry("420x520")
        
        # Header with user info
        header = tk.Frame(self.dialog, bg=LOGO_BLUE, pady=20, padx=24)
        header.pack(fill=tk.X)
        
        tk.Label(
            header, text=f"Welcome, {config.user.display_name}!",
            font=(FONT_FAMILY, 16, "bold"), fg=LOGO_DARK, bg=LOGO_BLUE
        ).pack()
        
        tk.Label(
            header, text=config.user.email,
            font=FONT_BODY, fg=LOGO_NAVY, bg=LOGO_BLUE
        ).pack(pady=(4, 0))
        
        # Body
        body = tk.Frame(self.dialog, bg=BG_PRIMARY, padx=32, pady=20)
        body.pack(fill=tk.BOTH, expand=True)
        
        # Current Plan section
        tk.Label(
            body, text="YOUR PLAN", font=FONT_HEADING,
            fg=TEXT_PRIMARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 8))
        
        plan_frame = tk.Frame(body, bg=BG_SECONDARY, padx=16, pady=16)
        plan_frame.pack(fill=tk.X, pady=(0, 16))
        plan_frame.configure(highlightbackground=BORDER, highlightthickness=1)
        
        if config.is_enterprise:
            plan_name, plan_color = "Enterprise Plan", "#CE93D8"
            plan_desc = f"{config.user.company_name or 'Your company'}  |  up to {config.user.max_workers:,} workers"
        elif config.is_premium:
            plan_name, plan_color = "Premium Plan", SUCCESS
            plan_desc = f"{config.max_slots:,} clipboard slots"
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
        
        # Renewal countdown (paid plans)
        if config.is_premium and config.user.subscription_expiry is not None:
            from datetime import datetime
            days = config.user.days_until_expiry
            if config.user.subscription_expiry <= datetime.now():
                cd_text, cd_fg = "Subscription EXPIRED - renew now", ERROR
            else:
                cd_text = (f"{days} day{'s' if days != 1 else ''} remaining "
                           f"(until {config.user.subscription_expiry:%d %b %Y})")
                cd_fg = "#FFC107" if days <= 30 else LOGO_CYAN
            tk.Label(plan_frame, text=cd_text, font=(FONT_FAMILY, 9, "bold"),
                     fg=cd_fg, bg=BG_SECONDARY).pack(anchor=tk.W, pady=(6, 0))
        
        # Features list
        trial_note = "" if config.is_premium else f" ({config.user.trial_days_remaining} days left)"
        features = [
            (f"Clipboard slots ({config.max_slots:,})", True),
            (f"Share & Mirror{trial_note}", config.is_premium or config.user.is_trial_active),
            ("Translation (9 languages)", config.is_premium),
            ("Add connections to share with", config.is_premium),
            ("Team accounts (up to 3,000 workers)", config.is_enterprise),
        ]
        
        for feature, available in features:
            icon = "[+]" if available else "[x]"
            fg = TEXT_PRIMARY if available else TEXT_MUTED
            tk.Label(
                plan_frame, text=f"  {icon}  {feature}",
                font=FONT_SMALL, fg=fg, bg=BG_SECONDARY
            ).pack(anchor=tk.W, pady=1)
        
        # Plan actions
        def _action(text, bg, fg, cmd):
            tk.Button(body, text=text, font=FONT_HEADING, fg=fg, bg=bg,
                      activebackground=bg, relief=tk.FLAT, pady=8, cursor="hand2",
                      command=cmd).pack(fill=tk.X, pady=(0, 8))
        
        if not config.is_premium:
            _action("Upgrade to Premium  (from GHS 20 / 10 slots)", SUCCESS, TEXT_PRIMARY,
                    lambda: self.app._open_payment("premium"))
            _action(f"Upgrade to Enterprise  (GHS {config.PRICE_GHS_ENTERPRISE:.0f} / month)",
                    "#7B1FA2", TEXT_PRIMARY, lambda: self.app._open_payment("enterprise"))
        elif not config.is_enterprise:
            _action("Renew Premium", LOGO_BLUE, LOGO_DARK, lambda: self.app._open_payment("premium"))
            _action(f"Upgrade to Enterprise  (GHS {config.PRICE_GHS_ENTERPRISE:.0f} / month)",
                    "#7B1FA2", TEXT_PRIMARY, lambda: self.app._open_payment("enterprise"))
        else:
            _action("Renew Enterprise", LOGO_BLUE, LOGO_DARK, lambda: self.app._open_payment("enterprise"))
        
        if config.is_premium:
            tk.Button(
                body, text="Switch to Basic Plan", font=FONT_SMALL,
                fg=TEXT_MUTED, bg=BG_HOVER, activebackground=BG_ACTIVE,
                relief=tk.FLAT, pady=4, cursor="hand2",
                command=self._on_downgrade
            ).pack(fill=tk.X, pady=(0, 12))
        
        # Log Out button
        logout_btn = tk.Button(
            body, text="Log Out", font=FONT_BODY,
            fg=TEXT_PRIMARY, bg=ERROR, activebackground="#D32F2F",
            relief=tk.FLAT, pady=8, cursor="hand2",
            command=self._on_logout
        )
        logout_btn.pack(fill=tk.X, pady=(8, 0))
    
    def _on_signup(self):
        """Handle sign up — validate form then send verification code."""
        name = self.name_entry.get().strip()
        email = self.email_entry.get().strip()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()
        
        # Validation
        if not name:
            messagebox.showwarning("Missing Field", "Please enter your display name.", parent=self.dialog)
            return
        if not email or '@' not in email or '.' not in email.split('@')[-1]:
            messagebox.showwarning("Invalid Email", "Please enter a valid email address.", parent=self.dialog)
            return
        if len(password) < 6:
            messagebox.showwarning("Weak Password", "Password must be at least 6 characters.", parent=self.dialog)
            return
        if password != confirm:
            messagebox.showwarning("Password Mismatch", "Passwords do not match.", parent=self.dialog)
            return
        
        # Store pending signup info
        self._pending_name = name
        self._pending_email = email
        
        # Generate and send verification code
        from ratt.email_verification import create_verification, send_verification_email
        token = create_verification(email, name)
        success, msg = send_verification_email(email, name, token)
        if not success:
            messagebox.showerror("Email not sent", msg, parent=self.dialog)
            return
        
        # Store token for Phase 1 demo mode (when SMTP not configured)
        self._demo_token = None
        if "[DEMO]" in msg:
            # Extract code from demo message
            import re
            m = re.search(r'Code: (\d{6})', msg)
            if m:
                self._demo_token = m.group(1)
        
        # Show verification screen
        for widget in self.dialog.winfo_children():
            widget.destroy()
        self._build_verify_view(email, name, demo_token=self._demo_token)
    
    def _build_verify_view(self, email: str, name: str, demo_token=None):
        """Show the email verification code entry screen."""
        self.dialog.title("RATT — Verify Your Email")
        self.dialog.geometry("420x480")
        
        # Header
        header = tk.Frame(self.dialog, bg="#0D2137", pady=20, padx=24)
        header.pack(fill=tk.X)
        
        tk.Label(header, text="Check your email", font=(FONT_FAMILY, 16, "bold"),
                 fg="#00BFFF", bg="#0D2137").pack()
        tk.Label(header, text=f"We sent a 6-digit code to:", font=FONT_SMALL,
                 fg="#5599BB", bg="#0D2137").pack(pady=(6, 0))
        tk.Label(header, text=email, font=(FONT_FAMILY, 11, "bold"),
                 fg=TEXT_PRIMARY, bg="#0D2137").pack()
        
        body = tk.Frame(self.dialog, bg=BG_PRIMARY, padx=32, pady=24)
        body.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(body, text="Enter the 6-digit verification code",
                 font=FONT_BODY, fg=TEXT_PRIMARY, bg=BG_PRIMARY).pack(pady=(0, 12))
        
        # Big code entry
        code_frame = tk.Frame(body, bg=BG_PRIMARY)
        code_frame.pack(pady=(0, 8))
        self.code_entry = tk.Entry(
            code_frame, font=(FONT_FAMILY, 28, "bold"),
            bg=BG_SECONDARY, fg="#00BFFF",
            insertbackground="#00BFFF", relief=tk.FLAT,
            width=8, justify=tk.CENTER,
            highlightbackground="#00BFFF", highlightthickness=2
        )
        self.code_entry.pack(ipady=10)
        self.code_entry.focus_set()
        
        # Demo notice (Phase 1 only — shown when SMTP not yet configured)
        if demo_token:
            notice = tk.Frame(body, bg="#1A2A0A", padx=10, pady=8)
            notice.pack(fill=tk.X, pady=(0, 8))
            tk.Label(notice, text="[DEMO MODE — SMTP not configured]",
                     font=FONT_SMALL, fg="#8BC34A", bg="#1A2A0A").pack()
            tk.Label(notice, text=f"Your code:  {demo_token}",
                     font=(FONT_FAMILY, 14, "bold"), fg="#8BC34A", bg="#1A2A0A").pack()
            tk.Label(notice, text="In production, this will be sent to your email only.",
                     font=FONT_SMALL, fg="#558822", bg="#1A2A0A").pack()
        
        self._verify_status = tk.Label(body, text="", font=FONT_SMALL,
                                        fg=ERROR, bg=BG_PRIMARY)
        self._verify_status.pack(pady=(0, 8))
        
        # Verify button
        verify_btn = tk.Button(
            body, text="Verify & Create Account",
            font=FONT_HEADING, fg=TEXT_PRIMARY, bg="#00BFFF",
            activebackground="#0099CC", relief=tk.FLAT, pady=10, cursor="hand2",
            command=lambda: self._on_verify(email, name)
        )
        verify_btn.pack(fill=tk.X, pady=(8, 0))
        self.code_entry.bind("<Return>", lambda e: self._on_verify(email, name))
        
        # Resend link
        resend_btn = tk.Button(
            body, text="Resend Code", font=FONT_SMALL,
            fg=TEXT_MUTED, bg=BG_PRIMARY, relief=tk.FLAT, cursor="hand2",
            command=lambda: self._on_resend(email, name)
        )
        resend_btn.pack(pady=(8, 0))
        
        # Back button
        tk.Button(body, text="Back", font=FONT_SMALL,
                  fg=TEXT_MUTED, bg=BG_PRIMARY, relief=tk.FLAT, cursor="hand2",
                  command=self._back_to_signup).pack(pady=(4, 0))
    
    def _on_verify(self, email: str, name: str):
        """Verify the entered code and complete account creation."""
        code = self.code_entry.get().strip()
        if not code or len(code) != 6 or not code.isdigit():
            self._verify_status.config(text="Please enter the 6-digit code.")
            return
        
        from ratt.email_verification import verify_token
        from datetime import datetime
        
        success, msg = verify_token(code, email)
        
        if not success:
            self._verify_status.config(text=msg, fg=ERROR)
            self.code_entry.delete(0, tk.END)
            return
        
        # Verification passed — create account
        config.user.display_name = name
        config.user.email = email
        config.user.is_logged_in = True
        config.user.created_at = datetime.now()
        config.save_session()  # Persist so user stays logged in on next launch
        
        messagebox.showinfo(
            "Account Verified!",
            f"Welcome to RATT, {name}!\n\n"
            "Your email has been verified and your account is active.\n\n"
            "You can now start using RATT. Upgrade to Premium for more slots!",
            parent=self.dialog
        )
        
        self.dialog.destroy()
        self.dialog = None
        self.app.rebuild_ui()
    
    def _on_resend(self, email: str, name: str):
        """Resend the verification code."""
        from ratt.email_verification import create_verification, send_verification_email
        import re
        
        token = create_verification(email, name)
        success, msg = send_verification_email(email, name, token)
        if not success:
            messagebox.showerror("Email not sent", msg, parent=self.dialog)
            return
        
        demo_token = None
        if "[DEMO]" in msg:
            m = re.search(r'Code: (\d{6})', msg)
            if m:
                demo_token = m.group(1)
        
        for widget in self.dialog.winfo_children():
            widget.destroy()
        self._build_verify_view(email, name, demo_token=demo_token)
        messagebox.showinfo("Code Resent", f"A new code has been sent to {email}.", parent=self.dialog)
    
    def _back_to_signup(self):
        """Go back to the signup form."""
        for widget in self.dialog.winfo_children():
            widget.destroy()
        self._build_signup_view()
    
    def _on_login(self):
        """Switch to login mode."""
        # Clear current view
        for widget in self.dialog.winfo_children():
            widget.destroy()
        
        self.dialog.title("RATT \u2014 Log In")
        self.dialog.geometry("420x400")
        
        # Header
        header = tk.Frame(self.dialog, bg=LOGO_BLUE, pady=20, padx=24)
        header.pack(fill=tk.X)
        
        tk.Label(
            header, text=f"{config.APP_NAME}", font=(FONT_FAMILY, 20, "bold"),
            fg=LOGO_DARK, bg=LOGO_BLUE
        ).pack()
        
        tk.Label(
            header, text="Log in to your account",
            font=FONT_BODY, fg=LOGO_NAVY, bg=LOGO_BLUE
        ).pack(pady=(4, 0))
        
        # Body
        body = tk.Frame(self.dialog, bg=BG_PRIMARY, padx=32, pady=20)
        body.pack(fill=tk.BOTH, expand=True)
        
        # Email
        tk.Label(
            body, text="Email Address", font=FONT_BODY,
            fg=TEXT_SECONDARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 4))
        
        self.login_email = tk.Entry(
            body, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            highlightbackground=BORDER, highlightthickness=1
        )
        self.login_email.pack(fill=tk.X, ipady=8)
        
        # Password
        tk.Label(
            body, text="Password", font=FONT_BODY,
            fg=TEXT_SECONDARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(16, 4))
        
        self.login_password = tk.Entry(
            body, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            show="\u2022", highlightbackground=BORDER, highlightthickness=1
        )
        self.login_password.pack(fill=tk.X, ipady=8)
        
        # Login button
        login_btn = tk.Button(
            body, text="Log In", font=FONT_HEADING,
            fg=TEXT_PRIMARY, bg=ACCENT, activebackground=ACCENT_HOVER,
            relief=tk.FLAT, pady=10, cursor="hand2",
            command=self._on_do_login
        )
        login_btn.pack(fill=tk.X, pady=(24, 8))
        
        # Back to sign up
        back_btn = tk.Button(
            body, text="Don't have an account? Sign Up", font=FONT_SMALL,
            fg=ACCENT, bg=BG_PRIMARY, activebackground=BG_PRIMARY,
            activeforeground=ACCENT_HOVER, relief=tk.FLAT, cursor="hand2",
            command=lambda: (self.dialog.destroy(), setattr(self, 'dialog', None), self.show())
        )
        back_btn.pack()
        
        self.login_email.focus_set()
    
    def _on_do_login(self):
        """Handle login."""
        email = self.login_email.get().strip()
        password = self.login_password.get()
        
        if not email or '@' not in email:
            messagebox.showwarning("Invalid Email", "Please enter a valid email address.", parent=self.dialog)
            return
        if not password:
            messagebox.showwarning("Missing Password", "Please enter your password.", parent=self.dialog)
            return
        
        # Local login (Phase 2 would verify with server)
        config.user.email = email
        config.user.display_name = email.split('@')[0].title()
        config.user.is_logged_in = True
        config.save_session()  # Persist login across restarts
        
        messagebox.showinfo(
            "Logged In!",
            f"Welcome back, {config.user.display_name}!",
            parent=self.dialog
        )
        
        self.dialog.destroy()
        self.dialog = None
        self.show()
        
        self.app.rebuild_ui()
    
    def _on_upgrade(self):
        """Handle upgrade - open payment dialog."""
        # Close this dialog first
        self.dialog.grab_release()
        self.dialog.destroy()
        self.dialog = None
        
        # Open payment dialog
        from ratt.ui.payment_dialog import PaymentDialog
        payment = PaymentDialog(self.root, self.app)
        payment.show()
    
    def _on_downgrade(self):
        """Handle downgrade to basic."""
        if messagebox.askyesno(
            "Downgrade?",
            "Are you sure you want to switch to the Basic plan?\n\n"
            "You will lose access to slots 3-10 and translation.",
            parent=self.dialog
        ):
            config.user.tier = UserTier.BASIC
            config.user.premium_slots = 0
            config.user.subscription_expiry = None
            config.user.last_renewal_alert = None
            config.save_session()  # Save the downgraded state
            
            self.dialog.destroy()
            self.dialog = None
            self.show()
            
            self.app.rebuild_ui()
    
    def _on_logout(self):
        """Handle logout — clears session from disk."""
        if messagebox.askyesno(
            "Log Out?",
            "Are you sure you want to log out?",
            parent=self.dialog
        ):
            config.clear_session()  # Delete saved session file
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
            
            self.dialog.destroy()
            self.dialog = None
            
            self.app.rebuild_ui()
    
    def dismiss(self):
        """Close the dialog."""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog = None
