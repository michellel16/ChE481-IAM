import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend"))

from app import server  # noqa: E402 — used by gunicorn as wsgi:server
