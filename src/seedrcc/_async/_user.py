"""AsyncUserMixin — user profile, quota, settings."""

from .. import models
from ._protocols import AsyncClientProtocol


class AsyncUserMixin:
    async def get_user(self: AsyncClientProtocol):
        """GET /user. Requires `profile` + `account.read`."""
        return models.User.model_validate(await self._request("get", "/user"))

    async def get_quota(self: AsyncClientProtocol):
        """GET /me/quota. Requires `account.read`."""
        return models.Quota.model_validate(await self._request("get", "/me/quota"))

    async def get_settings(self: AsyncClientProtocol):
        """GET /me/settings. Requires `account.read` + `settings.read`."""
        return models.Settings.model_validate(
            await self._request("get", "/me/settings")
        )
