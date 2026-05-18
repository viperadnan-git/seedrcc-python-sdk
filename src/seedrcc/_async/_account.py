"""AsyncAccountMixin — one-shot staticmethod wrappers over `AsyncCookieSession`.

Every method here opens a transient `AsyncCookieSession(username, password)`,
performs a single operation, and closes the session. Convenient for one-off
CLI-style usage.

For batch workloads that make multiple cookie-gated calls in a row, use
`AsyncSeedr.cookie_session(...)` directly so the cookie login (and any CSRF
scrape) is paid once instead of per call.
"""

from typing import List, Optional, Union

import httpx

from .. import constants, models
from ..token import Token
from ._cookie_session import AsyncCookieSession


class AsyncAccountMixin:
    # ── PATs ────────────────────────────────────────────────────────────────

    @staticmethod
    async def list_pats(
        username: str,
        password: str,
        httpx_client: Optional[httpx.AsyncClient] = None,
    ) -> List[models.PersonalAccessToken]:
        """GET /api/v0.1/account/pats via cookie login."""
        async with AsyncCookieSession(
            username, password, httpx_client=httpx_client
        ) as sess:
            return await sess.list_pats()

    @staticmethod
    async def create_pat(
        username: str,
        password: str,
        name: str = "default",
        scopes: Union[str, List[str]] = constants.ALL_SCOPES,
        expires_in: int = 0,
        httpx_client: Optional[httpx.AsyncClient] = None,
    ) -> models.PersonalAccessTokenCreated:
        """POST /api/v0.1/account/pats. The `token` value is only returned once."""
        async with AsyncCookieSession(
            username, password, httpx_client=httpx_client
        ) as sess:
            return await sess.create_pat(
                name=name, scopes=scopes, expires_in=expires_in
            )

    @staticmethod
    async def revoke_pat(
        username: str,
        password: str,
        token_hash: str,
        httpx_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """DELETE /api/v0.1/account/pats/{token_hash}."""
        async with AsyncCookieSession(
            username, password, httpx_client=httpx_client
        ) as sess:
            await sess.revoke_pat(token_hash)

    # ── Authorized devices ──────────────────────────────────────────────────

    @staticmethod
    async def list_devices(
        username: str,
        password: str,
        httpx_client: Optional[httpx.AsyncClient] = None,
    ) -> List[models.AuthorizedDevice]:
        """List authorized OAuth devices (scraped from the console page)."""
        async with AsyncCookieSession(
            username, password, httpx_client=httpx_client
        ) as sess:
            return await sess.list_devices()

    @staticmethod
    async def revoke_device(
        username: str,
        password: str,
        device_code: str,
        httpx_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """Revoke an authorized device by its `device_code`."""
        async with AsyncCookieSession(
            username, password, httpx_client=httpx_client
        ) as sess:
            await sess.revoke_device(device_code)

    # ── Onboarding + device flow ────────────────────────────────────────────

    @staticmethod
    async def accept_terms(
        username: str,
        password: str,
        newsletter: bool = False,
        httpx_client: Optional[httpx.AsyncClient] = None,
    ) -> models.TermsAcceptance:
        """POST /api/v0.1/me/accept-terms — onboarding terms + newsletter opt-in."""
        async with AsyncCookieSession(
            username, password, httpx_client=httpx_client
        ) as sess:
            return await sess.accept_terms(newsletter=newsletter)

    @staticmethod
    async def run_device_flow(
        username: str,
        password: str,
        client_id: str = constants.DEFAULT_CLIENT_ID,
        scope: str = constants.DEFAULT_SCOPE,
        httpx_client: Optional[httpx.AsyncClient] = None,
    ) -> Token:
        """Run the headless OAuth device flow — registers a new authorized device."""
        async with AsyncCookieSession(
            username, password, httpx_client=httpx_client
        ) as sess:
            return await sess.run_device_flow(client_id=client_id, scope=scope)
