import asyncio
import uvicorn
import sys
from pathlib import Path

from .public_api import app as public_app
from .local_api import app as local_app


async def run_dual_servers():
    """Run both public and local servers in the same process"""

    # Socket path for local API
    socket_path = "/tmp/fastapi-local.sock"

    # Remove existing socket file if it exists
    Path(socket_path).unlink(missing_ok=True)

    # Configure public server (TCP)
    public_config = uvicorn.Config(
        app=public_app, host="0.0.0.0", port=8000, log_level="info", access_log=True
    )
    public_server = uvicorn.Server(public_config)

    # Configure local server (Unix socket)
    local_config = uvicorn.Config(
        app=local_app, uds=socket_path, log_level="info", access_log=True
    )
    local_server = uvicorn.Server(local_config)

    print("🌍 Public API will be available at: http://0.0.0.0:8000")
    print(f"🔒 Local API will be available at: {socket_path}")
    print("Press Ctrl+C to stop both servers")

    try:
        # Run both servers concurrently
        await asyncio.gather(public_server.serve(), local_server.serve())
    except KeyboardInterrupt:
        print("\n⏹️  Shutting down servers...")
        # Cleanup socket file
        Path(socket_path).unlink(missing_ok=True)


def main():
    """Entry point for the dual server"""
    try:
        asyncio.run(run_dual_servers())
    except KeyboardInterrupt:
        print("\n👋 Servers stopped")
        sys.exit(0)


if __name__ == "__main__":
    main()
