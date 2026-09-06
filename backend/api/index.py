"""
Vercel Serverless Function entrypoint for TerraSense FastAPI backend.
Exposes the FastAPI `app` instance from backend/main.py.
"""
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
for _p in (str(_BACKEND_DIR), str(_REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from main import app
