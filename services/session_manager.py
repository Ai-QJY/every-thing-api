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
            self.browser = await self.playwright.chromium.launch(
                headless=config.HEADLESS,
                timeout=config.BROWSER_TIMEOUT
            )
        
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
            
            # Create new context with persistent storage
            user_data_dir = Path(config.SESSION_DIR) / "user_data"
            user_data_dir.mkdir(parents=True, exist_ok=True)
            
            self.context = await self.browser.new_context(
                user_data_dir=str(user_data_dir),
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True
            )
            
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
            # Check for user profile element or other logged-in indicators
            # This is a placeholder - actual implementation depends on Grok's UI
            profile_element = await self.page.query_selector(".user-profile", timeout=5000)
            
            if profile_element:
                return True
            
            # Check if we're still on login page
            login_form = await self.page.query_selector("form[action*='login']", timeout=5000)
            if login_form:
                return False
                
            # Default to checking URL
            current_url = self.page.url
            return "dashboard" in current_url or "home" in current_url
            
        except Exception:
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
            
            # Create new context with persistent storage
            user_data_dir = Path(config.SESSION_DIR) / "user_data"
            user_data_dir.mkdir(parents=True, exist_ok=True)
            
            self.context = await self.browser.new_context(
                user_data_dir=str(user_data_dir),
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True
            )
            
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
            
            # Create new context with persistent storage
            user_data_dir = Path(config.SESSION_DIR) / "user_data"
            user_data_dir.mkdir(parents=True, exist_ok=True)
            
            self.context = await self.browser.new_context(
                user_data_dir=str(user_data_dir),
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True
            )
            
            # Set user agent if provided
            if user_agent:
                await self.context.set_user_agent(user_agent)
            
            self.page = await self.context.new_page()
            
            # Add cookies to the browser context
            cookie_count = 0
            for cookie in cookies:
                try:
                    await self.context.add_cookies([{
                        "name": cookie["name"],
                        "value": cookie["value"],
                        "domain": cookie["domain"],
                        "path": cookie.get("path", "/"),
                        "expires": cookie.get("expires"),
                        "httpOnly": cookie.get("httpOnly", False),
                        "secure": cookie.get("secure", False),
                        "sameSite": cookie.get("sameSite")
                    }])
                    cookie_count += 1
                except Exception as e:
                    logging.warning(f"Failed to add cookie {cookie['name']}: {str(e)}")
            
            # Navigate to the target website to test the session
            await self.page.goto(config.GROK_URL, timeout=config.BROWSER_TIMEOUT)
            await self.page.wait_for_load_state("networkidle")
            
            # Check if the session is valid
            logged_in = await self._check_login_success()
            
            if logged_in and cookie_count > 0:
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
                return False, 0
                
        except Exception as e:
            logging.error(f"Cookie injection failed: {str(e)}")
            await self.close()
            return False, 0