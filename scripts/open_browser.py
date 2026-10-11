"""Open the app in the browser once the server is up.

Polls /api/health so the browser never opens on a port that isn't ours yet.

Usage:
    python scripts/open_browser.py 8642
"""
import json
import sys
import time
import urllib.request
import webbrowser

port = sys.argv[1] if len(sys.argv) > 1 else "8642"
base = f"http://127.0.0.1:{port}"

for _ in range(60):
    try:
        with urllib.request.urlopen(f"{base}/api/health", timeout=1) as response:
            if json.load(response).get("model_loaded"):
                webbrowser.open(base)
                break
    except (OSError, ValueError):
        pass
    time.sleep(1)
