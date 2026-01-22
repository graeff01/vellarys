#!/bin/bash

echo "=== Velaris Backend Startup ==="
echo "Running database migrations..."

# Try to run migrations
if alembic upgrade head; then
    echo "Migrations completed successfully!"
else
    echo "WARNING: Migrations failed. Checking current state..."

    # Show current revision
    alembic current || true

    # If tables already exist, stamp with head to skip
    echo "Attempting to stamp database with current head..."
    alembic stamp head || true

    echo "Continuing with startup despite migration issues..."
fi

echo ""
echo "Starting Uvicorn server..."
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000
