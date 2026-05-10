"""FastAPI application for Spin K8s Deployment Tool."""

import logging
import os
import sys
import time
import json
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.routes import router as api_router

# Configure logging level from environment variable
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, LOG_LEVEL, logging.INFO)

# Configure root logger
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True
)

# Set uvicorn loggers to same level
logging.getLogger("uvicorn").setLevel(log_level)
logging.getLogger("uvicorn.access").setLevel(log_level)
logging.getLogger("uvicorn.error").setLevel(log_level)

logger = logging.getLogger(__name__)
logger.info(f"Log level set to: {LOG_LEVEL}")


# Filter out health check logs from uvicorn access logs
class HealthCheckFilter(logging.Filter):
    """Filter to exclude health check endpoint logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Return False for health check requests to exclude them from logs."""
        return "/health" not in record.getMessage()


# Apply filter to uvicorn access logger at module load time
logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())


class RequestResponseLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log detailed request and response information."""

    async def dispatch(self, request: Request, call_next):
        # Skip health check endpoints
        if request.url.path == "/health":
            return await call_next(request)

        # Log request
        start_time = time.time()

        # Get request body for POST/PUT
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                # Reset body for downstream handlers
                async def receive():
                    return {"type": "http.request", "body": body}
                request._receive = receive
            except Exception:
                body = None

        logger.info(f">>> REQUEST: {request.method} {request.url.path}")
        logger.info(f"    Query: {dict(request.query_params)}")
        logger.info(f"    Headers: {dict(request.headers)}")
        if body and len(body) < 1000:  # Don't log large bodies
            try:
                logger.info(f"    Body: {body.decode('utf-8', errors='ignore')[:500]}")
            except Exception:
                logger.info(f"    Body: <binary data, {len(body)} bytes>")

        # Process request
        response = await call_next(request)

        # Log response
        duration = time.time() - start_time
        logger.info(f"<<< RESPONSE: {response.status_code} ({duration:.3f}s)")

        return response


app = FastAPI(
    title="Spin K8s Deployment Tool",
    description="FastAPI-based API server for building, pushing, and deploying Spin applications to Kubernetes",
    version="0.1.0",
)

# Add request/response logging middleware
app.add_middleware(RequestResponseLoggingMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for internal server errors."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


# Mount API router
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
