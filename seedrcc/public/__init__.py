"""Seedr public OAuth 2.0 API client.

Targets the /api/v0.1/p/* endpoints with `sdo_*` bearer tokens.
Legacy /oauth_test/* clients remain available as `seedrcc.Seedr` and `seedrcc.AsyncSeedr`.

Async-first design: the source of truth is `seedrcc.public._async.*`, and the
synchronous mirrors under `seedrcc.public._sync.*` are generated from them via
`scripts/generate_sync.py`.
"""

from .. import exceptions
from . import _constants, models
from ._async import AsyncCookieSession, AsyncSeedr
from ._sync import CookieSession, Seedr
from .token import Token
from .token_handlers import FileTokenHandler, MemoryTokenHandler, TokenHandler

__all__ = [
    "Seedr",
    "AsyncSeedr",
    "CookieSession",
    "AsyncCookieSession",
    "Token",
    "TokenHandler",
    "MemoryTokenHandler",
    "FileTokenHandler",
    "models",
    "exceptions",
    "_constants",
]
