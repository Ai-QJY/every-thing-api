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

        if config.GROK_HEADLESS_MODE:
            if self.browser is None:
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    timeout=config.BROWSER_TIMEOUT,
                )
        else:
            if self.context is None:
                profile_dir = Path(config.SESSION_DIR) / "grok_cookie_extractor_profile"
                profile_dir.mkdir(parents=True, exist_ok=True)

                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=str(profile_dir),
                    headless=False,
                    timeout=config.BROWSER_TIMEOUT,
                    viewport={"width": 1280, "height": 800},
                    ignore_https_errors=True,
                )
                self.browser = None
    
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
            
            if self.context is None and self.browser is not None:
                self.context = await self.browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    ignore_https_errors=True
                )

            if self.context is None:
                raise Exception("Browser context not initialized")

            if self.context.pages:
                self.page = self.context.pages[0]
            else:
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
        """Initialize Playwright and launch browser with visible UI.

        By default we use a persistent browser profile for the manual OAuth flow.
        This avoids Playwright's default "fresh" context which many users interpret
        as an incognito/guest mode window, and it also allows Google login to
        persist between runs.
        """
        self.playwright = await async_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-infobars",
            "--no-first-run",
            "--no-default-browser-check",
        ]

        context_options = {
            "viewport": {"width": 1280, "height": 800},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "ignore_https_errors": True,
        }

        if config.GROK_OAUTH_PERSISTENT_CONTEXT:
            profile_dir = Path(config.GROK_OAUTH_USER_DATA_DIR)
            profile_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"使用持久化浏览器配置文件: {profile_dir}")
            logger.info("这将保存您的登录状态，避免每次都需要重新登录")

            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=headless,
                args=launch_args,
                **context_options,
            )
            self.browser = None
        else:
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=launch_args,
            )
            self.context = await self.browser.new_context(**context_options)

        # Set up event handlers for popup windows
        async def handle_popup(popup_page):
            """Handle new popup windows (e.g., Google OAuth popup)"""
            popup_url = popup_page.url
            logger.info(f"📭 New popup window detected: {popup_url[:80]}...")
            
            # Track the popup
            if "google" in popup_url.lower() or "accounts.google" in popup_url.lower():
                logger.info("🔐 Google OAuth popup detected - please complete login in the popup")
            
            # Log when popup closes
            async def on_close():
                try:
                    logger.debug("Popup window closed")
                except Exception:
                    pass
            
            popup_page.on("close", on_close)
        
        self.context.on("page", handle_popup)

        if self.context.pages:
            self.page = self.context.pages[0]
        else:
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
        print("✅ 浏览器已打开（正常模式，非无痕模式）")
        print("⏳ 请在浏览器中完成以下步骤：")
        print("   1. 点击 'Sign in with Google' 按钮")
        print("   2. 使用 Google 账号登录")
        print("   3. 点击 'Authorize' 或 '同意' 按钮授权")
        print("   4. 等待页面加载完成")
        print(f"\n⏰ 等待超时时间：{timeout} 秒（{timeout // 60} 分钟）")
        print("\n📌 提示：")
        print("   - 浏览器使用持久化配置文件，登录信息会被保存")
        print("   - 登录完成后，Cookie 将自动导出")
        print("   - 提取完成前请不要关闭浏览器窗口（关闭会导致提取失败）")
        print("   - 可以随时按 Ctrl+C 中止操作")
        print("=" * 60 + "\n")
    
    async def _wait_for_login_completion(self, timeout_seconds: int) -> bool:
        """Wait for user to complete login by monitoring URL changes and new windows."""
        try:
            await asyncio.wait_for(self._wait_for_url_change_with_popups(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.info("Login completion wait timed out")
            return False
        except Exception as e:
            logger.info(f"Login completion monitor stopped: {e}")
            return False

        if self._stop_event.is_set() or not self.page or self.page.is_closed():
            return False

        return True

    async def _wait_for_url_change_with_popups(self):
        """
        Wait for URL to change to a logged-in state.
        
        Handles both:
        1. Redirect flow: grok.com → accounts.google.com → grok.com
        2. Popup flow: Main window stays, popup handles Google login
        """
        login_check_interval = 1  # Check every second
        max_checks = 600  # 10 minutes max
        
        checked_urls = set()  # Track URLs we've already processed
        all_pages_checked = set()  # Track all pages we've checked
        
        for check_count in range(max_checks):
            if self._stop_event.is_set():
                return

            if not self.context:
                return

            try:
                # Get ALL pages in the context (handles popup windows)
                all_pages = self.context.pages
                
                # Filter out empty/invalid pages
                valid_pages = []
                for p in all_pages:
                    if p and not p.is_closed():
                        try:
                            _ = p.url
                            valid_pages.append(p)
                        except Exception:
                            continue
                
                # Check all pages for login completion
                login_completed = False
                grok_page_found = False
                
                for page in valid_pages:
                    try:
                        current_url = page.url
                        all_pages_checked.add(current_url)
                        
                        # Check if this page is on grok.com or x.ai (logged in state)
                        if "grok.com" in current_url or "x.ai" in current_url:
                            grok_page_found = True
                            
                            # Check for chat interface or logged-in elements
                            chat_elements = await page.query_selector_all(
                                'textarea, [class*="chat"], [class*="conversation"], '
                                '[class*="prompt"], [class*="input"], [role="textbox"]'
                            )
                            
                            # Also check that we're NOT on a login page
                            is_login_page = any(keyword in current_url.lower() 
                                               for keyword in ["login", "signin", "auth/", "oauth/"])
                            
                            if chat_elements and not is_login_page:
                                logger.info(f"✅ Detected logged-in state on: {current_url}")
                                logger.info(f"   Found {len(chat_elements)} chat interface elements")
                                login_completed = True
                                break
                            
                            # If URL suggests we're on the main app, consider it logged in
                            if not is_login_page and len(chat_elements) > 0:
                                logger.info(f"✅ Detected app interface on: {current_url}")
                                login_completed = True
                                break
                        
                        # Check if still on Google auth page
                        if "accounts.google.com" in current_url:
                            # Still on Google, continue waiting
                            if current_url not in checked_urls:
                                logger.debug(f"Still on Google auth page: {current_url[:80]}...")
                                checked_urls.add(current_url)
                    
                    except Exception:
                        continue
                
                if login_completed:
                    return
                
                # If we found a Grok page but no chat elements, still wait (might still be loading)
                if grok_page_found:
                    logger.debug("Found Grok page, waiting for chat interface to load...")
                
                # Log progress periodically
                if check_count > 0 and check_count % 30 == 0:
                    elapsed = check_count * login_check_interval
                    logger.info(f"⏳ Still waiting for login... ({elapsed}s elapsed)")
                    # List all pages for debugging
                    page_urls = [p.url for p in valid_pages if p and hasattr(p, 'url')]
                    if page_urls:
                        logger.debug(f"   Open pages: {page_urls[:5]}")
                
                await asyncio.sleep(login_check_interval)
                
            except Exception as e:
                if "closed" in str(e).lower():
                    logger.debug("Browser context was closed")
                    return
                logger.warning(f"Error checking login status: {e}")
                await asyncio.sleep(login_check_interval)
    
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
            try:
                await self.page.goto(config.GROK_URL, timeout=30000)
                await self.page.wait_for_load_state("networkidle", timeout=15000)
            except Exception as e:
                message = str(e)
                if "has been closed" in message.lower():
                    return {
                        "status": "cancelled",
                        "error_type": "browser_closed",
                        "error_message": "Browser window was closed before navigation completed",
                        "cookies": [],
                        "cookie_count": 0,
                    }
                raise
            
            # Start monitoring for login completion in background
            login_monitor_task = asyncio.create_task(self._wait_for_login_completion(timeout))

            # Wait for login completion or timeout
            try:
                login_success = await login_monitor_task
            except Exception as e:
                logger.warning(f"Login monitor task failed: {e}")
                login_success = False

            # If login didn't complete via URL detection, still try to extract cookies
            # The user might have completed login but URL detection missed it

            # Export cookies
            try:
                cookies = await self.context.cookies()
            except Exception as e:
                message = str(e)
                if "has been closed" in message.lower():
                    return {
                        "status": "cancelled",
                        "error_type": "browser_closed",
                        "error_message": "Browser window was closed before cookies could be extracted",
                        "cookies": [],
                        "cookie_count": 0,
                    }
                raise
            
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
