import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn


APP_DIR = Path(__file__).parent / "app"
sys.path.insert(0, str(APP_DIR))


def open_browser():
    time.sleep(1.0)
    try:
        webbrowser.open("http://127.0.0.1:7860")
    except Exception:
        pass


if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("🚀 Starting the Corgue workspace...")
    print("👉 Browser address: http://127.0.0.1:7860")
    print("   (Press Ctrl+C to stop the application)")
    print("=" * 65 + "\n")

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("web_app:app", host="127.0.0.1", port=7860, log_level="info")
