.PHONY: help dev test test-public test-local clean install prod prod-test prod-stop admin-service

help: ## Show this help message
	@echo "FastAPI Dual Socket Demo"
	@echo "========================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies with uv
	uv sync

dev: ## Run the development server (TCP + Unix socket)
	uv run server

clean: ## Clean up socket files and cache
	rm -f /tmp/fastapi-local.sock /tmp/fastapi-dual-socket-admin-*.sock
	rm -f /tmp/gunicorn.pid /tmp/admin-service.pid
	rm -f /tmp/fastapi-dual-socket.db
	rm -rf __pycache__ src/__pycache__ .pytest_cache
	find . -name "*.pyc" -delete

test: ## Run all tests
	$(MAKE) test-setup
	$(MAKE) test-public
	$(MAKE) test-local
	$(MAKE) clean

test-setup: ## Start the server in background for testing
	@echo "🚀 Starting dual server for testing..."
	uv run python main.py &
	@echo $$! > server.pid
	@sleep 3  # Wait for servers to start

test-public: ## Test the public API (TCP)
	@echo "\n🌍 Testing Public API (TCP)..."
	@echo "Health check:"
	curl -s http://localhost:8000/health | jq '.' || echo "jq not installed, raw response above"
	@echo "\nGet data:"
	curl -s http://localhost:8000/data | jq '.' || echo "jq not installed, raw response above"
	@echo "\nPost data:"
	curl -s -X POST http://localhost:8000/data \
		-H "Content-Type: application/json" \
		-d '{"key": "public_key", "value": "public_value"}' | jq '.' || echo "jq not installed, raw response above"
	@echo "\nGet data again:"
	curl -s http://localhost:8000/data | jq '.' || echo "jq not installed, raw response above"

test-local: ## Test the local API (Unix socket)
	@echo "\n🔒 Testing Local API (Unix socket)..."
	@echo "Admin status:"
	curl -s --unix-socket /tmp/fastapi-local.sock http://localhost/admin/status | jq '.' || echo "jq not installed, raw response above"
	@echo "\nGet all data (including private):"
	curl -s --unix-socket /tmp/fastapi-local.sock http://localhost/admin/data/all | jq '.' || echo "jq not installed, raw response above"
	@echo "\nPost private data:"
	curl -s --unix-socket /tmp/fastapi-local.sock http://localhost/admin/data \
		-H "Content-Type: application/json" \
		-d '{"key": "_private_key", "value": "secret_value"}' -X POST | jq '.' || echo "jq not installed, raw response above"
	@echo "\nGet metrics:"
	curl -s --unix-socket /tmp/fastapi-local.sock http://localhost/admin/metrics | jq '.' || echo "jq not installed, raw response above"

stop-test: ## Stop the test server
	@if [ -f server.pid ]; then \
		echo "⏹️  Stopping test server..."; \
		kill `cat server.pid` 2>/dev/null || true; \
		rm -f server.pid; \
	fi
	$(MAKE) clean

demo: ## Run a full demo (start server, test, stop)
	@echo "🎬 Running FastAPI Dual Socket Demo"
	@echo "===================================="
	$(MAKE) test-setup
	sleep 2
	$(MAKE) test-public
	$(MAKE) test-local
	@echo "\n✅ Demo completed!"
	$(MAKE) stop-test

logs: ## Show recent logs (if running via systemd or similar)
	tail -f /tmp/fastapi-dual-socket.log 2>/dev/null || echo "No log file found"

check-deps: ## Check if required tools are available
	@echo "🔍 Checking dependencies..."
	@command -v curl >/dev/null 2>&1 || echo "❌ curl not found - required for testing"
	@command -v jq >/dev/null 2>&1 || echo "⚠️  jq not found - JSON output will be raw"
	@command -v uv >/dev/null 2>&1 || echo "❌ uv not found - required for running"
	@echo "✅ Dependency check complete"

# Production commands
prod: ## Start production server with Gunicorn
	uv run server --prod

prod-stop: ## Stop production server
	@echo "⏹️  Stopping production servers..."
	@pkill -f "gunicorn.*src.production" 2>/dev/null || true
	@pkill -f "python.*admin_service" 2>/dev/null || true
	@if [ -f /tmp/admin-service.pid ]; then \
		kill -TERM `cat /tmp/admin-service.pid` 2>/dev/null || true; \
		rm -f /tmp/admin-service.pid; \
	fi
	$(MAKE) clean


test-prod: ## Test production deployment
	@echo "🧪 Production Test"
	@echo "=================="
	@pkill -f "gunicorn.*src.production" 2>/dev/null || true
	@rm -f /tmp/fastapi-dual-socket-admin-*.sock /tmp/fastapi-dual-socket.db
	@sleep 2
	@echo "Starting production server..."
	@timeout 30 uv run server --prod > /tmp/prod-test.log 2>&1 &
	@echo $$! > prod-test.pid
	@sleep 6  # Wait for startup
	@echo "Running tests..."
	@uv run python test-production.py || echo "Tests completed (some may have failed)"
	@echo "Stopping servers..."
	@if [ -f prod-test.pid ]; then \
		kill -TERM `cat prod-test.pid` 2>/dev/null || true; \
		sleep 2; \
		kill -KILL `cat prod-test.pid` 2>/dev/null || true; \
		rm -f prod-test.pid; \
	fi
	@pkill -f "gunicorn.*src.production" 2>/dev/null || true
	@sleep 1
	$(MAKE) clean
	@echo "✅ Test completed and cleaned up"