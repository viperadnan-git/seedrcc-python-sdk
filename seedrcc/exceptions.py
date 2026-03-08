import json
from typing import Optional

import httpx


class SeedrError(Exception):
    """Base exception for all seedrcc errors."""


class APIError(SeedrError):
    """
    Raised when the API returns an error.

    Attributes:
        response (Optional[httpx.Response]): The full HTTP response object.
        error_type (Optional[str]): The type of error from the API response body (e.g., 'parsing_error').
    """

    def __init__(
        self,
        message: str = "An API error occurred.",
        response: Optional[httpx.Response] = None,
    ) -> None:
        self.response = response
        self.error_type: Optional[str] = None

        if response:
            message = self._parse_response(response, message)

        super().__init__(message)

    def _parse_response(self, response: httpx.Response, default_message: str) -> str:
        try:
            data = response.json()
            self.error_type = data.get("result") or data.get("reason_phrase")
            if data.get("error"):
                return data.get("error")
            elif self.error_type:
                return f"reason={self.error_type}"
            else:
                return f"{response.status_code} {response.reason_phrase}"
        except json.JSONDecodeError:
            return default_message


class JSONDecodeAPIError(APIError):
    """Raised when the API returns a response that cannot be decoded as JSON."""

    def __init__(
        self,
        response: Optional[httpx.Response] = None,
    ) -> None:
        super().__init__("API returned non-JSON response", response)
        self.error_type = "json_decode_error"

    def _parse_response(self, response: httpx.Response, default_message: str) -> str:
        text = (
            response.text[:200] + "..." if len(response.text) > 200 else response.text
        )
        return f'{default_message}: "{text}"'


class ServerError(SeedrError):
    """Raised for 5xx server-side errors."""

    def __init__(
        self,
        default_message: str = "A server error occurred.",
        response: Optional[httpx.Response] = None,
    ) -> None:
        self.response = response
        if response:
            message = f"{response.status_code} {response.reason_phrase}"
        else:
            message = default_message
        super().__init__(message)


class AuthenticationError(SeedrError):
    """
    Raised when authentication or re-authentication fails.

    Attributes:
        response (Optional[httpx.Response]): The full HTTP response object from the failed auth attempt.
        error_type (Optional[str]): The error type from the API response body (e.g., 'invalid_grant').
    """

    def __init__(
        self,
        default_message: str = "An authentication error occurred.",
        response: Optional[httpx.Response] = None,
    ) -> None:
        self.response = response
        self.error_type: Optional[str] = None
        message = default_message

        # Attempt to parse a more specific error message from the response
        if response:
            try:
                data = response.json()
                if isinstance(data, dict):
                    # Use 'error_description' as the main message if available
                    if "error_description" in data:
                        message = data["error_description"]
                    self.error_type = data.get("error")
            except json.JSONDecodeError:
                pass

        super().__init__(message)


class NetworkError(SeedrError):
    """Raised for network-level errors, such as timeouts or connection problems."""

    pass


class TokenError(SeedrError):
    """Raised for errors related to token serialization or deserialization."""

    pass
