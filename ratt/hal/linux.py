"""RATT Linux Hardware/OS Abstraction Layer (`ratt/hal/linux.py`).

Implements `BasePlatform` for Linux X11 & Wayland desktops (Ubuntu, Fedora, Mint, Debian):
  - Dual Display Server Support:
    * X11 (`libxcb` / `XGrabKey` / `XTestFakeKeyEvent` / `xclip`)
    * Wayland (`org.freedesktop.portal.GlobalShortcuts`, `org.freedesktop.portal.Clipboard`, `wl-clipboard`)
  - Multi-Format MIME Mapping:
    * Files (.docx, .xls, .mp4): `text/uri-list` and `x-special/gnome-copied-files`
    * Diagrams: `image/svg+xml`
    * Images: `image/png`
    * Unformatted Links & Text: `text/plain;charset=utf-8` (with `text/html` stripped)
  - IPC & Memory Security:
    * Unix Domain Socket `/run/user/<uid>/ratt.sock`
    * POSIX `mlock()` and `fcntl.flock`
"""
import ctypes
import hashlib
import os
import secrets
import socket
import subprocess
import urllib.parse
from typing import Dict, List, Optional, Tuple

from ratt import security_guard
from ratt.hal.base import BasePlatform

MIME_URI_LIST = "text/uri-list"
MIME_GNOME_FILES = "x-special/gnome-copied-files"
MIME_SVG = "image/svg+xml"
MIME_PNG = "image/png"
MIME_HTML = "text/html"
MIME_TEXT = "text/plain;charset=utf-8"

_PROCESS_KEY = secrets.token_bytes(32)
_LOCK_FD: Optional[int] = None


def _xor_stream(data: bytes, key: bytes) -> bytes:
    out = bytearray(len(data))
    blocks = (len(data) + 31) // 32
    for b in range(blocks):
        digest = hashlib.sha256(key + b.to_bytes(4, "little")).digest()
        start = b * 32
        end = min(start + 32, len(data))
        for i in range(start, end):
            out[i] = data[i] ^ digest[i - start]
    return bytes(out)


class LinuxPlatform(BasePlatform):
    """Linux (X11 & Wayland) Concrete Hardware/OS Abstraction Layer implementation."""

    def __init__(self):
        self._seq = 0
        self.session_type = os.environ.get("XDG_SESSION_TYPE", "x11").lower()
        self.is_wayland = self.session_type == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
        uid = getattr(os, "getuid", lambda: 1000)()
        self.socket_path = f"/run/user/{uid}/ratt.sock"

    @property
    def platform_name(self) -> str:
        return f"Linux ({'Wayland' if self.is_wayland else 'X11'})"

    def _read_mime_bytes(self, mime: str) -> Optional[bytes]:
        cmd = ["wl-paste", "--no-newline", "--type", mime] if self.is_wayland else [
            "xclip", "-selection", "clipboard", "-t", mime, "-o"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=1.5, check=False)
            if res.returncode == 0 and res.stdout:
                return res.stdout
        except Exception:
            pass
        return None

    def _write_mime_bytes(self, mime: str, data: bytes) -> bool:
        cmd = ["wl-copy", "--type", mime] if self.is_wayland else [
            "xclip", "-selection", "clipboard", "-t", mime, "-i"
        ]
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            proc.communicate(input=data, timeout=2)
            if proc.returncode == 0:
                self._seq += 1
                return True
        except Exception:
            pass
        return False

    def read_clipboard_bundle(self, default_action: str = "copy") -> dict:
        """Read Linux clipboard across `text/uri-list`, `image/svg+xml`, `image/png`, and `text/plain`."""
        # 1. Check `x-special/gnome-copied-files` or `text/uri-list` for files
        gnome_raw = self._read_mime_bytes(MIME_GNOME_FILES)
        uri_raw = self._read_mime_bytes(MIME_URI_LIST)
        action = default_action
        file_uris: List[str] = []
        if gnome_raw:
            lines = gnome_raw.decode("utf-8", errors="ignore").splitlines()
            if lines and lines[0].strip() in ("copy", "cut"):
                action = lines[0].strip()
                file_uris = lines[1:]
        elif uri_raw:
            file_uris = uri_raw.decode("utf-8", errors="ignore").splitlines()

        if file_uris:
            paths = []
            for u in file_uris:
                u = u.strip()
                if u.startswith("file://"):
                    paths.append(urllib.parse.unquote(u[7:]))
            if paths:
                ok, safe_files, err = security_guard.validate_file_list(paths)
                if not ok:
                    return {"ok": False, "error": err}
                names = [os.path.basename(p) for p in safe_files]
                summary = ", ".join(names[:3]) + (f" (+{len(names) - 3} more)" if len(names) > 3 else "")
                return {
                    "ok": True,
                    "kind": "files",
                    "action": action,
                    "text": summary,
                    "files": safe_files,
                    "formats": {},
                    "dimensions": (0, 0),
                }

        # 2. Check for SVG diagrams & PNG images
        svg_data = self._read_mime_bytes(MIME_SVG)
        if svg_data:
            ok_s, clean_svg, err_s = security_guard.sanitize_svg_diagram(svg_data)
            if not ok_s:
                return {"ok": False, "error": err_s}
            return {
                "ok": True,
                "kind": "diagram",
                "action": default_action,
                "text": "Vector Diagram (SVG)",
                "files": [],
                "formats": {"SVG": clean_svg},
                "dimensions": (0, 0),
            }

        png_data = self._read_mime_bytes(MIME_PNG)
        if png_data:
            ok_p, dims_p, err_p = security_guard.validate_image_binary("PNG", png_data)
            if not ok_p:
                return {"ok": False, "error": err_p}
            return {
                "ok": True,
                "kind": "image",
                "action": default_action,
                "text": f"Image [{dims_p[0]}x{dims_p[1]}]",
                "files": [],
                "formats": {"PNG": png_data},
                "dimensions": dims_p,
            }

        # 3. Unformatted Links & Plain Text
        text_bytes = self._read_mime_bytes(MIME_TEXT) or self._read_mime_bytes("UTF8_STRING")
        html_bytes = self._read_mime_bytes(MIME_HTML)
        raw_text = text_bytes.decode("utf-8", errors="replace") if text_bytes else ""
        raw_html = html_bytes.decode("utf-8", errors="ignore") if html_bytes else None

        ok_t, clean_text, is_link, err_t = security_guard.sanitize_unformatted_text_and_links(
            raw_text, raw_html
        )
        if not ok_t:
            return {"ok": False, "error": err_t}
        return {
            "ok": True,
            "kind": "link" if is_link else "text",
            "action": default_action,
            "text": clean_text,
            "files": [],
            "formats": {},
            "dimensions": (0, 0),
        }

    def restore_clipboard_bundle(self, bundle: dict) -> bool:
        ok, _ = self.write_clipboard_bundle(bundle)
        return ok

    def write_clipboard_bundle(self, bundle: dict) -> Tuple[bool, str]:
        if not bundle or not bundle.get("ok"):
            return False, "Invalid slot bundle."
        kind = bundle.get("kind", "text")
        action = bundle.get("action", "copy")

        if kind == "files":
            ok, safe_files, err = security_guard.validate_file_list(bundle.get("files", []))
            if not ok:
                return False, err
            uris = [f"file://{urllib.parse.quote(p)}" for p in safe_files]
            gnome_payload = (action + "\n" + "\n".join(uris)).encode("utf-8")
            uri_payload = ("\r\n".join(uris) + "\r\n").encode("utf-8")
            self._write_mime_bytes(MIME_GNOME_FILES, gnome_payload)
            ok_u = self._write_mime_bytes(MIME_URI_LIST, uri_payload)
            return (True, "") if ok_u else (False, "Failed to write text/uri-list to Linux clipboard.")

        if kind == "diagram" and "SVG" in bundle.get("formats", {}):
            ok_s, clean_svg, err_s = security_guard.sanitize_svg_diagram(bundle["formats"]["SVG"])
            if not ok_s:
                return False, err_s
            ok_w = self._write_mime_bytes(MIME_SVG, clean_svg)
            return (True, "") if ok_w else (False, "Failed to write SVG diagram to Linux clipboard.")

        if kind == "image" and "PNG" in bundle.get("formats", {}):
            ok_p, _, err_p = security_guard.validate_image_binary("PNG", bundle["formats"]["PNG"])
            if not ok_p:
                return False, err_p
            ok_w = self._write_mime_bytes(MIME_PNG, bundle["formats"]["PNG"])
            return (True, "") if ok_w else (False, "Failed to write PNG image to Linux clipboard.")

        raw_text = bundle.get("text", "")
        ok_t, clean_text, _, err_t = security_guard.sanitize_unformatted_text_and_links(raw_text)
        if not ok_t:
            return False, err_t
        ok_w = self._write_mime_bytes(MIME_TEXT, clean_text.encode("utf-8"))
        return (True, "") if ok_w else (False, "Failed to write plain text to Linux clipboard.")

    def inject_keystrokes(self, combo: str) -> None:
        """Send keystroke command over `/run/user/<uid>/ratt.sock` to `ratt_linux_daemon`."""
        if os.path.exists(self.socket_path):
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.settimeout(1.0)
                    s.connect(self.socket_path)
                    s.sendall(f"SEND {combo}\n".encode("utf-8"))
                    return
            except Exception:
                pass
        key = combo.lower().split("+")[-1].strip()
        if self.is_wayland:
            subprocess.run(["wtype", "-M", "ctrl", key, "-m", "ctrl"], check=False)
        else:
            subprocess.run(["xdotool", "key", f"ctrl+{key}"], check=False)

    def single_instance_acquire(self) -> bool:
        global _LOCK_FD
        try:
            import fcntl
            fd = os.open("/tmp/ratt_app_v2.lock", os.O_CREAT | os.O_RDWR, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _LOCK_FD = fd
            return True
        except Exception:
            return False

    def protect_memory_buffer(self, data: bytes) -> bytes:
        if not data:
            return b""
        enc = _xor_stream(data, _PROCESS_KEY)
        try:
            libc = ctypes.CDLL("libc.so.6")
            buf = ctypes.create_string_buffer(enc, len(enc))
            libc.mlock(ctypes.byref(buf), ctypes.c_size_t(len(enc)))
        except Exception:
            pass
        return enc

    def unprotect_memory_buffer(self, data: bytes, orig_len: int = 0) -> bytes:
        if not data:
            return b""
        dec = _xor_stream(data, _PROCESS_KEY)
        return dec[:orig_len] if orig_len > 0 else dec

    def get_sequence_number(self) -> int:
        return self._seq
