#!/usr/bin/env python3

"""
Simple test to verify the basic structure works
"""

import sys
import os

# Add project root to path
sys.path.insert(0, '/home/engine/project')

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    
    try:
        # Test config
        from config import config
        print("✓ Config module imported successfully")
        print(f"  - API will run on {config.API_HOST}:{config.API_PORT}")
        print(f"  - Browser type: {config.BROWSER_TYPE}")
        print(f"  - Headless mode: {config.HEADLESS}")
        
        # Test models
        from models.response_models import GenerationResponse, SessionStatusResponse
        print("✓ Response models imported successfully")
        
        # Test services
        from services.base_ai_service import BaseAIService
        from services.grok_service import GrokService
        from services.session_manager import SessionManager
        from services.ai_service_factory import AIServiceFactory
        print("✓ Service classes imported successfully")
        
        # Test utils
        from utils.error_handling import AIServiceError, ErrorHandler
        from utils.browser_utils import BrowserUtils
        print("✓ Utility modules imported successfully")
        
        # Test API routers
        from api.routers.grok import router as grok_router
        from api.routers.session import router as session_router
        print("✓ API routers imported successfully")
        
        # Test main app
        from main import app
        print("✓ Main application imported successfully")
        
        print("\n🎉 All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_config_values():
    """Test that config values are loaded correctly"""
    print("\nTesting configuration...")
    
    from config import config
    
    # Test default values
    assert config.BROWSER_TYPE == "chromium"
    assert config.HEADLESS == False
    assert config.API_HOST == "0.0.0.0"
    assert config.API_PORT == 8000
    
    print("✓ Configuration values are correct")
    return True

def test_directory_creation():
    """Test that directories are created"""
    print("\nTesting directory creation...")
    
    from config import config
    from pathlib import Path
    
    # Check if directories exist
    output_dir = Path(config.OUTPUT_DIR)
    session_dir = Path(config.SESSION_DIR)
    
    assert output_dir.exists(), f"Output directory {config.OUTPUT_DIR} does not exist"
    assert session_dir.exists(), f"Session directory {config.SESSION_DIR} does not exist"
    
    print(f"✓ Directories created: {config.OUTPUT_DIR}, {config.SESSION_DIR}")
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("AI Browser Automation API - Basic Structure Test")
    print("=" * 60)
    
    success = True
    
    # Run all test functions
    success &= test_imports()
    success &= test_config_values()
    success &= test_directory_creation()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED! The basic structure is working correctly.")
        print("\nNext steps:")
        print("1. Run 'playwright install' to install browser binaries")
        print("2. Start the API with 'python main.py'")
        print("3. Test the API endpoints with curl or Postman")
    else:
        print("❌ Some tests failed. Please check the error messages above.")
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())