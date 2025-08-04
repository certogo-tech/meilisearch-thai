"""
API Key authentication middleware for Thai Search Proxy.
"""

from typing import Optional
from fastapi import HTTPException, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
import os
import logging

logger = logging.getLogger(__name__)

# Security scheme for API documentation
security = HTTPBearer(auto_error=False)


class APIKeyAuth:
    """API Key authentication handler."""
    
    def __init__(self):
        self.api_key_required = os.getenv("API_KEY_REQUIRED", "false").lower() == "true"
        self.api_key = os.getenv("SEARCH_PROXY_API_KEY", "").strip()
        
        if self.api_key_required and not self.api_key:
            raise ValueError(
                "API_KEY_REQUIRED is true but SEARCH_PROXY_API_KEY is not set. "
                "Please set SEARCH_PROXY_API_KEY environment variable."
            )
        
        logger.info(f"API Key authentication: {'enabled' if self.api_key_required else 'disabled'}")
    
    async def __call__(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
    ) -> Optional[str]:
        """Validate API key from request headers."""
        
        # If API key is not required, allow all requests
        if not self.api_key_required:
            return None
        
        # Check X-API-Key header first (preferred)
        api_key = request.headers.get("X-API-Key")
        
        # Fallback to Authorization Bearer token
        if not api_key and credentials:
            api_key = credentials.credentials
        
        # No API key provided
        if not api_key:
            logger.warning(f"Missing API key from {request.client.host}")
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="API key required. Please provide X-API-Key header or Authorization Bearer token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Invalid API key
        if api_key != self.api_key:
            logger.warning(f"Invalid API key from {request.client.host}")
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Invalid API key.",
            )
        
        return api_key


# Global instance
api_key_auth = APIKeyAuth()


def get_api_key_auth() -> APIKeyAuth:
    """Get the API key authentication instance."""
    return api_key_auth


# Optional dependency for endpoints that may or may not require authentication
async def optional_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[str]:
    """Optional API key validation - doesn't raise exception if not required."""
    try:
        return await api_key_auth(request, credentials)
    except HTTPException:
        if api_key_auth.api_key_required:
            raise
        return None


# Middleware for automatic API key checking on all routes
class APIKeyMiddleware:
    """Middleware to check API key on all protected routes."""
    
    def __init__(self, app, exclude_paths: list = None):
        self.app = app
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/metrics",
            "/"
        ]
        self.auth = APIKeyAuth()
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope["path"]
            
            # Skip authentication for excluded paths
            if any(path.startswith(excluded) for excluded in self.exclude_paths):
                await self.app(scope, receive, send)
                return
            
            # Only check if API key is required
            if self.auth.api_key_required:
                headers = dict(scope["headers"])
                
                # Check for API key in headers
                api_key = None
                if b"x-api-key" in headers:
                    api_key = headers[b"x-api-key"].decode()
                elif b"authorization" in headers:
                    auth_header = headers[b"authorization"].decode()
                    if auth_header.startswith("Bearer "):
                        api_key = auth_header[7:]
                
                # Validate API key
                if not api_key or api_key != self.auth.api_key:
                    response = {
                        "status": 401 if not api_key else 403,
                        "headers": [(b"content-type", b"application/json")],
                    }
                    
                    await send({
                        "type": "http.response.start",
                        **response
                    })
                    
                    error_message = (
                        b'{"detail":"API key required. Please provide X-API-Key header or Authorization Bearer token."}'
                        if not api_key else
                        b'{"detail":"Invalid API key."}'
                    )
                    
                    await send({
                        "type": "http.response.body",
                        "body": error_message
                    })
                    return
        
        await self.app(scope, receive, send)