# OMA Backend Integration Guide

## Architecture Overview

This document describes the server-to-server OAuth 2.0 integration between **MCP Google Hub** and **OMA Backend**.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          System Architecture                              │
└──────────────────────────────────────────────────────────────────────────┘

┌─────────────┐         ┌──────────────────┐         ┌─────────────┐
│   Browser   │         │   OMA Backend    │         │   Google    │
│   (User)    │         │   (FastAPI)      │         │   OAuth     │
└──────┬──────┘         └────────┬─────────┘         └──────┬──────┘
       │                         │                          │
       │  1. Login               │                          │
       │────────────────────────>│                          │
       │  JWT Token              │                          │
       │<────────────────────────│                          │
       │                         │                          │
       │  2. Connect Google      │                          │
       │────────────────────────>│                          │
       │                         │  3. OAuth Flow          │
       │                         │────────────────────────>│
       │                         │  4. Access/Refresh Token│
       │                         │<────────────────────────│
       │  5. Success             │                          │
       │<────────────────────────│                          │
       │                         │  [Stores encrypted       │
       │                         │   credentials in DB]     │
       │                         │                          │

┌─────────────┐         ┌──────────────────┐         ┌─────────────┐
│ MCP Google  │         │   OMA Backend    │         │   Google    │
│    Hub      │         │   (FastAPI)      │         │   APIs      │
└──────┬──────┘         └────────┬─────────┘         └──────┬──────┘
       │                         │                          │
       │  6. Get Credentials     │                          │
       │────────────────────────>│                          │
       │  (JWT Token)            │                          │
       │                         │  [Decrypt & refresh      │
       │                         │   if needed]             │
       │  7. OAuth Tokens        │                          │
       │<────────────────────────│                          │
       │                         │                          │
       │  8. API Calls           │                          │
       │─────────────────────────────────────────────────>│
       │                         │                          │
```

## Authentication Flow Details

### Phase 1: User Authentication (Browser → OMA Backend)

**Endpoint:** `POST /api/v1/auth/login`

```bash
curl -X POST https://rndaibot.ru/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "password": "password123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer"
}
```

### Phase 2: Google OAuth Connection (Browser → OMA Backend → Google)

**Step 1: Get OAuth URL**

`GET /api/v1/google/auth/url`

```bash
curl https://rndaibot.ru/api/v1/google/auth/url \
  -H "Authorization: Bearer {OMA_ACCESS_TOKEN}"
```

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?client_id=...",
  "state": "base64_encoded_state_token"
}
```

**Step 2: User Authorizes via Browser**

Browser redirects to `auth_url`, user approves, Google redirects back to:
```
https://rndaibot.ru/api/auth/callback?code=...&state=...
```

**Step 3: OMA Backend Handles Callback**

OMA Backend:
1. Validates state token
2. Exchanges code for tokens
3. Encrypts and stores credentials in database
4. Redirects user back to frontend

### Phase 3: Server-to-Server Access (MCP Hub → OMA Backend)

**Endpoint:** `GET /api/v1/google/credentials`

```bash
curl https://rndaibot.ru/api/v1/google/credentials \
  -H "Authorization: Bearer {OMA_ACCESS_TOKEN}"
```

**Response:**
```json
{
  "access_token": "ya29.a0AfH6SMBx...",
  "refresh_token": "1//0gNvG7Z...",
  "token_expiry": "2024-11-05T15:30:00Z",
  "scopes": [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events"
  ]
}
```

## Implementation Details

### OMA Backend Components

#### 1. Google Service ([app/services/google_service.py](oma-backend/app/services/google_service.py))

```python
class GoogleService:
    @staticmethod
    def get_auth_url(user_id: str, return_url: str) -> GoogleAuthURL:
        """Generate OAuth URL with state token"""

    @staticmethod
    def handle_oauth_callback(db: Session, code: str, state: str) -> GoogleCredential:
        """Handle callback, exchange code for tokens, store encrypted"""

    @staticmethod
    def get_credentials_for_assistant(db: Session, user: User) -> GoogleCredentialsResponse:
        """Get credentials with auto-refresh for server-to-server use"""
```

**Key Features:**
- ✅ State token with CSRF protection (base64 encoded JSON)
- ✅ Encrypted token storage (AES encryption)
- ✅ Automatic token refresh when expired
- ✅ Scope-based access control

#### 2. Google API Routes ([app/api/google.py](oma-backend/app/api/google.py))

```python
@router.get("/auth/url")
def get_google_auth_url(current_user: User = Depends(get_current_user)):
    """Protected endpoint - requires JWT token"""

@auth_callback_router.get("/auth/callback")
async def google_oauth_callback_direct(code: str, state: str, db: Session):
    """Public endpoint - validates via state token"""

@router.get("/credentials")
def get_google_credentials(current_user: User = Depends(get_current_user)):
    """Server-to-server endpoint - returns OAuth tokens"""
```

### MCP Google Hub Components

#### 1. OMA Client ([src/auth/oma_client.py](mcpgoogle/src/auth/oma_client.py))

```python
class OMAAuthClient:
    """HTTP client for OMA Backend communication"""

    def get_google_credentials_sync(self) -> Credentials:
        """Fetch Google credentials from OMA backend"""
        response = client.get(
            f"{self.base_url}/google/credentials",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        return Credentials(
            token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            ...
        )
```

#### 2. Configuration ([src/config.py](mcpgoogle/src/config.py))

```python
# Authentication mode selection
AUTH_MODE: Literal["oma_backend", "local_file"] = "oma_backend"

# OMA Backend settings
OMA_BACKEND_URL = "https://rndaibot.ru/api/v1"
OMA_ACCESS_TOKEN = os.getenv("OMA_ACCESS_TOKEN")

# Google OAuth settings
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
```

#### 3. Google Auth ([src/auth/google_auth.py](mcpgoogle/src/auth/google_auth.py))

```python
def get_google_creds() -> Credentials:
    """Multi-mode authentication"""
    if is_oma_backend_mode():
        return _get_google_creds_from_oma()  # Server-to-server
    else:
        return _get_google_creds_from_local_file()  # Legacy
```

## Security Considerations

### OMA Backend Security

1. **Token Encryption**: Google OAuth tokens encrypted with AES-256
   - Encryption key from `SECRET_KEY` environment variable
   - Stored in database encrypted_at_rest

2. **JWT Authentication**: All protected endpoints require valid JWT
   - Short-lived access tokens (30 minutes)
   - Long-lived refresh tokens (7 days)

3. **State Token Validation**: OAuth callback validates state token
   - Base64 encoded JSON with user_id, return_url, csrf_token
   - Prevents CSRF attacks

4. **HTTPS Required**: All production endpoints use HTTPS
   - OAuth redirect URIs validated

### MCP Hub Security

1. **Access Token Storage**: OMA access token in environment variable
   - Never committed to git
   - Loaded from `.env` file

2. **SSL Verification**: HTTPS verification enabled by default
   - Can be disabled for dev: `OMA_VERIFY_SSL=false`

3. **No Local Credentials**: Google tokens never stored locally
   - Fetched on-demand from OMA Backend
   - Automatically refreshed when expired

## Setup Instructions

### 1. Setup OMA Backend

```bash
cd oma-backend

# Configure environment
cp env.example .env
# Edit .env with:
# - DATABASE_URL
# - SECRET_KEY
# - GOOGLE_CLIENT_ID
# - GOOGLE_CLIENT_SECRET
# - GOOGLE_REDIRECT_URI=https://rndaibot.ru/api/auth/callback

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Setup MCP Google Hub

```bash
cd mcpgoogle

# Configure environment
cp .env.example .env
# Edit .env with:
# - AUTH_MODE=oma_backend
# - OMA_BACKEND_URL=https://rndaibot.ru/api/v1
# - OMA_ACCESS_TOKEN=<your_token>
# - GOOGLE_CLIENT_ID=<same_as_oma_backend>
# - GOOGLE_CLIENT_SECRET=<same_as_oma_backend>

# Install dependencies
pip install -e .

# Run server
fastmcp run src/server.py
```

### 3. User Onboarding

1. User registers/logs in to OMA Backend web interface
2. User connects Google account via OAuth flow
3. User copies access token for MCP Hub configuration
4. MCP Hub can now access Google APIs on behalf of user

## Testing

### Test OAuth Flow

```bash
# 1. Login to OMA Backend
curl -X POST https://rndaibot.ru/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test@example.com", "password": "test123"}' \
  | jq -r '.access_token'

# 2. Get Google auth URL
curl https://rndaibot.ru/api/v1/google/auth/url \
  -H "Authorization: Bearer YOUR_TOKEN" \
  | jq -r '.auth_url'

# 3. Open URL in browser, authorize

# 4. Check credentials
curl https://rndaibot.ru/api/v1/google/credentials \
  -H "Authorization: Bearer YOUR_TOKEN" \
  | jq
```

### Test MCP Hub Integration

```python
# test_oma_integration.py
from src.auth.google_auth import get_google_creds
from googleapiclient.discovery import build

# Get credentials from OMA Backend
creds = get_google_creds()

# Use with Google APIs
gmail = build("gmail", "v1", credentials=creds)
messages = gmail.users().messages().list(userId="me", maxResults=5).execute()
print(f"Found {len(messages.get('messages', []))} messages")
```

## Troubleshooting

### Issue: "OMA_ACCESS_TOKEN environment variable is required"

**Solution:**
```bash
# Get token from login
TOKEN=$(curl -X POST https://rndaibot.ru/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}' \
  | jq -r '.access_token')

# Add to .env
echo "OMA_ACCESS_TOKEN=$TOKEN" >> .env
```

### Issue: "Google account not connected"

**Solution:** User must connect Google account via web interface first:
1. Navigate to `https://rndaibot.ru`
2. Login
3. Settings → Google Integration → Connect

### Issue: "Invalid authentication scheme"

**Solution:** Ensure `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` match between OMA Backend and MCP Hub.

## API Reference

### OMA Backend Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth/login` | POST | None | Login and get JWT tokens |
| `/auth/me` | GET | JWT | Get current user info |
| `/google/auth/url` | GET | JWT | Get Google OAuth URL |
| `/auth/callback` | GET | State | Handle OAuth callback |
| `/google/credentials` | GET | JWT | Get Google OAuth tokens |
| `/google/status` | GET | JWT | Check Google connection status |
| `/google/disconnect/{service}` | DELETE | JWT | Disconnect Google service |

### Response Schemas

**GoogleCredentialsResponse:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_expiry": "datetime",
  "scopes": ["string"]
}
```

**GoogleServiceStatus:**
```json
{
  "gmail_connected": true,
  "calendar_connected": true,
  "token_expiry": "2024-11-05T15:30:00Z"
}
```

## Migration from Legacy Mode

### Old Way (local_file mode):

```python
# Required local files:
# - secrets/credentials.json (from Google Cloud)
# - data/token.json (generated after OAuth)

from src.auth.google_auth import get_google_creds
creds = get_google_creds()  # Opens browser for OAuth
```

### New Way (oma_backend mode):

```env
# .env
AUTH_MODE=oma_backend
OMA_ACCESS_TOKEN=your_jwt_token
```

```python
from src.auth.google_auth import get_google_creds
creds = get_google_creds()  # Fetches from OMA Backend
```

**Benefits:**
- ✅ No local credential files
- ✅ No browser interaction required
- ✅ Centralized credential management
- ✅ Multi-user support
- ✅ Auto token refresh
- ✅ Encrypted storage

## Future Enhancements

- [ ] Redis caching for credentials (reduce OMA Backend calls)
- [ ] WebSocket support for real-time credential updates
- [ ] Credential rotation policies
- [ ] OAuth scope management UI
- [ ] Audit logging integration
- [ ] Multi-tenant support
