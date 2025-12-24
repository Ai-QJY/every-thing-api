from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel
from services.grok_service import GrokService
from services.session_manager import SessionManager
from models.response_models import GenerationResponse
import logging

router = APIRouter()

class ImageGenerationRequest(BaseModel):
    prompt: str
    timeout: Optional[int] = 300

class VideoGenerationRequest(BaseModel):
    prompt: str
    timeout: Optional[int] = 600

@router.post("/image", response_model=GenerationResponse)
async def generate_image(
    request: ImageGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate an image using Grok AI through browser automation
    """
    try:
        session_manager = SessionManager()
        grok_service = GrokService(session_manager)
        
        # Check if we have a valid session
        if not session_manager.has_valid_session():
            raise HTTPException(
                status_code=401,
                detail="No valid session. Please login first."
            )
        
        # Generate image in background
        result = await grok_service.generate_image(
            request.prompt,
            request.timeout
        )
        
        return result
        
    except Exception as e:
        logging.error(f"Image generation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Image generation failed: {str(e)}"
        )

@router.post("/video", response_model=GenerationResponse)
async def generate_video(
    request: VideoGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate a video using Grok AI through browser automation (future implementation)
    """
    try:
        session_manager = SessionManager()
        grok_service = GrokService(session_manager)
        
        # Check if we have a valid session
        if not session_manager.has_valid_session():
            raise HTTPException(
                status_code=401,
                detail="No valid session. Please login first."
            )
        
        # Generate video in background
        result = await grok_service.generate_video(
            request.prompt,
            request.timeout
        )
        
        return result
        
    except Exception as e:
        logging.error(f"Video generation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Video generation failed: {str(e)}"
        )