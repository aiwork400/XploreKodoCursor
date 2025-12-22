"""
Agency App Module - FastAPI Application Entry Point

This module provides a convenient import path for uvicorn:
    uvicorn agency.app:app

The actual FastAPI app is defined in api/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent.resolve())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the FastAPI app from api/main.py
from api.main import app

__all__ = ["app"]

