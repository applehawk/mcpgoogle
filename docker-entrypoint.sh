#!/bin/bash
# Docker entrypoint script for MCP Google Hub
# Automatically obtains JWT access token from OMA Backend

set -e

echo "🚀 Starting MCP Google Hub..."

# Check required environment variables
if [ -z "$OMA_BACKEND_URL" ]; then
    echo "❌ Error: OMA_BACKEND_URL is not set"
    exit 1
fi

# Method 1: Use Refresh Token (preferred for containers)
if [ -n "$MCP_REFRESH_TOKEN" ]; then
    echo "📡 Obtaining Access Token using Refresh Token..."
    echo "   Backend URL: $OMA_BACKEND_URL"

    RESPONSE=$(curl -s -X POST "${OMA_BACKEND_URL}/auth/refresh" \
        -H "Content-Type: application/json" \
        -d "{\"refresh_token\": \"$MCP_REFRESH_TOKEN\"}" \
        2>&1)

    ACCESS_TOKEN=$(echo "$RESPONSE" | grep -o '"access_token":"[^"]*' | grep -o '[^"]*$' || echo "")

    if [ -z "$ACCESS_TOKEN" ]; then
        echo "❌ Error: Failed to obtain Access Token from Refresh Token"
        echo "   Response: $RESPONSE"
        exit 1
    fi

    echo "✅ Access Token obtained from Refresh Token"
    echo "   Token: ${ACCESS_TOKEN:0:20}..."

# Method 2: Use Username/Password (fallback)
elif [ -n "$MCP_USERNAME" ] && [ -n "$MCP_PASSWORD" ]; then
    echo "📡 Obtaining JWT token using Username/Password..."
    echo "   Backend URL: $OMA_BACKEND_URL"
    echo "   Username: $MCP_USERNAME"

    RESPONSE=$(curl -s -X POST "${OMA_BACKEND_URL}/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"$MCP_USERNAME\", \"password\": \"$MCP_PASSWORD\"}" \
        2>&1)

    ACCESS_TOKEN=$(echo "$RESPONSE" | grep -o '"access_token":"[^"]*' | grep -o '[^"]*$' || echo "")

    if [ -z "$ACCESS_TOKEN" ]; then
        echo "❌ Error: Failed to obtain JWT token"
        echo "   Response: $RESPONSE"
        exit 1
    fi

    echo "✅ JWT token obtained via login"
    echo "   Token: ${ACCESS_TOKEN:0:20}..."

else
    echo "❌ Error: Neither MCP_REFRESH_TOKEN nor MCP_USERNAME/MCP_PASSWORD is set"
    echo ""
    echo "Please provide one of:"
    echo "  - MCP_REFRESH_TOKEN (recommended for containers)"
    echo "  - MCP_USERNAME + MCP_PASSWORD"
    exit 1
fi

# Export token for application
export OMA_ACCESS_TOKEN="$ACCESS_TOKEN"

# Start the application
echo "🎯 Starting FastMCP server..."
exec "$@"
