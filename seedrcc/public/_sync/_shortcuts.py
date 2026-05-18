# DO NOT EDIT — generated from seedrcc/public/_async/_shortcuts.py by scripts/gen_sync.py.
# Run `python scripts/gen_sync.py` (or rebuild the package) to regenerate.

"""ShortcutsMixin — compound convenience operations.

High-level workflows composed from the primitive mixin methods. A single
`_ShortcutSelf` Protocol captures the mixin methods any shortcut calls on
`self`, so each shortcut's body type-resolves without the mixin having to
inherit the composed client.
"""

from typing import Any, Dict, List, Protocol, Union

from .. import models
from ._protocols import ClientProtocol


class _ShortcutSelf(ClientProtocol, Protocol):
    """`self` type for `ShortcutsMixin` methods.

    Extends `ClientProtocol` with the primitive mixin methods that
    shortcuts compose. Add new stubs here when a new shortcut needs another
    primitive.
    """

    def list_tasks(self) -> models.TaskList: ...
    def delete_task(self, task_id: Union[int, str]) -> models.APIResult: ...
    def list_contents(
        self, folder_id: Union[int, str] = "root"
    ) -> models.FolderContents: ...
    def batch_delete(self, items: List[Dict[str, Any]]) -> models.APIResult: ...


class ShortcutsMixin:
    def purge(self: _ShortcutSelf, max_iterations: int = 5) -> None:
        """Cancel every running task and delete every file/folder at root.

        Each pass:
          1. Cancels every running task via `delete_task` (batch_delete with
             `type=torrent` only unlinks the folder entry — it doesn't stop
             the underlying task).
          2. Sweeps root-level folders + files in one `batch_delete`.

        The task's `folder_id` is intentionally NOT batch-deleted — it points
        to an internal `parent=-1` staging folder, and deleting it triggers
        server-side re-queue of hidden pending items. A task's
        `folder_created_id` (the user-visible output folder) always surfaces
        in `list_contents().folders` after completion, so iteration picks it
        up naturally.

        Exits early as soon as both lists are empty. Capped at
        `max_iterations` to bound runaway loops.
        """
        for _ in range(max_iterations):
            tasks = (self.list_tasks()).tasks
            for t in tasks:
                self.delete_task(t.id)

            r = self.list_contents()
            items: List[Dict[str, Any]] = [
                {"type": "folder", "id": f.id} for f in r.folders
            ] + [{"type": "file", "id": f.id} for f in r.files]

            if not items and not tasks:
                return
            if items:
                self.batch_delete(items)
