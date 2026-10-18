"""What start.bat runs: a .env with a fresh secret when there is none, the demo users (when they cannot be put in, a
one-line warning and the launch goes on), the v2 pages opened in the browser once the server answers, and the
server itself on this computer only. Run from the repository root:

    .venv/Scripts/python.exe -m src.api.launch
"""
import os
import secrets
import threading
import time
import urllib.request
import webbrowser

from dotenv import load_dotenv

from .db import ROOT, init_db, make_engine
from .jobs import fail_unfinished
from .settings import Settings

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
    """Free the demo job an interrupted seed left, then run role 3's seed, which refuses to run over one."""
    # Settings and database exactly as seed.main finds them: the root .env never overrides a variable already set.
    load_dotenv(ROOT / ".env")
    settings = Settings.from_env(os.environ)  # a bad setting is a ValueError, which main() turns into one line
    engine = make_engine(settings.database_url)
    try:
        init_db(engine)
        # Only the demo users' jobs, unlike the container (the only process on its volume, which fails every one):
        # another server may already be running on this database, and a real user's unfinished job there is alive.
        # A demo user cannot upload or delete a month, so their unfinished job is a stopped seed's leftover, and the
        # seed would refuse over it ("Stop unfinished demo jobs before seeding") until the server's own start-up. It
        # may instead belong to a seed running right now in another start.bat window or a manual
        # `python -m src.api.seed`, which this fails too; the damage is limited to fictional demo rows, which the
        # next run's completeness check rewrites.
        fail_unfinished(engine, demo_only=True)
    finally:
        engine.dispose()
    from . import seed  # seed.main loads .env again on its own; importing it lazily keeps launch light
    seed.main()


def reason_for(error, limit=160):
    """One short line on why a seed stopped: SystemExit's message (seed.main's "error: ..."), else the exception's
    type and message. No traceback. A long message (one clash per demo user) is cut in the middle: the seed ends it
    with what to do ("Delete the database file and run the seed again."), which must not be lost."""
    if isinstance(error, SystemExit):
        text = error.code if isinstance(error.code, str) else "the seed stopped"
    else:
        text = f"{type(error).__name__}: {error}" if str(error) else type(error).__name__
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    side = (limit - 3) // 2
    return text[:side] + " … " + text[-side:]


def main(root=ROOT):
    if ensure_env(root):
        print("已建立 .env（含一組新的 JWT_SECRET）；要改設定請編輯 .env 後重新啟動")
    # The demo users are optional: a seed that refuses (a bad setting, a database that no longer matches the demo list)
    # or breaks must not keep a person's own accounts and data from starting. A bad setting stops the server itself,
    # when the app loads it. SystemExit is no Exception, so it is named; Ctrl+C (KeyboardInterrupt) still stops here.
    try:
        seed_demo()
    except (SystemExit, Exception) as error:
        print(f"示範帳號沒有更新：{reason_for(error)}；繼續啟動伺服器")
    open_in_background()
    import uvicorn
    uvicorn.run("src.api.main:app", host=HOST, port=PORT)


if __name__ == "__main__":
    main()
