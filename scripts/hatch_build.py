"""Hatchling build hook for regenerating sync mirrors.

Runs ``scripts/gen_sync.py`` before every wheel/sdist build so the shipped
sync code is always up-to-date with the async source.
"""

from __future__ import annotations

import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class UnasyncBuildHook(BuildHookInterface):
    """Hatchling custom build hook that drives the unasync regen step."""

    PLUGIN_NAME = "unasync"

    def initialize(self, version: str, build_data: dict) -> None:
        """Add `scripts/` to `sys.path` and call `gen_sync.regenerate()`."""
        root = Path(self.root)
        scripts = root / "scripts"
        sys.path.insert(0, str(scripts))
        try:
            import gen_sync

            gen_sync.regenerate()
        finally:
            sys.path.remove(str(scripts))
