"""Cybrox Cloud Billing client for Premium and Enterprise subscriptions."""
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from ratt.api_config import get_value, is_production_configured


_ALLOWED_BILLING_HOSTS = frozenset({"api.cybrox.com", "cybrox.com", "www.cybrox.com", "ratt.cybrox.com"})


def _validated_https_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or host not in _ALLOWED_BILLING_HOSTS:
        raise ValueError("Billing endpoint must use an authorized Cybrox HTTPS host.")
    return url.strip().rstrip("/")


def initialize_checkout(plan_id: str, email: str, amount_ghs: float = 0.0, metadata: dict = None) -> dict:
    if not is_production_configured():
        return demo_payment(amount_ghs, plan_id)
    backend_url = _validated_https_url(get_value("CYBROX_BACKEND_URL"))
    payload = {
        "plan": plan_id,
        "email": email,
        "amount_ghs": amount_ghs,
        "metadata": metadata or {},
    }
    req = urllib.request.Request(
        f"{backend_url}/billing/checkout",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


class CybroxBillingGateway:
    """Client for the Cybrox Cloud Billing API."""

    def __init__(self):
        self.base_url = get_value("CYBROX_BACKEND_URL").rstrip("/")
        self.currency = "GHS"

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        token = get_value("CYBROX_API_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _get(self, endpoint: str) -> dict:
        try:
            base = _validated_https_url(get_value("CYBROX_BACKEND_URL"))
            req = urllib.request.Request(f"{base}/{endpoint}", headers=self._headers(), method="GET")
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"status": False, "message": str(e)}

    def initialize_transaction(self, email: str, amount_ghs: float, metadata: dict = None) -> dict:
        plan = (metadata or {}).get("plan", "premium")
        if not self.is_configured():
            return demo_payment(amount_ghs, plan)
        try:
            return initialize_checkout(plan, email, amount_ghs=amount_ghs, metadata=metadata)
        except Exception as e:
            return {"status": False, "message": str(e)}

    def verify_transaction(self, reference: str) -> dict:
        safe_ref = urllib.parse.quote(reference.strip(), safe="")
        return self._get(f"billing/verify/{safe_ref}")

    def is_configured(self) -> bool:
        return is_production_configured()


_gateway: Optional[CybroxBillingGateway] = None


def get_gateway() -> CybroxBillingGateway:
    global _gateway
    if _gateway is None:
        _gateway = CybroxBillingGateway()
    return _gateway


def demo_payment(amount_ghs: float, plan: str) -> dict:
    return {
        "status": True,
        "message": "Subscription activated",
        "data": {
            "reference": f"CYB_{secrets.token_hex(8).upper()}",
            "amount": int(amount_ghs * 100),
            "currency": "GHS",
            "plan": plan,
            "gateway": "CYBROX",
        },
    }
