"""RATT Payment Gateway (Paystack).

Handles secure payment processing via Paystack API.
Supports: Mobile Money (MTN, Vodafone, AirtelTigo) and Cards in GHS.

Docs: https://paystack.com/docs/api/
"""
import json
import urllib.request
import urllib.error
from typing import Optional


class PaystackGateway:
    """Paystack payment gateway integration."""
    
    def __init__(self):
        from ratt.api_config import PAYSTACK_SECRET_KEY, PAYSTACK_BASE_URL, PAYSTACK_CURRENCY, PAYSTACK_CALLBACK
        self.secret_key = PAYSTACK_SECRET_KEY
        self.base_url = PAYSTACK_BASE_URL
        self.currency = PAYSTACK_CURRENCY
        self.callback_url = PAYSTACK_CALLBACK
    
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }
    
    def _post(self, endpoint: str, data: dict) -> dict:
        url = f"{self.base_url}/{endpoint}"
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            return json.loads(body) if body else {"status": False, "message": str(e)}
    
    def _get(self, endpoint: str) -> dict:
        url = f"{self.base_url}/{endpoint}"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"status": False, "message": str(e)}
    
    def initialize_transaction(self, email: str, amount_ghs: float, metadata: dict = None) -> dict:
        """
        Initialize a Paystack transaction.
        Returns authorization_url to open in browser, and reference for verification.
        Amount is in GHS (converted to pesewas: 1 GHS = 100 pesewas).
        """
        amount_pesewas = int(amount_ghs * 100)
        payload = {
            "email": email,
            "amount": amount_pesewas,
            "currency": self.currency,
            "callback_url": self.callback_url,
            "metadata": metadata or {},
        }
        result = self._post("transaction/initialize", payload)
        return result
    
    def verify_transaction(self, reference: str) -> dict:
        """Verify a transaction by reference. Returns status and amount paid."""
        return self._get(f"transaction/verify/{reference}")
    
    def charge_mobile_money(self, email: str, amount_ghs: float, phone: str,
                             provider: str, metadata: dict = None) -> dict:
        """
        Charge Mobile Money directly.
        provider: 'mtn', 'vod' (Vodafone), 'tgo' (AirtelTigo)
        """
        amount_pesewas = int(amount_ghs * 100)
        payload = {
            "email": email,
            "amount": amount_pesewas,
            "currency": self.currency,
            "mobile_money": {
                "phone": phone,
                "provider": provider,
            },
            "metadata": metadata or {},
        }
        return self._post("charge", payload)
    
    def is_configured(self) -> bool:
        from ratt.api_config import payment_configured
        return payment_configured()


# Module-level singleton
_gateway: Optional[PaystackGateway] = None


def get_gateway() -> PaystackGateway:
    global _gateway
    if _gateway is None:
        _gateway = PaystackGateway()
    return _gateway


def demo_payment(amount_ghs: float, plan: str) -> dict:
    """Simulate a successful payment for demo/testing."""
    import secrets
    return {
        "status": True,
        "message": "Demo payment successful",
        "data": {
            "reference": f"RATT_DEMO_{secrets.token_hex(8).upper()}",
            "amount": int(amount_ghs * 100),
            "currency": "GHS",
            "plan": plan,
            "gateway": "DEMO",
        }
    }
