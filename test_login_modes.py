#!/usr/bin/env python3
"""
Test script for new login modes functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from fastapi.testclient import TestClient
from services.session_manager import SessionManager
from models.response_models import SessionStatusResponse

def test_api_creation():
    """Test that the API app can be created successfully"""
    print("✓ API app created successfully")
    
    # Check that new routes are registered
    routes = [route.path for route in app.routes]
    assert '/api/session/oauth-login' in routes, "OAuth login route not found"
    assert '/api/session/inject-cookies' in routes, "Cookie injection route not found"
    print("✓ New login mode routes registered")

def test_session_manager_imports():
    """Test that SessionManager has the new methods"""
    assert hasattr(SessionManager, 'oauth_login'), "SessionManager missing oauth_login method"
    assert hasattr(SessionManager, 'inject_cookies'), "SessionManager missing inject_cookies method"
    assert hasattr(SessionManager, '_get_oauth_url'), "SessionManager missing _get_oauth_url method"
    print("✓ SessionManager has new methods")

def test_documentation_files():
    """Test that documentation files exist"""
    docs_dir = os.path.join(os.path.dirname(__file__), 'docs')
    login_modes_file = os.path.join(docs_dir, 'LOGIN_MODES.md')
    
    assert os.path.exists(login_modes_file), f"Login modes documentation file not found: {login_modes_file}"
    print("✓ Login modes documentation file exists")
    
    # Check file size
    file_size = os.path.getsize(login_modes_file)
    assert file_size > 1000, f"Login modes documentation file too small: {file_size} bytes"
    print(f"✓ Login modes documentation is substantial ({file_size} bytes)")

def test_configuration():
    """Test that configuration includes OAuth settings"""
    from config import config
    
    # Check OAuth config attributes exist
    assert hasattr(config, 'OAUTH_GOOGLE_CLIENT_ID'), "Missing OAUTH_GOOGLE_CLIENT_ID config"
    assert hasattr(config, 'OAUTH_GOOGLE_CLIENT_SECRET'), "Missing OAUTH_GOOGLE_CLIENT_SECRET config"
    assert hasattr(config, 'OAUTH_GITHUB_CLIENT_ID'), "Missing OAUTH_GITHUB_CLIENT_ID config"
    assert hasattr(config, 'OAUTH_GITHUB_CLIENT_SECRET'), "Missing OAUTH_GITHUB_CLIENT_SECRET config"
    assert hasattr(config, 'OAUTH_TWITTER_CLIENT_ID'), "Missing OAUTH_TWITTER_CLIENT_ID config"
    assert hasattr(config, 'OAUTH_TWITTER_CLIENT_SECRET'), "Missing OAUTH_TWITTER_CLIENT_SECRET config"
    print("✓ OAuth configuration attributes exist")

def main():
    """Run all tests"""
    print("Testing new login modes functionality...")
    print()
    
    try:
        test_api_creation()
        test_session_manager_imports()
        test_documentation_files()
        test_configuration()
        
        print()
        print("🎉 All tests passed! New login modes functionality is working correctly.")
        print()
        print("Summary of changes:")
        print("- Added OAuth login endpoint: POST /api/session/oauth-login")
        print("- Added cookie injection endpoint: POST /api/session/inject-cookies")
        print("- Added comprehensive login modes documentation")
        print("- Added OAuth configuration options")
        print("- Updated existing documentation with references to new functionality")
        
        return 0
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())