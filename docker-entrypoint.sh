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
    echo "   Refresh Token: ${MCP_REFRESH_TOKEN:0:30}..."

    # Try to get access token with proper error handling
    HTTP_CODE=$(curl -s -w "%{http_code}" -o /tmp/response.json \
        --connect-timeout 10 \
        --max-time 30 \
        -X POST "${OMA_BACKEND_URL}/auth/refresh" \
        -H "Content-Type: application/json" \
        -d "{\"refresh_token\": \"$MCP_REFRESH_TOKEN\"}" \
        2>&1 || echo "000")

    echo "   HTTP Status: $HTTP_CODE"

    if [ "$HTTP_CODE" != "200" ]; then
        echo "❌ Error: Failed to obtain Access Token (HTTP $HTTP_CODE)"
        echo "   Response body:"
        cat /tmp/response.json 2>/dev/null || echo "   (no response body)"
        echo ""
        echo "⚠️  Container will exit and Docker will restart it."
        echo "⚠️  Check if OMA Backend is accessible from this container."
        echo "⚠️  Testing connectivity..."

        # Test basic connectivity
        if curl -s --connect-timeout 5 -o /dev/null -w "%{http_code}" "https://rndaibot.ru" | grep -q "200\|301\|302"; then
            echo "   ✓ Can reach rndaibot.ru"
        else
            echo "   ✗ Cannot reach rndaibot.ru (network issue?)"
        fi

        exit 1
    fi

    # Parse JSON response
    ACCESS_TOKEN=$(cat /tmp/response.json | grep -o '"access_token":"[^"]*' | grep -o '[^"]*$' || echo "")

    if [ -z "$ACCESS_TOKEN" ]; then
        echo "❌ Error: access_token not found in response"
        echo "   Response:"
        cat /tmp/response.json
        exit 1
    fi

    echo "✅ Access Token obtained from Refresh Token"
    echo "   Token: ${ACCESS_TOKEN:0:20}..."
    rm -f /tmp/response.json

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
