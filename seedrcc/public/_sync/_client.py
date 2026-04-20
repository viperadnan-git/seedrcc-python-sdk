# This file is auto-generated — do not edit directly.
# Regenerate with: python scripts/generate_sync.py
"""Seedr — the composed synchronous client."""

from typing import Dict, Optional

import httpx

from ._account import AccountMixin
from ._auth import AuthMixin
from ._base import BaseClient
from ._cookie_session import CookieSession
from ._files import FilesMixin
from ._media import MediaMixin
from ._shortcuts import ShortcutsMixin
from ._tasks import TasksMixin
from ._user import UserMixin


class Seedr(  # pyright: ignore[reportUnsafeMultipleInheritance]
    AuthMixin,
    UserMixin,
    FilesMixin,
    TasksMixin,
    MediaMixin,
    AccountMixin,
    ShortcutsMixin,
    BaseClient,
):
    """Synchronous client for the Seedr public API.

    Example:
        ```python
        from seedrcc.public import Seedr

        # First run: mint token via full headless flow, persist to .cache/seedr_token.json
        with Seedr.from_credentials("user", "pass") as client:
            user = client.get_user()
            print(user.username)

        # Subsequent runs: auto-load from .cache/seedr_token.json, auto-refresh on expiry
        with Seedr() as client:
            quota = client.get_quota()
            print(f"{quota.space_used}/{quota.space_max}")
        ```
    """

    @staticmethod
    def cookie_session(
        username: Optional[str] = None,
        password: Optional[str] = None,
        *,
        cookies: Optional[Dict[str, str]] = None,
        httpx_client: Optional[httpx.Client] = None,
    ) -> CookieSession:
        """Shared cookie session for PAT + device management.

        Logs in and scrapes the CSRF token once on first use; every subsequent
        method call reuses that state. Use as an async context manager:

            with Seedr.cookie_session(email, password) as sess:
                devices = sess.list_devices()
                pats = sess.list_pats()
                sess.revoke_device(code)
        """
        return CookieSession(
            username, password, cookies=cookies, httpx_client=httpx_client
        )
