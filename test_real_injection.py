#!/usr/bin/env python3
"""
Real browser cookie injection test
Uses the enhanced cookie injector with actual browser
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Setup logging to see detailed output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Try to import without pydantic first
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from services.session_manager import SessionManager
    from config import config
    HAS_DEPENDENCIES = True
except ImportError as e:
    HAS_DEPENDENCIES = False
    logging.error(f"Missing dependency: {e}")
    logging.error("You may need to install: pip install -r requirements.txt")

# Default test cookies (same as sample)
TEST_COOKIES = [
    {
        "name": "session_id",
        "value": "abc123xyz",
        "domain": ".grok.com",
        "path": "/",
        "httpOnly": True,
        "secure": True,
        "sameSite": "Lax",
        "expires": 1767283816.920831
    },
    {
        "name": "auth_token",
        "value": "Bearer_token_12345",
        "domain": ".grok.com",
        "path": "/",
        "httpOnly": True,
        "secure": True
    }
]

def load_cookies():
    """Load cookies from file or use defaults"""
    # Try to find real cookie file
    possible_paths = [
        "data/grok_cookies.json",
        "grok_cookies.json",
        "sample_cookies.json"
    ]
    
    for path in possible_paths:
        if Path(path).exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    cookies = data.get("cookies", data.get("data", []))
                    if cookies:
                        logging.info(f"Loaded {len(cookies)} cookies from {path}")
                        return cookies
            except Exception as e:
                logging.warning(f"Failed to load {path}: {e}")
    
    # Fallback to test cookies
    logging.info("Using test cookies")
    return TEST_COOKIES

async def test_injection():
    """Test cookie injection with real browser"""
    if not HAS_DEPENDENCIES:
        logging.error("Cannot run test without dependencies")
        return False
    
    cookies = load_cookies()
    
    if not cookies:
        logging.error("No cookies to inject!")
        return False
    
    logging.info(f"{'='*70}")
    logging.info("STARTING COOKIE INJECTION TEST")
    logging.info(f"{'='*70}")
    logging.info(f"Testing with {len(cookies)} cookies")
    logging.info(f"Browser mode: {'HEADLESS' if config.HEADLESS else 'VISIBLE'}")
    logging.info(f"Grok URL: {config.GROK_URL}")
    
    try:
        # Initialize session manager
        async with SessionManager() as session:
            logging.info("Session manager initialized")
            
            # Test injection
            logging.info("Starting cookie injection...")
            success, count = await session.inject_cookies(cookies)
            
            logging.info(f"{'='*70}")
            logging.info("TEST RESULT")
            logging.info(f"{'='*70}")
            logging.info(f"Success: {success}")
            logging.info(f"Cookies injected: {count}")
            logging.info(f"Expected: {len(cookies)}")
            
            if success:
                logging.info("\n✅ INJECTION SUCCESSFUL!")
                
                # Try to verify by checking context cookies
                try:
                    context_cookies = await session.context.cookies()
                    logging.info(f"Cookies in browser context: {len(context_cookies)}")
                    
                    if context_cookies:
                        logging.info("Cookie names:")
                        for c in context_cookies[:5]:
                            logging.info(f"  - {c.get('name', 'unknown')}")
                        if len(context_cookies) > 5:
                            logging.info(f"  ... and {len(context_cookies) - 5} more")
                except Exception as e:
                    logging.warning(f"Could not verify context cookies: {e}")
                
            else:
                logging.error("\n❌ INJECTION FAILED!")
                logging.error("Check the detailed logs above for specific errors")
                
                # Common troubleshooting tips
                logging.error("\nTroubleshooting tips:")
                logging.error("1. Set HEADLESS=False in config.py to see the browser")
                logging.error("2. Check if cookies are expired")
                logging.error("3. Verify cookie domains match the site")
                logging.error("4. Try extracting fresh cookies")
            
            return success
            
    except Exception as e:
        logging.error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_multiple_times(times=3):
    """Test injection multiple times to catch intermittent issues"""
    logging.info(f"Running {times} injection tests...")
    
    results = []
    for i in range(times):
        logging.info(f"\n{'='*70}")
        logging.info(f"TEST RUN #{i+1}")
        logging.info(f"{'='*70}")
        
        success = await test_injection()
        results.append(success)
        
        if i < times - 1:
            logging.info("Waiting 2 seconds before next test...")
            await asyncio.sleep(2)
    
    # Summary
    passed = sum(results)
    failed = len(results) - passed
    
    logging.info(f"\n{'='*70}")
    logging.info("SUMMARY")
    logging.info(f"{'='*70}")
    logging.info(f"Tests run: {times}")
    logging.info(f"Passed: {passed}")
    logging.info(f"Failed: {failed}")
    
    if passed == times:
        logging.info("\n✅ All tests passed!")
    elif failed == times:
        logging.error("\n❌ All tests failed - consistent issue")
    else:
        logging.warning(f"\n⚠️  Intermittent issues: {failed}/{times} failures")
    
    return passed > 0

def show_config():
    """Display current configuration"""
    if not HAS_DEPENDENCIES:
        return
    
    logging.info("Current Configuration:")
    logging.info(f"  GROK_URL: {config.GROK_URL}")
    logging.info(f"  HEADLESS: {config.HEADLESS}")
    logging.info(f"  BROWSER_TIMEOUT: {config.BROWSER_TIMEOUT}")
    logging.info(f"  SESSION_DIR: {config.SESSION_DIR}")
    logging.info("")

def main():
    """Main entry point"""
    logging.info("Starting real cookie injection test")
    
    if not HAS_DEPENDENCIES:
        logging.error("Missing required dependencies. Please install:")
        logging.error("pip install -r requirements.txt")
        return 1
    
    show_config()
    
    # Check if running in valid environment
    try:
        import playwright
        logging.info(f"Playwright version: {playwright.__version__}")
    except ImportError:
        logging.error("Playwright not installed: pip install playwright")
        return 1
    
    # Run test
    try:
        # Test once by default
        success = asyncio.run(test_injection())
        
        # Can also test multiple times
        # success = asyncio.run(test_multiple_times(3))
        
        return 0 if success else 1
        
    except Exception as e:
        logging.error(f"Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)