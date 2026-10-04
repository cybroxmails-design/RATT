"""RATT Email Verification Module.

Handles sending verification emails with a secure token link.
Uses Python's smtplib with a configurable SMTP server.

Phase 1: Simulated (logs token locally, shows it to user to confirm).
Phase 2: Real SMTP integration with Cybrox.Inc mail server.
"""
import secrets
import hashlib
import threading
import smtplib
import ssl
from datetime import datetime, timedelta
from typing import Optional, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# In-memory store of pending verifications: token -> {email, name, expires_at}
_pending: Dict[str, dict] = {}

# RATT mail configuration (Phase 2: replace with real server)
SMTP_FROM = "noreply@ratt.cybrox.inc"
SMTP_DISPLAY = "RATT by Cybrox.Inc"
TOKEN_EXPIRY_MINUTES = 30


def generate_token() -> str:
    """Generate a secure 6-digit numeric verification code."""
    return str(secrets.randbelow(900000) + 100000)


def create_verification(email: str, name: str) -> str:
    """
    Create a verification entry and return the token.
    Token expires in 30 minutes.
    """
    token = generate_token()
    expires = datetime.now() + timedelta(minutes=TOKEN_EXPIRY_MINUTES)
    _pending[token] = {
        "email": email.lower().strip(),
        "name": name,
        "expires_at": expires,
        "verified": False,
    }
    return token


def verify_token(token: str, email: str) -> tuple:
    """
    Verify a token for the given email.
    Returns (success: bool, message: str)
    """
    token = token.strip()
    email = email.lower().strip()
    
    entry = _pending.get(token)
    if not entry:
        return False, "Invalid verification code. Please check and try again."
    
    if entry["email"] != email:
        return False, "This code does not match your email address."
    
    if datetime.now() > entry["expires_at"]:
        _pending.pop(token, None)
        return False, "This code has expired. Please request a new one."
    
    if entry.get("verified"):
        return False, "This code has already been used."
    
    # Mark as verified
    entry["verified"] = True
    _pending.pop(token, None)
    return True, "Email verified successfully!"


def send_verification_email(email: str, name: str, token: str) -> tuple:
    """
    Send a verification email to the user.
    
    Phase 1: Simulated — returns True with token for display.
    Phase 2: Real SMTP sending to the user's email.
    
    Returns (success: bool, message: str)
    """
    # Build the email body
    body_html = f"""
<!DOCTYPE html>
<html>
<body style="font-family: 'Segoe UI', sans-serif; background: #0D1117; color: #E6EDF3; margin: 0; padding: 20px;">
  <div style="max-width: 480px; margin: 0 auto; background: #161B22; border-radius: 12px; padding: 32px;">
    <div style="text-align: center; margin-bottom: 24px;">
      <h1 style="color: #00BFFF; font-size: 28px; margin: 0;">RATT</h1>
      <p style="color: #8B949E; font-size: 13px; margin: 4px 0 0;">Rapid Access To Text &mdash; by Cybrox.Inc</p>
    </div>

    <h2 style="color: #E6EDF3; font-size: 18px;">Verify your email address</h2>

    <p style="color: #8B949E;">Hi {name},</p>
    <p style="color: #8B949E;">Thank you for signing up for RATT! Please use the verification code below to activate your account.</p>

    <div style="background: #0D2137; border-radius: 8px; padding: 24px; text-align: center; margin: 24px 0;">
      <p style="color: #8B949E; font-size: 13px; margin: 0 0 8px;">Your verification code</p>
      <p style="color: #00BFFF; font-size: 40px; font-weight: bold; letter-spacing: 12px; margin: 0;">{token}</p>
      <p style="color: #8B949E; font-size: 12px; margin: 8px 0 0;">Expires in {TOKEN_EXPIRY_MINUTES} minutes</p>
    </div>

    <p style="color: #8B949E; font-size: 13px;">
      Enter this code in the RATT app to verify your account and start using all features.
    </p>
    <p style="color: #8B949E; font-size: 12px; margin-top: 24px; border-top: 1px solid #21262D; padding-top: 16px;">
      If you did not create a RATT account, you can safely ignore this email.
      <br>&copy; {datetime.now().year} Cybrox.Inc. All rights reserved.
    </p>
  </div>
</body>
</html>
"""

    body_text = f"""
RATT — Rapid Access To Text (by Cybrox.Inc)

Hi {name},

Your RATT email verification code is:

    {token}

This code expires in {TOKEN_EXPIRY_MINUTES} minutes.

Enter this code in the RATT app to verify your account.

If you did not create a RATT account, ignore this email.
"""

    # Real SMTP when configured; otherwise demo mode (code shown on screen).
    from ratt.api_config import smtp_configured
    if not smtp_configured():
        return True, f"[DEMO] Code: {token}\n(Add SMTP settings in Settings > Configure Services to email codes)"
    try:
        _send_real_email(email, name, token, body_html, body_text)
        return True, f"Verification code sent to {email}"
    except Exception as e:
        # SMTP is configured but failed: NEVER reveal the code on screen,
        # otherwise the email check could be bypassed.
        return False, f"Could not send the verification email ({e}). Check Settings > Configure Services."


def _send_real_email(to_email: str, name: str, token: str, html: str, plain: str):
    """Send the actual email via SMTP. Configured via ratt.api_config."""
    from ratt.api_config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM, smtp_configured

    if not smtp_configured():
        raise RuntimeError("SMTP not configured")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your RATT account" if token != "TEST" else "RATT test email"
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    context = ssl.create_default_context()
    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=20) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
