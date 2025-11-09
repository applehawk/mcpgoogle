# Dockerfile for MCP Google Hub
# One container per user for complete isolation

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/
COPY examples/ ./examples/
COPY docker-entrypoint.sh /usr/local/bin/

# Make entrypoint executable
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Environment variables will be passed at runtime
ENV AUTH_MODE=oma_backend
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose port (will be mapped differently for each user)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use entrypoint to obtain JWT token automatically
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Run MCP Hub server
# Use --host to bind to all interfaces for Docker port mapping
CMD ["fastmcp", "run", "src/server.py", "--host", "0.0.0.0", "--port", "8000", "--transport", "http"]
