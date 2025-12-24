from pydantic import BaseModel
from typing import Optional
from enum import Enum

class FileType(str, Enum):
    image = "image"
    video = "video"
    other = "other"

class GenerationResponse(BaseModel):
    success: bool
    file_path: Optional[str] = None
    file_type: Optional[FileType] = None
    error_message: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "file_path": "/output/abc123.png",
                "file_type": "image"
            }
        }

class SessionStatusResponse(BaseModel):
    logged_in: bool
    session_valid: bool
    session_expiry: Optional[str] = None
    browser_type: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "logged_in": True,
                "session_valid": True,
                "session_expiry": "2023-12-31T23:59:59Z",
                "browser_type": "chromium"
            }
        }