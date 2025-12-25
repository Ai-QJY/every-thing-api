#!/usr/bin/env python3
"""
Simple cookie validation test - no external dependencies except json
"""

import json
import sys
import logging
import os
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def find_cookie_file():
    """Search for cookie files in common locations"""
    search_paths = [
        "data/grok_cookies.json",
        "grok_cookies.json", 
        "cookies.json",
        "session_cookies.json"
    ]
    
    for path in search_paths:
        if os.path.exists(path):
            return path
    
    return None

def load_cookies(filepath):
    """Load cookies from JSON file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        cookies = None
        if isinstance(data, dict):
            cookies = data.get("cookies", data.get("data", []))
        elif isinstance(data, list):
            cookies = data
        
        if not cookies:
            logging.warning(f"No cookies found in {filepath}")
            return []
        
        logging.info(f"Successfully loaded {len(cookies)} cookies from {filepath}")
        return cookies
    except Exception as e:
        logging.error(f"Failed to load cookies from {filepath}: {e}")
        return []

def validate_cookie_field(cookie, field, required=True):
    """Validate a single cookie field"""
    if field not in cookie:
        if required:
            return False, f"Missing required field: {field}"
        else:
            return True, None
    
    value = cookie[field]
    
    if field in ["name", "value", "domain", "path"]:
        if not isinstance(value, str):
            return False, f"Field '{field}' must be string, got {type(value).__name__}"
        if required and not value.strip():
            return False, f"Field '{field}' cannot be empty"
    
    elif field in ["httpOnly", "secure"]:
        if not isinstance(value, bool):
            return False, f"Field '{field}' must be boolean, got {type(value).__name__}"
    
    elif field == "expires":
        if value is None:
            return True, None
        if not isinstance(value, (int, float)):
            return False, f"Field '{field}' must be number, got {type(value).__name__}"
    
    elif field == "sameSite":
        if value is None:
            return True, None
        if not isinstance(value, str):
            return False, f"Field '{field}' must be string or null, got {type(value).__name__}"
        valid_values = ["Lax", "Strict", "None"]
        if value not in valid_values:
            return False, f"Field '{field}' must be one of {valid_values}, got '{value}'"
    
    return True, None

def validate_cookie(cookie, index=0):
    """Validate a single cookie"""
    issues = []
    warnings = []
    
    # Check all required fields
    required_fields = ["name", "value", "domain"]
    for field in required_fields:
        valid, error = validate_cookie_field(cookie, field, required=True)
        if not valid:
            issues.append(error)
    
    # Check optional fields
    optional_fields = ["path", "expires", "httpOnly", "secure", "sameSite"]
    for field in optional_fields:
        if field in cookie:
            valid, error = validate_cookie_field(cookie, field, required=False)
            if not valid:
                issues.append(error)
    
    # Custom validations
    name = cookie.get("name", "")
    if name and len(name) > 1024:
        warnings.append(f"Cookie name very long: {len(name)} characters")
    
    value = cookie.get("value", "")
    if value and len(value) > 4096:
        issues.append(f"Cookie value too large: {len(value)} bytes (max 4096)")
    
    # Domain validation
    domain = cookie.get("domain", "")
    if domain:
        if not domain.startswith(".") and domain != "localhost":
            warnings.append(f"Domain '{domain}' should start with '.' for subdomain cookies")
        if " " in domain:
            issues.append("Domain cannot contain spaces")
    
    # Expires validation
    if "expires" in cookie and cookie["expires"] is not None:
        expires = cookie["expires"]
        # Handle milliseconds
        if isinstance(expires, (int, float)) and expires > 1e10:
            expires = expires / 1000
            warnings.append(f"Converted expires from milliseconds to seconds: {cookie['expires']} -> {expires}")
            cookie["expires"] = expires
        
        # Check expiration
        now = datetime.now().timestamp()
        if expires <= 0:
            warnings.append("Expires is 0 (session cookie)")
        elif expires < now:
            hours_ago = (now - expires) / 3600
            issues.append(f"Cookie expired {hours_ago:.1f} hours ago")
    
    return {
        "index": index,
        "name": cookie.get("name", f"cookie_{index}"),
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "cookie": cookie
    }

def validate_all_cookies(cookies):
    """Validate all cookies and generate report"""
    if not cookies:
        logging.warning("No cookies to validate")
        return None
    
    logging.info(f"Validating {len(cookies)} cookies...")
    
    results = []
    for i, cookie in enumerate(cookies):
        result = validate_cookie(cookie, i)
        results.append(result)
        
        status = "✓" if result["valid"] else "✗"
        logging.info(f"Cookie {i+1:2d}: {status} {result['name']}")
        
        if result["warnings"]:
            for w in result["warnings"]:
                logging.info(f"         ! {w}")
        
        if not result["valid"]:
            for issue in result["issues"]:
                logging.error(f"         ✗ {issue}")
    
    # Summary
    valid_count = sum(1 for r in results if r["valid"])
    invalid_count = len(cookies) - valid_count
    
    logging.info(f"\n{'='*60}")
    logging.info(f"SUMMARY: {valid_count} valid, {invalid_count} invalid")
    logging.info(f"{'='*60}")
    
    return {
        "total": len(cookies),
        "valid": valid_count,
        "invalid": invalid_count,
        "results": results,
        "success": invalid_count == 0
    }

def create_sample_cookies():
    """Create valid sample cookies for testing"""
    now = datetime.now().timestamp()
    sample = [
        {
            "name": "session_id",
            "value": "abc123xyz",
            "domain": ".grok.com",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax",
            "expires": now + (86400 * 7)  # 7 days
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
    
    # Save sample
    with open("sample_cookies.json", "w") as f:
        json.dump({"cookies": sample}, f, indent=2)
    
    logging.info("Created sample_cookies.json with valid test cookies")
    return sample

def main():
    """Main function"""
    # Try to find cookie file
    cookie_file = find_cookie_file()
    cookies = []
    
    if cookie_file:
        logging.info(f"Found cookie file: {cookie_file}")
        cookies = load_cookies(cookie_file)
    else:
        logging.warning("No cookie file found")
        logging.info("Creating test cookies for demonstration...")
        cookies = create_sample_cookies()
        logging.info(f"\nTo use real cookies:")
        logging.info("1. Extract cookies using your browser")
        logging.info("2. Save them as 'grok_cookies.json'")
        logging.info("3. Run this script again")
    
    if not cookies:
        logging.error("No cookies available for validation")
        return 1
    
    # Run validation
    result = validate_all_cookies(cookies)
    
    if result and result["success"]:
        logging.info(f"\n✅ Cookie validation PASSED")
        logging.info(f"All {result['valid']} cookies are valid for injection")
        return 0
    else:
        logging.error(f"\n❌ Cookie validation FAILED")
        if result:
            logging.error(f"{result['invalid']} cookies have errors that need fixing")
            logging.error("\nCommon fixes:")
            logging.error("1. Add missing required fields (name, value, domain)")
            logging.error("2. Remove expired cookies")
            logging.error("3. Fix domain format (add . prefix for subdomains)")
            logging.error("4. Fix sameSite values (must be Lax, Strict, or None)")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        logging.error(f"Script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)