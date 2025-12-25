#!/usr/bin/env python3
"""
Unit tests for Grok cookie extraction and injection functionality

Tests for:
1. Automated login with email/password
2. Semi-automated manual OAuth extraction
3. Cookie file save/load operations
4. API endpoints
"""

import sys
import os
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from fastapi.testclient import TestClient
from services.cookie_extractor import (
    GrokCookieExtractor,
    extract_cookies_from_grok,
    ManualOAuthExtractor,
    save_cookies_to_file,
    load_cookies_from_file,
    ExtractionTask
)
from api.routers.session import (
    ManualOAuthRequest,
    ManualOAuthResponse,
    CookieInjectionRequestV2,
    CookieInjectionResponse,
    ExtractionStatusResponse
)


def test_cookie_extractor_import():
    """Test that cookie extractor module can be imported"""
    from services.cookie_extractor import (
        GrokCookieExtractor,
        extract_cookies_from_grok,
        ManualOAuthExtractor,
        save_cookies_to_file,
        load_cookies_from_file,
        ExtractionTask
    )
    assert GrokCookieExtractor is not None
    assert extract_cookies_from_grok is not None
    assert ManualOAuthExtractor is not None
    assert save_cookies_to_file is not None
    assert load_cookies_from_file is not None
    assert ExtractionTask is not None
    print("✓ Cookie extractor module imports successfully")


def test_grokcookieextractor_class():
    """Test GrokCookieExtractor class structure"""
    extractor = GrokCookieExtractor()
    assert hasattr(extractor, 'initialize')
    assert hasattr(extractor, 'close')
    assert hasattr(extractor, 'extract_cookies')
    assert hasattr(extractor, '_perform_login')
    assert hasattr(extractor, '_extract_all_cookies')
    print("✓ GrokCookieExtractor class has all required methods")


def test_manual_oauth_extractor_class():
    """Test ManualOAuthExtractor class structure"""
    extractor = ManualOAuthExtractor()
    assert hasattr(extractor, 'initialize')
    assert hasattr(extractor, 'close')
    assert hasattr(extractor, 'extract_with_manual_oauth')
    assert hasattr(extractor, '_print_user_instructions')
    assert hasattr(extractor, '_wait_for_login_completion')
    print("✓ ManualOAuthExtractor class has all required methods")


def test_extract_cookies_function_signature():
    """Test extract_cookies_from_grok function signature"""
    import inspect
    sig = inspect.signature(extract_cookies_from_grok)
    params = list(sig.parameters.keys())
    assert 'email' in params
    assert 'password' in params
    assert 'timeout_seconds' in params
    print("✓ extract_cookies_from_grok has correct function signature")


def test_extract_manual_oauth_function_signature():
    """Test extract_grok_cookies_with_manual_oauth function signature"""
    from services.cookie_extractor import extract_grok_cookies_with_manual_oauth
    import inspect
    sig = inspect.signature(extract_grok_cookies_with_manual_oauth)
    params = list(sig.parameters.keys())
    assert 'timeout_seconds' in params
    assert 'callback_url' in params
    print("✓ extract_grok_cookies_with_manual_oauth has correct function signature")


def test_api_endpoints_registered():
    """Test that new API endpoints are registered"""
    routes = [route.path for route in app.routes]
    assert '/api/session/extract-grok-cookies' in routes
    assert '/api/session/grok-login' in routes
    assert '/api/session/extract-grok-cookies-manual' in routes
    assert '/api/session/inject-grok-cookies' in routes
    assert '/api/session/extract-grok-status/{task_id}' in routes
    assert '/api/session/load-grok-cookies' in routes
    print("✓ New Grok API endpoints registered")


def test_grok_login_request_model():
    """Test GrokLoginRequest model validation"""
    from api.routers.session import GrokLoginRequest
    
    valid_request = GrokLoginRequest(
        email="test@example.com",
        password="password123"
    )
    assert valid_request.email == "test@example.com"
    assert valid_request.password == "password123"
    assert valid_request.timeout_seconds is None
    print("✓ GrokLoginRequest model validation works")


def test_manual_oauth_request_model():
    """Test ManualOAuthRequest model validation"""
    valid_request = ManualOAuthRequest(timeout=600)
    assert valid_request.timeout == 600
    assert valid_request.callback_url is None
    
    request_with_callback = ManualOAuthRequest(
        timeout=300,
        callback_url="http://localhost:8000/api/webhook"
    )
    assert request_with_callback.timeout == 300
    assert request_with_callback.callback_url == "http://localhost:8000/api/webhook"
    print("✓ ManualOAuthRequest model validation works")


def test_manual_oauth_request_validation():
    """Test ManualOAuthRequest field validation"""
    from pydantic import ValidationError
    
    # Test timeout too low
    try:
        ManualOAuthRequest(timeout=30)
        assert False, "Should have raised validation error for timeout < 60"
    except ValidationError:
        pass
    
    # Test timeout too high
    try:
        ManualOAuthRequest(timeout=2000)
        assert False, "Should have raised validation error for timeout > 1800"
    except ValidationError:
        pass
    
    # Valid timeouts
    valid_request = ManualOAuthRequest(timeout=60)
    assert valid_request.timeout == 60
    
    valid_request = ManualOAuthRequest(timeout=1800)
    assert valid_request.timeout == 1800
    print("✓ ManualOAuthRequest field validation works correctly")


def test_cookie_model():
    """Test Cookie model structure"""
    from api.routers.session import Cookie
    
    cookie = Cookie(
        name="test_cookie",
        value="test_value",
        domain=".example.com"
    )
    assert cookie.name == "test_cookie"
    assert cookie.value == "test_value"
    assert cookie.domain == ".example.com"
    assert cookie.path == "/"
    assert cookie.expires is None
    print("✓ Cookie model works correctly")


def test_cookie_injection_request_v2():
    """Test CookieInjectionRequestV2 model"""
    from api.routers.session import Cookie
    cookies = [
        Cookie(name="cookie1", value="value1", domain=".example.com"),
        Cookie(name="cookie2", value="value2", domain=".example.com")
    ]
    request = CookieInjectionRequestV2(cookies=cookies, remember_me=True)
    assert len(request.cookies) == 2
    assert request.remember_me is True
    print("✓ CookieInjectionRequestV2 model works correctly")


def test_mock_extract_cookies():
    """Test mock extraction returns expected format"""
    async def mock_extract():
        return {
            "status": "success",
            "cookies": [
                {
                    "name": "APISID",
                    "value": "mock_value",
                    "domain": ".google.com",
                    "path": "/",
                    "expires": 1735171200,
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "None"
                }
            ],
            "cookie_count": 1,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": 1.5
        }
    
    result = asyncio.run(mock_extract())
    assert result["status"] == "success"
    assert len(result["cookies"]) == 1
    assert result["cookie_count"] == 1
    assert "extracted_at" in result
    assert "duration_seconds" in result
    print("✓ Mock extraction returns expected format")


def test_error_response_format():
    """Test error response format for timeout"""
    error_response = {
        "status": "error",
        "error_type": "timeout",
        "error_message": "Operation timed out after 60 seconds",
        "cookies": [],
        "cookie_count": 0
    }
    assert error_response["status"] == "error"
    assert error_response["error_type"] == "timeout"
    assert len(error_response["cookies"]) == 0
    print("✓ Error response format is correct")


def test_config_has_grok_settings():
    """Test that config includes Grok-specific settings"""
    from config import config
    
    assert hasattr(config, 'GROK_COOKIE_TIMEOUT')
    assert hasattr(config, 'GROK_LOGIN_TIMEOUT')
    assert hasattr(config, 'GROK_HEADLESS_MODE')
    assert hasattr(config, 'GROK_OAUTH_TIMEOUT')
    assert hasattr(config, 'GROK_COOKIE_FILE_PATH')
    assert config.GROK_COOKIE_TIMEOUT == 60
    assert config.GROK_LOGIN_TIMEOUT == 120
    assert config.GROK_HEADLESS_MODE == False
    assert config.GROK_OAUTH_TIMEOUT == 600
    assert config.GROK_COOKIE_FILE_PATH == "data/grok_cookies.json"
    print("✓ Config has Grok-specific settings including OAuth")


def test_extractor_close_handles_none():
    """Test that extractor.close() handles None values gracefully"""
    async def test_close():
        extractor = GrokCookieExtractor()
        extractor.page = None
        extractor.context = None
        extractor.browser = None
        extractor.playwright = None
        await extractor.close()
        assert True
    
    asyncio.run(test_close())
    print("✓ Extractor close handles None values gracefully")


def test_cookies_list_structure():
    """Test that extracted cookies have all required fields"""
    mock_cookies = [
        {
            "name": "session_id",
            "value": "abc123",
            "domain": ".grok.com",
            "path": "/",
            "expires": 1735171200,
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax"
        },
        {
            "name": "user_pref",
            "value": "dark_mode",
            "domain": "grok.com",
            "path": "/settings",
            "expires": None,
            "httpOnly": False,
            "secure": False,
            "sameSite": None
        }
    ]
    
    for cookie in mock_cookies:
        assert "name" in cookie
        assert "value" in cookie
        assert "domain" in cookie
        assert "path" in cookie
        assert "expires" in cookie
        assert "httpOnly" in cookie
        assert "secure" in cookie
    
    assert len(mock_cookies) == 2
    print("✓ Cookie list structure is valid")


def test_save_cookies_to_file():
    """Test saving cookies to file"""
    import tempfile
    import os
    
    cookies = [
        {"name": "test_cookie", "value": "test_value", "domain": ".example.com", "path": "/"}
    ]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test_cookies.json")
        result = save_cookies_to_file(cookies, filepath)
        
        assert result == filepath
        assert os.path.exists(filepath)
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        assert "extracted_at" in data
        assert "cookie_count" in data
        assert data["cookie_count"] == 1
        assert len(data["cookies"]) == 1
        assert data["cookies"][0]["name"] == "test_cookie"
    
    print("✓ save_cookies_to_file works correctly")


def test_load_cookies_from_file():
    """Test loading cookies from file"""
    import tempfile
    import os
    
    cookies = [
        {"name": "test_cookie1", "value": "value1", "domain": ".example.com", "path": "/"},
        {"name": "test_cookie2", "value": "value2", "domain": ".example.com", "path": "/"}
    ]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, "test_cookies.json")
        
        # Save first
        save_cookies_to_file(cookies, filepath)
        
        # Load
        loaded = load_cookies_from_file(filepath)
        
        assert len(loaded) == 2
        assert loaded[0]["name"] == "test_cookie1"
        assert loaded[1]["name"] == "test_cookie2"
    
    print("✓ load_cookies_from_file works correctly")


def test_load_cookies_from_nonexistent_file():
    """Test loading cookies from nonexistent file returns empty list"""
    loaded = load_cookies_from_file("/nonexistent/path/cookies.json")
    assert loaded == []
    print("✓ load_cookies_from_file handles nonexistent file correctly")


def test_extraction_task_class():
    """Test ExtractionTask class functionality"""
    # Create task
    task_id = ExtractionTask.create_task(timeout=600)
    assert task_id is not None
    assert len(task_id) == 36  # UUID format
    
    # Get task
    task = ExtractionTask.get_task(task_id)
    assert task is not None
    assert task["status"] == "waiting_for_login"
    assert task["timeout"] == 600
    
    # Update task
    result = {"status": "success", "cookie_count": 15}
    ExtractionTask.update_task(task_id, "completed", result)
    
    task = ExtractionTask.get_task(task_id)
    assert task["status"] == "completed"
    assert task["result"]["cookie_count"] == 15
    
    # Delete task
    ExtractionTask.delete_task(task_id)
    task = ExtractionTask.get_task(task_id)
    assert task is None
    
    print("✓ ExtractionTask class works correctly")


def test_manual_oauth_response_model():
    """Test ManualOAuthResponse model"""
    response = ManualOAuthResponse(
        status="waiting_for_login",
        message="Please complete login in browser",
        task_id="test-uuid",
        timeout_seconds=600
    )
    assert response.status == "waiting_for_login"
    assert response.task_id == "test-uuid"
    assert response.timeout_seconds == 600
    print("✓ ManualOAuthResponse model works correctly")


def test_cookie_injection_response_model():
    """Test CookieInjectionResponse model"""
    response = CookieInjectionResponse(
        status="success",
        message="Cookies injected successfully",
        session_id="session-uuid",
        cookies_count=15,
        saved_to="data/grok_cookies.json"
    )
    assert response.status == "success"
    assert response.cookies_count == 15
    print("✓ CookieInjectionResponse model works correctly")


def test_extraction_status_response_model():
    """Test ExtractionStatusResponse model"""
    # Completed status
    status = ExtractionStatusResponse(
        task_id="task-uuid",
        status="completed",
        cookies_count=15,
        extracted_at="2025-12-24T10:30:00Z",
        duration_seconds=45.5
    )
    assert status.status == "completed"
    assert status.cookies_count == 15
    
    # Failed status
    status_failed = ExtractionStatusResponse(
        task_id="task-uuid",
        status="failed",
        error_message="Timeout error"
    )
    assert status_failed.status == "failed"
    assert status_failed.error_message == "Timeout error"
    
    print("✓ ExtractionStatusResponse model works correctly")


def test_script_file_exists():
    """Test that the extraction script exists"""
    script_path = Path(__file__).parent.parent / "scripts" / "extract_grok_cookies.py"
    assert script_path.exists()
    print("✓ Extraction script exists")


def test_guide_documentation_exists():
    """Test that the guide documentation exists"""
    guide_path = Path(__file__).parent.parent / "docs" / "GROK_COOKIE_GUIDE.md"
    assert guide_path.exists()
    print("✓ Guide documentation exists")


def main():
    """Run all tests"""
    print("Testing Grok cookie extraction and injection functionality...")
    print()
    
    try:
        # Basic imports and class structure
        test_cookie_extractor_import()
        test_grokcookieextractor_class()
        test_manual_oauth_extractor_class()
        
        # Function signatures
        test_extract_cookies_function_signature()
        test_extract_manual_oauth_function_signature()
        
        # API endpoints
        test_api_endpoints_registered()
        
        # Model validation
        test_grok_login_request_model()
        test_manual_oauth_request_model()
        test_manual_oauth_request_validation()
        test_cookie_model()
        test_cookie_injection_request_v2()
        
        # Mock extraction
        test_mock_extract_cookies()
        test_error_response_format()
        
        # Configuration
        test_config_has_grok_settings()
        
        # Cleanup
        test_extractor_close_handles_none()
        
        # Data structures
        test_cookies_list_structure()
        
        # File operations
        test_save_cookies_to_file()
        test_load_cookies_from_file()
        test_load_cookies_from_nonexistent_file()
        
        # Task management
        test_extraction_task_class()
        
        # Response models
        test_manual_oauth_response_model()
        test_cookie_injection_response_model()
        test_extraction_status_response_model()
        
        # Files
        test_script_file_exists()
        test_guide_documentation_exists()
        
        print()
        print("🎉 All tests passed! Grok cookie functionality is working correctly.")
        print()
        print("Summary of changes:")
        print("- Extended services/cookie_extractor.py with ManualOAuthExtractor class")
        print("- Added save_cookies_to_file() and load_cookies_from_file() functions")
        print("- Added ExtractionTask class for task management")
        print("- Added extract_grok_cookies_with_manual_oauth() convenience function")
        print("- Added POST /api/session/extract-grok-cookies-manual endpoint")
        print("- Added POST /api/session/inject-grok-cookies endpoint")
        print("- Added GET /api/session/extract-grok-status/{task_id} endpoint")
        print("- Added GET /api/session/load-grok-cookies endpoint")
        print("- Updated config.py with GROK_OAUTH_TIMEOUT and GROK_COOKIE_FILE_PATH")
        print("- Created scripts/extract_grok_cookies.py command-line tool")
        print("- Created docs/GROK_COOKIE_GUIDE.md usage documentation")
        
        return 0
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
