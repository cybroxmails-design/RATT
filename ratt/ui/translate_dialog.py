"""RATT Translation Dialog.

Allows premium users to translate clipboard content to another language.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ratt.app import RattApp

from ratt.ui.styles import *
from ratt.config import config
from ratt.translation import SUPPORTED_LANGUAGES, get_language_names


class TranslateDialog:
    """Dialog for translating clipboard content."""
    
    def __init__(self, root: tk.Tk, app: 'RattApp'):
        self.root = root
        self.app = app
        self.dialog: Optional[tk.Toplevel] = None
    
    def show(self, slot_num: Optional[int] = None):
        """Show the translation dialog."""
        if not config.is_premium:
            messagebox.showinfo(
                "Premium Feature",
                "Translation is available for Premium users only.\n\nUpgrade to Premium to unlock this feature.",
                parent=self.root
            )
            return
        
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.lift()
            return
        
        self.dialog = self.app.new_window("translate")
        self.dialog.title("RATT — Translate")
        self.dialog.geometry("500x550")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg=BG_PRIMARY)
        self.dialog.transient(self.root)
        
        # Header
        header = tk.Frame(self.dialog, bg=BG_SECONDARY, pady=12, padx=16)
        header.pack(fill=tk.X)
        
        tk.Label(
            header, text="🌐 Translate", font=FONT_TITLE,
            fg=ACCENT, bg=BG_SECONDARY
        ).pack(anchor=tk.W)
        
        tk.Label(
            header, text="Translate clipboard content to any language (Premium)",
            font=FONT_SMALL, fg=TEXT_SECONDARY, bg=BG_SECONDARY
        ).pack(anchor=tk.W, pady=(4, 0))
        
        # Body
        body = tk.Frame(self.dialog, bg=BG_PRIMARY, padx=24, pady=16)
        body.pack(fill=tk.BOTH, expand=True)
        
        # Source slot selector
        tk.Label(
            body, text="Source Slot", font=FONT_BODY,
            fg=TEXT_PRIMARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 4))
        
        slot_frame = tk.Frame(body, bg=BG_PRIMARY)
        slot_frame.pack(fill=tk.X, pady=(0, 12))
        
        self.slot_var = tk.IntVar(value=slot_num or 1)
        for i in range(1, config.max_slots + 1):
            slot = self.app.clipboard_manager.get_slot(i)
            has_content = slot is not None and not slot.is_empty
            color = get_slot_color(i)
            
            rb = tk.Radiobutton(
                slot_frame, text=str(i), variable=self.slot_var, value=i,
                font=FONT_SMALL, fg=color if has_content else TEXT_MUTED,
                bg=BG_PRIMARY, selectcolor=BG_SECONDARY,
                activebackground=BG_PRIMARY, activeforeground=TEXT_PRIMARY,
                state=tk.NORMAL if has_content else tk.DISABLED
            )
            rb.grid(row=0, column=i-1, padx=2)
        
        # Target language
        tk.Label(
            body, text="Target Language", font=FONT_BODY,
            fg=TEXT_PRIMARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 4))
        
        self.lang_var = tk.StringVar(value="Spanish")
        lang_combo = ttk.Combobox(
            body, textvariable=self.lang_var,
            values=get_language_names(), state="readonly",
            font=FONT_BODY
        )
        lang_combo.pack(fill=tk.X, ipady=4)
        
        # Source text preview
        tk.Label(
            body, text="\nSource Text", font=FONT_BODY,
            fg=TEXT_PRIMARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 4))
        
        self.source_text = tk.Text(
            body, font=FONT_MONO, bg=BG_SECONDARY, fg=TEXT_PRIMARY,
            relief=tk.FLAT, height=4, padx=8, pady=8, wrap=tk.WORD
        )
        self.source_text.pack(fill=tk.X)
        self.source_text.config(state=tk.DISABLED)
        
        # Load initial content
        self._load_slot_content()
        self.slot_var.trace_add("write", lambda *args: self._load_slot_content())
        
        # Translate button
        translate_btn = tk.Button(
            body, text="Translate", font=FONT_HEADING,
            fg=TEXT_PRIMARY, bg=ACCENT, activebackground=ACCENT_HOVER,
            relief=tk.FLAT, pady=8, cursor="hand2",
            command=self._on_translate
        )
        translate_btn.pack(fill=tk.X, pady=(12, 0))
        
        # Result area
        tk.Label(
            body, text="\nTranslation", font=FONT_BODY,
            fg=TEXT_PRIMARY, bg=BG_PRIMARY
        ).pack(anchor=tk.W, pady=(0, 4))
        
        self.result_text = tk.Text(
            body, font=FONT_MONO, bg=BG_SECONDARY, fg=SUCCESS,
            relief=tk.FLAT, height=4, padx=8, pady=8, wrap=tk.WORD
        )
        self.result_text.pack(fill=tk.X)
        self.result_text.config(state=tk.DISABLED)
        tk.Button(
            body, text="Copy translation", font=FONT_BODY,
            fg=LOGO_DARK, bg=LOGO_BLUE, relief=tk.FLAT, pady=4, cursor="hand2",
            command=self._copy_translation
        ).pack(fill=tk.X, pady=(8, 0))
    
    def _load_slot_content(self):
        """Load content from the selected slot."""
        slot_num = self.slot_var.get()
        slot = self.app.clipboard_manager.get_slot(slot_num)
        
        self.source_text.config(state=tk.NORMAL)
        self.source_text.delete("1.0", tk.END)
        if slot and not slot.is_empty:
            self.source_text.insert(tk.END, slot.content)
        else:
            self.source_text.insert(tk.END, "(empty slot)")
        self.source_text.config(state=tk.DISABLED)
    
    def _on_translate(self):
        """Translate the selected slot (network call runs off the UI thread)."""
        import threading
        from ratt.translation import TranslationManager, TranslationError, get_language_code

        slot_num = self.slot_var.get()
        slot = self.app.clipboard_manager.get_slot(slot_num)
        if not slot or slot.is_empty:
            messagebox.showwarning("Empty Slot", "The selected slot is empty.", parent=self.dialog)
            return

        target_lang = self.lang_var.get()
        code = get_language_code(target_lang) or "en"
        self._set_result(f"Translating to {target_lang}...")
        text = slot.content
        box = {}

        def work():
            try:
                box["v"] = TranslationManager().translate(text, code)
            except TranslationError as e:
                box["e"] = str(e)
            except Exception as e:  # noqa
                box["e"] = f"Translation failed ({e.__class__.__name__})"

        threading.Thread(target=work, daemon=True).start()

        def poll():
            try:
                if not (self.dialog and self.dialog.winfo_exists()):
                    return
            except tk.TclError:
                return
            if "v" in box:
                self._translation = box["v"]
                self._set_result(box["v"])
            elif "e" in box:
                self._translation = ""
                self._set_result(box["e"])
            else:
                self.dialog.after(150, poll)
        poll()

    def _set_result(self, text):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, text)
        self.result_text.config(state=tk.DISABLED)

    def _copy_translation(self):
        text = getattr(self, "_translation", "")
        if text:
            import pyperclip
            pyperclip.copy(text)
            self.app.show_notification("Translation copied - press Ctrl+V to paste it")

    def dismiss(self):
        """Close the dialog."""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog = None
