"""Seedr OAuth 2.0 API client.

Targets the /api/v0.1/p/* endpoints with `sdo_*` bearer tokens.
Legacy /oauth_test/* clients are available under `seedrcc.legacy.*`.

Async-first design: the source of truth is `seedrcc._async.*`, and the
synchronous mirrors under `seedrcc._sync.*` are generated from them via
`scripts/gen_sync.py`.
"""

from . import errors, models
from ._async import (
    AsyncCookieSession,
    AsyncFileTokenHandler,
    AsyncMemoryTokenHandler,
    AsyncSeedr,
    AsyncTokenHandler,
)
from ._sync import (
    CookieSession,
    FileTokenHandler,
    MemoryTokenHandler,
    Seedr,
    TokenHandler,
)
from .token import Token

__all__ = [
    "Seedr",
    "AsyncSeedr",
    "CookieSession",
    "AsyncCookieSession",
    "Token",
    "TokenHandler",
    "AsyncTokenHandler",
    "MemoryTokenHandler",
    "AsyncMemoryTokenHandler",
    "FileTokenHandler",
    "AsyncFileTokenHandler",
    "models",
    "errors",
]
