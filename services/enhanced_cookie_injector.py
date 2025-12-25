"""
Enhanced Cookie Injection Module
Provides improved cookie validation, detailed error reporting, and automatic fix suggestions
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from playwright.async_api import BrowserContext
from config import config

logger = logging.getLogger(__name__)

class EnhancedCookieInjector:
    """Enhanced cookie injection with detailed validation and reporting"""
    
    @staticmethod
    def validate_cookie(cookie: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
        """
        Validate a single cookie and return detailed validation result
        
        Args:
            cookie: The cookie dict to validate
            index: Cookie index for logging
            
        Returns:
            Dict with validation result, including fixed cookie or error details
        """
        errors = []
        warnings = []
        fixes = []
        
        original_cookie = cookie.copy()
        fixed_cookie = {}
        
        # Check required fields
        required_fields = ["name", "value"]
        for field in required_fields:
            if field not in cookie or not cookie[field]:
                errors.append(f"Missing or empty required field: '{field}'")
        
        # Extract basic fields
        name = cookie.get("name", "")
        value = cookie.get("value", "")
        
        if not errors:
            fixed_cookie["name"] = str(name)
            fixed_cookie["value"] = str(value)
        
        # Validate domain
        domain = cookie.get("domain", "")
        if not domain:
            errors.append("Missing domain field")
        else:
            # Fix domain format
            domain_str = str(domain).strip().lower()
            had_leading_dot = domain_str.startswith(".")
            
            # Remove leading dot, then re-add it properly
            domain_clean = domain_str.lstrip(".")
            if had_leading_dot or domain_clean.count(".") >= 1:
                # Subdomain cookie, should have leading dot
                if not domain_str.startswith("."):
                    warnings.append(f"Domain '{domain}' should start with '.' for subdomain cookies")
                    fixes.append(f"Added leading dot to domain: .{domain_clean}")
                fixed_cookie["domain"] = "." + domain_clean
            else:
                # Domain cookie (e.g., 'localhost')
                fixed_cookie["domain"] = domain_clean
        
        # Validate path
        path = cookie.get("path", "/")
        if not path or not isinstance(path, str):
            warnings.append(f"Invalid path '{path}', using default '/'")
            fixes.append("Set path to default '/'")
            fixed_cookie["path"] = "/"
        else:
            fixed_cookie["path"] = str(path)
        
        # Validate boolean fields
        for field, default in [("httpOnly", False), ("secure", False)]:
            value = cookie.get(field, default)
            if not isinstance(value, bool):
                warnings.append(f"Field '{field}' should be boolean, got {type(value).__name__}")
                fixes.append(f"Converted {field} to boolean")
                fixed_cookie[field] = bool(value)
            else:
                fixed_cookie[field] = value
        
        # Validate and normalize expires
        expires = cookie.get("expires")
        if expires is not None:
            try:
                if isinstance(expires, (int, float)):
                    epoch_ts = float(expires)
                    # Fix millisecond timestamps
                    if epoch_ts > 1e10:  # If timestamp is in milliseconds (beyond year 2286)
                        epoch_ts = epoch_ts / 1000
                        warnings.append(f"Converting expires from milliseconds to seconds ({expires} -> {epoch_ts})")
                        fixes.append("Divided expires by 1000 (ms -> s)")
                    
                    # Check if expired
                    now = datetime.now().timestamp()
                    if epoch_ts > 0 and epoch_ts < now:
                        hours_ago = (now - epoch_ts) / 3600
                        errors.append(f"Cookie expired {hours_ago:.1f} hours ago")
                    
                    fixed_cookie["expires"] = epoch_ts
                else:
                    errors.append(f"Invalid expires type: {type(expires).__name__}, expected int/float")
            except Exception as e:
                errors.append(f"Error parsing expires: {str(e)}")
                # Don't include invalid expires
        
        # Validate sameSite
        same_site = cookie.get("sameSite")
        if same_site:
            same_site_str = str(same_site)
            valid_values = ["Lax", "Strict", "None"]
            
            if same_site_str in valid_values:
                fixed_cookie["sameSite"] = same_site_str
            else:
                # Try to normalize
                normalized = {
                    "lax": "Lax",
                    "strict": "Strict",
                    "none": "None",
                    "no_restriction": "None",
                    "unspecified": "Lax"  # Common default
                }.get(same_site_str.lower())
                
                if normalized:
                    warnings.append(f"Invalid sameSite value '{same_site_str}', normalized to '{normalized}'")
                    fixes.append(f"Normalized sameSite to {normalized}")
                    fixed_cookie["sameSite"] = normalized
                else:
                    warnings.append(f"Unknown sameSite value '{same_site_str}', removing")
                    fixes.append(f"Removed invalid sameSite value")
        
        # Size check (browsers have cookie size limits)
        cookie_size = len(fixed_cookie.get("name", "")) + len(fixed_cookie.get("value", ""))
        if cookie_size > 4096:
            warnings.append(f"Cookie size is {cookie_size} bytes (limit is 4096)")
        
        return {
            "index": index,
            "original": original_cookie,
            "fixed": fixed_cookie if len(errors) == 0 else None,
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "fixes": fixes,
            "cookie_size": cookie_size
        }
    
    @staticmethod
    async def inject_single_cookie(context: BrowserContext, cookie: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Inject a single cookie with detailed error handling
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            await context.add_cookies([cookie])
            return True, None
        except Exception as e:
            error_msg = str(e)
            
            # Extract more details from common errors
            if "net::" in error_msg:
                # Network error
                return False, f"Network Error: {error_msg}"
            elif "Invalid cookie" in error_msg or "failed" in error_msg.lower():
                # Cookie validation error from browser
                return False, f"Browser rejected cookie: {error_msg}"
            elif "domain" in error_msg.lower():
                return False, f"Domain error: {error_msg}"
            elif "expired" in error_msg.lower():
                return False, f"Cookie expired: {error_msg}"
            else:
                return False, f"Unexpected error: {error_msg}"
    
    @staticmethod
    async def inject_cookies_with_report(
        context: BrowserContext,
        cookies: List[Dict[str, Any]],
        initial_page: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Inject cookies with comprehensive validation and detailed reporting
        
        Returns:
            Dict with injection results, metrics, and recommendations
        """
        logger.info(f"Starting enhanced cookie injection for {len(cookies)} cookies")
        
        # Track all cookies through validation and injection
        validation_results = []
        injection_results = []
        
        # Phase 1: Validate all cookies
        logger.info("Phase 1: Validating cookie structure...")
        for i, cookie in enumerate(cookies):
            result = EnhancedCookieInjector.validate_cookie(cookie, i)
            validation_results.append(result)
            
            status = "✓" if result["valid"] else "✗"
            logger.info(f"  Cookie {i+1}: {result['original'].get('name', 'unnamed')} [{status}]")
            
            if result["fixes"]:
                for fix in result["fixes"]:
                    logger.info(f"    Fixed: {fix}")
            
            for warning in result["warnings"]:
                logger.warning(f"    Warning: {warning}")
            
            for error in result["errors"]:
                logger.error(f"    Error: {error}")
        
        # Statistics
        valid_cookies = [r["fixed"] for r in validation_results if r["valid"]]
        invalid_cookies = [r for r in validation_results if not r["valid"]]
        
        logger.info(f"\nValidation Summary:")
        logger.info(f"  Total cookies: {len(cookies)}")
        logger.info(f"  Valid cookies: {len(valid_cookies)}")
        logger.info(f"  Invalid cookies: {len(invalid_cookies)}")
        
        if not valid_cookies:
            logger.error("No valid cookies to inject after validation!")
            return {
                "success": False,
                "cookies_processed": len(cookies),
                "cookies_valid": 0,
                "cookies_injected": 0,
                "cookies_failed": len(invalid_cookies),
                "validation_failures": invalid_cookies,
                "error": "All cookies failed validation"
            }
        
        # Phase 2: Visit domains to prime cookie store
        if initial_page:
            domains = set()
            for cookie in valid_cookies:
                domain = cookie.get("domain", "")
                if domain:
                    # Create visit URL from domain
                    if domain.startswith("."):
                        visit_domain = domain[1:]  # Remove leading dot
                    else:
                        visit_domain = domain
                    
                    # Choose protocol
                    if "localhost" in visit_domain or visit_domain.startswith("127.0."):
                        protocol = "http"
                    else:
                        protocol = "https"
                    
                    domains.add(f"{protocol}://{visit_domain}")
            
            logger.info(f"\nPhase 2: Priming cookie store by visiting {len(domains)} domains...")
            for url in sorted(domains):
                try:
                    logger.info(f"  Visiting: {url}")
                    await initial_page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    await asyncio.sleep(0.5)  # Brief pause
                except Exception as e:
                    logger.warning(f"  Failed to visit {url}: {str(e)}")
        
        # Phase 3: Inject valid cookies
        logger.info(f"\nPhase 3: Injecting {len(valid_cookies)} validated cookies...")
        injected_count = 0
        failed_count = 0
        
        for i, cookie in enumerate(valid_cookies):
            success, error = await EnhancedCookieInjector.inject_single_cookie(context, cookie)
            
            cookie_name = cookie.get("name", f"unnamed_{i}")
            
            if success:
                injected_count += 1
                logger.info(f"  [{injected_count}/{len(valid_cookies)}] ✓ Injected: {cookie_name}")
                injection_results.append({
                    "cookie": cookie,
                    "success": True
                })
            else:
                failed_count += 1
                logger.error(f"  [{i+1}/{len(valid_cookies)}] ✗ Failed to inject {cookie_name}: {error}")
                injection_results.append({
                    "cookie": cookie,
                    "success": False,
                    "error": error
                })
        
        # Final statistics
        success = injected_count > 0 and failed_count == 0
        
        logger.info(f"\n{'='*60}")
        logger.info("INJECTION REPORT")
        logger.info(f"{'='*60}")
        logger.info(f"Total cookies: {len(cookies)}")
        logger.info(f"Valid after validation: {len(valid_cookies)}")
        logger.info(f"Successfully injected: {injected_count}")
        logger.info(f"Failed injection: {failed_count}")
        logger.info(f"Overall success: {'✓' if success else '✗'}")
        
        # Generate recommendations
        recommendations = []
        
        if invalid_cookies:
            recommendations.append(f"Fix validation errors for {len(invalid_cookies)} cookies")
        
        if failed_count > 0:
            recommendations.append(f"Check browser console for errors related to {failed_count} failed cookies")
        
        if injected_count < len(valid_cookies):
            recommendations.append("Verify cookie domains match the site you are visiting")
        
        # Check domain mismatches
        if initial_page:
            try:
                current_url = initial_page.url
                if current_url:
                    from urllib.parse import urlparse
                    current_domain = urlparse(current_url).netloc
                    
                    cookie_domains = set()
                    for cookie in valid_cookies:
                        domain = cookie.get("domain", "")
                        if domain.startswith("."):
                            cookie_domains.add(domain[1:])
                        else:
                            cookie_domains.add(domain)
                    
                    if current_domain not in cookie_domains:
                        warnings = [f"You are on {current_domain} but cookies are for {list(cookie_domains)[:3]}"]
                        recommendations.append(f"Domain mismatch: Consider extracting cookies from {current_domain}")
            except:
                pass
        
        if not recommendations:
            recommendations.append("Cookie injection completed successfully!")
        
        return {
            "success": success,
            "cookies_processed": len(cookies),
            "cookies_valid": len(valid_cookies),
            "cookies_injected": injected_count,
            "cookies_failed": failed_count + len(invalid_cookies),
            "validation_failures": invalid_cookies,
            "injection_failures": [r for r in injection_results if not r["success"]],
            "recommendations": recommendations
        }