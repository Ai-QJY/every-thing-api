from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from services.session_manager import SessionManager
from services.cookie_extractor import (
    extract_cookies_from_grok,
    extract_grok_cookies_with_manual_oauth,
    save_cookies_to_file,
    load_cookies_from_file,
    ExtractionTask
)
from models.response_models import SessionStatusResponse
import logging
from typing import List, Optional
import asyncio
import uuid

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


class ManualOAuthRequest(BaseModel):
    """Request model for manual OAuth cookie extraction"""
    timeout: Optional[int] = Field(
        default=600,
        ge=60,
        le=1800,
        description="Timeout in seconds (60-1800, default: 600)"
    )
    callback_url: Optional[str] = Field(
        default=None,
        description="Optional webhook URL to notify on completion"
    )


class ManualOAuthResponse(BaseModel):
    """Response model for manual OAuth cookie extraction"""
    status: str
    message: str
    task_id: str
    timeout_seconds: int
    browser_url: Optional[str] = None


class CookieInjectionRequestV2(BaseModel):
    """Request model for injecting Grok cookies"""
    cookies: List[Cookie]
    user_agent: Optional[str] = None
    remember_me: bool = True


class CookieInjectionResponse(BaseModel):
    """Response model for cookie injection"""
    status: str
    message: str
    session_id: Optional[str] = None
    cookies_count: int
    saved_to: Optional[str] = None


class ExtractionStatusResponse(BaseModel):
    """Response model for extraction status"""
    task_id: str
    status: str
    cookies_count: Optional[int] = None
    extracted_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None

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


# ==================== Manual OAuth Endpoints ====================

@router.post("/extract-grok-cookies-manual", response_model=ManualOAuthResponse)
async def extract_grok_cookies_manual(request: ManualOAuthRequest):
    """
    Start semi-automated Grok cookie extraction with manual OAuth.
    
    This endpoint triggers a browser-based extraction process where:
    1. A visible browser window opens to grok.com
    2. User manually completes Google OAuth login
    3. Cookies are automatically extracted and saved
    
    The extraction runs asynchronously - use the returned task_id
    to poll the status endpoint.
    
    - **timeout**: Maximum time to wait for login (60-1800 seconds)
    - **callback_url**: Optional webhook URL for completion notification
    """
    from config import config
    
    logging.info(f"Starting manual OAuth cookie extraction with {request.timeout}s timeout")
    
    # Create a task for tracking
    task_id = ExtractionTask.create_task(timeout=request.timeout)
    
    try:
        # Run the extraction in a background task
        async def run_extraction():
            try:
                result = await extract_grok_cookies_with_manual_oauth(
                    timeout_seconds=request.timeout,
                    callback_url=request.callback_url
                )
                
                if result["status"] == "success":
                    ExtractionTask.update_task(task_id, "completed", result)
                elif result["status"] == "cancelled":
                    ExtractionTask.update_task(task_id, "cancelled", result)
                else:
                    ExtractionTask.update_task(task_id, "failed", result)
                    
            except Exception as e:
                logging.error(f"Extraction task failed: {str(e)}")
                ExtractionTask.update_task(
                    task_id, 
                    "failed",
                    {"status": "error", "error_message": str(e)}
                )
        
        # Start the extraction in background
        asyncio.create_task(run_extraction())
        
        return ManualOAuthResponse(
            status="waiting_for_login",
            message="浏览器已启动，请完成 Google 登录授权...",
            task_id=task_id,
            timeout_seconds=request.timeout
        )
        
    except Exception as e:
        logging.error(f"Failed to start manual OAuth extraction: {str(e)}")
        ExtractionTask.delete_task(task_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start extraction: {str(e)}"
        )


@router.post("/inject-grok-cookies", response_model=CookieInjectionResponse)
async def inject_grok_cookies(request: CookieInjectionRequestV2):
    """
    Inject previously extracted Grok cookies to create a session.
    
    Use this endpoint after running the manual extraction script or
    extracting cookies from the browser. The cookies will be saved
    to file and a session will be created.
    
    - **cookies**: List of cookie objects
    - **user_agent**: Optional user agent string
    - **remember_me**: Whether to persist the session
    """
    logging.info(f"Attempting to inject {len(request.cookies)} cookies")
    
    try:
        # Validate cookies
        if not request.cookies:
            raise HTTPException(
                status_code=400,
                detail="No cookies provided for injection"
            )
        
        # Convert cookies to dict format
        cookie_dicts = [c.dict() for c in request.cookies]
        
        # Log cookie domains for debugging
        domains = set(c.get("domain", "") for c in cookie_dicts)
        logging.info(f"Cookie domains: {domains}")
        
        # Save cookies to file
        save_path = save_cookies_to_file(cookie_dicts)
        logging.info(f"Cookies saved to: {save_path}")
        
        # Create session
        session_id = str(uuid.uuid4())
        session_manager = SessionManager()
        success, cookie_count = await session_manager.inject_cookies(
            cookie_dicts,
            request.user_agent,
            request.remember_me
        )
        
        if success:
            logging.info(f"✅ Successfully injected {cookie_count} cookies, session is valid")
            return CookieInjectionResponse(
                status="success",
                message=f"Cookies injected successfully. Session validated. Injected {cookie_count} cookies.",
                session_id=session_id,
                cookies_count=cookie_count,
                saved_to=save_path
            )
        else:
            # Check for expired cookies
            from datetime import datetime
            current_ts = datetime.now().timestamp()
            expired_count = sum(1 for c in cookie_dicts if c.get("expires") and 0 < c.get("expires") < current_ts)
            
            error_msg = (
                f"Session validation failed after cookie injection.\n"
                f"Injected: {cookie_count}/{len(cookie_dicts)} cookies\n"
                f"Expired: {expired_count} cookies\n\n"
                f"Possible causes:\n"
                f"1. Cookies are expired (check extraction time)\n"
                f"2. Server-side session invalidated\n"
                f"3. Login verification logic needs adjustment\n"
                f"4. Wrong domain - ensure cookies are from grok.com\n\n"
                f"Suggestions:\n"
                f"- Extract fresh cookies (< 1 hour old)\n"
                f"- Verify cookies are from an active grok.com session\n"
                f"- Check server logs for detailed validation info\n"
                f"- If cookies are valid, this might be a detection issue - check logs"
            )
            logging.error(error_msg)
            raise HTTPException(
                status_code=401,
                detail=error_msg
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Cookie injection failed with exception: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Cookie injection failed: {str(e)}"
        )


@router.get("/extract-grok-status/{task_id}", response_model=ExtractionStatusResponse)
async def get_extraction_status(task_id: str):
    """
    Get the status of a manual cookie extraction task.
    
    Use the task_id returned from /extract-grok-cookies-manual to
    poll for completion status.
    
    Possible statuses:
    - **waiting_for_login**: Extraction started, waiting for user login
    - **completed**: Cookies extracted successfully
    - **failed**: Extraction failed
    - **cancelled**: User cancelled the operation
    """
    task = ExtractionTask.get_task(task_id)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    result = task.get("result")
    
    if task["status"] == "completed" and result:
        return ExtractionStatusResponse(
            task_id=task_id,
            status="completed",
            cookies_count=result.get("cookie_count"),
            extracted_at=result.get("extracted_at"),
            duration_seconds=result.get("duration_seconds")
        )
    elif task["status"] == "failed" and result:
        return ExtractionStatusResponse(
            task_id=task_id,
            status="failed",
            error_message=result.get("error_message", "Unknown error")
        )
    elif task["status"] == "cancelled":
        return ExtractionStatusResponse(
            task_id=task_id,
            status="cancelled",
            error_message=(result or {}).get("error_message", "Operation was cancelled")
        )
    else:
        return ExtractionStatusResponse(
            task_id=task_id,
            status=task["status"]
        )


@router.get("/load-grok-cookies")
async def load_grok_cookies():
    """
    Load previously saved Grok cookies from file.
    
    Returns the cookies that were saved by a previous extraction.
    """
    try:
        cookies = load_cookies_from_file()
        
        return {
            "status": "success",
            "message": f"Loaded {len(cookies)} cookies",
            "cookies": cookies,
            "cookie_count": len(cookies)
        }
        
    except Exception as e:
        logging.error(f"Failed to load cookies: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load cookies: {str(e)}"
        )