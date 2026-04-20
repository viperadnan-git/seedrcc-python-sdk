"""AsyncMediaMixin — downloads, archives, presentations, subtitles, scrape."""

import os
from typing import Any, Dict, Optional, Union

import anyio

from .. import _request_models, models
from ._protocols import AsyncClientProtocol


class AsyncMediaMixin:
    # ── Download ────────────────────────────────────────────────────────────

    async def get_file_download_url(
        self: AsyncClientProtocol, file_id: Union[int, str]
    ):
        """GET /download/file/{id}/url — returns the signed direct URL.

        Response includes `url` (short-lived signed URL, query-scoped auth so
        it's usable without a Bearer header) and `name` (suggested filename).
        """
        return models.FileDownloadUrl.model_validate(
            await self._request("get", f"/download/file/{file_id}/url")
        )

    async def download_file(self: AsyncClientProtocol, file_id: Union[int, str]):
        """GET /download/file/{id} — returns the raw file content bytes."""
        response = await self._raw_request("get", f"/download/file/{file_id}")
        return response.content

    async def download_archive(self: AsyncClientProtocol, archive_uniq: str):
        """GET /download/archive/{uniq} — returns the archive content bytes."""
        response = await self._raw_request("get", f"/download/archive/{archive_uniq}")
        return response.content

    # ── Archives ────────────────────────────────────────────────────────────

    async def create_archive(self: AsyncClientProtocol, folder_id: Union[int, str]):
        """POST /download/archive — request archive creation for a folder."""
        data = await self._request(
            "post", "/download/archive", json={"folder_id": folder_id}
        )
        return models.Archive.model_validate(data or {})

    async def init_archive(self: AsyncClientProtocol, uuid: str):
        """PUT /download/archive/init/{uuid} — initialize a pending archive."""
        data = await self._request("put", f"/download/archive/init/{uuid}")
        return models.Archive.model_validate(data or {})

    # ── Presentations (media) ───────────────────────────────────────────────

    async def get_file_presentation(
        self: AsyncClientProtocol, file_id: Union[int, str], presentation_type: str
    ):
        """GET /presentations/file/{file_id}/{presentation_type}."""
        return await self._request(
            "get", f"/presentations/file/{file_id}/{presentation_type}"
        )

    async def get_folder_presentation(
        self: AsyncClientProtocol,
        folder_id: Union[int, str],
        presentation_type: Optional[str] = None,
    ):
        """GET /presentations/folder/{folder_id}[/{presentation_type}]."""
        path = f"/presentations/folder/{folder_id}"
        if presentation_type:
            path += f"/{presentation_type}"
        return await self._request("get", path)

    async def get_presentation_url(
        self: AsyncClientProtocol,
        collection_type: str,
        target_type: str,
        target_id: Union[int, str],
        presentation_type: str,
    ):
        """GET /presentation/{collection_type}/{target_type}/{target_id}/{presentation_type}/url."""
        path = (
            f"/presentation/{collection_type}/{target_type}/{target_id}"
            f"/{presentation_type}/url"
        )
        return await self._request("get", path)

    # ── Subtitles ───────────────────────────────────────────────────────────

    async def list_subtitles(self: AsyncClientProtocol, file_id: Union[int, str]):
        """GET /subtitles/file/{id}."""
        data = await self._request("get", f"/subtitles/file/{file_id}")
        items = data if isinstance(data, list) else data.get("subtitles", [])
        return [models.Subtitle.model_validate(s) for s in items]

    async def upload_subtitle(
        self: AsyncClientProtocol,
        file_id: Union[int, str],
        subtitle_path: str,
        language: Optional[str] = None,
    ):
        """POST /subtitles/file/{id} — upload a subtitle file."""
        file_name = os.path.basename(subtitle_path)
        path = anyio.Path(subtitle_path)
        content = await path.read_bytes()
        files = {"subtitle_file": (file_name, content)}
        data: Dict[str, Any] = {}
        if language:
            data["language"] = language
        result = await self._request(
            "post", f"/subtitles/file/{file_id}", data=data, files=files
        )
        return models.APIResult.model_validate(result or {})

    async def delete_subtitle(
        self: AsyncClientProtocol, file_id: Union[int, str], sub_id: Union[int, str]
    ):
        """DELETE /subtitles/file/{file_id}/{sub_id}."""
        data = await self._request("delete", f"/subtitles/file/{file_id}/{sub_id}")
        return models.APIResult.model_validate(data or {})

    async def get_subtitle(
        self: AsyncClientProtocol, file_id: Union[int, str], sub_id: Union[int, str]
    ):
        """GET /subtitles/file/{id}/{sub_id}.vtt — raw VTT text."""
        response = await self._raw_request(
            "get", f"/subtitles/file/{file_id}/{sub_id}.vtt"
        )
        return response.text

    async def search_subtitles(
        self: AsyncClientProtocol,
        file_id: Union[int, str],
        language: Optional[str] = None,
        query: Optional[str] = None,
    ):
        """POST /subtitles/v2/search."""
        payload = _request_models.SearchSubtitlesRequest(
            file_id=file_id, language=language, query=query
        )
        data = await self._request(
            "post", "/subtitles/v2/search", json=payload.model_dump(exclude_none=True)
        )
        items = data if isinstance(data, list) else data.get("results", [])
        return [models.SubtitleSearchResult.model_validate(s) for s in items]

    async def download_opensubtitle(
        self: AsyncClientProtocol, file_id: Union[int, str], lang: str
    ):
        """GET /subtitles/v2/download/{file_id}/{lang}/sub.vtt."""
        response = await self._raw_request(
            "get", f"/subtitles/v2/download/{file_id}/{lang}/sub.vtt"
        )
        return response.text

    async def upload_opensubtitle(
        self: AsyncClientProtocol, file_id: Union[int, str], opensubtitles_id: str
    ):
        """POST /subtitles/file/{id}/opensubtitles-v2."""
        data = await self._request(
            "post",
            f"/subtitles/file/{file_id}/opensubtitles-v2",
            json={"opensubtitles_id": opensubtitles_id},
        )
        return models.APIResult.model_validate(data or {})

    # ── Scrape ──────────────────────────────────────────────────────────────

    async def scrape_torrents(self: AsyncClientProtocol, url: str):
        """POST /scrape/html/torrents — extract magnet/torrent links from an HTML page."""
        return await self._request("post", "/scrape/html/torrents", json={"url": url})
