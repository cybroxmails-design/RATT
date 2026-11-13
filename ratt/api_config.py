"""Cybrox Cloud API and service configuration.

All billing and account operations are handled by the Cybrox Cloud service.
Client-side settings are stored in `%APPDATA%\\RATT\\services.json` protected with DPAPI.
"""
import base64
import json
import os
from typing import Dict

_FILE = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "RATT", "services.json")

_SPEC = {
    "CYBROX_BACKEND_URL":   ("RATT_BACKEND_URL", "https://api.cybrox.com/v1"),
    "CYBROX_API_TOKEN":     ("RATT_BACKEND_TOKEN", ""),
    "GOOGLE_TRANSLATE_KEY": ("RATT_GOOGLE_TRANSLATE_KEY", ""),
}

_SECRET_KEYS = {"CYBROX_API_TOKEN", "GOOGLE_TRANSLATE_KEY"}


def _encrypt_val(val: str) -> str:
    from ratt.config import AppConfig
    enc = AppConfig._dpapi_protect(val.encode("utf-8"))
    return "dpapi:" + base64.b64encode(enc).decode("ascii")


def _decrypt_val(val: str) -> str:
    if not isinstance(val, str) or not val.startswith("dpapi:"):
        return str(val or "")
    from ratt.config import AppConfig
    try:
        raw = base64.b64decode(val[6:].encode("ascii"))
        dec = AppConfig._dpapi_unprotect(raw)
        return dec.decode("utf-8") if dec is not None else ""
    except Exception:
        return ""


def _load_file() -> Dict[str, str]:
    try:
        with open(_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return {k: (_decrypt_val(v) if k in _SECRET_KEYS else v) for k, v in data.items() if k in _SPEC}
    except Exception:
        return {}


def get_value(key: str) -> str:
    if key not in _SPEC:
        return ""
    env, default = _SPEC[key]
    val = _load_file().get(key)
    if not val:
        val = os.environ.get(env, "")
    return str(val or default)


def __getattr__(name: str):
    if name in _SPEC:
        return get_value(name)
    raise AttributeError(name)


def save_services(values: Dict[str, str]) -> None:
    """Save DPAPI-protected service configuration atomically."""
    current = _load_file()
    for k, v in values.items():
        if k in _SPEC and v is not None and str(v).strip():
            current[k] = str(v).strip()
    to_disk = {
        k: (_encrypt_val(v) if (k in _SECRET_KEYS and v) else v)
        for k, v in current.items()
    }
    os.makedirs(os.path.dirname(_FILE), exist_ok=True)
    tmp_path = f"{_FILE}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(to_disk, f, indent=2)
    os.replace(tmp_path, _FILE)
    try:
        os.chmod(_FILE, 0o600)
    except OSError:
        pass


def is_production_configured() -> bool:
    """Return True when a live Cybrox Cloud API token is configured."""
    return bool(get_value("CYBROX_API_TOKEN"))


def payment_configured() -> bool:
    return is_production_configured()
