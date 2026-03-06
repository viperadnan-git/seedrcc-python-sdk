#!/usr/bin/env python3
"""Generate the synchronous client (client.py) from async_client.py.

async_client.py is the single source of truth. This script applies mechanical
transformations to produce the sync equivalent.

Usage:
    python scripts/generate_sync.py
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASYNC_PATH = ROOT / "seedrcc" / "async_client.py"
SYNC_PATH = ROOT / "seedrcc" / "client.py"

GENERATED_HEADER = (
    "# This file is auto-generated from async_client.py — do not edit directly.\n"
    "# Regenerate with: python scripts/generate_sync.py\n"
)

SYNC_CLASS_DOC = '''    """Synchronous client for interacting with the Seedr API.

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


def generate_sync(source: str) -> str:
    out = source

    # ── Phase 1: Complex async-specific patterns ──────────────────────────

    # 1a. Replace coroutine-aware callback dispatch with a direct call.
    out = re.sub(
        r"( +)if (\S+):\n"
        r"\1    if inspect\.iscoroutinefunction\(\2\):\n"
        r"\1        await \2\((\S+)\)\n"
        r"\1    else:\n"
        r"\1        await anyio\.to_thread\.run_sync\(\2, \3\)",
        r"\1if \2:\n\1    \2(\3)",
        out,
    )

    # 1b. Replace async torrent file reader with sync version.
    out = re.sub(
        r"    async def _read_torrent_file_async\(self.*?\n(?=    (?:async )?def |\Z)",
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
        out,
        flags=re.DOTALL,
    )
    out = out.replace("_read_torrent_file_async", "_read_torrent_file")

    # 1c. Simplify Coroutine type hints for sync callables.
    # Coroutine[Any, Any, Dict[str, Any]] -> Dict[str, Any]
    # (.*?\]) captures the return type including its closing bracket,
    # then \] matches Coroutine's ], then \s*\] matches Callable's ].
    out = re.sub(
        r"Callable\[\s*\[httpx\.AsyncClient\],\s*Coroutine\[Any,\s*Any,\s*(.*?\])\]\s*\]",
        r"Callable[[httpx.Client], \1]",
        out,
        flags=re.DOTALL,
    )

    # ── Phase 2: Import adjustments ───────────────────────────────────────

    out = out.replace("import inspect\n", "")
    out = re.sub(r"\nimport anyio\n", "\n", out)
    # Remove Coroutine from typing import
    out = re.sub(
        r"from typing import (.+)",
        lambda m: (
            "from typing import "
            + ", ".join(
                t.strip() for t in m.group(1).split(",") if t.strip() != "Coroutine"
            )
        ),
        out,
    )

    # ── Phase 3: Mechanical async→sync replacements ───────────────────────

    replacements = [
        ("AsyncSeedr", "Seedr"),
        ("httpx.AsyncClient", "httpx.Client"),
        ("async def ", "def "),
        ("async with ", "with "),
        ("async for ", "for "),
        ("await ", ""),
        ("__aenter__", "__enter__"),
        ("__aexit__", "__exit__"),
        (".aclose()", ".close()"),
    ]
    for old, new in replacements:
        out = out.replace(old, new)

    # ── Phase 4: Docstring & description fixes ────────────────────────────

    out = out.replace("Asynchronous client", "Synchronous client")
    out = out.replace("asynchronous client", "synchronous client")
    out = out.replace("Asynchronously reads", "Reads")
    out = out.replace("an asynchronous ", "an ")

    # Replace the class-level docstring (which still has asyncio boilerplate).
    out = re.sub(
        r'    """Synchronous client for interacting with the Seedr API\..*?"""',
        SYNC_CLASS_DOC,
        out,
        count=1,
        flags=re.DOTALL,
    )

    # ── Phase 5: Add header ───────────────────────────────────────────────

    out = GENERATED_HEADER + out

    return out


def main():
    source = ASYNC_PATH.read_text()
    result = generate_sync(source)
    SYNC_PATH.write_text(result)
    print(f"Generated {SYNC_PATH}")


if __name__ == "__main__":
    main()
