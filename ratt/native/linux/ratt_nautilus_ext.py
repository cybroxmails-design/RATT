"""RATT GNOME Files (Nautilus) Context Menu Extension (`ratt_nautilus_ext.py`).

Adds cascading 'RATT v2 > Copy to Slot N / Cut to Slot N / Paste from Slot N'
entries to GNOME Files on Linux and forwards `text/uri-list` file paths over
`/run/user/<uid>/ratt.sock`.
"""
import os
import socket
import urllib.parse

try:
    from gi.repository import GObject, Nautilus
except ImportError:
    GObject = object
    Nautilus = None


def _send_ipc(cmd: str) -> None:
    uid = getattr(os, "getuid", lambda: 1000)()
    sock_path = f"/run/user/{uid}/ratt.sock"
    if not os.path.exists(sock_path):
        return
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect(sock_path)
            s.sendall((cmd + "\n").encode("utf-8"))
    except Exception:
        pass


if Nautilus is not None:
    class RattNautilusExtension(GObject.GObject, Nautilus.MenuProvider):
        def get_file_items(self, *args):
            files = args[-1] if args else []
            top = Nautilus.MenuItem(name="RattMenu::Root", label="RATT v2", tip="Rapid Access To Text v2")
            sub = Nautilus.Menu()
            top.set_submenu(sub)

            for slot in range(1, 11):
                item = Nautilus.MenuItem(
                    name=f"RattMenu::CopySlot{slot}",
                    label=f"Copy to Slot {slot}",
                )
                paths = [urllib.parse.unquote(f.get_uri()[7:]) for f in files if f.get_uri().startswith("file://")]
                item.connect("activate", lambda _i, s=slot, p=paths: _send_ipc(f"ACTION copy {s}\t" + "\t".join(p)))
                sub.append_item(item)
            return [top]
