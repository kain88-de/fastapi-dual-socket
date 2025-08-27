"""
Production configuration for FastAPI dual socket demo.
Uses the same dual server approach as development, just with health checks.
"""

import os
from .public_api import app as public_app

# Add health check endpoints for production
@public_app.get("/health/ready")
def readiness_check():
    """Health check endpoint for load balancers"""
    return {"status": "ready", "service": "fastapi-dual-socket"}

@public_app.get("/health/live") 
def liveness_check():
    """Liveness check endpoint for orchestrators"""
    return {"status": "alive", "service": "fastapi-dual-socket"}

# Environment-based configuration
if os.getenv("ENVIRONMENT") == "production":
    import logging
    logging.basicConfig(level=logging.INFO)

# Export for use with Uvicorn
application = public_app