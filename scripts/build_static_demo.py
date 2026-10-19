"""Build the static v2 demo for GitHub Pages (https://lee851104.github.io/receipt/demo/) from a running demo server.

    .venv/Scripts/python.exe -m scripts.build_static_demo [--server http://127.0.0.1:8000] [--out demo]

Start the server first (start.bat, with DEMO_MODE=1 and the 300 demo users seeded). The script logs in as one
fictional demo user per persona, records every answer the v2 pages ask for (profile, account, the similar and
complementary lists for each range, and the explain of everyone those lists show), and writes them to
static-demo-data.js next to a copy of src/web_v2. scripts/static_demo_api.js answers the pages' /api requests from that
file, so no server is needed; a demo user cannot upload or change anything, and the static page says so. Only demo
users are ever recorded: the script stops if an answer says otherwise. src/web_v2 itself is not changed.
"""
import argparse
import json
import shutil
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/web_v2"
SHIM = ROOT / "scripts/static_demo_api.js"
MARKER = "static-demo-api.js"
PICK = "B"  # 咖啡上班族 B is the user in the README animation; every persona has a B
KINDS = ("similar", "opposite")
SCOPES = ("all", "district", "city", "region")

NOTICE = (
    '<p class="static-note">這是<strong>靜態展示版</strong>：資料是預先錄好的虛構示範帳號，'
    '選一位就能看月報、配對與連線圖。上傳發票、註冊等完整功能請在本機啟動，見 '
    '<a href="https://github.com/lee851104/receipt#6-快速開始">README 快速開始</a>。</p>'
)
STYLE = (
    "<style>/* static demo: only the demo users can sign in */"
    ".auth-tabs,#login-form,#register-form,#auth-title,#auth-subtitle,#demo-panel .divider{display:none!important}"
    ".static-note{margin:0 0 18px;line-height:1.7;color:var(--muted,#b9b4ae)}"
    ".static-note a{color:inherit;text-decoration:underline}</style>"
)
# Each edit names text that must be in the copied page exactly once, so a changed source stops the build.
EDITS = {
    "index.html": [
        ('<script defer src="./feedback.js', '<script src="./static-demo-data.js"></script>'
                                             f'<script src="./{MARKER}"></script>\n{STYLE}\n'
                                             '<script defer src="./feedback.js'),
        ('<a class="brand" href="/web/"', '<a class="brand" href="./"'),
        ('<div class="auth-tabs"', NOTICE + '<div class="auth-tabs"'),
        ("<title>消費配對系統 v2｜", "<title>消費配對系統 v2 靜態展示｜"),
        ("示範帳號不能上傳；請切換成自己的帳號。", "靜態展示版不能上傳；要分析自己的發票，請在本機啟動完整服務。"),
    ],
    "app.js": [("'服務已連線'", "'靜態展示版'")],
}


class Recorder:
    def __init__(self, server):
        self.server = server.rstrip("/")
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # a system proxy would take 127.0.0.1

    def call(self, path, token=None, payload=None):
        """[status, body] for one request, the way the pages see it."""
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.server + "/api" + path, data=data, headers=headers)
        try:
            with self.opener.open(request, timeout=30) as response:
                return [response.status, json.loads(response.read() or b"null")]
        except urllib.error.HTTPError as error:
            return [error.code, json.loads(error.read() or b"null")]

    def ok(self, path, token=None, payload=None):
        status, body = self.call(path, token, payload)
        if status != 200:
            raise SystemExit(f"error: {path} answered {status}: {body}")
        return body


def record(recorder):
    health = recorder.ok("/health")
    if not health.get("demo_mode"):
        raise SystemExit("error: the server is not in demo mode (DEMO_MODE=1); start it with start.bat")
    everyone = recorder.ok("/auth/demo-users")
    personas = list(dict.fromkeys(user["persona"] for user in everyone))
    chosen = [next(u for u in everyone if u["display_name"] == f"{persona} {PICK}") for persona in personas]
    users = {}
    for user in chosen:
        token = recorder.ok("/auth/demo-login", payload={"user_id": user["user_id"]})["access_token"]
        me = recorder.call("/me", token)
        if me[0] != 200 or me[1].get("is_demo") is not True:
            raise SystemExit(f"error: user {user['user_id']} is not a demo user; nothing was written")
        matches = {f"{kind}:{scope}": recorder.call(f"/matches?kind={kind}&scope={scope}", token)
                   for kind in KINDS for scope in SCOPES}
        shown = sorted({person["user_id"] for status, body in matches.values() if status == 200
                        for person in body["people"]})
        users[str(user["user_id"])] = {
            "me": me,
            "profile": recorder.call("/me/profile", token),
            "matches": matches,
            "explain": {str(other): recorder.call(f"/matches/{other}/explain", token) for other in shown},
        }
        print(f"{user['display_name']}: {len(shown)} people to explain")
    return {"health": health, "demoUsers": chosen, "users": users}


def edit(text, name):
    for old, new in EDITS.get(name, []):
        if text.count(old) != 1:
            raise SystemExit(f"error: {name} no longer holds {old!r} exactly once; update EDITS in this script")
        text = text.replace(old, new)
    return text


def build(data, out):
    if out.exists():
        if not (out / MARKER).exists():
            raise SystemExit(f"error: {out} exists and is not a static demo; choose another --out")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for path in sorted(SOURCE.iterdir()):
        if path.suffix in (".html", ".js"):
            (out / path.name).write_text(edit(path.read_text(encoding="utf-8"), path.name), encoding="utf-8",
                                         newline="\n")
        else:
            shutil.copyfile(path, out / path.name)
    shutil.copyfile(SHIM, out / MARKER)
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    (out / "static-demo-data.js").write_text(
        "/* Recorded answers of fictional demo users, written by scripts/build_static_demo.py. */\n"
        f"globalThis.STATIC_DEMO_DATA = {body};\n", encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    parser.add_argument("--out", default="demo")
    args = parser.parse_args()
    out = ROOT / args.out
    data = record(Recorder(args.server))
    build(data, out)
    size = sum(path.stat().st_size for path in out.iterdir())
    print(f"wrote {out.relative_to(ROOT)}: {len(data['users'])} demo users, {size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
