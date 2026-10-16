"""本機假模型 HTTP／瀏覽器整合。獨立臨時 DB；完成關閉服務，不讀私人資料。"""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import uvicorn
from sqlmodel import Session
from src.api.app import create_app
from src.api.settings import Settings
from src.api.tables import User, Profile
from scripts.concepts_example import example


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scripts", nargs="*", default=["tests/web-v2-live-browser.cjs"])
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="receipt-role4-http-") as folder:
        settings = Settings(jwt_secret=secrets.token_urlsafe(48), demo_mode=True,
                            database_url="sqlite:///" + (Path(folder) / "app.db").as_posix(),
                            llama_server_url="http://127.0.0.1:9")
        app = create_app(settings)  # 正式路由／worker／模型載入器，兩模型設定維持 fake
        # 僅數學教學的兩個合成 profiles；不冒充角色 3 的完整 seed。
        sample = example()
        with Session(app.state.engine) as session:
            for index, side in enumerate(("mine", "theirs"), 1):
                user = User(username=f"concept_{index}", display_name=f"概念範例{index}", is_demo=True)
                session.add(user)
                session.flush()
                session.add(Profile(user_id=user.id, item_count=30, areas="[]",
                                    vector=json.dumps([c[side] for c in sample["cells"]])))
            session.commit()
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning", access_log=False))
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
            thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
            thread.start()
            try:
                for _ in range(100):
                    if server.started:
                        break
                    if not thread.is_alive():
                        raise RuntimeError("測試服務啟動失敗")
                    time.sleep(.1)
                else:
                    raise RuntimeError("測試服務啟動逾時")
                print(f"HTTP TEST pid={os.getpid()} port={port} cwd={ROOT} models=fake/fake GPU=off temporary_DB", flush=True)
                env = {**os.environ, "RECEIPT_TEST_URL": f"http://127.0.0.1:{port}"}
                for script in args.scripts:
                    subprocess.run(["node", script], cwd=ROOT, env=env, check=True, timeout=180)
            finally:
                server.should_exit = True
                thread.join(timeout=10)
                app.state.worker.queue.join()
                app.state.engine.dispose()
                print(f"HTTP TEST released port={port}", flush=True)
                if thread.is_alive():
                    raise RuntimeError("測試服務未結束")


if __name__ == "__main__":
    main()
