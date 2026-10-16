"""What start.bat runs: a .env with a fresh secret when there is none, the demo users, the v2 pages opened in the
browser once the server answers, and the server itself on this computer only. Run from the repository root:

    .venv/Scripts/python.exe -m src.api.launch
"""
import secrets
import threading
import time
import urllib.request
import webbrowser

from .db import ROOT

HOST, PORT = "127.0.0.1", 8000  # this computer only: DEMO_MODE lets anyone log in as a demo user
PAGE = f"http://{HOST}:{PORT}/web/"
HEALTH = f"http://{HOST}:{PORT}/api/health"


def ensure_env(root):
    """Write root/.env from .env.example with a new JWT_SECRET when there is no .env; True when it did. An existing
    .env is never read or changed."""
    env = root / ".env"
    if env.exists():
        return False
    lines = (root / ".env.example").read_text(encoding="utf-8").splitlines()
    secret = secrets.token_urlsafe(32)
    env.write_text("".join((f"JWT_SECRET={secret}" if line.startswith("JWT_SECRET=") else line) + "\n" for line in lines),
                   encoding="utf-8")
    return True


def answers(url):
    """Whether url answers 200, straight to it: a system proxy would otherwise take 127.0.0.1 too."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=1) as response:
            return response.status == 200
    except OSError:
        return False


def open_when_ready(url=PAGE, health=HEALTH, opener=webbrowser.open, fetch=answers, timeout=60, pause=0.5):
    """Open url once health answers; give up quietly after timeout seconds. True when the page was opened."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if fetch(health):
            opener(url)
            return True
        time.sleep(pause)
    return False


def open_in_background():
    threading.Thread(target=open_when_ready, name="open-browser", daemon=True).start()


def seed_demo():
    from . import seed  # reads .env itself, so only after ensure_env
    seed.main()


def main(root=ROOT):
    if ensure_env(root):
        print("已建立 .env（含一組新的 JWT_SECRET）；要改設定請編輯 .env 後重新啟動")
    seed_demo()
    open_in_background()
    import uvicorn
    uvicorn.run("src.api.main:app", host=HOST, port=PORT)


if __name__ == "__main__":
    main()
