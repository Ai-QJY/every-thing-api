# AI Browser Automation API - Login Modes Documentation

This document describes the various login methods available for the AI Browser Automation API service.

## Overview

The API supports multiple login modes to accommodate different use cases and security requirements:

1. **Manual Account/Password Login** - Traditional username/password authentication
2. **OAuth Authorization Login** - Third-party authorization via OAuth providers
3. **Manual Session/Cookie Injection** - Direct session/cookie injection for advanced users

## 1. Manual Account/Password Login

This is the standard login method that requires manual interaction through a real browser.

### API Endpoint

```http
POST /api/session/login
```

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `username` | string | Yes | Your account username/email |
| `password` | string | Yes | Your account password |
| `remember_me` | boolean | No | Remember login session (default: true) |

### Example Request

```bash
curl -X POST http://localhost:8000/api/session/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password", "remember_me": true}'
```

### Response

```json
{
  "success": true,
  "message": "Login successful"
}
```

### How It Works

1. The API launches a real Chromium browser window
2. Navigates to the AI website's login page
3. Automatically fills in the username and password fields
4. Submits the login form
5. Waits for successful login confirmation
6. Persists the browser session for future use

### Notes

- This method requires a display server (X11 on Linux) for the browser to open
- The browser window will be visible during the login process
- Session data is stored in `./sessions/user_data/` directory
- Login state persists across API restarts

## 2. OAuth Authorization Login

For websites that support OAuth authentication, you can use third-party authorization providers.

### API Endpoint

```http
POST /api/session/oauth-login
```

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `provider` | string | Yes | OAuth provider name (e.g., "google", "github", "twitter") |
| `auth_code` | string | Yes | Authorization code from OAuth provider |
| `redirect_uri` | string | No | Redirect URI used during OAuth flow |
| `remember_me` | boolean | No | Remember login session (default: true) |

### Example Request

```bash
curl -X POST http://localhost:8000/api/session/oauth-login \
  -H "Content-Type: application/json" \
  -d '{"provider": "google", "auth_code": "your_auth_code", "redirect_uri": "http://localhost:8000/callback"}'
```

### Response

```json
{
  "success": true,
  "message": "OAuth login successful",
  "provider": "google",
  "session_id": "abc123-xyz456"
}
```

### OAuth Flow

1. **Initiate OAuth Flow** (Client-side):
   - Redirect user to OAuth provider's authorization URL
   - Example: `https://accounts.google.com/o/oauth2/auth?client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&response_type=code&scope=email%20profile`

2. **Handle OAuth Callback** (Client-side):
   - Receive authorization code from OAuth provider
   - Exchange code for access token (if needed)

3. **Complete Login** (API):
   - Send authorization code to the API
   - API completes the OAuth flow and establishes browser session

### Supported OAuth Providers

The API supports OAuth providers that are compatible with the target AI websites. Common providers include:

- Google
- GitHub
- Twitter/X
- Microsoft
- Apple

### Notes

- OAuth support depends on the target AI website's authentication options
- You need to register your application with the OAuth provider
- OAuth credentials (client ID, client secret) should be configured in the API
- This method may not require manual browser interaction

## 3. Manual Session/Cookie Injection

For advanced users who want to bypass the login process entirely, you can directly inject session cookies.

### API Endpoint

```http
POST /api/session/inject-cookies
```

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `cookies` | array | Yes | Array of cookie objects |
| `user_agent` | string | No | User agent string for the session |
| `remember_me` | boolean | No | Remember session (default: true) |

### Cookie Object Structure

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Cookie name |
| `value` | string | Yes | Cookie value |
| `domain` | string | Yes | Cookie domain |
| `path` | string | No | Cookie path (default: "/") |
| `expires` | number | No | Expiration timestamp (seconds since epoch) |
| `httpOnly` | boolean | No | HTTP-only flag |
| `secure` | boolean | No | Secure flag |
| `sameSite` | string | No | SameSite policy ("Lax", "Strict", "None") |

### Example Request

```bash
curl -X POST http://localhost:8000/api/session/inject-cookies \
  -H "Content-Type: application/json" \
  -d '{
    "cookies": [
      {
        "name": "session_id",
        "value": "your_session_id_here",
        "domain": ".grok.ai",
        "path": "/",
        "expires": 1735689600,
        "httpOnly": true,
        "secure": true,
        "sameSite": "Lax"
      },
      {
        "name": "auth_token",
        "value": "your_auth_token_here",
        "domain": ".grok.ai",
        "path": "/",
        "httpOnly": true,
        "secure": true
      }
    ],
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "remember_me": true
  }'
```

### Response

```json
{
  "success": true,
  "message": "Cookies injected successfully",
  "session_valid": true,
  "cookie_count": 2
}
```

### How to Obtain Session Cookies

To use this method, you need valid session cookies from the target AI website:

1. **Manual Extraction**:
   - Log in to the AI website using a regular browser
   - Use browser developer tools to copy cookies
   - Export cookies in the required format

2. **From Existing Session**:
   - If you have an existing valid session, you can extract cookies from the session storage

3. **From OAuth Flow**:
   - After completing an OAuth login, extract the resulting session cookies

### Notes

- Cookies must be valid and not expired
- Domain and path must match the target website exactly
- HTTP-only and secure flags should match the original cookies
- This method bypasses the normal login flow entirely
- Useful for testing, development, or when you already have valid sessions

## Session Management API

### Check Session Status

```http
GET /api/session/status
```

**Response:**
```json
{
  "logged_in": true,
  "session_valid": true,
  "session_expiry": "2023-12-31T23:59:59Z",
  "browser_type": "chromium"
}
```

### Logout

```http
POST /api/session/logout
```

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

## Error Handling

### Common Error Responses

**Invalid Credentials (401 Unauthorized):**
```json
{
  "detail": "Login failed. Please check credentials."
}
```

**Invalid OAuth Code (401 Unauthorized):**
```json
{
  "detail": "OAuth login failed. Invalid authorization code."
}
```

**Invalid Cookies (401 Unauthorized):**
```json
{
  "detail": "Session injection failed. Invalid or expired cookies."
}
```

**Browser Error (503 Service Unavailable):**
```json
{
  "detail": "Login failed: Browser initialization error"
}
```

## Security Considerations

### Best Practices

1. **Credential Storage**: Never hardcode credentials in your application
2. **HTTPS**: Always use HTTPS in production environments
3. **Session Isolation**: Each user should have separate browser contexts
4. **Cookie Security**: Handle cookies securely, especially HTTP-only cookies
5. **Rate Limiting**: Implement rate limiting to prevent abuse

### Risks

1. **Manual Cookie Injection**: Injecting invalid cookies may cause session corruption
2. **OAuth Security**: Ensure OAuth credentials are properly secured
3. **Session Persistence**: Long-lived sessions may be compromised if not properly secured

## Troubleshooting

### Login Fails with Valid Credentials

- Check if the website URL in configuration is correct
- Verify the website is accessible and not down
- Ensure you're not being rate-limited
- Check if the website has changed its login UI (selectors may need updating)

### OAuth Login Fails

- Verify your OAuth client credentials are correct
- Check if the redirect URI matches exactly
- Ensure the OAuth provider is supported by the target website
- Check if the authorization code has expired

### Cookie Injection Fails

- Verify cookies are not expired
- Check domain and path match exactly
- Ensure all required cookies are included
- Verify the user agent is compatible

### Browser Doesn't Open

- Ensure `HEADLESS=False` in configuration
- Check if you have a display server running (X11 on Linux)
- Try running with `DISPLAY=:0` environment variable

## Advanced Usage

### Session Persistence

Sessions are automatically persisted to disk and can survive API restarts:

```bash
# Session files are stored in:
./sessions/user_data/

# Session metadata:
./sessions/grok_session.json
```

### Multiple AI Websites

The API supports multiple AI websites through the adapter pattern. Login modes work consistently across all supported websites.

### Custom User Agents

You can specify custom user agents for different login modes to simulate different browsers.

## Configuration

### Session Configuration

```env
# Session settings in .env file
SESSION_DIR=./sessions
BROWSER_TYPE=chromium
HEADLESS=False
```

### OAuth Configuration

```env
# OAuth settings (example for Google)
OAUTH_GOOGLE_CLIENT_ID=your_client_id
OAUTH_GOOGLE_CLIENT_SECRET=your_client_secret
OAUTH_GOOGLE_REDIRECT_URI=http://localhost:8000/callback
```

## Future Enhancements

The login system may be enhanced in future versions with:

- **Automated Session Recovery**: Automatic re-login when sessions expire
- **Multi-Factor Authentication**: Support for MFA flows
- **Session Sharing**: Share sessions across multiple API instances
- **Enhanced OAuth Support**: More OAuth providers and flows

## Appendix: Cookie Formats

### Browser Export Format

Most browsers allow exporting cookies in JSON format that can be adapted for this API.

### Playwright Cookie Format

The API uses Playwright-compatible cookie format:

```json
{
  "name": "cookie_name",
  "value": "cookie_value",
  "domain": ".example.com",
  "path": "/",
  "expires": 1735689600,  // Unix timestamp in seconds
  "httpOnly": true,
  "secure": true,
  "sameSite": "Lax"
}
```

### Converting from Browser DevTools

1. Open DevTools in your browser (F12)
2. Go to Application > Cookies
3. Copy cookies and format them according to the API specification

## Support

For issues with login modes:

- Check the API logs for detailed error information
- Verify your credentials and cookies are valid
- Consult the specific AI website's authentication documentation
- Review the browser automation logs for any UI-related issues