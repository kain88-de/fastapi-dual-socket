#!/usr/bin/env python3
"""
Unified server startup for FastAPI dual socket demo.

Usage:
    uv run server           # Start development server  
    uv run server --prod    # Start production server

This replaces all the shell scripts with a single Python command.
"""

import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import uvicorn


def cleanup_processes():
    """Clean up any existing processes and files"""
    print("🧹 Cleaning up existing processes...")
    
    # Kill existing processes
    subprocess.run(["pkill", "-f", "gunicorn.*src.production"], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-f", "python.*admin_service"], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Clean up files
    files_to_remove = [
        "/tmp/fastapi-local.sock",
        "/tmp/fastapi-admin.sock", 
        "/tmp/fastapi-dual-socket.db",
        "/tmp/admin-service.pid",
        "/tmp/gunicorn.pid"
    ]
    
    for file_path in files_to_remove:
        try:
            Path(file_path).unlink(missing_ok=True)
        except:
            pass
    
    time.sleep(2)  # Wait for cleanup


def check_port_available(port: int = 8000) -> bool:
    """Check if port is available"""
    try:
        result = subprocess.run(
            ["netstat", "-tlnp"], 
            capture_output=True, text=True, timeout=10
        )
        return f":{port} " not in result.stdout
    except:
        return True


def start_development():
    """Start development server (original dual server)"""
    print("🚀 Starting Development Server")
    print("=" * 35)
    print("- Public API: http://0.0.0.0:8000")
    print("- Admin API: /tmp/fastapi-local.sock")
    print()
    
    cleanup_processes()
    
    # Import here to avoid import issues
    from .dual_server import run_dual_servers
    
    try:
        asyncio.run(run_dual_servers())
    except KeyboardInterrupt:
        print("\n👋 Development server stopped")
        cleanup_processes()


def start_production():
    """Start production server"""
    print("🚀 Starting Production Server")
    print("=" * 34)
    
    cleanup_processes()
    
    if not check_port_available(8000):
        print("❌ Port 8000 is in use. Please stop other services.")
        sys.exit(1)
    
    # Configuration
    workers = int(os.environ.get("WORKERS", "1"))  # Default to 1 for dual socket
    host = os.environ.get("HOST", "0.0.0.0") 
    port = int(os.environ.get("PORT", "8000"))
    
    if workers > 1:
        print("⚠️  Note: Multiple workers don't work with dual sockets (Unix socket conflict)")
        print("   Using single worker for dual socket support")
        workers = 1
    
    print(f"- Workers: {workers}")  
    print(f"- Public API: http://{host}:{port}")
    print(f"- Admin API: /tmp/fastapi-local.sock")
    print()
    
    # Setup signal handling
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down production server...")
        cleanup_processes()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🌍 Starting production server with dual sockets...")
    try:
        # For production, just run the dual server approach directly
        # This is the simplest and most reliable approach
        from .dual_server import run_dual_servers
        asyncio.run(run_dual_servers())
    except KeyboardInterrupt:
        pass
    finally:
        print("\n🛑 Shutting down...")
        cleanup_processes()


def main():
    """Main entry point"""
    # Check for production flag
    if "--prod" in sys.argv or "--production" in sys.argv:
        start_production()
    elif "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        print("Options:")
        print("  --prod, --production    Start production server")
        print("  --help, -h             Show this help")
    else:
        start_development()


if __name__ == "__main__":
    main()