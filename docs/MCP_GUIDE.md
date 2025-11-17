# MCP Google Hub - OpenAI Agents Integration Guide

Complete guide for using MCP Google Hub with OpenAI Agents and the Model Context Protocol (MCP).

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [MCP Protocol Endpoints](#mcp-protocol-endpoints)
- [Testing with curl](#testing-with-curl)
- [OpenAI Agents Integration](#openai-agents-integration)
- [Authentication](#authentication)
- [Error Handling](#error-handling)
- [Troubleshooting](#troubleshooting)

## Overview

MCP Google Hub is a FastMCP server that exposes Google services (Gmail, Calendar) through the Model Context Protocol (MCP). It's fully compatible with OpenAI Agents' `HostedMCPTool`.

### Architecture

```
OpenAI Agents → HTTP/JSON-RPC 2.0 → MCP Google Hub → Google APIs
                                     (FastMCP)         (Gmail, Calendar)
```

### Key Features

- **MCP Compliant**: Implements MCP specification with JSON-RPC 2.0
- **OpenAI Ready**: Works out-of-the-box with `HostedMCPTool`
- **Secure**: Optional Bearer token authentication
- **CORS Enabled**: Works from browser and cross-origin requests
- **Streaming Support**: Streamable HTTP transport for real-time responses

## Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

**Minimum configuration for MCP:**

```env
# Google OAuth (required)
AUTH_MODE=oma_backend
OMA_BACKEND_URL=https://rndaibot.ru/api/v1
OMA_ACCESS_TOKEN=your_token_here
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# MCP Server (optional - defaults shown)
MCP_TRANSPORT=streamable-http
MCP_HOST=0.0.0.0
MCP_PORT=8000
MCP_CORS_ORIGINS=*
# MCP_AUTH_TOKEN=  # Leave empty for dev mode
```

### 2. Start Server

```bash
# Option 1: Using Python directly
python src/server.py

# Option 2: Using FastMCP CLI
fastmcp run src/server.py

# Option 3: Using module
python -m src.server
```

Server will start at: **http://localhost:8000/mcp/**

### 3. Verify Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "mcp-google-hub",
  "auth_enabled": false,
  "transport": "streamable-http"
}
```

## MCP Protocol Endpoints

### Base URL

```
http://localhost:8000/mcp/
```

All MCP requests are JSON-RPC 2.0 POST requests to this endpoint.

### Method: tools/list

List all available tools with their schemas.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "gmail_list_unread",
        "description": "Lista correos no leidos (INBOX).",
        "inputSchema": {
          "type": "object",
          "properties": {
            "max_results": {
              "type": "integer",
              "description": "Parameter max_results"
            }
          },
          "additionalProperties": false
        }
      },
      {
        "name": "gmail_send_message",
        "description": "Envia un correo simple con opcionales CC/BCC y adjuntos.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "to": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "cc": {"type": "string"},
            "bcc": {"type": "string"}
          },
          "required": ["to", "subject", "body"],
          "additionalProperties": false
        }
      }
    ]
  }
}
```

### Method: tools/call

Execute a tool with arguments.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "gmail_list_unread",
    "arguments": {
      "max_results": 5
    }
  }
}
```

**Response (Success):**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "[{\"id\": \"abc123\", \"from\": \"sender@example.com\", \"subject\": \"Test\", \"date\": \"Mon, 1 Jan 2025 12:00:00 +0000\"}]"
      }
    ],
    "isError": false
  }
}
```

**Response (Error):**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Error executing tool 'gmail_list_unread': Invalid credentials"
      }
    ],
    "isError": true
  }
}
```

## Testing with curl

### 1. List Available Tools

```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

### 2. Call a Tool (List Unread Emails)

```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "gmail_list_unread",
      "arguments": {
        "max_results": 5
      }
    }
  }'
```

### 3. Call a Tool (Send Email)

```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "gmail_send_message",
      "arguments": {
        "to": "recipient@example.com",
        "subject": "Test from MCP",
        "body": "This email was sent via MCP Google Hub!"
      }
    }
  }'
```

### 4. With Authentication

If `MCP_AUTH_TOKEN` is set:

```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token-here" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

### 5. Using jq for Pretty Output

```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }' | jq '.'
```

## OpenAI Agents Integration

### Basic Configuration

```python
from openai import OpenAI

client = OpenAI(api_key="your-openai-api-key")

response = client.responses.create(
    model="gpt-4.1",
    tools=[
        {
            "type": "mcp",
            "server_label": "mcpgoogle",
            "server_url": "http://localhost:8000/mcp/",
            "require_approval": "never"
        }
    ],
    input="Check my unread emails and summarize them"
)

print(response.output)
```

### With Authentication

```python
from openai import OpenAI
import os

# Set your MCP auth token
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN")

client = OpenAI(api_key="your-openai-api-key")

response = client.responses.create(
    model="gpt-4.1",
    tools=[
        {
            "type": "mcp",
            "server_label": "mcpgoogle",
            "server_url": "http://localhost:8000/mcp/",
            "require_approval": "never",
            "headers": {
                "Authorization": f"Bearer {MCP_AUTH_TOKEN}"
            }
        }
    ],
    input="Send an email to team@company.com with subject 'Weekly Update'"
)

print(response.output)
```

### Production Deployment with ngrok

For testing with OpenAI (which requires public URLs):

```bash
# Terminal 1: Start your server
python src/server.py

# Terminal 2: Expose with ngrok
ngrok http 8000

# Use the ngrok URL in your OpenAI config
# Example: https://abc123.ngrok.io/mcp/
```

**OpenAI Config with ngrok:**

```python
{
    "type": "mcp",
    "server_label": "mcpgoogle",
    "server_url": "https://abc123.ngrok.io/mcp/",  # Your ngrok URL
    "require_approval": "never"
}
```

### Complete Example

```python
from openai import OpenAI
import os

def setup_mcp_google_hub():
    """Configure MCP Google Hub for OpenAI Agents"""

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    mcp_config = {
        "type": "mcp",
        "server_label": "mcpgoogle",
        "server_url": os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp/"),
        "require_approval": "never"
    }

    # Add auth if configured
    if os.getenv("MCP_AUTH_TOKEN"):
        mcp_config["headers"] = {
            "Authorization": f"Bearer {os.getenv('MCP_AUTH_TOKEN')}"
        }

    return client, mcp_config


def main():
    client, mcp_config = setup_mcp_google_hub()

    # Example 1: Check unread emails
    response = client.responses.create(
        model="gpt-4.1",
        tools=[mcp_config],
        input="Check my unread emails and summarize the important ones"
    )
    print("Emails Summary:", response.output)

    # Example 2: Send an email
    response = client.responses.create(
        model="gpt-4.1",
        tools=[mcp_config],
        input="""
        Send an email to john@example.com with:
        Subject: Meeting Tomorrow
        Body: Hi John, confirming our meeting tomorrow at 2 PM. See you then!
        """
    )
    print("Email Sent:", response.output)

    # Example 3: Check calendar
    response = client.responses.create(
        model="gpt-4.1",
        tools=[mcp_config],
        input="What are my upcoming events this week?"
    )
    print("Calendar:", response.output)


if __name__ == "__main__":
    main()
```

## Authentication

### Disable Authentication (Development)

Leave `MCP_AUTH_TOKEN` empty in `.env`:

```env
MCP_AUTH_TOKEN=
```

No authentication required for requests.

### Enable Authentication (Production)

Generate a secure token:

```bash
openssl rand -hex 32
```

Set in `.env`:

```env
MCP_AUTH_TOKEN=your-generated-token-here
```

Include in all requests:

```bash
curl -H "Authorization: Bearer your-generated-token-here" ...
```

### Advanced Authentication

For production, consider using FastMCP's JWT authentication:

```python
# src/core.py
from fastmcp.server.auth.providers.jwt import JWTVerifier

auth = JWTVerifier(
    jwks_uri="https://auth.yourcompany.com/.well-known/jwks.json",
    issuer="https://auth.yourcompany.com",
    audience="mcp-production-api"
)

mcp = FastMCP(name="MCPGoogle", auth=auth)
```

## Error Handling

### JSON-RPC 2.0 Error Codes

| Code | Name | Description |
|------|------|-------------|
| -32700 | Parse Error | Invalid JSON |
| -32600 | Invalid Request | Missing required fields |
| -32601 | Method Not Found | Unknown method |
| -32602 | Invalid Params | Invalid arguments |
| -32603 | Internal Error | Server error |
| -32001 | Unauthorized | Authentication failed |

### Example Error Response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32601,
    "message": "Method not found",
    "data": {
      "method": "invalid_method"
    }
  }
}
```

## Troubleshooting

### Server Not Starting

**Issue:** `ModuleNotFoundError: No module named 'fastmcp'`

**Solution:**
```bash
pip install -e .
# or
pip install fastmcp>=2.13.0
```

### Authentication Errors

**Issue:** `401 Unauthorized: Bearer token required`

**Solutions:**
1. Disable auth: `MCP_AUTH_TOKEN=` in `.env`
2. Include token: `Authorization: Bearer your-token`
3. Check token matches in `.env` and request

### CORS Errors (Browser)

**Issue:** `Access-Control-Allow-Origin` error in browser console

**Solution:** Check `MCP_CORS_ORIGINS` in `.env`:

```env
# Allow all (dev only)
MCP_CORS_ORIGINS=*

# Specific domains (production)
MCP_CORS_ORIGINS=https://api.openai.com,https://yourapp.com
```

### Tools Not Appearing

**Issue:** `tools/list` returns empty array

**Solutions:**
1. Verify tools are imported in `src/server.py`
2. Check `@mcp.tool` decorator is applied
3. Restart server after code changes

### Google API Errors

**Issue:** `Error executing tool: Invalid credentials`

**Solutions:**
1. Verify `OMA_ACCESS_TOKEN` is valid
2. Check Google account is connected in OMA Backend
3. Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
4. Ensure required scopes are configured

### OpenAI Connection Issues

**Issue:** OpenAI can't reach MCP server

**Solutions:**
1. Use public URL (ngrok, etc.) not localhost
2. Verify server URL ends with `/mcp/`
3. Check firewall allows incoming connections
4. Verify CORS is configured correctly

## Additional Resources

- [MCP Specification](https://modelcontextprotocol.io/specification)
- [FastMCP Documentation](https://gofastmcp.com/)
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)

## Support

For issues or questions:
1. Check [README.md](README.md) for general setup
2. Review error messages in server logs
3. Test with curl before integrating with OpenAI
4. Verify Google OAuth is working independently

---

**Generated with MCP Google Hub** | Model Context Protocol Implementation
