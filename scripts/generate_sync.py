#!/usr/bin/env python3
"""Generate synchronous clients from their async sources.

Pipelines are declared in `PIPELINES` below — one entry per source→dest pair.
Each pipeline can inject a `pre` transform (applied before the core mechanical
async→sync rewrite) and a `post` transform (applied after). Add a new pipeline
by appending another `Pipeline(...)`; no branching needed.

Core rewrite includes auto-stripping the `Async` prefix from class names (at
identifier boundaries), so `AsyncSeedr`, `AsyncBaseClient`, `httpx.AsyncClient`,
etc. do not need to be listed anywhere.

Usage:
    python scripts/generate_sync.py
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent

GENERATED_HEADER = (
    "# This file is auto-generated — do not edit directly.\n"
    "# Regenerate with: python scripts/generate_sync.py\n"
)

LEGACY_SYNC_CLASS_DOC = '''    """Synchronous client for interacting with the Seedr API.

    Example:
        ```python
        from seedrcc import Seedr, Token

        # Load a previously saved token from a JSON string
        token_string = '{"access_token": "...", "refresh_token": "..."}'
        token = Token.from_json(token_string)

        # Initialize the client and make a request
        with Seedr(token=token) as client:
            settings = client.get_settings()
            print(f"Hello, {settings.account.username}")
        ```
    """'''

PUBLIC_SYNC_DOC = '''    """Synchronous client for the Seedr public API.

    Example:
        ```python
        from seedrcc.public import Seedr

        # First run: mint token via full headless flow, persist to .cache/seedr_token.json
        with Seedr.from_credentials("user", "pass") as client:
            user = client.get_user()
            print(user.username)

        # Subsequent runs: auto-load from .cache/seedr_token.json, auto-refresh on expiry
        with Seedr() as client:
            quota = client.get_quota()
            print(f"{quota.space_used}/{quota.space_max}")
        ```
    """'''


# ── Core mechanical transforms ──────────────────────────────────────────────


def _rewrite_torrent_reader(src: str) -> str:
    """Swap the async torrent reader for the sync equivalent in-place.

    Terminates at the next top-level class member (`    @decorator`,
    `    def `, `    async def `) or EOF so the replacement doesn't swallow
    a following `@staticmethod` / method.
    """
    return re.sub(
        r"    async def _read_torrent_file_async\(self.*?\n"
        r"(?=    @|    (?:async )?def |\Z)",
        (
            "    def _read_torrent_file(self, torrent_file: str) -> Dict[str, Any]:\n"
            '        """Reads a torrent file from a local path or a remote URL into memory."""\n'
            '        if torrent_file.startswith(("http://", "https://")):\n'
            "            file_content = httpx.get(torrent_file).content\n"
            '            return {"torrent_file": file_content}\n'
            "        else:\n"
            '            with open(torrent_file, "rb") as f:\n'
            '                return {"torrent_file": f.read()}\n\n'
        ),
        src,
        flags=re.DOTALL,
    )


_TYPING_NAMES_TO_DROP = ("Coroutine", "Awaitable")


def _drop_async_typing_names(src: str) -> str:
    """Strip async-only names (`Coroutine`, `Awaitable`) from typing imports.

    Handles both single-line (`from typing import Awaitable, ...`) and
    multi-line parenthesised forms.
    """
    for name in _TYPING_NAMES_TO_DROP:
        # Multi-line: a line containing only the name (optional trailing comma)
        src = re.sub(rf"^\s+{name},?\n", "", src, flags=re.MULTILINE)
        # Single-line: `Name, ` or `, Name` inside `from typing import ...`
        src = re.sub(rf"(from typing import [^\n]*?){name},\s*", r"\1", src)
        src = re.sub(rf"(from typing import [^\n]*?),\s*{name}", r"\1", src)
    return src


def _strip_async_prefix(src: str) -> str:
    """AsyncFoo → Foo at identifier boundaries.

    Covers `AsyncSeedr`, `AsyncBaseClient`, `AsyncClientProtocol`,
    `httpx.AsyncClient`, `AsyncIterator`, etc. without listing them.
    """
    return re.sub(r"\bAsync([A-Z]\w*)", r"\1", src)


_KEYWORD_REPLACEMENTS = (
    ("async def ", "def "),
    ("async with ", "with "),
    ("async for ", "for "),
    ("await ", ""),
    ("__aenter__", "__enter__"),
    ("__aexit__", "__exit__"),
    (".aclose()", ".close()"),
)

_DOCSTRING_REPLACEMENTS = (
    ("Asynchronous client", "Synchronous client"),
    ("asynchronous client", "synchronous client"),
    ("Asynchronously reads", "Reads"),
    ("an asynchronous ", "an "),
)


def _core_transforms(src: str) -> str:
    src = _rewrite_torrent_reader(src)
    src = src.replace("_read_torrent_file_async", "_read_torrent_file")

    # Coroutine[Any, Any, T] / Awaitable[T] wrapping httpx.AsyncClient callables → T
    src = re.sub(
        r"Callable\[\s*\[httpx\.AsyncClient\],\s*Coroutine\[Any,\s*Any,\s*(.*?\])\]\s*\]",
        r"Callable[[httpx.Client], \1]",
        src,
        flags=re.DOTALL,
    )
    src = re.sub(
        r"Callable\[\s*\[httpx\.AsyncClient\],\s*Awaitable\[(.*?)\]\s*\]",
        r"Callable[[httpx.Client], \1]",
        src,
        flags=re.DOTALL,
    )

    # AsyncFoo → Foo (also turns httpx.AsyncClient → httpx.Client)
    src = _strip_async_prefix(src)

    # anyio → stdlib (time.sleep / pathlib.Path)
    src = re.sub(r"\nimport anyio\n", "\n", src)
    src = src.replace("anyio.sleep", "time.sleep")
    if "anyio.Path" in src:
        src = src.replace("anyio.Path", "Path")
        if "from pathlib import Path" not in src:
            # Insert alongside the standard-library imports.
            src = re.sub(
                r"^(from typing import )",
                r"from pathlib import Path\n\1",
                src,
                count=1,
                flags=re.MULTILINE,
            )

    # Drop imports that are only needed in the async path
    src = src.replace("import inspect\n", "")
    src = _drop_async_typing_names(src)

    for old, new in _KEYWORD_REPLACEMENTS:
        src = src.replace(old, new)

    for old, new in _DOCSTRING_REPLACEMENTS:
        src = src.replace(old, new)

    return src


# ── Per-pipeline pre/post hooks ─────────────────────────────────────────────


def _legacy_pre(src: str) -> str:
    """Collapse `inspect.iscoroutinefunction`-dispatched callback into a plain call."""
    return re.sub(
        r"( +)if (\S+):\n"
        r"\1    if inspect\.iscoroutinefunction\(\2\):\n"
        r"\1        await \2\((\S+)\)\n"
        r"\1    else:\n"
        r"\1        await anyio\.to_thread\.run_sync\(\2, \3\)",
        r"\1if \2:\n\1    \2(\3)",
        src,
    )


def _legacy_post(src: str, _name: str) -> str:
    return re.sub(
        r'    """Synchronous client for interacting with the Seedr API\..*?"""',
        LEGACY_SYNC_CLASS_DOC,
        src,
        count=1,
        flags=re.DOTALL,
    )


def _public_post(src: str, name: str) -> str:
    # Keep intra-package imports pointing at the sync tree.
    src = src.replace("seedrcc.public._async", "seedrcc.public._sync")
    # The composed-client docstring needs an async-free example block.
    if name == "_client.py":
        src = re.sub(
            r'    """Synchronous client for the Seedr public API\..*?"""',
            PUBLIC_SYNC_DOC,
            src,
            count=1,
            flags=re.DOTALL,
        )
    return src


def _noop(src: str) -> str:
    return src


def _noop_post(src: str, _name: str) -> str:
    return src


# ── Pipeline schema ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Pipeline:
    source: Path
    dest: Path
    pre: Callable[[str], str] = field(default=_noop)
    post: Callable[[str, str], str] = field(default=_noop_post)


PIPELINES: tuple[Pipeline, ...] = (
    Pipeline(
        source=ROOT / "seedrcc" / "async_client.py",
        dest=ROOT / "seedrcc" / "client.py",
        pre=_legacy_pre,
        post=_legacy_post,
    ),
    Pipeline(
        source=ROOT / "seedrcc" / "public" / "_async",
        dest=ROOT / "seedrcc" / "public" / "_sync",
        post=_public_post,
    ),
)


# ── Driver ──────────────────────────────────────────────────────────────────


def _generate_file(src: Path, dst: Path, pipeline: Pipeline) -> None:
    content = src.read_text()
    content = pipeline.pre(content)
    content = _core_transforms(content)
    content = pipeline.post(content, dst.name)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(GENERATED_HEADER + content)
    print(f"Generated {dst}")


def _run(pipeline: Pipeline) -> None:
    if not pipeline.source.exists():
        return
    if pipeline.source.is_dir():
        for src_file in sorted(pipeline.source.glob("*.py")):
            _generate_file(src_file, pipeline.dest / src_file.name, pipeline)
    else:
        _generate_file(pipeline.source, pipeline.dest, pipeline)


def main() -> None:
    for pipeline in PIPELINES:
        _run(pipeline)


if __name__ == "__main__":
    main()
