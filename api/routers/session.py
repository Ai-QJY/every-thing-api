from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from services.session_manager import SessionManager
from services.cookie_extractor import extract_cookies_from_grok
from models.response_models import SessionStatusResponse
import logging
from typing import List, Optional
import asyncio

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

class GrokLoginRequest(BaseModel):
    email: str = Field(..., description="User email for Grok login")
    password: str = Field(..., description="User password for Grok login")
    timeout_seconds: Optional[int] = Field(
        None,
        ge=10,
        le=300,
        description="Custom timeout in seconds (10-300)"
    )

class GrokLoginResponse(BaseModel):
    status: str
    message: str
    session_id: Optional[str] = None
    cookie_count: Optional[int] = None

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

@router.post("/extract-grok-cookies")
async def extract_grok_cookies(request: GrokLoginRequest):
    """
    Automatically extract cookies from Grok after login.
    
    This endpoint performs an automated login to Grok.com and extracts
    all cookies from the browser session.
    
    - **email**: User email for Grok login
    - **password**: User password for Grok login
    - **timeout_seconds**: Optional custom timeout (10-300 seconds)
    """
    logging.info(f"Starting Grok cookie extraction for: {request.email}")
    
    try:
        result = await asyncio.wait_for(
            extract_cookies_from_grok(
                request.email,
                request.password,
                request.timeout_seconds
            ),
            timeout=request.timeout_seconds or 120
        )
        
        if result["status"] == "success":
            logging.info(
                f"Successfully extracted {result['cookie_count']} cookies "
                f"for {request.email}"
            )
            return {
                "status": "success",
                "message": "Cookies extracted successfully",
                "cookies": result["cookies"],
                "cookie_count": result["cookie_count"],
                "extracted_at": result["extracted_at"],
                "duration_seconds": result["duration_seconds"]
            }
        else:
            error_type = result.get("error_type", "unknown")
            error_message = result.get("error_message", "Unknown error")
            
            if error_type == "timeout":
                logging.error(f"Cookie extraction timed out for {request.email}")
                raise HTTPException(
                    status_code=504,
                    detail=f"Cookie extraction timed out: {error_message}"
                )
            else:
                logging.error(
                    f"Cookie extraction failed for {request.email}: {error_message}"
                )
                raise HTTPException(
                    status_code=401,
                    detail=f"Login failed: {error_message}"
                )
                
    except asyncio.TimeoutError:
        logging.error(f"Cookie extraction timed out for {request.email}")
        raise HTTPException(
            status_code=504,
            detail="Cookie extraction timed out. Please try again or increase timeout."
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Cookie extraction failed for {request.email}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Cookie extraction failed: {str(e)}"
        )

@router.post("/grok-login")
async def grok_login(request: GrokLoginRequest):
    """
    One-step login and cookie injection for Grok.
    
    This endpoint performs an automated login to Grok.com, extracts
    all cookies, and injects them into a session.
    
    - **email**: User email for Grok login
    - **password**: User password for Grok login
    - **timeout_seconds**: Optional custom timeout (10-300 seconds)
    """
    import uuid
    
    logging.info(f"Starting Grok login and session creation for: {request.email}")
    
    try:
        result = await asyncio.wait_for(
            extract_cookies_from_grok(
                request.email,
                request.password,
                request.timeout_seconds
            ),
            timeout=request.timeout_seconds or 120
        )
        
        if result["status"] == "success":
            session_id = str(uuid.uuid4())
            
            session_manager = SessionManager()
            success, cookie_count = await session_manager.inject_cookies(
                result["cookies"],
                user_agent=None,
                remember_me=True
            )
            
            if success:
                logging.info(
                    f"Successfully created session {session_id} with "
                    f"{cookie_count} cookies for {request.email}"
                )
                return {
                    "status": "success",
                    "message": "Grok login and session creation successful",
                    "session_id": session_id,
                    "cookie_count": cookie_count,
                    "extracted_at": result["extracted_at"]
                }
            else:
                logging.error(
                    f"Cookie injection failed for {request.email}"
                )
                raise HTTPException(
                    status_code=401,
                    detail="Session creation failed after successful login"
                )
        else:
            error_type = result.get("error_type", "unknown")
            error_message = result.get("error_message", "Unknown error")
            
            if error_type == "timeout":
                logging.error(f"Grok login timed out for {request.email}")
                raise HTTPException(
                    status_code=504,
                    detail=f"Login timed out: {error_message}"
                )
            else:
                logging.error(
                    f"Grok login failed for {request.email}: {error_message}"
                )
                raise HTTPException(
                    status_code=401,
                    detail=f"Login failed: {error_message}"
                )
                
    except asyncio.TimeoutError:
        logging.error(f"Grok login timed out for {request.email}")
        raise HTTPException(
            status_code=504,
            detail="Login timed out. Please try again or increase timeout."
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Grok login failed for {request.email}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )