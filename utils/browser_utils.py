import asyncio
import logging
from typing import Optional, List, Dict
from playwright.async_api import Page, Locator

class BrowserUtils:
    """
    Utility functions for browser automation
    """
    
    @staticmethod
    async def wait_for_element(
        page: Page,
        selectors: List[str],
        timeout: int = 10000,
        visible: bool = True
    ) -> Optional[Locator]:
        """
        Wait for any of the specified elements to appear
        """
        for selector in selectors:
            try:
                element = await page.wait_for_selector(
                    selector,
                    timeout=timeout,
                    state="visible" if visible else "attached"
                )
                if element:
                    return element
            except Exception:
                continue
        return None
        
    @staticmethod
    async def wait_for_navigation(
        page: Page,
        timeout: int = 30000,
        url_pattern: Optional[str] = None
    ) -> bool:
        """
        Wait for page navigation to complete
        """
        try:
            if url_pattern:
                await page.wait_for_url(url_pattern, timeout=timeout)
            else:
                await page.wait_for_load_state("networkidle", timeout=timeout)
            return True
        except Exception as e:
            logging.warning(f"Navigation wait timed out: {str(e)}")
            return False
            
    @staticmethod
    async def human_like_typing(
        element: Locator,
        text: str,
        delay: float = 0.1
    ):
        """
        Type text in a human-like manner to avoid detection
        """
        for char in text:
            await element.type(char)
            await asyncio.sleep(delay)
            
    @staticmethod
    async def human_like_click(
        element: Locator,
        delay: float = 0.5
    ):
        """
        Click element with human-like delay
        """
        await asyncio.sleep(delay)
        await element.click()
        
    @staticmethod
    async def scroll_page(
        page: Page,
        scrolls: int = 3,
        delay: float = 1.0
    ):
        """
        Scroll page to simulate human behavior
        """
        for _ in range(scrolls):
            await page.mouse.wheel(0, 500)
            await asyncio.sleep(delay)
            
    @staticmethod
    async def get_element_screenshot(
        element: Locator,
        file_path: str
    ) -> bool:
        """
        Take screenshot of an element
        """
        try:
            await element.screenshot(path=file_path)
            return True
        except Exception as e:
            logging.error(f"Failed to take element screenshot: {str(e)}")
            return False