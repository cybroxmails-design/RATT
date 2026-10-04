"""RATT - Rapid Access To Text.

Entry point for the RATT application.
Run this file to start RATT.

Publisher: Cybrox.Inc
"""
import sys
import os
import re
import socket

# Ensure the project root is in the Python path
if getattr(sys, 'frozen', False):
    # Running as compiled .exe
    app_dir = os.path.dirname(sys.executable)
else:
    # Running as script
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# Local-only port used to detect an already-running RATT
INSTANCE_PORT = 47653


def launch_action():
    """Action requested on the command line (from the right-click menu), e.g.
    ['copy', '3'] or ['translate', 'fr'].  Empty list = plain launch."""
    allowed = ("open", "copy", "cut", "paste", "translate", "share", "mirror", "popup")
    args = [a for a in sys.argv[1:4] if re.fullmatch(r"[A-Za-z0-9\-]{1,10}", a)]
    return args if args and args[0] in allowed else []


def acquire_single_instance(action=None):
    """Return a listening socket if we are the first RATT, else None.

    If RATT is already running, hand it the request (show window / run the menu
    action) and return None, so clicking the logo many times never opens
    multiple copies."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        srv.bind(("127.0.0.1", INSTANCE_PORT))
        srv.listen(5)
        return srv
    except OSError:
        srv.close()
        try:
            with socket.create_connection(("127.0.0.1", INSTANCE_PORT), timeout=2) as c:
                c.sendall((("ACTION " + " ".join(action)) if action else "SHOW").encode("ascii") + b"\n")
        except OSError:
            pass
        return None


def main():
    """Main entry point."""
    action = launch_action()
    server = acquire_single_instance(action)
    if server is None:
        return  # another RATT is running; it has been handed the request

    try:
        from ratt.app import RattApp
        app = RattApp()
        if action:
            if action[0] in ("copy", "cut", "paste", "translate"):
                app.root.withdraw()      # keep focus in the user's document
            app._pending_actions.append((action[0], action[1:]))
        app.start_instance_listener(server)
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        # Show error in a GUI messagebox instead of console
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "RATT - Error",
                f"RATT encountered an error:\n\n{e}\n\nPlease restart the application."
            )
            root.destroy()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
