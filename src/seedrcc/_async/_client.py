"""Composed Seedr public API client."""

from typing import Dict, Optional

import httpx

from ._account import AsyncAccountMixin
from ._auth import AsyncAuthMixin
from ._base import AsyncBaseClient
from ._cookie_session import AsyncCookieSession
from ._files import AsyncFilesMixin
from ._media import AsyncMediaMixin
from ._shortcuts import AsyncShortcutsMixin
from ._tasks import AsyncTasksMixin
from ._user import AsyncUserMixin


class AsyncSeedr(  # pyright: ignore[reportUnsafeMultipleInheritance]
    AsyncAuthMixin,
    AsyncUserMixin,
    AsyncFilesMixin,
    AsyncTasksMixin,
    AsyncMediaMixin,
    AsyncAccountMixin,
    AsyncShortcutsMixin,
    AsyncBaseClient,
):
    """Asynchronous client for the Seedr public API.

    Example:
        ```python
        import asyncio
        from seedrcc import AsyncSeedr

        async def main():
            # First run: mint token via full headless flow, persist to .cache/seedr_token.json
            async with await AsyncSeedr.from_credentials("user", "pass") as client:
                user = await client.get_user()
                print(user.username)

            # Subsequent runs: auto-load from .cache/seedr_token.json, auto-refresh on expiry
            async with AsyncSeedr() as client:
                quota = await client.get_quota()
                print(f"{quota.space_used}/{quota.space_max}")

        asyncio.run(main())
        ```

    """

    @staticmethod
    def cookie_session(
        username: Optional[str] = None,
        password: Optional[str] = None,
        *,
        cookies: Optional[Dict[str, str]] = None,
        httpx_client: Optional[httpx.AsyncClient] = None,
    ) -> AsyncCookieSession:
        """Shared cookie session for PAT + device management.

        Logs in and scrapes the CSRF token once on first use; every subsequent
        method call reuses that state. Use as a context manager:

            async with AsyncSeedr.cookie_session(email, password) as sess:
                devices = await sess.list_devices()
                pats = await sess.list_pats()
                await sess.revoke_device(code)
        """
        return AsyncCookieSession(
            username, password, cookies=cookies, httpx_client=httpx_client
        )
