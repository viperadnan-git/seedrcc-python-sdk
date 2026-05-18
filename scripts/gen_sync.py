"""Generate sync mirrors of the async sources via unasync.

    uv run python scripts/gen_sync.py            # regenerate
    uv run python scripts/gen_sync.py --check    # drift check (exit 1 on diff)

Pipeline: token-rewrite via :class:`_ProseRule` (handles ``async``/``await``,
``Async`` prefixes, prose in docstrings/comments) → per-file post-process for
project-specific surgery (``anyio`` → stdlib, ``inspect.iscoroutinefunction``
dispatch collapse, ``Coroutine``/``Awaitable`` typing strip) → prepend header
→ ``ruff check --fix`` + ``ruff format`` (skipped if absent) → write-if-changed
or check.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tokenize as std_tokenize
from pathlib import Path
from typing import Callable

import tokenize_rt
import unasync

ROOT = Path(__file__).resolve().parents[1]

# Token-level: applied to NAME tokens and (via _ProseRule) to the inner contents
# of STRING tokens. Whole-token match only — substring matches go through the
# prose patterns below.
ADDITIONAL_REPLACEMENTS = {
    "AsyncClient": "Client",
    "aclose": "close",
    "_async": "_sync",
    "_read_torrent_file_async": "_read_torrent_file",
}

# Substring/prose match: applied to docstrings/comments to rewrite content the
# base class doesn't (it only does whole-token NAME/STRING-inner lookups).
# The source-level convention is that docstrings stay implementation-agnostic
# in prose; only code-example bodies need rewriting, which this covers.
_PROSE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bAsync([A-Z]\w*)\b"), r"\1"),
    (re.compile(r"\basync\s+with\b"), "with"),
    (re.compile(r"\basync\s+for\b"), "for"),
    (re.compile(r"\basync\s+def\b"), "def"),
    (re.compile(r"\bawait\s+(?=\S)"), ""),
)

_HEADER = """\
# DO NOT EDIT — generated from {source} by scripts/gen_sync.py.
# Run `python scripts/gen_sync.py` (or rebuild the package) to regenerate.

"""


def _rewrite_prose(text: str) -> str:
    for pat, repl in _PROSE_PATTERNS:
        text = pat.sub(repl, text)
    return text


class _ProseRule(unasync.Rule):
    """Extended ``unasync.Rule``.

    Adds:

    - Docstring/comment regex rewriting (``_PROSE_PATTERNS``) — the base class
      only does whole-string lookups, so prose inside docstrings/comments needs
      this extra pass.
    - ``Async``-prefix stripping on identifier tokens (``AsyncSeedr`` → ``Seedr``,
      ``AsyncBaseClient`` → ``BaseClient``, etc.) without listing each name.

    Token-level ``async``/``await`` removal + NAME replacement is inherited.
    """

    _PROSE_TOKEN_NAMES = frozenset({"STRING", "COMMENT", "FSTRING_MIDDLE"})
    _ASYNC_PREFIX_RE = re.compile(r"^Async(?=[A-Z])")

    def _unasync_name(self, name):
        # Bypass unasync's built-in ``Async`` → ``Sync`` prefix fallback;
        # we want the prefix stripped entirely (``AsyncSeedr`` → ``Seedr``).
        if name in self.token_replacements:
            return self.token_replacements[name]
        return self._ASYNC_PREFIX_RE.sub("", name)

    def _unasync_tokens(self, tokens):
        for token in super()._unasync_tokens(tokens):
            if token.name in self._PROSE_TOKEN_NAMES:
                new_src = _rewrite_prose(token.src)
                if new_src != token.src:
                    token = token._replace(src=new_src)
            yield token


# ── Post-process surgery ────────────────────────────────────────────────────
# These handle constructs unasync can't express token-locally: structural code
# collapses, typing-import pruning, anyio→stdlib swaps that span lines.


def _strip_anyio(src: str) -> str:
    """Drop ``anyio`` in favour of stdlib equivalents.

    Removes ``import anyio``, swaps ``anyio.sleep`` → ``time.sleep`` and
    ``anyio.Path`` → ``pathlib.Path``, and ensures the new imports are present.
    """
    if "anyio" not in src:
        return src

    needs_time = "anyio.sleep" in src
    needs_path = "anyio.Path" in src
    src = src.replace("anyio.sleep", "time.sleep")
    src = src.replace("anyio.Path", "Path")
    src = re.sub(r"^import anyio\n", "", src, flags=re.MULTILINE)

    if needs_time and "import time" not in src:
        src = re.sub(
            r"^(import httpx\n)", r"import time\n\1", src, count=1, flags=re.MULTILINE
        )
    if needs_path and "from pathlib import Path" not in src:
        src = re.sub(
            r"^(from typing import )",
            r"from pathlib import Path\n\1",
            src,
            count=1,
            flags=re.MULTILINE,
        )
    return src


def _collapse_iscoroutinefunction(src: str) -> str:
    """Collapse the ``iscoroutinefunction`` dispatch into a direct call.

    Matches ``if inspect.iscoroutinefunction(cb): cb(x); else: run_sync(cb, x)``
    (after await-stripping) and replaces it with ``cb(x)``.
    """
    return re.sub(
        r"( +)if (\S+):\n"
        r"\1    if inspect\.iscoroutinefunction\(\2\):\n"
        r"\1        \2\((\S+)\)\n"
        r"\1    else:\n"
        r"\1        anyio\.to_thread\.run_sync\(\2, \3\)",
        r"\1if \2:\n\1    \2(\3)",
        src,
    )


def _strip_async_typing(src: str) -> str:
    """Drop ``Coroutine`` / ``Awaitable`` from ``typing`` imports.

    They survive the token rewrite because they're plain identifiers, but the
    sync mirror never uses them after the Callable signatures are flattened.
    """
    for name in ("Coroutine", "Awaitable"):
        src = re.sub(rf"^\s+{name},?\n", "", src, flags=re.MULTILINE)
        src = re.sub(rf"(from typing import [^\n]*?){name},\s*", r"\1", src)
        src = re.sub(rf"(from typing import [^\n]*?),\s*{name}", r"\1", src)
    return src


def _flatten_async_callable_signatures(src: str) -> str:
    """Unwrap ``Coroutine``/``Awaitable`` from ``Callable`` return types.

    ``Callable[[httpx.Client], Coroutine[Any, Any, T]]`` → ``Callable[[httpx.Client], T]``
    and the same for ``Awaitable[T]``. These appear in factory-helper signatures
    where the async source returns an awaitable but the sync mirror returns T.
    """
    src = re.sub(
        r"Callable\[\s*\[httpx\.Client\],\s*Coroutine\[Any,\s*Any,\s*(.*?\])\]\s*\]",
        r"Callable[[httpx.Client], \1]",
        src,
        flags=re.DOTALL,
    )
    src = re.sub(
        r"Callable\[\s*\[httpx\.Client\],\s*Awaitable\[(.*?)\]\s*\]",
        r"Callable[[httpx.Client], \1]",
        src,
        flags=re.DOTALL,
    )
    return src


def _strip_inspect_import(src: str) -> str:
    return src.replace("import inspect\n", "")


# ── Pipeline schema ─────────────────────────────────────────────────────────


class Pipeline:
    """One source → dest mapping plus its post-process chain.

    ``source`` may be a single file or a directory; the driver handles both.
    ``post_steps`` are applied in order after the unasync rewrite.
    """

    def __init__(
        self,
        source: Path,
        dest: Path,
        post_steps: tuple[Callable[[str], str], ...] = (),
    ) -> None:
        """Capture the source→dest mapping and its post-process chain."""
        self.source = source
        self.dest = dest
        self.post_steps = post_steps

    def post(self, src: str) -> str:
        """Run `post_steps` over `src` in order, returning the final source."""
        for step in self.post_steps:
            src = step(src)
        return src


# Class-doc swap: hand-written examples in the async source reference
# ``asyncio.run(...)`` etc. and can't survive a mechanical rewrite. We swap the
# whole class docstring for a sync-flavoured version in the output.
_LEGACY_SYNC_CLASS_DOC = '''    """Synchronous client for interacting with the Seedr API.

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

_PUBLIC_SYNC_CLIENT_DOC = '''    """Synchronous client for the Seedr public API.

    Example:
        ```python
        from seedrcc import Seedr

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


def _legacy_class_doc_swap(src: str) -> str:
    return re.sub(
        r'    """Asynchronous client for interacting with the Seedr API\..*?"""',
        _LEGACY_SYNC_CLASS_DOC,
        src,
        count=1,
        flags=re.DOTALL,
    )


def _read_torrent_file_rewrite(src: str) -> str:
    """Rewrite the async-flavoured torrent reader to use blocking I/O.

    The token rewrite handles the signature and the ``with httpx.Client()`` line,
    but the body still needs the ``raise_for_status`` removed and a simpler
    ``open()`` for the local-path branch.
    """
    return re.sub(
        r"    def _read_torrent_file\(self, torrent_file: str\) -> Dict\[str, Any\]:\n"
        r".*?(?=\n    def |\n    @|\n    class |\Z)",
        (
            "    def _read_torrent_file(self, torrent_file: str) -> Dict[str, Any]:\n"
            '        """Reads a torrent file from a local path or a remote URL into memory."""\n'
            '        if torrent_file.startswith(("http://", "https://")):\n'
            "            file_content = httpx.get(torrent_file).content\n"
            '            return {"torrent_file": file_content}\n'
            "        else:\n"
            '            with open(torrent_file, "rb") as f:\n'
            '                return {"torrent_file": f.read()}'
        ),
        src,
        count=1,
        flags=re.DOTALL,
    )


def _public_client_doc_swap(src: str) -> str:
    return re.sub(
        r'    """Asynchronous client for the Seedr public API\..*?"""',
        _PUBLIC_SYNC_CLIENT_DOC,
        src,
        count=1,
        flags=re.DOTALL,
    )


# Steps shared by every generated file.
_COMMON_STEPS: tuple[Callable[[str], str], ...] = (_strip_anyio,)

_PKG = ROOT / "src" / "seedrcc"

PIPELINES: tuple[Pipeline, ...] = (
    Pipeline(
        source=_PKG / "legacy" / "async_client.py",
        dest=_PKG / "legacy" / "client.py",
        post_steps=(
            _collapse_iscoroutinefunction,
            _flatten_async_callable_signatures,
            _strip_inspect_import,
            *_COMMON_STEPS,
            _strip_async_typing,
            _read_torrent_file_rewrite,
            _legacy_class_doc_swap,
        ),
    ),
    Pipeline(
        source=_PKG / "_async",
        dest=_PKG / "_sync",
        post_steps=(
            _flatten_async_callable_signatures,
            *_COMMON_STEPS,
            _strip_async_typing,
            _read_torrent_file_rewrite,
            _public_client_doc_swap,
        ),
    ),
)


# ── Driver ──────────────────────────────────────────────────────────────────


def _iter_sources(pipeline: Pipeline) -> list[tuple[Path, Path]]:
    """Resolve a pipeline into a list of (source_file, dest_file) pairs."""
    src = pipeline.source
    if not src.exists():
        return []
    if src.is_dir():
        return [
            (p, pipeline.dest / p.relative_to(src)) for p in sorted(src.rglob("*.py"))
        ]
    return [(src, pipeline.dest)]


def _make_rule() -> _ProseRule:
    # `fromdir`/`todir` here are placeholders; we apply the rule per-token via
    # `_unasync_tokens`, not via unasync's own dir-renaming driver.
    return _ProseRule(
        fromdir="/",
        todir="/",
        additional_replacements=ADDITIONAL_REPLACEMENTS,
    )


def _render(rule: _ProseRule, source: Path) -> bytes:
    with open(source, "rb") as f:
        encoding, _ = std_tokenize.detect_encoding(f.readline)
    with open(source, encoding=encoding) as f:
        tokens = tokenize_rt.src_to_tokens(f.read())
        tokens = rule._unasync_tokens(tokens)
        body = tokenize_rt.tokens_to_src(tokens)
    return body.encode(encoding)


def _ruff(path: Path, content: bytes) -> bytes:
    try:
        fixed = subprocess.run(
            [
                "ruff",
                "check",
                "--fix",
                "--exit-zero",
                "--stdin-filename",
                str(path),
                "-",
            ],
            input=content,
            capture_output=True,
            check=True,
        ).stdout
        return subprocess.run(
            ["ruff", "format", "--stdin-filename", str(path), "-"],
            input=fixed,
            capture_output=True,
            check=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(f"ruff failed on {path}:\n{exc.stderr.decode()}\n")
        raise


def _render_all() -> dict[Path, bytes]:
    rule = _make_rule()
    try:
        subprocess.run(["ruff", "--version"], capture_output=True, check=True)
        have_ruff = True
    except (FileNotFoundError, subprocess.CalledProcessError):
        have_ruff = False

    outputs: dict[Path, bytes] = {}
    for pipeline in PIPELINES:
        for source, dest in _iter_sources(pipeline):
            body = _render(rule, source).decode("utf-8")
            body = pipeline.post(body)
            rel_source = source.relative_to(ROOT).as_posix()
            content = (_HEADER.format(source=rel_source) + body).encode("utf-8")
            if have_ruff:
                content = _ruff(dest, content)
            outputs[dest] = content
    if not outputs:
        raise SystemExit("Sync generator: no source files found.")
    return outputs


def _write_if_changed(outputs: dict[Path, bytes]) -> list[Path]:
    changed: list[Path] = []
    for path, content in outputs.items():
        if path.exists() and path.read_bytes() == content:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        changed.append(path)
    return changed


def _check(outputs: dict[Path, bytes]) -> int:
    drift: list[Path] = []
    for path, content in outputs.items():
        actual = path.read_bytes() if path.exists() else b""
        if actual != content:
            drift.append(path)
    if not drift:
        return 0
    sys.stderr.write(
        "Sync generator: drift detected. Run `python scripts/gen_sync.py`:\n"
    )
    for path in drift:
        sys.stderr.write(f"  {path.relative_to(ROOT)}\n")
    return 1


def regenerate() -> list[Path]:
    """Programmatic entry point used by the Hatch build hook."""
    return _write_if_changed(_render_all())


def cli(argv: list[str] | None = None) -> int:
    """Command-line entry point: regenerate (default) or `--check` for drift."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if regenerating would change any file. Doesn't write.",
    )
    args = parser.parse_args(argv)

    outputs = _render_all()
    if args.check:
        return _check(outputs)
    changed = _write_if_changed(outputs)
    if changed:
        sys.stderr.write(f"Sync generator: wrote {len(changed)} file(s):\n")
        for path in changed:
            sys.stderr.write(f"  {path.relative_to(ROOT)}\n")
    else:
        sys.stderr.write("Sync generator: already up to date.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
