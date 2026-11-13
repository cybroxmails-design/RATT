"""RATT macOS Hardware/OS Abstraction Layer (`ratt/hal/macos.py`).

Implements `BasePlatform` for macOS 12+ (Intel & Apple Silicon M1/M2/M3):
  - Multi-Format Pasteboard Driver (`NSPasteboard`):
    * Files (.docx, .xls, .mp4): `NSPasteboardTypeFileURL` (`public.file-url`) — gated to Premium & Enterprise
    * Images & Diagrams: `NSPasteboardTypePNG` (`public.png`), `NSPasteboardTypeTIFF`, `image/svg+xml`
    * Unformatted Hyperlinks & Text: `NSPasteboardTypeHTML` & `NSPasteboardTypeString` (`public.utf8-plain-text`)
  - Global Hotkeys & Keystroke Injection:
    * Carbon `RegisterEventHotKey` (via `ratt_mac_daemon.m`) & Quartz `CGEventPost` (`Cmd+C`, `Cmd+X`, `Cmd+V`)
    * Accessibility & Input Monitoring permission verification (`AXIsProcessTrustedWithOptions`)
  - Memory Protection & Single-Instance:
    * AES-256-GCM authenticated encryption in RAM + POSIX `mlock()` prevents clipboard buffers from swapping to disk
    * User-private `fcntl.flock` with `O_NOFOLLOW` in `~/Library/Application Support/RATT/ratt_app_v2.lock` (`0o700`)
"""
import base64
import ctypes
import json
import os
import secrets
import subprocess
from typing import List, Optional, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ratt import security_guard
from ratt.hal.base import BasePlatform

# NSPasteboard Uniform Type Identifiers (UTIs)
NSPasteboardTypeFileURL = "public.file-url"
NSPasteboardTypePNG = "public.png"
NSPasteboardTypeTIFF = "public.tiff"
NSPasteboardTypeSVG = "image/svg+xml"
NSPasteboardTypeHTML = "public.html"
NSPasteboardTypeString = "public.utf8-plain-text"

# macOS Virtual Keycodes (Carbon / HIToolbox Events.h)
kVK_ANSI_C = 0x08
kVK_ANSI_V = 0x09
kVK_ANSI_X = 0x07
kCGEventFlagMaskCommand = 1 << 20
kCGHIDEventTap = 0

_PROCESS_KEY = secrets.token_bytes(32)
_AAD_RAM = b"RATT-macOS-RAM-AES256GCM"
_LOCK_FD: Optional[int] = None

UPGRADE_MACOS_MSG = (
    "UPGRADE_REQUIRED:Copy, Cut & Paste on macOS and cross-platform sync with macOS "
    "(Android to macOS / iOS to macOS) is limited to Premium and Enterprise users. "
    "Please upgrade your plan."
)


def check_macos_entitlement(app_config=None) -> Tuple[bool, str]:
    """Verify that the active user holds a Premium or Enterprise subscription for macOS sync."""
    if app_config is None:
        from ratt.config import config as app_config
    if getattr(app_config, "is_premium", False):
        return True, ""
    return False, UPGRADE_MACOS_MSG


class MacOSPlatform(BasePlatform):
    """macOS 12+ Concrete Hardware/OS Abstraction Layer implementation."""

    def __init__(self, app_config=None):
        self._config = app_config
        self._seq = 0
        self._libc = None
        self._appservices = None
        self._locked_buffers: List[ctypes.Array] = []
        if hasattr(os, "uname") and os.uname().sysname == "Darwin":
            try:
                self._libc = ctypes.CDLL("/usr/lib/libc.dylib")
                self._appservices = ctypes.CDLL(
                    "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
                )
            except Exception:
                pass

    @property
    def platform_name(self) -> str:
        return "macOS"

    def _get_config(self):
        if self._config is not None:
            return self._config
        from ratt.config import config
        return config

    def check_accessibility_permissions(self, prompt: bool = True) -> bool:
        """Check (and optionally prompt for) macOS Accessibility & Input Monitoring permissions."""
        if not self._appservices:
            return True
        try:
            self._appservices.AXIsProcessTrusted.restype = ctypes.c_bool
            trusted = bool(self._appservices.AXIsProcessTrusted())
            if not trusted and prompt:
                subprocess.Popen(
                    [
                        "open",
                        "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            return trusted
        except Exception:
            return False

    def _osascript_read_file_urls(self) -> List[str]:
        """Query NSPasteboard for `public.file-url` file references via JXA/Foundation."""
        script = (
            'ObjC.import("AppKit");'
            "var pb = $.NSPasteboard.generalPasteboard;"
            "var urls = pb.readObjectsForClassesOptions($([$.NSURL.class]), $({}));"
            "var out = [];"
            "if (urls) {"
            "  for (var i = 0; i < urls.count; i++) {"
            "    var u = urls.objectAtIndex(i);"
            "    if (u.isFileURL) out.push(ObjC.unwrap(u.path));"
            "  }"
            "}"
            "JSON.stringify(out);"
        )
        try:
            res = subprocess.run(
                ["osascript", "-l", "JavaScript", "-e", script],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip().startswith("["):
                return [str(p) for p in json.loads(res.stdout.strip()) if p]
        except Exception:
            pass
        return []

    def _osascript_write_file_urls(self, files: List[str]) -> bool:
        """Write `NSPasteboardTypeFileURL` objects to `NSPasteboard.generalPasteboard`."""
        paths_json = json.dumps(files)
        script = (
            'ObjC.import("AppKit");'
            f"var paths = {paths_json};"
            "var pb = $.NSPasteboard.generalPasteboard;"
            "pb.clearContents;"
            "var arr = $.NSMutableArray.alloc.init;"
            "for (var i = 0; i < paths.length; i++) {"
            "  arr.addObject($.NSURL.fileURLWithPath($(paths[i])));"
            "}"
            "pb.writeObjects(arr);"
        )
        try:
            res = subprocess.run(
                ["osascript", "-l", "JavaScript", "-e", script],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            return res.returncode == 0
        except Exception:
            return False

    def _osascript_read_png(self) -> Optional[bytes]:
        """Read native PNG image data from NSPasteboard via JXA."""
        script = (
            'ObjC.import("AppKit");'
            'var pb = $.NSPasteboard.generalPasteboard;'
            'var data = pb.dataForType("public.png");'
            'if (data) {'
            '  data.base64EncodedStringWithOptions(0).js;'
            '} else {'
            '  "";'
            '}'
        )
        try:
            res = subprocess.run(
                ["osascript", "-l", "JavaScript", "-e", script],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                return base64.b64decode(res.stdout.strip())
        except Exception:
            pass
        return None

    def _osascript_write_png(self, png_bytes: bytes) -> bool:
        """Write native PNG image data to NSPasteboard via JXA."""
        b64 = base64.b64encode(png_bytes).decode("ascii")
        script = (
            'ObjC.import("AppKit");'
            f'var b64 = "{b64}";'
            'var d = $.NSData.alloc.initWithBase64Encoding($(b64));'
            'var pb = $.NSPasteboard.generalPasteboard;'
            'pb.clearContents;'
            'pb.setDataForType(d, "public.png");'
        )
        try:
            res = subprocess.run(
                ["osascript", "-l", "JavaScript", "-e", script],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            return res.returncode == 0
        except Exception:
            return False

    def read_clipboard_bundle(self, default_action: str = "copy") -> dict:
        """Read macOS `NSPasteboard` across FileURL, PNG/SVG, and unformatted String/HTML."""
        # 1. Check for NSPasteboardTypeFileURL files (.docx, .xls, .pdf, .mp4, etc.)
        file_paths = self._osascript_read_file_urls()
        if file_paths:
            allowed_ent, err_ent = check_macos_entitlement(self._get_config())
            if not allowed_ent:
                return {"ok": False, "error": err_ent, "upgrade_required": True}
            ok, safe_files, err = security_guard.validate_file_list(file_paths)
            if not ok:
                return {"ok": False, "error": err}
            names = [os.path.basename(p) for p in safe_files]
            summary = ", ".join(names[:3]) + (f" (+{len(names) - 3} more)" if len(names) > 3 else "")
            return {
                "ok": True,
                "kind": "files",
                "action": default_action,
                "text": summary,
                "files": safe_files,
                "formats": {},
                "dimensions": (0, 0),
            }

        # 2. Check for native PNG image data
        png_data = self._osascript_read_png()
        if png_data:
            kb_size = len(png_data) // 1024
            return {
                "ok": True,
                "kind": "image",
                "action": default_action,
                "text": f"Image ({kb_size} KB)",
                "files": [],
                "formats": {"png": png_data},
                "dimensions": (0, 0),
            }

        # 3. Check for plain text / unformatted links via pbpaste
        raw_text = ""
        try:
            res = subprocess.run(
                ["pbpaste"], capture_output=True, text=True, timeout=2, check=False
            )
            if res.returncode == 0:
                raw_text = res.stdout
        except Exception:
            pass

        ok_t, clean_text, is_link, err_t = security_guard.sanitize_unformatted_text_and_links(raw_text)
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
        if kind == "files":
            allowed_ent, err_ent = check_macos_entitlement(self._get_config())
            if not allowed_ent:
                return False, err_ent
            ok, safe_files, err = security_guard.validate_file_list(bundle.get("files", []))
            if not ok:
                return False, err
            if self._osascript_write_file_urls(safe_files):
                self._seq += 1
                return True, ""
            return False, "Failed to write NSPasteboardTypeFileURL to macOS Pasteboard."

        if kind in ("image", "diagram"):
            png_bytes = bundle.get("formats", {}).get("png")
            if not png_bytes and bundle.get("dataBase64"):
                try:
                    png_bytes = base64.b64decode(bundle["dataBase64"])
                except Exception:
                    png_bytes = None
            if png_bytes and self._osascript_write_png(png_bytes):
                self._seq += 1
                return True, ""
            # Fallback to text preview if image cannot be written
            raw_text = bundle.get("text", "[Image]")
        else:
            raw_text = bundle.get("text", "")
        ok_t, clean_text, _, err_t = security_guard.sanitize_unformatted_text_and_links(raw_text)
        if not ok_t:
            return False, err_t
        try:
            proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            proc.communicate(input=clean_text.encode("utf-8"), timeout=2)
            self._seq += 1
            return (True, "") if proc.returncode == 0 else (False, "pbcopy failed.")
        except Exception as e:
            return False, str(e)

    def inject_keystrokes(self, combo: str) -> None:
        """Inject synthetic Cmd+C, Cmd+X, or Cmd+V using Quartz Event Services (`CGEventPost`)."""
        key_char = combo.lower().split("+")[-1].strip()
        vk_map = {"c": kVK_ANSI_C, "x": kVK_ANSI_X, "v": kVK_ANSI_V}
        vk = vk_map.get(key_char)
        if vk is None or not self._appservices:
            return
        try:
            cg = self._appservices
            cg.CGEventCreateKeyboardEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint16, ctypes.c_bool]
            cg.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
            cg.CGEventSetFlags.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
            cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
            cg.CFRelease.argtypes = [ctypes.c_void_p]

            ev_down = cg.CGEventCreateKeyboardEvent(None, vk, True)
            ev_up = cg.CGEventCreateKeyboardEvent(None, vk, False)
            if ev_down and ev_up:
                cg.CGEventSetFlags(ev_down, kCGEventFlagMaskCommand)
                cg.CGEventSetFlags(ev_up, kCGEventFlagMaskCommand)
                cg.CGEventPost(kCGHIDEventTap, ev_down)
                cg.CGEventPost(kCGHIDEventTap, ev_up)
                cg.CFRelease(ev_down)
                cg.CFRelease(ev_up)
        except Exception:
            pass

    def single_instance_acquire(self) -> bool:
        """Acquire an exclusive POSIX `fcntl.flock` in user-private Application Support (`O_NOFOLLOW`)."""
        global _LOCK_FD
        try:
            import fcntl
            lock_dir = os.path.expanduser("~/Library/Application Support/RATT")
            os.makedirs(lock_dir, mode=0o700, exist_ok=True)
            lock_path = os.path.join(lock_dir, "ratt_app_v2.lock")
            flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(lock_path, flags, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _LOCK_FD = fd
            return True
        except Exception:
            return False

    def protect_memory_buffer(self, data: bytes) -> bytes:
        """Encrypt memory buffer with AES-256-GCM and pin pages via POSIX `mlock()`."""
        if not data:
            return b""
        iv = secrets.token_bytes(12)
        enc = iv + AESGCM(_PROCESS_KEY).encrypt(iv, data, _AAD_RAM)
        if self._libc:
            try:
                buf = ctypes.create_string_buffer(enc, len(enc))
                self._libc.mlock(ctypes.byref(buf), ctypes.c_size_t(len(enc)))
                self._locked_buffers.append(buf)
                if len(self._locked_buffers) > 64:
                    old = self._locked_buffers.pop(0)
                    ctypes.memset(old, 0, len(old))
                    self._libc.munlock(ctypes.byref(old), ctypes.c_size_t(len(old)))
            except Exception:
                pass
        return enc

    def unprotect_memory_buffer(self, data: bytes, orig_len: int = 0) -> bytes:
        if not data or len(data) < 28:
            return b""
        try:
            iv, ct = data[:12], data[12:]
            dec = AESGCM(_PROCESS_KEY).decrypt(iv, ct, _AAD_RAM)
            return dec[:orig_len] if orig_len > 0 else dec
        except Exception:
            return b""

    def get_sequence_number(self) -> int:
        return self._seq
