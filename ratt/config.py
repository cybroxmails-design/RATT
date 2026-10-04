"""RATT Application Configuration."""
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List


class UserTier(Enum):
    """User subscription tier."""
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


# Supported translation languages
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

# Trial period for basic users (Share & Mirror)
TRIAL_DAYS = 7


@dataclass
class ConnectedUser:
    """A connected user for sharing/mirroring."""
    email: str = ""
    display_name: str = ""
    is_online: bool = False


@dataclass
class UserProfile:
    """User profile information."""
    email: str = ""
    display_name: str = "User"
    tier: UserTier = UserTier.BASIC
    is_logged_in: bool = False
    premium_slots: int = 0
    created_at: Optional[datetime] = None
    subscription_expiry: Optional[datetime] = None   # Set when user pays (30 days × months)
    last_renewal_alert: Optional[datetime] = None    # When the renewal reminder was last shown
    
    # Connected users (Premium & Enterprise)
    connections: List[ConnectedUser] = field(default_factory=list)
    
    # Enterprise-specific
    company_name: str = ""
    max_workers: int = 0       # Enterprise: 1-3000
    workers: List[ConnectedUser] = field(default_factory=list)

    @property
    def trial_days_remaining(self) -> int:
        if self.tier in (UserTier.PREMIUM, UserTier.ENTERPRISE):
            return 999
        if self.created_at is None:
            return TRIAL_DAYS
        elapsed = (datetime.now() - self.created_at).days
        return max(0, TRIAL_DAYS - elapsed)

    @property
    def is_trial_active(self) -> bool:
        if self.tier in (UserTier.PREMIUM, UserTier.ENTERPRISE):
            return True
        return self.trial_days_remaining > 0

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Days remaining in subscription. None if no expiry set."""
        if self.subscription_expiry is None:
            return None
        import math
        secs = (self.subscription_expiry - datetime.now()).total_seconds()
        return max(0, math.ceil(secs / 86400))

    @property
    def renewal_alert_needed(self) -> bool:
        """True if within 90 days of expiry and subscription is paid tier."""
        if self.tier == UserTier.BASIC or self.subscription_expiry is None:
            return False
        days = self.days_until_expiry
        return days is not None and days <= 90

    def should_show_renewal_alert(self) -> bool:
        """Reminder schedule: starts 90 days (3 months) before expiry and repeats
        every 30 days; in the final 7 days it repeats daily."""
        if not self.renewal_alert_needed:
            return False
        if self.last_renewal_alert is None:
            return True
        now = datetime.now()
        if self.days_until_expiry <= 7:
            return self.last_renewal_alert.date() != now.date()
        return (now - self.last_renewal_alert).days >= 30

    def set_subscription(self, months: int = 1):
        """Start/extend a paid subscription by `months` x 30 days.
        Renewing before expiry adds time on top of the remaining period."""
        now = datetime.now()
        start = self.subscription_expiry if (self.subscription_expiry and self.subscription_expiry > now) else now
        self.subscription_expiry = start + timedelta(days=30 * months)
        self.last_renewal_alert = None
    
    @property
    def all_contacts(self) -> List[ConnectedUser]:
        """Get all contacts (connections + workers) for sharing."""
        contacts = list(self.connections)
        for w in self.workers:
            if w.email not in [c.email for c in contacts]:
                contacts.append(w)
        return contacts


@dataclass 
class AppConfig:
    """Application configuration."""
    APP_NAME: str = "RATT"
    VERSION: str = "1.0.0"
    PUBLISHER: str = "Cybrox.Inc"
    COMPANY: str = "Cybrox.Inc"
    
    # Slot limits
    MAX_SLOTS_BASIC: int = 2
    MIN_SLOTS_PREMIUM: int = 10
    MAX_SLOTS_PREMIUM: int = 50000
    
    # Pricing
    PRICE_GHS_PER_10_SLOTS: float = 20.0   # Premium: GHS 20 per 10 slots/month
    PRICE_GHS_ENTERPRISE: float = 250.0     # Enterprise: GHS 250/month flat
    GHS_TO_USD_RATE: float = 15.4
    MAX_ENTERPRISE_WORKERS: int = 3000
    
    # Hotkey chord timeout (seconds)
    CHORD_TIMEOUT: float = 2.0
    
    # Popup hotkey
    POPUP_HOTKEY: str = "ctrl+shift+r"
    
    # Share/Mirror link validity
    SHARE_VALIDITY_HOURS: int = 12
    
    # User profile
    user: UserProfile = field(default_factory=UserProfile)
    
    @property
    def price_usd_per_10_slots(self) -> float:
        return round(self.PRICE_GHS_PER_10_SLOTS / self.GHS_TO_USD_RATE, 2)
    
    @property
    def price_usd_enterprise(self) -> float:
        return round(self.PRICE_GHS_ENTERPRISE / self.GHS_TO_USD_RATE, 2)
    
    def calculate_price(self, num_slots: int) -> dict:
        blocks = num_slots / 10
        ghs = blocks * self.PRICE_GHS_PER_10_SLOTS
        usd = round(ghs / self.GHS_TO_USD_RATE, 2)
        return {
            "slots": num_slots,
            "ghs_monthly": round(ghs, 2),
            "usd_monthly": usd,
            "ghs_per_slot": round(self.PRICE_GHS_PER_10_SLOTS / 10, 2),
            "usd_per_slot": round(usd / num_slots, 4) if num_slots > 0 else 0,
        }
    
    @property
    def max_slots(self) -> int:
        if self.user.tier == UserTier.ENTERPRISE:
            return self.user.premium_slots if self.user.premium_slots > 0 else self.MIN_SLOTS_PREMIUM
        if self.user.tier == UserTier.PREMIUM:
            return self.user.premium_slots if self.user.premium_slots > 0 else self.MIN_SLOTS_PREMIUM
        return self.MAX_SLOTS_BASIC
    
    @property
    def is_premium(self) -> bool:
        return self.user.tier in (UserTier.PREMIUM, UserTier.ENTERPRISE)
    
    @property
    def is_enterprise(self) -> bool:
        return self.user.tier == UserTier.ENTERPRISE


    def save_session(self):
        """Persist user session to disk so they stay logged in across restarts."""
        import json, os
        session_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "RATT")
        os.makedirs(session_dir, exist_ok=True)
        session_file = os.path.join(session_dir, "session.json")
        
        # Serialize connections and workers
        def ser_contact(c):
            return {"email": c.email, "display_name": c.display_name, "is_online": c.is_online}
        
        data = {
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
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_session(self):
        """Load user session from disk on startup."""
        import json, os
        session_file = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")), "RATT", "session.json"
        )
        if not os.path.exists(session_file):
            return  # No saved session — fresh install

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.user.email = data.get("email", "")
            self.user.display_name = data.get("display_name", "User")
            self.user.tier = UserTier(data.get("tier", "basic"))
            self.user.is_logged_in = data.get("is_logged_in", False)
            self.user.premium_slots = data.get("premium_slots", 0)
            self.user.company_name = data.get("company_name", "")
            self.user.max_workers = data.get("max_workers", 0)

            raw_dt = data.get("created_at")
            if raw_dt:
                self.user.created_at = datetime.fromisoformat(raw_dt)

            raw_exp = data.get("subscription_expiry")
            if raw_exp:
                self.user.subscription_expiry = datetime.fromisoformat(raw_exp)
            raw_alert = data.get("last_renewal_alert")
            if raw_alert:
                self.user.last_renewal_alert = datetime.fromisoformat(raw_alert)

            def load_contact(d):
                c = ConnectedUser()
                c.email = d.get("email", "")
                c.display_name = d.get("display_name", "")
                c.is_online = d.get("is_online", False)
                return c

            self.user.connections = [load_contact(c) for c in data.get("connections", [])]
            self.user.workers = [load_contact(w) for w in data.get("workers", [])]
        except Exception:
            pass  # Corrupt session file — start fresh

    def clear_session(self):
        """Delete saved session (logout)."""
        import os
        session_file = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")), "RATT", "session.json"
        )
        try:
            os.remove(session_file)
        except FileNotFoundError:
            pass


# Global config instance — load saved session immediately
config = AppConfig()
config.load_session()
