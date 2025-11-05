# Next.js Integration: Automatic Docker Container Management

## Проблема

Текущая Docker архитектура требует **ручного** запуска контейнера для каждого пользователя. Но пользователи регистрируются через Next.js Frontend. Как автоматизировать?

## ✅ Решение: Container Orchestration Service

### Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                Next.js + Docker Orchestration                    │
└─────────────────────────────────────────────────────────────────┘

1️⃣ User Registration Flow:

User → Next.js → OMA Backend
                     ↓
            Создается user record
            Возвращается JWT
                     ↓
         Next.js вызывает Orchestrator API
                     ↓
         POST /containers/create
         {
           username: "alice",
           password: "alice_pass"
         }
                     ↓
         Orchestrator запускает Docker контейнер:
         docker run -e MCP_USERNAME=alice \
                    -e MCP_PASSWORD=alice_pass \
                    mcpgoogle:latest
                     ↓
         Контейнер стартует →
         docker-entrypoint.sh →
         Получает JWT автоматически →
         MCP Hub готов!


2️⃣ User Login Flow:

User → Next.js (login) → JWT в cookies
                            ↓
                 Проверяет статус контейнера
                            ↓
         GET /containers/status/alice
                            ↓
         Если контейнер НЕ запущен:
           → Запускает контейнер
         Если контейнер запущен:
           → Ничего не делает
```

### Вариант 1: Node.js Orchestrator Service

Создать отдельный Node.js сервис для управления Docker контейнерами:

**Структура:**

```
orchestrator-service/
├── src/
│   ├── server.ts          # Express/Fastify server
│   ├── docker-manager.ts  # Docker API client
│   └── routes/
│       └── containers.ts  # CRUD для контейнеров
├── package.json
└── Dockerfile
```

**API Endpoints:**

```typescript
// POST /containers/create
// Создает и запускает контейнер для пользователя
{
  "username": "alice",
  "password": "alice_password",
  "email": "alice@example.com"
}

// GET /containers/status/:username
// Проверяет статус контейнера пользователя
Response: {
  "status": "running" | "stopped" | "not_exists",
  "port": 3001,
  "health": "healthy"
}

// DELETE /containers/:username
// Останавливает и удаляет контейнер
```

**Реализация (TypeScript):**

```typescript
// src/docker-manager.ts
import Docker from 'dockerode';

const docker = new Docker();

export class DockerManager {
  async createUserContainer(username: string, password: string): Promise<string> {
    // Проверяем, есть ли уже контейнер
    const existing = await this.getContainer(username);
    if (existing) {
      return existing.id;
    }

    // Находим свободный порт
    const port = await this.findFreePort();

    // Создаем контейнер
    const container = await docker.createContainer({
      Image: 'mcpgoogle:latest',
      name: `mcpgoogle-${username}`,
      Env: [
        'AUTH_MODE=oma_backend',
        'OMA_BACKEND_URL=https://rndaibot.ru/apib/v1',
        `MCP_USERNAME=${username}`,
        `MCP_PASSWORD=${password}`,
        `GOOGLE_CLIENT_ID=${process.env.GOOGLE_CLIENT_ID}`,
        `GOOGLE_CLIENT_SECRET=${process.env.GOOGLE_CLIENT_SECRET}`,
      ],
      HostConfig: {
        PortBindings: {
          '8000/tcp': [{ HostPort: port.toString() }]
        },
        RestartPolicy: {
          Name: 'unless-stopped'
        }
      },
      Labels: {
        'com.mcpgoogle.user': username,
        'com.mcpgoogle.managed': 'true'
      }
    });

    // Запускаем контейнер
    await container.start();

    return container.id;
  }

  async getContainer(username: string): Promise<Docker.Container | null> {
    const containers = await docker.listContainers({ all: true });
    const found = containers.find(c => c.Names.includes(`/mcpgoogle-${username}`));

    return found ? docker.getContainer(found.Id) : null;
  }

  async getContainerStatus(username: string): Promise<{
    status: string;
    port?: number;
    health?: string;
  }> {
    const container = await this.getContainer(username);

    if (!container) {
      return { status: 'not_exists' };
    }

    const info = await container.inspect();

    return {
      status: info.State.Status,
      port: info.NetworkSettings.Ports['8000/tcp']?.[0]?.HostPort,
      health: info.State.Health?.Status
    };
  }

  private async findFreePort(): Promise<number> {
    // Находим следующий свободный порт начиная с 3001
    const containers = await docker.listContainers();
    const usedPorts = new Set(
      containers.flatMap(c =>
        Object.values(c.Ports)
          .filter(p => p.PublicPort)
          .map(p => p.PublicPort)
      )
    );

    let port = 3001;
    while (usedPorts.has(port)) {
      port++;
    }
    return port;
  }
}
```

**Express Routes:**

```typescript
// src/routes/containers.ts
import { Router } from 'express';
import { DockerManager } from '../docker-manager';

const router = Router();
const dockerManager = new DockerManager();

// Создать контейнер для пользователя
router.post('/create', async (req, res) => {
  try {
    const { username, password } = req.body;

    const containerId = await dockerManager.createUserContainer(username, password);

    res.json({
      success: true,
      containerId,
      message: `Container created for user ${username}`
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Проверить статус контейнера
router.get('/status/:username', async (req, res) => {
  try {
    const { username } = req.params;
    const status = await dockerManager.getContainerStatus(username);

    res.json(status);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Остановить контейнер
router.delete('/:username', async (req, res) => {
  try {
    const { username } = req.params;
    const container = await dockerManager.getContainer(username);

    if (container) {
      await container.stop();
      await container.remove();
      res.json({ success: true });
    } else {
      res.status(404).json({ error: 'Container not found' });
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

export default router;
```

### Вариант 2: Интеграция в OMA Backend (FastAPI)

Добавить Docker management endpoint в существующий OMA Backend:

**Файл:** `oma-backend/app/api/containers.py`

```python
from fastapi import APIRouter, Depends, HTTPException
import docker
from app.models.user import User
from app.api.auth import get_current_user

router = APIRouter(prefix="/containers", tags=["Container Management"])
client = docker.from_env()

@router.post("/start")
def start_user_container(current_user: User = Depends(get_current_user)):
    """Start MCP Google Hub container for current user"""

    container_name = f"mcpgoogle-{current_user.username}"

    # Check if container exists
    try:
        container = client.containers.get(container_name)
        if container.status == "running":
            return {"message": "Container already running", "status": "running"}
        container.start()
        return {"message": "Container started", "status": "started"}
    except docker.errors.NotFound:
        pass

    # Find free port
    port = find_free_port(start=3001)

    # Create and start container
    container = client.containers.run(
        "mcpgoogle:latest",
        name=container_name,
        environment={
            "AUTH_MODE": "oma_backend",
            "OMA_BACKEND_URL": "https://rndaibot.ru/api/v1",
            "MCP_USERNAME": current_user.username,
            "MCP_PASSWORD": get_user_password(current_user),  # Нужно хранить!
            "GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID,
            "GOOGLE_CLIENT_SECRET": settings.GOOGLE_CLIENT_SECRET,
        },
        ports={'8000/tcp': port},
        detach=True,
        restart_policy={"Name": "unless-stopped"},
        labels={
            "com.mcpgoogle.user": current_user.username,
            "com.mcpgoogle.user_id": str(current_user.id)
        }
    )

    return {
        "message": "Container created and started",
        "container_id": container.id,
        "port": port
    }

@router.get("/status")
def get_container_status(current_user: User = Depends(get_current_user)):
    """Get MCP Hub container status for current user"""

    container_name = f"mcpgoogle-{current_user.username}"

    try:
        container = client.containers.get(container_name)
        return {
            "status": container.status,
            "port": container.ports.get('8000/tcp', [{}])[0].get('HostPort'),
            "health": container.attrs.get('State', {}).get('Health', {}).get('Status')
        }
    except docker.errors.NotFound:
        return {"status": "not_exists"}

def find_free_port(start=3001):
    """Find next free port"""
    containers = client.containers.list(all=True)
    used_ports = set()

    for c in containers:
        ports = c.ports.get('8000/tcp', [])
        for port_info in ports:
            if port_info.get('HostPort'):
                used_ports.add(int(port_info['HostPort']))

    port = start
    while port in used_ports:
        port += 1
    return port
```

### Next.js Integration

**Frontend Hook:**

```typescript
// src/hooks/useContainerManagement.ts
import { useState, useEffect } from 'react';

export function useContainerManagement() {
  const [containerStatus, setContainerStatus] = useState<string>('unknown');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async () => {
    try {
      const response = await fetch('/api/containers/status', {
        credentials: 'include'
      });
      const data = await response.json();
      setContainerStatus(data.status);
    } catch (error) {
      console.error('Failed to check container status:', error);
    }
  };

  const startContainer = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/containers/start', {
        method: 'POST',
        credentials: 'include'
      });

      if (response.ok) {
        await checkStatus();
      }
    } catch (error) {
      console.error('Failed to start container:', error);
    } finally {
      setLoading(false);
    }
  };

  return {
    containerStatus,
    startContainer,
    loading,
    checkStatus
  };
}
```

**Component:**

```typescript
// src/components/ContainerStatus.tsx
'use client';

import { useContainerManagement } from '@/hooks/useContainerManagement';
import { useAuth } from '@/contexts/AuthContext';

export function ContainerStatus() {
  const { user } = useAuth();
  const { containerStatus, startContainer, loading } = useContainerManagement();

  if (!user) return null;

  return (
    <div className="container-status">
      <h3>MCP Google Hub Status</h3>

      {containerStatus === 'running' && (
        <div className="status-running">
          ✅ Your MCP Hub container is running
        </div>
      )}

      {containerStatus === 'not_exists' && (
        <div className="status-not-running">
          ⚠️ Container not started
          <button onClick={startContainer} disabled={loading}>
            {loading ? 'Starting...' : 'Start My Container'}
          </button>
        </div>
      )}

      {containerStatus === 'stopped' && (
        <div className="status-stopped">
          ⏸️ Container stopped
          <button onClick={startContainer}>Restart Container</button>
        </div>
      )}
    </div>
  );
}
```

### ⚠️ Проблема: Хранение паролей

**Вопрос:** Как получить пароль пользователя для запуска контейнера?

**Варианты решения:**

#### Вариант A: Хранить plain-text пароль (❌ НЕ рекомендуется)

```sql
ALTER TABLE users ADD COLUMN plain_password TEXT;
```

**Плюсы:** Просто
**Минусы:** Небезопасно!

#### Вариант B: Использовать API key вместо пароля (✅ Рекомендуется)

```sql
ALTER TABLE users ADD COLUMN api_key TEXT UNIQUE;
```

```python
# При регистрации генерируем API key
import secrets

api_key = secrets.token_urlsafe(32)
user.api_key = api_key
```

**Docker контейнер использует API key:**

```python
container = client.containers.run(
    "mcpgoogle:latest",
    environment={
        "MCP_API_KEY": current_user.api_key,  # ← Вместо password
        ...
    }
)
```

**docker-entrypoint.sh обновить:**

```bash
# Вместо username/password login
# Использовать API key authentication

if [ -n "$MCP_API_KEY" ]; then
    # Login with API key
    TOKEN=$(curl -X POST "${OMA_BACKEND_URL}/auth/api-key-login" \
        -H "X-API-Key: $MCP_API_KEY" | jq -r '.access_token')
else
    # Fallback to username/password
    ...
fi
```

#### Вариант C: Refresh Token (✅ Лучший вариант)

**При логине пользователя:**

1. User логинится → получает JWT + Refresh Token
2. Refresh Token хранится в БД (уже есть в `refresh_tokens` table)
3. Контейнер использует Refresh Token для получения Access Token

**Преимущества:**
- ✅ Не нужно хранить пароль
- ✅ Refresh Token можно отозвать
- ✅ Стандартный OAuth 2.0 flow

**Реализация:**

```python
@router.post("/start")
def start_user_container(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Получаем active refresh token пользователя
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.user_id == current_user.id,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()

    if not refresh_token:
        raise HTTPException(400, "No valid refresh token found")

    # Контейнер получает refresh token
    container = client.containers.run(
        "mcpgoogle:latest",
        environment={
            "MCP_REFRESH_TOKEN": refresh_token.token,
            ...
        }
    )
```

**docker-entrypoint.sh:**

```bash
# Use refresh token to get access token
if [ -n "$MCP_REFRESH_TOKEN" ]; then
    ACCESS_TOKEN=$(curl -X POST "${OMA_BACKEND_URL}/auth/refresh" \
        -H "Content-Type: application/json" \
        -d "{\"refresh_token\": \"$MCP_REFRESH_TOKEN\"}" \
        | jq -r '.access_token')

    export OMA_ACCESS_TOKEN="$ACCESS_TOKEN"
fi
```

## Рекомендуемая архитектура

```
User регистрируется (Next.js)
        ↓
OMA Backend создает user + refresh_token
        ↓
Frontend автоматически вызывает POST /containers/start
        ↓
OMA Backend:
  1. Получает refresh_token пользователя из БД
  2. Запускает Docker контейнер с MCP_REFRESH_TOKEN
  3. Контейнер стартует → получает access_token автоматически
        ↓
User может использовать свой MCP Hub!
```

## Summary

**✅ Ответ на ваш вопрос:**

> Стартовать контейнер надо с login/password самого пользователя?

**Нет, есть лучший вариант:**
- ✅ Использовать **Refresh Token** (уже хранится в БД)
- ✅ Frontend вызывает API: `POST /containers/start` после регистрации
- ✅ OMA Backend автоматически запускает контейнер с refresh_token
- ✅ Контейнер получает access_token при старте
- ✅ **Никаких паролей в контейнерах!**

Хотите, чтобы я реализовал полное решение с Refresh Token?
