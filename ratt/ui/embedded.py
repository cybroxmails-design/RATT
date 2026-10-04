"""Embedded pages.

Lets the existing dialog classes render *inside* the main RATT window
(no separate pop-up windows). `EmbeddedPage` quacks like a Toplevel for the
handful of window-manager calls the dialogs make (title, geometry, grab_set...).
"""
import tkinter as tk

from ratt.ui.styles import *


class EmbeddedPage(tk.Frame):
    """A Frame that accepts (and ignores) Toplevel window-manager calls."""

    def __init__(self, parent, container, app):
        super().__init__(parent, bg=BG_PRIMARY)
        self._container = container
        self._app = app
        self.title_label = None

    # --- window-manager no-ops -------------------------------------------
    def geometry(self, *a, **k): return ""
    def resizable(self, *a, **k): return None
    def transient(self, *a, **k): return None
    def grab_set(self, *a, **k): return None
    def grab_release(self, *a, **k): return None
    def protocol(self, *a, **k): return None
    def iconbitmap(self, *a, **k): return None
    def attributes(self, *a, **k): return None
    def minsize(self, *a, **k): return None
    def maxsize(self, *a, **k): return None
    def focus_force(self): 
        try:
            self.focus_set()
        except tk.TclError:
            pass

    def title(self, text=None):
        """Dialogs call title('RATT - Settings'): show it in the page bar."""
        if text is not None and self.title_label is not None:
            try:
                clean = text.replace("RATT \u2014 ", "").replace("RATT - ", "")
                self.title_label.config(text=clean)
            except tk.TclError:
                pass
        return text

    def destroy(self):
        container = self._container
        app = self._app
        # Re-entrant call (the container is already being destroyed and is
        # tearing down its children, including this page): just destroy ourselves.
        if getattr(container, "_ratt_dying", False):
            super().destroy()
            return
        container._ratt_dying = True
        try:
            if app._page is container:
                app._page = None
                app._page_key = None
        except Exception:
            pass
        try:
            container.destroy()
        except tk.TclError:
            pass
        try:
            app.root.after_idle(app._home_if_empty)
        except Exception:
            pass
