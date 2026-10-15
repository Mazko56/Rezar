"""Resolve the HTTPS URL for the admin Telegram Mini App.

Explicit MINIAPP_URL takes priority. RAILWAY_PUBLIC_DOMAIN is available on
Railway services that have Public Networking configured.
"""

import os
from urllib.parse import urlsplit


def get_miniapp_url() -> str | None:
    explicit = os.getenv("MINIAPP_URL", "").strip()
    if explicit:
        candidate = explicit
    else:
        domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
        if not domain:
            return None
        candidate = domain if "://" in domain else f"https://{domain}"

    parsed = urlsplit(candidate)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        return None
    # The app is served at the root path of the Railway service.
    if parsed.path not in ("", "/"):
        return None
    return f"https://{parsed.netloc}"
