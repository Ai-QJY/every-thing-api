import asyncio
from fastapi.testclient import TestClient
from main import app
from config import config

# Create test client - use the app directly
client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "AI Browser Automation API Service"}
    print("✓ Root endpoint test passed")

def test_session_status_no_session():
    """Test session status when no session exists"""
    response = client.get("/api/session/status")
    assert response.status_code == 200
    data = response.json()
    assert data["logged_in"] == False
    assert data["session_valid"] == False
    print("✓ Session status test passed")

def test_grok_image_no_session():
    """Test image generation without session"""
    response = client.post("/api/grok/image", json={
        "prompt": "test prompt"
    })
    assert response.status_code == 401
    assert "No valid session" in response.json()["detail"]
    print("✓ Grok image no session test passed")

if __name__ == "__main__":
    test_root_endpoint()
    test_session_status_no_session()
    test_grok_image_no_session()
    print("\n🎉 All basic tests passed!")