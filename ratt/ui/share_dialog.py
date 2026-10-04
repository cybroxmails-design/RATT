"""RATT Share Dialog.

Allows users to share clipboard contents with another user.
Generates a 6-character alphanumeric verification code.
"""
import tkinter as tk
from tkinter import messagebox
import string
import random
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ratt.app import RattApp

from ratt.ui.styles import *


class ShareDialog:
    """Dialog for sharing clipboard with another user."""
    
    def __init__(self, root: tk.Tk, app: 'RattApp'):
        self.root = root
        self.app = app
        self.dialog: Optional[tk.Toplevel] = None
        self._verification_code: str = ""
    
    def show(self):
        """Show the share dialog."""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.lift()
            return
        
        self.dialog = self.app.new_window("share")
        self.dialog.title("RATT — Share Clipboard")
        self.dialog.geometry("450x400")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=BG_PRIMARY)
        self.dialog.transient(self.root)
        self.dialog.grab_set()
        
        # Header
        header = tk.Frame(self.dialog, bg=BG_SECONDARY, pady=12, padx=16)
        header.pack(fill=tk.X)
        
        tk.Label(
            header, text="🔗 Share Clipboard", font=FONT_TITLE,
            fg=ACCENT, bg=BG_SECONDARY
        ).pack(anchor=tk.W)
        
        tk.Label(
            header, text="Share your clipboard contents with another RATT user",
            font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY
        ).pack(anchor=tk.W, pady=(4, 0))
        
        # Body
        body = tk.Frame(self.dialog, bg=BG_PRIMARY, padx=24, pady=16)
        body.pack(fill=tk.BOTH, expand=True)
        
        # Email input
        tk.Label(
            body, text="Receiver's Email Address", font=FONT_BODY,
            fg=TEXT_PRIMARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 4))
        
        self.email_entry = tk.Entry(
            body, font=FONT_BODY, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            highlightbackground=BORDER, highlightthickness=1
        )
        self.email_entry.pack(fill=tk.X, ipady=6)
        self.email_entry.focus_set()
        
        # Slot selector
        tk.Label(
            body, text="\nSelect slots to share", font=FONT_BODY,
            fg=TEXT_PRIMARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 4))
        
        self.slot_vars = {}
        slots_frame = tk.Frame(body, bg=BG_PRIMARY)
        slots_frame.pack(fill=tk.X, pady=(0, 8))
        
        from ratt.config import config
        for i in range(1, config.max_slots + 1):
            slot = self.app.clipboard_manager.get_slot(i)
            has_content = slot is not None and not slot.is_empty
            var = tk.BooleanVar(value=False)
            self.slot_vars[i] = var
            
            cb = tk.Checkbutton(
                slots_frame, text=f"Slot {i}",
                variable=var, font=FONT_SMALL,
                fg=TEXT_PRIMARY if has_content else TEXT_MUTED,
                bg=BG_PRIMARY, selectcolor=BG_SECONDARY,
                activebackground=BG_PRIMARY, activeforeground=TEXT_PRIMARY,
                state=tk.NORMAL if has_content else tk.DISABLED
            )
            cb.grid(row=i//6, column=(i-1)%5, sticky=tk.W, padx=4)
        
        # Verification code display (initially hidden)
        self.code_frame = tk.Frame(body, bg=BG_PRIMARY)
        self.code_frame.pack(fill=tk.X, pady=(8, 0))
        
        # Send button
        self.send_btn = tk.Button(
            body, text="Send Share Request", font=FONT_HEADING,
            fg=TEXT_PRIMARY, bg=ACCENT, activebackground=ACCENT_HOVER,
            relief=tk.FLAT, pady=8, cursor="hand2",
            command=self._on_send
        )
        self.send_btn.pack(fill=tk.X, pady=(16, 0))
        
        # Status
        self.status_label = tk.Label(
            body, text="", font=FONT_SMALL,
            fg=TEXT_SECONDARY, bg=BG_PRIMARY
        )
        self.status_label.pack(pady=(8, 0))
    
    def _generate_code(self) -> str:
        """Generate a random 6-character alphanumeric code."""
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choices(chars, k=6))
    
    def _on_send(self):
        """Handle send button click."""
        email = self.email_entry.get().strip()
        if not email or '@' not in email:
            messagebox.showwarning("Invalid Email", "Please enter a valid email address.", parent=self.dialog)
            return
        
        selected_slots = [k for k, v in self.slot_vars.items() if v.get()]
        if not selected_slots:
            messagebox.showwarning("No Slots Selected", "Please select at least one slot to share.", parent=self.dialog)
            return
        
        # Generate verification code
        self._verification_code = self._generate_code()
        
        # Show the code
        for w in self.code_frame.winfo_children():
            w.destroy()
        
        tk.Label(
            self.code_frame, text="Verification Code:", font=FONT_BODY,
            fg=TEXT_SECONDARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W)
        
        tk.Label(
            self.code_frame, text=self._verification_code, font=(FONT_FAMILY, 28, "bold"),
            fg=SUCCESS, bg=BG_PRIMARY
        ).pack(pady=4)
        
        tk.Label(
            self.code_frame, text="(In production, this code would be emailed to the receiver)",
            font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_PRIMARY
        ).pack()
        
        # Update status
        self.send_btn.config(state=tk.DISABLED, text="Request Sent")
        self.status_label.config(
            text=f"Share request sent to {email}\nWaiting for receiver to accept...",
            fg=WARNING
        )
    
    def dismiss(self):
        """Close the dialog."""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog = None
