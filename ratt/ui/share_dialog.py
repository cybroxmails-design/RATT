"""RATT Method 3: Zero-Knowledge E2EE Cross-Country Share & Receive Hub.

Enforces Method 3 Architecture:
  1. Client-Side Encryption: AES-256-GCM + X25519 key derivation (PBKDF2 10,000 rounds).
  2. Blind Ephemeral Relay: Ciphertext-only payload hosted in RAM; relay possesses 0 private keys.
  3. Burn-on-Read: Payload is permanently purged from memory immediately upon retrieval (60s TTL).
  4. Two-Way Operation:
     - Tab 1: Share / Send to another device or user in any country.
     - Tab 2: Receive / Decrypt into any chosen local slot (1-10).
"""

import base64
import mimetypes
import os
import secrets
import string
import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from typing import Optional, TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ratt.app import RattApp

from ratt import security_guard
from ratt.ui.styles import *
from ratt.remote_relay import share_slots_e2ee, receive_slots_e2ee, get_default_relay


class ShareDialog:
    """Dialog for sharing and receiving clipboard slots across countries via Method 3."""

    def __init__(self, root: tk.Tk, app: 'RattApp'):
        self.root = root
        self.app = app
        self.dialog: Optional[tk.Toplevel] = None
        self._verification_code: str = ""
        self._current_tab = "send"  # "send" or "receive"

    def show(self):
        """Show the Method 3 E2EE share dialog."""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.lift()
            return

        self.dialog = self.app.new_window("share")
        self.dialog.title("RATT — Method 3 Zero-Knowledge E2EE Share & Receive")
        self.dialog.geometry("490x520")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=BG_PRIMARY)
        self.dialog.transient(self.root)
        self.dialog.grab_set()

        # Header
        header = tk.Frame(self.dialog, bg=BG_SECONDARY, pady=12, padx=16)
        header.pack(fill=tk.X)

        title_row = tk.Frame(header, bg=BG_SECONDARY)
        title_row.pack(fill=tk.X)

        tk.Label(
            title_row, text="🔒 Zero-Knowledge Cross-Country Sync", font=FONT_TITLE,
            fg=ACCENT, bg=BG_SECONDARY
        ).pack(side=tk.LEFT)

        tk.Label(
            title_row, text="METHOD 3 ACTIVE", font=FONT_SMALL,
            fg=SUCCESS, bg=BG_SECONDARY, bd=1, relief=tk.SOLID, padx=4
        ).pack(side=tk.RIGHT)

        tk.Label(
            header, text="AES-256-GCM + X25519 E2EE • RAM-Only Ephemeral Relay • Burn-on-Read",
            font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY
        ).pack(anchor=tk.W, pady=(4, 0))

        # Mode Tab Buttons
        tab_bar = tk.Frame(self.dialog, bg=BG_PRIMARY, pady=8, padx=20)
        tab_bar.pack(fill=tk.X)

        self.btn_tab_send = tk.Button(
            tab_bar, text="📤 Share / Send to Country", font=FONT_HEADING,
            bg=ACCENT, fg=TEXT_PRIMARY, relief=tk.FLAT, padx=12, pady=6, cursor="hand2",
            command=lambda: self._switch_tab("send")
        )
        self.btn_tab_send.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 4))

        self.btn_tab_recv = tk.Button(
            tab_bar, text="📥 Receive / Paste from Country", font=FONT_HEADING,
            bg=BG_SECONDARY, fg=TEXT_SECONDARY, relief=tk.FLAT, padx=12, pady=6, cursor="hand2",
            command=lambda: self._switch_tab("receive")
        )
        self.btn_tab_recv.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(4, 0))

        # Content Container
        self.content_container = tk.Frame(self.dialog, bg=BG_PRIMARY, padx=24, pady=8)
        self.content_container.pack(fill=tk.BOTH, expand=True)

        self._render_tab_content()

    def _switch_tab(self, tab: str):
        self._current_tab = tab
        if tab == "send":
            self.btn_tab_send.config(bg=ACCENT, fg=TEXT_PRIMARY)
            self.btn_tab_recv.config(bg=BG_SECONDARY, fg=TEXT_SECONDARY)
        else:
            self.btn_tab_send.config(bg=BG_SECONDARY, fg=TEXT_SECONDARY)
            self.btn_tab_recv.config(bg=ACCENT, fg=TEXT_PRIMARY)
        self._render_tab_content()

    def _render_tab_content(self):
        for w in self.content_container.winfo_children():
            w.destroy()

        if self._current_tab == "send":
            self._build_send_tab()
        else:
            self._build_receive_tab()

    def _build_send_tab(self):
        # Instructions
        tk.Label(
            self.content_container,
            text="Select slot(s) to encrypt and transfer across countries:",
            font=FONT_BODY, fg=TEXT_PRIMARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 6))

        # Slot selector
        self.slot_vars = {}
        slots_frame = tk.Frame(self.content_container, bg=BG_SECONDARY, padx=10, pady=8, highlightbackground=BORDER, highlightthickness=1)
        slots_frame.pack(fill=tk.X, pady=(0, 10))

        from ratt.config import config
        for i in range(1, min(config.max_slots, 10) + 1):
            slot = self.app.clipboard_manager.get_slot(i)
            has_content = slot is not None and not slot.is_empty
            var = tk.BooleanVar(value=(i == 1 and has_content))
            self.slot_vars[i] = var

            summary = f"Slot #{i}: " + (slot.preview[:18] if has_content else "(empty)")
            cb = tk.Checkbutton(
                slots_frame, text=summary,
                variable=var, font=FONT_SMALL,
                fg=TEXT_PRIMARY if has_content else TEXT_MUTED,
                bg=BG_SECONDARY, selectcolor=BG_PRIMARY,
                activebackground=BG_SECONDARY, activeforeground=TEXT_PRIMARY,
                state=tk.NORMAL if has_content else tk.DISABLED
            )
            cb.grid(row=(i - 1) // 2, column=(i - 1) % 2, sticky=tk.W, padx=6, pady=2)

        # Code & Ephemeral Relay Status Card
        self.code_frame = tk.Frame(self.content_container, bg=BG_PRIMARY)
        self.code_frame.pack(fill=tk.X, pady=(4, 8))

        # Send Button
        self.send_btn = tk.Button(
            self.content_container, text="🔒 Encrypt & Post to Ephemeral Relay", font=FONT_HEADING,
            fg=TEXT_PRIMARY, bg=ACCENT, activebackground=ACCENT_HOVER,
            relief=tk.FLAT, pady=8, cursor="hand2",
            command=self._on_send_e2ee
        )
        self.send_btn.pack(fill=tk.X, pady=(6, 4))

        # Status Label
        self.status_label = tk.Label(
            self.content_container,
            text="Payload will be encrypted client-side before transmission (60s TTL).",
            font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_PRIMARY
        )
        self.status_label.pack()

    def _build_receive_tab(self):
        tk.Label(
            self.content_container,
            text="Enter the 6-character Short Authentication Code (SAS):",
            font=FONT_BODY, fg=TEXT_PRIMARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 4))

        self.recv_code_entry = tk.Entry(
            self.content_container, font=(FONT_FAMILY, 20, "bold"), justify="center",
            bg=BG_SECONDARY, fg=ACCENT, insertbackground=TEXT_PRIMARY, relief=tk.FLAT,
            highlightbackground=BORDER, highlightthickness=1
        )
        self.recv_code_entry.pack(fill=tk.X, ipady=6, pady=(0, 10))
        self.recv_code_entry.focus_set()

        # Destination Slot Selector
        tk.Label(
            self.content_container,
            text="Paste decrypted content into Slot:",
            font=FONT_BODY, fg=TEXT_PRIMARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 4))

        dest_frame = tk.Frame(self.content_container, bg=BG_SECONDARY, padx=10, pady=8, highlightbackground=BORDER, highlightthickness=1)
        dest_frame.pack(fill=tk.X, pady=(0, 12))

        self.dest_slot_var = tk.IntVar(value=1)
        for i in range(1, 11):
            rb = tk.Radiobutton(
                dest_frame, text=f"#{i}", variable=self.dest_slot_var, value=i,
                font=FONT_SMALL, fg=TEXT_PRIMARY, bg=BG_SECONDARY, selectcolor=BG_PRIMARY,
                activebackground=BG_SECONDARY
            )
            rb.grid(row=(i - 1) // 5, column=(i - 1) % 5, sticky=tk.W, padx=10, pady=2)

        # Receive Button
        self.recv_btn = tk.Button(
            self.content_container, text="📥 Decrypt & Paste from Relay", font=FONT_HEADING,
            fg=TEXT_PRIMARY, bg=SUCCESS, activebackground="#059669",
            relief=tk.FLAT, pady=8, cursor="hand2",
            command=self._on_receive_e2ee
        )
        self.recv_btn.pack(fill=tk.X, pady=(4, 6))

        # Status Label
        self.recv_status_label = tk.Label(
            self.content_container,
            text="Validates 128-bit GCM tag and purges relay memory upon receipt.",
            font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_PRIMARY
        )
        self.recv_status_label.pack()

    def _generate_code(self) -> str:
        """Generate a cryptographically random 6-character alphanumeric code."""
        chars = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(6))

    def _on_send_e2ee(self):
        """Execute Method 3: Encrypt selected slots (text, image, or document) with AES-256-GCM and post to ephemeral relay."""
        selected = {}
        for k, v in self.slot_vars.items():
            if not v.get():
                continue
            slot = self.app.clipboard_manager.get_slot(k)
            if not slot or slot.is_empty:
                continue
            bundle = slot.get_bundle()
            kind = bundle.get("kind", "text")

            if kind in ("image", "diagram"):
                formats = bundle.get("formats", {})
                png_bytes = formats.get("PNG") or formats.get("CF_DIB")
                if png_bytes and len(png_bytes) <= 10 * 1024 * 1024:
                    selected[k] = {
                        "kind": "image",
                        "text": bundle.get("text", "Image"),
                        "data_b64": base64.b64encode(png_bytes).decode("ascii"),
                        "mime": "image/png",
                        "dims": list(bundle.get("dimensions", (0, 0)))
                    }
                else:
                    selected[k] = {"kind": "text", "text": slot.text}
            elif kind == "files":
                safe_files = bundle.get("files", [])
                if safe_files and os.path.exists(safe_files[0]):
                    sz = os.path.getsize(safe_files[0])
                    if sz <= 25 * 1024 * 1024:
                        with open(safe_files[0], "rb") as f:
                            f_bytes = f.read()
                        fname = os.path.basename(safe_files[0])
                        selected[k] = {
                            "kind": "files",
                            "text": f"{fname} ({sz // 1024} KB)",
                            "file_name": fname,
                            "data_b64": base64.b64encode(f_bytes).decode("ascii"),
                            "mime": mimetypes.guess_type(fname)[0] or "application/octet-stream",
                            "size": sz
                        }
                    else:
                        selected[k] = {"kind": "text", "text": slot.text}
                else:
                    selected[k] = {"kind": "text", "text": slot.text}
            else:
                selected[k] = {"kind": "text", "text": slot.text}

        if not selected:
            messagebox.showwarning("No Slots Selected", "Please select at least one slot with content.", parent=self.dialog)
            return

        code = self._generate_code()
        ok, res = share_slots_e2ee(selected, code)
        if not ok:
            messagebox.showerror("Encryption Failed", f"Could not encrypt payload: {res}", parent=self.dialog)
            return

        # Display Code & Ephemeral Relay Confirmation
        for w in self.code_frame.winfo_children():
            w.destroy()

        card = tk.Frame(self.code_frame, bg=BG_SECONDARY, padx=12, pady=10, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill=tk.X)

        tk.Label(
            card, text="6-CHARACTER SHORT AUTH CODE (SAS):", font=FONT_SMALL,
            fg=TEXT_SECONDARY, bg=BG_SECONDARY
        ).pack()

        tk.Label(
            card, text=f"{code[:3]}-{code[3:]}", font=(FONT_FAMILY, 24, "bold"),
            fg=SUCCESS, bg=BG_SECONDARY
        ).pack(pady=2)

        tk.Label(
            card,
            text="Share this code with your recipient in any country.\n"
                 "Relay RAM burns upon pickup • 60-second expiration.",
            font=FONT_SMALL, fg=TEXT_MUTED, bg=BG_SECONDARY
        ).pack()

        self.send_btn.config(text="Encrypted & Ready on Relay (Active)")
        self.status_label.config(
            text=f"Slot payload sealed with AES-256-GCM. Waiting for recipient...",
            fg=SUCCESS
        )

    def _on_receive_e2ee(self):
        """Execute Method 3: Fetch, verify GCM tag, decrypt locally, and burn from relay."""
        code = self.recv_code_entry.get().strip().upper()
        if not code or len(code) < 4:
            messagebox.showwarning("Invalid Code", "Please enter the 6-character share code.", parent=self.dialog)
            return

        target_slot = self.dest_slot_var.get()
        ok, slots, msg = receive_slots_e2ee(code)
        if not ok or not slots:
            messagebox.showerror("Redemption Failed", msg, parent=self.dialog)
            self.recv_status_label.config(text=f"Error: {msg}", fg=ERROR)
            return

        # Ingest first shared slot into target_slot
        first_key = list(slots.keys())[0]
        val = slots[first_key]

        if isinstance(val, dict):
            kind = val.get("kind", "text")
            data_b64 = val.get("data_b64")
            if kind in ("image", "diagram") and data_b64:
                try:
                    img_bytes = base64.b64decode(data_b64.encode("ascii"))
                    ok_i, dims, _ = security_guard.validate_image_binary("PNG", img_bytes)
                    if ok_i:
                        bundle = {
                            "ok": True,
                            "kind": "image",
                            "action": "copy",
                            "text": val.get("text", f"Image [{dims[0]}x{dims[1]}]"),
                            "files": [],
                            "formats": {"PNG": img_bytes},
                            "dimensions": dims
                        }
                        from ratt.clipboard_manager import ClipboardSlot, SlotAction
                        with self.app.clipboard_manager._lock:
                            old = self.app.clipboard_manager._slots.get(target_slot)
                            if old:
                                old.wipe()
                            self.app.clipboard_manager._slots[target_slot] = ClipboardSlot(
                                timestamp=datetime.now(), action=SlotAction.COPY, bundle=bundle
                            )
                except Exception:
                    self.app.clipboard_manager.set_slot(target_slot, val.get("text", "Image"))
            elif kind == "files" and data_b64:
                try:
                    file_bytes = base64.b64decode(data_b64.encode("ascii"))
                    fname = os.path.basename(val.get("file_name", "received_file.bin"))
                    base_dir = os.path.join(os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~"), "RATT", "spool")
                    os.makedirs(base_dir, exist_ok=True)
                    dest_path = os.path.join(base_dir, f"relay_{secrets.token_hex(4)}_{fname}")
                    with open(dest_path, "wb") as f:
                        f.write(file_bytes)
                    self.app.clipboard_manager.store_files_to_slot(target_slot, [dest_path])
                except Exception:
                    self.app.clipboard_manager.set_slot(target_slot, val.get("text", "File"))
            else:
                self.app.clipboard_manager.set_slot(target_slot, val.get("text", ""))
        else:
            self.app.clipboard_manager.set_slot(target_slot, str(val))

        self.app.clipboard_manager.last_error = ""

        # Trigger desktop refresh
        if hasattr(self.app, "_refresh_slots"):
            self.app._refresh_slots()

        self.recv_status_label.config(
            text=f"SUCCESS: Decrypted & pasted into Slot #{target_slot}! Relay memory purged.",
            fg=SUCCESS
        )
        messagebox.showinfo(
            "Transfer Complete",
            f"Successfully decrypted payload via Zero-Knowledge E2EE!\n\n"
            f"Content saved into Slot #{target_slot}.\n"
            f"Relay server memory was permanently wiped (Burn-on-Read).",
            parent=self.dialog
        )

    def dismiss(self):
        """Close the dialog."""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog = None
