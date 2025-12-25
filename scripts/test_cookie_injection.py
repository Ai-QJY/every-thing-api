#!/usr/bin/env python3
"""
Test script for cookie injection functionality.

This script helps test and debug the cookie injection process.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.session_manager import SessionManager
from services.cookie_extractor import load_cookies_from_file
from config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_cookie_injection():
    """Test cookie injection with cookies from file."""
    
    print("\n" + "="*60)
    print("Cookie Injection Test")
    print("="*60 + "\n")
    
    # Load cookies from file
    cookie_file = config.GROK_COOKIE_FILE_PATH
    print(f"Loading cookies from: {cookie_file}")
    
    if not Path(cookie_file).exists():
        print(f"❌ Cookie file not found: {cookie_file}")
        print("\nPlease run the extraction script first:")
        print("  python scripts/extract_grok_cookies.py")
        return
    
    cookies = load_cookies_from_file()
    
    if not cookies:
        print("❌ No cookies found in file")
        return
    
    print(f"✅ Loaded {len(cookies)} cookies")
    
    # Show cookie summary
    domains = set(c.get("domain", "") for c in cookies)
    print(f"\nCookie domains: {domains}")
    
    # Check for expired cookies
    from datetime import datetime
    current_ts = datetime.now().timestamp()
    expired_count = 0
    valid_count = 0
    
    for cookie in cookies:
        expires = cookie.get("expires")
        if expires and expires > 0:
            if expires < current_ts:
                expired_count += 1
            else:
                valid_count += 1
        else:
            valid_count += 1  # Session cookies are considered valid
    
    print(f"\nCookie status:")
    print(f"  - Valid: {valid_count}")
    print(f"  - Expired: {expired_count}")
    
    # Proceed with injection
    print("\n" + "-"*60)
    print("Starting cookie injection...")
    print("-"*60 + "\n")
    
    session_manager = SessionManager()
    
    try:
        success, cookie_count = await session_manager.inject_cookies(
            cookies,
            user_agent=None,
            remember_me=True
        )
        
        if success:
            print("\n" + "="*60)
            print("✅ SUCCESS!")
            print("="*60)
            print(f"Injected {cookie_count} cookies")
            print("Session is valid and authenticated")
        else:
            print("\n" + "="*60)
            print("❌ FAILED")
            print("="*60)
            print("Cookie injection completed but session validation failed")
            print("\nPossible issues:")
            print("  1. Cookies may be expired or invalid")
            print("  2. Session may have been invalidated on the server")
            print("  3. Additional authentication may be required")
            print("\nTry extracting fresh cookies from an active session")
            
    except Exception as e:
        print("\n" + "="*60)
        print("❌ ERROR")
        print("="*60)
        print(f"Exception: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Note: We don't close the browser here to allow inspection
        # In production, you'd want to call await session_manager.close()
        print("\n💡 Browser left open for inspection")
        print("   Press Ctrl+C to close and exit")
        
        try:
            # Keep the script running so browser stays open
            await asyncio.sleep(300)  # 5 minutes
        except KeyboardInterrupt:
            print("\n\nClosing browser...")
            await session_manager.close()
            print("Done!")


if __name__ == "__main__":
    try:
        asyncio.run(test_cookie_injection())
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(0)
