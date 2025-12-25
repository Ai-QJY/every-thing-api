#!/usr/bin/env python3
"""
Debug script to test cookie injection and understand why validation fails
"""
import asyncio
import logging
import json
import sys
from pathlib import Path
from services.session_manager import SessionManager
from services.cookie_extractor import load_cookies_from_file
from config import config

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def debug_cookie_injection():
    """Test cookie injection and print detailed debug information"""
    print("=" * 80)
    print("🔍 Cookie Injection Debug Tool")
    print("=" * 80)
    
    # Load cookies
    try:
        cookies = load_cookies_from_file()
        print(f"\n✅ Loaded {len(cookies)} cookies from file")
        
        # Print cookie summary
        print("\n📋 Cookie Summary:")
        for cookie in cookies[:5]:  # Show first 5
            print(f"  - {cookie['name']}: domain={cookie.get('domain')}, expires={cookie.get('expires')}")
        if len(cookies) > 5:
            print(f"  ... and {len(cookies) - 5} more")
            
    except Exception as e:
        print(f"\n❌ Failed to load cookies: {e}")
        print("\n💡 Hint: Make sure you have extracted cookies first using:")
        print("   python scripts/extract_grok_cookies.py")
        return
    
    # Check if cookies are expired
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
    
    print(f"\n⏰ Cookie Expiration Status:")
    print(f"  - Valid: {valid_count}")
    print(f"  - Expired: {expired_count}")
    print(f"  - Session (no expiry): {len(cookies) - valid_count - expired_count}")
    
    # Create session manager
    print("\n🚀 Starting cookie injection test...")
    session_manager = SessionManager()
    
    try:
        print("\n1️⃣ Initializing browser...")
        await session_manager.initialize()
        print("   ✅ Browser initialized")
        
        print("\n2️⃣ Injecting cookies...")
        success, cookie_count = await session_manager.inject_cookies(
            cookies,
            user_agent=None,
            remember_me=True
        )
        
        if success:
            print(f"\n✅ SUCCESS! Injected {cookie_count} cookies and validated session")
        else:
            print(f"\n❌ FAILED! Injected {cookie_count} cookies but session validation failed")
            print("\nPossible causes:")
            print("1. Cookies are expired or invalid")
            print("2. The session was invalidated on the server")
            print("3. Login detection logic needs adjustment")
            print("4. Network/connectivity issues")
            
        # Get current page URL
        if session_manager.page:
            current_url = session_manager.page.url
            print(f"\n🌐 Current page URL: {current_url}")
            
            # Take a screenshot for debugging
            screenshot_path = Path(config.OUTPUT_DIR) / "debug_cookie_injection.png"
            await session_manager.page.screenshot(path=str(screenshot_path))
            print(f"📸 Screenshot saved to: {screenshot_path}")
            
            # Print page title
            title = await session_manager.page.title()
            print(f"📄 Page title: {title}")
            
            # Get all cookies from context
            current_cookies = await session_manager.context.cookies()
            print(f"\n🍪 Current browser has {len(current_cookies)} cookies")
            
            # Keep browser open for manual inspection
            print("\n⏳ Keeping browser open for 30 seconds for manual inspection...")
            print("   You can check if the page is actually logged in")
            await asyncio.sleep(30)
        
    except Exception as e:
        print(f"\n❌ Error during injection: {e}")
        logging.exception("Full error details:")
    finally:
        print("\n🧹 Cleaning up...")
        await session_manager.close()
        print("   ✅ Done")

if __name__ == "__main__":
    asyncio.run(debug_cookie_injection())
