import logging
from fastapi import HTTPException
from typing import Optional

class AIServiceError(Exception):
    """Base exception for AI service errors"""
    pass

class SessionError(AIServiceError):
    """Session-related errors"""
    pass

class GenerationError(AIServiceError):
    """Generation process errors"""
    pass

class BrowserError(AIServiceError):
    """Browser automation errors"""
    pass

class ErrorHandler:
    """
    Centralized error handling for the API
    """
    
    @staticmethod
    def handle_exception(e: Exception) -> HTTPException:
        """
        Convert internal exceptions to appropriate HTTP responses
        """
        logging.error(f"Exception occurred: {str(e)}", exc_info=True)
        
        if isinstance(e, SessionError):
            return HTTPException(
                status_code=401,
                detail=f"Session error: {str(e)}"
            )
        elif isinstance(e, GenerationError):
            return HTTPException(
                status_code=422,
                detail=f"Generation error: {str(e)}"
            )
        elif isinstance(e, BrowserError):
            return HTTPException(
                status_code=503,
                detail=f"Browser error: {str(e)}"
            )
        elif isinstance(e, HTTPException):
            return e
        else:
            return HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )
    
    @staticmethod
    def log_error(context: str, error: Exception, **kwargs):
        """
        Log error with context
        """
        extra_info = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        logging.error(f"{context}: {str(error)} | {extra_info}", exc_info=True)