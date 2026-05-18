"""Legacy Seedr /oauth_test/* clients (pre-OAuth 2.0).

Kept for backward compatibility with existing integrations. New code
should use the OAuth 2.0 clients at `seedrcc.Seedr` / `seedrcc.AsyncSeedr`.

Example:
    from seedrcc.legacy import *  # AsyncSeedr, Seedr, Token, models, errors

"""

from .. import errors
from . import models
from .async_client import AsyncSeedr
from .client import Seedr
from .token import Token

__all__ = ["AsyncSeedr", "Seedr", "Token", "models", "errors"]
