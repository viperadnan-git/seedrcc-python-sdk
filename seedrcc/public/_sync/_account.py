# This file is auto-generated — do not edit directly.
# Regenerate with: python scripts/generate_sync.py
"""AccountMixin — one-shot staticmethod wrappers over `CookieSession`.

Every method here opens a transient `CookieSession(username, password)`,
performs a single operation, and closes the session. Convenient for one-off
CLI-style usage.

For batch workloads that make multiple cookie-gated calls in a row, use
`Seedr.cookie_session(...)` directly so the cookie login (and any CSRF
scrape) is paid once instead of per call.
"""

from typing import List, Optional, Union

import httpx

from .. import _constants, models
from ..token import Token
from ._cookie_session import CookieSession


class AccountMixin:
    # ── PATs ────────────────────────────────────────────────────────────────

    @staticmethod
    def list_pats(
        username: str,
        password: str,
        httpx_client: Optional[httpx.Client] = None,
    ) -> List[models.PersonalAccessToken]:
        """GET /api/v0.1/account/pats via cookie login."""
        with CookieSession(username, password, httpx_client=httpx_client) as sess:
            return sess.list_pats()

    @staticmethod
    def create_pat(
        username: str,
        password: str,
        name: str = "default",
        scopes: Union[str, List[str]] = _constants.ALL_SCOPES,
        expires_in: int = 0,
        httpx_client: Optional[httpx.Client] = None,
    ) -> models.PersonalAccessTokenCreated:
        """POST /api/v0.1/account/pats. The `token` value is only returned once."""
        with CookieSession(username, password, httpx_client=httpx_client) as sess:
            return sess.create_pat(name=name, scopes=scopes, expires_in=expires_in)

    @staticmethod
    def revoke_pat(
        username: str,
        password: str,
        token_hash: str,
        httpx_client: Optional[httpx.Client] = None,
    ) -> None:
        """DELETE /api/v0.1/account/pats/{token_hash}."""
        with CookieSession(username, password, httpx_client=httpx_client) as sess:
            sess.revoke_pat(token_hash)

    # ── Authorized devices ──────────────────────────────────────────────────

    @staticmethod
    def list_devices(
        username: str,
        password: str,
        httpx_client: Optional[httpx.Client] = None,
    ) -> List[models.AuthorizedDevice]:
        """List authorized OAuth devices (scraped from the console page)."""
        with CookieSession(username, password, httpx_client=httpx_client) as sess:
            return sess.list_devices()

    @staticmethod
    def revoke_device(
        username: str,
        password: str,
        device_code: str,
        httpx_client: Optional[httpx.Client] = None,
    ) -> None:
        """Revoke an authorized device by its `device_code`."""
        with CookieSession(username, password, httpx_client=httpx_client) as sess:
            sess.revoke_device(device_code)

    # ── Onboarding + device flow ────────────────────────────────────────────

    @staticmethod
    def accept_terms(
        username: str,
        password: str,
        newsletter: bool = False,
        httpx_client: Optional[httpx.Client] = None,
    ) -> models.TermsAcceptance:
        """POST /api/v0.1/me/accept-terms — onboarding terms + newsletter opt-in."""
        with CookieSession(username, password, httpx_client=httpx_client) as sess:
            return sess.accept_terms(newsletter=newsletter)

    @staticmethod
    def run_device_flow(
        username: str,
        password: str,
        client_id: str = _constants.DEFAULT_CLIENT_ID,
        scope: str = _constants.DEFAULT_SCOPE,
        httpx_client: Optional[httpx.Client] = None,
    ) -> Token:
        """Run the headless OAuth device flow — registers a new authorized device."""
        with CookieSession(username, password, httpx_client=httpx_client) as sess:
            return sess.run_device_flow(client_id=client_id, scope=scope)
