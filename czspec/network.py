"""Runtime network policy for CZSpec.

The public application can be used without Internet access.  Online-only
features consult this module before contacting external services.
"""

from __future__ import annotations

import os

PROJECT_URL = "https://github.com/Corzo2347/CZSpec"


class OfflineModeError(RuntimeError):
    """Raised when an online-only operation is requested in offline mode."""


def online_enabled() -> bool:
    value = str(os.environ.get("CZSPEC_ONLINE", "1") or "1").strip().lower()
    return value not in {"0", "false", "off", "no"}


def require_online(feature: str = "This feature") -> None:
    if not online_enabled():
        raise OfflineModeError(
            f"{feature} requires Internet access, but CZSpec is in Offline mode."
        )
