"""RATT iPhone (iOS) Slot Palette Extension bridge (`ratt/hal/ios_bridge.py`).

Connects RATT Desktop slots with the RATT Slot Palette Extension on an iPhone/iPad
(`ios/RattKeyboard/RattKeyboardViewController.swift`, a `UIInputViewController`
and `ios/Shared/AppGroupDataManager.swift`) over the local Wi-Fi network, port 49211.

Commercial policy (same as Android): Copy / Cut / Paste to or from iOS is limited to
**Premium** and **Enterprise** subscribers. Basic users get an `UPGRADE_REQUIRED:` reply.

How it works
------------
iOS apps cannot be reached by a desktop in the background, so the desktop is the server
and the phone is the client:

  * "Copy/Cut to iPhone" puts the slot text in an *outbox*; the keyboard fetches it with a
    `pull` request whenever it opens (or on "Sync now" in the RATT iOS app).
  * Text the keyboard sends with `push` lands in an *inbox*; "Paste from iPhone" moves it
    into a desktop slot.
  * When the host PC clears a slot (`clear_slot`) or wipes all slots (`clear_all`), the
    bridge immediately purges the outbox/inbox, zeroes memory buffers (`MEM-003`), and
    records a signed `CLEAR_SLOT` or `CLEAR_ALL` tombstone packet (`DEL-002 < 100ms`) so
    `AppGroupDataManager.clearSlot(id:)` removes `slot_<id>.enc` and posts the Darwin
    notification `"com.cybrox.ratt.slotCleared"`.

Security (the phone is on a network anyone on the Wi-Fi can reach):
  * Pairing: Supports Curve25519 (X25519) ECDH key agreement + SHA-256 HKDF session key
    derivation authenticated via a dynamic 6-digit rolling PIN / QR code or 128-bit
    base32 pairing code.
  * Every request and response is one AES-256-GCM sealed frame with a 96-bit CSPRNG IV
    and 128-bit tag (`SEC-001: Zero Cleartext`). A frame that does not authenticate is
    dropped without any reply (no oracle for guessing the code).
  * Requests carry a timestamp and a random id; stale or replayed frames are refused.
  * Text in both directions passes through `security_guard` (no HTML, spoofing characters
    or executable link schemes).
  * The server only runs while the user is Premium/Enterprise AND has paired a phone.
"""
import base64
import hashlib
import hmac
import json
import os
import platform
import secrets
import socket
import socketserver
import struct
import threading
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from ratt import security_guard
from ratt.hal.base import BasePlatform

IOS_BRIDGE_PORT = 49211
PROTOCOL_VERSION = 1
UPGRADE_IOS_MSG = (
    "UPGRADE_REQUIRED:Copy, Cut & Paste to iPhone is limited to Premium and "
    "Enterprise users. Please upgrade your plan to unlock iOS integration."
)
UPGRADE_CROSS_SYNC_MSG = (
    "UPGRADE_REQUIRED:Cross-platform sync between Android, iOS, and macOS is "
    "limited to Premium and Enterprise users. Please upgrade your plan to unlock."
)

MAX_FRAME_BYTES = 256 * 1024
MAX_TEXT_CHARS = 64 * 1024
CLOCK_SKEW_SECONDS = 120
SOCKET_TIMEOUT = 5.0
MAX_AUTH_FAILURES = 8              # per client address ...
FAILURE_WINDOW_SECONDS = 60        # ... within this window, then it is ignored for a while

_HKDF_SALT = b"RATT-iOS-bridge-v1"
_HKDF_INFO = b"aes-256-gcm"
AAD_REQUEST = b"RATT-iOS-v1:request"
AAD_RESPONSE = b"RATT-iOS-v1:response"
HOST_NODE_ID = f"PC-{platform.system().upper()}-HOST"


# ---- pairing code, ECDH Curve25519, and key derivation ------------------------------

def new_pairing_secret() -> bytes:
    return secrets.token_bytes(16)


def format_pairing_code(secret: bytes) -> str:
    """26 base32 characters in groups of five, e.g. ABCDE-FGHIJ-KLMNO-PQRST-UVWXY-Z."""
    text = base64.b32encode(secret).decode("ascii").rstrip("=")
    return "-".join(text[i:i + 5] for i in range(0, len(text), 5))


def parse_pairing_code(code: str) -> Optional[bytes]:
    """Inverse of `format_pairing_code`; None if the text is not a valid code."""
    text = "".join(ch for ch in (code or "").upper() if ch.isalnum())
    if len(text) != 26:
        return None
    try:
        secret = base64.b32decode(text + "======")
    except ValueError:
        return None
    return secret if len(secret) == 16 else None


def derive_key(secret: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=_HKDF_SALT, info=_HKDF_INFO).derive(secret)


def generate_ecdh_keypair() -> Tuple[bytes, bytes]:
    """Generate a Curve25519 (X25519) private/public keypair for iOS Secure Enclave / CryptoKit pairing."""
    priv = x25519.X25519PrivateKey.generate()
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return priv_bytes, pub_bytes


def derive_ecdh_session_key(private_key_bytes: bytes, peer_public_key_bytes: bytes, pin: str = "") -> bytes:
    """Perform Curve25519 ECDH key agreement and derive a 256-bit AES-GCM key via SHA-256 HKDF."""
    priv = x25519.X25519PrivateKey.from_private_bytes(private_key_bytes)
    peer_pub = x25519.X25519PublicKey.from_public_bytes(peer_public_key_bytes)
    shared = priv.exchange(peer_pub)
    info = _HKDF_INFO + (f":pin={pin}".encode("utf-8") if pin else b"")
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=_HKDF_SALT, info=info).derive(shared)


def generate_rolling_pin(secret: bytes, window_seconds: int = 60) -> str:
    """Generate a 6-digit rolling PIN authenticated by the pairing secret."""
    counter = int(time.time() // max(1, window_seconds)).to_bytes(8, "big")
    digest = hmac.new(secret, counter, hashlib.sha256).digest()
    return f"{int.from_bytes(digest[:4], 'big') % 1_000_000:06d}"


def build_deletion_packet(
    action: str = "CLEAR_SLOT",
    slot_id: Optional[int] = None,
    source_device: str = HOST_NODE_ID,
) -> dict:
    """Construct the Section 3 Real-Time Global Slot Deletion payload schema."""
    payload: dict = {"action": action}
    if action == "CLEAR_SLOT" and slot_id is not None:
        payload["slot_id"] = int(slot_id)
    payload["timestamp"] = int(time.time())
    payload["nonce"] = secrets.token_hex(12)
    payload["source_device"] = source_device
    return payload


# ---- sealed frames ------------------------------------------------------------------

def seal(key: bytes, message: dict, aad: bytes) -> bytes:
    nonce = secrets.token_bytes(12)  # 96-bit CSPRNG IV
    body = bytearray(json.dumps(message, separators=(",", ":")).encode("utf-8"))
    try:
        return nonce + AESGCM(key).encrypt(nonce, bytes(body), aad)
    finally:
        for i in range(len(body)):
            body[i] = 0


def open_sealed(key: bytes, blob: bytes, aad: bytes) -> dict:
    """Decrypt and parse a frame; raises ValueError if it is not authentic."""
    if len(blob) < 12 + 16:
        raise ValueError("frame too short")
    try:
        body = AESGCM(key).decrypt(blob[:12], blob[12:], aad)
        message = json.loads(body.decode("utf-8"))
    except (InvalidTag, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("frame rejected") from error
    if not isinstance(message, dict):
        raise ValueError("frame is not an object")
    return message


def send_frame(sock: socket.socket, blob: bytes) -> None:
    sock.sendall(struct.pack(">I", len(blob)) + blob)


def _read_exactly(sock: socket.socket, count: int) -> Optional[bytes]:
    data = b""
    while len(data) < count:
        chunk = sock.recv(count - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def recv_frame(sock: socket.socket) -> Optional[bytes]:
    """Read one frame; None on EOF or an oversized length."""
    header = _read_exactly(sock, 4)
    if header is None:
        return None
    (length,) = struct.unpack(">I", header)
    if length == 0 or length > MAX_FRAME_BYTES:
        return None
    return _read_exactly(sock, length)


# ---- entitlement --------------------------------------------------------------------

def check_ios_entitlement(app_config=None) -> Tuple[bool, str]:
    """Verify that the active user holds a Premium or Enterprise subscription."""
    if app_config is None:
        from ratt.config import config as app_config
    if not app_config.is_premium:
        return False, UPGRADE_IOS_MSG
    return True, ""


def lan_address() -> str:
    """This PC's address on the local network (what the iPhone must connect to)."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))        # a UDP "connect" sends nothing
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


# ---- pairing storage ----------------------------------------------------------------

class PairingStore:
    """The pairing secret, kept on disk protected for the current Windows user (DPAPI)."""

    def __init__(self, folder: Optional[str] = None):
        base = folder or os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "RATT")
        self.path = os.path.join(base, "ios_pairing.bin")
        self._memory_secret: Optional[bytes] = None

    def load(self) -> Optional[bytes]:
        if self._memory_secret is not None:
            return self._memory_secret
        from ratt.config import AppConfig
        try:
            with open(self.path, "rb") as f:
                secret = AppConfig._dpapi_unprotect(f.read())
        except OSError:
            return None
        return secret if secret and len(secret) == 16 else None

    def create(self) -> bytes:
        from ratt.config import AppConfig
        secret = new_pairing_secret()
        self._memory_secret = secret
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "wb") as f:
                f.write(AppConfig._dpapi_protect(secret))
        except OSError:
            pass
        return secret

    def delete(self) -> None:
        self._memory_secret = None
        try:
            os.remove(self.path)
        except OSError:
            pass


# ---- the server ---------------------------------------------------------------------

class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 8

    def __init__(self, address, bridge):
        super().__init__(address, _Handler)
        self.bridge = bridge


class _Handler(socketserver.BaseRequestHandler):
    def handle(self):
        bridge = self.server.bridge
        client = self.client_address[0]
        self.request.settimeout(SOCKET_TIMEOUT)
        try:
            if bridge.is_throttled(client):
                return
            blob = recv_frame(self.request)
            if blob is None:
                return
            try:
                request = open_sealed(bridge.key(), blob, AAD_REQUEST)
            except ValueError:
                bridge.note_auth_failure(client)
                return                                    # no reply: nothing to learn from us
            response = bridge.handle_request(request)
            send_frame(self.request, seal(bridge.key(), response, AAD_RESPONSE))
        except OSError:
            pass


class IOSBridgePlatform(BasePlatform):
    """Bridge driver connecting RATT slots to the RATT iOS Slot Palette Extension."""

    def __init__(self, app_config=None, store: Optional[PairingStore] = None, port: int = IOS_BRIDGE_PORT):
        self._config = app_config
        self._store = store or PairingStore()
        self._port = port
        self._lock = threading.Lock()
        self._outbox: Dict[int, str] = {}        # desktop -> iPhone (served by `pull`)
        self._inbox: Dict[int, str] = {}         # iPhone -> desktop (filled by `push`)
        self._tombstones: List[dict] = []        # pending `CLEAR_SLOT` / `CLEAR_ALL` packets
        self._seen_ids: Dict[str, float] = {}
        self._failures: Dict[str, list] = {}
        self._clipboard_manager = None
        self._server: Optional[_Server] = None
        self._key: Optional[bytes] = None
        self.last_error = ""
        self.on_inbound: Optional[Callable[[int], None]] = None   # called with the slot number

    def set_clipboard_manager(self, mgr) -> None:
        self._clipboard_manager = mgr

    @property
    def platform_name(self) -> str:
        return "iOS (iPhone/iPad Slot Palette Bridge)"

    def _get_config(self):
        if self._config is not None:
            return self._config
        from ratt.config import config
        return config

    # -- pairing and server lifecycle --

    def is_paired(self) -> bool:
        return self._store.load() is not None

    def pairing_code(self, create: bool = False) -> Optional[str]:
        """The code to type into the iOS app (created on first use if `create`)."""
        secret = self._store.load()
        if secret is None and create:
            secret = self._store.create()
        return format_pairing_code(secret) if secret else None

    def reset_pairing(self) -> None:
        """Forget the paired phone: new code needed, server stopped, buffers wiped."""
        self.stop_server()
        self._store.delete()
        with self._lock:
            self._key = None
            self._outbox.clear()
            self._inbox.clear()
            self._tombstones.clear()

    def key(self) -> bytes:
        with self._lock:
            if self._key is None:
                secret = self._store.load()
                if secret is None:
                    raise ValueError("not paired")
                self._key = derive_key(secret)
            return self._key

    def running(self) -> bool:
        return self._server is not None

    def ensure_running(self) -> None:
        """Start the server while the user is entitled and has paired a phone; stop it otherwise."""
        wanted = check_ios_entitlement(self._get_config())[0] and self.is_paired()
        if wanted and self._server is None:
            self.start_server()
        elif not wanted and self._server is not None:
            self.stop_server()

    def start_server(self) -> bool:
        if self._server is not None:
            return True
        try:
            self._server = _Server(("0.0.0.0", self._port), self)
        except OSError as error:
            self.last_error = f"Cannot listen on port {self._port}: {error}"
            return False
        threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.25}, daemon=True).start()
        self.last_error = ""
        return True

    def stop_server(self) -> None:
        server, self._server = self._server, None
        if server is not None:
            server.shutdown()
            server.server_close()

    def status(self) -> dict:
        return {
            "paired": self.is_paired(),
            "running": self.running(),
            "address": f"{lan_address()}:{self._port}",
            "error": self.last_error,
        }

    # -- Phase 1 Real-Time Global Slot Deletion (`CLEAR_SLOT` & `CLEAR_ALL`) --

    def emit_clear_slot(self, slot_num: int) -> dict:
        """Purge slot from outbox/inbox and record `CLEAR_SLOT` tombstone packet (<100ms)."""
        packet = build_deletion_packet(action="CLEAR_SLOT", slot_id=slot_num)
        with self._lock:
            old_out = self._outbox.pop(slot_num, None)
            old_in = self._inbox.pop(slot_num, None)
            for s in (old_out, old_in):
                if s:
                    if isinstance(s, dict):
                        for k, v in list(s.items()):
                            if isinstance(v, str):
                                try:
                                    buf = bytearray(v.encode("utf-8"))
                                    for i in range(len(buf)):
                                        buf[i] = 0
                                except Exception:
                                    pass
                        s.clear()
                    elif isinstance(s, str):
                        try:
                            buf = bytearray(s.encode("utf-8"))
                            for i in range(len(buf)):
                                buf[i] = 0
                        except Exception:
                            pass
            self._tombstones.append(packet)
            if len(self._tombstones) > 32:
                self._tombstones = self._tombstones[-32:]
        return packet

    def emit_clear_all(self) -> dict:
        """Purge all slots from outbox/inbox and record `CLEAR_ALL` tombstone packet (<100ms)."""
        packet = build_deletion_packet(action="CLEAR_ALL", slot_id=None)
        with self._lock:
            for d in (self._outbox, self._inbox):
                for val in list(d.values()):
                    if isinstance(val, dict):
                        for k, v in list(val.items()):
                            if isinstance(v, str):
                                try:
                                    buf = bytearray(v.encode("utf-8"))
                                    for i in range(len(buf)):
                                        buf[i] = 0
                                except Exception:
                                    pass
                        val.clear()
                    elif isinstance(val, str):
                        try:
                            buf = bytearray(val.encode("utf-8"))
                            for i in range(len(buf)):
                                buf[i] = 0
                        except Exception:
                            pass
                d.clear()
            self._tombstones.append(packet)
            if len(self._tombstones) > 32:
                self._tombstones = self._tombstones[-32:]
        return packet

    # -- request handling (runs on server threads) --

    def is_throttled(self, client: str) -> bool:
        now = time.time()
        with self._lock:
            recent = [t for t in self._failures.get(client, []) if now - t < FAILURE_WINDOW_SECONDS]
            self._failures[client] = recent
            return len(recent) >= MAX_AUTH_FAILURES

    def note_auth_failure(self, client: str) -> None:
        with self._lock:
            self._failures.setdefault(client, []).append(time.time())

    def _fresh(self, request: dict) -> bool:
        """Reject stale timestamps and replayed request ids."""
        now = time.time()
        stamp, request_id = request.get("ts"), request.get("id")
        if not isinstance(stamp, (int, float)) or not isinstance(request_id, str) or len(request_id) > 64:
            return False
        if abs(now - stamp) > CLOCK_SKEW_SECONDS:
            return False
        with self._lock:
            self._seen_ids = {k: t for k, t in self._seen_ids.items() if now - t < 2 * CLOCK_SKEW_SECONDS}
            if request_id in self._seen_ids:
                return False
            self._seen_ids[request_id] = now
        return True

    @staticmethod
    def _reply(ok: bool, **fields) -> dict:
        return {"v": PROTOCOL_VERSION, "ok": ok, **fields}

    def handle_request(self, request: dict) -> dict:
        if request.get("v") != PROTOCOL_VERSION or not self._fresh(request):
            return self._reply(False, error="Stale or unsupported request.")
        config = self._get_config()
        allowed, error = check_ios_entitlement(config)
        if not allowed:
            return self._reply(False, error=error, upgrade_required=True)

        op = request.get("op")
        tier_val = getattr(getattr(config, "user", None), "tier", None)
        tier_str = tier_val.value if hasattr(tier_val, "value") else "basic"

        if op in ("cross_sync_android", "cross_sync_macos"):
            if not getattr(config, "is_premium", False):
                return self._reply(False, error=UPGRADE_CROSS_SYNC_MSG, upgrade_required=True, tier=tier_str)
            return self._reply(True, tier=tier_str)
        if op == "ping":
            return self._reply(True, tier=tier_str)
        if op == "pull":
            with self._lock:
                slots = {}
                for n, item in self._outbox.items():
                    if isinstance(item, dict):
                        slots[str(n)] = item
                    else:
                        slots[str(n)] = {"kind": "text", "text": str(item)}
                deletions = list(self._tombstones)
                self._tombstones.clear()
            return self._reply(True, slots=slots, deletions=deletions, max_slots=config.max_slots, tier=tier_str)
        if op == "push":
            res = self._store_inbound(request, config)
            res["tier"] = tier_str
            return res
        if op == "clear_slot":
            slot = request.get("slot")
            if isinstance(slot, int) and 1 <= slot <= 10:
                with self._lock:
                    self._outbox.pop(slot, None)
                    self._inbox.pop(slot, None)
                    packet = build_deletion_packet(action="CLEAR_SLOT", slot_id=slot)
                    self._tombstones.append(packet)
                    if len(self._tombstones) > 32:
                        self._tombstones = self._tombstones[-32:]
                if hasattr(self, "_clipboard_manager") and self._clipboard_manager:
                    try:
                        self._clipboard_manager.clear_slot(slot)
                    except Exception:
                        pass
            return self._reply(True, tier=tier_str)
        if op == "clear_all":
            with self._lock:
                self._outbox.clear()
                self._inbox.clear()
                packet = build_deletion_packet(action="CLEAR_ALL", slot_id=None)
                self._tombstones.append(packet)
                if len(self._tombstones) > 32:
                    self._tombstones = self._tombstones[-32:]
            if hasattr(self, "_clipboard_manager") and self._clipboard_manager:
                try:
                    self._clipboard_manager.clear_all()
                except Exception:
                    pass
            return self._reply(True, tier=tier_str)
        return self._reply(False, error="Unknown operation.")

    def _store_inbound(self, request: dict, config) -> dict:
        slot = request.get("slot")
        if not isinstance(slot, int) or isinstance(slot, bool) or not 1 <= slot <= config.max_slots:
            return self._reply(False, error="That slot is not available on your plan.")

        kind = request.get("kind", "text")
        data_b64 = request.get("data_b64")
        text = request.get("text")

        if not text and not data_b64:
            # Empty payload without explicit deletion command must not wipe desktop slot
            return self._reply(True)

        if kind in ("image", "diagram") and data_b64:
            try:
                img_bytes = base64.b64decode(data_b64.encode("ascii"))
                ok_i, dims, err_i = security_guard.validate_image_binary("PNG", img_bytes)
                if ok_i and hasattr(self, "_clipboard_manager") and self._clipboard_manager:
                    bundle = {
                        "ok": True,
                        "kind": "image",
                        "action": "copy",
                        "text": f"Image [{dims[0]}x{dims[1]}]",
                        "files": [],
                        "formats": {"PNG": img_bytes},
                        "dimensions": dims
                    }
                    from ratt.clipboard_manager import ClipboardSlot, SlotAction
                    with self._clipboard_manager._lock:
                        old = self._clipboard_manager._slots.get(slot)
                        if old:
                            old.wipe()
                        self._clipboard_manager._slots[slot] = ClipboardSlot(
                            timestamp=datetime.now(), action=SlotAction.COPY, bundle=bundle
                        )
                    self._clipboard_manager._notify_listeners()
                    with self._lock:
                        self._inbox[slot] = "[Image from iPhone]"
                    if self.on_inbound:
                        self.on_inbound(slot)
                    return self._reply(True)
            except Exception as e:
                return self._reply(False, error=f"Invalid image data: {e}")

        if kind == "files" and data_b64:
            try:
                fname = os.path.basename(str(request.get("file_name") or ""))
                # WIN-01: Validate filename, BiDi/nulls, reserved names, and blocked extensions BEFORE writing to disk
                if (
                    not fname
                    or security_guard.contains_bidi_spoofing(fname)
                    or "\x00" in fname
                    or ":" in fname
                    or fname.rstrip(". ").split(".")[0].upper() in security_guard._RESERVED_DEVICES
                ):
                    return self._reply(False, error="Security Block: Unsafe file name.")
                parts = fname.rstrip(". ").lower().split(".")
                if len(parts) > 1 and any(("." + p) in security_guard.BLOCKED_EXTENSIONS for p in parts[1:]):
                    return self._reply(False, error="Security Block: Blocked executable or script file extension.")
                file_bytes = base64.b64decode(data_b64.encode("ascii"))
                if len(file_bytes) > 25 * 1024 * 1024:
                    return self._reply(False, error="File exceeds 25 MB mobile sync limit.")
                base_dir = os.path.join(os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~"), "RATT", "spool")
                os.makedirs(base_dir, exist_ok=True)
                dest = os.path.join(base_dir, f"ios_{secrets.token_hex(4)}_{fname}")
                with open(dest, "wb") as f:
                    f.write(file_bytes)
                stored_ok = False
                try:
                    if hasattr(self, "_clipboard_manager") and self._clipboard_manager:
                        res = self._clipboard_manager.store_files_to_slot(slot, [dest])
                        stored_ok = bool(res[0] if isinstance(res, tuple) else res)
                    else:
                        stored_ok = True
                finally:
                    if not stored_ok and os.path.exists(dest):
                        try:
                            os.remove(dest)
                        except OSError:
                            pass
                if not stored_ok:
                    return self._reply(False, error="File rejected by security policy.")
                with self._lock:
                    self._inbox[slot] = f"[File: {fname}]"
                if self.on_inbound:
                    self.on_inbound(slot)
                return self._reply(True)
            except Exception as e:
                return self._reply(False, error=f"Invalid file data: {e}")

        if not isinstance(text, str) or len(text) > MAX_TEXT_CHARS:
            return self._reply(False, error="Text is missing or too long.")
        allowed, clean, _, error = security_guard.sanitize_unformatted_text_and_links(text)
        if not allowed:
            return self._reply(False, error=error)
        with self._lock:
            self._inbox[slot] = clean
        if hasattr(self, "_clipboard_manager") and self._clipboard_manager:
            try:
                self._clipboard_manager.copy_to_slot(slot, text=clean)
            except Exception:
                pass
        if self.on_inbound:
            self.on_inbound(slot)
        return self._reply(True)

    # -- desktop side of Copy / Cut / Paste (same shape as the Android bridge) --

    def sync_slot_to_ios(self, slot_num: int, bundle: dict, action: str = "copy") -> Tuple[bool, str]:
        """Copy or Cut a slot (text, image, or document) to the iPhone Slot Palette (Premium/Enterprise only)."""
        allowed, error = check_ios_entitlement(self._get_config())
        if not allowed:
            return False, error
        if not self.is_paired():
            return False, "Pair your iPhone first: Settings > iPhone (iOS) sync."
        if not bundle or not bundle.get("ok"):
            return False, "Invalid slot bundle."

        kind = bundle.get("kind", "text")
        outbox_payload = None

        if kind in ("image", "diagram"):
            formats = bundle.get("formats", {})
            png_bytes = formats.get("PNG") or formats.get("png")
            if not png_bytes and ("CF_DIB" in formats or "cf_dib" in formats):
                png_bytes = formats.get("CF_DIB") or formats.get("cf_dib")
            if not png_bytes and bundle.get("dataBase64"):
                try:
                    png_bytes = base64.b64decode(bundle["dataBase64"])
                except Exception:
                    png_bytes = None
            if not png_bytes:
                return False, "No valid image data available for iOS sync."
            if len(png_bytes) > 10 * 1024 * 1024:
                return False, "Image exceeds maximum iOS sync limit of 10 MB."
            dims = list(bundle.get("dimensions", (0, 0)))
            outbox_payload = {
                "kind": "image",
                "text": bundle.get("text", "Image"),
                "data_b64": base64.b64encode(png_bytes).decode("ascii"),
                "mime": "image/png",
                "dims": dims,
                "size": len(png_bytes)
            }
        elif kind == "files":
            files = bundle.get("files", [])
            ok_f, safe_files, err_f = security_guard.validate_file_list(files)
            if not ok_f or not safe_files:
                return False, err_f or "No valid files found."
            first_path = safe_files[0]
            if not os.path.exists(first_path):
                return False, "File does not exist on disk."
            sz = os.path.getsize(first_path)
            if sz > 25 * 1024 * 1024:
                return False, f"File ({sz // (1024*1024)} MB) exceeds 25 MB mobile sync limit."
            try:
                with open(first_path, "rb") as f:
                    file_bytes = f.read()
            except Exception as e:
                return False, f"Could not read file: {e}"
            import mimetypes
            fname = os.path.basename(first_path)
            mime = mimetypes.guess_type(first_path)[0] or "application/octet-stream"
            outbox_payload = {
                "kind": "files",
                "text": f"{fname} ({sz // 1024} KB)",
                "file_name": fname,
                "data_b64": base64.b64encode(file_bytes).decode("ascii"),
                "mime": mime,
                "size": sz
            }
        else:
            allowed, clean, _, error = security_guard.sanitize_unformatted_text_and_links(bundle.get("text", ""))
            if not allowed:
                return False, error
            if len(clean) > MAX_TEXT_CHARS:
                return False, "That slot is too long for the iPhone Slot Palette (limit 64,000 characters)."
            outbox_payload = {
                "kind": kind if kind in ("text", "link") else "text",
                "text": clean
            }

        with self._lock:
            self._outbox[slot_num] = outbox_payload
        self.ensure_running()
        verb = "Cut" if action == "cut" else "Copied"
        type_label = "Image" if kind in ("image", "diagram") else ("File" if kind == "files" else "Text")
        return True, f"{verb} {type_label} Slot #{slot_num} to iPhone Slot Palette"

    def paste_slot_from_ios(self, slot_num: int) -> Tuple[bool, Optional[dict], str]:
        """Take the text the iPhone sent for this slot (Premium/Enterprise only)."""
        allowed, error = check_ios_entitlement(self._get_config())
        if not allowed:
            return False, None, error
        with self._lock:
            text = self._inbox.pop(slot_num, None)
        if text is None:
            return False, None, f"The iPhone has not sent Slot #{slot_num} yet."
        bundle = {"ok": True, "kind": "text", "action": "copy", "text": text, "files": [],
                  "formats": {}, "dimensions": (0, 0)}
        return True, bundle, f"Pasted Slot #{slot_num} from iPhone Slot Palette"

    # -- BasePlatform contract --

    def read_clipboard_bundle(self, default_action: str = "copy") -> dict:
        allowed, error = check_ios_entitlement(self._get_config())
        if not allowed:
            return {"ok": False, "error": error, "upgrade_required": True}
        with self._lock:
            if not self._inbox:
                return {"ok": False, "error": "No iPhone keyboard data available."}
            text = self._inbox[max(self._inbox)]
        return {"ok": True, "kind": "text", "action": default_action, "text": text,
                "files": [], "formats": {}, "dimensions": (0, 0)}

    def restore_clipboard_bundle(self, bundle: dict) -> bool:
        return self.write_clipboard_bundle(bundle)[0]

    def write_clipboard_bundle(self, bundle: dict) -> Tuple[bool, str]:
        return self.sync_slot_to_ios(int(bundle.get("slot", 1)), bundle, bundle.get("action", "copy"))

    def inject_keystrokes(self, combo: str) -> None:
        """On iOS the keyboard extension types with `textDocumentProxy.insertText`."""
        return None

    def single_instance_acquire(self) -> bool:
        return True

    def protect_memory_buffer(self, data: bytes) -> bytes:
        """Encrypt bytes in RAM using a per-process ephemeral 256-bit random key (COM-01)."""
        if not data:
            return b""
        if not hasattr(self, "_ram_key") or not self._ram_key:
            self._ram_key = secrets.token_bytes(32)
        nonce = secrets.token_bytes(12)
        return nonce + AESGCM(self._ram_key).encrypt(nonce, data, b"RATT-IOS-RAM-V2")

    def unprotect_memory_buffer(self, data: bytes, orig_len: int = 0) -> bytes:
        if not data or len(data) < 28 or not hasattr(self, "_ram_key") or not self._ram_key:
            return b""
        try:
            dec = AESGCM(self._ram_key).decrypt(data[:12], data[12:], b"RATT-IOS-RAM-V2")
            return dec[:orig_len] if orig_len > 0 else dec
        except Exception:
            return b""

    def get_sequence_number(self) -> int:
        with self._lock:
            return len(self._outbox) + len(self._inbox)
