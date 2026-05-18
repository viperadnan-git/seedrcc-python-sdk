# DO NOT EDIT — generated from src/seedrcc/_async/_token_handlers.py by scripts/gen_sync.py.
# Run `python scripts/gen_sync.py` (or rebuild the package) to regenerate.

"""Token persistence backends."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union

from ..token import Token


class TokenHandler(ABC):
    """Abstract base for token persistence backends."""

    @abstractmethod
    def load(self) -> Optional[Token]:
        """Load the stored token, or None if nothing is stored."""

    @abstractmethod
    def save(self, token: Token) -> None:
        """Persist the given token, replacing any previously stored value."""


class MemoryTokenHandler(TokenHandler):
    """In-process token storage. Lost on process exit."""

    def __init__(self, initial: Optional[Token] = None) -> None:
        self._token = initial

    def load(self) -> Optional[Token]:
        return self._token

    def save(self, token: Token) -> None:
        self._token = token


class FileTokenHandler(TokenHandler):
    """JSON file storage with atomic writes."""

    DEFAULT_PATH = ".cache/seedr_token.json"

    def __init__(self, path: Union[str, Path] = DEFAULT_PATH) -> None:
        self.path = Path(path)

    def load(self) -> Optional[Token]:
        try:
            return Token.model_validate_json(self.path.read_text())
        except (ValueError, OSError):
            return None

    def save(self, token: Token) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(token.model_dump_json(exclude_none=True))
        tmp.replace(self.path)
