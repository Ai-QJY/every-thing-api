import os
from pathlib import Path
from pydantic_settings import BaseSettings

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