"""Token persistence backends."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union

import anyio

from ..token import Token


class AsyncTokenHandler(ABC):
    """Abstract base for token persistence backends."""

    @abstractmethod
    async def load(self) -> Optional[Token]:
        """Load the stored token, or None if nothing is stored."""

    @abstractmethod
    async def save(self, token: Token) -> None:
        """Persist the given token, replacing any previously stored value."""


class AsyncMemoryTokenHandler(AsyncTokenHandler):
    """In-process token storage. Lost on process exit."""

    def __init__(self, initial: Optional[Token] = None) -> None:
        self._token = initial

    async def load(self) -> Optional[Token]:
        return self._token

    async def save(self, token: Token) -> None:
        self._token = token


class AsyncFileTokenHandler(AsyncTokenHandler):
    """JSON file storage with atomic writes."""

    DEFAULT_PATH = ".cache/seedr_token.json"

    def __init__(self, path: Union[str, Path] = DEFAULT_PATH) -> None:
        self.path = anyio.Path(path)

    async def load(self) -> Optional[Token]:
        try:
            return Token.model_validate_json(await self.path.read_text())
        except (ValueError, OSError):
            return None

    async def save(self, token: Token) -> None:
        await self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        await tmp.write_text(token.model_dump_json(exclude_none=True))
        await tmp.replace(self.path)
