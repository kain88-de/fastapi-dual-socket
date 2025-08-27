"""
Production ASGI application factory for Gunicorn deployment.

This creates separate FastAPI applications that can be served by Gunicorn workers.
Since Gunicorn workers are separate processes, we handle the dual socket architecture differently:
- Public API runs on multiple Gunicorn workers (load balanced)
- Local admin API needs to be handled separately (single Unix socket per machine)
"""

import os
from pathlib import Path
from .public_api import app as public_app
from .local_api import app as local_app

# Public API - this is what Gunicorn will serve
public_application = public_app

# For local admin API in production, you have a few options:

def create_local_admin_app():
    """
    Factory for local admin API.
    In production, this would typically run as a separate service.
    """
    return local_app

# Environment-based configuration
def configure_for_environment():
    """Configure applications based on environment variables"""
    
    # Configure logging
    if os.getenv("ENVIRONMENT") == "production":
        import logging
        logging.basicConfig(level=logging.INFO)
        
    # Configure CORS if needed
    if os.getenv("ENABLE_CORS", "false").lower() == "true":
        from fastapi.middleware.cors import CORSMiddleware
        
        allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
        if allowed_origins:
            public_app.add_middleware(
                CORSMiddleware,
                allow_origins=allowed_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
    
    return public_app

# Initialize the application
application = configure_for_environment()

# Health check for load balancer
@public_app.get("/health/ready")
def readiness_check():
    """Kubernetes/Docker health check endpoint"""
    return {"status": "ready", "service": "fastapi-dual-socket"}

@public_app.get("/health/live") 
def liveness_check():
    """Kubernetes/Docker liveness check endpoint"""
    return {"status": "alive", "service": "fastapi-dual-socket"}