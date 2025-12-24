import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import config
import asyncio

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