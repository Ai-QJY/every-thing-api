from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from services.session_manager import SessionManager
from models.response_models import SessionStatusResponse
import logging
from typing import List, Optional

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = True

class OAuthLoginRequest(BaseModel):
    provider: str
    auth_code: str
    redirect_uri: Optional[str] = None
    remember_me: bool = True

class Cookie(BaseModel):
    name: str
    value: str
    domain: str
    path: str = "/"
    expires: Optional[int] = None
    httpOnly: bool = False
    secure: bool = False
    sameSite: Optional[str] = None

class CookieInjectionRequest(BaseModel):
    cookies: List[Cookie]
    user_agent: Optional[str] = None
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

@router.post("/oauth-login")
async def oauth_login(request: OAuthLoginRequest):
    """
    OAuth authorization login
    """
    try:
        session_manager = SessionManager()
        success, session_id = await session_manager.oauth_login(
            request.provider,
            request.auth_code,
            request.redirect_uri,
            request.remember_me
        )
        
        if success:
            return {
                "success": True,
                "message": "OAuth login successful",
                "provider": request.provider,
                "session_id": session_id
            }
        else:
            raise HTTPException(
                status_code=401,
                detail="OAuth login failed. Invalid authorization code or provider."
            )
        
    except Exception as e:
        logging.error(f"OAuth login failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"OAuth login failed: {str(e)}"
        )

@router.post("/inject-cookies")
async def inject_cookies(request: CookieInjectionRequest):
    """
    Manual session/cookie injection
    """
    try:
        session_manager = SessionManager()
        success, cookie_count = await session_manager.inject_cookies(
            request.cookies,
            request.user_agent,
            request.remember_me
        )
        
        if success:
            return {
                "success": True,
                "message": "Cookies injected successfully",
                "session_valid": session_manager.has_valid_session(),
                "cookie_count": cookie_count
            }
        else:
            raise HTTPException(
                status_code=401,
                detail="Session injection failed. Invalid or expired cookies."
            )
        
    except Exception as e:
        logging.error(f"Cookie injection failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Cookie injection failed: {str(e)}"
        )