#!/usr/bin/env python3
"""
First-time authentication helper for Telegram bot.
Run this script to authenticate your Telegram account before using the main bot.
"""

import asyncio
import sys
from telethon import TelegramClient
from config import load_config

async def authenticate():
    """Authenticate with Telegram"""
    print("=== Telegram Authentication Helper ===\n")
    
    try:
        # Load configuration
        config = load_config()
        
        # Create client
        client = TelegramClient(
            config.telegram.session_name,
            config.telegram.api_id,
            config.telegram.api_hash
        )
        
        print(f"Phone number: {config.telegram.phone_number}")
        print("Connecting to Telegram...\n")
        
        # Start client (this will prompt for code)
        await client.start(phone=config.telegram.phone_number)
        
        # Test that we're connected
        me = await client.get_me()
        print(f"\n✓ Successfully authenticated as: {me.first_name} {me.last_name or ''}")
        print(f"Username: @{me.username}" if me.username else "No username set")
        print(f"Phone: {me.phone}")
        
        # Disconnect
        await client.disconnect()
        
        print("\n✓ Authentication successful! You can now run the main bot.")
        print("Run: python main.py")
        
    except Exception as e:
        print(f"\n✗ Authentication failed: {e}")
        print("\nPlease check your configuration in .env file")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(authenticate())