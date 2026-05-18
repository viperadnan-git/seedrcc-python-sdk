# DO NOT EDIT — generated from src/seedrcc/_async/_files.py by scripts/gen_sync.py.
# Run `python scripts/gen_sync.py` (or rebuild the package) to regenerate.

"""FilesMixin — files, folders, batch ops, search."""

from typing import Any, Dict, List, Union

from .. import _request_models, models
from ._protocols import ClientProtocol


class FilesMixin:
    # ── Reads ───────────────────────────────────────────────────────────────

    def get_root(self: ClientProtocol):
        """GET /fs/root — metadata of the user's root folder."""
        return models.Folder.model_validate(self._request("get", "/fs/root"))

    def list_contents(self: ClientProtocol, folder_id: Union[int, str] = "root"):
        """List folder contents.

        `folder_id="root"` (default) hits `/fs/root/contents`; any other id hits
        `/fs/folder/{id}/contents`.
        """
        if folder_id in ("root", 0, "0"):
            endpoint = "/fs/root/contents"
        else:
            endpoint = f"/fs/folder/{folder_id}/contents"
        return models.FolderContents.model_validate(self._request("get", endpoint))

    def get_folder(self: ClientProtocol, folder_id: Union[int, str]):
        """GET /fs/folder/{id}. Requires `files.read`."""
        return models.Folder.model_validate(
            self._request("get", f"/fs/folder/{folder_id}")
        )

    def get_file(self: ClientProtocol, file_id: Union[int, str]):
        """GET /fs/file/{id}. Requires `files.read`."""
        return models.File.model_validate(self._request("get", f"/fs/file/{file_id}"))

    def get_path(self: ClientProtocol, path: str):
        """GET /fs/path?path=… — resolve a string path to a folder."""
        return models.Folder.model_validate(
            self._request("get", "/fs/path", params={"path": path})
        )

    def search_fs(self: ClientProtocol, query: str):
        """GET /search/fs?q=… — full-text search across files/folders/torrents."""
        data = self._request("get", "/search/fs", params={"q": query})
        return models.SearchResults.model_validate(data)

    # ── Writes ──────────────────────────────────────────────────────────────

    def create_folder(self: ClientProtocol, name: str, parent_id: Union[int, str] = 0):
        """POST /fs/folder. Requires `files.write`."""
        payload = _request_models.CreateFolderRequest(name=name, parent_id=parent_id)
        data = self._request(
            "post", "/fs/folder", json=payload.model_dump(exclude_none=True)
        )
        return models.Folder.model_validate(data)

    def delete_folder(self: ClientProtocol, folder_id: Union[int, str]):
        """Deletes a folder. Requires `files.write`.

        Routed through `/fs/batch/delete` (the path-based DELETE endpoint
        requires a non-standard form body).
        """
        data = self._request(
            "post",
            "/fs/batch/delete",
            json={"delete_arr": [{"type": "folder", "id": folder_id}]},
        )
        return models.APIResult.model_validate(data or {})

    def delete_file(self: ClientProtocol, file_id: Union[int, str]):
        """Deletes a file. Requires `files.write`.

        Routed through `/fs/batch/delete` (see `delete_folder`).
        """
        data = self._request(
            "post",
            "/fs/batch/delete",
            json={"delete_arr": [{"type": "file", "id": file_id}]},
        )
        return models.APIResult.model_validate(data or {})

    def batch_copy(
        self: ClientProtocol,
        items: List[Dict[str, Any]],
        destination_folder_id: Union[int, str],
    ):
        """POST /fs/batch/copy.

        `items` is a list of `{"type": "file"|"folder", "id": <int>}`.
        """
        payload = {"destination_folder_id": destination_folder_id, "items": items}
        data = self._request("post", "/fs/batch/copy", json=payload)
        return models.APIResult.model_validate(data or {})

    def batch_move(
        self: ClientProtocol,
        items: List[Dict[str, Any]],
        destination_folder_id: Union[int, str],
    ):
        """POST /fs/batch/move."""
        payload = {"destination_folder_id": destination_folder_id, "items": items}
        data = self._request("post", "/fs/batch/move", json=payload)
        return models.APIResult.model_validate(data or {})

    def batch_delete(self: ClientProtocol, items: List[Dict[str, Any]]):
        """POST /fs/batch/delete.

        Requires BOTH `files.write` AND `tasks.write`. `items` accepts type
        `"file"`, `"folder"`, or `"torrent"`.
        """
        data = self._request("post", "/fs/batch/delete", json={"delete_arr": items})
        return models.APIResult.model_validate(data or {})
