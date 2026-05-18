"""OAuth 2.0 token model for the public API."""

import base64
import time
from typing import Optional

from pydantic import BaseModel, ConfigDict

from .errors import TokenError


class Token(BaseModel):
    """OAuth 2.0 token pair for the public API.

    Fields:
        access_token: Bearer token (prefixed `sdo_`). 1-hour TTL.
        refresh_token: Used to mint new access tokens. Rotates on every refresh.
        client_id: Registered OAuth app id. Required for refresh calls.
        scope: Space-delimited granted scopes.
        expires_at: Absolute epoch seconds at which `access_token` expires.

    Use the standard Pydantic API:
        Token.model_validate(dict_data)
        Token.model_validate_json(json_str)
        token.model_dump(exclude_none=True)
        token.model_dump_json(exclude_none=True)
        token.model_copy(update={...})
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    client_id: Optional[str] = None
    scope: Optional[str] = None
    expires_at: Optional[int] = None

    def is_expired(self, skew: int = 60) -> bool:
        """True if the access_token is within `skew` seconds of expiring."""
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at - skew

    def to_base64(self) -> str:
        """Encodes the token as a single base64 string (for shareable transport)."""
        return base64.b64encode(
            self.model_dump_json(exclude_none=True).encode("utf-8")
        ).decode("utf-8")

    @classmethod
    def from_base64(cls, b64_str: str) -> "Token":
        """Decodes a token previously produced by `to_base64()`."""
        try:
            return cls.model_validate_json(base64.b64decode(b64_str).decode("utf-8"))
        except (ValueError, TypeError) as e:
            raise TokenError(f"Failed to decode Base64 string: {e}") from e

    def __repr__(self) -> str:
        """Masked repr that doesn't leak token secrets."""

        def _mask(value: Optional[str]) -> str:
            if value is None:
                return "None"
            return f"{value[:6]}****"

        parts = [
            f"access_token={_mask(self.access_token)}",
            f"refresh_token={_mask(self.refresh_token)}",
            f"client_id={self.client_id}",
            f"scope={self.scope!r}",
            f"expires_at={self.expires_at}",
        ]
        return f"Token({', '.join(parts)})"
