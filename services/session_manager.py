import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import config
import asyncio
import uuid

class SessionManager:
    def __init__(self):
        self.session_file = Path(config.SESSION_DIR) / "grok_session.json"
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
    async def __aenter__(self):
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def initialize(self):
        """Initialize Playwright and browser"""
        if self.playwright is None:
            self.playwright = await async_playwright().start()

        if config.HEADLESS:
            if self.browser is None:
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    timeout=config.BROWSER_TIMEOUT,
                )
        else:
            if self.context is None:
                user_data_dir = Path(config.SESSION_DIR) / "session_manager_profile"
                user_data_dir.mkdir(parents=True, exist_ok=True)

                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,
                    timeout=config.BROWSER_TIMEOUT,
                    viewport={"width": 1280, "height": 800},
                    ignore_https_errors=True,
                )
                self.browser = None
        
    async def close(self):
        """Close browser and cleanup"""
        if self.page:
            await self.page.close()
            self.page = None
            
        if self.context:
            await self.context.close()
            self.context = None
            
        if self.browser:
            await self.browser.close()
            self.browser = None
            
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
            
    async def login(self, username: str, password: str, remember_me: bool = True) -> bool:
        """
        Perform manual login to Grok AI
        """
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
            
            # Navigate to login page
            await self.page.goto(config.GROK_URL, timeout=config.LOGIN_TIMEOUT * 1000)
            
            # Wait for login elements - this will need to be customized based on actual Grok login page
            await self.page.wait_for_selector("input[name='username']", timeout=10000)
            await self.page.wait_for_selector("input[name='password']", timeout=10000)
            await self.page.wait_for_selector("button[type='submit']", timeout=10000)
            
            # Fill login form
            await self.page.fill("input[name='username']", username)
            await self.page.fill("input[name='password']", password)
            
            if remember_me:
                remember_checkbox = await self.page.query_selector("input[name='remember']")
                if remember_checkbox:
                    await remember_checkbox.check()
            
            # Submit login form
            await self.page.click("button[type='submit']")
            
            # Wait for navigation to complete
            await self.page.wait_for_load_state("networkidle", timeout=config.LOGIN_TIMEOUT * 1000)
            
            # Check if login was successful by looking for logged-in indicators
            # This will need to be customized based on actual Grok UI
            logged_in = await self._check_login_success()
            
            if logged_in:
                # Save session information
                session_data = {
                    "logged_in": True,
                    "timestamp": datetime.now().isoformat(),
                    "expiry": (datetime.now() + timedelta(days=30)).isoformat(),
                    "browser_type": config.BROWSER_TYPE
                }
                
                with open(self.session_file, "w") as f:
                    json.dump(session_data, f)
                
                return True
            else:
                return False
                
        except Exception as e:
            logging.error(f"Login failed: {str(e)}")
            await self.close()
            return False
            
    async def _check_login_success(self) -> bool:
        """
        Check if login was successful by looking for UI elements that indicate logged-in state
        """
        try:
            current_url = self.page.url
            logging.info(f"Checking login success at URL: {current_url}")
            
            # Give the page a moment to fully load after cookie injection
            await asyncio.sleep(1)
            
            # Check if we're on a login/auth page (indicates not logged in)
            if any(keyword in current_url.lower() for keyword in ["login", "signin", "sign-in", "auth/", "oauth/"]):
                logging.info("Still on login/auth page - not logged in")
                return False
            
            # If we're on the main Grok domain, that's a strong indicator
            if "grok.com" in current_url or "grok.x.ai" in current_url:
                # Check for common Grok logged-in indicators
                # Try multiple selectors that might indicate a logged-in state
                login_indicators = [
                    # Chat interface elements (Grok-specific)
                    'textarea',
                    'input[type="text"]',
                    'div[role="textbox"]',
                    'textarea[placeholder*="Ask"]',
                    'textarea[placeholder*="Message"]',
                    'textarea[placeholder*="Type"]',
                    'div[class*="chat"]',
                    'div[class*="conversation"]',
                    'button[aria-label*="Send"]',
                    # User profile/menu elements
                    'button[aria-label*="Profile"]',
                    'button[aria-label*="User"]',
                    'button[aria-label*="Menu"]',
                    '[data-testid*="profile"]',
                    '[data-testid*="user"]',
                    '[data-testid*="menu"]',
                    # Navigation elements that appear when logged in
                    'nav',
                    'aside',
                    '[class*="sidebar"]',
                    '[class*="navigation"]',
                    # Avatar or user icon
                    'img[alt*="avatar"]',
                    'img[alt*="profile"]',
                    '[class*="avatar"]',
                ]
                
                for selector in login_indicators:
                    try:
                        element = await self.page.wait_for_selector(selector, timeout=3000, state="attached")
                        if element:
                            logging.info(f"✅ Found logged-in indicator: {selector}")
                            return True
                    except Exception:
                        continue
            
            # Check for "Sign in" or "Login" buttons (indicates not logged in)
            try:
                login_button_selectors = [
                    'button:has-text("Sign in")',
                    'button:has-text("Log in")',
                    'a:has-text("Sign in")',
                    'a:has-text("Log in")',
                    'button:has-text("Login")',
                ]
                for selector in login_button_selectors:
                    try:
                        button = await self.page.wait_for_selector(selector, timeout=1000)
                        if button:
                            text = await button.inner_text()
                            logging.info(f"❌ Found login button: {text} - not logged in")
                            return False
                    except Exception:
                        continue
            except Exception:
                pass
            
            # If URL suggests we're in the app and no login buttons found, consider logged in
            if any(keyword in current_url.lower() for keyword in ["chat", "conversation", "app", "dashboard", "home", "grok.com"]):
                logging.info(f"✅ URL suggests logged in state: {current_url}")
                
                # Additional check: verify we have important cookies
                cookies = await self.context.cookies()
                if len(cookies) > 0:
                    logging.info(f"✅ Found {len(cookies)} cookies in context")
                    return True
            
            # Check cookies for session indicators
            cookies = await self.context.cookies()
            logging.info(f"🍪 Total cookies in context: {len(cookies)}")
            
            # Log cookie names for debugging
            cookie_names = [c.get("name", "") for c in cookies]
            logging.info(f"🍪 Cookie names: {', '.join(cookie_names[:10])}")
            
            session_cookies = [c for c in cookies if any(
                keyword in c.get("name", "").lower() 
                for keyword in ["session", "auth", "token", "sid", "_ga", "ct0", "kdt"]
            )]
            
            if session_cookies:
                logging.info(f"✅ Found {len(session_cookies)} session-related cookies")
                return True
            
            # If we have a significant number of cookies and we're on grok.com, assume logged in
            if len(cookies) >= 3 and "grok.com" in current_url:
                logging.info(f"✅ Have {len(cookies)} cookies and on grok.com - assuming logged in")
                return True
            
            logging.warning("⚠️ No definitive login indicators found")
            return False
            
        except Exception as e:
            logging.error(f"❌ Error checking login success: {str(e)}")
            return False
            
    def has_valid_session(self) -> bool:
        """
        Check if we have a valid session
        """
        if not self.session_file.exists():
            return False
            
        try:
            with open(self.session_file, "r") as f:
                session_data = json.load(f)
                
            if not session_data.get("logged_in", False):
                return False
                
            expiry_str = session_data.get("expiry")
            if expiry_str:
                expiry = datetime.fromisoformat(expiry_str)
                if datetime.now() > expiry:
                    return False
                    
            return True
            
        except Exception:
            return False
            
    def get_session_status(self) -> Dict[str, Any]:
        """
        Get current session status
        """
        status = {
            "logged_in": False,
            "session_valid": False,
            "session_expiry": None,
            "browser_type": config.BROWSER_TYPE
        }
        
        if self.session_file.exists():
            try:
                with open(self.session_file, "r") as f:
                    session_data = json.load(f)
                    
                status.update({
                    "logged_in": session_data.get("logged_in", False),
                    "session_valid": self.has_valid_session(),
                    "session_expiry": session_data.get("expiry")
                })
                
            except Exception as e:
                logging.error(f"Failed to read session file: {str(e)}")
        
        return status
        
    def logout(self):
        """
        Clear current session
        """
        try:
            if self.session_file.exists():
                os.remove(self.session_file)
                
            # Clear user data directory
            user_data_dir = Path(config.SESSION_DIR) / "user_data"
            if user_data_dir.exists():
                import shutil
                shutil.rmtree(user_data_dir)
                
        except Exception as e:
            logging.error(f"Logout failed: {str(e)}")
            
    async def get_page(self) -> Page:
        """
        Get a page with valid session
        """
        if not self.has_valid_session():
            raise Exception("No valid session available")
            
        if self.page is None:
            await self.initialize()
            
            user_data_dir = Path(config.SESSION_DIR) / "user_data"
            if not user_data_dir.exists():
                raise Exception("No user data directory found")
                
            self.context = await self.browser.new_context(
                user_data_dir=str(user_data_dir),
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True
            )
            
            self.page = await self.context.new_page()
            
            # Navigate to home page to ensure session is valid
            await self.page.goto(config.GROK_URL, timeout=config.BROWSER_TIMEOUT)
            await self.page.wait_for_load_state("networkidle")
            
        return self.page
    
    async def oauth_login(self, provider: str, auth_code: str, redirect_uri: Optional[str] = None, remember_me: bool = True) -> Tuple[bool, str]:
        """
        Perform OAuth authorization login
        """
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
            
            # Navigate to OAuth callback URL or provider-specific login page
            oauth_url = self._get_oauth_url(provider, auth_code, redirect_uri)
            await self.page.goto(oauth_url, timeout=config.LOGIN_TIMEOUT * 1000)
            
            # Wait for OAuth completion - this depends on the specific website's OAuth flow
            await self.page.wait_for_load_state("networkidle", timeout=config.LOGIN_TIMEOUT * 1000)
            
            # Check if OAuth login was successful
            logged_in = await self._check_login_success()
            
            if logged_in:
                # Generate a session ID
                session_id = str(uuid.uuid4())
                
                # Save session information
                session_data = {
                    "logged_in": True,
                    "timestamp": datetime.now().isoformat(),
                    "expiry": (datetime.now() + timedelta(days=30)).isoformat(),
                    "browser_type": config.BROWSER_TYPE,
                    "login_method": "oauth",
                    "oauth_provider": provider,
                    "session_id": session_id
                }
                
                with open(self.session_file, "w") as f:
                    json.dump(session_data, f)
                
                return True, session_id
            else:
                return False, ""
                
        except Exception as e:
            logging.error(f"OAuth login failed: {str(e)}")
            await self.close()
            return False, ""
    
    def _get_oauth_url(self, provider: str, auth_code: str, redirect_uri: Optional[str] = None) -> str:
        """
        Get the appropriate OAuth URL based on provider
        """
        # This is a placeholder - actual implementation depends on the target website's OAuth flow
        # Different websites have different OAuth callback URLs and flows
        
        if provider.lower() == "google":
            return f"{config.GROK_URL}/auth/google/callback?code={auth_code}&redirect_uri={redirect_uri or ''}"
        elif provider.lower() == "github":
            return f"{config.GROK_URL}/auth/github/callback?code={auth_code}&redirect_uri={redirect_uri or ''}"
        elif provider.lower() == "twitter" or provider.lower() == "x":
            return f"{config.GROK_URL}/auth/twitter/callback?code={auth_code}&redirect_uri={redirect_uri or ''}"
        else:
            # Default fallback - may need to be customized
            return f"{config.GROK_URL}/auth/{provider}/callback?code={auth_code}&redirect_uri={redirect_uri or ''}"
    
    async def inject_cookies(self, cookies: List[Dict[str, Any]], user_agent: Optional[str] = None, remember_me: bool = True) -> Tuple[bool, int]:
        """
        Manually inject cookies to establish a session
        """
        try:
            await self.initialize()
            
            if self.context is None and self.browser is not None:
                context_kwargs = {
                    "viewport": {"width": 1280, "height": 800},
                    "ignore_https_errors": True,
                }
                if user_agent:
                    context_kwargs["user_agent"] = user_agent

                self.context = await self.browser.new_context(**context_kwargs)

            if self.context is None:
                raise Exception("Browser context not initialized")
            
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()
            
            # IMPORTANT: Visit relevant domains BEFORE injecting cookies.
            # Some browsers/cookie stores can behave unexpectedly if a domain has never been visited.
            cookie_domains = {
                str(c.get("domain", "")).lstrip(".")
                for c in cookies
                if c.get("domain")
            }

            bootstrap_urls: List[str] = []
            if any("grok.com" in d for d in cookie_domains):
                bootstrap_urls.append("https://grok.com")
            if any("x.ai" in d for d in cookie_domains):
                bootstrap_urls.append(config.X_AI_URL)
            if any("grok.ai" in d for d in cookie_domains):
                bootstrap_urls.append("https://grok.ai")

            if not bootstrap_urls:
                bootstrap_urls.append(config.GROK_URL)

            logging.info(f"Bootstrap domains before cookie injection: {bootstrap_urls}")
            for url in bootstrap_urls:
                logging.info(f"Navigating to {url} before cookie injection...")
                await self.page.goto(url, timeout=config.BROWSER_TIMEOUT)
                await self.page.wait_for_load_state("domcontentloaded")
            
            # Filter out expired cookies and prepare cookies for injection
            current_timestamp = datetime.now().timestamp()
            valid_cookies = []
            
            for cookie in cookies:
                # Normalize/validate expires
                expires = cookie.get("expires")
                if isinstance(expires, (int, float)):
                    # Some exports store expiry in milliseconds
                    if expires > 10_000_000_000:
                        expires = expires / 1000
                else:
                    expires = None

                # Check if cookie is expired
                if expires and expires > 0 and expires < current_timestamp:
                    logging.debug(f"Skipping expired cookie: {cookie.get('name', '')}")
                    continue

                # Normalize domain
                domain_raw = str(cookie.get("domain", "")).strip()
                if not domain_raw:
                    logging.debug(f"Skipping cookie without domain: {cookie.get('name', '')}")
                    continue

                had_leading_dot = domain_raw.startswith(".")
                domain = domain_raw.lstrip(".")
                if had_leading_dot:
                    domain = "." + domain

                cookie_data: Dict[str, Any] = {
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": domain,
                    "path": cookie.get("path", "/"),
                    "httpOnly": cookie.get("httpOnly", False),
                    "secure": cookie.get("secure", False),
                }

                # Add expires only if it's valid
                if expires and expires > 0:
                    cookie_data["expires"] = float(expires)

                # Add sameSite if present (normalize common formats)
                same_site = cookie.get("sameSite")
                if same_site:
                    same_site_str = str(same_site)
                    same_site_norm = {
                        "lax": "Lax",
                        "strict": "Strict",
                        "none": "None",
                        "no_restriction": "None",
                    }.get(same_site_str.lower())
                    if same_site_norm:
                        cookie_data["sameSite"] = same_site_norm

                valid_cookies.append(cookie_data)
            
            logging.info(f"Injecting {len(valid_cookies)} valid cookies (filtered from {len(cookies)} total)")
            
            # Add cookies to the browser context using enhanced injector
            from services.enhanced_cookie_injector import EnhancedCookieInjector
            
            injection_report = await EnhancedCookieInjector.inject_cookies_with_report(
                self.context, valid_cookies, self.page
            )
            
            cookie_count = injection_report["cookies_injected"]
            
            # Log the detailed report
            logging.info(f"Enhanced injection completed. Report:")
            logging.info(f"  - Processed: {injection_report['cookies_processed']}")
            logging.info(f"  - Valid: {injection_report['cookies_valid']}")
            logging.info(f"  - Injected: {injection_report['cookies_injected']}")
            logging.info(f"  - Failed: {injection_report['cookies_failed']}")
            
            if injection_report.get("recommendations"):
                logging.info("Recommendations:")
                for rec in injection_report["recommendations"]:
                    logging.info(f"  - {rec}")
            
            if not injection_report["success"]:
                logging.error("Enhanced cookie injection reported issues. See details above.")
            
            # Navigate to a suitable URL to apply the cookies (prefer Grok UI)
            validation_url = config.GROK_URL
            if not any("grok.com" in d for d in cookie_domains):
                if any("grok.ai" in d for d in cookie_domains):
                    validation_url = "https://grok.ai"
                elif any("x.ai" in d for d in cookie_domains):
                    validation_url = config.X_AI_URL

            logging.info(f"🔄 Navigating to {validation_url} to apply injected cookies...")
            await self.page.goto(validation_url, wait_until="networkidle", timeout=30000)
            
            # Wait for page to fully render and JavaScript to execute
            logging.info("⏳ Waiting for page to fully render...")
            await asyncio.sleep(3)
            
            # Log current URL and page title for debugging
            current_url = self.page.url
            page_title = await self.page.title()
            logging.info(f"📍 Current URL: {current_url}")
            logging.info(f"📄 Page title: {page_title}")
            
            # Check cookies in context
            context_cookies = await self.context.cookies()
            logging.info(f"🍪 Cookies in context after injection: {len(context_cookies)}")
            
            # Check if the session is valid
            logging.info("🔍 Validating login state...")
            logged_in = await self._check_login_success()
            
            if logged_in and cookie_count > 0:
                logging.info(f"✅ Cookie injection successful! {cookie_count} cookies injected, session is valid")
                
                # Save session information
                session_data = {
                    "logged_in": True,
                    "timestamp": datetime.now().isoformat(),
                    "expiry": (datetime.now() + timedelta(days=30)).isoformat(),
                    "browser_type": config.BROWSER_TYPE,
                    "login_method": "cookie_injection",
                    "cookie_count": cookie_count,
                    "user_agent": user_agent
                }
                
                with open(self.session_file, "w") as f:
                    json.dump(session_data, f)
                
                return True, cookie_count
            else:
                logging.error(f"❌ Cookie injection validation failed. Logged in: {logged_in}, Injected cookies: {cookie_count}")
                logging.error(f"   URL: {current_url}")
                logging.error(f"   Title: {page_title}")
                logging.error(f"   Context cookies: {len(context_cookies)}")
                return False, cookie_count
                
        except Exception as e:
            logging.error(f"Cookie injection failed: {str(e)}")
            await self.close()
            return False, 0