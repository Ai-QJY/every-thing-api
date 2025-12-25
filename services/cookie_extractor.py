"""
Grok Cookie Extractor Module

Automates the extraction of cookies from Grok.com after login.
This module handles browser automation, login flow, and cookie collection.

Supports two modes:
1. Automated login with email/password
2. Semi-automated manual OAuth (user manually completes Google login)
"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
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


# ==================== Manual OAuth Functions ====================

def save_cookies_to_file(cookies: List[Dict[str, Any]], filepath: Optional[str] = None) -> str:
    """
    Save cookies to a JSON file.
    
    Args:
        cookies: List of cookie dictionaries
        filepath: Optional custom filepath, uses config.GROK_COOKIE_FILE_PATH by default
        
    Returns:
        Path to the saved file
    """
    save_path = Path(filepath or config.GROK_COOKIE_FILE_PATH)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    save_data = {
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "cookie_count": len(cookies),
        "cookies": cookies
    }
    
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Cookies saved to {save_path}")
    return str(save_path)


def load_cookies_from_file(filepath: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load cookies from a JSON file.
    
    Args:
        filepath: Optional custom filepath, uses config.GROK_COOKIE_FILE_PATH by default
        
    Returns:
        List of cookie dictionaries
    """
    load_path = Path(filepath or config.GROK_COOKIE_FILE_PATH)
    
    if not load_path.exists():
        logger.warning(f"Cookie file not found: {load_path}")
        return []
    
    with open(load_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get("cookies", [])


class ManualOAuthExtractor:
    """
    Handles semi-automated Grok cookie extraction with manual OAuth.
    
    This class launches a visible browser window and waits for the user
    to manually complete the Google OAuth login process.
    """
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self._stop_event = asyncio.Event()
    
    async def initialize(self, headless: bool = False):
        """Initialize Playwright and launch browser with visible UI"""
        self.playwright = await async_playwright().start()
        
        # Launch browser with UI (not headless)
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        # Create browser context with typical user settings
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ignore_https_errors=True
        )
        
        self.page = await self.context.new_page()
    
    async def close(self):
        """Close browser and cleanup resources"""
        self._stop_event.set()
        
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
    
    def _print_user_instructions(self, timeout: int):
        """Print clear instructions for the user"""
        print("\n" + "=" * 60)
        print("✅ 浏览器已打开")
        print("⏳ 请在浏览器中完成以下步骤：")
        print("   1. 点击 'Sign in with Google' 按钮")
        print("   2. 使用 Google 账号登录")
        print("   3. 点击 'Authorize' 或 '同意' 按钮授权")
        print("   4. 等待页面加载完成")
        print(f"\n⏰ 等待超时时间：{timeout} 秒（{timeout // 60} 分钟）")
        print("\n📌 提示：")
        print("   - 登录完成后，Cookie 将自动导出")
        print("   - 可以随时按 Ctrl+C 中止操作")
        print("=" * 60 + "\n")
    
    async def _wait_for_login_completion(self, timeout_seconds: int) -> bool:
        """
        Wait for user to complete login by monitoring URL changes.
        
        Args:
            timeout_seconds: Maximum time to wait
            
        Returns:
            True if login appears complete, False if timeout
        """
        try:
            # Wait for URL to change to a Grok-related page
            # This indicates the user has successfully authenticated
            await asyncio.wait_for(
                self._wait_for_url_change(),
                timeout=timeout_seconds
            )
            return True
        except asyncio.TimeoutError:
            logger.info("Login completion wait timed out")
            return False
    
    async def _wait_for_url_change(self):
        """Wait for URL to change to a logged-in state"""
        initial_url = self.page.url
        
        # Patterns that indicate successful login
        logged_in_patterns = [
            "**/feed**",
            "**/chat**",
            "**/grok.com/**",
        ]
        
        # Poll for URL changes that indicate login
        for _ in range(600):  # Check every second for 10 minutes max
            await asyncio.sleep(1)
            current_url = self.page.url
            
            # Check if we're on a Grok page (not still on auth)
            if "accounts.google.com" not in current_url and \
               "grok.com" in current_url or \
               "x.ai" in current_url:
                logger.info(f"Detected login completion. Current URL: {current_url}")
                return
            
            # Also check if we see the chat interface or main content
            try:
                # Check for common post-login elements
                chat_elements = await self.page.query_selector_all(
                    '[class*="chat"], [class*="conversation"], textarea, input[class*="prompt"]'
                )
                if len(chat_elements) > 0:
                    logger.info("Detected chat interface elements")
                    return
            except Exception:
                pass
    
    async def extract_with_manual_oauth(
        self,
        timeout_seconds: Optional[int] = None,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract cookies from Grok with manual OAuth flow.
        
        This launches a visible browser window and waits for the user
        to manually complete the Google OAuth login process.
        
        Args:
            timeout_seconds: Maximum time to wait for login (default: 600s)
            callback_url: Optional URL to notify on completion
            
        Returns:
            Dict containing status, cookies, and metadata
        """
        timeout = timeout_seconds or config.GROK_OAUTH_TIMEOUT
        start_time = datetime.now(timezone.utc)
        
        logger.info(f"Starting manual OAuth cookie extraction with {timeout}s timeout")
        
        try:
            # Initialize browser with visible UI
            await self.initialize(headless=False)
            
            # Print user instructions
            self._print_user_instructions(timeout)
            
            # Open Grok
            await self.page.goto(config.GROK_URL, timeout=30000)
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            
            # Start monitoring for login completion in background
            login_monitor_task = asyncio.create_task(
                self._wait_for_login_completion(timeout)
            )
            
            # Wait for login completion or timeout
            login_success = await login_monitor_task
            
            # If login didn't complete via URL detection, still try to extract cookies
            # The user might have completed login but URL detection missed it
            
            # Export cookies
            cookies = await self.context.cookies()
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            if cookies:
                # Save cookies to file
                save_path = save_cookies_to_file(cookies)
                
                result = {
                    "status": "success",
                    "message": "Cookies extracted successfully",
                    "cookies": cookies,
                    "cookie_count": len(cookies),
                    "extracted_at": end_time.isoformat(),
                    "duration_seconds": round(duration, 2),
                    "saved_to": save_path,
                    "login_detected": login_success
                }
                
                logger.info(
                    f"Successfully extracted {len(cookies)} cookies in {duration:.2f}s"
                )
                
                return result
            else:
                result = {
                    "status": "error",
                    "error_type": "no_cookies",
                    "error_message": "No cookies found after extraction",
                    "cookies": [],
                    "cookie_count": 0
                }
                
                logger.warning("No cookies found after extraction")
                return result
                
        except asyncio.TimeoutError:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(f"Manual OAuth extraction timed out after {duration:.2f}s")
            return {
                "status": "error",
                "error_type": "timeout",
                "error_message": f"Login timed out after {timeout} seconds",
                "cookies": [],
                "cookie_count": 0
            }
        except KeyboardInterrupt:
            logger.info("Manual OAuth extraction interrupted by user")
            return {
                "status": "cancelled",
                "error_type": "user_interrupted",
                "error_message": "Operation cancelled by user",
                "cookies": [],
                "cookie_count": 0
            }
        except Exception as e:
            logger.error(f"Manual OAuth extraction failed: {str(e)}")
            return {
                "status": "error",
                "error_type": "extraction_failed",
                "error_message": str(e),
                "cookies": [],
                "cookie_count": 0
            }
        finally:
            await self.close()


async def extract_grok_cookies_with_manual_oauth(
    timeout_seconds: Optional[int] = None,
    callback_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to extract cookies from Grok with manual OAuth.
    
    This function launches a visible browser window and waits for the user
    to manually complete the Google OAuth login process.
    
    Args:
        timeout_seconds: Maximum time to wait for login (default: 600s)
        callback_url: Optional URL to notify on completion
        
    Returns:
        Dict containing status, cookies, and metadata
        
    Example:
        >>> import asyncio
        >>> result = asyncio.run(extract_grok_cookies_with_manual_oauth(timeout=300))
        >>> if result["status"] == "success":
        ...     print(f"Extracted {result['cookie_count']} cookies")
        ...     print(f"Saved to: {result['saved_to']}")
    """
    extractor = ManualOAuthExtractor()
    return await extractor.extract_with_manual_oauth(timeout_seconds, callback_url)


# ==================== Task Management ====================

class ExtractionTask:
    """
    Manages async extraction tasks for API endpoints.
    """
    
    _tasks: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def create_task(cls, timeout: int = 600) -> str:
        """Create a new extraction task and return task_id"""
        import uuid
        task_id = str(uuid.uuid4())
        cls._tasks[task_id] = {
            "status": "waiting_for_login",
            "timeout": timeout,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "result": None
        }
        return task_id
    
    @classmethod
    def update_task(cls, task_id: str, status: str, result: Optional[Dict] = None):
        """Update task status"""
        if task_id in cls._tasks:
            cls._tasks[task_id]["status"] = status
            cls._tasks[task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            if result:
                cls._tasks[task_id]["result"] = result
    
    @classmethod
    def get_task(cls, task_id: str) -> Optional[Dict]:
        """Get task info"""
        return cls._tasks.get(task_id)
    
    @classmethod
    def delete_task(cls, task_id: str):
        """Delete a completed task"""
        if task_id in cls._tasks:
            del cls._tasks[task_id]
