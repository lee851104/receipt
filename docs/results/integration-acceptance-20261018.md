# 整合版本機驗收（2026-10-18，角色 1）

驗收對象：本機分支 `role-1/integration` 的 84d95f2。它合併了角色 1 到 d9b26b3 的工作、角色 3 的 6065c8c（屬性模型與 300 人 seed）、角色 2 的 4c5bdb1（BERT 載入與受保護下載）、角色 4 的 5fcda91（v2 前端）。分支還沒有推送，也不在 main。

所有資料都是虛構的：示範帳號來自 seed，測試帳號由驗收腳本隨機建立、密碼不寫進任何紀錄，上傳的 CSV 只用「示範…」開頭的品名。驗收用的資料庫和容器 volume 都在暫存位置，做完已刪除，只留下 Docker 專案 `receipt-r1-accept` 供複查。

## 結果一覽

| 項目 | 結果 | 對應任務 |
|---|---|---|
| 單元測試（`-W error`）、前端測試、OpenSpec | Python 562 OK、Node 149/149、`openspec validate --strict` valid | 6.5 一部分 |
| 映像檔建置與內容 | 建置成功（11 分 40 秒，1.67 GB）；沒有私人檔案與模型檔 | 2.12 本機部分 |
| Docker 啟動、示範帳號、重建後資料仍在、第一次啟動被中斷 | 全部通過 | 2.12、6.4 本機部分 |
| API 走一遍（示範帳號、上傳、配對、計算過程、帳號管理） | 全部通過 | 6.3（API） |
| 網頁走一遍（內建瀏覽器、Playwright） | 全部通過 | 6.3（網頁） |
| start.bat 的啟動流程（換埠、不開瀏覽器） | 通過 | 2.10 本機部分 |
| GPU 模式（RTX 4060、Qwen3-4B） | 通過 | 6.2 |
| `/docs` 與 overview 第 5 節 | 17 個路由完全一致 | 6.5 一部分 |
| 隱私掃描 | 第一次掃描有命中；使用者確認是隱私後換成合成名稱，重掃為 0（Git 歷史未改寫） | 6.6 |
| GitHub CI（推送 4abaad8 後） | tests、docker 兩個 job 都成功；紀錄裡沒有下載模型 | 2.11（PR 還沒開）、2.12 |
| 真的 BERT（受保護 Space） | 本機下載、`check_classify`、容器下載與無憑證重啟都通過 | 2.15 |
| 沒有 GPU 的電腦、乾淨電腦、組員照 README | 未做 | 2.10、2.14、6.1、6.4 |

## 測試與 OpenSpec

主資料夾，84d95f2，15:39:37–15:41:02：

- `PYTHON_DOTENV_DISABLED=1 HF_HUB_OFFLINE=1 .venv/Scripts/python.exe -X utf8 -W error -m unittest discover -s tests` → Ran 562 tests OK（含角色 2 的小型 BERT 真載入測試，沒有 skip）
- `node --test "tests/*.test.cjs"` → 149/149
- `OPENSPEC_TELEMETRY=0 openspec validate add-matching-system --strict` → valid

## Docker

Docker 29.8.2、Compose v5.6.0，在這台開發電腦上（不是乾淨電腦）。這台電腦的 8000 埠被另一個程式占用，所以用獨立的 Compose 專案名稱和埠：

```powershell
docker compose --env-file <暫存>/accept.env -p receipt-r1-accept -f docker-compose.yml -f <暫存>/port-8010.yml up -d --build
```

`accept.env` 是空的，所以 Compose 不讀專案根目錄的 `.env`；`port-8010.yml` 只用 `!override` 把埠換成 `127.0.0.1:8010:8000`。其他設定都是 `docker-compose.yml` 的預設（`CATEGORY_MODEL=fake`、`ATTRIBUTES_MODEL=qwen`、`DEMO_MODE=1`）。

- **映像檔內容**（和 CI 同一段檢查，另外加查 `*.db`、`*.safetensors`、`*.gguf`）：沒有 `/app/rawdata`、`/app/data`、`/app/.env`、`/app/models`、`/app/src/web`，也沒有 CSV、壓縮檔、`.env*`、資料庫和模型檔。`/app` 只有 `configs`、`datasets/synthetic/attribute-cache.jsonl`、兩個 requirements 檔和 `src`。
- **第一次啟動**：17 秒後 `/api/health` 回應（含放入 300 位示範帳號）；記錄寫 `demo users: 300 in all, 300 added`；health 是 `demo_mode: true`、`models: {category: fake, attributes: cache_only}`、`gpu_mode: false`。
- **重建後資料仍在**：`docker compose down`（不加 `-v`）再 `up -d`：6 秒後回應，記錄寫 `0 added (already complete)`；驗收帳號的 profile 還在，兩個月都在。
- **第一次啟動被中斷**：另一個專案（127.0.0.1:8011），啟動 8 秒、seed 做到一半時 `docker compose kill`，再 `up -d`：17 秒後回應，記錄寫 `0 added, purchases and profiles rewritten`；第一位和最後一位示範帳號都是 ready、沒有待分析品名。這個專案做完已用 `down -v` 刪除。

## API 走一遍

驗收腳本經真正的 HTTP 打 `http://127.0.0.1:8010`，只印狀態和數字：

- 示範帳號列出 300 位；第一位和最後一位登入後 profile 都是 ready、兩個月、待分析 0；配對清單 5 人且全是示範帳號；計算過程回 200
- 註冊兩個測試帳號，各上傳兩個月（各 40 行虛構明細，其中一個品名不在快取裡），四個背景工作都是 done；profile ready、80 筆、待分析 1
- 帳號 B 的配對清單第一位就是 A（+92%），計算過程回 200
- A 刪除 2026-05 → 只剩 2026-06；改顯示名稱成功；改密碼後舊 token 401、舊密碼 401、新密碼可以登入；登出後 token 401；刪除帳號後無法登入，也不在 B 的配對清單
- 第一次跑時配對與 profile 失敗：原因是腳本選的品名大多不在假分類模型的關鍵字裡，被歸到 10「待確認」不計入，每人只有 18 筆；改用假分類模型認得的虛構品名後全部通過（不是服務的問題）

## 網頁走一遍

- **內建瀏覽器**（打容器 8010）：登入頁的示範選單有 300 位；以「咖啡上班族 A」進入 → 二選一首頁 → 月報（兩個月、總額顯示、待分析提示隱藏，因為是 0）→ 配對（「219 位品味相似度 +30% 以上，顯示前 5 位」、顯示生活圈）→ 點第一位 → 連線圖與綜合解讀（SVG 725 個節點）；console 沒有錯誤
- **Playwright**（角色 4 的 `tests/web-v2-browser.cjs` 與 `tests/web-v2-live-browser.cjs`，headless Chromium 1208，整合版程式、暫存資料庫、fake/fake）：
  `NODE_PATH=<Playwright> BROWSER_EXECUTABLE=<chrome.exe> .venv/Scripts/python.exe -X utf8 tests/run_web_v2_live.py tests/web-v2-browser.cjs tests/web-v2-live-browser.cjs` → exit 0。通過的段落：註冊與上傳、錯誤 CSV／過大檔案／失敗工作可重試、月報與配對與連線圖與手機版、計算過程範例（82%）、兩個月 80 筆 → 月報 → 配對 → 18 格、帳號管理（取消／刪除月份 → 重算 40 筆 → 改名 → 改密碼舊 token 401 → 登出 → 新密碼登入 → 錯誤密碼拒絕 → 刪除帳號後不能登入、不在配對清單）

## start.bat 的啟動流程

在暫存 worktree（同一個 84d95f2，沒有 `.env`）執行 `launch.main`，只把埠換成 8012、不開瀏覽器：它自己從 `.env.example` 建了 `.env`（屬性模型 `qwen`），放入 300 位示範帳號，20 秒後 health 回應（`cache_only`）。同一份 API 驗收腳本全部通過。這是在有 GPU 的電腦上關掉 llama-server 跑的，**不是**任務 2.10 要求的「在沒有 GPU 的電腦上點兩下」。

## GPU 模式（6.2）

RTX 4060，主資料夾 `runtime/llama-b11557-cuda/llama-server.exe`，模型 Qwen3-4B-Instruct-2507 Q4_K_M（角色 3 選定的版本），參數 `--host 127.0.0.1 --port 8080 -ngl 99 -c 4096 -np 1 -t 2`，GPU 記憶體 2.3 → 5.4 GB；用完已停止並釋放。

- 沒有 llama-server 時：health `cache_only`、`gpu_mode: false`；上傳含新品名的月份後待分析大於 0；分類輸入框的新品名是 `pending`
- 開 llama-server 後：health `qwen`、`gpu_mode: true`；分類輸入框的新品名 2.1 秒內從 `pending` 變成 `ready`（23 欄中 20 欄有值）；同一個月重新上傳 6.2 秒完成，待分析從 13 變成 0，18 格中有 3 格的值改變
- 第一次用「示範驗收新奶茶」時待分析一樣歸零，但 18 格的值沒變（待分析時的飲品甜度預設和模型答案相同），所以改用「示範驗收無糖綠茶」重跑，確認向量真的更新

## `/docs` 與 overview 第 5 節

容器的 `/openapi.json` 有 17 個路由，和 overview 第 5 節寫的端點完全一樣（第 5 節另外寫了帶查詢參數的 `GET /api/matches?kind=similar&scope=all`，是同一個路由）。

## 隱私掃描（6.6）

腳本從 14 個真實發票 CSV（專案根目錄和 `rawdata/`）讀出品名和店名，只留 4 個字以上、不以「示範」開頭的 832 個字串，只放在記憶體裡；再找 git 追蹤的 411 個文字檔和映像檔 `/app` 的 89 個文字檔裡有沒有**完全相同**的字串。輸出只有檔名和數量：

- git 追蹤的檔案：13 個檔案有符合的字串。其中 6 個只出現在「示範…」品名裡面（`datasets/synthetic/attribute-cache*.jsonl`、`attribute-review.jsonl`、`docs/results/synthetic-cache-review.md`、`src/receipt/personas.py`），另外 7 個：`configs/brands.json`（1）、`datasets/synthetic/item-names.jsonl`（3）、`experiments/category-models/synthetic_names.py`（3）、`docs/superpowers/plans/2026-10-07-tags-matching.md`（2）、`docs/superpowers/plans/2026-10-07-taste-traits.md`（1）、`docs/superpowers/specs/2026-10-07-tags-matching-design.md`（1）、`invoice-insights.html`（2）
- 映像檔 `/app`：3 個檔案，`configs/brands.json`（1），其餘兩個只在「示範…」品名裡

完全相同的字串可能只是常見的通用品名或連鎖店名，也可能是真的外洩，Claude 不能看內容判斷。符合的字串和檔案寫在主資料夾的 `data/private/privacy-scan-20261018.json`（被 git 忽略，只給使用者自己看）。

**10/18 晚上的處理**：使用者確認這些命中是隱私。角色 2 把 3 個合成品名換掉（df82024，不重訓模型），Codex 依使用者授權把其餘 11 個檔案的命中換成獨立的合成名稱（店家規則、示範品名、v1 規劃文件、v1 網頁內嵌的示範資料、兩筆屬性快取名稱；快取的屬性值不變，`privacy_replacement` 寫明沒有重新呼叫模型），細節見 [privacy-cleanup-20261018.md](privacy-cleanup-20261018.md)。Claude 只看新增的行與掃描數字（刪掉的行含有舊字串，不看），用同一支腳本重掃：git 追蹤的 415 個文字檔、Codex 新建映像檔 `/app` 的 89 個文字檔都是 0；被換掉的店家規則原本就對到預設的「一般店家」，真實資料的通路判斷不變。**舊的 Git 提交（含已推送的分支與 PR）仍留著原來的字串**，要從歷史移除得另外改寫歷史並強制推送，這次沒有做。

## GitHub CI

使用者同意後推送 `role-1/integration`（4abaad8，沒有開 PR）。CI run 39110711344：`tests` job（86 秒）Ran 562 tests OK（skipped=1）、Node pass 149；`docker` job（82 秒）建置映像檔、私人檔案檢查、compose 啟動並確認 `cache_only`、300 位示範帳號、第一位和最後一位 profile ready 且沒有待分析，全部成功。整份 log 只有安裝 `safetensors` 套件時出現模型相關字樣，沒有下載任何模型。

## 真的 BERT（受保護的 Hugging Face Space）

使用者同意用自己已登入的 Hugging Face 帳號下載。Claude 沒有打開或印出權杖。

- **本機**：`python -m scripts.download_category_model --repo lee851104/receipt-model-lab --revision 29b655b96b4ced268bb0c3994e901c72dfd65420 --sha256 16997425… --destination models/category` → `downloaded`（53 秒，391 MB，逐檔核對 SHA-256；`models/` 被 git 忽略）
- **後端接口**：用 `load_backends`（`CATEGORY_MODEL=bert`、固定 SHA）載入，`backends.category` 是 `bert`，`tests/model_contract.check_classify` 通過（鮮奶茶 → 1 飲品、滷肉飯 → 0 正餐、衛生紙 12 包 → 8 日用品）；1000 個虛構品名在 CPU 上 13.4 秒；SHA 設錯時是 `unavailable`
- **Docker 下載**：`docker-compose.yml` 疊 `docker-compose.category.yml`（Space、revision、SHA、`HF_TOKEN_FILE` 指向本機的權杖檔，以唯讀 secret 掛進容器），獨立專案 `receipt-r1-bert`、127.0.0.1:8013：77 秒後 health 是 `category: bert`、`attributes: cache_only`；同一份 API 驗收腳本全部通過（BERT 把部分虛構品名放到待確認，每人計入 68 筆）；分類框對虛構品名的答案和本機一致
- **無憑證重啟**：`down`（不加 `-v`）後只設 `CATEGORY_MODEL=bert` 和 SHA、不疊 category 設定也不掛權杖：9 秒後 health 仍是 `bert`，資料保留

## 沒有做、要等人或推送的

- 2.11 要的是 PR 上的綠燈（這次只推送，沒有開 PR）
- 沒有 GPU 的電腦點兩下 start.bat（2.10、6.1）、只裝 Docker 的乾淨電腦（6.4，含模型自動下載）、組員照 README 從零啟動（2.14）
- 6.5 的「每一個規格情境都有對應的測試或手動紀錄」另外整理

## 容器連主機上的模型服務（2026-10-19 補上）

main bd5c4c5，這台開發電腦（RTX 4060）。主機上開 llama-server（只綁 `127.0.0.1:8080`，Qwen3-4B Q4_K_M），用驗收專案 `receipt-r1-accept`（127.0.0.1:8010，預設設定，容器連 `http://host.docker.internal:8080`）重建映像並啟動：

- Docker Desktop 的 `host.docker.internal` 由主機端代為連線，所以只綁 127.0.0.1 的 llama-server 也連得到，不用把它開放給外面
- 21 秒後 health 是 `gpu_mode: true`、`models: {category: fake, attributes: qwen}`；啟動時 seed 依角色 3 的 ce090cf 重建了 6 位連假旅人（`300 in all, 0 added, purchases and profiles rewritten`）
- 新帳號在分類框輸入新的虛構品名：`pending` → `ready`（23 欄中 21 欄有值）；上傳一個月（其中一個品名不在快取裡）後背景工作 done、profile ready、待分析 0
- 這就是 service-runtime「連到主機的模型服務」：容器以 GPU 模式運作，新品名的屬性可以被判斷。用完已停止 llama-server 與容器，GPU 與 8080、8010 都已釋放
