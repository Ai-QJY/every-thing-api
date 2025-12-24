from abc import ABC, abstractmethod
from typing import Optional
from models.response_models import GenerationResponse

class BaseAIService(ABC):
    """
    Base class for AI website services using the adapter pattern
    """
    
    @abstractmethod
    async def generate_image(self, prompt: str, timeout: int = 300) -> GenerationResponse:
        """
        Generate an image from the given prompt
        """
        pass
        
    @abstractmethod
    async def generate_video(self, prompt: str, timeout: int = 600) -> GenerationResponse:
        """
        Generate a video from the given prompt
        """
        pass
        
    @abstractmethod
    async def initialize_session(self):
        """
        Initialize and validate session
        """
        pass
        
    @abstractmethod
    async def close_session(self):
        """
        Close session and cleanup resources
        """
        pass