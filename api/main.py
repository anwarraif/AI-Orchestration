"""
FastAPI application entry point.
Main application with middleware, startup/shutdown events, and router registration.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import logging
import time
import os
import sys

from .routers import chat, sessions, suggestions, metrics, vitals, health
from db.client import get_db_client
from db.indexes import create_indexes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Track application start time for uptime
APP_START_TIME = time.time()

# Security scheme for Swagger
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting AI Orchestration Backend...")
    
    try:
        # Connect to MongoDB
        db_client = get_db_client()
        await db_client.connect()
        logger.info("MongoDB connected")
        
        # Create indexes
        db = db_client.get_database()
        await create_indexes(db)
        logger.info("Indexes created")
        
        # Store start time in app state
        app.state.start_time = APP_START_TIME
        
        # Log environment
        llm_provider = os.getenv("LLM_PROVIDER", "mock")
        logger.info(f"LLM Provider: {llm_provider}")
        
        logger.info("Application started successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Orchestration Backend...")
    
    try:
        db_client = get_db_client()
        await db_client.disconnect()
        logger.info("✓ MongoDB disconnected")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


# Create FastAPI application with security scheme
app = FastAPI(
    title="AI Orchestration Backend",
    description="""
Multi-agent orchestration with LangGraph, streaming, and context-aware memory.

## Authentication
All endpoints (except /health) require Bearer token authentication.

**Default token for testing:** `devkey`

Click the **Authorize** button and enter: `Bearer devkey`
""",
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True  # Remember auth across page reloads
    }
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing."""
    start_time = time.time()
    
    # Log request
    logger.info(f"→ {request.method} {request.url.path}")
    
    # Process request
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"Request failed: {str(e)}", exc_info=True)
        raise
    
    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000
    
    # Log response
    logger.info(
        f"← {request.method} {request.url.path} "
        f"[{response.status_code}] {duration_ms:.2f}ms"
    )
    
    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if os.getenv("DEBUG") == "true" else "An error occurred"
        }
    )


# Register routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(chat.router, prefix="/v1/chat", tags=["Chat"])
app.include_router(sessions.router, prefix="/v1/sessions", tags=["Sessions"])
app.include_router(suggestions.router, prefix="/v1/suggestions", tags=["Suggestions"])
app.include_router(metrics.router, prefix="/v1/metrics", tags=["Metrics"])
app.include_router(vitals.router, prefix="/v1/vitals", tags=["Vitals"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AI Orchestration Backend",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "auth": "Use 'Bearer devkey' for testing"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )