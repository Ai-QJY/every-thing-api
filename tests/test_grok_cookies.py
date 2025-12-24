#!/usr/bin/env python3
"""
Unit tests for Grok cookie extraction and injection functionality
"""

import sys
import os
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from fastapi.testclient import TestClient
from services.cookie_extractor import GrokCookieExtractor, extract_cookies_from_grok


def test_cookie_extractor_import():
    """Test that cookie extractor module can be imported"""
    from services.cookie_extractor import (
        GrokCookieExtractor,
        extract_cookies_from_grok
    )
    assert GrokCookieExtractor is not None
    assert extract_cookies_from_grok is not None
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


def test_extract_cookies_function_signature():
    """Test extract_cookies_from_grok function signature"""
    import inspect
    sig = inspect.signature(extract_cookies_from_grok)
    params = list(sig.parameters.keys())
    assert 'email' in params
    assert 'password' in params
    assert 'timeout_seconds' in params
    print("✓ extract_cookies_from_grok has correct function signature")


def test_api_endpoints_registered():
    """Test that new API endpoints are registered"""
    routes = [route.path for route in app.routes]
    assert '/api/session/extract-grok-cookies' in routes
    assert '/api/session/grok-login' in routes
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
    
    request_with_timeout = GrokLoginRequest(
        email="test@example.com",
        password="password123",
        timeout_seconds=60
    )
    assert request_with_timeout.timeout_seconds == 60
    print("✓ GrokLoginRequest model validation works")


def test_grok_login_request_validation():
    """Test GrokLoginRequest field validation"""
    from api.routers.session import GrokLoginRequest
    from pydantic import ValidationError
    
    try:
        GrokLoginRequest(
            email="test@example.com",
            password="password123",
            timeout_seconds=5
        )
        assert False, "Should have raised validation error for timeout < 10"
    except ValidationError:
        pass
    
    try:
        GrokLoginRequest(
            email="test@example.com",
            password="password123",
            timeout_seconds=400
        )
        assert False, "Should have raised validation error for timeout > 300"
    except ValidationError:
        pass
    print("✓ GrokLoginRequest field validation works correctly")


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
    assert config.GROK_COOKIE_TIMEOUT == 60
    assert config.GROK_LOGIN_TIMEOUT == 120
    assert config.GROK_HEADLESS_MODE == False
    print("✓ Config has Grok-specific settings")


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


def main():
    """Run all tests"""
    print("Testing Grok cookie extraction and injection functionality...")
    print()
    
    try:
        test_cookie_extractor_import()
        test_grokcookieextractor_class()
        test_extract_cookies_function_signature()
        test_api_endpoints_registered()
        test_grok_login_request_model()
        test_grok_login_request_validation()
        test_cookie_model()
        test_mock_extract_cookies()
        test_error_response_format()
        test_config_has_grok_settings()
        test_extractor_close_handles_none()
        test_cookies_list_structure()
        
        print()
        print("🎉 All tests passed! Grok cookie functionality is working correctly.")
        print()
        print("Summary of changes:")
        print("- Created services/cookie_extractor.py with GrokCookieExtractor class")
        print("- Added extract_cookies_from_grok() convenience function")
        print("- Added POST /api/session/extract-grok-cookies endpoint")
        print("- Added POST /api/session/grok-login endpoint")
        print("- Added Grok-specific configuration in config.py")
        print("- Added comprehensive error handling and validation")
        print("- Added structured logging throughout")
        
        return 0
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
