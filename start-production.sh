#!/bin/bash

# Simple production startup script - no background processes or complex cleanup
set -e

echo "🚀 Starting FastAPI Production Server"
echo "======================================"

# Kill any existing processes first
echo "🧹 Cleaning existing processes..."
pkill -f "gunicorn.*src.production" 2>/dev/null || true
pkill -f "python.*admin_service" 2>/dev/null || true
rm -f /tmp/fastapi-admin.sock /tmp/fastapi-dual-socket.db
rm -f /tmp/admin-service.pid /tmp/gunicorn.pid
sleep 2

# Check port availability
if netstat -tlnp 2>/dev/null | grep -q ":8000 "; then
    echo "❌ Port 8000 still in use. Manual cleanup may be needed."
    netstat -tlnp | grep ":8000"
    exit 1
fi

# Set environment
export ENVIRONMENT=production
export WORKERS=4  # Fewer workers for testing
export PORT=8000
export HOST=0.0.0.0

echo "Configuration: $WORKERS workers on $HOST:$PORT"

# Start admin service first
echo "🔒 Starting admin service..."
uv run python -m src.admin_service &
ADMIN_PID=$!
echo $ADMIN_PID > /tmp/admin-service.pid

# Wait for admin service to start
sleep 3
if ! kill -0 $ADMIN_PID 2>/dev/null; then
    echo "❌ Admin service failed to start"
    exit 1
fi

echo "✅ Admin service running (PID: $ADMIN_PID)"

# Start Gunicorn
echo "🌍 Starting Gunicorn with $WORKERS workers..."
exec uv run gunicorn src.production:application \
    --config gunicorn.conf.py \
    --bind "$HOST:$PORT" \
    --workers "$WORKERS" \
    --timeout 30 \
    --keep-alive 2 \
    --max-requests 1000