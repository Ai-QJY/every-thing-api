#!/usr/bin/env python3
"""
Quick cookie status checker.

This script quickly checks the status of saved cookies without injecting them.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import config


def check_cookies():
    """Check the status of saved cookies."""
    
    cookie_file = Path(config.GROK_COOKIE_FILE_PATH)
    
    print("\n" + "="*60)
    print("🍪 Cookie Status Checker")
    print("="*60 + "\n")
    
    # Check if file exists
    if not cookie_file.exists():
        print(f"❌ Cookie file not found: {cookie_file}")
        print("\n💡 Please extract cookies first:")
        print("   python scripts/extract_grok_cookies.py")
        return False
    
    # Load cookies
    try:
        with open(cookie_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to read cookie file: {e}")
        return False
    
    cookies = data.get("cookies", [])
    extracted_at = data.get("extracted_at")
    
    if not cookies:
        print("❌ No cookies found in file")
        return False
    
    print(f"📁 Cookie file: {cookie_file}")
    print(f"📅 Extracted at: {extracted_at}")
    print(f"🍪 Total cookies: {len(cookies)}")
    print()
    
    # Analyze cookies
    current_ts = datetime.now(timezone.utc).timestamp()
    
    valid_cookies = []
    expired_cookies = []
    session_cookies = []
    domains = set()
    
    for cookie in cookies:
        name = cookie.get("name", "")
        domain = cookie.get("domain", "")
        expires = cookie.get("expires")
        
        domains.add(domain)
        
        if expires is None or expires == -1:
            session_cookies.append(name)
        elif expires > 0:
            if expires < current_ts:
                expired_cookies.append(name)
            else:
                valid_cookies.append(name)
    
    # Print summary
    print("📊 Cookie Status:")
    print(f"   ✅ Valid: {len(valid_cookies)}")
    print(f"   🕐 Session: {len(session_cookies)}")
    print(f"   ❌ Expired: {len(expired_cookies)}")
    print()
    
    print("🌐 Domains:")
    for domain in sorted(domains):
        print(f"   - {domain}")
    print()
    
    # Show important cookies
    important_patterns = ["auth", "session", "token", "sid", "user"]
    important_cookies = [
        c for c in cookies 
        if any(pattern in c.get("name", "").lower() for pattern in important_patterns)
    ]
    
    if important_cookies:
        print("🔑 Important cookies (auth-related):")
        for cookie in important_cookies:
            name = cookie.get("name")
            expires = cookie.get("expires")
            
            if expires and expires > 0:
                expire_dt = datetime.fromtimestamp(expires, tz=timezone.utc)
                status = "✅" if expires > current_ts else "❌"
                print(f"   {status} {name} (expires: {expire_dt.strftime('%Y-%m-%d %H:%M:%S UTC')})")
            else:
                print(f"   🕐 {name} (session cookie)")
        print()
    
    # Show expired cookies if any
    if expired_cookies:
        print("⚠️  Expired cookies:")
        for name in expired_cookies[:5]:  # Show first 5
            print(f"   - {name}")
        if len(expired_cookies) > 5:
            print(f"   ... and {len(expired_cookies) - 5} more")
        print()
    
    # Recommendations
    print("💡 Recommendations:")
    
    if len(expired_cookies) > len(cookies) * 0.3:
        print("   ⚠️  More than 30% of cookies are expired!")
        print("   → Recommend extracting fresh cookies")
    elif expired_cookies:
        print(f"   ℹ️  {len(expired_cookies)} expired cookies found")
        print("   → Should still work, but consider refreshing if injection fails")
    else:
        print("   ✅ All cookies are valid!")
        print("   → Ready for injection")
    
    # Calculate age
    if extracted_at:
        try:
            extracted_dt = datetime.fromisoformat(extracted_at.replace('Z', '+00:00'))
            age = datetime.now(timezone.utc) - extracted_dt
            age_hours = age.total_seconds() / 3600
            
            print()
            print(f"⏰ Cookie age: {age_hours:.1f} hours")
            
            if age_hours > 24:
                print("   ⚠️  Cookies are more than 24 hours old")
                print("   → Recommend extracting fresh cookies")
            elif age_hours > 6:
                print("   ℹ️  Cookies are getting old")
                print("   → Should work, but monitor for issues")
            else:
                print("   ✅ Cookies are fresh")
        except Exception:
            pass
    
    print("\n" + "="*60 + "\n")
    
    return len(expired_cookies) < len(cookies)


if __name__ == "__main__":
    try:
        success = check_cookies()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
