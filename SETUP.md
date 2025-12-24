# AI Browser Automation API - Setup Guide

## Prerequisites

- Python 3.10+
- Node.js (for Playwright browser installation)
- Git
- Chromium/Chrome browser (optional, Playwright will install its own)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-repo/ai-browser-automation-api.git
cd ai-browser-automation-api
```

### 2. Create virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright browsers

```bash
playwright install
```

This will download the required browser binaries (Chromium by default).

### 5. Configure the service

Edit the `.env` file to customize settings:

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Browser Configuration
BROWSER_TYPE=chromium
HEADLESS=False  # Set to True for headless mode (not recommended for production)

# File Storage
OUTPUT_DIR=./output
SESSION_DIR=./sessions

# AI Website URLs
GROK_URL=https://grok.ai
X_AI_URL=https://x.ai
```

## Running the Service

### Development mode (auto-reload)

```bash
python main.py
```

### Production mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

**Note**: Use only 1 worker since Playwright browsers are not thread-safe.

## First-Time Setup

### 1. Manual Login

Before using the generation APIs, you need to establish a session:

```bash
curl -X POST http://localhost:8000/api/session/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

This will open a real browser window where you can complete the login process manually.

### 2. Verify Session

```bash
curl http://localhost:8000/api/session/status
```

Should return:
```json
{
  "logged_in": true,
  "session_valid": true,
  "session_expiry": "2023-12-31T23:59:59Z",
  "browser_type": "chromium"
}
```

## Using the API

### Generate an Image

```bash
curl -X POST http://localhost:8000/api/grok/image \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A cyberpunk cat with neon lights"}'
```

Response:
```json
{
  "success": true,
  "file_path": "/home/engine/project/output/grok_image_20231224_123456_abc123.png",
  "file_type": "image"
}
```

### Generate a Video (when implemented)

```bash
curl -X POST http://localhost:8000/api/grok/video \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A futuristic cityscape with flying cars", "timeout": 600}'
```

## Troubleshooting

### Browser doesn't open

- Ensure `HEADLESS=False` in `.env`
- Check if you have display server running (X11 on Linux)
- Try running with `DISPLAY=:0` environment variable

### Login fails

- Verify your credentials are correct
- Check if the website URL in `.env` is correct
- Ensure you're not being rate-limited
- Try clearing the session directory and logging in again

### Generation times out

- Increase `GENERATION_TIMEOUT` in `.env`
- Check your internet connection
- Verify the AI website is working properly

## Development

### Running tests

```bash
pytest test_basic.py
```

### Adding new AI websites

1. Create a new service class in `services/` implementing `BaseAIService`
2. Add website-specific selectors and workflows
3. Register the service in `AIServiceFactory`
4. Add configuration to `.env`

### Updating selectors

If the target website changes its UI:

1. Identify the new selectors using browser dev tools
2. Update the selector lists in the service methods
3. Test with the actual website

## Deployment Options

### Local Development

Run directly on your development machine with browser visible.

### Docker Container

Create a Dockerfile with appropriate display settings for headless operation.

### Internal Network

Deploy on a server within your network with proper authentication.

## Security Recommendations

- Use HTTPS in production
- Implement API key authentication
- Restrict access to trusted IPs
- Monitor API usage
- Rotate credentials regularly

## Performance Tuning

- Adjust timeouts based on your network speed
- Monitor browser resource usage
- Consider separate instances for different AI websites
- Implement request queuing for high load scenarios

## Updating

```bash
git pull origin main
pip install -r requirements.txt
playwright install
```

## Support

For issues and questions:

- Check the logs in the console
- Review the browser automation steps
- Consult the architecture documentation
- Examine the specific error messages

## License

[Specify your license here - MIT, Apache 2.0, etc.]