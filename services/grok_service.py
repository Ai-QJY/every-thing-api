import os
import logging
import asyncio
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from playwright.async_api import Page, Locator
from config import config
from models.response_models import GenerationResponse, FileType
from services.session_manager import SessionManager

class GrokService:
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        
    async def generate_image(self, prompt: str, timeout: int = 300) -> GenerationResponse:
        """
        Generate an image using Grok AI through browser automation
        """
        try:
            page = await self.session_manager.get_page()
            
            # Navigate to image generation page
            await self._navigate_to_generation_page(page, "image")
            
            # Find and fill the prompt input
            prompt_input = await self._find_prompt_input(page)
            await prompt_input.fill(prompt)
            
            # Find and click generate button
            generate_button = await self._find_generate_button(page)
            await generate_button.click()
            
            # Wait for generation to complete
            generation_complete = await self._wait_for_generation_complete(page, timeout)
            
            if not generation_complete:
                return GenerationResponse(
                    success=False,
                    error_message="Generation timed out"
                )
                
            # Download the generated image
            file_path = await self._download_generated_content(page, "image")
            
            return GenerationResponse(
                success=True,
                file_path=file_path,
                file_type=FileType.image
            )
            
        except Exception as e:
            logging.error(f"Image generation failed: {str(e)}")
            return GenerationResponse(
                success=False,
                error_message=str(e)
            )
            
    async def generate_video(self, prompt: str, timeout: int = 600) -> GenerationResponse:
        """
        Generate a video using Grok AI through browser automation
        """
        try:
            page = await self.session_manager.get_page()
            
            # Navigate to video generation page
            await self._navigate_to_generation_page(page, "video")
            
            # Find and fill the prompt input
            prompt_input = await self._find_prompt_input(page)
            await prompt_input.fill(prompt)
            
            # Find and click generate button
            generate_button = await self._find_generate_button(page)
            await generate_button.click()
            
            # Wait for generation to complete (videos take longer)
            generation_complete = await self._wait_for_generation_complete(page, timeout)
            
            if not generation_complete:
                return GenerationResponse(
                    success=False,
                    error_message="Generation timed out"
                )
                
            # Download the generated video
            file_path = await self._download_generated_content(page, "video")
            
            return GenerationResponse(
                success=True,
                file_path=file_path,
                file_type=FileType.video
            )
            
        except Exception as e:
            logging.error(f"Video generation failed: {str(e)}")
            return GenerationResponse(
                success=False,
                error_message=str(e)
            )
            
    async def _navigate_to_generation_page(self, page: Page, content_type: str):
        """
        Navigate to the appropriate generation page
        """
        if content_type == "image":
            # Navigate to image generation URL
            # This will need to be customized based on actual Grok URLs
            await page.goto(f"{config.GROK_URL}/generate/image", timeout=config.BROWSER_TIMEOUT)
        elif content_type == "video":
            await page.goto(f"{config.GROK_URL}/generate/video", timeout=config.BROWSER_TIMEOUT)
            
        await page.wait_for_load_state("networkidle")
        
    async def _find_prompt_input(self, page: Page) -> Locator:
        """
        Find the prompt input field on the page
        """
        # Try different common selectors for prompt input
        selectors = [
            "textarea[placeholder*='prompt']",
            "textarea[placeholder*='describe']",
            "input[placeholder*='prompt']",
            "#prompt-input",
            ".prompt-textarea",
            "[name='prompt']"
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector, timeout=5000)
                if element:
                    return element
            except Exception:
                continue
                
        raise Exception("Could not find prompt input field")
        
    async def _find_generate_button(self, page: Page) -> Locator:
        """
        Find the generate button on the page
        """
        # Try different common selectors for generate button
        selectors = [
            "button:has-text('Generate')",
            "button:has-text('Create')",
            "button:has-text('Generate Image')",
            "button:has-text('Generate Video')",
            "#generate-btn",
            ".generate-button",
            "[aria-label='Generate']"
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector, timeout=5000)
                if element:
                    return element
            except Exception:
                continue
                
        raise Exception("Could not find generate button")
        
    async def _wait_for_generation_complete(self, page: Page, timeout: int) -> bool:
        """
        Wait for generation to complete by monitoring UI indicators
        """
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < timeout:
            try:
                # Check for completion indicators
                # These selectors will need to be customized based on actual Grok UI
                
                # Check if generate button is re-enabled
                generate_button = await self._find_generate_button(page)
                is_disabled = await generate_button.get_attribute("disabled")
                
                if not is_disabled:
                    # Check for download button or result preview
                    download_button = await page.query_selector("button:has-text('Download')", timeout=2000)
                    result_preview = await page.query_selector(".result-preview img", timeout=2000)
                    
                    if download_button or result_preview:
                        return True
                
                # Check for progress indicators
                progress_bar = await page.query_selector(".progress-bar", timeout=2000)
                if progress_bar:
                    progress_text = await progress_bar.text_content()
                    if "100%" in progress_text or "complete" in progress_text.lower():
                        return True
                
                # Wait a bit before checking again
                await asyncio.sleep(2)
                
            except Exception:
                await asyncio.sleep(2)
                continue
                
        return False
        
    async def _download_generated_content(self, page: Page, content_type: str) -> str:
        """
        Download the generated content from the page
        """
        output_dir = Path(config.OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        
        if content_type == "image":
            filename = f"grok_image_{timestamp}_{unique_id}.png"
            file_path = output_dir / filename
            
            # Find image element and download
            img_element = await page.query_selector(".result-preview img", timeout=10000)
            if not img_element:
                img_element = await page.query_selector("img[alt*='generated']", timeout=10000)
                
            if img_element:
                img_src = await img_element.get_attribute("src")
                if img_src:
                    # Download the image
                    async with page.context.expect_download() as download_info:
                        await img_element.click()
                        
                    download = await download_info.value
                    await download.save_as(str(file_path))
                    return str(file_path)
                
        elif content_type == "video":
            filename = f"grok_video_{timestamp}_{unique_id}.mp4"
            file_path = output_dir / filename
            
            # Find video element and download
            video_element = await page.query_selector("video", timeout=10000)
            if video_element:
                video_src = await video_element.get_attribute("src")
                if video_src:
                    # Download the video
                    async with page.context.expect_download() as download_info:
                        await video_element.click()
                        
                    download = await download_info.value
                    await download.save_as(str(file_path))
                    return str(file_path)
            
            # Alternative: find download button
            download_button = await page.query_selector("button:has-text('Download')", timeout=10000)
            if download_button:
                async with page.context.expect_download() as download_info:
                    await download_button.click()
                    
                download = await download_info.value
                await download.save_as(str(file_path))
                return str(file_path)
                
        raise Exception(f"Could not download {content_type} content")