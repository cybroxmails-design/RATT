"""RATT API Configuration (SMTP + Paystack payments).

Secrets are NEVER stored in source code. They are read, in this order, from:
  1. %APPDATA%\\RATT\\services.json   (written by Settings > Configure Services)
  2. Environment variables            (RATT_SMTP_HOST, RATT_PAYSTACK_SECRET, ...)

Values are read lazily, so saving new settings takes effect immediately
without restarting RATT.

Paystack (https://paystack.com) supports Ghana Mobile Money (MTN, Vodafone,
AirtelTigo) and cards. RATT uses Paystack's *hosted checkout*, so card /
MoMo credentials are typed on Paystack's page and never touch this app.
"""
import json
import os
from typing import Dict

_FILE = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "RATT", "services.json")

# key -> (env var, default)
_SPEC = {
    "SMTP_HOST":           ("RATT_SMTP_HOST", "smtp.gmail.com"),
    "SMTP_PORT":           ("RATT_SMTP_PORT", "587"),
    "SMTP_USER":           ("RATT_SMTP_USER", ""),
    "SMTP_PASS":           ("RATT_SMTP_PASS", ""),
    "SMTP_FROM":           ("RATT_SMTP_FROM", ""),
    "PAYSTACK_SECRET_KEY": ("RATT_PAYSTACK_SECRET", ""),
    "PAYSTACK_PUBLIC_KEY": ("RATT_PAYSTACK_PUBLIC", ""),
    "GOOGLE_TRANSLATE_KEY": ("RATT_GOOGLE_TRANSLATE_KEY", ""),
    "PAYSTACK_CALLBACK":   ("RATT_PAYSTACK_CALLBACK", "https://ratt.cybrox.inc/payment/callback"),
}

PAYSTACK_BASE_URL = "https://api.paystack.co"
PAYSTACK_CURRENCY = "GHS"
SMTP_USE_TLS = True


def _load_file() -> Dict[str, str]:
    try:
        with open(_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_value(key: str) -> str:
    env, default = _SPEC[key]
    val = _load_file().get(key)
    if val in (None, ""):
        val = os.environ.get(env, "")
    if val in (None, ""):
        val = default
    return str(val)


def __getattr__(name):  # PEP 562: dynamic module attributes
    if name in _SPEC:
        if name == "SMTP_PORT":
            try:
                return int(get_value(name))
            except ValueError:
                return 587
        if name == "SMTP_FROM":
            v = get_value(name)
            return v or f"RATT by Cybrox.Inc <{get_value('SMTP_USER')}>"
        return get_value(name)
    raise AttributeError(name)


def save_services(values: Dict[str, str]) -> None:
    """Persist service settings (blank values keep the existing value)."""
    current = _load_file()
    for k, v in values.items():
        if k in _SPEC and v is not None and str(v).strip() != "":
            current[k] = str(v).strip()
    os.makedirs(os.path.dirname(_FILE), exist_ok=True)
    with open(_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    try:  # best effort: keep the secrets file private to the current user
        os.chmod(_FILE, 0o600)
    except Exception:
        pass


def smtp_configured() -> bool:
    return bool(get_value("SMTP_HOST") and get_value("SMTP_USER") and get_value("SMTP_PASS"))


def payment_configured() -> bool:
    sk, pk = get_value("PAYSTACK_SECRET_KEY"), get_value("PAYSTACK_PUBLIC_KEY")
    return sk.startswith("sk_") and pk.startswith("pk_")


def get_config_status() -> dict:
    sk = get_value("PAYSTACK_SECRET_KEY")
    if payment_configured():
        mode = "LIVE" if sk.startswith("sk_live") else "TEST"
    else:
        mode = "DEMO (not configured)"
    return {
        "smtp": smtp_configured(),
        "smtp_host": get_value("SMTP_HOST") if smtp_configured() else "Not configured",
        "smtp_user": get_value("SMTP_USER") if smtp_configured() else "",
        "payment": payment_configured(),
        "payment_mode": mode,
    }
