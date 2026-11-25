"""Application configuration, user profile state, and local session storage."""
import base64
import ctypes
import hashlib
import hmac
import json
import math
import os
import re
import secrets
import time
import urllib.parse
import webbrowser
from ctypes import wintypes
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple


class UserTier(Enum):
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


TRANSLATE_LANGUAGES = [
    ("en", "English"),
    ("fr", "French"),
    ("es", "Spanish"),
    ("de", "German"),
    ("ru", "Russian"),
    ("zh", "Chinese"),
    ("ar", "Arabic"),
    ("ja", "Japanese"),
    ("hi", "Hindi"),
]

TRIAL_DAYS = 7

# Cybrox web portal endpoints (Sign-Up, Sign-In, Password & Profile Management)
CYBROX_WEB_URL = "https://cybrox.com"
CYBROX_SIGNUP_URL = "https://cybrox.com/signup"
CYBROX_SIGNIN_URL = "https://cybrox.com/signin"
CYBROX_ACCOUNT_URL = "https://cybrox.com/account"
CYBROX_PASSWORD_URL = "https://cybrox.com/account/password"
CYBROX_PROFILE_URL = "https://cybrox.com/account/profile"

_ALLOWED_WEB_HOSTS = frozenset({"cybrox.com", "www.cybrox.com", "ratt.cybrox.com", "api.cybrox.com"})
_VALID_NAME_RE = re.compile(r"^[A-Za-z0-9 ]+$")


def validate_user_name(name: str) -> Tuple[bool, str]:
    """Validate that a user's name contains only letters, numbers, and spaces (no special characters)."""
    cleaned = " ".join((name or "").strip().split())
    if not cleaned:
        return False, "Please enter your profile name."
    if len(cleaned) > 80:
        return False, "Profile name must be 80 characters or fewer."
    if not _VALID_NAME_RE.match(cleaned) or not any(ch.isalnum() for ch in cleaned):
        return False, "Profile name cannot contain special characters (only letters and numbers are allowed)."
    return True, cleaned

# Ed25519 public key used to verify cloud-issued subscription tokens
# (Placeholder empty-string SHA-256 is explicitly rejected until a real production key is provisioned.)
_PLACEHOLDER_PUBLIC_KEY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
CYBROX_PUBLIC_KEY = os.environ.get("RATT_LICENSE_PUBLIC_KEY", _PLACEHOLDER_PUBLIC_KEY)

# Brute-force login protection (in-memory per-account attempt tracker)
_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_LOCKOUT_SECONDS = 300
_login_failures: Dict[str, List[float]] = {}
_DUMMY_SALT = "00" * 16


def open_cybrox_web(url: str = CYBROX_ACCOUNT_URL) -> bool:
    """Open an official Cybrox HTTPS page in the user's default browser."""
    try:
        parsed = urllib.parse.urlparse(url.strip())
        if parsed.scheme != "https" or (parsed.hostname or "").lower() not in _ALLOWED_WEB_HOSTS:
            return False
        return bool(webbrowser.open(url.strip(), new=2))
    except Exception:
        return False


def load_verified_license(token_b64: str, public_key_hex: Optional[str] = None) -> dict:
    """Verify an Ed25519-signed license token from the Cybrox Cloud service (COM-03).

    Accepts a Base64-encoded payload consisting of `64-byte Ed25519 signature + UTF-8 JSON`
    and verifies it using `cryptography` (or `PyNaCl` if available). Explicitly rejects
    the placeholder SHA-256("") key.
    """
    fallback = {"tier": "basic", "premium_slots": 0, "expires_at": None}
    key_hex = (public_key_hex or CYBROX_PUBLIC_KEY or "").strip().lower()
    if not key_hex or key_hex == _PLACEHOLDER_PUBLIC_KEY or len(key_hex) != 64:
        return fallback
    try:
        raw_key = bytes.fromhex(key_hex)
        signed_blob = base64.b64decode(token_b64.encode("ascii"))
        if len(signed_blob) <= 64:
            return fallback
        sig, msg = signed_blob[:64], signed_blob[64:]
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            Ed25519PublicKey.from_public_bytes(raw_key).verify(sig, msg)
            data = json.loads(msg.decode("utf-8"))
        except ImportError:
            import nacl.signing
            verify_key = nacl.signing.VerifyKey(raw_key)
            data = json.loads(verify_key.verify(signed_blob).decode("utf-8"))
        return data if isinstance(data, dict) else fallback
    except Exception:
        return fallback


def _atomic_write_json(path: str, payload: dict) -> None:
    """Write JSON atomically and restrict file permissions to the current user."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_path, path)
        os.chmod(path, 0o600)
    except OSError:
        pass


@dataclass
class ConnectedUser:
    email: str = ""
    display_name: str = ""
    is_online: bool = False


@dataclass
class UserProfile:
    email: str = ""
    display_name: str = "User"
    tier: UserTier = UserTier.BASIC
    is_logged_in: bool = False
    premium_slots: int = 0
    created_at: Optional[datetime] = None
    subscription_expiry: Optional[datetime] = None
    last_renewal_alert: Optional[datetime] = None
    connections: List[ConnectedUser] = field(default_factory=list)
    company_name: str = ""
    max_workers: int = 0
    workers: List[ConnectedUser] = field(default_factory=list)

    @property
    def is_subscription_expired(self) -> bool:
        if self.tier == UserTier.BASIC or self.subscription_expiry is None:
            return False
        return self.subscription_expiry <= datetime.now()

    @property
    def trial_days_remaining(self) -> int:
        if self.tier in (UserTier.PREMIUM, UserTier.ENTERPRISE) and not self.is_subscription_expired:
            return 999
        if self.created_at is None:
            return TRIAL_DAYS
        elapsed = (datetime.now() - self.created_at).days
        return max(0, TRIAL_DAYS - elapsed)

    @property
    def is_trial_active(self) -> bool:
        if self.tier in (UserTier.PREMIUM, UserTier.ENTERPRISE) and not self.is_subscription_expired:
            return True
        return self.trial_days_remaining > 0

    @property
    def days_until_expiry(self) -> Optional[int]:
        if self.subscription_expiry is None:
            return None
        secs = (self.subscription_expiry - datetime.now()).total_seconds()
        return max(0, math.ceil(secs / 86400))

    @property
    def renewal_alert_needed(self) -> bool:
        if self.tier == UserTier.BASIC or self.subscription_expiry is None:
            return False
        days = self.days_until_expiry
        return days is not None and days <= 90

    def should_show_renewal_alert(self) -> bool:
        if not self.renewal_alert_needed:
            return False
        if self.last_renewal_alert is None:
            return True
        now = datetime.now()
        if self.days_until_expiry <= 7:
            return self.last_renewal_alert.date() != now.date()
        return (now - self.last_renewal_alert).days >= 30

    def set_subscription(self, months: int = 1):
        now = datetime.now()
        start = self.subscription_expiry if (self.subscription_expiry and self.subscription_expiry > now) else now
        self.subscription_expiry = start + timedelta(days=30 * months)
        self.last_renewal_alert = None

    @property
    def all_contacts(self) -> List[ConnectedUser]:
        contacts = list(self.connections)
        existing = {c.email for c in contacts}
        for w in self.workers:
            if w.email not in existing:
                contacts.append(w)
                existing.add(w.email)
        return contacts


@dataclass
class AppConfig:
    APP_NAME: str = "RATT"
    VERSION: str = "2"
    VERSION_FULL: str = "2.0.0"
    PUBLISHER: str = "Cybrox"
    COMPANY: str = "Cybrox"

    # Website URLs exposed on config instance for convenient access
    CYBROX_WEB_URL: str = CYBROX_WEB_URL
    CYBROX_SIGNUP_URL: str = CYBROX_SIGNUP_URL
    CYBROX_SIGNIN_URL: str = CYBROX_SIGNIN_URL
    CYBROX_ACCOUNT_URL: str = CYBROX_ACCOUNT_URL
    CYBROX_PASSWORD_URL: str = CYBROX_PASSWORD_URL
    CYBROX_PROFILE_URL: str = CYBROX_PROFILE_URL

    # Slot limits
    MAX_SLOTS_BASIC: int = 10
    MIN_SLOTS_PREMIUM: int = 10
    MAX_SLOTS_PREMIUM: int = 50000

    # Commercial pricing
    PRICE_USD_PER_10_SLOTS: float = 0.99
    PRICE_USD_ENTERPRISE: float = 2.99
    GHS_TO_USD_RATE: float = 15.4
    MAX_ENTERPRISE_WORKERS: int = 3000

    # Hotkey timing (seconds)
    CHORD_TIMEOUT: float = 2.5
    PASTE_SLOT_DELAY: float = 1.0
    DIGIT_GAP: float = 0.5

    # Global hotkeys
    POPUP_HOTKEY: str = "ctrl+shift+r"
    EMERGENCY_TOGGLE_HOTKEY: str = "ctrl+alt+p"
    EMERGENCY_TOGGLE_HOTKEY_ALT: str = "win+shift+pause"

    # Global ON/OFF state (True = Active, False = Paused / Keyboard & Mouse released)
    enabled: bool = True

    # Encrypted Vault & Searchable Archive Configuration (Solves Competitor Edge #2)
    enable_vault: bool = True
    vault_retention_days: int = 30
    vault_scrub_sensitive: bool = True

    # Zero-Knowledge Remote Relay & Cross-Country Bridge (Solves Competitor Edge #1)
    enable_remote_relay: bool = True
    remote_relay_host: str = "relay.cybrox.com"

    SHARE_VALIDITY_HOURS: int = 12
    user: UserProfile = field(default_factory=UserProfile)

    @property
    def price_usd_per_10_slots(self) -> float:
        return self.PRICE_USD_PER_10_SLOTS

    @property
    def price_usd_enterprise(self) -> float:
        return self.PRICE_USD_ENTERPRISE

    @property
    def PRICE_GHS_PER_10_SLOTS(self) -> float:
        return round(self.PRICE_USD_PER_10_SLOTS * self.GHS_TO_USD_RATE, 2)

    @property
    def PRICE_GHS_ENTERPRISE(self) -> float:
        return round(self.PRICE_USD_ENTERPRISE * self.GHS_TO_USD_RATE, 2)

    def calculate_price(self, num_slots: int) -> dict:
        blocks = num_slots / 10
        usd = round(blocks * self.PRICE_USD_PER_10_SLOTS, 2)
        ghs = round(usd * self.GHS_TO_USD_RATE, 2)
        return {
            "slots": num_slots,
            "ghs_monthly": ghs,
            "usd_monthly": usd,
            "ghs_per_slot": round(self.PRICE_GHS_PER_10_SLOTS / 10, 2),
            "usd_per_slot": round(usd / num_slots, 4) if num_slots > 0 else 0,
        }

    @property
    def has_paid_tier(self) -> bool:
        return self.user.tier in (UserTier.PREMIUM, UserTier.ENTERPRISE)

    @property
    def max_slots(self) -> int:
        if self.is_enterprise or self.is_premium:
            return self.user.premium_slots if self.user.premium_slots > 0 else self.MIN_SLOTS_PREMIUM
        return self.MAX_SLOTS_BASIC

    @property
    def is_premium(self) -> bool:
        return self.user.tier in (UserTier.PREMIUM, UserTier.ENTERPRISE) and not self.user.is_subscription_expired

    @property
    def is_enterprise(self) -> bool:
        return self.user.tier == UserTier.ENTERPRISE and not self.user.is_subscription_expired

    # -- DPAPI & HMAC storage helpers --

    @staticmethod
    def _appdata_dir() -> str:
        d = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "RATT")
        os.makedirs(d, exist_ok=True)
        return d

    @classmethod
    def _posix_local_key(cls) -> bytes:
        """Per-user 256-bit AES-GCM key stored with 0600 permissions for non-Windows hosts (COM-03)."""
        kpath = os.path.join(cls._appdata_dir(), ".local_enc_key")
        if os.path.exists(kpath):
            try:
                with open(kpath, "rb") as f:
                    k = f.read()
                if len(k) == 32:
                    return k
            except OSError:
                pass
        k = secrets.token_bytes(32)
        try:
            fd = os.open(kpath, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(k)
        except OSError:
            pass
        return k

    @classmethod
    def _dpapi_protect(cls, raw: bytes) -> bytes:
        """Encrypt bytes using Windows DPAPI (or AES-256-GCM on POSIX; never silent plaintext) (COM-03)."""
        if not raw:
            return b""
        if os.name != "nt":
            try:
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                nonce = secrets.token_bytes(12)
                return b"RATTGCM1" + nonce + AESGCM(cls._posix_local_key()).encrypt(nonce, raw, b"RATT-POSIX-ATREST")
            except Exception:
                return b""
        try:
            class DATA_BLOB(ctypes.Structure):
                _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

            crypt32 = ctypes.windll.crypt32
            kernel32 = ctypes.windll.kernel32
            kernel32.LocalFree.argtypes = [ctypes.c_void_p]
            kernel32.LocalFree.restype = ctypes.c_void_p

            buf = ctypes.create_string_buffer(raw, len(raw))
            try:
                in_blob = DATA_BLOB(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
                out_blob = DATA_BLOB()
                CRYPTPROTECT_UI_FORBIDDEN = 0x01
                if crypt32.CryptProtectData(
                    ctypes.byref(in_blob), None, None, None, None,
                    CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out_blob)
                ):
                    try:
                        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
                    finally:
                        kernel32.LocalFree(ctypes.cast(out_blob.pbData, ctypes.c_void_p))
            finally:
                ctypes.memset(buf, 0, len(raw))
        except Exception:
            pass
        return b""

    @classmethod
    def _dpapi_unprotect(cls, enc: bytes) -> Optional[bytes]:
        """Decrypt bytes protected with Windows DPAPI (or POSIX AES-256-GCM). Returns None on tamper/failure."""
        if not enc:
            return None
        if os.name != "nt":
            if enc.startswith(b"RATTGCM1") and len(enc) > 20:
                try:
                    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                    return AESGCM(cls._posix_local_key()).decrypt(enc[8:20], enc[20:], b"RATT-POSIX-ATREST")
                except Exception:
                    return None
            return None
        try:
            class DATA_BLOB(ctypes.Structure):
                _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

            crypt32 = ctypes.windll.crypt32
            kernel32 = ctypes.windll.kernel32
            kernel32.LocalFree.argtypes = [ctypes.c_void_p]
            kernel32.LocalFree.restype = ctypes.c_void_p

            buf = ctypes.create_string_buffer(enc, len(enc))
            in_blob = DATA_BLOB(len(enc), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
            out_blob = DATA_BLOB()
            CRYPTPROTECT_UI_FORBIDDEN = 0x01
            if crypt32.CryptUnprotectData(
                ctypes.byref(in_blob), None, None, None, None,
                CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out_blob)
            ):
                try:
                    return ctypes.string_at(out_blob.pbData, out_blob.cbData)
                finally:
                    ctypes.memset(out_blob.pbData, 0, out_blob.cbData)
                    kernel32.LocalFree(ctypes.cast(out_blob.pbData, ctypes.c_void_p))
            return None
        except Exception:
            return None

    @classmethod
    def _get_hmac_key(cls) -> bytes:
        key_file = os.path.join(cls._appdata_dir(), ".key")
        if os.path.exists(key_file):
            try:
                with open(key_file, "rb") as f:
                    raw = cls._dpapi_unprotect(f.read())
                if raw and len(raw) == 32:
                    return raw
            except Exception:
                pass
        key = secrets.token_bytes(32)
        try:
            with open(key_file, "wb") as f:
                f.write(cls._dpapi_protect(key))
            os.chmod(key_file, 0o600)
        except Exception:
            pass
        return key

    @classmethod
    def _sign_dict(cls, payload: dict) -> str:
        clean = {k: v for k, v in payload.items() if k != "_sig"}
        canonical = json.dumps(clean, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac.new(cls._get_hmac_key(), canonical, hashlib.sha256).hexdigest()

    @classmethod
    def _verify_dict(cls, payload: dict) -> bool:
        sig = payload.get("_sig", "")
        if not sig or not isinstance(sig, str):
            return False
        return secrets.compare_digest(sig, cls._sign_dict(payload))

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        if not salt:
            salt = secrets.token_hex(16)
        dk = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt),
            n=16384, r=8, p=1, dklen=32,
        )
        return salt, dk.hex()

    @classmethod
    def verify_password(cls, password: str, salt: str, expected_hash: str) -> bool:
        try:
            _, actual_hash = cls.hash_password(password, salt)
            return secrets.compare_digest(actual_hash, expected_hash)
        except Exception:
            return False

    def _load_accounts(self) -> dict:
        acct_file = os.path.join(self._appdata_dir(), "accounts.json")
        if not os.path.exists(acct_file):
            return {}
        try:
            with open(acct_file, "r", encoding="utf-8") as f:
                wrapper = json.load(f)
            if not isinstance(wrapper, dict) or not self._verify_dict(wrapper):
                return {}
            accounts = wrapper.get("accounts", {})
            return accounts if isinstance(accounts, dict) else {}
        except Exception:
            return {}

    def _save_accounts(self, accounts: dict):
        acct_file = os.path.join(self._appdata_dir(), "accounts.json")
        wrapper = {"accounts": accounts}
        wrapper["_sig"] = self._sign_dict(wrapper)
        _atomic_write_json(acct_file, wrapper)

    def account_exists(self, email: str) -> bool:
        norm = email.strip().lower()
        return bool(norm and norm in self._load_accounts())

    def _serialize_user_state(self) -> dict:
        def ser_contact(c):
            return {"email": c.email, "display_name": c.display_name, "is_online": c.is_online}

        return {
            "email": self.user.email,
            "display_name": self.user.display_name,
            "tier": self.user.tier.value,
            "is_logged_in": self.user.is_logged_in,
            "premium_slots": self.user.premium_slots,
            "created_at": self.user.created_at.isoformat() if self.user.created_at else None,
            "subscription_expiry": self.user.subscription_expiry.isoformat() if self.user.subscription_expiry else None,
            "last_renewal_alert": self.user.last_renewal_alert.isoformat() if self.user.last_renewal_alert else None,
            "company_name": self.user.company_name,
            "max_workers": self.user.max_workers,
            "connections": [ser_contact(c) for c in self.user.connections],
            "workers": [ser_contact(w) for w in self.user.workers],
        }

    def _apply_user_state(self, data: dict):
        self.user.email = data.get("email", "")
        raw_name = str(data.get("display_name", "User") or "User")
        sanitized_name = re.sub(r"[^A-Za-z0-9 ]", "", raw_name).strip()
        self.user.display_name = " ".join(sanitized_name.split()) or "User"
        self.user.tier = UserTier(data.get("tier", "basic"))
        self.user.is_logged_in = data.get("is_logged_in", False)
        self.user.premium_slots = data.get("premium_slots", 0)
        self.user.company_name = data.get("company_name", "")
        self.user.max_workers = data.get("max_workers", 0)

        raw_dt = data.get("created_at")
        self.user.created_at = datetime.fromisoformat(raw_dt) if raw_dt else None

        raw_exp = data.get("subscription_expiry")
        self.user.subscription_expiry = datetime.fromisoformat(raw_exp) if raw_exp else None

        raw_alert = data.get("last_renewal_alert")
        self.user.last_renewal_alert = datetime.fromisoformat(raw_alert) if raw_alert else None

        def load_contact(d):
            c_name = re.sub(r"[^A-Za-z0-9 ]", "", str(d.get("display_name", "") or "")).strip()
            return ConnectedUser(
                email=d.get("email", ""),
                display_name=" ".join(c_name.split()),
                is_online=d.get("is_online", False),
            )

        self.user.connections = [load_contact(c) for c in data.get("connections", [])]
        self.user.workers = [load_contact(w) for w in data.get("workers", [])]

    def register_account(self, email: str, display_name: str, password_salt: str, password_hash: str):
        ok, clean_name = validate_user_name(display_name)
        if not ok:
            raise ValueError(clean_name)
        norm = email.strip().lower()
        self.user = UserProfile(
            email=email.strip(),
            display_name=clean_name,
            tier=UserTier.BASIC,
            is_logged_in=True,
            premium_slots=0,
            created_at=datetime.now(),
        )
        accounts = self._load_accounts()
        acct_data = self._serialize_user_state()
        acct_data["password_salt"] = password_salt
        acct_data["password_hash"] = password_hash
        accounts[norm] = acct_data
        self._save_accounts(accounts)
        self.save_session()

    def authenticate_user(self, email: str, password: str) -> Tuple[bool, str]:
        """Authenticate against registered accounts with brute-force throttling and timing equalization."""
        norm = email.strip().lower()
        now = time.time()
        recent = [t for t in _login_failures.get(norm, []) if now - t < _LOGIN_LOCKOUT_SECONDS]
        _login_failures[norm] = recent
        if len(recent) >= _LOGIN_MAX_ATTEMPTS:
            return False, "Too many failed sign-in attempts. Please wait 5 minutes or reset your password on the Cybrox website."

        accounts = self._load_accounts()
        acct = accounts.get(norm)
        if not acct:
            # Equalize response timing and use identical error message to prevent email enumeration (COM-07)
            self.hash_password(password or "invalid", _DUMMY_SALT)
            _login_failures.setdefault(norm, []).append(now)
            return False, "Incorrect email or password."

        salt = acct.get("password_salt", "")
        pw_hash = acct.get("password_hash", "")
        if not salt or not pw_hash or not self.verify_password(password, salt, pw_hash):
            _login_failures.setdefault(norm, []).append(now)
            return False, "Incorrect email or password."

        _login_failures.pop(norm, None)
        self._apply_user_state(acct)
        self.user.is_logged_in = True
        self.save_session()
        return True, f"Welcome back, {self.user.display_name}!"

    def update_profile_name(self, new_name: str) -> Tuple[bool, str]:
        """Update the signed-in user's display name (letters, numbers, and spaces only)."""
        ok, res = validate_user_name(new_name)
        if not ok:
            return False, res
        self.user.display_name = res
        self.save_session()
        return True, "Profile name updated."

    def change_password(self, email: str, current_password: str, new_password: str) -> Tuple[bool, str]:
        """Change password for a registered account."""
        if len(new_password or "") < 6:
            return False, "New password must be at least 6 characters."
        norm = email.strip().lower()
        accounts = self._load_accounts()
        acct = accounts.get(norm)
        if not acct:
            return False, "Account not found."
        salt = acct.get("password_salt", "")
        pw_hash = acct.get("password_hash", "")
        if not self.verify_password(current_password, salt, pw_hash):
            return False, "Current password is incorrect."
        new_salt, new_hash = self.hash_password(new_password)
        acct["password_salt"] = new_salt
        acct["password_hash"] = new_hash
        accounts[norm] = acct
        self._save_accounts(accounts)
        return True, "Password updated successfully."

    def save_session(self):
        session_file = os.path.join(self._appdata_dir(), "session.json")
        data = self._serialize_user_state()
        data["_sig"] = self._sign_dict(data)
        _atomic_write_json(session_file, data)

        if self.user.is_logged_in and self.user.email:
            norm = self.user.email.strip().lower()
            accounts = self._load_accounts()
            if norm in accounts:
                pw_salt = accounts[norm].get("password_salt", "")
                pw_hash = accounts[norm].get("password_hash", "")
                updated = self._serialize_user_state()
                updated["password_salt"] = pw_salt
                updated["password_hash"] = pw_hash
                accounts[norm] = updated
                self._save_accounts(accounts)

    def load_session(self):
        session_file = os.path.join(self._appdata_dir(), "session.json")
        if not os.path.exists(session_file):
            return

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict) or not self._verify_dict(data):
                self.clear_session()
                return

            email = data.get("email", "").strip().lower()
            accounts = self._load_accounts()
            if not email or email not in accounts:
                self.clear_session()
                return

            if "license_token" in data and data["license_token"]:
                verified = load_verified_license(str(data["license_token"]))
                data["tier"] = verified.get("tier", "basic")
                data["premium_slots"] = 0 if data["tier"] == "basic" else verified.get("premium_slots", 0)
                if verified.get("expires_at"):
                    data["subscription_expiry"] = verified["expires_at"]

            self._apply_user_state(data)
        except Exception:
            pass

    def clear_session(self):
        self.user = UserProfile()
        session_file = os.path.join(self._appdata_dir(), "session.json")
        try:
            os.remove(session_file)
        except OSError:
            pass


config = AppConfig()
config.load_session()
