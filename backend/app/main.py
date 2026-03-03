"""
FastAPI Application Factory
Main entry point for the RAG Framework backend
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from .config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages FastAPI app lifecycle - startup and shutdown
    """
    # Startup
    logger.info("🚀 RAG Framework Backend starting up...")
    settings = get_settings()
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Vector DB: {settings.vector_db.type}")
    logger.info(f"LLM: {settings.llm.type} at {settings.llm.ollama_host}")
    
    # Initialize database
    try:
        from .database import init_db
        init_db()
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    yield

    # Shutdown
    logger.info("🛑 RAG Framework Backend shutting down...")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application instance
    """
    settings = get_settings()

    # Create app with lifespan
    app = FastAPI(
        title=settings.api_title,
        description="Multi-Agent RAG Framework for CI/CD Error Resolution",
        version=settings.api_version,
        debug=settings.debug,
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add exception handlers
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(exc) if settings.debug else "Unknown error"}
        )

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """
        Health check endpoint for load balancers and monitoring
        """
        return {
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.app_version
        }

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """
        Root endpoint with API information
        """
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "openapi_schema": "/openapi.json"
        }

    # Include routers
    from .api import logs, dependencies, rag, integrations, analysis, setup
    app.include_router(logs.router)
    app.include_router(dependencies.router)
    app.include_router(rag.router)
    app.include_router(integrations.router)
    app.include_router(analysis.router)
    app.include_router(setup.router)

    logger.info(f"✅ FastAPI app created with {len(app.routes)} routes")
    return app


# Create app instance
app = create_app()

# For uvicorn: uvicorn backend.app.main:app --reload
