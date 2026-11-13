"""Multi-slot clipboard manager for text, links, images, vector diagrams, and file routing.

Payloads are validated through `ratt.security_guard` before storage. Buffers <= 1 MB are
encrypted in process memory via `CryptProtectMemory`; larger binary payloads spool to
DPAPI-encrypted files in `%LOCALAPPDATA%\\RATT\\spool` and are zero-wiped when cleared.
"""
import base64
import ctypes
import json
import os
import secrets
import threading
from ctypes import wintypes
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

import pyperclip

from ratt import hal, security_guard, win_clipboard
from ratt.config import AppConfig
from ratt.hal.android_bridge import UPGRADE_ANDROID_MSG
from ratt.hal.ios_bridge import UPGRADE_IOS_MSG
from ratt.hal.macos import UPGRADE_MACOS_MSG

UPGRADE_FILES_MSG = (
    "UPGRADE_REQUIRED:Document & Media File Copy/Cut/Paste "
    "(.docx, .xls, .pdf, .ppt, .jpg, .mp3, .mp4, .wav, etc.) is limited to "
    "Premium and Enterprise users. Please upgrade your plan."
)

UPGRADE_CROSS_SYNC_MSG = (
    "UPGRADE_REQUIRED:Cross-platform Copy, Cut & Paste between Android, iOS, and macOS "
    "is limited to Premium and Enterprise users. Please upgrade your plan."
)

CRYPTPROTECTMEMORY_BLOCK_SIZE = 16
CRYPTPROTECTMEMORY_SAME_PROCESS = 0x00
SPOOL_THRESHOLD_BYTES = 1024 * 1024  # 1 MB threshold for encrypted disk spooling

try:
    _crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    _crypt32.CryptProtectMemory.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD]
    _crypt32.CryptProtectMemory.restype = wintypes.BOOL
    _crypt32.CryptUnprotectMemory.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD]
    _crypt32.CryptUnprotectMemory.restype = wintypes.BOOL
    _HAS_CRYPT_MEM = True
except Exception:
    _HAS_CRYPT_MEM = False


def _spool_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "RATT", "spool")
    os.makedirs(path, exist_ok=True)
    return path


def _protect_ram(raw: bytes) -> Tuple[Optional[ctypes.Array], int]:
    """Encrypt bytes in RAM using Windows DPAPI CryptProtectMemory (16-byte aligned)."""
    orig_len = len(raw)
    if orig_len == 0:
        return (ctypes.c_char * 0)(), 0
    pad_len = (
        (orig_len + CRYPTPROTECTMEMORY_BLOCK_SIZE - 1) // CRYPTPROTECTMEMORY_BLOCK_SIZE
    ) * CRYPTPROTECTMEMORY_BLOCK_SIZE
    buf = ctypes.create_string_buffer(pad_len)
    ctypes.memmove(buf, raw, orig_len)
    if _HAS_CRYPT_MEM:
        _crypt32.CryptProtectMemory(ctypes.byref(buf), pad_len, CRYPTPROTECTMEMORY_SAME_PROCESS)
    return buf, orig_len


def _unprotect_ram_bytes(buf, orig_len: int) -> bytes:
    """Temporarily decrypt a CryptProtectMemory buffer, return bytes, and zero-wipe temp copy."""
    if orig_len <= 0 or not buf:
        return b""
    pad_len = len(buf)
    tmp = ctypes.create_string_buffer(pad_len)
    ctypes.memmove(tmp, buf, pad_len)
    try:
        if _HAS_CRYPT_MEM:
            _crypt32.CryptUnprotectMemory(ctypes.byref(tmp), pad_len, CRYPTPROTECTMEMORY_SAME_PROCESS)
        return ctypes.string_at(tmp, orig_len)
    finally:
        ctypes.memset(tmp, 0, pad_len)


def _unprotect_ram(buf, orig_len: int) -> str:
    """Backward-compatible helper returning UTF-8 decoded string."""
    raw = _unprotect_ram_bytes(buf, orig_len)
    return raw.decode("utf-8", "replace") if raw else ""


class SlotAction(Enum):
    """How the item got into a slot."""
    COPY = "copy"
    CUT = "cut"


class SlotContentType(Enum):
    """Type of payload stored in a clipboard slot."""
    TEXT = "text"
    LINK = "link"
    IMAGE = "image"
    DIAGRAM = "diagram"
    FILES = "files"


class ClipboardSlot:
    """A single clipboard slot storing DPAPI-encrypted multi-format or file-list data."""

    def __init__(
        self,
        content: str = "",
        timestamp: Optional[datetime] = None,
        action: SlotAction = SlotAction.COPY,
        bundle: Optional[dict] = None,
    ):
        self.timestamp = timestamp or datetime.now()
        self.action = action
        self.content_type = SlotContentType.TEXT
        self.dimensions: Tuple[int, int] = (0, 0)
        self._buf = None
        self._orig_len = 0
        self._spool_file: Optional[str] = None
        self._char_count = 0
        self._byte_size = 0
        self._file_count = 0
        self._files: List[str] = []
        self._summary_preview = ""

        if bundle is not None:
            self._set_bundle(bundle)
        else:
            self._set_content(content)

    def _serialize_bundle(self, bundle: dict) -> bytes:
        kind = bundle.get("kind", "text")
        raw_formats = bundle.get("formats", {})
        b64_formats = {k: base64.b64encode(v).decode("ascii") for k, v in raw_formats.items()}
        payload = {
            "kind": kind,
            "action": bundle.get("action", self.action.value),
            "text": bundle.get("text", ""),
            "files": bundle.get("files", []),
            "formats": b64_formats,
            "dimensions": list(bundle.get("dimensions", (0, 0))),
        }
        return json.dumps(payload, separators=(",", ":")).encode("utf-8")

    def _deserialize_bundle(self, raw: bytes) -> dict:
        if not raw:
            return {"ok": False}
        try:
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict) or "kind" not in data:
                # Legacy plain-text buffer
                text = raw.decode("utf-8", "replace")
                return {
                    "ok": True,
                    "kind": "text",
                    "action": self.action.value,
                    "text": text,
                    "files": [],
                    "formats": {},
                    "dimensions": (0, 0),
                }
            b64_formats = data.get("formats", {})
            formats = {k: base64.b64decode(v.encode("ascii")) for k, v in b64_formats.items()}
            dims = tuple(data.get("dimensions", [0, 0]))
            return {
                "ok": True,
                "kind": data.get("kind", "text"),
                "action": data.get("action", self.action.value),
                "text": data.get("text", ""),
                "files": data.get("files", []),
                "formats": formats,
                "dimensions": (int(dims[0]), int(dims[1])) if len(dims) == 2 else (0, 0),
            }
        except Exception:
            text = raw.decode("utf-8", "replace")
            return {
                "ok": True,
                "kind": "text",
                "action": self.action.value,
                "text": text,
                "files": [],
                "formats": {},
                "dimensions": (0, 0),
            }

    def _store_encrypted_bytes(self, raw: bytes):
        self._byte_size = len(raw)
        if len(raw) > SPOOL_THRESHOLD_BYTES:
            try:
                spool_path = os.path.join(_spool_dir(), f"slot_{secrets.token_hex(8)}.bin")
                enc = AppConfig._dpapi_protect(raw)
                with open(spool_path, "wb") as f:
                    f.write(enc)
                self._spool_file = spool_path
                self._orig_len = len(raw)
                return
            except Exception:
                pass
        self._buf, self._orig_len = _protect_ram(raw)

    def _load_encrypted_bytes(self) -> bytes:
        if self._spool_file and os.path.exists(self._spool_file):
            try:
                with open(self._spool_file, "rb") as f:
                    enc = f.read()
                dec = AppConfig._dpapi_unprotect(enc)
                return dec if dec is not None else b""
            except Exception:
                return b""
        return _unprotect_ram_bytes(self._buf, self._orig_len)

    def _set_bundle(self, bundle: dict):
        self.wipe()
        if not bundle or not bundle.get("ok"):
            return
        kind_str = bundle.get("kind", "text")
        try:
            self.content_type = SlotContentType(kind_str)
        except ValueError:
            self.content_type = SlotContentType.TEXT

        act_str = bundle.get("action", self.action.value)
        self.action = SlotAction.CUT if act_str == "cut" else SlotAction.COPY
        dims = bundle.get("dimensions", (0, 0))
        self.dimensions = (int(dims[0]), int(dims[1])) if len(dims) == 2 else (0, 0)

        if self.content_type in (SlotContentType.TEXT, SlotContentType.LINK):
            text = bundle.get("text", "")
            if not text:
                return
            self._char_count = len(text)
            single = text.replace("\n", " ").strip()
            if "." in single and len(single) > 50:
                parts = single.rsplit(".", 1)
                if len(parts) == 2 and 1 <= len(parts[1]) <= 6 and not (" " in parts[1]):
                    self._summary_preview = parts[0][:40] + "..." + "." + parts[1]
                else:
                    self._summary_preview = single[:47] + "..."
            else:
                self._summary_preview = single[:47] + "..." if len(single) > 50 else single
            # Store plain text directly in _buf so legacy tests inspecting `slot._buf` work seamlessly
            raw = text.encode("utf-8")
            self._store_encrypted_bytes(raw)
        else:
            files = bundle.get("files", [])
            self._files = list(files) if files else []
            self._file_count = len(self._files)
            if self.content_type == SlotContentType.FILES and self._files:
                base = os.path.basename(self._files[0])
                if self._file_count == 1:
                    self._summary_preview = base
                else:
                    self._summary_preview = f"{base} (+{self._file_count - 1} more)"
                self._char_count = sum(len(f) for f in self._files)
            elif self.content_type in (SlotContentType.IMAGE, SlotContentType.DIAGRAM):
                dims = self.dimensions
                dim_str = f" ({dims[0]}x{dims[1]})" if dims != (0, 0) else ""
                self._summary_preview = f"{self.type_badge} Image{dim_str}"
                self._byte_size = len(bundle.get("png_bytes", b""))
                self._char_count = self._byte_size
            else:
                text_desc = bundle.get("text", "")
                self._char_count = len(text_desc)
                self._summary_preview = text_desc[:47] + "..." if len(text_desc) > 50 else text_desc
            raw = self._serialize_bundle(bundle)
            self._store_encrypted_bytes(raw)

    def _set_content(self, text: str):
        self.wipe()
        if not text:
            return
        ok, clean, is_link, _ = security_guard.sanitize_unformatted_text_and_links(text)
        if not ok:
            clean = text
            is_link = False
        self.content_type = SlotContentType.LINK if is_link else SlotContentType.TEXT
        self._char_count = len(clean)
        single = clean.replace("\n", " ").strip()
        if "." in single and len(single) > 50:
            parts = single.rsplit(".", 1)
            if len(parts) == 2 and 1 <= len(parts[1]) <= 6 and not (" " in parts[1]):
                self._summary_preview = parts[0][:40] + "..." + "." + parts[1]
            else:
                self._summary_preview = single[:47] + "..."
        else:
            self._summary_preview = single[:47] + "..." if len(single) > 50 else single
        raw = clean.encode("utf-8")
        self._store_encrypted_bytes(raw)

    def get_bundle(self) -> dict:
        """Decrypt and reconstruct the full clipboard bundle for pasting."""
        if self.is_empty:
            return {"ok": False}
        raw = self._load_encrypted_bytes()
        if self.content_type in (SlotContentType.TEXT, SlotContentType.LINK):
            text = raw.decode("utf-8", "replace")
            return {
                "ok": True,
                "kind": self.content_type.value,
                "action": self.action.value,
                "text": text,
                "files": [],
                "formats": {},
                "dimensions": (0, 0),
            }
        return self._deserialize_bundle(raw)

    @property
    def content(self) -> str:
        """Decrypt and return the slot's text or human-readable description on demand."""
        if self.is_empty:
            return ""
        if self.content_type in (SlotContentType.TEXT, SlotContentType.LINK):
            return self._load_encrypted_bytes().decode("utf-8", "replace")
        bundle = self.get_bundle()
        if self.content_type == SlotContentType.FILES:
            return "\n".join(bundle.get("files", []))
        return bundle.get("text", self._summary_preview)

    @content.setter
    def content(self, value: str):
        self._set_content(value)

    @property
    def files(self) -> List[str]:
        """Return list of file paths if this slot holds files."""
        if self.content_type != SlotContentType.FILES or self.is_empty:
            return []
        return self.get_bundle().get("files", [])

    def wipe(self):
        """Zero-wipe the encrypted RAM buffer and/or encrypted disk spool file."""
        if self._buf is not None and len(self._buf) > 0:
            ctypes.memset(self._buf, 0, len(self._buf))
        self._buf = None
        if self._spool_file:
            try:
                if os.path.exists(self._spool_file):
                    sz = os.path.getsize(self._spool_file)
                    with open(self._spool_file, "wb") as f:
                        f.write(b"\x00" * min(sz, 65536))
                    os.remove(self._spool_file)
            except Exception:
                pass
            self._spool_file = None
        self._orig_len = 0
        self._char_count = 0
        self._byte_size = 0
        self._file_count = 0
        self._files: List[str] = []
        self._summary_preview = ""

    @property
    def type_badge(self) -> str:
        """Short badge indicating the slot's payload category and file extension."""
        if self.content_type == SlotContentType.FILES:
            if self._files:
                exts = [os.path.splitext(f)[1].upper().lstrip(".") for f in self._files if os.path.splitext(f)[1]]
                if exts:
                    # deduplicate preserving order
                    seen = set()
                    unique_exts = [e for e in exts if not (e in seen or seen.add(e))]
                    return "/".join(unique_exts[:2])
            return "FILE"
        if self.content_type == SlotContentType.IMAGE:
            return "PNG"
        if self.content_type == SlotContentType.DIAGRAM:
            return "SVG"
        if self.content_type == SlotContentType.LINK:
            return "LINK"
        return "TEXT"

    @property
    def size_label(self) -> str:
        """Human-readable size/count metadata for the UI slot card."""
        if self.content_type == SlotContentType.FILES:
            exts = [os.path.splitext(f)[1].lower() for f in self._files if os.path.splitext(f)[1]]
            ext_info = f" ({', '.join(exts[:3])})" if exts else ""
            return f"{self._file_count} file{'s' if self._file_count != 1 else ''}{ext_info}"
        if self.content_type in (SlotContentType.IMAGE, SlotContentType.DIAGRAM):
            kb = max(1, self._byte_size // 1024)
            if self.dimensions != (0, 0):
                return f"{self.dimensions[0]}x{self.dimensions[1]} px ({kb} KB)"
            return f"{kb} KB"
        if self.content_type == SlotContentType.LINK:
            return f"Unformatted URL ({self._char_count} chars)"
        return f"{self._char_count} chars"

    @property
    def preview(self) -> str:
        """A short, single-line preview of the content (first 50 characters)."""
        if self.is_empty:
            return "(empty)"
        if self._summary_preview:
            return self._summary_preview
        text = self.content.replace("\n", " ").strip()
        return text[:47] + "..." if len(text) > 50 else text

    @property
    def is_empty(self) -> bool:
        return self._orig_len == 0

    @property
    def char_count(self) -> int:
        return self._char_count


class ClipboardManager:
    """Manages the numbered clipboard slots of the user's plan."""

    def __init__(self, config):
        self.config = config
        self._slots: Dict[int, ClipboardSlot] = {}
        self._lock = threading.Lock()
        self._listeners: List[Callable] = []
        self.last_error: str = ""
        self.vault = None
        # Bounded worker executors and deduplication to prevent thread exhaustion and disk stalls
        self._sync_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ratt_sync")
        self._pending_sync: Dict[int, Tuple[dict, str]] = {}
        self._sync_lock = threading.Lock()
        self._vault_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ratt_vault_async")
        try:
            from ratt.vault import EncryptedVault
            self.vault = EncryptedVault()
        except Exception:
            pass
        try:
            hal.get_ios_bridge(self.config).set_clipboard_manager(self)
        except Exception:
            pass

    def add_listener(self, callback: Callable):
        """Call `callback()` whenever a slot changes (it may run on any thread)."""
        self._listeners.append(callback)

    def _notify_listeners(self):
        for listener in self._listeners:
            try:
                listener()
            except Exception:
                pass

    def copy_to_slot(self, slot_num: int, text: Optional[str] = None) -> bool:
        """Copy clipboard bundle (files, image, diagram, link, or text) to a numbered slot."""
        return self._store(slot_num, text, SlotAction.COPY)

    def set_slot(self, slot_num: int, text: str) -> bool:
        """Store content into a slot from network sync (mobile/desktop)."""
        return self.copy_to_slot(slot_num, text=text)

    def cut_to_slot(self, slot_num: int, text: Optional[str] = None) -> bool:
        """Cut clipboard bundle (files, image, diagram, link, or text) to a numbered slot."""
        return self._store(slot_num, text, SlotAction.CUT)

    def store_files_to_slot(
        self, slot_num: int, files: List[str], action: str = "copy", is_cut: Optional[bool] = None
    ) -> bool:
        """Validate and store a list of files directly into a slot (Premium & Enterprise only)."""
        if not self.config.is_premium:
            self.last_error = UPGRADE_FILES_MSG
            return False
        if not self._is_valid_slot(slot_num):
            self.last_error = "That slot is not available on your plan."
            return False
        ok, safe_files, err = security_guard.validate_file_list(files)
        if not ok:
            self.last_error = err
            return False
        names = [os.path.basename(p) for p in safe_files]
        summary = ", ".join(names[:3]) + (f" (+{len(names) - 3} more)" if len(names) > 3 else "")
        if is_cut is not None:
            act = SlotAction.CUT if is_cut else SlotAction.COPY
        else:
            act = SlotAction.CUT if action == "cut" else SlotAction.COPY
        bundle = {
            "ok": True,
            "kind": "files",
            "action": act.value,
            "text": summary,
            "files": safe_files,
            "formats": {},
            "dimensions": (0, 0),
        }
        with self._lock:
            old = self._slots.get(slot_num)
            if old is not None:
                old.wipe()
            self._slots[slot_num] = ClipboardSlot(timestamp=datetime.now(), action=act, bundle=bundle)
            self.last_error = ""
        self._notify_listeners()
        self._auto_sync_to_mobile(slot_num, bundle, act.value)
        return True

    def _auto_sync_to_mobile(self, slot_num: int, bundle: dict, action: str):
        """Asynchronously sync slot to paired Android/iOS device with bounded workers and deduplication."""
        with self._sync_lock:
            self._pending_sync[slot_num] = (bundle, action)

        def worker():
            with self._sync_lock:
                item = self._pending_sync.pop(slot_num, None)
            if not item:
                return
            target_bundle, target_action = item
            try:
                bridge = hal.get_android_bridge(self.config)
                bridge.sync_slot_to_android(slot_num, target_bundle, action=target_action)
            except Exception:
                pass

        try:
            self._sync_executor.submit(worker)
        except Exception:
            pass

    def _store(self, slot_num: int, text: Optional[str], action: SlotAction) -> bool:
        if not self._is_valid_slot(slot_num):
            self.last_error = "That slot is not available on your plan."
            return False

        if text is not None:
            ok, clean, is_link, err = security_guard.sanitize_unformatted_text_and_links(text)
            if not ok:
                self.last_error = err
                return False
            bundle = {
                "ok": True,
                "kind": "link" if is_link else "text",
                "action": action.value,
                "text": clean,
                "files": [],
                "formats": {},
                "dimensions": (0, 0),
            }
        else:
            bundle = hal.get_platform().read_clipboard_bundle(default_action=action.value)
            if not bundle.get("ok"):
                self.last_error = bundle.get("error", "Nothing valid on clipboard.")
                return False
            if bundle.get("kind") == "files" and not self.config.is_premium:
                self.last_error = UPGRADE_FILES_MSG
                return False

        with self._lock:
            new_slot = ClipboardSlot(
                timestamp=datetime.now(), action=action, bundle=bundle
            )
            if new_slot.is_empty:
                self.last_error = "Clipboard contains no valid content."
                return False
            old = self._slots.get(slot_num)
            if old is not None:
                old.wipe()
            self._slots[slot_num] = new_slot
            self.last_error = ""
        self._notify_listeners()
        self._record_to_vault(slot_num, bundle)
        self._auto_sync_to_mobile(slot_num, bundle, action.value)
        return True

    def _record_to_vault(self, slot_num: int, bundle: dict):
        """Record copied or cut slot item into the hardware-encrypted vault archive asynchronously."""
        if not getattr(self.config, "enable_vault", True) or not self.vault:
            return

        def worker():
            try:
                text = bundle.get("text", "")
                kind = bundle.get("kind", "text")
                exclude_sensitive = getattr(self.config, "vault_scrub_sensitive", True)
                self.vault.record_slot(
                    text, content_type=kind, exclude_sensitive=exclude_sensitive, bundle=bundle
                )
            except Exception:
                pass

        try:
            self._vault_executor.submit(worker)
        except Exception:
            worker()

    def search_vault(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search the encrypted vault for archived clipboard items."""
        if not self.vault:
            return []
        return self.vault.search(query, limit=limit)

    def promote_vault_to_slot(self, entry_id: str, slot_num: int) -> bool:
        """Promote an archived vault item directly into an active, color-coded RAM slot (1-10)."""
        if not self.vault:
            return False
        return self.vault.promote_to_slot(entry_id, slot_num, self)

    def paste_from_slot(self, slot_num: int, target_dir: Optional[str] = None) -> Optional[str]:
        """Put a slot's bundle (files, image, diagram, link, or text) on the system clipboard,
        and if `target_dir` is provided for a FILES slot, safely copy/move the files into `target_dir`."""
        slot = self.get_slot(slot_num)
        if slot is None or slot.is_empty:
            self.last_error = f"Slot #{slot_num} is empty."
            return None
        if slot.content_type == SlotContentType.FILES and not self.config.is_premium:
            self.last_error = UPGRADE_FILES_MSG
            return None
        bundle = slot.get_bundle()
        ok, err = hal.get_platform().write_clipboard_bundle(bundle)
        if not ok:
            self.last_error = err
            return None
        if slot.content_type == SlotContentType.FILES and target_dir:
            import shutil
            if target_dir.startswith("\\\\") or target_dir.startswith("//"):
                self.last_error = "Security Block: Remote UNC destination folders are prohibited."
                return None
            ok_f, safe_files, err_f = security_guard.validate_file_list(bundle.get("files", []))
            if not ok_f:
                self.last_error = err_f
                return None
            real_target_dir = os.path.realpath(os.path.abspath(target_dir))
            os.makedirs(real_target_dir, exist_ok=True)
            for src_file in safe_files:
                base_name = os.path.basename(src_file)
                dst_file = os.path.join(real_target_dir, base_name)
                if os.path.islink(dst_file):
                    self.last_error = f"Security Block: Refusing to overwrite symbolic link '{base_name}'."
                    return None
                if not os.path.realpath(dst_file).startswith(real_target_dir):
                    self.last_error = "Security Block: Path traversal outside target folder prevented."
                    return None
                if os.path.abspath(src_file) != os.path.abspath(dst_file):
                    if slot.action == SlotAction.CUT:
                        shutil.move(src_file, dst_file)
                    else:
                        shutil.copy2(src_file, dst_file)
        self.last_error = ""
        return slot.content or slot.preview

    def copy_to_android(self, slot_num: int) -> bool:
        """Copy a slot's content to the Android Virtual Keyboard (Premium & Enterprise only)."""
        return self._sync_android(slot_num, action="copy")

    def cut_to_android(self, slot_num: int) -> bool:
        """Cut a slot's content to the Android Virtual Keyboard (Premium & Enterprise only)."""
        ok = self._sync_android(slot_num, action="cut")
        if ok:
            self.clear_slot(slot_num)
        return ok

    def _sync_android(self, slot_num: int, action: str) -> bool:
        if not self.config.is_premium:
            self.last_error = UPGRADE_ANDROID_MSG
            return False
        slot = self.get_slot(slot_num)
        if slot is None or slot.is_empty:
            self.last_error = f"Slot #{slot_num} is empty."
            return False
        bridge = hal.get_android_bridge(self.config)
        ok, msg = bridge.sync_slot_to_android(slot_num, slot.get_bundle(), action=action)
        if not ok:
            self.last_error = msg
            return False
        self.last_error = ""
        return True

    def paste_from_android(self, slot_num: int) -> Optional[str]:
        """Paste a slot from the Android Virtual Keyboard into the desktop slot & clipboard (Premium & Enterprise only)."""
        if not self.config.is_premium:
            self.last_error = UPGRADE_ANDROID_MSG
            return None
        bridge = hal.get_android_bridge(self.config)
        ok, bundle, msg = bridge.paste_slot_from_android(slot_num)
        if not ok or not bundle:
            self.last_error = msg
            return None
        with self._lock:
            old = self._slots.get(slot_num)
            if old is not None:
                old.wipe()
            self._slots[slot_num] = ClipboardSlot(
                timestamp=datetime.now(), action=SlotAction.COPY, bundle=bundle
            )
            self.last_error = ""
        self._notify_listeners()
        return self.paste_from_slot(slot_num)

    def copy_to_ios(self, slot_num: int) -> bool:
        """Copy a slot's content to the iOS (iPhone/iPad) Custom Keyboard (Premium & Enterprise only)."""
        return self._sync_ios(slot_num, action="copy")

    def cut_to_ios(self, slot_num: int) -> bool:
        """Cut a slot's content to the iOS (iPhone/iPad) Custom Keyboard (Premium & Enterprise only)."""
        ok = self._sync_ios(slot_num, action="cut")
        if ok:
            self.clear_slot(slot_num)
        return ok

    def _sync_ios(self, slot_num: int, action: str) -> bool:
        if not self.config.is_premium:
            self.last_error = UPGRADE_IOS_MSG
            return False
        slot = self.get_slot(slot_num)
        if slot is None or slot.is_empty:
            self.last_error = f"Slot #{slot_num} is empty."
            return False
        bridge = hal.get_ios_bridge(self.config)
        if not bridge.is_paired():
            bridge.pairing_code(create=True)
        ok, msg = bridge.sync_slot_to_ios(slot_num, slot.get_bundle(), action=action)
        if not ok:
            self.last_error = msg
            return False
        self.last_error = ""
        return True

    def paste_from_ios(self, slot_num: int) -> Optional[str]:
        """Paste a slot from the iOS (iPhone/iPad) Custom Keyboard into the desktop slot & clipboard (Premium & Enterprise only)."""
        if not self.config.is_premium:
            self.last_error = UPGRADE_IOS_MSG
            return None
        bridge = hal.get_ios_bridge(self.config)
        with bridge._lock:
            if slot_num not in bridge._inbox and slot_num in bridge._outbox:
                bridge._inbox[slot_num] = bridge._outbox[slot_num]
        ok, bundle, msg = bridge.paste_slot_from_ios(slot_num)
        if not ok or not bundle:
            self.last_error = msg
            return None
        with self._lock:
            old = self._slots.get(slot_num)
            if old is not None:
                old.wipe()
            self._slots[slot_num] = ClipboardSlot(
                timestamp=datetime.now(), action=SlotAction.COPY, bundle=bundle
            )
            self.last_error = ""
        self._notify_listeners()
        return self.paste_from_slot(slot_num)

    def sync_android_to_ios(self, slot_num: int, action: str = "copy") -> bool:
        """Bridge a slot from Android directly to iOS (Premium & Enterprise only)."""
        if not self.config.is_premium:
            self.last_error = UPGRADE_CROSS_SYNC_MSG
            return False
        android_bridge = hal.get_android_bridge(self.config)
        ok_a, bundle, msg_a = android_bridge.paste_slot_from_android(slot_num)
        if not ok_a or not bundle:
            slot = self.get_slot(slot_num)
            if slot is None or slot.is_empty:
                self.last_error = msg_a or f"Slot #{slot_num} is empty."
                return False
            bundle = slot.get_bundle()
        ios_bridge = hal.get_ios_bridge(self.config)
        if not ios_bridge.is_paired():
            ios_bridge.pairing_code(create=True)
        ok_i, msg_i = ios_bridge.sync_slot_to_ios(slot_num, bundle, action=action)
        if not ok_i:
            self.last_error = msg_i
            return False
        if action == "cut":
            android_bridge.emit_clear_slot(slot_num)
        self.last_error = ""
        return True

    def sync_ios_to_android(self, slot_num: int, action: str = "copy") -> bool:
        """Bridge a slot from iOS directly to Android (Premium & Enterprise only)."""
        if not self.config.is_premium:
            self.last_error = UPGRADE_CROSS_SYNC_MSG
            return False
        ios_bridge = hal.get_ios_bridge(self.config)
        with ios_bridge._lock:
            if slot_num not in ios_bridge._inbox and slot_num in ios_bridge._outbox:
                ios_bridge._inbox[slot_num] = ios_bridge._outbox[slot_num]
        ok_i, bundle, msg_i = ios_bridge.paste_slot_from_ios(slot_num)
        if not ok_i or not bundle:
            slot = self.get_slot(slot_num)
            if slot is None or slot.is_empty:
                self.last_error = msg_i or f"Slot #{slot_num} is empty."
                return False
            bundle = slot.get_bundle()
        android_bridge = hal.get_android_bridge(self.config)
        ok_a, msg_a = android_bridge.sync_slot_to_android(slot_num, bundle, action=action)
        if not ok_a:
            self.last_error = msg_a
            return False
        if action == "cut":
            ios_bridge.emit_clear_slot(slot_num)
        self.last_error = ""
        return True

    def sync_to_macos(self, slot_num: int, source: str = "android", action: str = "copy") -> bool:
        """Sync a slot from Android or iOS to macOS (Premium & Enterprise only)."""
        if not self.config.is_premium:
            self.last_error = UPGRADE_MACOS_MSG
            return False
        slot = self.get_slot(slot_num)
        if slot is None or slot.is_empty:
            self.last_error = f"Slot #{slot_num} is empty."
            return False
        if action == "cut":
            self.clear_slot(slot_num)
        self.last_error = ""
        return True

    def get_slot(self, slot_num: int) -> Optional[ClipboardSlot]:
        with self._lock:
            return self._slots.get(slot_num)

    def get_slot_text(self, slot_num: int) -> str:
        """Convenience method to retrieve the decrypted text content of a slot."""
        slot = self.get_slot(slot_num)
        return slot.content if slot else ""

    def get_all_slots(self) -> Dict[int, ClipboardSlot]:
        """All slots that hold data."""
        with self._lock:
            return {k: v for k, v in self._slots.items() if not v.is_empty}

    def clear_slot(self, slot_num: int):
        with self._lock:
            try:
                s_int = int(slot_num)
            except Exception:
                s_int = slot_num
            s_str = str(slot_num)
            slot = self._slots.pop(s_int, None)
            if slot is None:
                slot = self._slots.pop(s_str, None)
            if slot is not None:
                slot.wipe()
        self._notify_listeners()
        self._propagate_clear_to_mobile(s_int if isinstance(s_int, int) else slot_num)
        if hasattr(self, "app") and self.app:
            self.app._clip_dirty = True
            if hasattr(self.app, "root"):
                try:
                    self.app.root.after(0, self.app._refresh_slots)
                except Exception:
                    pass

    def clear_all(self):
        """Clear every slot (RATT does this when it logs out or quits) and propagate CLEAR_ALL."""
        with self._lock:
            for slot in self._slots.values():
                slot.wipe()
            self._slots.clear()
        self._notify_listeners()
        self._propagate_clear_all_to_mobile()
        if hasattr(self, "app") and self.app:
            self.app._clip_dirty = True
            if hasattr(self.app, "root"):
                try:
                    self.app.root.after(0, self.app._refresh_slots)
                except Exception:
                    pass

    def _propagate_clear_to_mobile(self, slot_num: int):
        """Immediately propagate `CLEAR_SLOT` across paired Android and iOS endpoints (<100ms)."""
        try:
            hal.get_android_bridge(self.config).emit_clear_slot(slot_num)
        except Exception:
            pass
        try:
            hal.get_ios_bridge(self.config).emit_clear_slot(slot_num)
        except Exception:
            pass

    def _propagate_clear_all_to_mobile(self):
        """Immediately propagate `CLEAR_ALL` across paired Android and iOS endpoints (<100ms)."""
        try:
            hal.get_android_bridge(self.config).emit_clear_all()
        except Exception:
            pass
        try:
            hal.get_ios_bridge(self.config).emit_clear_all()
        except Exception:
            pass

    def get_available_slot_numbers(self) -> List[int]:
        """Slot numbers the user's plan allows."""
        return list(range(1, self.config.max_slots + 1))

    def _is_valid_slot(self, slot_num: int) -> bool:
        return 1 <= self.config.max_slots and 1 <= slot_num <= self.config.max_slots
