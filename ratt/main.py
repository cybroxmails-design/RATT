"""RATT - Rapid Access To Text.

Entry point of the application.

Publisher: Cybrox
"""
import os
import re
import sys

# Make the project root importable
if getattr(sys, "frozen", False):
    app_dir = os.path.dirname(sys.executable)      # compiled .exe
else:
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

# Actions the right-click menu may ask for on the command line
MENU_ACTIONS = ("open", "copy", "cut", "paste", "translate", "share", "mirror", "popup")


def launch_action():
    """Action requested on the command line, e.g. ['copy', '3'] or ['copy', '1', 'C:\\path\\file.txt'].
    Empty list = plain launch."""
    if len(sys.argv) < 2:
        return []
    verb = sys.argv[1].lower().strip()
    if verb not in MENU_ACTIONS:
        return []
    action = [verb]
    for a in sys.argv[2:5]:
        val = a.strip().strip('"')
        if val:
            action.append(val)
    return action


def set_taskbar_identity():
    """Own taskbar identity, so Windows shows the RATT icon instead of Python's."""
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Cybrox.RATT")
    except (AttributeError, OSError):
        pass


def hand_over(action):
    """RATT is already running: pass the request on and let this launch end."""
    from ratt import daemon_link, instance
    if action:
        # Write to pending_action.txt so the primary instance receives full arguments (including file paths)
        try:
            appdata = os.environ.get("APPDATA", "")
            if appdata:
                p_dir = os.path.join(appdata, "RATT")
                os.makedirs(p_dir, exist_ok=True)
                p_file = os.path.join(p_dir, "pending_action.txt")
                with open(p_file, "w", encoding="utf-8") as f:
                    f.write("\t".join(action))
        except Exception:
            pass
        # Also attempt instant delivery via daemon helper if available
        daemon_link.send_command("ACTION " + " ".join(action[:3]))
    instance.request_show()


def main():
    set_taskbar_identity()
    action = launch_action()

    from ratt import instance
    if not instance.acquire():
        hand_over(action)
        return

    try:
        from ratt.app import RattApp
        app = RattApp()
        if action:
            if action[0] in ("copy", "cut", "paste", "translate"):
                app.root.withdraw()      # keep focus in the user's document
            app.queue_action(action[0], action[1:])
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as error:
        # Show the error in a message box instead of a console
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "RATT - Error",
                f"RATT encountered an error:\n\n{error}\n\nPlease restart the application.")
            root.destroy()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
