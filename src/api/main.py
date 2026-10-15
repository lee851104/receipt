"""The app uvicorn serves. Run from the repository root:

    .venv/Scripts/python.exe -m uvicorn src.api.main:app --reload
"""
import os
import sys

from dotenv import load_dotenv

from .app import ROOT, create_app
from .settings import Settings

load_dotenv(ROOT / ".env")
try:
    settings = Settings.from_env(os.environ)
    app = create_app(settings)
except ValueError as error:  # a missing secret, a bad setting or a model not there yet: one line, not a traceback
    sys.exit(f"error: {error}")
if settings.demo_mode:
    print("DEMO_MODE=1: anyone who can reach this server can log in as a demo user without a password. "
          "Keep uvicorn on its default 127.0.0.1; never add --host 0.0.0.0 while it is on.", file=sys.stderr)
