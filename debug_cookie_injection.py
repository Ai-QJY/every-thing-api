#!/usr/bin/env python3
"""
Debug script for cookie injection
Runs comprehensive tests to identify why cookies are not being injected
"""
import asyncio
import json
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

sys.path.insert(0, str(Path(__file__).parent))

from config import config
from services.session_manager import SessionManager

def load_cookies_from_file(filepath):
    """Load cookies from JSON file"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            cookies = data.get("cookies", [])
            logging.info(f"Loaded {len(cookies)} cookies from {filepath}")
            return cookies
    except Exception as e:
        logging.error(f"Failed to load cookies from {filepath}: {e}")
        return []

def validate_cookie_structure(cookie: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize a single cookie"""
    errors = []
    warnings = []
    
    # Check required fields
    required_fields = ["name", "value", "domain"]
    for field in required_fields:
        if field not in cookie:
            errors.append(f"Missing required field: {field}")
    
    # Check name and value
    name = cookie.get("name", "")
    value = cookie.get("value", "")
    
    if not name:
        errors.append("Cookie name is empty")
    if not value:
        warnings.append("Cookie value is empty")
    
    # Check domain
    domain = cookie.get("domain", "")
    if not domain:
        errors.append("Missing domain")
    else:
        # Ensure domain starts with dot for subdomains
        if not domain.startswith(".") and "." in domain:
            warnings.append(f"Domain '{domain}' should start with . for subdomain cookies")
    
    # Check path
    path = cookie.get("path", "/")
    if not path:
        cookie["path"] = "/"
        warnings.append("Path was empty, set to '/'")
    
    # Check expires
    expires = cookie.get("expires")
    if expires is not None:
        try:
            if isinstance(expires, (int, float)):
                epoch_ts = float(expires)
                # Convert milliseconds to seconds if needed
                if epoch_ts > 1e10:
                    epoch_ts = epoch_ts / 1000
                    warnings.append("Converting expires from milliseconds to seconds")
                
                expiry_date = datetime.fromtimestamp(epoch_ts)
                now = datetime.now()
                
                if epoch_ts <= 0:
                    warnings.append("Expires is 0 (session cookie)")
                elif epoch_ts < now.timestamp():
                    errors.append(f"Cookie expired at {expiry_date}")
                else:
                    hours_left = (expiry_date - now).total_seconds() / 3600
                    if hours_left < 24:
                        warnings.append(f"Cookie expires in {hours_left:.1f} hours")
                
                cookie["expires"] = epoch_ts
            else:
                errors.append(f"Invalid expires format: {expires}")
        except Exception as e:
            errors.append(f"Error parsing expires: {e}")
    
    # Check boolean fields
    http_only = cookie.get("httpOnly")
    if http_only is not None and not isinstance(http_only, bool):
        warnings.append(f"httpOnly should be boolean, got {type(http_only)}")
        cookie["httpOnly"] = bool(http_only)
    
    secure = cookie.get("secure")
    if secure is not None and not isinstance(secure, bool):
        warnings.append(f"secure should be boolean, got {type(secure)}")
        cookie["secure"] = bool(secure)
    
    # Validate sameSite
    same_site = cookie.get("sameSite")
    if same_site:
        valid_values = ["Lax", "Strict", "None"]
        if same_site not in valid_values:
            # Try to normalize
            normalized = {
                "lax": "Lax",
                "strict": "Strict", 
                "none": "None",
                "no_restriction": "None"
            }.get(str(same_site).lower())
            
            if normalized:
                cookie["sameSite"] = normalized
                warnings.append(f"Normalized sameSite from '{same_site}' to '{normalized}'")
            else:
                warnings.append(f"Invalid sameSite value: '{same_site}', removing")
                del cookie["sameSite"]
    
    return {
        "cookie": cookie,
        "errors": errors,
        "warnings": warnings,
        "valid": len(errors) == 0
    }

def validate_all_cookies(cookies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate all cookies and return detailed report"""
    total = len(cookies)
    valid_cookies = []
    invalid_cookies = []
    domain_stats = {}
    
    logging.info(f"\n{'='*60}")
    logging.info(f"Validating {total} cookies")
    logging.info(f"{'='*60}")
    
    for i, cookie in enumerate(cookies):
        result = validate_cookie_structure(cookie.copy())
        cookie_obj = result["cookie"]
        
        # Count domains
        domain = cookie_obj.get("domain", "unknown")
        domain_stats[domain] = domain_stats.get(domain, 0) + 1
        
        if result["valid"]:
            valid_cookies.append(cookie_obj)
            status = "✓"
        else:
            invalid_cookies.append({
                "cookie": cookie_obj,
                "errors": result["errors"],
                "warnings": result["warnings"]
            })
            status = "✗"
        
        logging.info(f"\n{i+1:2d}. [{status}] Cookie: {cookie_obj.get('name', 'unnamed')}")
        logging.info(f"    Domain: {cookie_obj.get('domain')}")
        
        if result["warnings"]:
            for w in result["warnings"]:
                logging.info(f"    ⚠️  {w}")
        
        if not result["valid"]:
            for e in result["errors"]:
                logging.info(f"    ❌ {e}")
    
    logging.info(f"\n{'='*60}")
    logging.info(f"Summary:")
    logging.info(f"  Total cookies: {total}")
    logging.info(f"  Valid cookies: {len(valid_cookies)}")
    logging.info(f"  Invalid cookies: {len(invalid_cookies)}")
    logging.info(f"\nDomain distribution:")
    for domain, count in sorted(domain_stats.items()):
        logging.info(f"  {domain}: {count}")
    
    return {
        "total": total,
        "valid": len(valid_cookies),
        "invalid": len(invalid_cookies),
        "valid_cookies": valid_cookies,
        "invalid_cookies": invalid_cookies,
        "domain_stats": domain_stats
    }

async def test_cookie_injection_detailed(cookies: List[Dict[str, Any]]):
    """Test injection with detailed logging"""
    logging.info(f"\n{'='*60}")
    logging.info("TESTING COOKIE INJECTION")
    logging.info(f"{'='*60}")
    
    if not cookies:
        logging.error("No cookies provided for injection test")
        return False, 0
    
    # Validate cookies first
    validation = validate_all_cookies(cookies)
    
    if validation["valid"] == 0:
        logging.error("No valid cookies to inject!")
        return False, 0
    
    # Test injection
    try:
        session_manager = SessionManager()
        success, cookie_count = await session_manager.inject_cookies(validation["valid_cookies"])
        
        logging.info(f"\n{'='*60}")
        logging.info("INJECTION RESULT:")
        logging.info(f"{'='*60}")
        logging.info(f"Success: {success}")
        logging.info(f"Number of cookies injected: {cookie_count}")
        logging.info(f"Expected: {validation['valid']}")
        
        if not success:
            logging.error("INJECTION FAILED!")
            logging.error("Make sure:")
            logging.error("1. Browser is visible (HEADLESS=False)")
            logging.error("2. You can manually check the browser state")
            logging.error("3. Check logs above for any errors during injection")
        else:
            logging.info("✅ INJECTION SUCCESSFUL!")
        
        await session_manager.close()
        return success, cookie_count
        
    except Exception as e:
        logging.error(f"Exception during injection test: {e}")
        import traceback
        traceback.print_exc()
        return False, 0

def check_cookie_file_exists():
    """Check if cookie file exists in standard locations"""
    possible_paths = [
        config.GROK_COOKIE_FILE_PATH,
        Path("data/grok_cookies.json"),
        Path("grok_cookies.json"),
    ]
    
    for path in possible_paths:
        if Path(path).exists():
            logging.info(f"Found cookie file at: {path}")
            return str(path)
    
    logging.warning("No cookie file found in standard locations")
    logging.info(f"Expected at: {config.GROK_COOKIE_FILE_PATH}")
    return None

def create_test_cookies():
    """Create test cookies for validation testing"""
    return [
        {
            "name": "test_cookie_1",
            "value": "test_value_1",
            "domain": ".grok.com",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax"
        },
        {
            "name": "test_cookie_2",
            "value": "test_value_2",
            "domain": ".x.ai",
            "path": "/",
            "expires": (datetime.now().timestamp() + 86400),  # 24 hours from now
            "httpOnly": False,
            "secure": True,
            "sameSite": "Strict"
        }
    ]

async def main():
    """Main test function"""
    logging.info("Starting cookie injection debug test")
    
    # Try to load real cookies first
    cookie_file = check_cookie_file_exists()
    cookies = []
    
    if cookie_file:
        cookies = load_cookies_from_file(cookie_file)
    else:
        logging.warning("No cookie file found, using test cookies")
        cookies = create_test_cookies()
    
    if not cookies:
        logging.error("No cookies available for testing")
        return False
    
    # Run injection test
    success, count = await test_cookie_injection_detailed(cookies)
    
    logging.info(f"\n{'='*60}")
    logging.info("FINAL RESULT")
    logging.info(f"{'='*60}")
    logging.info(f"Injection successful: {success}")
    logging.info(f"Cookies injected: {count}")
    
    return success

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except Exception as e:
        logging.error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)