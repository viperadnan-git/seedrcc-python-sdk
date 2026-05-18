"""Request payload models for the public OAuth 2.0 API.

All request payloads are plain Pydantic `BaseModel`s. Call sites serialize
with `model.model_dump(exclude_none=True)` to drop unset optional fields.
"""

from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict

from . import constants


class _BaseRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


# ── OAuth ────────────────────────────────────────────────────────────────────


class DeviceCodeRequest(_BaseRequest):
    client_id: str = constants.DEFAULT_CLIENT_ID
    scope: str = constants.DEFAULT_SCOPE


class DeviceTokenRequest(_BaseRequest):
    client_id: str
    device_code: str
    grant_type: str = constants.GRANT_DEVICE_CODE


class RefreshTokenRequest(_BaseRequest):
    client_id: str
    refresh_token: str
    grant_type: str = constants.GRANT_REFRESH_TOKEN


class RevokeTokenRequest(_BaseRequest):
    token: str
    client_id: Optional[str] = None
    token_type_hint: Optional[str] = None  # "access_token" | "refresh_token"


class CookieLoginRequest(_BaseRequest):
    username: str
    password: str
    rememberme: int = 1


# ── File system ──────────────────────────────────────────────────────────────


class CreateFolderRequest(_BaseRequest):
    name: str
    parent_id: Union[int, str] = 0


# ── Tasks ────────────────────────────────────────────────────────────────────


class SetUnwantedRequest(_BaseRequest):
    unwanted: List[int]


# ── PATs ─────────────────────────────────────────────────────────────────────


class CreatePATRequest(_BaseRequest):
    name: str
    scopes: List[str]
    expires_in: Optional[int] = None


# ── Subtitles ────────────────────────────────────────────────────────────────


class SearchSubtitlesRequest(_BaseRequest):
    file_id: Union[int, str]
    language: Optional[str] = None
    query: Optional[str] = None
