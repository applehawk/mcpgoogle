# Docker Deployment Guide - Multi-User Setup

## Архитектура: Один контейнер на пользователя

```
┌──────────────────────────────────────────────────────────────────┐
│                     Docker Multi-User Architecture                │
└──────────────────────────────────────────────────────────────────┘

┌────────────────┐         ┌────────────────┐         ┌────────────────┐
│ Container 1    │         │ Container 2    │         │ Container 3    │
│ mcpgoogle-alice│         │ mcpgoogle-bob  │         │ mcpgoogle-carol│
│                │         │                │         │                │
│ Port: 3001     │         │ Port: 3002     │         │ Port: 3003     │
│ JWT: ALICE     │         │ JWT: BOB       │         │ JWT: CAROL     │
└───────┬────────┘         └───────┬────────┘         └───────┬────────┘
        │                          │                          │
        └──────────────────────────┼──────────────────────────┘
                                   │
                                   ▼
                          ┌────────────────┐
                          │  OMA Backend   │
                          │   (Shared)     │
                          └────────┬───────┘
                                   │
                                   ▼
                          ┌────────────────┐
                          │  PostgreSQL    │
                          │  - users       │
                          │  - google_creds│
                          └────────────────┘
```

## Зачем отдельные контейнеры?

### ✅ Преимущества

1. **Полная изоляция процессов**
   - Каждый пользователь = отдельный процесс
   - Crash одного контейнера не влияет на других

2. **Независимое масштабирование**
   - Можно ограничить CPU/RAM для каждого пользователя
   - Горизонтальное масштабирование (добавил контейнер = добавил пользователя)

3. **Безопасность**
   - Изоляция на уровне контейнера (namespace isolation)
   - Один пользователь не может повлиять на другого

4. **Мониторинг и отладка**
   - Логи отдельно для каждого пользователя
   - Легко отследить проблемы конкретного пользователя

5. **Гибкая конфигурация**
   - Разные настройки для разных пользователей
   - Разные версии кода (A/B testing)

## Quick Start

### 1. Подготовка

```bash
cd mcpgoogle

# Build Docker image
docker build -t mcpgoogle:latest .
```

### 2. Получение JWT токенов для пользователей

Каждый пользователь должен:

```bash
# User 1 (Alice) - Register and login
curl -X POST https://rndaibot.ru/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "password": "alice_password"
  }'

curl -X POST https://rndaibot.ru/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "password": "alice_password"
  }' | jq -r '.access_token'

# Copy JWT token → ALICE_OMA_TOKEN

# User 2 (Bob) - Same process
# ...

# User 3 (Carol) - Same process
# ...
```

### 3. Подключение Google аккаунтов

Каждый пользователь через web интерфейс:

```bash
# Alice
1. Open https://rndaibot.ru
2. Login with alice / alice_password
3. Settings → Connect Google Account
4. Authorize Gmail/Calendar access

# Bob
1. Open https://rndaibot.ru
2. Login with bob / bob_password
3. Settings → Connect Google Account
4. Authorize Gmail/Calendar access

# ... и так далее для всех пользователей
```

### 4. Конфигурация Docker Compose

```bash
# Copy environment template
cp .env.docker .env

# Edit .env and add JWT tokens
nano .env
```

`.env` file:
```env
GOOGLE_CLIENT_ID=your-app.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret

ALICE_OMA_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
BOB_OMA_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
CAROL_OMA_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DAVE_OMA_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
EVE_OMA_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 5. Запуск всех контейнеров

```bash
# Start all user containers
docker-compose -f docker-compose.multi-user.yml up -d

# Check status
docker-compose -f docker-compose.multi-user.yml ps

# Expected output:
# NAME                STATUS    PORTS
# mcpgoogle-alice     Up        0.0.0.0:3001->8000/tcp
# mcpgoogle-bob       Up        0.0.0.0:3002->8000/tcp
# mcpgoogle-carol     Up        0.0.0.0:3003->8000/tcp
# mcpgoogle-dave      Up        0.0.0.0:3004->8000/tcp
# mcpgoogle-eve       Up        0.0.0.0:3005->8000/tcp
```

### 6. Проверка работы

```bash
# Test Alice's container
curl http://localhost:3001/health
# {"status": "healthy"}

# Test Bob's container
curl http://localhost:3002/health
# {"status": "healthy"}

# ... и так далее
```

## Использование

### Пример: Alice отправляет email

```bash
# Alice's container on port 3001
docker exec -it mcpgoogle-alice python -c "
from src.tools.gmail_tool import gmail_send_message
gmail_send_message(
    to='recipient@example.com',
    subject='Hello from Alice',
    body='This is Alice\\'s email'
)
"
```

### Пример: Bob проверяет календарь

```bash
# Bob's container on port 3002
docker exec -it mcpgoogle-bob python -c "
from src.tools.calendar_tool import calendar_upcoming
events = calendar_upcoming(max_results=5)
print(f'Bob has {len(events)} upcoming events')
"
```

## Управление контейнерами

### Просмотр логов

```bash
# All containers
docker-compose -f docker-compose.multi-user.yml logs -f

# Specific user
docker logs -f mcpgoogle-alice
docker logs -f mcpgoogle-bob

# Last 100 lines
docker logs --tail 100 mcpgoogle-alice
```

### Перезапуск конкретного пользователя

```bash
# Restart Alice's container only
docker-compose -f docker-compose.multi-user.yml restart mcpgoogle-alice

# Stop and remove
docker-compose -f docker-compose.multi-user.yml stop mcpgoogle-alice
docker-compose -f docker-compose.multi-user.yml rm mcpgoogle-alice
```

### Обновление JWT токена

Если JWT токен истек (после 30 минут):

```bash
# 1. Get new token
NEW_TOKEN=$(curl -X POST https://rndaibot.ru/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "alice_password"}' \
  | jq -r '.access_token')

# 2. Update .env
sed -i "s/ALICE_OMA_TOKEN=.*/ALICE_OMA_TOKEN=$NEW_TOKEN/" .env

# 3. Restart container
docker-compose -f docker-compose.multi-user.yml restart mcpgoogle-alice
```

## Добавление нового пользователя

### 1. Регистрация в OMA Backend

```bash
# Register new user
curl -X POST https://rndaibot.ru/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "frank",
    "email": "frank@example.com",
    "password": "frank_password"
  }'

# Login and get JWT
FRANK_TOKEN=$(curl -X POST https://rndaibot.ru/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "frank", "password": "frank_password"}' \
  | jq -r '.access_token')

echo "Frank's token: $FRANK_TOKEN"
```

### 2. Подключение Google Account

- Открыть https://rndaibot.ru
- Login as frank
- Connect Google Account

### 3. Добавить в docker-compose.yml

```yaml
# Add to docker-compose.multi-user.yml

  mcpgoogle-frank:
    build: .
    container_name: mcpgoogle-frank
    restart: unless-stopped
    environment:
      AUTH_MODE: oma_backend
      OMA_BACKEND_URL: https://rndaibot.ru/api/v1
      OMA_ACCESS_TOKEN: ${FRANK_OMA_TOKEN}
      OMA_VERIFY_SSL: "true"
      GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
      GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}

    ports:
      - "3006:8000"  # Frank's port

    networks:
      - mcpgoogle-network

    labels:
      - "com.mcpgoogle.user=frank"
      - "com.mcpgoogle.email=frank@example.com"
```

### 4. Добавить токен в .env

```bash
echo "FRANK_OMA_TOKEN=$FRANK_TOKEN" >> .env
```

### 5. Запустить новый контейнер

```bash
docker-compose -f docker-compose.multi-user.yml up -d mcpgoogle-frank
```

## Мониторинг

### Resource usage

```bash
# CPU/Memory usage for all containers
docker stats mcpgoogle-alice mcpgoogle-bob mcpgoogle-carol

# Output:
# CONTAINER          CPU %    MEM USAGE / LIMIT    MEM %
# mcpgoogle-alice    0.5%     150MB / 512MB        29.3%
# mcpgoogle-bob      0.3%     145MB / 512MB        28.3%
# mcpgoogle-carol    0.4%     152MB / 512MB        29.7%
```

### Health checks

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' mcpgoogle-alice
# Output: healthy

# All containers
for container in alice bob carol dave eve; do
  echo -n "mcpgoogle-$container: "
  docker inspect --format='{{.State.Health.Status}}' mcpgoogle-$container
done
```

## Ограничение ресурсов

### CPU и Memory limits

В `docker-compose.multi-user.yml` добавить:

```yaml
  mcpgoogle-alice:
    # ... existing config
    deploy:
      resources:
        limits:
          cpus: '0.5'      # 50% of one CPU
          memory: 512M     # 512MB RAM max
        reservations:
          cpus: '0.1'      # Min 10% CPU guaranteed
          memory: 128M     # Min 128MB RAM
```

## Production Deployment

### С Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/mcpgoogle

# Alice's MCP Hub
server {
    listen 443 ssl;
    server_name alice.mcpgoogle.example.com;

    ssl_certificate /etc/letsencrypt/live/alice.mcpgoogle.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/alice.mcpgoogle.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Bob's MCP Hub
server {
    listen 443 ssl;
    server_name bob.mcpgoogle.example.com;

    ssl_certificate /etc/letsencrypt/live/bob.mcpgoogle.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bob.mcpgoogle.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# ... и так далее для остальных
```

### С Kubernetes (опционально)

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcpgoogle-alice
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mcpgoogle
      user: alice
  template:
    metadata:
      labels:
        app: mcpgoogle
        user: alice
    spec:
      containers:
      - name: mcpgoogle
        image: mcpgoogle:latest
        env:
        - name: OMA_ACCESS_TOKEN
          valueFrom:
            secretKeyRef:
              name: alice-oma-token
              key: token
        - name: GOOGLE_CLIENT_ID
          valueFrom:
            secretKeyRef:
              name: google-oauth
              key: client_id
        ports:
        - containerPort: 8000
```

## Troubleshooting

### Container не стартует

```bash
# Check logs
docker logs mcpgoogle-alice

# Common errors:
# 1. Missing OMA_ACCESS_TOKEN
# 2. Invalid JWT token
# 3. Google account not connected
```

### JWT token истек

```bash
# Get new token
# See "Обновление JWT токена" section above
```

### Google credentials не найдены

```bash
# User must connect Google account via web UI:
# 1. https://rndaibot.ru
# 2. Login
# 3. Settings → Connect Google
```

## Автоматизация

### Shell script для добавления нового пользователя

```bash
#!/bin/bash
# add-user.sh - Automate new user setup

set -e

USERNAME=$1
EMAIL=$2
PASSWORD=$3
PORT=$4

if [ -z "$USERNAME" ] || [ -z "$EMAIL" ] || [ -z "$PASSWORD" ] || [ -z "$PORT" ]; then
    echo "Usage: ./add-user.sh <username> <email> <password> <port>"
    exit 1
fi

echo "Registering user $USERNAME..."
curl -X POST https://rndaibot.ru/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}"

echo "Getting JWT token..."
TOKEN=$(curl -X POST https://rndaibot.ru/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}" \
  | jq -r '.access_token')

echo "Token: $TOKEN"

# Add to .env
echo "${USERNAME^^}_OMA_TOKEN=$TOKEN" >> .env

# Add to docker-compose
cat >> docker-compose.multi-user.yml <<EOF

  mcpgoogle-$USERNAME:
    build: .
    container_name: mcpgoogle-$USERNAME
    restart: unless-stopped
    environment:
      AUTH_MODE: oma_backend
      OMA_BACKEND_URL: https://rndaibot.ru/api/v1
      OMA_ACCESS_TOKEN: \${${USERNAME^^}_OMA_TOKEN}
      OMA_VERIFY_SSL: "true"
      GOOGLE_CLIENT_ID: \${GOOGLE_CLIENT_ID}
      GOOGLE_CLIENT_SECRET: \${GOOGLE_CLIENT_SECRET}
    ports:
      - "$PORT:8000"
    networks:
      - mcpgoogle-network
    labels:
      - "com.mcpgoogle.user=$USERNAME"
      - "com.mcpgoogle.email=$EMAIL"
EOF

echo "Starting container..."
docker-compose -f docker-compose.multi-user.yml up -d mcpgoogle-$USERNAME

echo "✅ Done! Container mcpgoogle-$USERNAME running on port $PORT"
echo "User must now connect Google account at https://rndaibot.ru"
```

Использование:
```bash
chmod +x add-user.sh
./add-user.sh frank frank@example.com frank_password 3006
```

## Summary

**✅ Docker контейнеризация - лучшее решение для multi-user:**

- Один контейнер = один пользователь = полная изоляция
- Легко масштабировать (добавил контейнер = добавил пользователя)
- Независимые ресурсы и мониторинг
- Production-ready архитектура
- Безопасность на уровне контейнеров

**5 пользователей = 5 контейнеров = 5 портов = 0 конфликтов!** 🎯
