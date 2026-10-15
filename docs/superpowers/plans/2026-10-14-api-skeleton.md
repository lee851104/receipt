# 後端骨架（角色 1 第一週）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FastAPI 後端骨架用假模型跑通：註冊、登入、demo 快速切換、品名即時分類、健康檢查，以及從同一個伺服器提供 `src/web/` 網頁。

**Architecture:** `src/api/` 是 FastAPI 伺服器，`create_app(settings, backends)` 組出整個 app。設定從環境變數讀進 `Settings`；模型透過 `Backends` 接上，第一週只有 `src/ml/fakes.py` 的假替身；SQLite 用 SQLModel，目前只有 `users` 一張表。錯誤一律是 `{"detail": "<代碼>"}`。測試用記憶體資料庫和假模型，不需要 GPU。

**Tech Stack:** Python 3.12、FastAPI、SQLModel（SQLite）、PyJWT、pwdlib（argon2）、unittest、Starlette TestClient（httpx2）

**Spec:** `docs/team/overview.md` 第 5 節（端點、錯誤代碼、設定）

## Global Constraints

- 從 `feature/matching-system` 開分支 `role-1/api-skeleton` 工作；不要 push。
- 所有 Python 指令都用專案的虛擬環境：`.venv/Scripts/python.exe`（Git Bash 和 PowerShell 都能這樣寫）。不要用系統的 `python`，它沒有 FastAPI。
- 指令都在專案根目錄執行：
  - 全部 Python 測試：`.venv/Scripts/python.exe -m unittest discover -s tests`
  - 單一檔：`.venv/Scripts/python.exe -m unittest tests.test_api_auth -v`
  - Node 測試：`node --test "tests/*.test.cjs"`（這個計畫不改 JS，最後應該還是 82 個通過）
- **不改** `src/receipt/`、`src/web/`、`configs/`，只讀。
- **不讀** `data/`、`rawdata/`、根目錄的 `*.csv`（真實發票）。測試只用虛構的名字和品名。
- 每個任務只 `git add` 該任務列出的檔案，不要用 `git add -A` 或 `git add .`。
- 改檔一律用編輯工具（Edit／Write），程式碼照本計畫逐字輸入（Python 的縮排有意義）。不要用 shell 的 heredoc、`sed` 或 `echo` 寫程式碼。
- Commit 訊息用英文，結尾一行 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
- Git 在 Windows 上會提示「LF will be replaced by CRLF」，可以忽略。

## 不在這個計畫裡（第二週之後）

上傳與背景任務（`/api/invoices`、`/api/jobs`）、`/api/me/profile`、`/api/matches`、`explain`、真的分類模型與 Qwen、`item_cache` 和其他資料表、GPU 模式下把 pending 品名排進背景分析、GitHub Actions、`start.bat`。

## 試做結果

最終狀態已在專案副本完整跑過：Python 測試 121 個全部通過（原本 77 + 新增 44），把 `DeprecationWarning` 當成錯誤也通過；9 個新測試檔各自單獨執行也通過。也實際啟動過伺服器：seed 加入 40 個 demo 用戶（再跑一次加入 0 個）、`/api/health`、demo 登入、品名分類、`/web/match.html`、`/docs` 都正常。中間各任務的程式碼是最終版的一部分，沒有逐任務單獨驗證。

每個任務結束時的 Python 測試數：

| 任務後 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Python | 77 | 81 | 86 | 90 | 94 | 100 | 107 | 111 | 114 | 119 | 121 |

試做時發現、已經寫進計畫的兩件事：

- Starlette 1.8 的 TestClient 要 `httpx2`；只裝 `httpx` 會出現棄用警告。
- 網頁如果掛在 `/`，POST 到不存在的路徑（例如 `DEMO_MODE` 關閉時的 `demo-login`）會被靜態檔案接走，回 405 而不是 404。所以網頁掛在 `/web/`。

## 實作時的變更（2026-10-15）

每個任務都經過規格審查和程式品質審查，修正後的程式碼和下面各任務的程式碼區塊有出入，**以 repo 裡的程式碼為準**。最後 Python 測試 153 個（原本預期 121）。主要差異：

- `src/ml/`：`describe_items(names, ask_model=True)`；新增 `tests/model_contract.py`，角色 2、3 可以拿來檢查真模型的回傳格式（一般 Python 型別、機率加總為 1 等）
- `settings.py`：留空等於預設值；數字錯誤或超出範圍時錯誤訊息會指出變數名稱；`repr` 不印密鑰
- `backends.py`：llama-server 偵測不經過 proxy、不會丟例外、結果記住 5 秒
- `db.py`：`ROOT` 移到這裡；相對路徑的 SQLite 檔從 repo 根目錄算起（新增 `tests/test_api_db.py`）
- `tables.py`、`security.py`：每個使用者有隨機 `token_key`，token 帶著它，帳號 id 被重用時舊 token 失效；DEMO_MODE 關閉時 demo token 立刻失效；密碼做 NFKC 正規化，登入時先截到 512 字元再正規化
- `routes/auth.py`：帳號一律存成小寫、不能以 `demo_` 開頭；顯示名稱不能有控制或看不見的字元；登入失敗的 401 帶 `WWW-Authenticate`；demo-login 的 `user_id` 只接受 1 到 2^63−1 的整數
- `routes/items.py`：品名不能有控制或看不見的字元；分類框只查快取（`ask_model=False`）
- `errors.py`：422 不回傳被拒絕的輸入值；程式出錯時回 500 JSON `internal_error`
- `seed.py`：資料庫裡的 demo 用戶跟假用戶清單對不上時停下來，不會默默略過
- `main.py`：DEMO_MODE 開啟時印提醒；設定錯誤或模型還沒有時只印一行（新增 `tests/test_api_main.py`）
- `.gitignore`：擋住 `/src/web/*-data.js`

## 檔案

| 檔案 | 負責 |
|---|---|
| `requirements.txt` | API 和測試要的套件，固定版本 |
| `.env.example` | 設定範本（`.env` 本身不進 git） |
| `src/ml/fields.py` | 10 類、16 個屬性、7 個旗標的欄位名，模型、假替身、API 共用 |
| `src/ml/fakes.py` | `classify()`、`describe_items()` 假替身，固定結果 |
| `src/api/settings.py` | `Settings.from_env()`：讀環境變數、檢查密鑰和模型名稱 |
| `src/api/backends.py` | `Backends`：用哪個模型、llama-server 有沒有開 |
| `src/api/errors.py` | `ApiError` 和它的處理器：`{"detail": 代碼}` |
| `src/api/tables.py` | 資料表（目前只有 `users`） |
| `src/api/db.py` | SQLite 引擎、建表、每個請求一個 session |
| `src/api/security.py` | 密碼雜湊、JWT、`current_user` |
| `src/api/routes/health.py` | `GET /api/health` |
| `src/api/routes/auth.py` | 註冊、登入、demo 名單、demo 登入 |
| `src/api/routes/items.py` | `POST /api/items/classify` |
| `src/api/app.py` | `create_app()`：把上面全部組起來 |
| `src/api/seed.py` | 把虛構用戶放進資料庫當 demo 用戶 |
| `src/api/main.py` | uvicorn 的進入點 |
| `tests/api_support.py` | 測試用 client（記憶體資料庫、假模型、沒有 GPU） |

---

### Task 0: 分支、套件與設定範本

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`

- [ ] **Step 1: 開分支**

```bash
git switch feature/matching-system
git switch -c role-1/api-skeleton
```

- [ ] **Step 2: 建立 `requirements.txt`**

```text
# The API server and its tests. Model training packages live in experiments/*/requirements*.txt.
fastapi==0.143.0
uvicorn[standard]==0.54.0
sqlmodel==0.0.48
python-multipart==0.0.32
pyjwt==2.15.1
pwdlib[argon2]==0.3.1
python-dotenv==1.2.4
# Starlette's TestClient wants httpx2; plain httpx only gives a deprecation warning.
httpx2==2.13.1
```

- [ ] **Step 3: 建立 `.env.example`**

```text
# Copy to .env (never committed) and set JWT_SECRET, at least 32 characters:
#   .venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET=
JWT_EXPIRE_MINUTES=1440
# 1 opens the demo quick switch; keep 0 anywhere other people can reach.
DEMO_MODE=1
DATABASE_URL=sqlite:///data/app.db
LLAMA_SERVER_URL=http://127.0.0.1:8080
CATEGORY_MODEL=fake
ATTRIBUTES_MODEL=fake
CATEGORY_MIN_PROB=0.5
```

- [ ] **Step 4: 安裝套件**

沒有 `.venv` 的話先建：`uv venv --python 3.12 .venv`。然後：

```bash
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
```

Expected: 結尾沒有錯誤；`httpx2` 在安裝清單裡（或已經裝過）。

- [ ] **Step 5: 確認現有測試都通過**

```bash
.venv/Scripts/python.exe -m unittest discover -s tests
node --test "tests/*.test.cjs"
```

Expected: Python `Ran 77 tests` … `OK`；Node `pass 82`、`fail 0`。

- [ ] **Step 6: 確認 `.env` 會被擋住、範本不會**

```bash
git check-ignore -q .env && echo ".env is ignored"; git check-ignore -q .env.example || echo "example is tracked"
```

Expected: 印出 `.env is ignored` 和 `example is tracked` 兩行。（不要加 `-v`：加了之後，`!.env.example` 這種排除規則也會讓結束碼變成 0。）

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .env.example
git commit -m "chore: pin the API packages and add the settings template" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 1: 模型欄位與假替身（`src/ml/`）

**Files:**
- Create: `src/ml/__init__.py`
- Create: `src/ml/fields.py`
- Create: `src/ml/fakes.py`
- Test: `tests/test_ml_fakes.py`

- [ ] **Step 1: 寫測試 `tests/test_ml_fakes.py`**

```python
"""The fake models answer in exactly the shape the real ones will."""
import unittest
from pathlib import Path

from src.ml import fakes
from src.ml.fields import ATTRIBUTES, CATEGORY_COUNT, FIELDS
from src.receipt.attributes import describe
from src.receipt.traits import load_context

ROOT = Path(__file__).resolve().parents[1]


class FakeModelTests(unittest.TestCase):
    def test_classify_gives_each_name_a_category_and_ten_probabilities(self):
        answers = fakes.classify(["鮮奶茶", "滷肉飯", "衛生紙 12 包"])
        self.assertEqual([answer["category"] for answer in answers], [1, 0, 8])
        for answer in answers:
            self.assertEqual(len(answer["probs"]), CATEGORY_COUNT)
            self.assertAlmostEqual(sum(answer["probs"]), 1.0)
            self.assertEqual(max(answer["probs"]), answer["probs"][answer["category"]])

    def test_a_name_without_keywords_is_a_weak_guess(self):
        [answer] = fakes.classify(["滷肉飯"])
        self.assertLess(answer["probs"][answer["category"]], 0.5)

    def test_describe_items_has_every_field_and_knows_none_of_them(self):
        answers = fakes.describe_items(["鮮奶茶", "滷肉飯"])
        self.assertEqual(len(answers), 2)
        for answer in answers:
            self.assertEqual(list(answer), list(FIELDS))
            self.assertTrue(all(value is None for value in answer.values()))

    def test_the_sixteen_attributes_are_what_the_rules_answer_today(self):
        vocabulary = load_context(ROOT)["vocabulary"]
        row = {"name": "鮮奶茶", "category": 1, "quantity": 1, "merchant": "飲料店"}
        # describe() answers food plus the 16 attributes; food is also one of the 7 flags.
        self.assertEqual(set(describe(row, "一般店家", vocabulary)), set(ATTRIBUTES) | {"food"})
        self.assertEqual(len(FIELDS), 23)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑測試，確認失敗**

Run: `.venv/Scripts/python.exe -m unittest tests.test_ml_fakes -v`
Expected: ERROR，`ModuleNotFoundError: No module named 'src.ml'`

- [ ] **Step 3: 建立 `src/ml/__init__.py`**

```python
"""Model interfaces for product names: categories (classify) and attributes (describe_items), plus fakes."""
```

- [ ] **Step 4: 建立 `src/ml/fields.py`**

```python
"""Names shared by the category and attribute models, their fakes and the API."""

CATEGORY_COUNT = 10  # models answer 0-9; 10 (待確認) is decided later from the probability, never by a model
ATTRIBUTES = ("clearance", "sugar", "quick", "cooking", "kitchen", "sport_supply", "sport_gear", "car_care",
              "bulk", "home", "stationery", "fun", "pet_food", "pet_supply", "species", "alcohol")
FLAGS = ("food", "meal", "drink", "fresh", "daily", "tech", "sport")
FIELDS = ATTRIBUTES + FLAGS  # what describe_items() answers for one name; None means unknown, never False
```

- [ ] **Step 5: 建立 `src/ml/fakes.py`**

```python
"""Stand-ins with the same interface as category.classify and attributes.describe_items.

The API and CI use them until the real models land, so every answer is fixed.
"""
from .fields import CATEGORY_COUNT, FIELDS

# A few words per category so the classify box shows more than one answer; any other name is a weak 正餐.
KEYWORDS = ((1, ("茶", "咖啡", "拿鐵", "可樂")), (2, ("餅乾", "蛋糕", "巧克力", "布丁")),
            (3, ("蔬菜", "雞蛋", "豬肉", "香蕉")), (8, ("衛生紙", "洗衣", "牙膏")))
SURE, UNSURE = 0.9, 0.3


def spread(category, top):
    """Ten probabilities: top on one category and the rest shared evenly, adding up to 1."""
    rest = (1 - top) / (CATEGORY_COUNT - 1)
    return [top if index == category else rest for index in range(CATEGORY_COUNT)]


def classify(names):
    """Each name's category 0-9 and the probability of every category."""
    answers = []
    for name in names:
        category = next((category for category, words in KEYWORDS if any(word in name for word in words)), None)
        answers.append({"category": 0, "probs": spread(0, UNSURE)} if category is None
                       else {"category": category, "probs": spread(category, SURE)})
    return answers


def describe_items(names):
    """Every field unknown for every name: the shape of a real answer with nothing guessed."""
    return [dict.fromkeys(FIELDS) for _ in names]
```

- [ ] **Step 6: 跑測試，確認通過**

Run: `.venv/Scripts/python.exe -m unittest tests.test_ml_fakes -v`
Expected: 4 個測試 `ok`。全部 Python 測試：`Ran 81 tests` … `OK`

- [ ] **Step 7: Commit**

```bash
git add src/ml/__init__.py src/ml/fields.py src/ml/fakes.py tests/test_ml_fakes.py
git commit -m "feat: add the shared model field names and fake models" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: 設定（`src/api/settings.py`）

**Files:**
- Create: `src/api/__init__.py`
- Create: `src/api/settings.py`
- Test: `tests/test_api_settings.py`

- [ ] **Step 1: 寫測試 `tests/test_api_settings.py`**

```python
"""Settings come from the environment, with the defaults the team overview lists."""
import unittest

from src.api.settings import Settings

SECRET = "s" * 32


class SettingsTests(unittest.TestCase):
    def test_only_the_secret_is_required_and_the_rest_has_the_listed_defaults(self):
        settings = Settings.from_env({"JWT_SECRET": SECRET})
        self.assertEqual(settings, Settings(
            jwt_secret=SECRET, jwt_expire_minutes=1440, demo_mode=False, database_url="sqlite:///data/app.db",
            llama_server_url="http://127.0.0.1:8080", category_model="fake", attributes_model="fake",
            category_min_prob=0.5))

    def test_every_variable_is_read(self):
        settings = Settings.from_env({
            "JWT_SECRET": SECRET, "JWT_EXPIRE_MINUTES": "60", "DEMO_MODE": "1", "DATABASE_URL": "sqlite://",
            "LLAMA_SERVER_URL": "http://10.0.0.5:8080/", "CATEGORY_MODEL": "bert", "ATTRIBUTES_MODEL": "qwen",
            "CATEGORY_MIN_PROB": "0.6"})
        self.assertEqual(settings, Settings(
            jwt_secret=SECRET, jwt_expire_minutes=60, demo_mode=True, database_url="sqlite://",
            llama_server_url="http://10.0.0.5:8080", category_model="bert", attributes_model="qwen",
            category_min_prob=0.6))

    def test_demo_mode_is_on_only_for_exactly_1(self):
        for value in ("0", "true", "yes", ""):
            with self.subTest(value=value):
                self.assertFalse(Settings.from_env({"JWT_SECRET": SECRET, "DEMO_MODE": value}).demo_mode)

    def test_a_missing_or_short_secret_stops_the_server(self):
        for env in ({}, {"JWT_SECRET": ""}, {"JWT_SECRET": "s" * 31}):
            with self.subTest(env=env), self.assertRaisesRegex(ValueError, "JWT_SECRET"):
                Settings.from_env(env)

    def test_unknown_model_names_stop_the_server(self):
        for key in ("CATEGORY_MODEL", "ATTRIBUTES_MODEL"):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, key):
                Settings.from_env({"JWT_SECRET": SECRET, key: "gpt"})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑測試，確認失敗**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_settings -v`
Expected: ERROR，`ModuleNotFoundError: No module named 'src.api'`

- [ ] **Step 3: 建立 `src/api/__init__.py`**

```python
"""The FastAPI server: accounts, uploads, profiles and matches over the receipt pipeline."""
```

- [ ] **Step 4: 建立 `src/api/settings.py`**

```python
"""Server settings from environment variables; docs/team/overview.md section 5.10 lists them."""
from dataclasses import dataclass

CATEGORY_MODELS = ("fake", "tfidf", "embedding", "bert")
ATTRIBUTE_MODELS = ("fake", "qwen")
MIN_SECRET = 32  # characters; HS256 wants a key at least as long as its 256-bit hash


@dataclass(frozen=True)
class Settings:
    jwt_secret: str
    jwt_expire_minutes: int = 1440
    demo_mode: bool = False
    database_url: str = "sqlite:///data/app.db"
    llama_server_url: str = "http://127.0.0.1:8080"
    category_model: str = "fake"
    attributes_model: str = "fake"
    category_min_prob: float = 0.5

    @classmethod
    def from_env(cls, env):
        """Settings from a mapping such as os.environ; a weak secret or an unknown model name stops the server."""
        secret = env.get("JWT_SECRET", "")
        if len(secret) < MIN_SECRET:
            raise ValueError(f"JWT_SECRET must be at least {MIN_SECRET} characters; see .env.example")
        settings = cls(
            jwt_secret=secret,
            jwt_expire_minutes=int(env.get("JWT_EXPIRE_MINUTES", cls.jwt_expire_minutes)),
            demo_mode=env.get("DEMO_MODE", "0") == "1",
            database_url=env.get("DATABASE_URL", cls.database_url),
            llama_server_url=env.get("LLAMA_SERVER_URL", cls.llama_server_url).rstrip("/"),
            category_model=env.get("CATEGORY_MODEL", cls.category_model),
            attributes_model=env.get("ATTRIBUTES_MODEL", cls.attributes_model),
            category_min_prob=float(env.get("CATEGORY_MIN_PROB", cls.category_min_prob)),
        )
        if settings.category_model not in CATEGORY_MODELS:
            raise ValueError("CATEGORY_MODEL must be one of " + ", ".join(CATEGORY_MODELS))
        if settings.attributes_model not in ATTRIBUTE_MODELS:
            raise ValueError("ATTRIBUTES_MODEL must be one of " + ", ".join(ATTRIBUTE_MODELS))
        return settings
```

- [ ] **Step 5: 跑測試，確認通過**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_settings -v`
Expected: 5 個測試 `ok`。全部 Python 測試：`Ran 86 tests` … `OK`

- [ ] **Step 6: Commit**

```bash
git add src/api/__init__.py src/api/settings.py tests/test_api_settings.py
git commit -m "feat: read the API settings from the environment" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: 模型接口與 GPU 偵測（`src/api/backends.py`）

**Files:**
- Create: `src/api/backends.py`
- Test: `tests/test_api_backends.py`

- [ ] **Step 1: 寫測試 `tests/test_api_backends.py`**

```python
"""The server picks its models from the settings and probes the llama-server for GPU mode."""
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from src.api.backends import llama_probe, load_backends
from src.api.settings import Settings
from src.ml import fakes

SECRET = "s" * 32


class Answer(BaseHTTPRequestHandler):
    """A stand-in llama-server whose /health says ok."""
    def do_GET(self):
        self.send_response(200 if self.path == "/health" else 404)
        self.end_headers()

    def log_message(self, *args):
        pass


class BackendTests(unittest.TestCase):
    def test_the_fakes_are_loaded_by_default(self):
        backends = load_backends(Settings(jwt_secret=SECRET))
        self.assertEqual((backends.category, backends.attributes), ("fake", "fake"))
        self.assertIs(backends.classify, fakes.classify)
        self.assertIs(backends.describe_items, fakes.describe_items)

    def test_asking_for_a_real_model_before_it_exists_stops_the_server(self):
        for changes in ({"category_model": "bert"}, {"attributes_model": "qwen"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                load_backends(Settings(jwt_secret=SECRET, **changes))

    def test_the_probe_is_true_while_the_llama_server_answers(self):
        server = HTTPServer(("127.0.0.1", 0), Answer)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            self.assertTrue(llama_probe(f"http://127.0.0.1:{server.server_port}")())
        finally:
            server.shutdown()
            server.server_close()

    def test_the_probe_is_false_when_nothing_listens_or_the_url_is_broken(self):
        server = HTTPServer(("127.0.0.1", 0), Answer)
        port = server.server_port
        server.server_close()  # the port was free a moment ago and nothing listens on it now
        self.assertFalse(llama_probe(f"http://127.0.0.1:{port}")())
        self.assertFalse(llama_probe("not a url")())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑測試，確認失敗**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_backends -v`
Expected: ERROR，`ModuleNotFoundError: No module named 'src.api.backends'`

- [ ] **Step 3: 建立 `src/api/backends.py`**

```python
"""Which category and attribute models answer, and whether the llama-server running Qwen is up."""
from dataclasses import dataclass
from typing import Callable
import urllib.request

from ..ml import fakes


@dataclass(frozen=True)
class Backends:
    category: str                    # the name /api/health reports
    classify: Callable               # list[str] -> list[{"category": 0-9, "probs": [10 floats]}]
    attributes: str
    describe_items: Callable         # list[str] -> list[dict | None]
    gpu_probe: Callable[[], bool]    # whether the llama-server answers right now


def llama_probe(url, timeout=0.5):
    """A function telling whether the llama-server at url answers its /health check."""
    def probe():
        try:
            with urllib.request.urlopen(url + "/health", timeout=timeout) as response:
                return response.status == 200
        except (OSError, ValueError):  # refused, timed out, an error status, or a malformed URL
            return False
    return probe


def load_backends(settings):
    """The models settings ask for. Only the fakes exist until src/ml has the real ones."""
    if settings.category_model != "fake" or settings.attributes_model != "fake":
        raise ValueError("Only CATEGORY_MODEL=fake and ATTRIBUTES_MODEL=fake work until src/ml has the real models")
    return Backends(category="fake", classify=fakes.classify, attributes="fake",
                    describe_items=fakes.describe_items, gpu_probe=llama_probe(settings.llama_server_url))
```

- [ ] **Step 4: 跑測試，確認通過**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_backends -v`
Expected: 4 個測試 `ok`。全部 Python 測試：`Ran 90 tests` … `OK`

- [ ] **Step 5: Commit**

```bash
git add src/api/backends.py tests/test_api_backends.py
git commit -m "feat: choose the models from the settings and probe the llama-server" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: App 骨架與健康檢查

**Files:**
- Create: `src/api/errors.py`
- Create: `src/api/tables.py`
- Create: `src/api/db.py`
- Create: `src/api/routes/__init__.py`
- Create: `src/api/routes/health.py`
- Create: `src/api/app.py`
- Create: `tests/api_support.py`
- Test: `tests/test_api_health.py`

- [ ] **Step 1: 建立測試輔助 `tests/api_support.py`**

`register()` 和 `login()` 要到 Task 6 才用得到，先一起寫好。檔名不是 `test_` 開頭，所以 unittest 不會把它當成測試。

```python
"""A test client on its own in-memory database, with the fake models and no GPU."""
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.backends import Backends
from src.api.settings import Settings
from src.ml import fakes

SECRET = "test-secret-0123456789abcdef0123456789"


def fake_backends(**changes):
    values = {"category": "fake", "classify": fakes.classify, "attributes": "fake",
              "describe_items": fakes.describe_items, "gpu_probe": lambda: False}
    return Backends(**{**values, **changes})


def make_client(demo_mode=False, **backend_changes):
    settings = Settings(jwt_secret=SECRET, demo_mode=demo_mode, database_url="sqlite://")
    return TestClient(create_app(settings, fake_backends(**backend_changes)))


def register(client, username="amy", password="password123", **extra):
    return client.post("/api/auth/register", json={"username": username, "password": password, **extra})


def login(client, username="amy", password="password123"):
    """Bearer headers for a user that register() created."""
    response = client.post("/api/auth/login", data={"username": username, "password": password})
    return {"Authorization": "Bearer " + response.json()["access_token"]}
```

- [ ] **Step 2: 寫測試 `tests/test_api_health.py`**

```python
"""GET /api/health answers without a login and says which models and modes are on."""
import unittest

from tests.api_support import make_client


class HealthTests(unittest.TestCase):
    def test_health_needs_no_login_and_reports_models_and_modes(self):
        response = make_client().get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "gpu_mode": False, "demo_mode": False,
                                           "models": {"category": "fake", "attributes": "fake"}})

    def test_gpu_mode_follows_the_llama_server_probe(self):
        self.assertTrue(make_client(gpu_probe=lambda: True).get("/api/health").json()["gpu_mode"])
        self.assertTrue(make_client(demo_mode=True).get("/api/health").json()["demo_mode"])

    def test_qwen_without_the_llama_server_reads_only_its_cache(self):
        down = make_client(attributes="qwen").get("/api/health").json()
        up = make_client(attributes="qwen", gpu_probe=lambda: True).get("/api/health").json()
        self.assertEqual((down["models"]["attributes"], up["models"]["attributes"]), ("cache_only", "qwen"))

    def test_unknown_api_paths_are_404(self):
        self.assertEqual(make_client().get("/api/nothing").status_code, 404)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 跑測試，確認失敗**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_health -v`
Expected: ERROR，`ModuleNotFoundError: No module named 'src.api.app'`

- [ ] **Step 4: 建立 `src/api/errors.py`**

```python
"""Errors sent as {"detail": code} with an optional message; overview section 5 lists the codes."""
from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status, code, message=None, headers=None):
        super().__init__(code)
        self.status, self.code, self.message, self.headers = status, code, message, headers


async def api_error_handler(request: Request, error: ApiError):
    content = {"detail": error.code}
    if error.message is not None:
        content["message"] = error.message
    return JSONResponse(status_code=error.status, content=content, headers=error.headers)
```

- [ ] **Step 5: 建立 `src/api/tables.py`**

```python
"""Database tables. Week 1 needs only users; jobs, items, item_cache and profiles come with the uploads."""
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str | None = None  # demo users have none, so only demo-login lets them in
    display_name: str
    is_demo: bool = False
    persona: str | None = None        # the fictional type, such as 咖啡上班族; None for real people
```

- [ ] **Step 6: 建立 `src/api/db.py`**

```python
"""The SQLite engine, and one session per request."""
from pathlib import Path

from fastapi import Request
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from . import tables  # noqa: F401  registers every table on SQLModel.metadata

MEMORY = "sqlite://"


def make_engine(url):
    """An engine for url. An in-memory database keeps one shared connection, or each request would see an empty one."""
    if url == MEMORY:
        return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    if url.startswith("sqlite:///"):
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, connect_args={"check_same_thread": False})


def init_db(engine):
    """Create the tables that do not exist yet."""
    SQLModel.metadata.create_all(engine)


def get_session(request: Request):
    with Session(request.app.state.engine) as session:
        yield session
```

- [ ] **Step 7: 建立 `src/api/routes/__init__.py`**

```python
"""One module per group of endpoints in overview section 5.2."""
```

- [ ] **Step 8: 建立 `src/api/routes/health.py`**

```python
"""GET /api/health: the server is up, whether the GPU model is reachable, and which models answer."""
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/api/health")
def health(request: Request):
    settings, backends = request.app.state.settings, request.app.state.backends
    gpu = backends.gpu_probe()
    # Without the llama-server, Qwen can only answer from its cache.
    attributes = "cache_only" if backends.attributes == "qwen" and not gpu else backends.attributes
    return {"status": "ok", "gpu_mode": gpu, "demo_mode": settings.demo_mode,
            "models": {"category": backends.category, "attributes": attributes}}
```

- [ ] **Step 9: 建立 `src/api/app.py`（這一版只有健康檢查，之後的任務會再加路由）**

```python
"""Build the FastAPI app: settings, database, models and the /api routes."""
import json
from pathlib import Path

from fastapi import FastAPI

from .backends import load_backends
from .db import init_db, make_engine
from .errors import ApiError, api_error_handler
from .routes import health

ROOT = Path(__file__).resolve().parents[2]


def create_app(settings, backends=None):
    """The app for these settings; backends defaults to the models settings ask for, and tests pass their own."""
    app = FastAPI(title="消費配對系統 API", version="2.0.0")
    app.state.settings = settings
    app.state.engine = make_engine(settings.database_url)
    init_db(app.state.engine)
    app.state.backends = backends or load_backends(settings)
    report = json.loads((ROOT / "configs" / "report.json").read_text(encoding="utf-8"))
    app.state.categories = [category["name"] for category in report["categories"]]
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(health.router)
    return app
```

- [ ] **Step 10: 跑測試，確認通過**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_health -v`
Expected: 4 個測試 `ok`。全部 Python 測試：`Ran 94 tests` … `OK`

- [ ] **Step 11: Commit**

```bash
git add src/api/errors.py src/api/tables.py src/api/db.py src/api/routes/__init__.py src/api/routes/health.py src/api/app.py tests/api_support.py tests/test_api_health.py
git commit -m "feat: add the FastAPI app skeleton with the users table and the health check" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: 密碼與 token（`src/api/security.py`）

**Files:**
- Create: `src/api/security.py`
- Test: `tests/test_api_security.py`

- [ ] **Step 1: 寫測試 `tests/test_api_security.py`**

```python
"""Passwords are stored hashed and tokens only work while they are genuine and fresh."""
import unittest
from datetime import datetime, timedelta, timezone

from src.api.security import create_token, hash_password, read_token, verify_password
from src.api.settings import Settings

SETTINGS = Settings(jwt_secret="test-secret-0123456789abcdef0123456789")


class PasswordTests(unittest.TestCase):
    def test_a_hash_hides_the_password_and_checks_it(self):
        hashed = hash_password("password123")
        self.assertNotIn("password123", hashed)
        self.assertTrue(verify_password("password123", hashed))
        self.assertFalse(verify_password("password124", hashed))

    def test_no_password_matches_a_user_without_a_hash(self):
        self.assertFalse(verify_password("anything", None))


class TokenTests(unittest.TestCase):
    def test_a_token_names_the_user_it_was_issued_for(self):
        self.assertEqual(read_token(create_token(7, SETTINGS), SETTINGS), 7)

    def test_an_expired_token_is_refused(self):
        issued = datetime.now(timezone.utc) - timedelta(minutes=SETTINGS.jwt_expire_minutes + 1)
        self.assertIsNone(read_token(create_token(7, SETTINGS, now=issued), SETTINGS))

    def test_a_token_signed_with_another_secret_is_refused(self):
        other = Settings(jwt_secret="another-secret-0123456789abcdef012345")
        self.assertIsNone(read_token(create_token(7, other), SETTINGS))

    def test_garbage_is_refused(self):
        self.assertIsNone(read_token("not.a.token", SETTINGS))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑測試，確認失敗**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_security -v`
Expected: ERROR，`ModuleNotFoundError: No module named 'src.api.security'`

- [ ] **Step 3: 建立 `src/api/security.py`**

```python
"""Password hashes, access tokens, and the logged-in user behind a request."""
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlmodel import Session

from .db import get_session
from .errors import ApiError
from .tables import User

HASHER = PasswordHash.recommended()  # argon2
# Checked when there is no password to check, so a wrong username takes as long as a wrong password.
DUMMY_HASH = HASHER.hash("no account has this password")
ALGORITHM = "HS256"
# auto_error=False: a missing token reaches current_user, which answers in the API's own error format.
bearer = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password):
    return HASHER.hash(password)


def verify_password(password, hashed):
    """Whether password matches hashed; always False without a hash (no such user, or a demo user)."""
    if hashed is None:
        HASHER.verify(password, DUMMY_HASH)
        return False
    return HASHER.verify(password, hashed)


def create_token(user_id, settings, now=None):
    now = now or datetime.now(timezone.utc)
    claims = {"sub": str(user_id), "exp": now + timedelta(minutes=settings.jwt_expire_minutes)}
    return jwt.encode(claims, settings.jwt_secret, algorithm=ALGORITHM)


def read_token(token, settings):
    """The user id a token was issued for, or None when it is forged, broken or expired."""
    try:
        return int(jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None


def token_response(user, settings):
    """What login and demo-login send back."""
    return {"access_token": create_token(user.id, settings), "token_type": "bearer",
            "expires_in": settings.jwt_expire_minutes * 60}


def current_user(request: Request, token: Annotated[str | None, Depends(bearer)],
                 session: Annotated[Session, Depends(get_session)]):
    """The user the bearer token names; 401 not_authenticated when there is no valid token."""
    user_id = None if token is None else read_token(token, request.app.state.settings)
    user = None if user_id is None else session.get(User, user_id)
    if user is None:
        raise ApiError(401, "not_authenticated", headers={"WWW-Authenticate": "Bearer"})
    return user
```

- [ ] **Step 4: 跑測試，確認通過**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_security -v`
Expected: 6 個測試 `ok`。全部 Python 測試：`Ran 100 tests` … `OK`

- [ ] **Step 5: Commit**

```bash
git add src/api/security.py tests/test_api_security.py
git commit -m "feat: hash passwords and issue access tokens" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: 註冊與登入

**Files:**
- Create: `src/api/routes/auth.py`
- Modify: `src/api/app.py`（加入 `auth.router`）
- Test: `tests/test_api_auth.py`

- [ ] **Step 1: 寫測試 `tests/test_api_auth.py`（demo 的測試在 Task 9 加）**

```python
"""Register, log in, and the demo quick switch that only fictional people can use."""
import unittest

from src.api.security import read_token
from tests.api_support import login, make_client, register


class RegisterTests(unittest.TestCase):
    def test_register_answers_201_with_the_new_user(self):
        response = register(make_client(), display_name="Amy")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"user_id": 1, "username": "amy", "display_name": "Amy"})

    def test_the_display_name_defaults_to_the_username(self):
        self.assertEqual(register(make_client()).json()["display_name"], "amy")

    def test_a_taken_username_is_409(self):
        client = make_client()
        register(client)
        response = register(client, password="different-password")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {"detail": "username_taken"})

    def test_bad_fields_are_422(self):
        for fields in ({"username": "am"}, {"username": "a" * 33}, {"username": "amy!"}, {"password": "short"},
                       {"password": "p" * 129}, {"display_name": "   "}, {"display_name": "名" * 21}):
            with self.subTest(fields=fields):
                self.assertEqual(register(make_client(), **fields).status_code, 422)


class LoginTests(unittest.TestCase):
    def test_login_answers_a_bearer_token_for_the_user(self):
        client = make_client()
        user_id = register(client).json()["user_id"]
        body = client.post("/api/auth/login", data={"username": "amy", "password": "password123"}).json()
        self.assertEqual((body["token_type"], body["expires_in"]), ("bearer", 86400))
        self.assertEqual(read_token(body["access_token"], client.app.state.settings), user_id)

    def test_a_wrong_password_and_an_unknown_user_get_the_same_401(self):
        client = make_client()
        register(client)
        for form in ({"username": "amy", "password": "wrong-password"}, {"username": "bob", "password": "password123"}):
            with self.subTest(form=form):
                response = client.post("/api/auth/login", data=form)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"detail": "bad_credentials"})

    def test_the_helper_headers_work(self):
        client = make_client()
        register(client)
        self.assertTrue(login(client)["Authorization"].startswith("Bearer "))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑測試，確認失敗**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_auth -v`
Expected: 7 個測試都 FAIL 或 ERROR，路由還不存在（例如 `AssertionError: 404 != 201`、`KeyError: 'user_id'`）

- [ ] **Step 3: 建立 `src/api/routes/auth.py`（demo 的部分在 Task 9 加）**

```python
"""Accounts: register and log in, and the demo quick switch that exists only when DEMO_MODE=1."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..db import get_session
from ..errors import ApiError
from ..security import hash_password, token_response, verify_password
from ..tables import User

router = APIRouter(prefix="/api/auth")
SessionDep = Annotated[Session, Depends(get_session)]


class Registration(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9_]{3,32}$")
    password: str = Field(min_length=8, max_length=128)
    display_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)] | None = None


@router.post("/register", status_code=201)
def register(body: Registration, session: SessionDep):
    user = User(username=body.username, password_hash=hash_password(body.password),
                display_name=body.display_name or body.username)
    session.add(user)
    try:
        session.commit()
    except IntegrityError:  # the username is unique in the table, so a taken one fails here
        raise ApiError(409, "username_taken") from None
    session.refresh(user)
    return {"user_id": user.id, "username": user.username, "display_name": user.display_name}


@router.post("/login")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], request: Request, session: SessionDep):
    user = session.exec(select(User).where(User.username == form.username)).first()
    # One answer for an unknown username and a wrong password, so neither tells which accounts exist.
    if not verify_password(form.password, None if user is None else user.password_hash):
        raise ApiError(401, "bad_credentials")
    return token_response(user, request.app.state.settings)
```

- [ ] **Step 4: 修改 `src/api/app.py`，接上 `auth.router`**

把

```python
from .routes import health
```

改成

```python
from .routes import auth, health
```

把

```python
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(health.router)
```

改成

```python
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(auth.router)
    app.include_router(health.router)
```

- [ ] **Step 5: 跑測試，確認通過**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_auth -v`
Expected: 7 個測試 `ok`。全部 Python 測試：`Ran 107 tests` … `OK`

- [ ] **Step 6: Commit**

```bash
git add src/api/routes/auth.py src/api/app.py tests/test_api_auth.py
git commit -m "feat: register and log in with a password" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: 品名即時分類

**Files:**
- Create: `src/api/routes/items.py`
- Modify: `src/api/app.py`（加入 `items.router`）
- Test: `tests/test_api_items.py`

- [ ] **Step 1: 寫測試 `tests/test_api_items.py`**

```python
"""POST /api/items/classify needs a login and answers the category and attributes of one name."""
import unittest

from src.ml.fields import FIELDS
from tests.api_support import login, make_client, register


class ClassifyTests(unittest.TestCase):
    def client_and_headers(self, **backend_changes):
        client = make_client(**backend_changes)
        register(client)
        return client, login(client)

    def test_classify_needs_a_valid_token(self):
        client = make_client()
        for headers in ({}, {"Authorization": "Bearer not.a.token"}):
            with self.subTest(headers=headers):
                response = client.post("/api/items/classify", json={"name": "鮮奶茶"}, headers=headers)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"detail": "not_authenticated"})
                self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")

    def test_classify_answers_the_category_probabilities_and_attributes(self):
        client, headers = self.client_and_headers()
        body = client.post("/api/items/classify", json={"name": "  鮮奶茶 微糖 "}, headers=headers).json()
        self.assertEqual(body["name"], "鮮奶茶 微糖")
        self.assertEqual(body["category"], {"id": 1, "name": "飲品", "prob": 0.9})
        self.assertEqual(len(body["probs"]), 10)
        self.assertEqual(body["attributes"], dict.fromkeys(FIELDS))
        self.assertEqual(body["attributes_status"], "ready")

    def test_a_name_the_attribute_model_has_not_seen_is_pending(self):
        client, headers = self.client_and_headers(describe_items=lambda names: [None for _ in names])
        body = client.post("/api/items/classify", json={"name": "鮮奶茶"}, headers=headers).json()
        self.assertEqual((body["attributes"], body["attributes_status"]), (None, "pending"))

    def test_an_empty_or_too_long_name_is_422(self):
        client, headers = self.client_and_headers()
        for name in ("", "   ", "茶" * 101):
            with self.subTest(length=len(name)):
                response = client.post("/api/items/classify", json={"name": name}, headers=headers)
                self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑測試，確認失敗**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_items -v`
Expected: 4 個測試都 FAIL 或 ERROR，路由還不存在（例如 `AssertionError: 404 != 401`）

- [ ] **Step 3: 建立 `src/api/routes/items.py`**

```python
"""POST /api/items/classify: one product name's category and attributes, for the classify box."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, StringConstraints

from ..security import current_user

router = APIRouter(prefix="/api/items", dependencies=[Depends(current_user)])


class ItemName(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


@router.post("/classify")
def classify(body: ItemName, request: Request):
    state = request.app.state
    [answer] = state.backends.classify([body.name])
    [attributes] = state.backends.describe_items([body.name])
    category = answer["category"]
    return {"name": body.name,
            "category": {"id": category, "name": state.categories[category], "prob": answer["probs"][category]},
            "probs": answer["probs"], "attributes": attributes,
            "attributes_status": "pending" if attributes is None else "ready"}
```

- [ ] **Step 4: 修改 `src/api/app.py`，接上 `items.router`**

把

```python
from .routes import auth, health
```

改成

```python
from .routes import auth, health, items
```

把

```python
    app.include_router(auth.router)
    app.include_router(health.router)
```

改成

```python
    app.include_router(auth.router)
    app.include_router(items.router)
    app.include_router(health.router)
```

- [ ] **Step 5: 跑測試，確認通過**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_items -v`
Expected: 4 個測試 `ok`。全部 Python 測試：`Ran 111 tests` … `OK`

- [ ] **Step 6: Commit**

```bash
git add src/api/routes/items.py src/api/app.py tests/test_api_items.py
git commit -m "feat: classify one product name for logged-in users" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: 把虛構用戶放進資料庫（`src/api/seed.py`）

**Files:**
- Create: `src/api/seed.py`
- Test: `tests/test_api_seed.py`

- [ ] **Step 1: 寫測試 `tests/test_api_seed.py`**

```python
"""The fictional population becomes demo users once, however often the seed runs."""
import unittest
from pathlib import Path

from sqlmodel import Session, select

from src.api.db import MEMORY, init_db, make_engine
from src.api.seed import seed_demo_users
from src.api.tables import User
from src.receipt.personas import build_personas
from src.receipt.traits import load_context

ROOT = Path(__file__).resolve().parents[1]
PEOPLE = [{"name": "咖啡上班族 A", "type": "咖啡上班族"}, {"name": "健身族 A", "type": "健身族"}]


class SeedTests(unittest.TestCase):
    def setUp(self):
        self.engine = make_engine(MEMORY)
        init_db(self.engine)

    def users(self):
        with Session(self.engine) as session:
            return session.exec(select(User).order_by(User.id)).all()

    def test_each_person_becomes_a_demo_user_without_a_password(self):
        self.assertEqual(seed_demo_users(self.engine, PEOPLE), 2)
        self.assertEqual([(user.username, user.display_name, user.persona, user.is_demo, user.password_hash)
                          for user in self.users()],
                         [("demo_001", "咖啡上班族 A", "咖啡上班族", True, None),
                          ("demo_002", "健身族 A", "健身族", True, None)])

    def test_running_the_seed_again_adds_nobody(self):
        seed_demo_users(self.engine, PEOPLE)
        self.assertEqual(seed_demo_users(self.engine, PEOPLE), 0)
        self.assertEqual(len(self.users()), 2)

    def test_the_whole_fictional_population_fits(self):
        people = build_personas(load_context(ROOT)["calendar"])
        self.assertEqual(seed_demo_users(self.engine, people), len(people))
        self.assertEqual(len({user.display_name for user in self.users()}), len(people))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑測試，確認失敗**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_seed -v`
Expected: ERROR，`ModuleNotFoundError: No module named 'src.api.seed'`

- [ ] **Step 3: 建立 `src/api/seed.py`**

```python
"""Put the fictional population in the database as demo users. Run from the repository root:

    .venv/Scripts/python.exe -m src.api.seed
"""
import os

from dotenv import load_dotenv
from sqlmodel import Session, select

from ..receipt.personas import build_personas
from ..receipt.traits import load_context
from .app import ROOT
from .db import init_db, make_engine
from .settings import Settings
from .tables import User


def seed_demo_users(engine, people):
    """One demo user per fictional person, demo_001 onwards; usernames already taken are left alone."""
    with Session(engine) as session:
        taken = set(session.exec(select(User.username)).all())
        added = 0
        for index, person in enumerate(people, start=1):
            username = f"demo_{index:03}"
            if username not in taken:
                session.add(User(username=username, display_name=person["name"], is_demo=True,
                                 persona=person["type"]))
                added += 1
        session.commit()
    return added


def main():
    load_dotenv(ROOT / ".env")
    engine = make_engine(Settings.from_env(os.environ).database_url)
    init_db(engine)
    people = build_personas(load_context(ROOT)["calendar"])
    print("added", seed_demo_users(engine, people), "demo users;", len(people), "fictional people in all")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑測試，確認通過**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_seed -v`
Expected: 3 個測試 `ok`。全部 Python 測試：`Ran 114 tests` … `OK`

- [ ] **Step 5: Commit**

```bash
git add src/api/seed.py tests/test_api_seed.py
git commit -m "feat: seed the fictional population as demo users" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: demo 快速切換（只在 `DEMO_MODE=1`）

**Files:**
- Modify: `src/api/routes/auth.py`
- Modify: `src/api/app.py`
- Modify: `tests/test_api_auth.py`

- [ ] **Step 1: 在 `tests/test_api_auth.py` 加 demo 的測試**

把

```python
from src.api.security import read_token
from tests.api_support import login, make_client, register
```

改成

```python
from src.api.security import read_token
from src.api.seed import seed_demo_users
from tests.api_support import login, make_client, register

PEOPLE = [{"name": "咖啡上班族 A", "type": "咖啡上班族"}, {"name": "健身族 A", "type": "健身族"}]
```

然後在 `LoginTests` 類別後面、`if __name__ == "__main__":` 前面加上：

```python
class DemoTests(unittest.TestCase):
    def setUp(self):
        self.client = make_client(demo_mode=True)
        seed_demo_users(self.client.app.state.engine, PEOPLE)
        self.real_id = register(self.client).json()["user_id"]

    def test_without_demo_mode_the_demo_endpoints_do_not_exist(self):
        client = make_client()
        self.assertEqual(client.get("/api/auth/demo-users").status_code, 404)
        self.assertEqual(client.post("/api/auth/demo-login", json={"user_id": 1}).status_code, 404)

    def test_demo_users_lists_only_fictional_people_in_order(self):
        self.assertEqual(self.client.get("/api/auth/demo-users").json(), [
            {"user_id": 1, "display_name": "咖啡上班族 A", "persona": "咖啡上班族"},
            {"user_id": 2, "display_name": "健身族 A", "persona": "健身族"}])

    def test_demo_login_gives_a_fictional_person_a_token(self):
        body = self.client.post("/api/auth/demo-login", json={"user_id": 2}).json()
        self.assertEqual(read_token(body["access_token"], self.client.app.state.settings), 2)
        self.assertEqual((body["token_type"], body["expires_in"]), ("bearer", 86400))

    def test_demo_login_refuses_real_accounts_and_unknown_ids(self):
        real = self.client.post("/api/auth/demo-login", json={"user_id": self.real_id})
        self.assertEqual((real.status_code, real.json()), (403, {"detail": "not_demo_user"}))
        unknown = self.client.post("/api/auth/demo-login", json={"user_id": 99})
        self.assertEqual((unknown.status_code, unknown.json()), (404, {"detail": "not_found"}))

    def test_a_fictional_person_cannot_log_in_with_a_password(self):
        response = self.client.post("/api/auth/login", data={"username": "demo_001", "password": "password123"})
        self.assertEqual(response.status_code, 401)
```

- [ ] **Step 2: 跑測試，確認失敗**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_auth -v`
Expected: `test_demo_users_lists_only_fictional_people_in_order`、`test_demo_login_gives_a_fictional_person_a_token`、`test_demo_login_refuses_real_accounts_and_unknown_ids` 這 3 個 FAIL 或 ERROR（路由還不存在）。`test_without_demo_mode_the_demo_endpoints_do_not_exist` 和 `test_a_fictional_person_cannot_log_in_with_a_password` 現在就會過，它們是防止之後改壞的檢查。

- [ ] **Step 3: 修改 `src/api/routes/auth.py`**

把

```python
from sqlmodel import Session, select
```

改成

```python
from sqlmodel import Session, col, select
```

把

```python
router = APIRouter(prefix="/api/auth")
SessionDep = Annotated[Session, Depends(get_session)]
```

改成

```python
router = APIRouter(prefix="/api/auth")
demo_router = APIRouter(prefix="/api/auth")
SessionDep = Annotated[Session, Depends(get_session)]
```

在 `Registration` 類別後面加上：

```python
class DemoLogin(BaseModel):
    user_id: int
```

在檔案最後（`login` 函式後面）加上：

```python
@demo_router.get("/demo-users")
def demo_users(session: SessionDep):
    users = session.exec(select(User).where(col(User.is_demo).is_(True)).order_by(col(User.id))).all()
    return [{"user_id": user.id, "display_name": user.display_name, "persona": user.persona} for user in users]


@demo_router.post("/demo-login")
def demo_login(body: DemoLogin, request: Request, session: SessionDep):
    user = session.get(User, body.user_id)
    if user is None:
        raise ApiError(404, "not_found")
    # Real accounts always need their password, even with DEMO_MODE on.
    if not user.is_demo:
        raise ApiError(403, "not_demo_user")
    return token_response(user, request.app.state.settings)
```

- [ ] **Step 4: 修改 `src/api/app.py`，只在 `DEMO_MODE` 開啟時接上 `demo_router`**

把

```python
    app.include_router(auth.router)
    app.include_router(items.router)
```

改成

```python
    app.include_router(auth.router)
    # Without DEMO_MODE the demo endpoints do not exist at all, so they answer 404 and stay out of /docs.
    if settings.demo_mode:
        app.include_router(auth.demo_router)
    app.include_router(items.router)
```

- [ ] **Step 5: 跑測試，確認通過**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_auth -v`
Expected: 12 個測試 `ok`。全部 Python 測試：`Ran 119 tests` … `OK`

- [ ] **Step 6: Commit**

```bash
git add src/api/routes/auth.py src/api/app.py tests/test_api_auth.py
git commit -m "feat: add the demo quick switch for fictional users behind DEMO_MODE" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: 網頁、啟動與實際跑一次

**Files:**
- Modify: `src/api/app.py`
- Create: `src/api/main.py`
- Test: `tests/test_api_pages.py`

- [ ] **Step 1: 寫測試 `tests/test_api_pages.py`**

```python
"""The same server hands out the web pages under /web/, so the pages call the API without CORS."""
import unittest

from tests.api_support import make_client


class PageTests(unittest.TestCase):
    def test_the_web_folder_is_served_next_to_the_api(self):
        client = make_client()
        page = client.get("/web/match.html")
        self.assertEqual(page.status_code, 200)
        self.assertIn("text/html", page.headers["content-type"])
        self.assertEqual(client.get("/web/trait-similarity.js").status_code, 200)

    def test_the_api_docs_and_unknown_paths_are_not_files(self):
        client = make_client()
        self.assertEqual(client.post("/api/nothing").status_code, 404)
        self.assertEqual(client.get("/api/health").json()["status"], "ok")
        self.assertEqual(client.get("/docs").status_code, 200)
        self.assertEqual(client.get("/openapi.json").json()["info"]["title"], "消費配對系統 API")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑測試，確認失敗**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_pages -v`
Expected: `test_the_web_folder_is_served_next_to_the_api` FAIL（`AssertionError: 404 != 200`）。另一個現在就會過，它檢查的是掛上網頁之後不能壞掉的部分。

- [ ] **Step 3: 修改 `src/api/app.py`**

把第一行的 docstring

```python
"""Build the FastAPI app: settings, database, models and the /api routes."""
```

改成

```python
"""Build the FastAPI app: settings, database, models, the /api routes, and the web pages under /web/."""
```

把

```python
from fastapi import FastAPI
```

改成

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
```

把

```python
    app.include_router(health.router)
    return app
```

改成

```python
    app.include_router(health.router)
    # Under /web/ rather than /, so an unknown /api path is a plain 404 instead of a static-file 405.
    app.mount("/web", StaticFiles(directory=ROOT / "src" / "web", html=True), name="web")
    return app
```

- [ ] **Step 4: 跑測試，確認通過**

Run: `.venv/Scripts/python.exe -m unittest tests.test_api_pages -v`
Expected: 2 個測試 `ok`。全部 Python 測試：`Ran 121 tests` … `OK`

- [ ] **Step 5: 建立 `src/api/main.py`**

```python
"""The app uvicorn serves. Run from the repository root:

    .venv/Scripts/python.exe -m uvicorn src.api.main:app --reload
"""
import os

from dotenv import load_dotenv

from .app import ROOT, create_app
from .settings import Settings

load_dotenv(ROOT / ".env")
app = create_app(Settings.from_env(os.environ))
```

- [ ] **Step 6: 準備 `.env`（不會進 git）**

`.env` 已經存在就跳過這一步。不然複製 `.env.example` 成 `.env`，再把下面這行印出的字串貼到 `JWT_SECRET=` 後面：

```bash
.venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```

- [ ] **Step 7: 放入 demo 用戶，跑兩次**

```bash
.venv/Scripts/python.exe -m src.api.seed
.venv/Scripts/python.exe -m src.api.seed
```

Expected: 第一次 `added 40 demo users; 40 fictional people in all`，第二次 `added 0 demo users; 40 fictional people in all`。資料庫在 `data/app.db`（被 `.gitignore` 擋住）。

- [ ] **Step 8: 啟動伺服器，逐一檢查**

```bash
.venv/Scripts/python.exe -m uvicorn src.api.main:app --reload
```

用瀏覽器打開：

- `http://127.0.0.1:8000/api/health` → `{"status":"ok","gpu_mode":false,"demo_mode":true,"models":{"category":"fake","attributes":"fake"}}`（有開 llama-server 時 `gpu_mode` 是 true）
- `http://127.0.0.1:8000/api/auth/demo-users` → 40 個人，第一個是 `省錢上班族 A`
- `http://127.0.0.1:8000/docs` → 文件頁。按 Authorize 用一個註冊過的帳號登入，再試 `POST /api/items/classify`，`{"name": "鮮奶茶"}` 應該回 `飲品`、`0.9`
- `http://127.0.0.1:8000/web/match.html` → 現有配對頁的原始檔（還沒有資料，畫面是空的，正常）

確認完按 Ctrl+C 關掉伺服器。

- [ ] **Step 9: 全部測試**

```bash
.venv/Scripts/python.exe -m unittest discover -s tests
node --test "tests/*.test.cjs"
```

Expected: Python `Ran 121 tests` … `OK`；Node `pass 82`、`fail 0`。

- [ ] **Step 10: 確認沒有多出不該提交的檔案**

```bash
git status --short
```

Expected: 只列出 `src/api/app.py`、`src/api/main.py`、`tests/test_api_pages.py`。`.env` 和 `data/app.db` 不應該出現。

- [ ] **Step 11: Commit**

```bash
git add src/api/app.py src/api/main.py tests/test_api_pages.py
git commit -m "feat: serve the web pages under /web and add the uvicorn entry point" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: 在總覽寫下怎麼啟動

**Files:**
- Modify: `docs/team/overview.md`（第 12 節「環境」）

- [ ] **Step 1: 在第 12 節「環境」的步驟 2 和 3 之間插入新的步驟 3，原本的 3 改成 4**

找到

```markdown
   預期結果：Python 77 個、JS 82 個全部通過
3. 4060：
```

改成

```markdown
   預期結果：Python 77 個、JS 82 個全部通過（後端骨架合併之後是 Python 121 個）
3. 後端（角色 1 的第一週成果）：
   - 安裝套件：`uv pip install --python .venv/Scripts/python.exe -r requirements.txt`
   - 複製 `.env.example` 成 `.env`，`JWT_SECRET` 填一串至少 32 字元的亂碼：`.venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(32))"`
   - 放入 demo 用戶：`.venv/Scripts/python.exe -m src.api.seed`
   - 啟動：`.venv/Scripts/python.exe -m uvicorn src.api.main:app --reload`，打開 `http://127.0.0.1:8000/docs`
4. 4060：
```

- [ ] **Step 2: Commit**

```bash
git add docs/team/overview.md
git commit -m "docs: explain how to start the API server" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
