import sys
from pathlib import Path

# Add project root and backend folder to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "backend"))

from backend.app import app

# Vercel WSGI entry point
# Vercel Python runtime detects the Flask "app" object automatically
