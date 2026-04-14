# =============================================
# security_patch.py
# Sentinel AI CCTV — Security & Privacy Module
# Apply: import this at the top of your main app
# =============================================

import os
import time
from dotenv import load_dotenv
from flask import request

# ── STEP 1: Load secrets from .env ──────────────────────────────────────────
load_dotenv()

API_KEY          = os.getenv("API_KEY")
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Validate that critical secrets are actually set
if not API_KEY:
    raise RuntimeError("API_KEY is not set in .env — refusing to start.")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set in .env — refusing to start.")

# ── STEP 5: Privacy — disable auto face learning ────────────────────────────
AUTO_LEARN_ENABLED = os.getenv("AUTO_LEARN_ENABLED", "False").lower() == "true"

# ── STEP 6: Auto-delete old evidence files ──────────────────────────────────
AUTO_DELETE_SECONDS = int(os.getenv("AUTO_DELETE_SECONDS", "300"))  # default 5 min

def cleanup_old_files(folder: str) -> int:
    """
    Delete files older than AUTO_DELETE_SECONDS from `folder`.
    Returns the number of files deleted.
    Safe no-op if folder doesn't exist.
    """
    if not os.path.isdir(folder):
        return 0

    now = time.time()
    deleted = 0

    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        try:
            if os.path.isfile(path):
                age = now - os.path.getmtime(path)
                if age > AUTO_DELETE_SECONDS:
                    os.remove(path)
                    deleted += 1
        except OSError:
            pass  # file already gone or permission issue — skip

    return deleted


# ── STEP 2: API key authentication middleware ────────────────────────────────
def register_auth(app):
    """
    Call this after creating your Flask app:

        app = Flask(__name__)
        register_auth(app)
    """
    @app.before_request
    def auth():
        public_routes = ["/"]

        if request.path not in public_routes:
            key = (
                request.headers.get("x-api-key")
                or request.args.get("api_key")
            )
            if key != API_KEY:
                return "Unauthorized", 401
