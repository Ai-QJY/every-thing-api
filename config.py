import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent


class Config(BaseSettings):
    # Browser configuration
    BROWSER_TYPE: str = "chromium"
    HEADLESS: bool = False
    BROWSER_TIMEOUT: int = 60000  # 60 seconds
    
    # File storage
    OUTPUT_DIR: str = "/home/engine/project/output"
    SESSION_DIR: str = "/home/engine/project/sessions"
    
    # AI Website URLs
    GROK_URL: str = "https://grok.ai"
    X_AI_URL: str = "https://x.ai"
    
    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Timeout settings
    GENERATION_TIMEOUT: int = 300  # 5 minutes for generation
    LOGIN_TIMEOUT: int = 120  # 2 minutes for login
    
    # Grok specific settings
    GROK_COOKIE_TIMEOUT: int = 60  # Cookie extraction timeout in seconds
    GROK_LOGIN_TIMEOUT: int = 120  # Login operation timeout in seconds
    GROK_HEADLESS_MODE: bool = False  # Use headless browser for debugging
    
    # Manual OAuth settings (for semi-automated extraction)
    GROK_OAUTH_TIMEOUT: int = 600  # Wait for user login timeout (10 minutes)
    GROK_COOKIE_FILE_PATH: str = str(BASE_DIR / "data" / "grok_cookies.json")  # Cookie storage path

    # Use a persistent browser profile for manual OAuth (avoids "incognito"-like fresh contexts)
    # Can be overridden via env var GROK_OAUTH_USER_DATA_DIR
    GROK_OAUTH_USER_DATA_DIR: str = str(BASE_DIR / "data" / "grok_oauth_profile")
    GROK_OAUTH_PERSISTENT_CONTEXT: bool = True
    
    # OAuth settings
    OAUTH_GOOGLE_CLIENT_ID: str = ""
    OAUTH_GOOGLE_CLIENT_SECRET: str = ""
    OAUTH_GITHUB_CLIENT_ID: str = ""
    OAUTH_GITHUB_CLIENT_SECRET: str = ""
    OAUTH_TWITTER_CLIENT_ID: str = ""
    OAUTH_TWITTER_CLIENT_SECRET: str = ""
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

config = Config()

# Ensure directories exist
Path(config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
Path(config.SESSION_DIR).mkdir(parents=True, exist_ok=True)