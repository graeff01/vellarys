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

# Run migrations - If multiple heads exist, merge them first
alembic upgrade heads || {
    echo "⚠️ Multiple heads detected, trying merge..."
    alembic upgrade 20260128_merge_heads || {
        echo "⚠️ Migrations failed or already up to date"
        alembic current
    }
}

echo "✅ Database ready!"

# 3. UPDATE PLAN FEATURES (uma vez só)
FEATURES_MARKER="/tmp/.vellarys_features_updated"

if [ ! -f "$FEATURES_MARKER" ] && [ -f "scripts/update_plan_features.py" ]; then
    echo ""
    echo "🔧 Updating plan features (copilot, simulator, reports, export)..."

    if python3 scripts/update_plan_features.py; then
        echo "✅ Plan features updated successfully!"
        touch "$FEATURES_MARKER"
    else
        echo "⚠️ Feature update failed - will continue anyway"
        echo "Features may need manual update"
        # Não falha - continua mesmo se der erro
    fi
else
    if [ -f "$FEATURES_MARKER" ]; then
        echo "ℹ️ Plan features already updated previously"
    else
        echo "ℹ️ Feature update script not found - skipping"
    fi
fi

# 4. SEED RESPONSE TEMPLATES (uma vez só)
TEMPLATES_MARKER="/tmp/.vellarys_templates_seeded"

if [ ! -f "$TEMPLATES_MARKER" ] && [ -f "scripts/seed_response_templates.py" ]; then
    echo ""
    echo "🌱 Seeding response templates for sellers..."

    if python3 scripts/seed_response_templates.py; then
        echo "✅ Response templates seeded successfully!"
        touch "$TEMPLATES_MARKER"
    else
        echo "⚠️ Template seed failed - will continue anyway"
        echo "Templates may need manual seeding"
        # Não falha - continua mesmo se der erro
    fi
else
    if [ -f "$TEMPLATES_MARKER" ]; then
        echo "ℹ️ Response templates already seeded previously"
    else
        echo "ℹ️ Template seed script not found - skipping"
    fi
fi

echo ""
echo "Starting Uvicorn server..."
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000
