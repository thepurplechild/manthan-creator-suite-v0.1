# /app/serve.py  (copied from backend/serve.py by the Dockerfile)
import os
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app:app",  # module:function — now valid because app.py is at /app/app.py
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8080")),
        log_level="info",
    )

