# DO NOT EDIT — generated from src/seedrcc/_async/_base.py by scripts/gen_sync.py.
# Run `python scripts/gen_sync.py` (or rebuild the package) to regenerate.

"""BaseClient — owns the HTTP client, token state, and refresh pipeline.

All mixins assume an instance of this as `self`. See `_protocols.ClientProtocol`.
"""

import json
import time
from typing import Any, Dict, Optional, TypeVar

import httpx

from .. import _request_models, constants
from ..errors import (
    AuthenticationError,
    JSONDecodeAPIError,
)
from ..token import Token
from ._http import make_http_request, raise_for_status
from ._token_handlers import FileTokenHandler, TokenHandler

TBase = TypeVar("TBase", bound="BaseClient")


class BaseClient:
    """Owns the client state, HTTP request pipeline, and refresh logic."""

    _token: Token
    _handler: TokenHandler
    _client: httpx.Client
    _manages_client_lifecycle: bool

    def __init__(
        self,
        token: Optional[Token] = None,
        token_handler: Optional[TokenHandler] = None,
        httpx_client: Optional[httpx.Client] = None,
        timeout: float = 30.0,
        proxy: Optional[Dict[str, str]] = None,
        **httpx_kwargs: Any,
    ) -> None:
        """Initializes the client.

        Args:
            token: Optional explicit Token. If omitted, the handler is consulted
                on context-manager entry (`with ...`).
            token_handler: Persistence backend. Defaults to `FileTokenHandler()`
                (JSON at `./.cache/seedr_token.json`). Pass `MemoryTokenHandler()`
                for in-process only.
            httpx_client: Optional pre-configured `httpx.Client`.
            timeout: Network timeout in seconds (ignored if `httpx_client` is given).
            proxy: Optional proxy config (ignored if `httpx_client` is given).
            **httpx_kwargs: Extra kwargs for `httpx.Client` (ignored if `httpx_client`).

        """
        self._handler: TokenHandler = token_handler or FileTokenHandler()
        self._token: Token = token if token is not None else Token()

        if httpx_client is not None:
            self._client = httpx_client
            self._manages_client_lifecycle = False
        else:
            httpx_kwargs.setdefault("timeout", timeout)
            httpx_kwargs.setdefault("proxy", proxy)
            self._client = httpx.Client(**httpx_kwargs)
            self._manages_client_lifecycle = True

    @property
    def token(self) -> Token:
        """The current Token in memory."""
        return self._token

    @property
    def token_handler(self) -> TokenHandler:
        """The persistence backend in use."""
        return self._handler

    # ── Refresh ─────────────────────────────────────────────────────────────

    def _refresh_access_token(self) -> None:
        """POST /oauth/token with grant_type=refresh_token. Rotates the stored token."""
        if not (self._token.refresh_token and self._token.client_id):
            raise AuthenticationError(
                "Missing refresh_token or client_id — cannot refresh."
            )
        payload = _request_models.RefreshTokenRequest(
            client_id=self._token.client_id,
            refresh_token=self._token.refresh_token,
        )
        response = make_http_request(
            self._client,
            "post",
            constants.TOKEN_URL,
            data=payload.model_dump(exclude_none=True),
        )
        if not response.is_success:
            raise AuthenticationError("Token refresh failed.", response=response)
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise JSONDecodeAPIError(response=response) from e
        if "access_token" not in data or not data["access_token"]:
            raise AuthenticationError(
                "Refresh response missing access_token.", response=response
            )
        self._token = Token(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", self._token.refresh_token),
            client_id=self._token.client_id,
            scope=data.get("scope", self._token.scope),
            expires_at=int(time.time()) + int(data.get("expires_in", 3600)),
        )
        self._handler.save(self._token)

    # ── HTTP core ───────────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        auth: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Send a request against PUBLIC_API with bearer auth and refresh handling.

        If `auth=False`, no Authorization header is sent (public OAuth endpoints).
        """
        response = self._raw_request(method, endpoint, auth=auth, **kwargs)
        if response.status_code == 204:
            return None
        try:
            return response.json()
        except json.JSONDecodeError as e:
            raise JSONDecodeAPIError(response=response) from e

    def _raw_request(
        self,
        method: str,
        endpoint: str,
        *,
        auth: bool = True,
        **kwargs: Any,
    ) -> httpx.Response:
        """Same as `_request` but returns the raw httpx.Response (for binary downloads)."""
        url = f"{constants.PUBLIC_API}{endpoint}"
        if auth:
            if self._token.is_expired() and self._token.refresh_token:
                self._refresh_access_token()
            if not self._token.access_token:
                raise AuthenticationError(
                    "No access_token available — authenticate first."
                )
            headers = dict(kwargs.pop("headers", {}) or {})
            headers["Authorization"] = f"Bearer {self._token.access_token}"
            headers.setdefault("Accept", "application/json")
            kwargs["headers"] = headers

        response = make_http_request(self._client, method, url, **kwargs)

        if (
            auth
            and response.status_code == 401
            and self._token.refresh_token
            and self._token.client_id
        ):
            self._refresh_access_token()
            kwargs["headers"]["Authorization"] = f"Bearer {self._token.access_token}"
            response = make_http_request(self._client, method, url, **kwargs)

        raise_for_status(response)
        return response

    # ── Misc ────────────────────────────────────────────────────────────────

    def _read_torrent_file(self, torrent_file: str) -> Dict[str, Any]:
        """Reads a torrent file from a local path or a remote URL into memory."""
        if torrent_file.startswith(("http://", "https://")):
            file_content = httpx.get(torrent_file).content
            return {"torrent_file": file_content}
        else:
            with open(torrent_file, "rb") as f:
                return {"torrent_file": f.read()}

    def close(self) -> None:
        if self._manages_client_lifecycle:
            self._client.close()

    def __enter__(self: TBase) -> TBase:
        if not self._token.access_token and not self._token.refresh_token:
            loaded = self._handler.load()
            if loaded is not None:
                self._token = loaded
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
