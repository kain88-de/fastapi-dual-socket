"""
Separate admin service for Unix socket in production.

Since Gunicorn workers are separate processes and can't share a single Unix socket,
we need to run the admin API as a separate service.
"""

import asyncio
import uvicorn
from pathlib import Path
from .local_api import app as local_app

async def run_admin_service():
    """Run the admin service on Unix socket"""
    socket_path = "/tmp/fastapi-admin.sock"
    
    # Remove existing socket
    Path(socket_path).unlink(missing_ok=True)
    
    # Configure admin server
    config = uvicorn.Config(
        app=local_app,
        uds=socket_path,
        log_level="info",
        access_log=True
    )
    
    server = uvicorn.Server(config)
    
    print(f"🔒 Admin API starting on: {socket_path}")
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        print("\n⏹️  Shutting down admin service...")
        Path(socket_path).unlink(missing_ok=True)

def main():
    """Entry point for admin service"""
    try:
        asyncio.run(run_admin_service())
    except KeyboardInterrupt:
        print("\n👋 Admin service stopped")

if __name__ == "__main__":
    main()