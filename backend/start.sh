#!/bin/bash
set -e  # Exit on error

echo "=== Velaris Backend Startup ==="
echo "Running database migrations..."

# Show current revision before upgrade
echo "Current database revision:"
alembic current || echo "No current revision"

echo ""
echo "Upgrading to head..."

# Run migrations
alembic upgrade head

echo "✅ Migrations completed successfully!"

echo ""
echo "Starting Uvicorn server..."
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000
