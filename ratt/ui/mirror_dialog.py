"""RATT Mirror Dialog.

Allows users to mirror clipboard contents to another user's screen.
The mirrored text appears in a read-only transparent overlay.
"""
import tkinter as tk
from tkinter import messagebox
import secrets
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ratt.app import RattApp

from ratt.ui.styles import *


class MirrorDialog:
    """Dialog for mirroring clipboard to another user."""
    
    def __init__(self, root: tk.Tk, app: 'RattApp'):
        self.root = root
        self.app = app
        self.dialog: Optional[tk.Toplevel] = None
        self.mirror_overlay: Optional[tk.Toplevel] = None
        self._verification_code: str = ""
    
    def show(self):
        """Show the mirror setup dialog."""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.lift()
            return
        
        self.dialog = self.app.new_window("mirror")
        self.dialog.title("RATT — Mirror")
        self.dialog.geometry("450x380")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=BG_PRIMARY)
        self.dialog.transient(self.root)
        self.dialog.grab_set()
        
        # Header
        header = tk.Frame(self.dialog, bg=BG_SECONDARY, pady=12, padx=16)
        header.pack(fill=tk.X)
        
        tk.Label(
            header, text="🪞 Mirror", font=FONT_TITLE,
            fg=ACCENT, bg=BG_SECONDARY
        ).pack(anchor=tk.W)
        
        tk.Label(
            header, text="Mirror text to another user's screen (read-only)",
            font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY
        ).pack(anchor=tk.W, pady=(4, 0))
        
        # Body
        body = tk.Frame(self.dialog, bg=BG_PRIMARY, padx=24, pady=16)
        body.pack(fill=tk.BOTH, expand=True)
        
        # Mode selector
        tk.Label(
            body, text="Mode", font=FONT_BODY,
            fg=TEXT_PRIMARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 4))
        
        self.mode_var = tk.StringVar(value="host")
        
        mode_frame = tk.Frame(body, bg=BG_PRIMARY)
        mode_frame.pack(fill=tk.X, pady=(0, 12))
        
        tk.Radiobutton(
            mode_frame, text="Host (send mirror)", variable=self.mode_var,
            value="host", font=FONT_BODY, fg=TEXT_PRIMARY, bg=BG_PRIMARY,
            selectcolor=BG_SECONDARY, activebackground=BG_PRIMARY,
            activeforeground=TEXT_PRIMARY
        ).pack(side=tk.LEFT, padx=(0, 16))
        
        tk.Radiobutton(
            mode_frame, text="Guest (receive mirror)", variable=self.mode_var,
            value="guest", font=FONT_BODY, fg=TEXT_PRIMARY, bg=BG_PRIMARY,
            selectcolor=BG_SECONDARY, activebackground=BG_PRIMARY,
            activeforeground=TEXT_PRIMARY
        ).pack(side=tk.LEFT)
        
        # Email input (for host)
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
        
        # Code display/entry area
        self.code_frame = tk.Frame(body, bg=BG_PRIMARY)
        self.code_frame.pack(fill=tk.X, pady=(12, 0))
        
        # Connect button
        self.connect_btn = tk.Button(
            body, text="Start Mirror Session", font=FONT_HEADING,
            fg=TEXT_PRIMARY, bg=ACCENT, activebackground=ACCENT_HOVER,
            relief=tk.FLAT, pady=8, cursor="hand2",
            command=self._on_connect
        )
        self.connect_btn.pack(fill=tk.X, pady=(16, 0))
        
        # Demo button
        demo_btn = tk.Button(
            body, text="Demo Mirror Overlay", font=FONT_SMALL,
            fg=TEXT_SECONDARY, bg=BG_HOVER, activebackground=BG_ACTIVE,
            relief=tk.FLAT, pady=4, cursor="hand2",
            command=self._show_demo_overlay
        )
        demo_btn.pack(fill=tk.X, pady=(8, 0))
        
        # Status
        self.status_label = tk.Label(
            body, text="", font=FONT_SMALL,
            fg=TEXT_SECONDARY, bg=BG_PRIMARY
        )
        self.status_label.pack(pady=(8, 0))
    
    def _generate_code(self) -> str:
        """Generate a cryptographically random 6-digit code."""
        return ''.join(secrets.choice('0123456789') for _ in range(6))
    
    def _on_connect(self):
        """Handle connect button."""
        mode = self.mode_var.get()
        
        if mode == "host":
            email = self.email_entry.get().strip()
            if not email or '@' not in email:
                messagebox.showwarning("Invalid Email", "Please enter a valid email address.", parent=self.dialog)
                return
            
            self._verification_code = self._generate_code()
            self.app._active_mirror_code = self._verification_code
            
            for w in self.code_frame.winfo_children():
                w.destroy()
            
            tk.Label(
                self.code_frame, text="Mirror Code:", font=FONT_BODY,
                fg=TEXT_SECONDARY, bg=BG_PRIMARY
            ).pack(anchor=tk.W)
            
            tk.Label(
                self.code_frame, text=self._verification_code, font=(FONT_FAMILY, 32, "bold"),
                fg=SUCCESS, bg=BG_PRIMARY
            ).pack(pady=4)
            
            tk.Label(
                self.code_frame, text="(In production, this code would be emailed to the receiver)",
                font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_PRIMARY
            ).pack()
            
            self.connect_btn.config(state=tk.DISABLED, text="Waiting for Guest...")
            self.status_label.config(
                text=f"Mirror request sent to {email}",
                fg=WARNING
            )
        else:
            # Guest mode - show code entry
            for w in self.code_frame.winfo_children():
                w.destroy()
            
            tk.Label(
                self.code_frame, text="Enter the mirror code:", font=FONT_BODY,
                fg=TEXT_PRIMARY, bg=BG_PRIMARY
            ).pack(anchor=tk.W, pady=(0, 4))
            
            self.code_entry = tk.Entry(
                self.code_frame, font=(FONT_FAMILY, 24, "bold"),
                bg=BG_SECONDARY, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY,
                relief=tk.FLAT, justify=tk.CENTER, width=8,
                highlightbackground=BORDER, highlightthickness=1
            )
            self.code_entry.pack(ipady=4)
            self.code_entry.focus_set()
            
            self.connect_btn.config(text="Accept & Connect", command=self._on_guest_accept)
    
    def _on_guest_accept(self):
        """Handle guest accepting mirror connection."""
        code = self.code_entry.get().strip()
        if not code or not code.isdigit() or len(code) not in (4, 6):
            messagebox.showwarning("Invalid Code", "Please enter a valid numeric mirror code.", parent=self.dialog)
            return
        expected = getattr(self.app, "_active_mirror_code", "")
        if not expected or not secrets.compare_digest(code, expected):
            messagebox.showerror(
                "Invalid Mirror Code",
                "The mirror code was not recognized or has expired.\n"
                "(Generate a host code first, or click 'Demo Mirror Overlay' to preview.)",
                parent=self.dialog
            )
            return
        
        self.status_label.config(text="Connected! Mirror overlay active.", fg=SUCCESS)
        self.connect_btn.config(state=tk.DISABLED, text="Connected")
        self._show_demo_overlay()
    
    def _show_demo_overlay(self):
        """Show a demo mirror overlay window."""
        if self.mirror_overlay and self.mirror_overlay.winfo_exists():
            self.mirror_overlay.destroy()
        
        # Get some content to display
        content = "No clipboard data to mirror."
        slots = self.app.clipboard_manager.get_all_slots()
        if slots:
            first_slot = list(slots.values())[0]
            content = first_slot.content
        
        self.mirror_overlay = tk.Toplevel(self.root)
        self.mirror_overlay.title("RATT Mirror — Read Only")
        self.mirror_overlay.geometry("600x400+100+100")
        self.mirror_overlay.configure(bg="#1a1a2e")
        self.mirror_overlay.attributes("-alpha", 0.9)  # Semi-transparent
        self.mirror_overlay.attributes("-topmost", True)
        
        # Header
        header = tk.Frame(self.mirror_overlay, bg="#16213e", pady=8, padx=12)
        header.pack(fill=tk.X)
        
        tk.Label(
            header, text="🪞 RATT Mirror — READ ONLY", font=FONT_HEADING,
            fg="#e94560", bg="#16213e"
        ).pack(side=tk.LEFT)
        
        close_btn = tk.Button(
            header, text="✕ Close", font=FONT_SMALL,
            fg=TEXT_PRIMARY, bg="#e94560", relief=tk.FLAT,
            padx=8, cursor="hand2",
            command=self.mirror_overlay.destroy
        )
        close_btn.pack(side=tk.RIGHT)
        
        # Content area - read only
        text_frame = tk.Frame(self.mirror_overlay, bg="#1a1a2e", padx=16, pady=12)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(
            text_frame, font=FONT_MONO, bg="#0f3460", fg="#e0e0e0",
            relief=tk.FLAT, padx=12, pady=12, wrap=tk.WORD,
            cursor="arrow"  # No text cursor
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, content)
        text_widget.config(state=tk.DISABLED)  # Read-only
        
        # Disable all keyboard shortcuts for copying
        text_widget.bind("<Control-c>", lambda e: "break")
        text_widget.bind("<Control-a>", lambda e: "break")
        text_widget.bind("<Control-x>", lambda e: "break")
        text_widget.bind("<Button-3>", lambda e: "break")  # Right-click
        
        # Footer
        footer = tk.Label(
            self.mirror_overlay, text="🔒 Volatile memory only  •  Read-only access  •  Cannot copy or modify",
            font=FONT_SMALL, fg=TEXT_MUTED, bg="#1a1a2e", pady=6
        )
        footer.pack(fill=tk.X)
    
    def dismiss(self):
        """Close the dialog."""
        if self.mirror_overlay and self.mirror_overlay.winfo_exists():
            self.mirror_overlay.destroy()
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog = None
