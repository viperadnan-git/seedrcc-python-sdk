"""Response models for the public OAuth 2.0 API.

All models are frozen Pydantic v2 `BaseModel`s with `extra="allow"` so that
unknown fields from the API are preserved on the instance (accessible via
`model.__pydantic_extra__` or the convenience `model.get_raw()`).
"""

from datetime import datetime
from typing import Annotated, Any, List, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from seedrcc.public.token import Token

__all__ = [
    "DeviceCode",
    "RegisteredApp",
    "AppList",
    "User",
    "UserProfile",
    "UserAccount",
    "UserStorage",
    "UserFeatures",
    "Quota",
    "Settings",
    "Folder",
    "File",
    "TaskInProgress",
    "TorrentTask",
    "AddTaskResult",
    "FolderContents",
    "TaskList",
    "TaskProgress",
    "UnwantedEntries",
    "Subtitle",
    "SubtitleSearchResult",
    "Archive",
    "FileDownloadUrl",
    "SearchResults",
    "PersonalAccessToken",
    "PersonalAccessTokenCreated",
    "AuthorizedDevice",
    "TermsAcceptance",
    "APIResult",
]


# ── Shared helpers ──────────────────────────────────────────────────────────


def _parse_seedr_datetime(v: Any) -> Optional[datetime]:
    """Parses Seedr's `YYYY-MM-DD HH:MM:SS` timestamp format (and unix seconds)."""
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, (int, float)):
        try:
            return datetime.fromtimestamp(v)
        except (ValueError, OSError):
            return None
    try:
        return datetime.strptime(str(v), "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        pass
    # Fall back to Pydantic's built-in ISO parsing
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


SeedrDateTime = Annotated[Optional[datetime], BeforeValidator(_parse_seedr_datetime)]


def _split_scopes(v: Any) -> Any:
    """Accept space-delimited strings and return a list of scopes."""
    return v.split() if isinstance(v, str) else v


ScopeList = Annotated[List[str], BeforeValidator(_split_scopes)]


class _BaseModel(BaseModel):
    """Base for all response models.

    Frozen (immutable), accepts and preserves extra fields from the API (they
    land in `self.__pydantic_extra__`), and trims surrounding whitespace on
    string inputs.

    Use the standard Pydantic API:
        Model.model_validate(dict_data)
        Model.model_validate_json(json_str)
        instance.model_dump()
        instance.model_dump_json()
    """

    model_config = ConfigDict(
        frozen=True,
        extra="allow",
        str_strip_whitespace=True,
        populate_by_name=True,
    )


# ── OAuth ────────────────────────────────────────────────────────────────────


class DeviceCode(_BaseModel):
    """Returned by POST /oauth/device/code."""

    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str
    expires_in: int
    interval: int = 5


class RegisteredApp(_BaseModel):
    """An entry from GET /oauth/apps."""

    client_id: str
    name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    homepage_url: Optional[str] = None
    category: Optional[str] = None
    developer_name: Optional[str] = None
    developer_email: Optional[str] = None
    privacy_policy_url: Optional[str] = None
    terms_url: Optional[str] = None


class AppList(_BaseModel):
    """Pagination envelope for registered apps."""

    apps: List[RegisteredApp] = []
    total: int = 0
    page: int = 1
    limit: int = 15
    total_pages: int = 1


# ── User / Account ───────────────────────────────────────────────────────────


class UserProfile(_BaseModel):
    """The `profile` block inside GET /user."""

    id: int = 0
    email: str = ""
    username: str = ""
    created_at: Optional[int] = None
    last_login: Optional[int] = None


class UserStorage(_BaseModel):
    """The `account.storage` block inside GET /user."""

    limit: int = 0
    used: int = 0
    scope: str = "user"
    pool_name: Optional[str] = None


class UserFeatures(_BaseModel):
    """The `account.features` block inside GET /user."""

    max_torrents: Any = None
    active_torrents: int = 0
    max_wishlist: int = 0
    concurrent_downloads: int = 0


class UserAccount(_BaseModel):
    """The `account` block inside GET /user."""

    is_premium: bool = False
    storage: UserStorage = UserStorage()
    features: UserFeatures = UserFeatures()


class User(_BaseModel):
    """GET /user — mirrors the API response shape as-is."""

    profile: UserProfile = UserProfile()
    account: UserAccount = UserAccount()


class Quota(_BaseModel):
    """GET /me/quota."""

    bandwidth_used: int = 0
    bandwidth_max: int = 0
    space_used: int = 0
    space_max: int = 0
    space_scope: str = "user"
    is_premium: bool = False


class Settings(_BaseModel):
    """GET /me/settings."""

    subtitles_language: Optional[str] = None
    site_language: Optional[str] = None
    email_newsletter: int = 0
    email_announcements: int = 0
    email_task_notifications_enabled: bool = False
    select_files_on_task_add: int = 0
    user_id: Optional[int] = Field(default=None, alias="userId")


# ── Files & Folders ──────────────────────────────────────────────────────────


class File(_BaseModel):
    """A file entry inside a folder listing."""

    id: int = 0
    name: str = ""
    size: int = 0
    hash: str = ""
    last_update: SeedrDateTime = None
    is_audio: bool = False
    is_video: bool = False
    video_progress: Optional[str] = None
    thumb: Optional[str] = None


class TaskInProgress(_BaseModel):
    """A torrent task embedded in folder listings (not a full Task)."""

    id: int = 0
    name: str = ""
    size: int = 0
    progress: float = 0.0
    hash: str = ""


class Folder(_BaseModel):
    """A folder node. Returned by /fs/root, /fs/folder/{id}."""

    id: int = 0
    name: str = ""
    fullname: str = ""
    path: str = ""
    size: int = 0
    parent: Optional[int] = None
    timestamp: SeedrDateTime = None
    space_max: int = 0
    space_used: int = 0
    space_scope: str = "user"

    @model_validator(mode="before")
    @classmethod
    def _fill_fullname(cls, data: Any) -> Any:
        # API sometimes omits `fullname`; mirror legacy behavior of defaulting to `path`.
        if isinstance(data, dict) and "fullname" not in data and "path" in data:
            return {**data, "fullname": data.get("path", "")}
        return data


class FolderContents(_BaseModel):
    """GET /fs/folder/{id}/contents or /fs/root/contents."""

    id: int = 0
    name: str = ""
    path: str = ""
    parent: Optional[int] = None
    size: int = 0
    space_max: int = 0
    space_used: int = 0
    folders: List[Folder] = []
    files: List[File] = []
    torrents: List[TaskInProgress] = []
    tasks: List[TaskInProgress] = []


# ── Tasks (torrents) ─────────────────────────────────────────────────────────


class TorrentTask(_BaseModel):
    """A torrent task record from /tasks or /tasks/{id}.

    `progress` is a percentage (0-100). Torrent-specific peer stats come from
    the nested `torrent_payload` and are flattened onto this model for
    convenience.
    """

    id: int = 0
    name: str = ""
    type: str = "torrent"
    state: Optional[str] = None
    progress: float = 0.0  # 0..100
    size: int = 0
    storage_size: int = 0
    folder_id: Optional[int] = None
    folder_created_id: Optional[int] = None
    items_total: int = 0
    items_completed: int = 0
    error: Optional[str] = None
    created_at: SeedrDateTime = None
    started_at: SeedrDateTime = None
    updated_at: SeedrDateTime = None
    completed_at: SeedrDateTime = None
    last_update: SeedrDateTime = None
    # Flattened from torrent_payload
    hash: str = ""
    seeders: int = 0
    leechers: int = 0
    connected_to: int = 0
    downloading_from: int = 0
    uploading_to: int = 0
    download_rate: int = 0
    stopped: int = 0
    is_private: bool = False
    torrent_quality: Optional[int] = None
    progress_url: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _unwrap_and_flatten(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # GET /tasks/{id} returns {"task": {...}, "success": true}
        if "task" in data and isinstance(data["task"], dict):
            data = data["task"]
        # Merge torrent_payload into the top level
        tp = data.get("torrent_payload")
        if isinstance(tp, dict):
            return {**tp, **data}  # top-level wins on conflict
        return data


class AddTaskResult(_BaseModel):
    """Response from POST /tasks."""

    user_torrent_id: int = 0
    title: str = ""
    torrent_hash: str = ""
    success: bool = True


class TaskList(_BaseModel):
    """GET /tasks."""

    tasks: List[TorrentTask] = []
    user_id: Optional[int] = None


class TaskProgress(_BaseModel):
    """GET /tasks/{id}/progress.

    Returns a pointer (`url`) to a subnode's JSONP-style progress endpoint that
    serves a base64-encoded progress bitmap. The URL is short-lived and already
    includes the auth token — fetch it directly.
    """

    id: str = ""
    url: str = ""

    @model_validator(mode="before")
    @classmethod
    def _stringify_id(cls, data: Any) -> Any:
        if isinstance(data, dict) and "id" in data and not isinstance(data["id"], str):
            return {**data, "id": str(data["id"])}
        return data


class UnwantedEntries(_BaseModel):
    """GET /tasks/{id}/unwanted — list of file indexes marked as unwanted."""

    unwanted: List[int] = []


# ── Subtitles ────────────────────────────────────────────────────────────────


class Subtitle(_BaseModel):
    """A subtitle entry for a file."""

    id: int = 0
    name: str = ""
    language: Optional[str] = None
    url: Optional[str] = None


class SubtitleSearchResult(_BaseModel):
    """POST /subtitles/v2/search result item (OpenSubtitles shape)."""

    id: str = ""
    language: Optional[str] = None
    title: Optional[str] = None
    release: Optional[str] = None
    rating: Optional[float] = None
    downloads: Optional[int] = None


# ── Archives ─────────────────────────────────────────────────────────────────


class Archive(_BaseModel):
    """POST /download/archive or PUT /download/archive/init/{uuid}."""

    uuid: Optional[str] = None
    url: Optional[str] = None
    status: Optional[str] = None


class FileDownloadUrl(_BaseModel):
    """GET /download/file/{id}/url — signed direct download URL (short-lived)."""

    url: str
    name: str
    success: bool


# ── Search ───────────────────────────────────────────────────────────────────


class SearchResults(_BaseModel):
    """GET /search/fs."""

    name: str = ""
    path: str = ""
    max_space: int = 0
    used_space: int = 0
    space_scope: str = "user"
    folders: List[Folder] = []
    files: List[File] = []
    torrents: List[TaskInProgress] = []


# ── Personal Access Tokens ───────────────────────────────────────────────────


class PersonalAccessToken(_BaseModel):
    """An entry from GET /account/pats.

    `token_hash` is the stable identifier used for revocation; the raw token
    value is only returned once at creation time.
    """

    token_hash: str = ""
    name: str = ""
    scopes: ScopeList = []
    created_at: Optional[str] = None
    last_used_at: Optional[str] = None
    expires_at: Optional[str] = None


class PersonalAccessTokenCreated(_BaseModel):
    """Response from POST /account/pats — `token` is only returned here."""

    token: str
    token_hash: str
    name: str
    scopes: ScopeList = []
    expires_at: Optional[datetime] = None
    message: Optional[str] = None

    def to_token(self) -> Token:
        return Token(
            access_token=self.token,
            scope=" ".join(self.scopes),
            expires_at=int(self.expires_at.timestamp()) if self.expires_at else None,
        )


# ── Authorized Devices ──────────────────────────────────────────────────────


class AuthorizedDevice(_BaseModel):
    """An authorized OAuth device (device-flow registration).

    Scraped from the `/console/devices` page — no JSON endpoint exists.
    `device_code` is the stable identifier used to revoke the device.
    """

    name: str = ""
    device_code: str = ""
    first_authorized_at: Optional[str] = None
    last_used_at: Optional[str] = None


class TermsAcceptance(_BaseModel):
    """Response from POST /me/accept-terms — server-side stored state."""

    success: bool
    accepted_terms: bool
    newsletter: bool


# ── Generic ──────────────────────────────────────────────────────────────────


class APIResult(_BaseModel):
    """Generic success/failure envelope used by write endpoints that return no body."""

    result: bool = True
    code: Optional[int] = None
    error: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_result(cls, data: Any) -> Any:
        # Some cookie-API responses use `success` instead of `result`.
        if isinstance(data, dict):
            if "result" not in data and "success" in data:
                return {**data, "result": bool(data["success"])}
        return data
