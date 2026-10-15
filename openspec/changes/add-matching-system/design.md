# Design

## Context

動機見 proposal.md 的 Why；詳細的 27 項決定和角色分工見 `docs/team/overview.md`。

**API 的路徑、欄位、錯誤代碼和設定名稱，以 `docs/team/overview.md` 第 5 節（2026-10-14 定案，10/15 補上 5.11 帳號管理）為準**，這份 design 不重複列出，只記錄架構層級的決定。角色 1 第 1 週的逐步實作在 `docs/superpowers/plans/2026-10-14-api-skeleton.md`。

影響做法的現況：

- 核心邏輯都在 `src/receipt/`，是只用標準函式庫的純函式，流程是 `invoices` → `attributes` → `signals` → `traits` → `similarity`，另外有 159 個測試保護。`similarity.compare` 已經會回傳每一格的貢獻（`parts`）。
- `src/web/` 的 JS 目前讀的是建置時內嵌進 HTML 的資料，相似度另外有一份 JS 版本，兩邊共用 `tests/fixtures/similarity-cases.json`。
- 常去行政區由 `places.areas_of` 從發票推算，不是使用者自己填。
- 現有的 `invoices.build_month` 遇到「作廢」發票或有小數的金額、數量會直接報錯，但 5–8 月的真實發票兩種情況都有（3–8 月共 336 列：作廢 2 列、依金額規則略過 61 列，留下 273 列）。

限制：

- 4 週、4 人，程式主要由 AI 寫；全部是 Windows 電腦，只有一台有 RTX 4060 8G。
- repo 是公開的，真實資料不能進 git。

## Goals / Non-Goals

**Goals:**

- 直接重用 `src/receipt/`，不重寫核心邏輯，現有測試不必修改就能通過
- 模型可以替換：介面固定，先用假替身開發，模型好了再換成真的
- 每一層都能單獨說明、單獨測試

**Non-Goals:**

- 雲端部署、多台機器；在容器裡使用 GPU
- 向量資料庫和近似最近鄰搜尋
- 聊天、好友邀請等交友功能；忘記密碼、Email 驗證、管理員後台
- 拍照辨識、手動記帳
- 調整模型的超參數來追求最佳準確度

## Decisions

### D1. 三層架構，依賴只往一個方向

`src/api/`（服務）→ `src/ml/`（模型介接）→ `src/receipt/`（核心）。`src/receipt/` 不 import 另外兩層，仍然只用標準函式庫；v1 靜態建置照舊可以跑。

- 替代方案：把核心搬進新套件重寫。否決，因為會失去 159 個測試和已經校準好的數值。

### D2. FastAPI + SQLModel + 單一 SQLite 檔

資料表：

| 資料表 | 內容 |
|---|---|
| `users` | `id`、`username`、`password_hash`（假用戶是空的）、`display_name`、`is_demo`、`persona`（假用戶的類型），以及帳號管理時加上的 `tokens_valid_after` |
| `jobs` | 上傳工作：月份、狀態、`done`／`total`、訊息 |
| `items` | 品項：月份、日、發票代碼、店家、行政區、品名、數量、金額、類別（0–9，或 10 待確認）、屬性狀態 |
| `item_cache` | 品名、模型版本、23 個欄位的結果 |
| `profiles` | 每人的 18 格向量、常去行政區、有效品項數、更新時間 |

第 1 週只有 `users`，其餘四張在第 2 週接上傳時加入。SQLite 開 WAL 模式，寫入都用短交易。沒有引入資料庫遷移工具：SQLModel 的 `create_all` 不會替已經存在的資料表加欄位，所以開發用的 `data/app.db` 在結構改變時直接刪掉重建，再跑一次 seed。

- 替代方案：PostgreSQL + pgvector。否決，因為 `compare` 會略過沒有資料的格子，還要求至少 5 格共同的雙向格，pgvector 內建的餘弦做不到這兩件事；而且每台開發用的電腦都得多跑一個資料庫服務。

### D3. 配對在每次查詢時即時計算

拿 `profiles` 裡所有人的向量逐一跑 `similarity.compare`（300 人 × 18 格不到 1 秒），再套用 `configs/traits.json` 的門檻和 `places` 的距離。計算過程直接使用 `compare` 回傳的 `parts`，另外補上分母的各項，所以「貢獻加總 = 分數」一定成立；關係圖的資料用現有的 `build.trait_network_data`，品名經過 `items.label` 去掉地名（overview 5.8）。前端只負責顯示，不再自己算分數。

- 替代方案：預先算好所有配對並存起來。否決，因為 300 × 300 約 9 萬筆，每次有人上傳就要全部重算。

### D4. 背景任務分兩段

第一段在請求裡同步完成：解析整份 CSV（略過作廢、低於 10 元、金額有小數的明細；小數數量當 1），格式不對當場回 400，不建立工作。

第二段用 FastAPI 的 `BackgroundTasks` 執行：
1. 列出不重複品名，呼叫 `classify()`；最高機率低於 `CATEGORY_MIN_PROB` 的存成 10 待確認
2. 呼叫 `describe_items()`：先查 `item_cache`，GPU 模式下沒有快取的才問 Qwen；無 GPU 模式下沒有快取的回 `None`，記成待分析
3. 用這個人所有月份的資料重算 18 格，存進 `profiles`
4. 工作改成 `done`

待分析的品名，在 GPU 恢復後重新上傳同一個月份就會補算；GPU 模式下即時分類遇到新品名，會另外排一個背景分析。服務重啟時，還在跑的工作標成 `failed`，請使用者重傳。

- 替代方案：服務啟動時自動補算所有待分析品名。否決，因為重新上傳就能做到同樣的事，不必多寫一個常駐的佇列。

- 替代方案：Celery + Redis。否決，因為多一個服務要裝，在 Windows 上支援又差。

### D5. Qwen 跑在獨立的 llama.cpp `llama-server`

後端用 HTTP 呼叫 `LLAMA_SERVER_URL`（OpenAI 相容格式），連得上就是 GPU 模式。prompt 以及 `bulk_rule.py`、`sugar_guard.py` 沿用 `experiments/receipt-attributes/`。

模型用同一套評估重新選型，候選是約 5 GB 的模型（例如 Qwen3-8B Q4_K_M）；第一週結束還沒定案，就用已驗證的 Qwen3-4B。

- 替代方案：用 `llama-cpp-python` 把模型載入後端程序。否決，因為在 Windows 上編譯 CUDA 版很麻煩，而且模型和 API 綁在同一個程序，沒有 GPU 的電腦就跑不起來。

### D6. 屬性來源的接法

`src/ml/attributes.describe_items(names)` 回傳 23 個欄位，或 `None`（待分析）。`attributes.describe` 新增一個參數，可以接收外部提供的屬性：

- 店家通路 `channel_of` 照舊用規則，不交給 LLM
- fun 的英文值對應成現有的中文值：movie → 電影、singing → 唱歌、show → 展演、game → 遊樂
- 甜度預設規則留在品味計算時補位（見 taste-profile 規格）

API 路徑一律使用模型屬性；關鍵字規則只留給 v1 靜態建置和現有測試。

- 替代方案：屬性還在待分析時先用關鍵字規則頂替。否決，因為兩種來源混在一起，評估和說明都會變得不清楚。

### D7. 分類模型

`bert-base-chinese` 微調（品名最長 32 個 token），在 4060 上訓練，推論用 CPU 也可以。A、B 兩個比較基準沿用 `experiments/category-models/` 的程式。服務用 `CATEGORY_MODEL`（fake / tfidf / embedding / bert）選擇要用哪一個，`bert` 從 `CATEGORY_MODEL_DIR` 載入。

訓練資料：

- 真實品名，由 Qwen 預標、組員複核
- 稀少類別用 AI 生成的假品名補足。假品名不涉及隱私，可以用雲端 AI 生成

模型檔不進 git，而是公開在 Hugging Face 的模型庫：設定裡寫明模型庫名稱和固定的 revision，服務依此下載（見 D14）。模型卡要寫明訓練資料包含真實品名，但資料本身不公開。模型公開之前，組員一律用假替身開發。

- 替代方案：只用 TF-IDF。否決，因為它雖然最小最快，專案就少了深度學習那一段可以講。
- 替代方案：用私人雲端硬碟分享模型檔。否決，因為 Docker 和面試官都需要一個公開、可以固定版本的下載來源。

### D8. 登入

採用 OAuth2 password flow，登入用表單，`/docs` 的 Authorize 按鈕可以直接用：

- 權杖用 PyJWT 的 HS256 簽發，`sub` 是 user_id，有效期限 `JWT_EXPIRE_MINUTES`（預設 24 小時）
- 密碼用 pwdlib 的 argon2 雜湊；帳號不存在時也驗一次假雜湊，讓錯帳號和錯密碼花的時間相同
- 密鑰是 `.env` 的 `JWT_SECRET`（至少 32 字元）；git 裡只放 `.env.example`
- 錯誤一律是 `{"detail": "<代碼>"}`，由 `ApiError` 統一產生
- `DEMO_MODE=1` 時才有 demo 名單和快速切換，而且只能切換成假用戶
- 帳號管理上線時，權杖多帶 `iat`，驗證時還要檢查簽發時間不早於這位使用者的 `tokens_valid_after`。登出和改密碼都把 `tokens_valid_after` 設成現在（取到秒），所以這個帳號所有裝置上的舊權杖都會一起失效。改密碼時，新權杖要在更新這個欄位之後才簽發

- 替代方案：用 session cookie 或第三方登入。否決，因為前者要另外處理 CSRF，後者要在外部服務設定帳號。
- 登出的替代方案：只讓前端丟掉權杖（舊權杖在 1 天內仍然有效），或另開一張表記錄撤銷的權杖（多一張表，也要定期清理）。都否決，改用 `tokens_valid_after`：不加表，就能真正從伺服器端登出，代價是會登出所有裝置。

### D8a. 設定項目

名稱和預設值見 overview 5.10：`JWT_SECRET`、`JWT_EXPIRE_MINUTES`、`DEMO_MODE`、`DATABASE_URL`、`LLAMA_SERVER_URL`、`CATEGORY_MODEL`、`ATTRIBUTES_MODEL`、`CATEGORY_MIN_PROB`，以及 10/15 為 Docker 補上的 `CATEGORY_MODEL_DIR`、`CATEGORY_MODEL_REPO`、`CATEGORY_MODEL_REVISION`。由 `src/api/settings.py` 的 `Settings.from_env()` 讀取並檢查。

### D9. 前端

保留 `src/web/` 現有的 JS，新增一個 API 客戶端模組，把原本讀內嵌資料的地方改成呼叫 API。

- 整個 `src/web/` 由同一個 FastAPI 以靜態檔案掛在 `/web/`，和 API 同網域，不用設 CORS；v2 的入口是新的 `src/web/index.html`；不使用打包工具
- 前端把 API 的錯誤代碼對應成中文
- 根目錄的 `invoice-insights.html` 不動

- 替代方案：把網頁掛在 `/`。否決，因為 POST 到不存在的 `/api` 路徑會被靜態檔案接走，回 405 而不是 404（第 1 週試做時發現的）。
- 替代方案：用 Streamlit 或 React 重做（規劃會議第 10 題已經否決）。

### D10. 假用戶與假資料

把 `personas.py` 擴充到約 300 人，每種類型 37–38 人，用固定的種子。

- 假品名詞庫、假用戶、假品名的 Qwen 屬性結果都存成 JSONL，放在 `datasets/synthetic/` 並進 git，這樣沒有 GPU 的電腦也有完整的假用戶
- `src/api/seed.py`（第 1 週先放入 40 人，帳號是 `demo_001` 起算、沒有密碼）之後擴充成：把假發票寫進 `items`、把屬性結果載入 `item_cache`，再走一般的管線算出品味向量；重複執行不會重複加人

### D11. 測試與 CI

- Python 測試沿用 unittest（`python -m unittest discover -s tests`），JS 測試用 `node --test "tests/*.test.cjs"`
- API 測試用 Starlette 的 TestClient（需要 `httpx2`）加上記憶體 SQLite，模型一律用 `src/ml/fakes.py`（`CATEGORY_MODEL=fake`、`ATTRIBUTES_MODEL=fake`），不需要 GPU
- GitHub Actions 在 push 和 PR 時，用 Python 3.12 和 Node 24 執行全部測試，再執行一次 `docker build`（只建置，不下載模型）

- 替代方案：改用 pytest。否決，因為現有 77 個測試和第 1 週計畫都是 unittest，不需要多一套工具。

### D12. 隱私的實作方式

- 上傳的檔案寫到暫存檔，處理完就刪除
- 發票號碼沿用現有的 `YYYY-MM-Rnn` 代碼
- 地址沿用 `parse_district`，只留到行政區
- 配對清單的輸出結構裡根本沒有品項欄位；計算過程裡的品名一律經過 `items.label`（去掉地名、住宿與長途交通改成通用名稱、地點相關訊號不列品名），漏網的地名加進 `configs/attributes.json` 的 `place_words`，不在 API 另寫一套規則

### D13. 帳號管理

端點和錯誤代碼見 overview 5.11（`/api/me`、`/api/me/password`、`/api/me/months/{month}`、`/api/auth/logout`）。資料表不增加，只在 `users` 加 `tokens_valid_after`。

- **刪除帳號**在一個交易裡依序刪除：`items` → `jobs` → `profiles` → `users`，最後刪掉 `item_cache` 裡已經沒有任何 `items` 用到的品名。帳號刪除後，權杖查不到使用者，自然回應 401 `not_authenticated`
- **刪除月份**：先確認那個月份沒有 `queued` 或 `running` 的工作，再刪除那個月的 `items` 和 `jobs`，然後重算品味向量；快取的清理方式和刪除帳號相同
- **假用戶**（`is_demo`）的修改和刪除一律回 403 `demo_user_read_only`，而且這個檢查要在比對密碼之前；登出照常可用

- 替代方案：資料表加 `deleted_at`，只做「軟刪除」。否決，因為使用者要求刪除時就應該真的刪掉，軟刪除還得另外處理「刪除後的資料不能出現」的所有查詢。

### D14. Docker

- 一個映像檔，以 `python:3.12-slim` 為基底，只裝服務需要的套件（含 CPU 版 torch）
- `docker-compose.yml` 只有一個服務，兩個 volume：一個放 SQLite 資料庫，一個放下載的模型
- 啟動流程：
  1. 讀設定
  2. `CATEGORY_MODEL=bert` 而且 `CATEGORY_MODEL_DIR`（在模型 volume 裡）沒有模型時，用 `huggingface_hub` 下載 `CATEGORY_MODEL_REPO` 在 `CATEGORY_MODEL_REVISION` 的版本
  3. 資料庫是空的且 `DEMO_MODE=1` 時，執行和 `python -m src.api.seed` 相同的匯入
  4. 用 uvicorn 啟動 `src.api.main:app`
- 容器預設是無 GPU 模式；`LLAMA_SERVER_URL` 設成 `http://host.docker.internal:8080` 時，就連到主機上的 `llama-server`
- `.dockerignore` 排除 `rawdata/`、`data/`、`*.csv`、壓縮檔、`.env`、`models/`、`experiments/*/private`、`results`、`outputs`
- 組員開發時仍以 `start.bat` 為主；Docker 是給面試官和「乾淨環境驗證」用的

- 替代方案：不做 Docker。否決，因為面試官用一個指令就能跑起來，是作品集很重要的一環。
- 替代方案：用 devcontainer。否決，它主要是開發環境，不是給別人執行 demo 用的。
- 替代方案：在容器裡用 GPU 跑 LLM。否決，Windows 的 Docker 要接 GPU 很麻煩，而且面試官的電腦不一定有顯示卡。

## Risks / Trade-offs

- [選 5 GB 模型拖太久] → 第一週結束還沒定案，就退回 Qwen3-4B（砍功能順序 ①）
- [資料太少，BERT 沒有比 TF-IDF 好] → 照實報告。專案的亮點是流程和比較，不是 BERT 一定要贏
- [組員電腦沒有分類模型檔] → 模型公開到 Hugging Face 之前用假替身開發；之後服務會自動下載；健康檢查會明確顯示有沒有載入
- [公開的模型權重透露訓練用的真實品名] → 分類模型被反推出訓練品名的可能性很低，但不是零。模型卡寫明訓練資料的來源和不公開資料；公開前用 3.7 的掃描，確認模型卡和設定檔裡沒有真實品名
- [Docker 進度落後] → Docker 只是包裝已經完成的服務，排在第 3–4 週；它依賴分類模型已經公開，所以 HF 公開要在第 3 週完成
- [刪除帳號時誤刪別人還在用的快取] → 只刪除已經沒有任何 `items` 用到的品名，並寫測試涵蓋「別人也用過」的情況
- [服務重啟打斷背景工作] → 上傳工作標成 `failed` 請使用者重傳；待分析的品名靠重新上傳補算
- [`build_month` 遇到作廢或小數會報錯] → 第 2 週接上傳之前先修，用虛構的 CSV 寫測試涵蓋作廢、折扣、0 元、小數金額和小數數量
- [資料表結構改變，舊的開發資料庫少欄位] → 沒有遷移工具，直接刪掉 `data/app.db` 重建再 seed；正式資料只有 demo，不會遺失真人資料
- [Windows 版 llama.cpp 的 CUDA 相容問題] → 角色 3 第一週先驗證；退路是用 CPU 跑，速度慢，但待分析機制撐得住
- [4 人同時改 `src/receipt/` 或 `tasks.md` 起衝突] → 每個角色在自己的分支工作，以 PR 合併，CI 通過才合併；tasks.md 依角色分區
- [真實資料誤入 git] → `.gitignore` 已經擋掉壓縮檔（例如根目錄的 `rawdata.rar`）和 `/runtime/`；每個任務只 `git add` 自己的檔案，不用 `git add -A`
- [Python 和 JS 的相似度結果不一致] → v2 由後端計算，前端只顯示；共用的測試案例繼續保留

## Migration Plan

- 這次只新增、不取代：v1 靜態版照舊，v2 是新的入口；使用全新的資料庫，沒有資料要搬
- 合併順序：先合併 `experiment/receipt-attributes` 和 `feature/matching-system` 兩個 PR，各角色再從 `main` 開自己的分支（第 1 週計畫在合併前先從 `feature/matching-system` 開 `role-1/api-skeleton`）
- 退回方式：v2 是獨立的，移除 `src/api/` 和 `src/ml/` 不會影響 v1 和現有測試

## Open Questions

- 約 5 GB 的模型最後選哪一個：由選型實驗決定，不影響介面
- 配對驗證用的「相反類型」對照表：角色 3 在第 3 週訂出來
- Hugging Face 模型庫的名稱和帳號：第 3 週公開時再決定，只影響設定值
