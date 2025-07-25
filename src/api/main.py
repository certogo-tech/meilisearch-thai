"""FastAPI application for Thai tokenizer service."""

import time
from contextlib import asynccontextmanager
from typing import Dict, Any
from datetime import datetime
import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.utils.logging import setup_logging
from src.api.models.responses import HealthCheckResponse, ErrorResponse
from src.tokenizer.config_manager import ConfigManager
from src.meilisearch_integration.client import MeiliSearchClient
from src.utils.health import health_checker, register_default_checks

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Global state
app_state: Dict[str, Any] = {
    "start_time": time.time(),
    "version": "1.0.0",
    "config_manager": None,
    "meilisearch_client": None,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Thai tokenizer service")
    
    try:
        # Initialize configuration manager
        app_state["config_manager"] = ConfigManager()
        logger.info("Configuration manager initialized")
        
        # Initialize MeiliSearch client
        meilisearch_config = app_state["config_manager"].get_meilisearch_config()
        # Convert to the client's expected config format
        from src.meilisearch_integration.client import MeiliSearchConfig as ClientConfig
        client_config = ClientConfig(
            host=meilisearch_config.host,
            api_key=meilisearch_config.api_key,
            timeout=meilisearch_config.timeout_ms // 1000,  # Convert ms to seconds
            max_retries=meilisearch_config.max_retries
        )
        app_state["meilisearch_client"] = MeiliSearchClient(client_config)
        logger.info("MeiliSearch client initialized")
        
        # Register health checks
        register_default_checks(
            app_state["meilisearch_client"],
            app_state["config_manager"]
        )
        logger.info("Health checks registered")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down Thai tokenizer service")
        if app_state.get("meilisearch_client"):
            # Cleanup MeiliSearch client if needed
            pass


# Create FastAPI application
app = FastAPI(
    title="Thai Tokenizer for MeiliSearch",
    description="A service for Thai text tokenization and MeiliSearch integration",
    version=app_state["version"],
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all requests and responses."""
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
        }
    )
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"Response: {response.status_code} in {process_time:.4f}s",
        extra={
            "status_code": response.status_code,
            "process_time": process_time,
        }
    )
    
    return response


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="validation_error",
            message="Request validation failed",
            details={"errors": exc.errors()},
            timestamp=datetime.now()
        ).model_dump()
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP error {exc.status_code}: {exc.detail}")
    error_response = ErrorResponse(
        error="http_error",
        message=exc.detail,
        timestamp=datetime.now()
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode="json")
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    error_response = ErrorResponse(
        error="internal_error",
        message="Internal server error",
        timestamp=datetime.now()
    )
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(mode="json")
    )


# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint for container monitoring."""
    uptime = int(time.time() - app_state["start_time"])
    
    # Run all health checks
    check_results = await health_checker.run_all_checks()
    
    # Convert results to simple status format
    dependencies = {}
    for name, result in check_results.items():
        dependencies[name] = result["status"]
    
    # Get overall status
    status = health_checker.get_overall_status(check_results)
    
    return HealthCheckResponse(
        status=status,
        version=app_state["version"],
        uptime_seconds=uptime,
        dependencies=dependencies
    )


# Include routers
from src.api.endpoints import tokenize, documents, config
app.include_router(tokenize.router, prefix="/api/v1", tags=["tokenization"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(config.router, prefix="/api/v1", tags=["configuration"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Thai Tokenizer for MeiliSearch",
        "version": app_state["version"],
        "status": "running",
        "docs": "/docs"
    }