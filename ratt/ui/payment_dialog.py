"""RATT Payment Dialog.

Handles Premium and Enterprise subscription payment.
- Premium: GHS 20 per 10 slots/month, custom slot count (10-50,000)
- Enterprise: GHS 250/month flat, 1-3,000 workers, includes 50 slots
"""
import tkinter as tk
from tkinter import messagebox
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ratt.app import RattApp

from ratt.ui.styles import *
from ratt.config import config, UserTier


class PaymentDialog:
    """Payment dialog for Premium/Enterprise upgrade."""
    
    def __init__(self, root: tk.Tk, app: 'RattApp', plan: str = "premium"):
        self.root = root
        self.app = app
        self.dialog: Optional[tk.Toplevel] = None
        self.plan = plan  # "premium" or "enterprise"
    
    def show(self):
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.lift()
            return
        
        self.dialog = self.app.new_window("payment", scroll=False)
        title = "Premium" if self.plan == "premium" else "Enterprise"
        self.dialog.title(f"RATT - Upgrade to {title}")
        self.dialog.geometry("500x720")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=BG_PRIMARY)
        self.dialog.transient(self.root)
        self.dialog.grab_set()
        
        # Scrollable content (centered inside the main window)
        canvas = tk.Canvas(self.dialog, bg=BG_PRIMARY, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.dialog, orient=tk.VERTICAL, command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=BG_PRIMARY)
        
        self.scroll_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win = canvas.create_window((0, 0), window=self.scroll_frame, anchor="n")
        def _fit(e):
            canvas.itemconfig(win, width=min(e.width, 520))
            canvas.coords(win, e.width // 2, 0)
        canvas.bind("<Configure>", _fit)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.app.set_scroll_canvas(canvas)
        
        # Plan selector tabs
        tab_frame = tk.Frame(self.scroll_frame, bg=BG_SECONDARY)
        tab_frame.pack(fill=tk.X)
        
        self.premium_tab = tk.Button(
            tab_frame, text="Premium", font=FONT_HEADING,
            fg=TEXT_PRIMARY if self.plan == "premium" else TEXT_MUTED,
            bg=ACCENT if self.plan == "premium" else BG_HOVER,
            relief=tk.FLAT, padx=20, pady=10, cursor="hand2",
            command=lambda: self._switch_plan("premium"),
            state=tk.DISABLED if config.user.tier == UserTier.ENTERPRISE else tk.NORMAL
        )
        self.premium_tab.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.enterprise_tab = tk.Button(
            tab_frame, text="Enterprise", font=FONT_HEADING,
            fg=TEXT_PRIMARY if self.plan == "enterprise" else TEXT_MUTED,
            bg="#7B1FA2" if self.plan == "enterprise" else BG_HOVER,
            relief=tk.FLAT, padx=20, pady=10, cursor="hand2",
            command=lambda: self._switch_plan("enterprise")
        )
        self.enterprise_tab.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Content area
        self.content = tk.Frame(self.scroll_frame, bg=BG_PRIMARY, padx=24, pady=16)
        self.content.pack(fill=tk.BOTH, expand=True)
        
        if self.plan == "premium":
            self._build_premium()
        else:
            self._build_enterprise()
    
    def _switch_plan(self, plan):
        self.plan = plan
        self.dialog.destroy()
        self.dialog = None
        self.show()
    
    def _build_premium(self):
        """Build Premium plan UI."""
        body = self.content
        
        # Header
        tk.Label(body, text="Premium Plan", font=(FONT_FAMILY, 16, "bold"),
                 fg="#4CAF50", bg=BG_PRIMARY).pack(anchor=tk.W)
        tk.Label(body, text="Custom clipboard slots for power users",
                 font=FONT_BODY, fg=TEXT_SECONDARY, bg=BG_PRIMARY).pack(anchor=tk.W, pady=(2, 12))
        
        # Pricing
        pf = tk.Frame(body, bg=BG_SECONDARY, padx=14, pady=10)
        pf.pack(fill=tk.X, pady=(0, 12))
        pf.configure(highlightbackground=BORDER, highlightthickness=1)
        tk.Label(pf, text="PRICING", font=FONT_HEADING, fg=ACCENT, bg=BG_SECONDARY).pack(anchor=tk.W)
        tk.Label(pf, text=f"GHS {config.PRICE_GHS_PER_10_SLOTS:.2f} / 10 slots / month",
                 font=(FONT_FAMILY, 12, "bold"), fg=TEXT_PRIMARY, bg=BG_SECONDARY).pack(anchor=tk.W, pady=(4, 0))
        tk.Label(pf, text=f"(USD {config.price_usd_per_10_slots:.2f} / 10 slots / month)",
                 font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY).pack(anchor=tk.W)
        
        # Slot selector
        tk.Label(body, text="NUMBER OF SLOTS", font=FONT_HEADING,
                 fg=TEXT_PRIMARY, bg=BG_PRIMARY).pack(anchor=tk.W, pady=(8, 2))
        tk.Label(body, text=f"Min: {config.MIN_SLOTS_PREMIUM}  |  Max: {config.MAX_SLOTS_PREMIUM:,}",
                 font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_PRIMARY).pack(anchor=tk.W, pady=(0, 6))
        
        sf = tk.Frame(body, bg=BG_PRIMARY)
        sf.pack(fill=tk.X, pady=(0, 6))
        self.slot_var = tk.StringVar(value=str(config.user.premium_slots if (config.user.tier == UserTier.PREMIUM and config.user.premium_slots) else 10))
        self.slot_entry = tk.Entry(sf, textvariable=self.slot_var,
            font=(FONT_FAMILY, 14, "bold"), bg=BG_SECONDARY, fg=ACCENT,
            insertbackground=ACCENT, relief=tk.FLAT, width=10, justify=tk.CENTER,
            highlightbackground=BORDER, highlightthickness=1)
        self.slot_entry.pack(side=tk.LEFT, ipady=6, padx=(0, 8))
        tk.Label(sf, text="slots", font=FONT_BODY, fg=TEXT_SECONDARY, bg=BG_PRIMARY).pack(side=tk.LEFT)
        
        # Quick buttons
        qf = tk.Frame(body, bg=BG_PRIMARY)
        qf.pack(fill=tk.X, pady=(0, 10))
        for s in [10, 20, 50, 100, 500, 1000]:
            tk.Button(qf, text=str(s), font=FONT_SMALL, fg=TEXT_PRIMARY, bg=BG_HOVER,
                      relief=tk.FLAT, padx=6, pady=2, cursor="hand2",
                      command=lambda v=s: self.slot_var.set(str(v))).pack(side=tk.LEFT, padx=2)
        
        self.slot_var.trace_add("write", lambda *_: self._update_premium_price())
        
        # Price display
        self.price_frame = tk.Frame(body, bg="#0D47A1", padx=14, pady=12)
        self.price_frame.pack(fill=tk.X, pady=(0, 12))
        self.price_frame.configure(highlightbackground="#1976D2", highlightthickness=2)
        tk.Label(self.price_frame, text="YOUR TOTAL", font=FONT_SMALL,
                 fg="#90CAF9", bg="#0D47A1").pack(anchor=tk.W)
        self.price_ghs = tk.Label(self.price_frame, text="GHS 20.00 / month",
            font=(FONT_FAMILY, 16, "bold"), fg=TEXT_PRIMARY, bg="#0D47A1")
        self.price_ghs.pack(anchor=tk.W, pady=(4, 0))
        self.price_usd = tk.Label(self.price_frame, text="(USD 1.30 / month)",
            font=FONT_BODY, fg="#90CAF9", bg="#0D47A1")
        self.price_usd.pack(anchor=tk.W)
        
        # Payment method + pay button
        self._build_payment_section(body)
        self._update_premium_price()
    
    def _build_enterprise(self):
        """Build Enterprise plan UI."""
        body = self.content
        
        # Header
        tk.Label(body, text="Enterprise Plan", font=(FONT_FAMILY, 16, "bold"),
                 fg="#CE93D8", bg=BG_PRIMARY).pack(anchor=tk.W)
        tk.Label(body, text="Team clipboard sharing for organizations",
                 font=FONT_BODY, fg=TEXT_SECONDARY, bg=BG_PRIMARY).pack(anchor=tk.W, pady=(2, 12))
        
        # Pricing
        pf = tk.Frame(body, bg="#1A0033", padx=14, pady=12)
        pf.pack(fill=tk.X, pady=(0, 12))
        pf.configure(highlightbackground="#7B1FA2", highlightthickness=2)
        tk.Label(pf, text="FLAT RATE", font=FONT_HEADING, fg="#CE93D8", bg="#1A0033").pack(anchor=tk.W)
        tk.Label(pf, text=f"GHS {config.PRICE_GHS_ENTERPRISE:.2f} / month",
                 font=(FONT_FAMILY, 16, "bold"), fg=TEXT_PRIMARY, bg="#1A0033").pack(anchor=tk.W, pady=(4, 0))
        tk.Label(pf, text=f"(USD {config.price_usd_enterprise:.2f} / month)",
                 font=FONT_BODY, fg="#CE93D8", bg="#1A0033").pack(anchor=tk.W)
        
        # Features
        features = [
            "50 clipboard slots included",
            "Register 1 to 3,000 workers",
            "Share/Mirror/Paste with team members",
            "Translation in 9 languages",
            "Centralized admin dashboard",
            "Priority support",
        ]
        ff = tk.Frame(body, bg=BG_SECONDARY, padx=14, pady=10)
        ff.pack(fill=tk.X, pady=(0, 12))
        ff.configure(highlightbackground=BORDER, highlightthickness=1)
        tk.Label(ff, text="INCLUDES", font=FONT_HEADING, fg="#CE93D8", bg=BG_SECONDARY).pack(anchor=tk.W)
        for feat in features:
            tk.Label(ff, text=f"  [+]  {feat}", font=FONT_BODY,
                     fg=TEXT_PRIMARY, bg=BG_SECONDARY).pack(anchor=tk.W, pady=1)
        
        # Company name
        tk.Label(body, text="COMPANY NAME", font=FONT_HEADING,
                 fg=TEXT_PRIMARY, bg=BG_PRIMARY).pack(anchor=tk.W, pady=(8, 4))
        self.company_entry = tk.Entry(body, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            highlightbackground=BORDER, highlightthickness=1)
        self.company_entry.pack(fill=tk.X, ipady=6, pady=(0, 8))
        
        # Number of workers
        tk.Label(body, text="NUMBER OF WORKERS", font=FONT_HEADING,
                 fg=TEXT_PRIMARY, bg=BG_PRIMARY).pack(anchor=tk.W, pady=(4, 4))
        tk.Label(body, text="Min: 1  |  Max: 3,000", font=FONT_SMALL,
                 fg=TEXT_MUTED, bg=BG_PRIMARY).pack(anchor=tk.W, pady=(0, 4))
        
        wf = tk.Frame(body, bg=BG_PRIMARY)
        wf.pack(fill=tk.X, pady=(0, 12))
        self.worker_var = tk.StringVar(value="10")
        self.worker_entry = tk.Entry(wf, textvariable=self.worker_var,
            font=(FONT_FAMILY, 14, "bold"), bg=BG_SECONDARY, fg="#CE93D8",
            insertbackground="#CE93D8", relief=tk.FLAT, width=10, justify=tk.CENTER,
            highlightbackground=BORDER, highlightthickness=1)
        self.worker_entry.pack(side=tk.LEFT, ipady=6, padx=(0, 8))
        tk.Label(wf, text="workers", font=FONT_BODY, fg=TEXT_SECONDARY, bg=BG_PRIMARY).pack(side=tk.LEFT)
        
        # Price display
        self.price_frame = tk.Frame(body, bg="#4A148C", padx=14, pady=12)
        self.price_frame.pack(fill=tk.X, pady=(0, 12))
        self.price_frame.configure(highlightbackground="#7B1FA2", highlightthickness=2)
        tk.Label(self.price_frame, text="TOTAL", font=FONT_SMALL,
                 fg="#CE93D8", bg="#4A148C").pack(anchor=tk.W)
        self.price_ghs = tk.Label(self.price_frame,
            text=f"GHS {config.PRICE_GHS_ENTERPRISE:.2f} / month",
            font=(FONT_FAMILY, 16, "bold"), fg=TEXT_PRIMARY, bg="#4A148C")
        self.price_ghs.pack(anchor=tk.W, pady=(4, 0))
        self.price_usd = tk.Label(self.price_frame,
            text=f"(USD {config.price_usd_enterprise:.2f} / month)",
            font=FONT_BODY, fg="#CE93D8", bg="#4A148C")
        self.price_usd.pack(anchor=tk.W)
        
        # Payment method + pay button
        self._build_payment_section(body, is_enterprise=True)
    
    MONTH_CHOICES = (1, 3, 6, 12)

    def _build_payment_section(self, body, is_enterprise=False):
        """Email, billing period, payment method, pay button."""
        from ratt.api_config import payment_configured
        self._is_enterprise = is_enterprise
        live = payment_configured()

        # Email address
        tk.Label(body, text="EMAIL ADDRESS", font=FONT_HEADING,
                 fg=TEXT_PRIMARY, bg=BG_PRIMARY).pack(anchor=tk.W, pady=(4, 4))
        self.email_entry = tk.Entry(body, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            highlightbackground=BORDER, highlightthickness=1)
        self.email_entry.pack(fill=tk.X, ipady=6, pady=(0, 10))
        if config.user.email:
            self.email_entry.insert(0, config.user.email)

        # Billing period
        tk.Label(body, text="BILLING PERIOD", font=FONT_HEADING,
                 fg=TEXT_PRIMARY, bg=BG_PRIMARY).pack(anchor=tk.W, pady=(4, 4))
        self.months_var = tk.IntVar(value=1)
        mrow = tk.Frame(body, bg=BG_PRIMARY)
        mrow.pack(fill=tk.X, pady=(0, 6))
        for m in self.MONTH_CHOICES:
            tk.Radiobutton(
                mrow, text=f"{m} month{'s' if m > 1 else ''}", variable=self.months_var,
                value=m, indicatoron=False, font=FONT_SMALL, fg=TEXT_PRIMARY, bg=BG_HOVER,
                selectcolor=LOGO_BLUE, activebackground=BG_ACTIVE, relief=tk.FLAT,
                padx=10, pady=5, cursor="hand2", command=self._refresh_total
            ).pack(side=tk.LEFT, padx=(0, 4))
        self.total_label = tk.Label(body, text="", font=(FONT_FAMILY, 10, "bold"),
                                    fg=LOGO_CYAN, bg=BG_PRIMARY)
        self.total_label.pack(anchor=tk.W, pady=(0, 8))

        # Payment method
        tk.Label(body, text="PAYMENT METHOD", font=FONT_HEADING,
                 fg=TEXT_PRIMARY, bg=BG_PRIMARY).pack(anchor=tk.W, pady=(4, 6))
        self.payment_method = tk.StringVar(value="momo")
        mf = tk.Frame(body, bg=BG_PRIMARY)
        mf.pack(fill=tk.X, pady=(0, 6))
        for val, txt in [("momo", "Mobile Money (MTN, Vodafone, AirtelTigo)"),
                         ("card", "Credit / Debit Card")]:
            rf = tk.Frame(mf, bg=BG_SECONDARY, padx=10, pady=8)
            rf.pack(fill=tk.X, pady=1)
            tk.Radiobutton(rf, text=f"  {txt}", font=FONT_BODY,
                fg=TEXT_PRIMARY, bg=BG_SECONDARY, selectcolor=BG_SECONDARY,
                activebackground=BG_SECONDARY, variable=self.payment_method, value=val,
                command=self._update_payment_fields).pack(anchor=tk.W)

        self.pay_input = tk.Frame(body, bg=BG_PRIMARY)
        self.pay_input.pack(fill=tk.X, pady=(0, 6))
        self._update_payment_fields()

        if live:
            note = ("Secure checkout: you will be taken to Paystack to approve the payment.\n"
                    "RATT never sees or stores your card or Mobile Money PIN.")
            note_fg, note_bg = "#A5D6A7", "#10260F"
        else:
            note = ("DEMO MODE - no real money is charged.\n"
                    "Add your Paystack keys in Settings > Configure Services to accept real payments.")
            note_fg, note_bg = "#FFE082", "#2A2108"
        tk.Label(body, text=note, font=FONT_SMALL, fg=note_fg, bg=note_bg,
                 justify=tk.LEFT, padx=10, pady=8, anchor=tk.W).pack(fill=tk.X, pady=(0, 8))

        btn_color = "#7B1FA2" if is_enterprise else SUCCESS
        btn_text = "Pay & Activate Enterprise" if is_enterprise else "Pay & Upgrade"
        self.pay_btn = tk.Button(body, text=btn_text, font=(FONT_FAMILY, 12, "bold"),
            fg=TEXT_PRIMARY, bg=btn_color, relief=tk.FLAT, pady=10, cursor="hand2",
            command=self._on_pay_enterprise if is_enterprise else self._on_pay_premium)
        self.pay_btn.pack(fill=tk.X, pady=(4, 0))

        tk.Button(body, text="Cancel", font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_PRIMARY,
                  relief=tk.FLAT, cursor="hand2", command=self.dismiss).pack(pady=(4, 0))
        self._refresh_total()

    # ---------- pricing ----------

    def _slot_count(self):
        try:
            return int(self.slot_var.get().replace(",", "").strip())
        except (ValueError, TypeError, AttributeError):
            return 0

    def _monthly_amount(self):
        """GHS per month for the plan being bought (None if input invalid)."""
        if self._is_enterprise:
            return config.PRICE_GHS_ENTERPRISE
        count = self._slot_count()
        if count < config.MIN_SLOTS_PREMIUM or count > config.MAX_SLOTS_PREMIUM:
            return None
        return config.calculate_price(count)["ghs_monthly"]

    def _refresh_total(self):
        if not hasattr(self, "pay_btn") or not hasattr(self, "total_label"):
            return
        monthly = self._monthly_amount()
        base_bg = "#7B1FA2" if self._is_enterprise else SUCCESS
        try:
            if monthly is None:
                self.total_label.config(text="")
                self.pay_btn.config(state=tk.DISABLED, bg=BG_HOVER)
                return
            months = self.months_var.get()
            total = round(monthly * months, 2)
            usd = round(total / config.GHS_TO_USD_RATE, 2)
            self.total_label.config(
                text=f"Total due now: GHS {total:,.2f}  (USD {usd:,.2f})  for {months} month{'s' if months > 1 else ''}")
            label = "Pay GHS {:,.2f} & Activate Enterprise" if self._is_enterprise else "Pay GHS {:,.2f} & Upgrade"
            self.pay_btn.config(state=tk.NORMAL, bg=base_bg, text=label.format(total))
        except tk.TclError:
            pass

    def _update_premium_price(self):
        count = self._slot_count()
        if count < config.MIN_SLOTS_PREMIUM or count > config.MAX_SLOTS_PREMIUM:
            self.price_ghs.config(text="Enter 10 - 50,000 slots")
            self.price_usd.config(text="")
        else:
            p = config.calculate_price(count)
            self.price_ghs.config(text=f"GHS {p['ghs_monthly']:,.2f} / month")
            self.price_usd.config(text=f"(USD {p['usd_monthly']:,.2f} / month)")
        self._refresh_total()

    def _update_payment_fields(self):
        for w in self.pay_input.winfo_children():
            w.destroy()
        if self.payment_method.get() == "momo":
            tk.Label(self.pay_input, text="Mobile Money phone number", font=FONT_SMALL,
                     fg=TEXT_SECONDARY, bg=BG_PRIMARY).pack(anchor=tk.W, pady=(4, 2))
            self.phone_entry = tk.Entry(self.pay_input, font=FONT_BODY,
                bg=BG_SECONDARY, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY,
                relief=tk.FLAT, highlightbackground=BORDER, highlightthickness=1)
            self.phone_entry.pack(fill=tk.X, ipady=6)
            self.phone_entry.insert(0, "+233 ")
        else:
            tk.Label(self.pay_input,
                     text="Card details are entered on the secure checkout page,\nnot inside RATT.",
                     font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_PRIMARY,
                     justify=tk.LEFT).pack(anchor=tk.W, pady=(4, 2))

    def _validate_payment(self):
        email = self.email_entry.get().strip()
        if not email or '@' not in email or '.' not in email.split('@')[-1]:
            messagebox.showwarning("Email Required",
                "Please enter a valid email address.", parent=self.dialog)
            return False
        if self.payment_method.get() == "momo":
            digits = "".join(ch for ch in self.phone_entry.get() if ch.isdigit())
            if len(digits) < 10:
                messagebox.showwarning("Invalid Phone",
                    "Enter a valid Mobile Money phone number.", parent=self.dialog)
                return False
        return True

    # ---------- paying ----------

    def _on_pay_premium(self):
        count = self._slot_count()
        if count < config.MIN_SLOTS_PREMIUM or count > config.MAX_SLOTS_PREMIUM:
            messagebox.showwarning("Invalid Slots",
                f"Enter {config.MIN_SLOTS_PREMIUM} to {config.MAX_SLOTS_PREMIUM:,} slots.", parent=self.dialog)
            return
        self._begin_payment("premium", {"slots": count})

    def _on_pay_enterprise(self):
        company = self.company_entry.get().strip()
        if not company:
            messagebox.showwarning("Company Name", "Enter your company name.", parent=self.dialog)
            return
        try:
            workers = int(self.worker_var.get().strip())
        except (ValueError, TypeError):
            workers = 0
        if workers < 1 or workers > config.MAX_ENTERPRISE_WORKERS:
            messagebox.showwarning("Invalid Workers",
                f"Enter 1 to {config.MAX_ENTERPRISE_WORKERS:,} workers.", parent=self.dialog)
            return
        self._begin_payment("enterprise", {"company": company, "workers": workers})

    def _alive(self):
        try:
            return self.dialog is not None and bool(self.dialog.winfo_exists())
        except tk.TclError:
            return False

    def _run_async(self, fn, callback):
        """Run a blocking network call off the UI thread; callback(result, error) on the UI thread."""
        import threading
        box = {}

        def work():
            try:
                box["v"] = fn()
            except Exception as e:  # noqa
                box["e"] = e

        threading.Thread(target=work, daemon=True).start()

        def poll():
            if not self._alive():
                return
            if "v" in box or "e" in box:
                callback(box.get("v"), box.get("e"))
            else:
                self.dialog.after(150, poll)
        poll()

    def _fail(self, message):
        if self._alive():
            messagebox.showerror("Payment not completed", message, parent=self.dialog)
            self.pay_btn.config(state=tk.NORMAL)
            self._refresh_total()

    def _begin_payment(self, plan, details):
        if not self._validate_payment():
            return
        from ratt.payment_gateway import get_gateway, demo_payment
        months = self.months_var.get()
        total = round(self._monthly_amount() * months, 2)
        email = self.email_entry.get().strip()
        self.pay_btn.config(text="Processing...", state=tk.DISABLED, bg=BG_HOVER)
        self.dialog.update_idletasks()

        gw = get_gateway()
        if not gw.is_configured():
            ref = demo_payment(total, plan)["data"]["reference"]
            self.dialog.after(1200, lambda: self._finish(plan, details, months, total, ref, "DEMO"))
            return

        meta = {"app": "RATT", "plan": plan, "months": months, **details}
        self._run_async(
            lambda: gw.initialize_transaction(email, total, meta),
            lambda res, err: self._on_initialized(gw, res, err, plan, details, months, total))

    def _on_initialized(self, gw, res, err, plan, details, months, total):
        if err or not res or not res.get("status"):
            msg = (res or {}).get("message") or str(err) or "Could not reach the payment service."
            self._fail(msg)
            return
        data = res["data"]
        import webbrowser
        webbrowser.open(data["authorization_url"])
        self.pay_btn.config(text="Waiting for payment... finish in your browser")
        self._poll_verify(gw, data["reference"], plan, details, months, total, tries=120)

    def _poll_verify(self, gw, ref, plan, details, months, total, tries):
        if not self._alive():
            return
        if tries <= 0:
            self._fail("Payment was not confirmed in time. If you were charged, contact support with reference " + ref)
            return
        self._run_async(
            lambda: gw.verify_transaction(ref),
            lambda res, err: self._after_verify(gw, res, err, ref, plan, details, months, total, tries))

    def _after_verify(self, gw, res, err, ref, plan, details, months, total, tries):
        data = ((res or {}).get("data")) or {}
        status = data.get("status")
        if status == "success":
            if data.get("currency") != "GHS" or int(data.get("amount", 0)) < int(round(total * 100)):
                self._fail("The amount paid does not match the plan price. Reference: " + ref)
                return
            self._finish(plan, details, months, total, ref, "Paystack")
        elif status in ("failed", "abandoned", "reversed"):
            self._fail(f"Payment {status}. Please try again.")
        else:
            self.dialog.after(5000, lambda: self._poll_verify(gw, ref, plan, details, months, total, tries - 1))

    def _finish(self, plan, details, months, total, ref, gateway):
        """Activate the plan and start/extend the subscription period."""
        if not self._alive():
            return
        user = config.user
        if plan == "premium":
            user.tier = UserTier.PREMIUM
            user.premium_slots = details["slots"]
            plan_line = f"Plan: Premium  |  Slots: {details['slots']:,}"
        else:
            keep = user.premium_slots if user.tier == UserTier.PREMIUM else 0
            user.tier = UserTier.ENTERPRISE
            user.premium_slots = max(50, keep)      # never reduce slots on upgrade
            user.company_name = details["company"]
            user.max_workers = details["workers"]
            plan_line = f"Plan: Enterprise  |  Workers: {details['workers']:,}  |  Company: {details['company']}"
        user.set_subscription(months)
        config.save_session()

        days = user.days_until_expiry
        messagebox.showinfo(
            "Payment successful" if gateway != "DEMO" else "Demo payment successful",
            f"GHS {total:,.2f} for {months} month{'s' if months > 1 else ''}\n"
            f"{plan_line}\n"
            f"Active for {days} days (until {user.subscription_expiry:%d %b %Y})\n"
            f"Reference: {ref}" + ("\n\n(Demo mode - no real charge)" if gateway == "DEMO" else ""),
            parent=self.dialog)
        self.dialog.destroy()
        self.dialog = None
        self.app.rebuild_ui()

    def dismiss(self):
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog = None
