# This file is auto-generated — do not edit directly.
# Regenerate with: python scripts/generate_sync.py
"""UserMixin — user profile, quota, settings."""

from .. import models
from ._protocols import ClientProtocol


class UserMixin:
    def get_user(self: ClientProtocol):
        """GET /user. Requires `profile` + `account.read`."""
        return models.User.model_validate(self._request("get", "/user"))

    def get_quota(self: ClientProtocol):
        """GET /me/quota. Requires `account.read`."""
        return models.Quota.model_validate(self._request("get", "/me/quota"))

    def get_settings(self: ClientProtocol):
        """GET /me/settings. Requires `account.read` + `settings.read`."""
        return models.Settings.model_validate(self._request("get", "/me/settings"))
