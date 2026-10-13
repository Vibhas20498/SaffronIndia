import sys
from pathlib import Path
import urllib.parse

# Add project root and backend folder to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "backend"))

from backend.app import app


class VercelPathFix:
    """
    WSGI Middleware for Vercel Serverless Functions.
    Restores the original client requested path when Vercel rewrites route to /api/index.py.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        
        # If Vercel rewrote the path to /api/index.py, /index.py, or base /api
        if "index.py" in path or path in ("/api", "/api/"):
            # 1. Try Vercel's standard x-matched-path header (e.g. /api/login)
            matched = environ.get("HTTP_X_MATCHED_PATH")
            if matched and "index.py" not in matched:
                environ["PATH_INFO"] = matched
            # 2. Try query parameter __vercel_route__ passed from vercel.json
            elif "__vercel_route__=" in environ.get("QUERY_STRING", ""):
                qs = urllib.parse.parse_qs(environ.get("QUERY_STRING", ""))
                route = qs.get("__vercel_route__", [""])[0]
                if route:
                    environ["PATH_INFO"] = f"/api/{route.lstrip('/')}"
            # 3. Try RAW_URI or REQUEST_URI
            elif environ.get("RAW_URI") and "index.py" not in environ.get("RAW_URI"):
                environ["PATH_INFO"] = environ["RAW_URI"].split("?")[0]
            elif environ.get("REQUEST_URI") and "index.py" not in environ.get("REQUEST_URI"):
                environ["PATH_INFO"] = environ["REQUEST_URI"].split("?")[0]

        # If PATH_INFO is e.g. /login (without /api prefix), normalize to /api/login
        cur_path = environ.get("PATH_INFO", "")
        if cur_path and not cur_path.startswith("/api/") and cur_path != "/":
            environ["PATH_INFO"] = f"/api/{cur_path.lstrip('/')}"

        return self.wsgi_app(environ, start_response)


# Apply middleware to the Flask WSGI application
app.wsgi_app = VercelPathFix(app.wsgi_app)
