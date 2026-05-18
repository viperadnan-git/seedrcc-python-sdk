"""Protocol describing what mixin methods can assume about `self`.

Used only as a *structural* type-hint on `self:` parameters — mixins do NOT
inherit from this Protocol. The `AsyncBaseClient` concrete class (and thus
the composed `AsyncSeedr`) satisfies this Protocol by providing the listed
attributes via instance/class annotations.

Only the symbols accessed by mixin methods are listed here. The `token` /
`token_handler` public properties are intentionally excluded because no
mixin reads them via `self` — they exist for external callers.
"""

from typing import Any, Callable, Protocol

import httpx

from ..token import Token
from ..token_handlers import TokenHandler


class AsyncClientProtocol(Protocol):
    """What a mixin can assume about `self` on the client."""

    # State
    _token: Token
    _handler: TokenHandler
    _client: httpx.AsyncClient

    # HTTP + refresh pipeline. Typed as Callable attribute annotations so no
    # method body is created at runtime.
    _request: Callable[..., Any]
    _raw_request: Callable[..., Any]
    _refresh_access_token: Callable[[], Any]
    _read_torrent_file_async: Callable[[str], Any]
