# DO NOT EDIT — generated from seedrcc/public/_async/_cookie_session.py by scripts/gen_sync.py.
# Run `python scripts/gen_sync.py` (or rebuild the package) to regenerate.

"""CookieSession — shared cookie login for PAT and device management.

Session lifecycle is split into two idempotent steps:
- `_ensure_logged_in` — cookie login only; required by every method.
- `_ensure_csrf` — logs in if needed, then scrapes the header CSRF token
  from `/console/documentation`. Only called by methods that need the CSRF
  header (PATs); device methods use the form-scoped CSRF embedded in the
  console HTML and don't hit this path.

Example:
    with Seedr.cookie_session(email, password) as sess:
        devices = sess.list_devices()
        pats = sess.list_pats()
        sess.revoke_device(code)
"""

import re
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import parse_qs, urlparse

import httpx

from ...exceptions import APIError, AuthenticationError
from .. import _constants, _request_models, models
from ..token import Token
from ._auth import AuthMixin
from ._http import make_http_request

# Each authorized device is rendered as:
#   <h5 class="mb-1">Kodi</h5>
#   <small class="text-muted">Device Code: ...hdGqeO</small><br>
#   <small class="text-muted">First authorized: Apr 17, 2026 10:05</small><br>
#   <small class="text-muted">Last used: Apr 17, 2026 10:05</small>
#   <form action="/api/v0.1/developer/devices/<device_code>/revoke" ...>
#     <input type="hidden" name="_csrf_token" value="<csrf>">
_DEVICE_ROW_RE = re.compile(
    r'<h5 class="mb-1">(?P<name>[^<]+)</h5>.*?'
    r"First authorized:\s*(?P<first>[^<]+)</small>.*?"
    r"Last used:\s*(?P<last>[^<]+)</small>.*?"
    r'action="/api/v0\.1/developer/devices/(?P<code>[^/]+)/revoke"',
    re.DOTALL,
)

_REVOKE_FORM_RE = re.compile(
    r'<form action="/api/v0\.1/developer/devices/(?P<code>[^/]+)/revoke"[^>]*>\s*'
    r'<input type="hidden" name="_csrf_token" value="(?P<csrf>[a-f0-9]+)">',
)


def cookie_login(client: httpx.Client, username: str, password: str) -> None:
    """POST /auth/login — populates `client.cookies` in place."""
    payload = _request_models.CookieLoginRequest(
        username=username, password=password
    ).model_dump(exclude_none=True)
    response = make_http_request(
        client,
        "post",
        _constants.COOKIE_LOGIN_URL,
        json=payload,
        headers=_constants.BROWSER_HEADERS,
    )
    if not response.is_success:
        raise AuthenticationError("Cookie authentication failed.", response=response)
    cookies = {c.name: c.value for c in response.cookies.jar if c.value is not None}
    if not cookies:
        raise AuthenticationError(
            "No cookies received from login response.", response=response
        )
    client.cookies.clear()
    client.cookies.update(cookies)


class CookieSession:
    """Reusable authenticated cookie session for cookie-gated endpoints.

    Accepts any one of (in priority order):
      1. `cookies` dict — attached to the client as-is (no login).
      2. `username` + `password` — `cookie_login` runs on first use.
      3. `httpx_client` that already carries session cookies — verified on
         first use; raises `AuthenticationError` if its cookie jar is empty.

    Raises `AuthenticationError` on construction if none of the above are provided.
    Login/cookie-attach happens lazily on first use; CSRF scrape happens once,
    only when a method that needs it runs. Use as a context manager.
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        *,
        cookies: Optional[Dict[str, str]] = None,
        httpx_client: Optional[httpx.Client] = None,
    ) -> None:
        if not cookies and not (username and password) and httpx_client is None:
            raise AuthenticationError(
                "CookieSession requires one of: cookies, "
                "username+password, or a pre-authenticated httpx_client."
            )
        self._username = username
        self._password = password
        self._cookies = cookies
        self._client = httpx_client or httpx.Client()
        self._owns_client = httpx_client is None
        self._logged_in = False
        self._csrf_token: Optional[str] = None

    def __enter__(self) -> "CookieSession":
        self._ensure_logged_in()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    @property
    def cookies(self) -> Dict[str, str]:
        """Snapshot of the session's cookie jar as a plain dict."""
        return dict(self._client.cookies)

    # ── Session bootstrap (idempotent) ──────────────────────────────────────

    def _ensure_logged_in(self) -> None:
        if self._logged_in:
            return
        if self._cookies:
            self._client.cookies.update(self._cookies)
        elif self._username and self._password:
            cookie_login(self._client, self._username, self._password)
        elif not self._client.cookies:
            raise AuthenticationError(
                "CookieSession received only httpx_client but it has no cookies."
            )
        self._logged_in = True

    def _ensure_csrf(self) -> None:
        self._ensure_logged_in()
        if self._csrf_token is not None:
            return
        response = make_http_request(
            self._client,
            "get",
            _constants.CSRF_SOURCE_URL,
            headers=_constants.BROWSER_HEADERS,
        )
        if not response.is_success:
            raise AuthenticationError(
                "Could not load CSRF source page.", response=response
            )
        match = re.search(r"csrfToken\s*=\s*['\"]([a-f0-9]+)['\"]", response.text)
        if not match:
            raise AuthenticationError(
                "Could not extract CSRF token.", response=response
            )
        self._csrf_token = match.group(1)

    def _api_headers(self) -> Dict[str, str]:
        assert self._csrf_token is not None
        return {
            **_constants.BROWSER_HEADERS,
            "x-csrf-token": self._csrf_token,
            "accept": "application/json",
        }

    # ── PATs (need header CSRF) ─────────────────────────────────────────────

    def list_pats(self) -> List[models.PersonalAccessToken]:
        """GET /api/v0.1/account/pats."""
        self._ensure_csrf()
        response = make_http_request(
            self._client, "get", _constants.PATS_URL, headers=self._api_headers()
        )
        if not response.is_success:
            raise APIError("Failed to list PATs.", response=response)
        payload = response.json()
        pats = payload.get("tokens", payload) if isinstance(payload, dict) else payload
        return [models.PersonalAccessToken.model_validate(p) for p in pats]

    def create_pat(
        self,
        name: str = "default",
        scopes: Union[str, List[str]] = _constants.ALL_SCOPES,
        expires_in: int = 0,
    ) -> models.PersonalAccessTokenCreated:
        """POST /api/v0.1/account/pats. The raw token is only returned here."""
        self._ensure_csrf()
        scope_list = scopes.split() if isinstance(scopes, str) else list(scopes)
        payload = _request_models.CreatePATRequest(
            name=name, scopes=scope_list, expires_in=expires_in
        ).model_dump(exclude_none=True)
        response = make_http_request(
            self._client,
            "post",
            _constants.PATS_URL,
            json=payload,
            headers=self._api_headers(),
        )
        if not response.is_success:
            raise APIError("Failed to create PAT.", response=response)
        return models.PersonalAccessTokenCreated.model_validate(response.json())

    def run_device_flow(
        self,
        client_id: str = _constants.DEFAULT_CLIENT_ID,
        scope: str = _constants.DEFAULT_SCOPE,
    ) -> Token:
        """Run the headless OAuth device flow using this cookie session.

        Delegates the mint (step 1) and exchange (step 4) to
        `AuthMixin.get_device_code` / `AuthMixin._poll_device_token`.
        The interactive approval (steps 2 + 3 — scraping the verify-page
        CSRF and POSTing `action=approve`) is unique to the cookie-session
        flavor and stays here. Registers a new authorized device on Seedr.
        """
        self._ensure_logged_in()

        # Step 1: mint device code (reuses AuthMixin primitive)
        dc = AuthMixin.get_device_code(client_id, scope, httpx_client=self._client)

        # Step 2: fetch verify page, scrape the form CSRF
        verify_url = f"{_constants.DEVICE_VERIFY_URL}?code={dc.user_code}"
        page = make_http_request(
            self._client, "get", verify_url, headers=_constants.BROWSER_HEADERS
        )
        if not page.is_success:
            raise AuthenticationError(
                "Could not load device verify page.", response=page
            )
        match = re.search(r'name="_csrf_token"\s+value="([a-f0-9]+)"', page.text)
        if not match:
            raise AuthenticationError(
                "Could not find CSRF token on verify page.", response=page
            )

        # Step 3: POST approve
        approve_resp = make_http_request(
            self._client,
            "post",
            _constants.DEVICE_VERIFY_URL,
            data={
                "code": dc.user_code,
                "_csrf_token": match.group(1),
                "action": "approve",
            },
            headers={**_constants.BROWSER_HEADERS, "referer": verify_url},
            follow_redirects=False,
        )
        location = approve_resp.headers.get("location", "")
        if approve_resp.status_code != 302 or not location.endswith("/approved"):
            error = (
                parse_qs(urlparse(location).query).get("error", [None])[0]
                or f"unexpected redirect: {location or '(no location header)'}"
            )
            raise AuthenticationError(
                f"Device approval failed: {error}", response=approve_resp
            )

        # Step 4: exchange device_code → token (reuses AuthMixin primitive)
        return AuthMixin._poll_device_token(
            self._client,
            dc.device_code,
            client_id,
            poll=False,
            interval=0,
            deadline=time.time() + 30,
        )

    def accept_terms(self, newsletter: bool = False) -> models.TermsAcceptance:
        """POST /api/v0.1/me/accept-terms — onboarding terms + newsletter opt-in.

        Cookie login only; no CSRF header required. The server persists state
        on first acceptance; subsequent calls return the stored record and
        ignore the `newsletter` arg.
        """
        self._ensure_logged_in()
        response = make_http_request(
            self._client,
            "post",
            _constants.ACCEPT_TERMS_URL,
            json={"newsletter": newsletter},
            headers={**_constants.BROWSER_HEADERS, "accept": "application/json"},
        )
        if not response.is_success:
            raise APIError("Failed to accept terms.", response=response)
        return models.TermsAcceptance.model_validate(response.json())

    def revoke_pat(self, token_hash: str) -> None:
        """DELETE /api/v0.1/account/pats/{token_hash}."""
        self._ensure_csrf()
        response = make_http_request(
            self._client,
            "delete",
            f"{_constants.PATS_URL}/{token_hash}",
            headers=self._api_headers(),
        )
        if not response.is_success:
            raise APIError("Failed to revoke PAT.", response=response)

    # ── Devices (use per-form CSRF; login only) ─────────────────────────────

    def _fetch_devices_html(self) -> str:
        self._ensure_logged_in()
        response = make_http_request(
            self._client,
            "get",
            _constants.DEVICES_CONSOLE_URL,
            headers=_constants.BROWSER_HEADERS,
        )
        if not response.is_success:
            raise AuthenticationError(
                "Could not load the devices console page.", response=response
            )
        return response.text

    def list_devices(self) -> List[models.AuthorizedDevice]:
        """Scrape the authorized-devices console page into `AuthorizedDevice`s."""
        html = self._fetch_devices_html()
        return [
            models.AuthorizedDevice(
                name=m.group("name").strip(),
                device_code=m.group("code"),
                first_authorized_at=m.group("first").strip(),
                last_used_at=m.group("last").strip(),
            )
            for m in _DEVICE_ROW_RE.finditer(html)
        ]

    def revoke_device(self, device_code: str) -> None:
        """Revoke an authorized device by its `device_code`.

        Re-fetches the console page to obtain the form-scoped CSRF token for
        the matching row, then POSTs to the revoke endpoint.
        """
        html = self._fetch_devices_html()
        csrf = None
        for m in _REVOKE_FORM_RE.finditer(html):
            if m.group("code") == device_code:
                csrf = m.group("csrf")
                break
        if csrf is None:
            raise APIError(f"No authorized device found for code={device_code}.")

        response = make_http_request(
            self._client,
            "post",
            _constants.DEVICE_REVOKE_URL_TEMPLATE.format(device_code=device_code),
            data={"_csrf_token": csrf},
            headers={
                **_constants.BROWSER_HEADERS,
                "content-type": "application/x-www-form-urlencoded",
            },
        )
        if not response.is_success:
            raise APIError("Failed to revoke device.", response=response)
