.PHONY: help dev test test-public test-local clean install

help: ## Show this help message
	@echo "FastAPI Dual Socket Demo"
	@echo "========================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies with uv
	uv sync

dev: ## Run the dual server (TCP + Unix socket)
	uv run python main.py

clean: ## Clean up socket files and cache
	rm -f /tmp/fastapi-local.sock
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