"""
Example: Using MCP Google Hub with OMA Backend Authentication

This example demonstrates server-to-server OAuth 2.0 integration
between MCP Google Hub and OMA Backend.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure we're in OMA backend mode
os.environ["AUTH_MODE"] = "oma_backend"


def example_gmail_send():
    """Example: Send email using OMA Backend credentials"""
    from mcp_hub.tools.gmail_tool import gmail_send_message

    print("=" * 60)
    print("Example: Send Email via OMA Backend")
    print("=" * 60)

    result = gmail_send_message(
        to="recipient@example.com",
        subject="Test Email from MCP Hub",
        body="This email was sent using OMA Backend authentication!\n\n"
        "The OAuth credentials were fetched from the centralized auth server.",
    )

    print(f"✅ Email sent successfully!")
    print(f"Message ID: {result.get('id')}")
    print()


def example_gmail_list():
    """Example: List unread emails"""
    from mcp_hub.tools.gmail_tool import gmail_list_unread

    print("=" * 60)
    print("Example: List Unread Emails")
    print("=" * 60)

    messages = gmail_list_unread(max_results=5)

    print(f"Found {len(messages)} unread messages:")
    for msg in messages:
        print(f"  - From: {msg.get('from')}")
        print(f"    Subject: {msg.get('subject')}")
        print(f"    Date: {msg.get('date')}")
        print()


def example_calendar_upcoming():
    """Example: Get upcoming calendar events"""
    from mcp_hub.tools.calendar_tool import calendar_upcoming

    print("=" * 60)
    print("Example: Upcoming Calendar Events")
    print("=" * 60)

    events = calendar_upcoming(max_results=10)

    print(f"Found {len(events)} upcoming events:")
    for event in events:
        print(f"  - {event.get('summary')}")
        print(f"    Start: {event.get('start')}")
        print(f"    End: {event.get('end')}")
        print()


def example_check_oma_status():
    """Example: Check OMA Backend connection status"""
    from mcp_hub.auth.oma_client import get_oma_client

    print("=" * 60)
    print("Example: Check OMA Backend Status")
    print("=" * 60)

    client = get_oma_client()

    try:
        # Check which Google services are connected
        import asyncio

        status = asyncio.run(client.check_google_status())

        print("Google Services Status:")
        print(f"  Gmail: {'✅ Connected' if status.get('gmail_connected') else '❌ Not connected'}")
        print(
            f"  Calendar: {'✅ Connected' if status.get('calendar_connected') else '❌ Not connected'}"
        )

        if status.get("token_expiry"):
            print(f"  Token expires: {status.get('token_expiry')}")

    except Exception as e:
        print(f"❌ Error: {e}")

    print()


def example_get_credentials():
    """Example: Direct credential access"""
    from mcp_hub.auth.google_auth import get_google_creds

    print("=" * 60)
    print("Example: Get Google Credentials from OMA Backend")
    print("=" * 60)

    try:
        creds = get_google_creds()

        print("✅ Successfully retrieved credentials from OMA Backend")
        print(f"Token: {creds.token[:20]}...")
        print(f"Scopes: {', '.join(creds.scopes)}")
        print(f"Valid: {creds.valid}")
        print(f"Expired: {creds.expired}")

        if creds.expiry:
            print(f"Expires at: {creds.expiry}")

    except ValueError as e:
        print(f"❌ Error: {e}")
        print()
        print("To fix this:")
        print("1. Set OMA_ACCESS_TOKEN in your .env file")
        print("2. Ensure user has connected Google account via web interface")
        print("3. Check that OMA backend is running and accessible")

    print()


def example_direct_api_call():
    """Example: Using credentials with Google API client directly"""
    from mcp_hub.auth.google_auth import get_google_creds
    from googleapiclient.discovery import build

    print("=" * 60)
    print("Example: Direct Google API Call")
    print("=" * 60)

    # Get credentials from OMA Backend
    creds = get_google_creds()

    # Build Gmail service
    gmail = build("gmail", "v1", credentials=creds)

    # Get user profile
    profile = gmail.users().getProfile(userId="me").execute()

    print("Gmail Profile:")
    print(f"  Email: {profile.get('emailAddress')}")
    print(f"  Messages Total: {profile.get('messagesTotal')}")
    print(f"  Threads Total: {profile.get('threadsTotal')}")
    print()


def main():
    """Run all examples"""
    print("\n")
    print("=" * 60)
    print("MCP Google Hub - OMA Backend Integration Examples")
    print("=" * 60)
    print()

    # Check configuration
    print("Configuration:")
    print(f"  AUTH_MODE: {os.getenv('AUTH_MODE')}")
    print(f"  OMA_BACKEND_URL: {os.getenv('OMA_BACKEND_URL')}")
    print(f"  OMA_ACCESS_TOKEN: {'✅ Set' if os.getenv('OMA_ACCESS_TOKEN') else '❌ Not set'}")
    print()

    if not os.getenv("OMA_ACCESS_TOKEN"):
        print("❌ ERROR: OMA_ACCESS_TOKEN not set!")
        print()
        print("Please set your OMA access token in .env:")
        print("1. Login to OMA Backend:")
        print("   curl -X POST https://rndaibot.ru/apib/v1/auth/login \\")
        print('     -d \'{"username": "user", "password": "pass"}\'')
        print()
        print("2. Copy access_token to .env:")
        print("   OMA_ACCESS_TOKEN=your_token_here")
        return

    # Run examples
    try:
        # Example 1: Check OMA Backend status
        example_check_oma_status()

        # Example 2: Get credentials
        example_get_credentials()

        # Example 3: List unread emails
        example_gmail_list()

        # Example 4: Send email (commented out to avoid spam)
        # example_gmail_send()

        # Example 5: Calendar events
        example_calendar_upcoming()

        # Example 6: Direct API call
        example_direct_api_call()

    except Exception as e:
        print(f"❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
