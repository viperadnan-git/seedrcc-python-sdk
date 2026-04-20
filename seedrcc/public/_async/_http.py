"""Module-level async HTTP helpers shared by the base client and auth mixins.

Kept at module scope so classmethod/staticmethod helpers on mixins can call
them directly without needing `cls` to resolve to the final composed class.
"""

import json
import re
from typing import Any

import httpx

from ...exceptions import (
    APIError,
    AuthenticationError,
    NetworkError,
    ScopeError,
    ServerError,
)


async def make_http_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: Any,
) -> httpx.Response:
    """Perform a raw HTTP request with network/server error translation."""
    try:
        response = await client.request(method, url, **kwargs)
        if response.is_server_error:
            raise ServerError(response=response)
        return response
    except httpx.RequestError as e:
        raise NetworkError(str(e)) from e


def raise_for_status(response: httpx.Response) -> None:
    """Translate HTTP client-error statuses into typed exceptions.

    404/405 are treated the same as other 4xx (APIError) — callers that want to
    handle "not found" distinctly should check `response.status_code` themselves.
    """
    if not response.is_client_error:
        return
    if response.status_code == 401:
        raise AuthenticationError("Invalid or expired token.", response=response)
    if response.status_code == 403:
        missing = None
        try:
            data = response.json()
            msg = data.get("reason_phrase") or data.get("message") or ""
            match = re.search(r"scope:\s*([A-Za-z0-9_\.]+)", msg)
            if match:
                missing = match.group(1)
            if "scope" in msg.lower() or missing:
                raise ScopeError(
                    msg or "Missing required scope.",
                    missing_scope=missing,
                    response=response,
                )
        except (json.JSONDecodeError, ValueError):
            pass
        raise APIError("Access forbidden.", response=response)
    if response.status_code == 429:
        raise APIError("Rate limit exceeded.", response=response)
    raise APIError("API request failed.", response=response)
