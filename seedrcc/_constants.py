# Base URLs
BASE_API_URL = "https://www.seedr.cc/api"
OAUTH_URL = "https://www.seedr.cc/oauth_test"

# API Endpoints
RESOURCE_URL = f"{OAUTH_URL}/resource.php"
TOKEN_URL = f"{OAUTH_URL}/token.php"
DEVICE_CODE_URL = f"{BASE_API_URL}/device/code"
DEVICE_AUTHORIZE_URL = f"{BASE_API_URL}/device/authorize"

# Client IDs
DEVICE_CLIENT_ID = "seedr_xbmc"
PSWRD_CLIENT_ID = "seedr_chrome"

# Cookie-based auth [cookie-auth]
COOKIE_BASE_URL = "https://www.seedr.cc"
COOKIE_LOGIN_URL = f"{COOKIE_BASE_URL}/auth/login"

# Browser-like headers for cookie-based auth [cookie-auth]
COOKIE_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "referer": f"{COOKIE_BASE_URL}/files",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
}
