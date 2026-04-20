# This file is auto-generated — do not edit directly.
# Regenerate with: python scripts/generate_sync.py
"""TasksMixin — torrent tasks (add, progress, pause/resume/delete)."""

from typing import Any, Dict, List, Optional, Union

from .. import _request_models, models
from ._protocols import ClientProtocol


class TasksMixin:
    def list_tasks(self: ClientProtocol):
        """GET /tasks. Requires `tasks.read`."""
        return models.TaskList.model_validate(self._request("get", "/tasks"))

    def get_task(self: ClientProtocol, task_id: Union[int, str]):
        """GET /tasks/{id}. Requires `tasks.read`."""
        return models.TorrentTask.model_validate(
            self._request("get", f"/tasks/{task_id}")
        )

    def get_task_contents(self: ClientProtocol, task_id: Union[int, str]):
        """GET /tasks/{id}/contents. Requires `tasks.read`."""
        return models.FolderContents.model_validate(
            self._request("get", f"/tasks/{task_id}/contents")
        )

    def get_task_progress(self: ClientProtocol, task_id: Union[int, str]):
        """GET /tasks/{id}/progress. Requires `tasks.read`."""
        return models.TaskProgress.model_validate(
            self._request("get", f"/tasks/{task_id}/progress")
        )

    def get_task_unwanted(self: ClientProtocol, task_id: Union[int, str]):
        """GET /tasks/{id}/unwanted — indexes marked as unwanted."""
        return models.UnwantedEntries.model_validate(
            self._request("get", f"/tasks/{task_id}/unwanted")
        )

    def add_task(
        self: ClientProtocol,
        torrent_magnet: Optional[str] = None,
        torrent_url: Optional[str] = None,
        torrent_file: Optional[str] = None,
        folder_id: Union[int, str] = 0,
        force_upload: bool = False,
    ):
        """POST /tasks — add a torrent via magnet, URL, or local/remote .torrent file.

        Exactly one of `torrent_magnet`, `torrent_url`, or `torrent_file` must be set.
        - `torrent_magnet`: magnet URI (server fetches the torrent)
        - `torrent_url`: direct URL to a .torrent file (server fetches)
        - `torrent_file`: local path; if a URL is given and `force_upload=True`, the
          client downloads it and uploads as multipart.
        """
        if sum(bool(x) for x in (torrent_magnet, torrent_url, torrent_file)) != 1:
            raise ValueError(
                "Exactly one of torrent_magnet, torrent_url, torrent_file is required."
            )
        if torrent_file:
            if force_upload or not torrent_file.startswith(("http://", "https://")):
                files = self._read_torrent_file(torrent_file)
                data = self._request(
                    "post",
                    "/tasks",
                    data={"folder_id": str(folder_id)},
                    files=files,
                )
                return models.AddTaskResult.model_validate(data)
            torrent_url = torrent_file
        payload: Dict[str, Any] = {"folder_id": folder_id}
        if torrent_magnet:
            payload["torrent_magnet"] = torrent_magnet
        else:
            payload["torrent_url"] = torrent_url
        data = self._request("post", "/tasks", json=payload)
        return models.AddTaskResult.model_validate(data)

    def set_task_unwanted(
        self: ClientProtocol, task_id: Union[int, str], unwanted: List[int]
    ):
        """POST /tasks/{id}/unwanted. Requires `tasks.write`."""
        payload = _request_models.SetUnwantedRequest(unwanted=unwanted)
        data = self._request(
            "post",
            f"/tasks/{task_id}/unwanted",
            json=payload.model_dump(exclude_none=True),
        )
        return models.APIResult.model_validate(data or {})

    def pause_task(self: ClientProtocol, task_id: Union[int, str]):
        """POST /tasks/{id}/pause. Requires `tasks.write`."""
        data = self._request("post", f"/tasks/{task_id}/pause")
        return models.APIResult.model_validate(data or {})

    def resume_task(self: ClientProtocol, task_id: Union[int, str]):
        """POST /tasks/{id}/resume. Requires `tasks.write`."""
        data = self._request("post", f"/tasks/{task_id}/resume")
        return models.APIResult.model_validate(data or {})

    def delete_task(self: ClientProtocol, task_id: Union[int, str]):
        """DELETE /tasks/{id}. Requires `tasks.write`."""
        data = self._request("delete", f"/tasks/{task_id}")
        return models.APIResult.model_validate(data or {})
