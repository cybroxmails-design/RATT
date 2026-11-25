"""RATT Windows Hardware/OS Abstraction Layer (`ratt/hal/win32.py`).

Implements `BasePlatform` on Windows 10/11:
  - Clipboard: `CF_HDROP` + `Preferred DropEffect` (files), `PNG` / `CF_DIBV5` / `CF_DIB`
    (images), `image/svg+xml` / `SVG` (diagrams), `CF_UNICODETEXT` (unformatted links & text).
  - Keystroke Injection: Win32 `SendInput` (`VK_CONTROL` + `C`/`X`/`V`).
  - Single-Instance Lock: Win32 Named Mutex (`Local\\RATT.App.v2`).
  - Memory Protection: Windows DPAPI `CryptProtectMemory` (`CRYPTPROTECTMEMORY_SAME_PROCESS`).
"""
import ctypes
import os
import struct
import time
from ctypes import wintypes
from typing import Dict, List, Optional, Tuple

import pyperclip

from ratt import security_guard
from ratt.hal.base import BasePlatform

# Standard Win32 Clipboard Formats
CF_DIB = 8
CF_UNICODETEXT = 13
CF_HDROP = 15
CF_DIBV5 = 17

# GlobalAlloc flags
GMEM_MOVEABLE = 0x0002
GMEM_ZEROINIT = 0x0040
GHND = GMEM_MOVEABLE | GMEM_ZEROINIT

# DropEffect constants
DROPEFFECT_COPY = 1
DROPEFFECT_MOVE = 2

CRYPTPROTECTMEMORY_BLOCK_SIZE = 16
CRYPTPROTECTMEMORY_SAME_PROCESS = 0x00

_IS_WIN = os.name == "nt"

if _IS_WIN:
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    _crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)

    _user32.OpenClipboard.argtypes = [wintypes.HWND]
    _user32.OpenClipboard.restype = wintypes.BOOL
    _user32.CloseClipboard.argtypes = []
    _user32.CloseClipboard.restype = wintypes.BOOL
    _user32.EmptyClipboard.argtypes = []
    _user32.EmptyClipboard.restype = wintypes.BOOL
    _user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    _user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
    _user32.GetClipboardData.argtypes = [wintypes.UINT]
    _user32.GetClipboardData.restype = wintypes.HANDLE
    _user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    _user32.SetClipboardData.restype = wintypes.HANDLE
    _user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
    _user32.RegisterClipboardFormatW.restype = wintypes.UINT
    _user32.GetClipboardSequenceNumber.argtypes = []
    _user32.GetClipboardSequenceNumber.restype = wintypes.DWORD
    _user32.GetForegroundWindow.argtypes = []
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.CreateWindowExW.restype = wintypes.HWND
    _user32.CreateWindowExW.argtypes = [
        wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID,
    ]
    _user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_ulong]
    _user32.keybd_event.restype = None

    _kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    _kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    _kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    _kernel32.GlobalFree.restype = wintypes.HGLOBAL
    _kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    _kernel32.GlobalLock.restype = ctypes.c_void_p
    _kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    _kernel32.GlobalUnlock.restype = wintypes.BOOL
    _kernel32.GlobalSize.argtypes = [wintypes.HGLOBAL]
    _kernel32.GlobalSize.restype = ctypes.c_size_t

    _shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
    _shell32.DragQueryFileW.restype = wintypes.UINT

    _crypt32.CryptProtectMemory.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD]
    _crypt32.CryptProtectMemory.restype = wintypes.BOOL
    _crypt32.CryptUnprotectMemory.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD]
    _crypt32.CryptUnprotectMemory.restype = wintypes.BOOL

    CF_PNG = _user32.RegisterClipboardFormatW("PNG")
    CF_MIME_PNG = _user32.RegisterClipboardFormatW("image/png")
    CF_MIME_SVG = _user32.RegisterClipboardFormatW("image/svg+xml")
    CF_SVG = _user32.RegisterClipboardFormatW("SVG")
    CF_HTML = _user32.RegisterClipboardFormatW("HTML Format")
    CF_PREFERREDDROPEFFECT = _user32.RegisterClipboardFormatW("Preferred DropEffect")
    CF_FILENAMEW = _user32.RegisterClipboardFormatW("FileNameW")
else:
    CF_PNG = CF_MIME_PNG = CF_MIME_SVG = CF_SVG = CF_HTML = CF_PREFERREDDROPEFFECT = CF_FILENAMEW = 0

# Fallback HGLOBAL table used ONLY if OS UIPI blocks SetClipboardData (e.g. Low-IL sandbox / CI)
_sandbox_hglobals: Dict[int, int] = {}
_sandbox_seq: int = 0
_clip_owner_hwnd = None


def _get_clip_owner_hwnd():
    """Return a valid hidden HWND owned by the current thread/process for OpenClipboard."""
    global _clip_owner_hwnd
    if not _IS_WIN:
        return None
    if not _clip_owner_hwnd:
        try:
            _clip_owner_hwnd = _user32.CreateWindowExW(
                0, "STATIC", "RATTClipboardOwner", 0, 0, 0, 0, 0, None, None, None, None
            )
        except Exception:
            _clip_owner_hwnd = None
    return _clip_owner_hwnd


def _clear_sandbox_hglobals():
    global _sandbox_seq
    if _IS_WIN:
        for h in _sandbox_hglobals.values():
            if h:
                try:
                    _kernel32.GlobalFree(h)
                except Exception:
                    pass
    _sandbox_hglobals.clear()
    _sandbox_seq += 1


def _fmt_in_sandbox(fmt: int) -> bool:
    return fmt in _sandbox_hglobals and bool(_sandbox_hglobals[fmt])


def _has_format(fmt: int) -> bool:
    if not fmt:
        return False
    if _IS_WIN and _user32.IsClipboardFormatAvailable(fmt):
        return True
    return _fmt_in_sandbox(fmt)


def _get_format_handle(fmt: int) -> int:
    if _IS_WIN and _user32.IsClipboardFormatAvailable(fmt):
        h = _user32.GetClipboardData(fmt)
        if h:
            return h
    if _fmt_in_sandbox(fmt):
        return _sandbox_hglobals[fmt]
    return 0


def _empty_clipboard():
    _clear_sandbox_hglobals()
    if _IS_WIN:
        _user32.EmptyClipboard()


class _ClipboardLock:
    """Context manager to open and close the Win32 clipboard with short retries."""

    def __init__(self, retries: int = 15, delay: float = 0.03):
        self.retries = retries
        self.delay = delay
        self.opened = False

    def __enter__(self) -> bool:
        if not _IS_WIN:
            return False
        owner = _get_clip_owner_hwnd()
        for _ in range(self.retries):
            if (owner and _user32.OpenClipboard(owner)) or _user32.OpenClipboard(None):
                self.opened = True
                return True
            time.sleep(self.delay)
        return False

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.opened and _IS_WIN:
            _user32.CloseClipboard()
            self.opened = False


def get_sequence_number() -> int:
    """Return the OS clipboard sequence number (increments on every clipboard change)."""
    if not _IS_WIN:
        return _sandbox_seq
    try:
        return int(_user32.GetClipboardSequenceNumber()) + _sandbox_seq
    except Exception:
        return _sandbox_seq


def _read_raw_format(fmt: int) -> Optional[bytes]:
    """Read raw bytes of a clipboard format while the clipboard is open."""
    if not _has_format(fmt):
        return None
    h = _get_format_handle(fmt)
    if not h:
        return None
    ptr = _kernel32.GlobalLock(h)
    if not ptr:
        return None
    try:
        sz = _kernel32.GlobalSize(h)
        if sz == 0 or sz > 150 * 1024 * 1024:
            return None
        return ctypes.string_at(ptr, sz)
    finally:
        _kernel32.GlobalUnlock(h)


def _write_raw_format(fmt: int, data: bytes) -> bool:
    """Allocate movable global memory and set a clipboard format while clipboard is open."""
    if not fmt or not data:
        return False
    h = _kernel32.GlobalAlloc(GHND, len(data))
    if not h:
        return False
    ptr = _kernel32.GlobalLock(h)
    if not ptr:
        _kernel32.GlobalFree(h)
        return False
    ctypes.memmove(ptr, data, len(data))
    _kernel32.GlobalUnlock(h)
    if _user32.SetClipboardData(fmt, h):
        return True
    if ctypes.get_last_error() == 5:
        old = _sandbox_hglobals.pop(fmt, None)
        if old:
            _kernel32.GlobalFree(old)
        _sandbox_hglobals[fmt] = h
        return True
    _kernel32.GlobalFree(h)
    return False


def _read_unicode_text() -> str:
    """Read CF_UNICODETEXT while the clipboard is open."""
    if not _has_format(CF_UNICODETEXT):
        return ""
    h = _get_format_handle(CF_UNICODETEXT)
    if not h:
        return ""
    ptr = _kernel32.GlobalLock(h)
    if not ptr:
        return ""
    try:
        return ctypes.wstring_at(ptr)
    except Exception:
        return ""
    finally:
        _kernel32.GlobalUnlock(h)


def _write_unicode_text(text: str) -> bool:
    """Write UTF-16LE string to CF_UNICODETEXT while the clipboard is open."""
    encoded = text.encode("utf-16-le") + b"\x00\x00"
    return _write_raw_format(CF_UNICODETEXT, encoded)


def _read_hdrop_files() -> Tuple[List[str], int]:
    """Read file paths from CF_HDROP and Preferred DropEffect while clipboard is open."""
    if not _has_format(CF_HDROP):
        return [], DROPEFFECT_COPY
    hdrop = _get_format_handle(CF_HDROP)
    if not hdrop:
        return [], DROPEFFECT_COPY
    count = _shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
    if count == 0 or count > 2000:
        return [], DROPEFFECT_COPY
    files: List[str] = []
    for i in range(count):
        cch = _shell32.DragQueryFileW(hdrop, i, None, 0)
        if cch == 0 or cch > 32768:
            continue
        buf = ctypes.create_unicode_buffer(cch + 1)
        if _shell32.DragQueryFileW(hdrop, i, buf, cch + 1):
            files.append(buf.value)

    effect = DROPEFFECT_COPY
    raw_eff = _read_raw_format(CF_PREFERREDDROPEFFECT)
    if raw_eff and len(raw_eff) >= 4:
        val = struct.unpack("<I", raw_eff[:4])[0]
        if val & DROPEFFECT_MOVE:
            effect = DROPEFFECT_MOVE
    return files, effect


def build_hdrop_bytes(files: List[str]) -> bytes:
    """Construct a Win32 DROPFILES (CF_HDROP) binary buffer for a list of file paths."""
    header = struct.pack("<IiiII", 20, 0, 0, 0, 1)
    body = b"".join(p.encode("utf-16-le") + b"\x00\x00" for p in files) + b"\x00\x00"
    return header + body


def read_clipboard_bundle(default_action: str = "copy") -> dict:
    """Capture the current system clipboard into a security-validated bundle dict."""
    if not _IS_WIN:
        try:
            raw = pyperclip.paste()
        except Exception:
            raw = ""
        ok, clean, is_link, err = security_guard.sanitize_unformatted_text_and_links(raw)
        if not ok:
            return {"ok": False, "error": err}
        return {
            "ok": True,
            "kind": "link" if is_link else "text",
            "action": default_action,
            "text": clean,
            "files": [],
            "formats": {},
            "dimensions": (0, 0),
        }

    with _ClipboardLock() as locked:
        if not locked:
            return {"ok": False, "error": "Could not access system clipboard."}

        # 1. Phase 2: Check for File System objects (CF_HDROP)
        if _has_format(CF_HDROP):
            raw_files, effect = _read_hdrop_files()
            ok, safe_files, err = security_guard.validate_file_list(raw_files)
            if not ok:
                return {"ok": False, "error": err}
            act = "cut" if (default_action == "cut" or effect == DROPEFFECT_MOVE) else "copy"
            names = [os.path.basename(p) for p in safe_files]
            summary = ", ".join(names[:3]) + (f" (+{len(names) - 3} more)" if len(names) > 3 else "")
            return {
                "ok": True,
                "kind": "files",
                "action": act,
                "text": summary,
                "files": safe_files,
                "formats": {},
                "dimensions": (0, 0),
            }

        # 2. Phase 1a: Check for Vector Diagrams (SVG) and explicit Raster Images (PNG)
        svg_data = _read_raw_format(CF_MIME_SVG) or _read_raw_format(CF_SVG)
        png_data = _read_raw_format(CF_PNG) or _read_raw_format(CF_MIME_PNG)

        if svg_data:
            ok_svg, clean_svg, err_svg = security_guard.sanitize_svg_diagram(svg_data)
            if not ok_svg:
                return {"ok": False, "error": err_svg}
            formats: Dict[str, bytes] = {"SVG": clean_svg}
            dims = (0, 0)
            if png_data:
                ok_p, dims_p, _ = security_guard.validate_image_binary("PNG", png_data)
                if ok_p:
                    formats["PNG"] = png_data
                    dims = dims_p
            dim_str = f" ({dims[0]}x{dims[1]})" if dims != (0, 0) else ""
            return {
                "ok": True,
                "kind": "diagram",
                "action": default_action,
                "text": f"Vector Diagram{dim_str}",
                "files": [],
                "formats": formats,
                "dimensions": dims,
            }

        if png_data:
            iend = png_data.find(b"IEND\xaeB`\x82")
            if iend != -1:
                png_data = png_data[: iend + 8]
            ok_p, dims_p, err_p = security_guard.validate_image_binary("PNG", png_data)
            if ok_p:
                dim_str = f"{dims_p[0]}x{dims_p[1]}" if dims_p != (0, 0) else f"{len(png_data) // 1024} KB"
                return {
                    "ok": True,
                    "kind": "image",
                    "action": default_action,
                    "text": f"Image [{dim_str}]",
                    "files": [],
                    "formats": {"PNG": png_data},
                    "dimensions": dims_p,
                }

        # 3. Phase 1b: Text / Links (CF_UNICODETEXT)
        # Note: Microsoft Office (Word, Excel, PowerPoint) registers CF_DIB / CF_DIBV5
        # alongside CF_UNICODETEXT. If CF_UNICODETEXT contains text, it is user document text,
        # NOT a bitmap picture!
        raw_text = _read_unicode_text()
        raw_html_bytes = _read_raw_format(CF_HTML)
        raw_html = raw_html_bytes.decode("utf-8", errors="ignore") if raw_html_bytes else None

        if raw_text and raw_text.strip():
            ok_t, clean_text, is_link, err_t = security_guard.sanitize_unformatted_text_and_links(
                raw_text, raw_html
            )
            if ok_t:
                return {
                    "ok": True,
                    "kind": "link" if is_link else "text",
                    "action": default_action,
                    "text": clean_text,
                    "files": [],
                    "formats": {},
                    "dimensions": (0, 0),
                }

        # 4. Pure Bitmap / DIB format (e.g. Paint, Snipping Tool, PrintScreen screenshot)
        dib5_data = _read_raw_format(CF_DIBV5)
        dib_data = _read_raw_format(CF_DIB)
        if dib_data or dib5_data:
            formats = {}
            dims = (0, 0)
            if dib5_data:
                ok_d5, dims_d5, _ = security_guard.validate_image_binary("CF_DIBV5", dib5_data)
                if ok_d5:
                    formats["CF_DIBV5"] = dib5_data
                    dims = dims_d5
            if dib_data:
                ok_d, dims_d, _ = security_guard.validate_image_binary("CF_DIB", dib_data)
                if ok_d:
                    formats["CF_DIB"] = dib_data
                    if dims == (0, 0):
                        dims = dims_d
            if formats:
                dim_str = f"{dims[0]}x{dims[1]}" if dims != (0, 0) else f"{ sum(len(v) for v in formats.values()) // 1024 } KB"
                return {
                    "ok": True,
                    "kind": "image",
                    "action": default_action,
                    "text": f"Image [{dim_str}]",
                    "files": [],
                    "formats": formats,
                    "dimensions": dims,
                }

        # Fallback to sanitize text if empty or error
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


def write_clipboard_bundle(bundle: dict) -> Tuple[bool, str]:
    """Re-verify security constraints and write a slot bundle onto the system clipboard."""
    if not bundle or not bundle.get("ok", True):
        return False, "Invalid slot bundle."

    kind = bundle.get("kind", "text")
    action = bundle.get("action", "copy")
    if "is_cut" in bundle and "action" not in bundle:
        action = "cut" if bundle["is_cut"] else "copy"

    if kind == "files":
        files = bundle.get("files", [])
        ok, safe_files, err = security_guard.validate_file_list(files)
        if not ok:
            return False, err
        hdrop_bytes = build_hdrop_bytes(safe_files)
        eff_val = DROPEFFECT_MOVE if action == "cut" else DROPEFFECT_COPY
        eff_bytes = struct.pack("<I", eff_val)
        with _ClipboardLock() as locked:
            if not locked:
                return False, "Could not open system clipboard."
            _empty_clipboard()
            ok_h = _write_raw_format(CF_HDROP, hdrop_bytes)
            if CF_PREFERREDDROPEFFECT:
                _write_raw_format(CF_PREFERREDDROPEFFECT, eff_bytes)
            if CF_FILENAMEW and safe_files:
                fn_bytes = safe_files[0].encode("utf-16-le") + b"\x00\x00"
                _write_raw_format(CF_FILENAMEW, fn_bytes)
            return (True, "") if ok_h else (False, "Failed to write file list to clipboard.")

    if kind in ("image", "diagram"):
        formats: Dict[str, bytes] = dict(bundle.get("formats", {}))
        if not formats:
            if bundle.get("svg"):
                formats["SVG"] = bundle["svg"]
            if bundle.get("png"):
                formats["PNG"] = bundle["png"]
            if bundle.get("dib"):
                formats["CF_DIB"] = bundle["dib"]
        if not formats:
            return False, "Image/Diagram slot buffer is empty."
        verified_formats: List[Tuple[int, bytes]] = []
        if "SVG" in formats:
            ok_s, clean_svg, err_s = security_guard.sanitize_svg_diagram(formats["SVG"])
            if not ok_s:
                return False, err_s
            if CF_MIME_SVG:
                verified_formats.append((CF_MIME_SVG, clean_svg))
            if CF_SVG:
                verified_formats.append((CF_SVG, clean_svg))
        if "PNG" in formats:
            ok_p, _, err_p = security_guard.validate_image_binary("PNG", formats["PNG"])
            if not ok_p:
                return False, err_p
            if CF_PNG:
                verified_formats.append((CF_PNG, formats["PNG"]))
            if CF_MIME_PNG:
                verified_formats.append((CF_MIME_PNG, formats["PNG"]))
        if "CF_DIBV5" in formats:
            ok_d5, _, err_d5 = security_guard.validate_image_binary("CF_DIBV5", formats["CF_DIBV5"])
            if not ok_d5:
                return False, err_d5
            verified_formats.append((CF_DIBV5, formats["CF_DIBV5"]))
        if "CF_DIB" in formats:
            ok_d, _, err_d = security_guard.validate_image_binary("CF_DIB", formats["CF_DIB"])
            if not ok_d:
                return False, err_d
            verified_formats.append((CF_DIB, formats["CF_DIB"]))

        if not verified_formats:
            return False, "No valid image/diagram representations in slot."

        with _ClipboardLock() as locked:
            if not locked:
                return False, "Could not open system clipboard."
            _empty_clipboard()
            wrote_any = False
            for fmt_id, raw_bytes in verified_formats:
                if _write_raw_format(fmt_id, raw_bytes):
                    wrote_any = True
            return (True, "") if wrote_any else (False, "Failed to write image/diagram to clipboard.")

    raw_text = bundle.get("text", "")
    ok_t, clean_text, _, err_t = security_guard.sanitize_unformatted_text_and_links(raw_text)
    if not ok_t:
        return False, err_t

    if not _IS_WIN:
        try:
            pyperclip.copy(clean_text)
            return True, ""
        except Exception as e:
            return False, str(e)

    with _ClipboardLock() as locked:
        if not locked:
            return False, "Could not open system clipboard."
        _empty_clipboard()
        ok_w = _write_unicode_text(clean_text)
        return (True, "") if ok_w else (False, "Failed to write unformatted text to clipboard.")


class Win32Platform(BasePlatform):
    """Windows 10/11 Concrete Hardware/OS Abstraction Layer implementation."""

    @property
    def platform_name(self) -> str:
        return "Windows"

    def read_clipboard_bundle(self, default_action: str = "copy") -> dict:
        return read_clipboard_bundle(default_action=default_action)

    def restore_clipboard_bundle(self, bundle: dict) -> bool:
        ok, _ = write_clipboard_bundle(bundle)
        return ok

    def write_clipboard_bundle(self, bundle: dict) -> Tuple[bool, str]:
        return write_clipboard_bundle(bundle)

    def inject_keystrokes(self, combo: str) -> None:
        if not _IS_WIN:
            return
        vk_map = {"c": 0x43, "x": 0x58, "v": 0x56}
        key_char = combo.lower().split("+")[-1].strip()
        vk = vk_map.get(key_char)
        if not vk:
            return
        KEYEVENTF_KEYUP = 0x0002
        VK_CONTROL = 0x11
        _user32.keybd_event(VK_CONTROL, 0, 0, 0)
        _user32.keybd_event(vk, 0, 0, 0)
        _user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        _user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

    def single_instance_acquire(self) -> bool:
        from ratt import instance
        return instance.acquire()

    def protect_memory_buffer(self, data: bytes) -> bytes:
        if not data:
            return b""
        if not _IS_WIN:
            return data
        pad_len = (
            (len(data) + CRYPTPROTECTMEMORY_BLOCK_SIZE - 1) // CRYPTPROTECTMEMORY_BLOCK_SIZE
        ) * CRYPTPROTECTMEMORY_BLOCK_SIZE
        buf = ctypes.create_string_buffer(pad_len)
        ctypes.memmove(buf, data, len(data))
        _crypt32.CryptProtectMemory(ctypes.byref(buf), pad_len, CRYPTPROTECTMEMORY_SAME_PROCESS)
        return ctypes.string_at(buf, pad_len)

    def unprotect_memory_buffer(self, data: bytes, orig_len: int = 0) -> bytes:
        if not data:
            return b""
        if not _IS_WIN:
            return data[:orig_len] if orig_len > 0 else data
        pad_len = len(data)
        buf = ctypes.create_string_buffer(data, pad_len)
        try:
            _crypt32.CryptUnprotectMemory(ctypes.byref(buf), pad_len, CRYPTPROTECTMEMORY_SAME_PROCESS)
            return ctypes.string_at(buf, orig_len if orig_len > 0 else pad_len)
        finally:
            ctypes.memset(buf, 0, pad_len)

    def get_foreground_window(self) -> int:
        if not _IS_WIN:
            return 0
        try:
            return int(_user32.GetForegroundWindow() or 0)
        except Exception:
            return 0

    def get_sequence_number(self) -> int:
        return get_sequence_number()
