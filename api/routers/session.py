from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from services.session_manager import SessionManager
from models.response_models import SessionStatusResponse
import logging

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = True

@router.post("/login")
async def login(request: LoginRequest):
    """
    Initialize manual login process
    """
    try:
        session_manager = SessionManager()
        success = await session_manager.login(
            request.username,
            request.password,
            request.remember_me
        )
        
        if success:
            return {"success": True, "message": "Login successful"}
        else:
            raise HTTPException(
                status_code=401,
                detail="Login failed. Please check credentials."
            )
        
    except Exception as e:
        logging.error(f"Login failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )

@router.get("/status", response_model=SessionStatusResponse)
async def session_status():
    """
    Check current session status
    """
    try:
        session_manager = SessionManager()
        status = session_manager.get_session_status()
        return status
        
    except Exception as e:
        logging.error(f"Session status check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Session status check failed: {str(e)}"
        )

@router.post("/logout")
async def logout():
    """
    Clear current session
    """
    try:
        session_manager = SessionManager()
        session_manager.logout()
        return {"success": True, "message": "Logged out successfully"}
        
    except Exception as e:
        logging.error(f"Logout failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Logout failed: {str(e)}"
        )