#!/bin/bash
set -e  # Exit on error

echo "=== Velaris Backend Startup ==="

# 1. APPLY FIX (uma vez só)
echo "🔧 Checking if database fix is needed..."
if [ -f "run_fix_once.sh" ]; then
    bash run_fix_once.sh || echo "⚠️ Fix script failed or already applied"
fi

echo ""
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
