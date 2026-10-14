import sys
import os
import traceback
from pathlib import Path
import urllib.parse

# 1. Ensure project root and backend folder are in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
for directory in (str(BASE_DIR), str(BASE_DIR / "backend")):
    if directory not in sys.path:
        sys.path.insert(0, directory)

# 2. Safely import Flask application
app_instance = None
init_error = None

try:
    try:
        from backend.app import app as app_instance
    except ImportError:
        from app import app as app_instance
except Exception:
    init_error = traceback.format_exc()
    print("FATAL: Failed to import backend app:\n" + init_error, file=sys.stderr)

if app_instance is None:
    from flask import Flask, jsonify
    fallback_app = Flask(__name__)

    @fallback_app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    @fallback_app.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    def error_route(path=""):
        return jsonify({
            "success": False,
            "error": "InitializationError",
            "message": "Backend Flask application failed to initialize.",
            "details": init_error
        }), 500

    flask_app = fallback_app
else:
    flask_app = app_instance


class VercelPathFix:
    """
    WSGI Middleware for Vercel Serverless Functions.
    Restores original client requested path and cleans query parameters
    when Vercel rewrites routes to /api/index.py.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        try:
            path = environ.get("PATH_INFO", "")

            # If Vercel passed /api/index.py, /index.py, /api/index, /api, or empty path
            if "index.py" in path or "index" in path or path in ("/api", "/api/", ""):
                qs = urllib.parse.parse_qs(environ.get("QUERY_STRING", ""))
                route = qs.get("__vercel_route__", [""])[0]

                # 1. Use __vercel_route__ query parameter if present
                if route:
                    clean_route = route.lstrip("/")
                    environ["PATH_INFO"] = f"/api/{clean_route}" if clean_route else "/api"
                # 2. Try Vercel's standard x-matched-path header (e.g. /api/login)
                elif environ.get("HTTP_X_MATCHED_PATH") and "index" not in environ.get("HTTP_X_MATCHED_PATH"):
                    environ["PATH_INFO"] = environ.get("HTTP_X_MATCHED_PATH")
                # 3. Try RAW_URI or REQUEST_URI
                elif environ.get("RAW_URI") and "index" not in environ.get("RAW_URI"):
                    environ["PATH_INFO"] = environ.get("RAW_URI").split("?")[0]
                elif environ.get("REQUEST_URI") and "index" not in environ.get("REQUEST_URI"):
                    environ["PATH_INFO"] = environ.get("REQUEST_URI").split("?")[0]

            # Clean __vercel_route__ out of QUERY_STRING so Flask request.args remains clean
            raw_qs = environ.get("QUERY_STRING", "")
            if "__vercel_route__=" in raw_qs:
                clean_parts = [p for p in raw_qs.split("&") if not p.startswith("__vercel_route__=")]
                environ["QUERY_STRING"] = "&".join(clean_parts)

            return self.wsgi_app(environ, start_response)
        except Exception:
            err = traceback.format_exc()
            print("FATAL: WSGI execution error:\n" + err, file=sys.stderr)
            import json
            status = "500 Internal Server Error"
            headers = [
                ("Content-Type", "application/json"),
                ("Access-Control-Allow-Origin", "*"),
                ("Access-Control-Allow-Headers", "Content-Type, Authorization"),
            ]
            start_response(status, headers)
            return [json.dumps({
                "success": False,
                "error": "WSGIExecutionError",
                "details": err
            }).encode("utf-8")]


# Apply WSGI path fix middleware
fixed_wsgi = VercelPathFix(flask_app.wsgi_app)
flask_app.wsgi_app = fixed_wsgi


class HybridApp:
    """
    Universal Application wrapper supporting both WSGI and ASGI.
    Automatically detects caller protocol (WSGI: 2 args, ASGI: 3 args)
    so Vercel Python runtimes (FastAPI or Flask presets) can invoke it seamlessly.
    """
    def __init__(self, wsgi_app, flask_obj):
        self.wsgi_app = wsgi_app
        self.flask_obj = flask_obj
        try:
            from a2wsgi import WSGIMiddleware
            self.asgi_app = WSGIMiddleware(wsgi_app)
        except Exception:
            self.asgi_app = None

    def __call__(self, *args, **kwargs):
        # WSGI: (environ, start_response)
        if len(args) == 2 and callable(args[1]):
            return self.wsgi_app(*args, **kwargs)
        # ASGI: (scope, receive, send)
        if len(args) == 3 and self.asgi_app is not None:
            return self.asgi_app(*args, **kwargs)
        # Fallback to WSGI
        return self.wsgi_app(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.flask_obj, name)


app = HybridApp(fixed_wsgi, flask_app)
handler = app
