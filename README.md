# FastAPI Dual Socket Demo

A demonstration of running FastAPI with both public (TCP) and local-only (Unix socket) APIs in the same process.

## Architecture

- **Public API** (TCP): World-accessible endpoints on port 8000
- **Local API** (Unix socket): Admin-only endpoints via `/tmp/fastapi-local.sock`
- **Shared State**: Both APIs share the same data store

## Features

### Public API (TCP - Port 8000)
- `GET /` - Health check
- `GET /data` - Get public data (filtered)
- `POST /data` - Set data (restricted)
- `GET /health` - System health

### Local API (Unix Socket)
- `GET /admin/metrics` - Detailed system metrics
- `GET /admin/data/all` - All data including private
- `POST /admin/data` - Set any data including private keys
- `DELETE /admin/data/reset` - Reset all data
- `GET /admin/status` - Detailed admin status

## Quick Start

```bash
# Install dependencies
make install

# Run the dual server
make dev

# Run full demo (in another terminal)
make demo
```

## Testing

The Makefile provides comprehensive testing commands:

- `make test` - Full test suite
- `make test-public` - Test public API only  
- `make test-local` - Test local API only
- `make demo` - Complete demo with server lifecycle

## Security Model

- **Public API**: Filters sensitive data, prevents private key access
- **Local API**: Full access to all data and admin functions
- **Network isolation**: Local API only accessible via Unix socket

## Implementation Notes

- Single process using `uvicorn.Server` and `asyncio.gather()`
- Automatic socket cleanup on shutdown
- Shared business logic between both APIs
- Graceful shutdown handling