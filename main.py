import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import grok, session
from config import config

app = FastAPI(title="AI Browser Automation API", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(grok.router, prefix="/api/grok", tags=["grok"])
app.include_router(session.router, prefix="/api/session", tags=["session"])

@app.get("/")
async def root():
    return {"message": "AI Browser Automation API Service"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True
    )