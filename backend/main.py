"""
backend/main.py
================
The main FastAPI application entry point.

Phase 3 additions:
  - Imports and uses the structured logger (utils/logger.py)
  - Registers the new /health endpoint (routes/health.py)
  - Supabase connection is checked on startup
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# 1. Load environment variables from the root .env file FIRST.
# This must happen before any other imports that read env vars,
# because they read os.getenv() at import time.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"), override=True)

# 2. Set up structured logging (Phase 3).
# We do this early so all subsequent imports can use the logger properly.
# This configures log output to both the terminal and logs/app.log.
from utils import setup_logging, get_logger
setup_logging(level="INFO")
logger = get_logger("backend.main")

# 3. Import routers from our routes directory
from routes import router as api_router
import database

# 4. Initialize SQLite database (creates tables & seeds mock data if first run)
database.init_db()
logger.info("SQLite database initialized successfully")

# 5. Initialize the FastAPI application
app = FastAPI(
    title="LiveKit Voice AI Support Backend",
    description="Backend API for generating LiveKit access tokens and managing customer rooms.",
    version="3.0.0"  # Updated to v3 for Phase 3
)

# 6. Configure Cross-Origin Resource Sharing (CORS)
# This allows our React frontend (typically running on http://localhost:3000)
# to communicate with our FastAPI server (running on http://localhost:8000).
# In production, replace "*" with your actual frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # For local development. Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],   # Allow all HTTP verbs (GET, POST, etc.)
    allow_headers=["*"],   # Allow all request headers
)

# 7. Include our API routers (each file handles a group of related endpoints)
app.include_router(api_router)

logger.info("All API routers registered")

# 8. Define a root endpoint to check if the backend is running
@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "LiveKit Voice AI Support Backend is running successfully!",
        "version": "3.0.0",
        "tip": "Visit /health for a full system status check"
    }

# 9. Run the server using Uvicorn if this file is executed directly
if __name__ == "__main__":
    # Get port from environment or default to 8000
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting server on http://localhost:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
