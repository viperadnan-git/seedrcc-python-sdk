# DO NOT EDIT — generated from src/seedrcc/_async/_auth.py by scripts/gen_sync.py.
# Run `python scripts/gen_sync.py` (or rebuild the package) to regenerate.

"""Bearer-token factories, refresh + revoke, and `get_device_code` entry point.

Covers `from_pat`, `from_device_code`, refresh, revoke, and the public
`get_device_code` entry point.

Credential-creation flows that hit Seedr's cookie-auth surface (PATs,
headless device-flow against a cookie-authenticated client) live on
`CookieSession` in `_cookie_session.py`. Consumers decide whether to
mint a credential; the library never does it implicitly.
"""

import json
import time
from typing import Any, Callable, Dict, Optional, Type, TypeVar

import httpx

from .. import _request_models, constants, models
from ..errors import APIError, AuthenticationError, JSONDecodeAPIError
from ..token import Token
from ._http import make_http_request
from ._protocols import ClientProtocol
from ._token_handlers import FileTokenHandler, TokenHandler

TSelf = TypeVar("TSelf", bound="AuthMixin")


class AuthMixin:
    """Bearer-token factories + refresh/revoke + OAuth-app listing.

    Mixed into `Seedr` alongside `BaseClient`. Instance methods type
    `self` as `ClientProtocol` so the type-checker sees the BaseClient-
    provided attributes (`_token`, `_request`, etc.) without the mixin itself
    inheriting from the Protocol.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Cooperative init — forwards to the next class in MRO (`BaseClient`).

        Declared so that type-checkers see `cls(token=..., token_handler=...,
        httpx_client=..., ...)` calls inside factory classmethods as valid.
        """
        super().__init__(*args, **kwargs)

    # ── Public helpers ──────────────────────────────────────────────────────

    @staticmethod
    def get_device_code(
        client_id: str = constants.DEFAULT_CLIENT_ID,
        scope: str = constants.DEFAULT_SCOPE,
        httpx_client: Optional[httpx.Client] = None,
    ) -> models.DeviceCode:
        """Step 1 of the device-code flow.

        POSTs to `/oauth/device/code` and returns the `DeviceCode`. Direct
        the user to `code.verification_uri_complete` to approve; then pass
        the `device_code` to `Seedr.from_device_code`.
        """
        payload = _request_models.DeviceCodeRequest(client_id=client_id, scope=scope)
        owns_client = httpx_client is None
        client = httpx_client or httpx.Client()
        try:
            response = make_http_request(
                client,
                "post",
                constants.DEVICE_CODE_URL,
                data=payload.model_dump(exclude_none=True),
            )
            if not response.is_success:
                raise APIError("Failed to get device code.", response=response)
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise JSONDecodeAPIError(response=response) from e
            return models.DeviceCode.model_validate(data)
        finally:
            if owns_client:
                client.close()

    # ── Factories ───────────────────────────────────────────────────────────

    @classmethod
    def _finalize_auth(
        cls: Type[TSelf],
        token_fetch: Callable[[httpx.Client], Token],
        *,
        token_handler: Optional[TokenHandler] = None,
        httpx_client: Optional[httpx.Client] = None,
        timeout: float = 30.0,
        proxy: Optional[Dict[str, str]] = None,
        **httpx_kwargs: Any,
    ) -> TSelf:
        """Build httpx client, run `token_fetch`, persist, and construct.

        Shared tail for factory classmethods. Closes the client if we built it
        and `token_fetch` raised.
        """
        httpx_kwargs.setdefault("timeout", timeout)
        httpx_kwargs.setdefault("proxy", proxy)
        client = httpx_client or httpx.Client(**httpx_kwargs)
        try:
            token = token_fetch(client)
        except BaseException:
            if httpx_client is None:
                client.close()
            raise
        handler = token_handler or FileTokenHandler()
        handler.save(token)
        return cls(
            token=token,
            token_handler=handler,
            httpx_client=client,
            **httpx_kwargs,
        )

    @classmethod
    def from_device_code(
        cls: Type[TSelf],
        device_code: str,
        client_id: str = constants.DEFAULT_CLIENT_ID,
        *,
        poll: bool = True,
        interval: float = 5.0,
        timeout_seconds: float = 600.0,
        token_handler: Optional[TokenHandler] = None,
        httpx_client: Optional[httpx.Client] = None,
        timeout: float = 30.0,
        proxy: Optional[Dict[str, str]] = None,
        **httpx_kwargs: Any,
    ) -> TSelf:
        """Step 2 of the device-code flow.

        Exchanges an already-obtained `device_code` for a bearer `Token`.
        If `poll=True` (default), polls until the user approves or
        `timeout_seconds` elapses. If `poll=False`, raises immediately on
        `authorization_pending`. Does NOT register a new device on Seedr —
        the caller obtained the device_code in a prior `get_device_code` call.
        """
        deadline = time.time() + timeout_seconds

        def fetch(client: httpx.Client) -> Token:
            return cls._poll_device_token(
                client, device_code, client_id, poll, interval, deadline
            )

        return cls._finalize_auth(
            fetch,
            token_handler=token_handler,
            httpx_client=httpx_client,
            timeout=timeout,
            proxy=proxy,
            **httpx_kwargs,
        )

    @classmethod
    def from_token(
        cls: Type[TSelf],
        token: Token,
        *,
        token_handler: Optional[TokenHandler] = None,
        httpx_client: Optional[httpx.Client] = None,
        timeout: float = 30.0,
        proxy: Optional[Dict[str, str]] = None,
        **httpx_kwargs: Any,
    ) -> TSelf:
        """Construct a client from an existing `Token`.

        Thin factory over the `Seedr(token=…)` constructor that also
        persists the token through the handler (defaults to `FileTokenHandler`).
        Useful when you have a token from `run_device_flow()`, `Token.from_base64()`,
        custom storage, etc.
        """
        handler = token_handler or FileTokenHandler()
        handler.save(token)
        return cls(
            token=token,
            token_handler=handler,
            httpx_client=httpx_client,
            timeout=timeout,
            proxy=proxy,
            **httpx_kwargs,
        )

    @classmethod
    def from_pat(
        cls: Type[TSelf],
        pat: str | models.PersonalAccessTokenCreated,
        *,
        token_handler: Optional[TokenHandler] = None,
        httpx_client: Optional[httpx.Client] = None,
        timeout: float = 30.0,
        proxy: Optional[Dict[str, str]] = None,
        **httpx_kwargs: Any,
    ) -> TSelf:
        """Construct a client from a Personal Access Token.

        Pass either the raw `sdp_…` string or a `PersonalAccessTokenCreated`
        returned by `CookieSession.create_pat()`. PATs don't refresh —
        mint a new one via the cookie session when one expires.
        """
        if isinstance(pat, models.PersonalAccessTokenCreated):
            token = pat.to_token()
        else:
            token = Token(access_token=pat)
        return cls.from_token(
            token,
            token_handler=token_handler,
            httpx_client=httpx_client,
            timeout=timeout,
            proxy=proxy,
            **httpx_kwargs,
        )

    # ── OAuth apps & revoke & refresh ───────────────────────────────────────

    def list_apps(self: ClientProtocol, page: int = 1, limit: int = 100):
        """GET /oauth/apps — list registered OAuth apps. Public endpoint, no auth."""
        data = self._request(
            "get", "/oauth/apps", params={"page": page, "limit": limit}, auth=False
        )
        return models.AppList.model_validate(data)

    def revoke_token(
        self: ClientProtocol,
        token: Optional[str] = None,
        token_type_hint: Optional[str] = None,
    ):
        """RFC 7009 token revocation.

        Revokes the current access_token by default. Pass `token=...` to
        revoke a specific value, and
        `token_type_hint="access_token"|"refresh_token"` to hint.
        """
        value = token or self._token.access_token
        if not value:
            raise AuthenticationError("No token to revoke.")
        payload = _request_models.RevokeTokenRequest(
            token=value,
            client_id=self._token.client_id,
            token_type_hint=token_type_hint,
        ).model_dump(exclude_none=True)
        response = make_http_request(
            self._client, "post", constants.REVOKE_URL, data=payload
        )
        if not response.is_success:
            raise APIError("Token revocation failed.", response=response)

    def refresh_token(self: ClientProtocol):
        """Manually refresh the access_token using the stored refresh_token.

        Most callers don't need to call this — `_request` auto-refreshes on
        expiry or 401. Returns the updated Token.
        """
        self._refresh_access_token()
        return self._token

    # ── Device-flow internals ───────────────────────────────────────────────

    @classmethod
    def _poll_device_token(
        cls,
        client: httpx.Client,
        device_code: str,
        client_id: str,
        poll: bool,
        interval: float,
        deadline: float,
    ) -> Token:
        """Poll `/oauth/device/token` until approved or the deadline passes."""
        payload = _request_models.DeviceTokenRequest(
            client_id=client_id, device_code=device_code
        ).model_dump(exclude_none=True)
        while True:
            response = make_http_request(
                client, "post", constants.DEVICE_TOKEN_URL, data=payload
            )
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise JSONDecodeAPIError(response=response) from e
            if response.is_success and data.get("access_token"):
                return Token(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    client_id=client_id,
                    scope=data.get("scope"),
                    expires_at=int(time.time()) + int(data.get("expires_in", 3600)),
                )
            err = data.get("error") if isinstance(data, dict) else None
            if err == "authorization_pending" and poll:
                if time.time() >= deadline:
                    raise AuthenticationError(
                        "Device authorization timed out.", response=response
                    )
                time.sleep(interval)
                continue
            if err == "slow_down" and poll:
                interval += 2
                time.sleep(interval)
                continue
            raise AuthenticationError("Device authorization failed.", response=response)
