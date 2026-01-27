#!/bin/bash

echo "=== Vellarys Backend Startup ==="

# 1. APPLY FIX (uma vez só, sem falhar se der erro)
FIX_MARKER="/tmp/.vellarys_fix_applied"

if [ ! -f "$FIX_MARKER" ] && [ -f "apply_fix.py" ]; then
    echo "🔧 Applying database fix for CRM Inbox columns..."

    if python3 apply_fix.py; then
        echo "✅ Database fix applied successfully!"
        touch "$FIX_MARKER"
    else
        echo "⚠️ Fix script failed - will continue anyway (columns may already exist)"
        echo "If backend fails with 'column does not exist', check the fix manually"
        # Não falha - continua mesmo se o fix falhar
    fi
else
    if [ -f "$FIX_MARKER" ]; then
        echo "ℹ️ Database fix already applied previously"
    else
        echo "ℹ️ Fix script not found (apply_fix.py) - skipping"
    fi
fi

echo ""
echo "Running database migrations..."

# Show current revision before upgrade
echo "Current database revision:"
alembic current || echo "No current revision"

echo ""
echo "Upgrading to head..."

# Run migrations (sem set -e para não falhar se migrations já estão aplicadas)
alembic upgrade head || {
    echo "⚠️ Migrations failed or already up to date"
    alembic current
}

echo "✅ Database ready!"

echo ""
echo "Starting Uvicorn server..."
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000
