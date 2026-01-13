import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Mock env vars because main.py loads settings on module level
os.environ["DATABASE_URL"] = "postgresql+asyncpg://user:pass@localhost/db"
os.environ["SECRET_KEY"] = "mock-secret-key-for-test"
os.environ["OPENAI_API_KEY"] = "mock-openai-key"

try:
    print("Checking imports...")
    from src.infrastructure import logging_config
    print("Logging config imported successfully.")
    
    from src.api import main
    print("Main module imported successfully.")
    
    # Check if formatting works
    import logging
    import json
    
    formatter = logging_config.JSONFormatter()
    record = logging.LogRecord("test", logging.INFO, "path", 1, "Verify log format", None, None)
    formatted = formatter.format(record)
    data = json.loads(formatted)
    
    if data['message'] == "Verify log format":
        print("JSON Formatter working as expected.")
    else:
        print("JSON Formatter failed.")
        sys.exit(1)

    print("ALL CHECKS PASSED")

except Exception as e:
    print(f"VERIFICATION FAILED: {e}")
    sys.exit(1)
