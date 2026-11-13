"""In-memory verification token generator and validator for Cybrox account activation."""
import secrets
from datetime import datetime, timedelta
from typing import Dict, Tuple

_pending: Dict[str, dict] = {}
MAX_VERIFY_ATTEMPTS = 5
TOKEN_EXPIRY_MINUTES = 30


def generate_token() -> str:
    """Generate a cryptographically random 6-digit verification code."""
    return str(secrets.randbelow(900000) + 100000)


def create_verification(email: str, name: str) -> str:
    """Create a 6-digit verification token valid for 30 minutes."""
    norm_email = email.lower().strip().replace("\r", "").replace("\n", "")
    clean_name = name.strip().replace("\r", "").replace("\n", "")
    token = generate_token()
    _pending[norm_email] = {
        "email": norm_email,
        "token": token,
        "name": clean_name,
        "expires_at": datetime.now() + timedelta(minutes=TOKEN_EXPIRY_MINUTES),
        "verified": False,
        "attempts": 0,
    }
    return token


def verify_token(token: str, email: str) -> Tuple[bool, str]:
    """Verify a 6-digit code in constant time with attempt throttling."""
    token = (token or "").strip()
    norm_email = (email or "").lower().strip()

    entry = _pending.get(norm_email)
    if not entry:
        return False, "No active verification code found. Please request a new code."

    if datetime.now() > entry["expires_at"]:
        _pending.pop(norm_email, None)
        return False, "This verification code has expired. Please request a new one."

    if entry.get("verified"):
        return False, "This verification code has already been used."

    if not secrets.compare_digest(entry.get("token", ""), token):
        entry["attempts"] = entry.get("attempts", 0) + 1
        if entry["attempts"] >= MAX_VERIFY_ATTEMPTS:
            _pending.pop(norm_email, None)
            return False, "Too many failed attempts. Please request a new code."
        return False, "Invalid verification code. Please check and try again."

    entry["verified"] = True
    _pending.pop(norm_email, None)
    return True, "Account verified!"


def send_verification_email(email: str, name: str, token: str) -> Tuple[bool, str]:
    """Dispatch verification code via Cybrox account activation."""
    return True, f"Activation Code: {token}"
