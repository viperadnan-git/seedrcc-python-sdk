"""AsyncFilesMixin — files, folders, batch ops, search."""

from typing import Any, Dict, List, Union

from .. import _request_models, models
from ._protocols import AsyncClientProtocol


class AsyncFilesMixin:
    # ── Reads ───────────────────────────────────────────────────────────────

    async def get_root(self: AsyncClientProtocol):
        """GET /fs/root — metadata of the user's root folder."""
        return models.Folder.model_validate(await self._request("get", "/fs/root"))

    async def list_contents(
        self: AsyncClientProtocol, folder_id: Union[int, str] = "root"
    ):
        """List folder contents.

        `folder_id="root"` (default) hits `/fs/root/contents`; any other id hits
        `/fs/folder/{id}/contents`.
        """
        if folder_id in ("root", 0, "0"):
            endpoint = "/fs/root/contents"
        else:
            endpoint = f"/fs/folder/{folder_id}/contents"
        return models.FolderContents.model_validate(
            await self._request("get", endpoint)
        )

    async def get_folder(self: AsyncClientProtocol, folder_id: Union[int, str]):
        """GET /fs/folder/{id}. Requires `files.read`."""
        return models.Folder.model_validate(
            await self._request("get", f"/fs/folder/{folder_id}")
        )

    async def get_file(self: AsyncClientProtocol, file_id: Union[int, str]):
        """GET /fs/file/{id}. Requires `files.read`."""
        return models.File.model_validate(
            await self._request("get", f"/fs/file/{file_id}")
        )

    async def get_path(self: AsyncClientProtocol, path: str):
        """GET /fs/path?path=… — resolve a string path to a folder."""
        return models.Folder.model_validate(
            await self._request("get", "/fs/path", params={"path": path})
        )

    async def search_fs(self: AsyncClientProtocol, query: str):
        """GET /search/fs?q=… — full-text search across files/folders/torrents."""
        data = await self._request("get", "/search/fs", params={"q": query})
        return models.SearchResults.model_validate(data)

    # ── Writes ──────────────────────────────────────────────────────────────

    async def create_folder(
        self: AsyncClientProtocol, name: str, parent_id: Union[int, str] = 0
    ):
        """POST /fs/folder. Requires `files.write`."""
        payload = _request_models.CreateFolderRequest(name=name, parent_id=parent_id)
        data = await self._request(
            "post", "/fs/folder", json=payload.model_dump(exclude_none=True)
        )
        return models.Folder.model_validate(data)

    async def delete_folder(self: AsyncClientProtocol, folder_id: Union[int, str]):
        """Deletes a folder. Requires `files.write`.

        Routed through `/fs/batch/delete` (the path-based DELETE endpoint
        requires a non-standard form body).
        """
        data = await self._request(
            "post",
            "/fs/batch/delete",
            json={"delete_arr": [{"type": "folder", "id": folder_id}]},
        )
        return models.APIResult.model_validate(data or {})

    async def delete_file(self: AsyncClientProtocol, file_id: Union[int, str]):
        """Deletes a file. Requires `files.write`.

        Routed through `/fs/batch/delete` (see `delete_folder`).
        """
        data = await self._request(
            "post",
            "/fs/batch/delete",
            json={"delete_arr": [{"type": "file", "id": file_id}]},
        )
        return models.APIResult.model_validate(data or {})

    async def batch_copy(
        self: AsyncClientProtocol,
        items: List[Dict[str, Any]],
        destination_folder_id: Union[int, str],
    ):
        """POST /fs/batch/copy.

        `items` is a list of `{"type": "file"|"folder", "id": <int>}`.
        """
        payload = {"destination_folder_id": destination_folder_id, "items": items}
        data = await self._request("post", "/fs/batch/copy", json=payload)
        return models.APIResult.model_validate(data or {})

    async def batch_move(
        self: AsyncClientProtocol,
        items: List[Dict[str, Any]],
        destination_folder_id: Union[int, str],
    ):
        """POST /fs/batch/move."""
        payload = {"destination_folder_id": destination_folder_id, "items": items}
        data = await self._request("post", "/fs/batch/move", json=payload)
        return models.APIResult.model_validate(data or {})

    async def batch_delete(self: AsyncClientProtocol, items: List[Dict[str, Any]]):
        """POST /fs/batch/delete.

        Requires BOTH `files.write` AND `tasks.write`. `items` accepts type
        `"file"`, `"folder"`, or `"torrent"`.
        """
        data = await self._request(
            "post", "/fs/batch/delete", json={"delete_arr": items}
        )
        return models.APIResult.model_validate(data or {})
