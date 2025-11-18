.PHONY: help find rm stop start logs build run-local test-health find-all stop-all rm-all

# Extract username from command line arguments
# Usage: make find mr.vasilenko.vlad
USERNAME := $(word 2,$(MAKECMDGOALS))

# Prevent make from treating username as a target
%:
	@:

# Default target - show help
help:
	@echo "MCP Google Hub - Docker Management"
	@echo ""
	@echo "Build commands:"
	@echo "  make build                  - Build latest Docker image"
	@echo ""
	@echo "Container management (per user):"
	@echo "  make find <username>        - Find user's container"
	@echo "  make rm <username>          - Remove user's container"
	@echo "  make stop <username>        - Stop user's container"
	@echo "  make start <username>       - Start user's container"
	@echo "  make logs <username>        - View user's container logs"
	@echo ""
	@echo "Bulk container management:"
	@echo "  make find-all               - Find all mcpgoogle-* containers"
	@echo "  make stop-all               - Stop all mcpgoogle-* containers"
	@echo "  make rm-all                 - Stop and remove all mcpgoogle-* containers"
	@echo ""
	@echo "Examples:"
	@echo "  make find mr.vasilenko.vlad"
	@echo "  make rm mr.vasilenko.vlad"
	@echo "  make stop mr.vasilenko.vlad"
	@echo ""
	@echo "Local development:"
	@echo "  make run-local              - Run server locally (not in Docker)"
	@echo "  make test-health            - Test health endpoint"

# Build the latest Docker image
build:
	@echo "🔨 Building MCP Google Hub image..."
	docker build -t mcpgoogle:latest .
	@echo "✅ Build complete!"

# Find container by username
find:
	@if [ -z "$(USERNAME)" ]; then \
		echo "❌ Error: Username not specified"; \
		echo "Usage: make find <username>"; \
		echo "Example: make find mr.vasilenko.vlad"; \
		exit 1; \
	fi
	@echo "🔍 Searching for container: mcpgoogle-$(USERNAME)"
	@docker ps -a --filter "name=mcpgoogle-$(USERNAME)" --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"

# Remove container by username
rm:
	@if [ -z "$(USERNAME)" ]; then \
		echo "❌ Error: Username not specified"; \
		echo "Usage: make rm <username>"; \
		echo "Example: make rm mr.vasilenko.vlad"; \
		exit 1; \
	fi
	@echo "🗑️  Removing container: mcpgoogle-$(USERNAME)"
	docker container rm -f mcpgoogle-$(USERNAME)
	@echo "✅ Container removed!"

# Stop container by username
stop:
	@if [ -z "$(USERNAME)" ]; then \
		echo "❌ Error: Username not specified"; \
		echo "Usage: make stop <username>"; \
		echo "Example: make stop mr.vasilenko.vlad"; \
		exit 1; \
	fi
	@echo "🛑 Stopping container: mcpgoogle-$(USERNAME)"
	docker container stop mcpgoogle-$(USERNAME)
	@echo "✅ Container stopped!"

# Start container by username
start:
	@if [ -z "$(USERNAME)" ]; then \
		echo "❌ Error: Username not specified"; \
		echo "Usage: make start <username>"; \
		echo "Example: make start mr.vasilenko.vlad"; \
		exit 1; \
	fi
	@echo "▶️  Starting container: mcpgoogle-$(USERNAME)"
	docker container start mcpgoogle-$(USERNAME)
	@echo "✅ Container started!"

# View container logs by username
logs:
	@if [ -z "$(USERNAME)" ]; then \
		echo "❌ Error: Username not specified"; \
		echo "Usage: make logs <username>"; \
		echo "Example: make logs mr.vasilenko.vlad"; \
		exit 1; \
	fi
	@echo "📋 Logs for container: mcpgoogle-$(USERNAME)"
	docker logs -f mcpgoogle-$(USERNAME)

# Run server locally (not in Docker)
run-local:
	@echo "🚀 Starting MCP Google Hub locally..."
	python -m src.server

# Test health endpoint
test-health:
	@echo "🏥 Testing health endpoint..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ Server not responding"

# Find all mcpgoogle-* containers
find-all:
	@echo "🔍 Searching for all mcpgoogle-* containers..."
	@docker ps -a --filter "name=mcpgoogle-" --format "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "No containers found"
	@echo ""
	@CONTAINER_COUNT=$$(docker ps -a --filter "name=mcpgoogle-" --format "{{.Names}}" | wc -l); \
	echo "Total: $$CONTAINER_COUNT container(s)"

# Stop all mcpgoogle-* containers
stop-all:
	@echo "🛑 Stopping all mcpgoogle-* containers..."
	@CONTAINERS=$$(docker ps --filter "name=mcpgoogle-" --format "{{.Names}}"); \
	if [ -z "$$CONTAINERS" ]; then \
		echo "No running containers found"; \
	else \
		echo "$$CONTAINERS" | xargs -r docker stop; \
		echo "✅ All containers stopped!"; \
	fi

# Stop and remove all mcpgoogle-* containers
rm-all:
	@echo "🗑️  Stopping and removing all mcpgoogle-* containers..."
	@CONTAINERS=$$(docker ps -a --filter "name=mcpgoogle-" --format "{{.Names}}"); \
	if [ -z "$$CONTAINERS" ]; then \
		echo "No containers found"; \
	else \
		echo "$$CONTAINERS" | xargs -r docker rm -f; \
		echo "✅ All containers removed!"; \
	fi
