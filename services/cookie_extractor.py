"""
Grok Cookie Extractor Module

Automates the extraction of cookies from Grok.com after login.
This module handles browser automation, login flow, and cookie collection.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import config

logger = logging.getLogger(__name__)


class GrokCookieExtractor:
    """
    Handles automated cookie extraction from Grok.com
    """
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
    
    async def initialize(self):
        """Initialize Playwright and browser"""
        if self.playwright is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=config.GROK_HEADLESS_MODE,
                timeout=config.BROWSER_TIMEOUT
            )
    
    async def close(self):
        """Close browser and cleanup resources"""
        if self.page:
            try:
                await self.page.close()
            except Exception:
                pass
            self.page = None
            
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
            self.context = None
            
        if self.browser:
            try:
                await self.browser.close()
            except Exception:
                pass
            self.browser = None
            
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
            self.playwright = None
    
    async def extract_cookies(
        self,
        email: str,
        password: str,
        timeout_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Automate login to Grok and extract all cookies.
        
        Args:
            email: User email for Grok login
            password: User password for Grok login
            timeout_seconds: Custom timeout for the operation
            
        Returns:
            Dict containing status, cookies, and metadata
        """
        timeout = timeout_seconds or config.GROK_COOKIE_TIMEOUT
        
        logger.info(f"Starting Grok cookie extraction for user: {email}")
        start_time = datetime.now(timezone.utc)
        
        try:
            await self.initialize()
            
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True
            )
            
            self.page = await self.context.new_page()
            
            await self._perform_login(email, password, timeout)
            
            cookies = await self._extract_all_cookies()
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            logger.info(
                f"Successfully extracted {len(cookies)} cookies in {duration:.2f}s"
            )
            
            return {
                "status": "success",
                "cookies": cookies,
                "cookie_count": len(cookies),
                "extracted_at": end_time.isoformat(),
                "duration_seconds": duration
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Cookie extraction timed out after {timeout}s")
            return {
                "status": "error",
                "error_type": "timeout",
                "error_message": f"Operation timed out after {timeout} seconds",
                "cookies": [],
                "cookie_count": 0
            }
        except Exception as e:
            logger.error(f"Cookie extraction failed: {str(e)}")
            return {
                "status": "error",
                "error_type": "extraction_failed",
                "error_message": str(e),
                "cookies": [],
                "cookie_count": 0
            }
        finally:
            await self.close()
    
    async def _perform_login(
        self,
        email: str,
        password: str,
        timeout_seconds: int
    ):
        """
        Perform the login flow on Grok.com
        """
        login_timeout = timeout_seconds * 1000
        
        try:
            await self.page.goto(config.GROK_URL, timeout=login_timeout)
            
            await self.page.wait_for_load_state("networkidle", timeout=30000)
            
            email_selectors = [
                'input[type="email"]',
                'input[name="email"]',
                'input[id*="email"]',
                'input[placeholder*="email"]',
                'input[autocomplete="email"]'
            ]
            
            password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[id*="password"]'
            ]
            
            email_input = None
            for selector in email_selectors:
                try:
                    email_input = await self.page.wait_for_selector(
                        selector, timeout=10000
                    )
                    if email_input:
                        break
                except Exception:
                    continue
            
            if not email_input:
                raise Exception("Email input field not found")
            
            await self.page.fill('input[type="email"]', email)
            
            await self.page.wait_for_selector('input[type="password"]', timeout=10000)
            await self.page.fill('input[type="password"]', password)
            
            submit_selectors = [
                'button[type="submit"]',
                'button:has-text("Sign")',
                'button:has-text("Log")',
                'button:has-text("Continue")'
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = await self.page.wait_for_selector(
                        selector, timeout=5000
                    )
                    if submit_button:
                        break
                except Exception:
                    continue
            
            if submit_button:
                await submit_button.click()
            else:
                await self.page.press('input[type="password"]', 'Enter')
            
            await self.page.wait_for_load_state("networkidle", timeout=login_timeout)
            
            current_url = self.page.url
            logger.info(f"Login navigation complete. Current URL: {current_url}")
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise
    
    async def _extract_all_cookies(self) -> List[Dict[str, Any]]:
        """
        Extract all cookies from the current browser context
        """
        raw_cookies = await self.context.cookies()
        
        formatted_cookies = []
        for cookie in raw_cookies:
            formatted_cookie = {
                "name": cookie.get("name", ""),
                "value": cookie.get("value", ""),
                "domain": cookie.get("domain", ""),
                "path": cookie.get("path", "/"),
                "expires": cookie.get("expires"),
                "httpOnly": cookie.get("httpOnly", False),
                "secure": cookie.get("secure", False),
                "sameSite": cookie.get("sameSite")
            }
            formatted_cookies.append(formatted_cookie)
        
        return formatted_cookies


async def extract_cookies_from_grok(
    email: str,
    password: str,
    timeout_seconds: Optional[int] = None
) -> Dict[str, Any]:
    """
    Convenience function to extract cookies from Grok.
    
    Args:
        email: User email for Grok login
        password: User password for Grok login
        timeout_seconds: Optional custom timeout
        
    Returns:
        Dict containing status, cookies, and metadata
    """
    extractor = GrokCookieExtractor()
    return await extractor.extract_cookies(email, password, timeout_seconds)
