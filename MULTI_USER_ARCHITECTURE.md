# Multi-User OAuth 2.0 Architecture

## Архитектура для множественных пользователей

Система спроектирована для работы с **множественными пользователями**, где каждый пользователь имеет:
- ✅ Свою учетную запись в OMA Backend
- ✅ Свой уникальный JWT access_token
- ✅ Свои собственные Google OAuth credentials (access_token + refresh_token)
- ✅ Полную изоляцию данных между пользователями

## Полный User Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Multi-User OAuth 2.0 Architecture                         │
└─────────────────────────────────────────────────────────────────────────────┘

ПОЛЬЗОВАТЕЛЬ A (alice@example.com)
=================================

1. Registration/Login (NextJS Frontend → OMA Backend)
   ┌──────────┐         ┌──────────────┐
   │ Browser  │ Register│ OMA Backend  │
   │ (Alice)  │────────>│   (FastAPI)  │
   └──────────┘         └──────┬───────┘
                               │
                               │ Creates User Record
                               ▼
                        ┌─────────────────┐
                        │ PostgreSQL DB   │
                        │ users table:    │
                        │ - id: uuid-A    │
                        │ - email: alice@ │
                        │ - password_hash │
                        └─────────────────┘

2. Login (Get JWT Token)
   ┌──────────┐         ┌──────────────┐
   │ Browser  │  POST   │ OMA Backend  │
   │ (Alice)  │ /login  │              │
   │          │────────>│ Validates    │
   │          │         │ credentials  │
   │          │ JWT-A   │              │
   │          │<────────│              │
   └──────────┘         └──────────────┘

   Response: {
     "access_token": "JWT-ALICE-xxx...",  ← Unique per user
     "refresh_token": "REFRESH-ALICE-xxx..."
   }

3. Connect Google Account (NextJS Frontend orchestrates)

   Step 1: Get OAuth URL
   ┌──────────┐         ┌──────────────┐
   │ Browser  │ GET     │ OMA Backend  │
   │ (Alice)  │ /google │ Checks       │
   │          │ /auth/  │ JWT-ALICE    │
   │          │ url     │ Extracts     │
   │          │ Header: │ user_id: A   │
   │          │ Bearer  │              │
   │          │ JWT-A   │ Generates    │
   │          │         │ state with   │
   │          │         │ user_id: A   │
   │          │ OAuth   │              │
   │          │ URL     │              │
   │          │<────────│              │
   └──────────┘         └──────────────┘

   Response: {
     "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
     "state": "base64({user_id: 'uuid-A', csrf_token: 'xxx', ...})"
   }

   Step 2: User authorizes at Google
   ┌──────────┐         ┌─────────────┐
   │ Browser  │ Redirect│   Google    │
   │ (Alice)  │────────>│   OAuth     │
   │          │         │   Server    │
   │          │ Approve │             │
   │          │────────>│             │
   └──────────┘         └──────┬──────┘
                               │ Callback with code
                               │
   Step 3: Callback to OMA Backend
                               │
                               ▼
                        ┌──────────────┐
                        │ OMA Backend  │
                        │ /auth/       │
                        │ callback     │
                        └──────┬───────┘
                               │
                               │ 1. Validates state
                               │ 2. Extracts user_id: A
                               │ 3. Exchanges code for tokens
                               │ 4. Stores encrypted tokens
                               │
                               ▼
                        ┌─────────────────────────────┐
                        │ PostgreSQL DB               │
                        │ google_credentials table:   │
                        │ - id: 1                     │
                        │ - user_id: uuid-A           │ ← Links to Alice
                        │ - access_token: ENCRYPTED   │ ← Alice's Google token
                        │ - refresh_token: ENCRYPTED  │
                        │ - token_expiry: datetime    │
                        │ - scopes: [gmail, calendar] │
                        └─────────────────────────────┘

4. MCP Hub accesses Alice's Google data
   ┌─────────────┐         ┌──────────────┐         ┌─────────┐
   │ MCP Google  │ GET     │ OMA Backend  │         │ Google  │
   │    Hub      │ /google │              │         │  APIs   │
   │             │ /creds  │ 1. Validates │         │         │
   │ Header:     │         │    JWT-ALICE │         │         │
   │ Bearer      │         │ 2. Extracts  │         │         │
   │ JWT-ALICE   │         │    user_id:A │         │         │
   │             │         │ 3. Finds     │         │         │
   │             │         │    Google    │         │         │
   │             │         │    creds     │         │         │
   │             │         │    for A     │         │         │
   │             │         │ 4. Decrypts  │         │         │
   │             │         │ 5. Refreshes │         │         │
   │             │         │    if needed │         │         │
   │ Alice's     │         │              │         │         │
   │ Google      │         │ Returns      │         │         │
   │ Tokens      │<────────│ Alice's      │         │         │
   │             │         │ tokens       │         │         │
   │             │         │              │         │         │
   │ API Call    │─────────────────────────────────>│ Alice's │
   │ with        │                                   │ Gmail   │
   │ Alice's     │<─────────────────────────────────│ Data    │
   │ token       │                                   │         │
   └─────────────┘         └──────────────┘         └─────────┘


ПОЛЬЗОВАТЕЛЬ B (bob@example.com)
=================================

[Same flow as Alice, but with different tokens and data]

Database State:
┌─────────────────────────────┐
│ PostgreSQL DB               │
│                             │
│ users table:                │
│ - id: uuid-A, email: alice@ │
│ - id: uuid-B, email: bob@   │
│                             │
│ google_credentials table:   │
│ - user_id: uuid-A           │ ← Alice's Google tokens
│   access_token: ENC-A       │
│   refresh_token: ENC-A      │
│                             │
│ - user_id: uuid-B           │ ← Bob's Google tokens
│   access_token: ENC-B       │
│   refresh_token: ENC-B      │
└─────────────────────────────┘
```

## Изоляция данных между пользователями

### Database Schema

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Google credentials table (one-to-one with users)
CREATE TABLE google_credentials (
    id SERIAL PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    access_token TEXT NOT NULL,        -- Encrypted with AES-256
    refresh_token TEXT,                -- Encrypted with AES-256
    token_expiry TIMESTAMP,
    scopes TEXT[],                     -- Array of granted scopes
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast lookup by user_id
CREATE INDEX idx_google_credentials_user_id ON google_credentials(user_id);
```

### Security Guarantees

**1. User Isolation via JWT**

Each user has a unique JWT token that includes their `user_id`:

```python
# OMA Backend: app/api/auth.py
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Extract user from JWT token"""
    token = extract_bearer_token(authorization)
    payload = decode_token(token)  # JWT decode
    user_id = payload.get("sub")   # user_id from JWT

    # Fetch user from database
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    return user  # Returns ONLY this user's data
```

**2. Credential Isolation via Foreign Key**

Google credentials are linked to specific users:

```python
# OMA Backend: app/services/google_service.py
@staticmethod
def get_credentials_for_assistant(db: Session, user: User) -> GoogleCredentialsResponse:
    """Get Google credentials for specific user ONLY"""

    # Query filters by user.id - ensures isolation
    google_cred = db.query(GoogleCredential).filter(
        GoogleCredential.user_id == user.id  # ← User isolation
    ).first()

    if not google_cred:
        raise HTTPException(
            status_code=404,
            detail="Google account not connected"
        )

    # Returns ONLY this user's credentials
    return GoogleCredentialsResponse(
        access_token=decrypt_token(google_cred.access_token),
        refresh_token=decrypt_token(google_cred.refresh_token),
        ...
    )
```

**3. Encryption at Rest**

Each user's Google tokens are encrypted with AES-256:

```python
# OMA Backend: app/core/security.py
from cryptography.fernet import Fernet

def encrypt_token(token: str) -> str:
    """Encrypt token with AES-256"""
    f = Fernet(settings.SECRET_KEY.encode())
    return f.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt token with AES-256"""
    f = Fernet(settings.SECRET_KEY.encode())
    return f.decrypt(encrypted_token.encode()).decode()
```

## MCP Hub Multi-User Support

### How MCP Hub Works with Multiple Users

MCP Hub can serve **different users simultaneously** by using their individual JWT tokens:

```python
# Example: Alice uses MCP Hub
import os
os.environ["OMA_ACCESS_TOKEN"] = "JWT-ALICE-xxx..."

from src.auth.google_auth import get_google_creds
creds_alice = get_google_creds()  # Gets Alice's Google credentials

# Gmail API call will access Alice's Gmail
from googleapiclient.discovery import build
gmail = build("gmail", "v1", credentials=creds_alice)
messages = gmail.users().messages().list(userId="me").execute()
# ↑ Returns Alice's emails ONLY
```

```python
# Example: Bob uses MCP Hub (separate instance/session)
import os
os.environ["OMA_ACCESS_TOKEN"] = "JWT-BOB-yyy..."

from src.auth.google_auth import get_google_creds
creds_bob = get_google_creds()  # Gets Bob's Google credentials

# Gmail API call will access Bob's Gmail
gmail = build("gmail", "v1", credentials=creds_bob)
messages = gmail.users().messages().list(userId="me").execute()
# ↑ Returns Bob's emails ONLY
```

### Deployment Scenarios

#### Scenario 1: Per-User MCP Hub Instances

Each user runs their own MCP Hub instance:

```
┌─────────────┐ JWT-A  ┌──────────────┐
│ MCP Hub A   │───────>│ OMA Backend  │──> Alice's Google data
│ (Alice)     │        └──────────────┘
└─────────────┘

┌─────────────┐ JWT-B  ┌──────────────┐
│ MCP Hub B   │───────>│ OMA Backend  │──> Bob's Google data
│ (Bob)       │        └──────────────┘
└─────────────┘
```

**Configuration per user:**
```bash
# Alice's .env
OMA_ACCESS_TOKEN=JWT-ALICE-xxx...

# Bob's .env
OMA_ACCESS_TOKEN=JWT-BOB-yyy...
```

#### Scenario 2: Shared MCP Hub with Dynamic Token Injection

Single MCP Hub instance serving multiple users (advanced):

```python
# Advanced: Dynamic user switching
class MultiUserMCPHub:
    def get_user_credentials(self, user_jwt: str):
        """Get credentials for specific user"""
        client = OMAAuthClient(access_token=user_jwt)
        return client.get_google_credentials_sync()

    def send_email_for_user(self, user_jwt: str, to: str, subject: str, body: str):
        """Send email on behalf of specific user"""
        creds = self.get_user_credentials(user_jwt)
        gmail = build("gmail", "v1", credentials=creds)
        # Send email using user's credentials
        ...
```

## Complete Flow Example: Two Users

```
TIME: T0 - Alice registers and connects Google
================================================

Frontend (NextJS):
  1. Alice visits https://rndaibot.ru
  2. Registers: alice@example.com / password123
  3. Logs in → receives JWT-ALICE
  4. Clicks "Connect Google" → OAuth flow
  5. Authorizes Google → callback

Backend (OMA):
  - User record created: user_id = uuid-A
  - Google credentials stored:
    * user_id: uuid-A
    * access_token: encrypted-alice-token
    * refresh_token: encrypted-alice-refresh

Database:
  users: [uuid-A: alice@example.com]
  google_credentials: [uuid-A → alice's encrypted tokens]


TIME: T1 - Bob registers and connects Google
================================================

Frontend (NextJS):
  1. Bob visits https://rndaibot.ru
  2. Registers: bob@example.com / password456
  3. Logs in → receives JWT-BOB
  4. Clicks "Connect Google" → OAuth flow
  5. Authorizes Google → callback

Backend (OMA):
  - User record created: user_id = uuid-B
  - Google credentials stored:
    * user_id: uuid-B
    * access_token: encrypted-bob-token
    * refresh_token: encrypted-bob-refresh

Database:
  users: [
    uuid-A: alice@example.com,
    uuid-B: bob@example.com
  ]
  google_credentials: [
    uuid-A → alice's encrypted tokens,
    uuid-B → bob's encrypted tokens
  ]


TIME: T2 - Alice uses MCP Hub
================================================

MCP Hub (Alice's instance):
  .env: OMA_ACCESS_TOKEN=JWT-ALICE

Request Flow:
  1. MCP Hub calls get_google_creds()
  2. OMAAuthClient uses JWT-ALICE
  3. GET /api/v1/google/credentials
     Header: Authorization: Bearer JWT-ALICE

OMA Backend:
  4. Decodes JWT-ALICE → user_id = uuid-A
  5. Queries: google_credentials WHERE user_id = uuid-A
  6. Decrypts Alice's tokens
  7. Returns Alice's Google tokens

MCP Hub:
  8. Calls Gmail API with Alice's token
  9. Gets Alice's emails ONLY


TIME: T3 - Bob uses MCP Hub (simultaneous)
================================================

MCP Hub (Bob's instance):
  .env: OMA_ACCESS_TOKEN=JWT-BOB

Request Flow:
  1. MCP Hub calls get_google_creds()
  2. OMAAuthClient uses JWT-BOB
  3. GET /api/v1/google/credentials
     Header: Authorization: Bearer JWT-BOB

OMA Backend:
  4. Decodes JWT-BOB → user_id = uuid-B
  5. Queries: google_credentials WHERE user_id = uuid-B
  6. Decrypts Bob's tokens
  7. Returns Bob's Google tokens

MCP Hub:
  8. Calls Gmail API with Bob's token
  9. Gets Bob's emails ONLY
```

## Security Analysis

### Attack Vectors & Mitigations

**1. Can Alice access Bob's data?**

❌ **NO** - JWT token contains Alice's user_id
- OMA Backend validates JWT and extracts user_id
- Database query filters by user_id
- Alice's JWT cannot be used to access Bob's credentials

**2. Can someone steal Alice's Google token from database?**

❌ **Difficult** - Tokens are encrypted with AES-256
- Encryption key from SECRET_KEY environment variable
- Attacker needs both:
  * Database access
  * SECRET_KEY value

**3. Can Alice reuse her JWT token indefinitely?**

❌ **NO** - JWT tokens expire
- Access token: 30 minutes lifetime
- Refresh token: 7 days lifetime
- User must re-authenticate periodically

**4. Can someone impersonate Alice by stealing her JWT?**

⚠️ **Partially** - If JWT is stolen:
- Attacker can access Alice's data until token expires
- **Mitigation**: Short token lifetime (30 min)
- **Best Practice**: Use HTTPS only, secure token storage

## Configuration Per User

### Alice's MCP Hub Configuration

```env
# alice/.env
AUTH_MODE=oma_backend
OMA_BACKEND_URL=https://rndaibot.ru/api/v1
OMA_ACCESS_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1dWlkLUEiLCJ0eXBlIjoiYWNjZXNzIn0...
GOOGLE_CLIENT_ID=your-app.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret
```

### Bob's MCP Hub Configuration

```env
# bob/.env
AUTH_MODE=oma_backend
OMA_BACKEND_URL=https://rndaibot.ru/api/v1
OMA_ACCESS_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1dWlkLUIiLCJ0eXBlIjoiYWNjZXNzIn0...
GOOGLE_CLIENT_ID=your-app.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret
```

**Key Differences:**
- ✅ Different `OMA_ACCESS_TOKEN` values
- ✅ Same `OMA_BACKEND_URL` (shared backend)
- ✅ Same `GOOGLE_CLIENT_ID` (same OAuth app)

## Testing Multi-User Scenarios

```bash
# Terminal 1: Alice's session
export OMA_ACCESS_TOKEN="JWT-ALICE-xxx..."
cd mcpgoogle-alice
python examples/oma_backend_example.py
# → Accesses Alice's Gmail

# Terminal 2: Bob's session (concurrent)
export OMA_ACCESS_TOKEN="JWT-BOB-yyy..."
cd mcpgoogle-bob
python examples/oma_backend_example.py
# → Accesses Bob's Gmail

# Both run simultaneously, data is isolated
```

## Summary

✅ **Архитектура полностью поддерживает multi-user OAuth 2.0:**

1. **Каждый пользователь имеет:**
   - Уникальный аккаунт в OMA Backend (user_id)
   - Собственный JWT access_token
   - Собственные Google OAuth credentials (access + refresh tokens)
   - Полную изоляцию данных

2. **Frontend (NextJS) обеспечивает:**
   - Регистрацию/логин пользователей
   - Google OAuth flow для каждого пользователя
   - Управление JWT токенами (cookies)

3. **OMA Backend гарантирует:**
   - Изоляцию credentials по user_id
   - Шифрование токенов в БД
   - JWT-based authentication
   - Автоматический refresh токенов

4. **MCP Hub получает:**
   - Credentials для конкретного пользователя по JWT
   - Доступ только к данным этого пользователя
   - Прозрачную работу с Google APIs

**Каждая почта = отдельный пользователь = отдельные токены = полная изоляция!** ✅
