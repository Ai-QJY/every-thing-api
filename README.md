# AI Browser Automation API Service

A local/private API service that automates browser interactions with AI websites (Grok, x.ai, etc.) to provide programmatic access to their generation capabilities without using official APIs.

## Architecture

```
GUI Program → HTTP → Local API Service (Python) → Playwright → Real Browser → AI Website
```

## Features

- Browser automation using Playwright with real Chromium browsers
- Session management with persistent login states
- Image and video generation endpoints
- Extensible adapter pattern for multiple AI websites
- Local file storage for generated content

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install

# Run the API service
python main.py
```

## API Endpoints

- POST `/api/grok/image` - Generate images from prompts
- POST `/api/grok/video` - Generate videos from prompts (future)
- POST `/api/session/login` - Manual login initialization
- POST `/api/session/oauth-login` - OAuth authorization login
- POST `/api/session/inject-cookies` - Manual session/cookie injection
- GET `/api/session/status` - Check login status

For detailed documentation on all login modes, see [Login Modes Documentation](docs/LOGIN_MODES.md).

## Configuration

Edit `config.py` to configure:
- Browser paths
- Output directories
- Timeout settings
- AI website URLs
