import os, sys, traceback
import logging

# Ensure /app is on the path when running in the container
sys.path.insert(0, os.getcwd())

try:
    import app  # noqa: F401  # just to check module import
except Exception as e:
    logging.error("Failed to import app.py")
    traceback.print_exc()
    sys.exit(3)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    # Debug log level so Cloud Run logs show the root cause
    uvicorn.run("app:app", host="0.0.0.0", port=port, log_level="debug")
