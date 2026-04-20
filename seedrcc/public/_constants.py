"""Constants for the public OAuth 2.0 API (/api/v0.1/p/*)."""

BASE_URL = "https://www.seedr.cc"
API_V0_1 = f"{BASE_URL}/api/v0.1"
PUBLIC_API = f"{API_V0_1}/p"

# OAuth 2.0
DEVICE_CODE_URL = f"{PUBLIC_API}/oauth/device/code"
DEVICE_TOKEN_URL = f"{PUBLIC_API}/oauth/device/token"
DEVICE_VERIFY_URL = f"{PUBLIC_API}/oauth/device/verify"
TOKEN_URL = f"{PUBLIC_API}/oauth/token"
REVOKE_URL = f"{PUBLIC_API}/oauth/token/revoke_rfc7009"
APPS_URL = f"{PUBLIC_API}/oauth/apps"

# Cookie login (used transiently for headless device approval)
COOKIE_LOGIN_URL = f"{BASE_URL}/auth/login"

# Personal Access Tokens (requires cookie session + CSRF, not bearer)
PATS_URL = f"{API_V0_1}/account/pats"
# Accept-terms onboarding (cookie session; no CSRF needed)
ACCEPT_TERMS_URL = f"{API_V0_1}/me/accept-terms"
# Authorized devices: list scraped from the console page; revoke via
# developer endpoint with form-scoped CSRF (one token per rendered form).
DEVICES_CONSOLE_URL = f"{API_V0_1}/console/devices"
DEVICE_REVOKE_URL_TEMPLATE = f"{API_V0_1}/developer/devices/{{device_code}}/revoke"
# Page that exposes a usable CSRF token in its HTML
CSRF_SOURCE_URL = f"{API_V0_1}/console/documentation"

# OAuth grant types
GRANT_DEVICE_CODE = "urn:ietf:params:oauth:grant-type:device_code"
GRANT_REFRESH_TOKEN = "refresh_token"

# Registered OAuth client_ids (public app registry at /api/v0.1/p/oauth/apps)
CLIENT_ID_JELLYFIN = "2nFVuW1jvHk4cdggrru203G9v4f2jrnf"
CLIENT_ID_KODI = "EKp43IJEBXiGjaRg6cd7F17R3z3zv6VL"
CLIENT_ID_PYSEEDR = "MSdSo3q61ePf8uQOThtpiELi7bME93ph"
CLIENT_ID_ROKU = "2Ynz4SpC92zjz6lg6uEAhaETKMGN5DAC"
CLIENT_ID_SONARR = "yWbNgXonQzzPY2osP9fJQzN3Sv00YECC"
CLIENT_ID_STREMIO = "nHxVvl5nIgQyyiG55EwMPWWss3ALccSM"

DEFAULT_CLIENT_ID = CLIENT_ID_KODI

# Scopes
SCOPE_PROFILE = "profile"
SCOPE_ACCOUNT_READ = "account.read"
SCOPE_ACCOUNT_WRITE = "account.write"
SCOPE_SETTINGS_READ = "settings.read"
SCOPE_SETTINGS_WRITE = "settings.write"
SCOPE_FILES_READ = "files.read"
SCOPE_FILES_WRITE = "files.write"
SCOPE_TASKS_READ = "tasks.read"
SCOPE_TASKS_WRITE = "tasks.write"
SCOPE_ARCHIVES_MANAGE = "archives.manage"
SCOPE_MEDIA_READ = "media.read"
SCOPE_SUBTITLES_READ = "subtitles.read"
SCOPE_SUBTITLES_WRITE = "subtitles.write"

ALL_SCOPES = [
    SCOPE_PROFILE,
    SCOPE_ACCOUNT_READ,
    SCOPE_ACCOUNT_WRITE,
    SCOPE_SETTINGS_READ,
    SCOPE_SETTINGS_WRITE,
    SCOPE_FILES_READ,
    SCOPE_FILES_WRITE,
    SCOPE_TASKS_READ,
    SCOPE_TASKS_WRITE,
    SCOPE_ARCHIVES_MANAGE,
    SCOPE_MEDIA_READ,
    SCOPE_SUBTITLES_READ,
    SCOPE_SUBTITLES_WRITE,
]

DEFAULT_SCOPE = " ".join(ALL_SCOPES)

# Browser-like headers required by the cookie-protected device approval page
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)

BROWSER_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "user-agent": USER_AGENT,
}
