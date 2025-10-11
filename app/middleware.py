from fastapi import Request, HTTPException, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# from fastapi.middleware.base import BaseHTTPMiddleware
import time
import logging
from typing import Callable

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers to all responses"""

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), bluetooth=()"
        )

        # Remove server information for security
        if "Server" in response.headers:
            del response.headers["Server"]

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses"""

    async def dispatch(self, request: Request, call_next: Callable):

        print(f"Request Headers: {request.headers}")
        print(f"Request Method: {request.method}")
        print(f"Request URL: {request.url}")
        start_time = time.time()

        # Log request
        logger.info(f"Request: {request.method} {request.url}")

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Log response
        logger.info(f"Response: {response.status_code} - {process_time:.4f}s")

        # Add process time to response headers
        response.headers["X-Process-Time"] = str(process_time)
        print(f"Response Headers: {response.headers}")
        print(f"Response Status: {response.status_code}")

        # Handle different response types for logging
        try:
            if hasattr(response, 'body') and response.body is not None:
                print(f"Response Body: {response.body}")
            else:
                print("Response Body: [Streaming or empty response]")
        except Exception as e:
            print(f"Response Body: [Could not read body: {str(e)}]")

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for handling errors gracefully"""

    async def dispatch(self, request: Request, call_next: Callable):
        try:
            response = await call_next(request)
            return response
        except HTTPException:
            # Re-raise HTTP exceptions (these are handled by FastAPI)
            raise
        except Exception as e:
            # Log unexpected errors
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)

            # Return a generic error response
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "An unexpected error occurred",
                    "error": "Internal Server Error",
                },
            )
