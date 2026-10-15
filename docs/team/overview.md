# 消費配對系統：團隊總覽

> 給 4 位組員和各自的 AI 先讀的唯一一份文件。最後更新：2026-10-15。
> 逐條需求、技術決定和任務清單在 OpenSpec 變更 `openspec/changes/add-matching-system/`。API 的路徑、欄位、錯誤代碼和設定名稱以本文件第 5 節為準，兩邊不一致時改 OpenSpec。
> 交給 AI 時可以這樣說：「先讀 `docs/team/overview.md`，我是角色 N，今天要做第 N 週的哪一項。」
> 角色之間要轉告的事寫在第 13 節，開工前先看自己的那一段。

## 1. 一句話

上傳電子發票 → 模型把每個品名分類、判斷屬性 → 算出每個人 18 格的「品味向量」→ 用餘弦相似度（分子就是內積）找出**相近**和**互補**的人。

這是職訓結案專案（4 人，到 2026-11-10 左右），也是之後應徵 AI 軟體工程師的作品。**架構完整、每一層都講得清楚，比模型準確度更重要。**

## 2. 現在已經有的東西

| 部分 | 現況 | 位置 |
|---|---|---|
| 發票解析 | 讀財政部電子發票 CSV，一份一個月；地址只取到縣市和行政區 | `src/receipt/invoices.py`、`address.py` |
| 品項屬性 | 關鍵字規則（`describe`、`channel_of`） | `src/receipt/attributes.py`、`configs/attributes.json`、`brands.json` |
| 品味向量 | 46 個訊號算成 18 格，少於 20 個品項就不算 | `src/receipt/signals.py`、`traits.py`、`configs/traits.json` |
| 相似度 | 加權內積 ÷（向量長度相乘 + 0.25），只算兩人都有的格子，至少要 5 格雙向格 | `src/receipt/similarity.py`，JS 版 `src/web/trait-similarity.js`，共用案例 `tests/fixtures/similarity-cases.json` |
| 配對頁 | +30% 以上算相近、−10% 以下算互補，各取前 5；可依同區、同縣市、同地區篩選 | `src/web/match.html`、`match-filter.js`、`src/receipt/places.py`、`configs/regions.json` |
| 假用戶 | 8 種類型 × 5 人 = 40 人，2026 年 3–4 月的假發票 | `src/receipt/personas.py` |
| 網頁 | 單一 HTML 檔，JS 全部內嵌，GitHub Pages 公開中 | `scripts/build_report.py` → `invoice-insights.html` |
| 後端骨架 | FastAPI + SQLite：註冊、登入、demo 快速切換、品名即時分類、健康檢查，模型先用假替身；v2 網頁從 `/web/` 提供（10/15 完成角色 1 第 1 週） | `src/api/`、`src/ml/`、`src/web_v2/` |
| 測試 | Python 154 個（unittest）、JS 82 個（node:test），全部通過 | `tests/` |
| 分類實驗 | 品名 → 10 類。A：TF-IDF + 邏輯迴歸，macro-F1 0.62；B：bge-small-zh（512 維）+ 邏輯迴歸，macro-F1 0.66。只有 57 個人工確認品名，只能驗證 4 類 | `experiments/category-models/`、`docs/category-models-brief.md` |
| 屬性實驗 | Qwen3-4B（Q4_K_M，2.4 GB）判斷 16 個屬性。真實資料上模型單獨 F1 44%，加規則 94%（事後回測，不是獨立驗證） | `experiments/receipt-attributes/` |

**還沒有的：** 上傳與背景任務、品味向量和配對的 API、帳號管理、真的分類和屬性模型、CI、BERT。

### 18 格品味向量

- **雙向（−1～+1）**：spend 省錢↔享受、meals 快速解決↔好好吃飯、motive 超商：省錢↔省時、cooking 外食↔自己煮、sweet 低甜度↔高甜度、routine 固定習慣↔喜歡嘗鮮、travel 待在生活圈↔常出遊、stock 囤貨↔少量即買、days 上班日型↔休假日型、holiday 避開連假↔連假出遊
- **程度（0～1）**：sport 運動投入、driving 自己開車騎車、lifestyle 生活質感小物、tech 3C 投入、fun 娛樂體驗、pets_cat 養貓、pets_dog 養狗、alcohol 小酌

### 10 個消費類別

0 正餐、1 飲品、2 零食甜點、3 生鮮食材、4 運動、5 其他服務、6 交通、7 住宿、8 日用品、9 電子產品（10 = 待確認）

### 16 個品項屬性（Qwen 輸出）

clearance、sugar、quick、cooking、kitchen、sport_supply、sport_gear、car_care、bulk、home、stationery、fun、pet_food、pet_supply、species、alcohol，另外還有 7 個基本旗標：food、meal、drink、fresh、daily、tech、sport。**`null` 表示不知道，不能當成 `false`。**

## 3. 決策紀錄（2026-10-13 共 27 題）

| # | 主題 | 決定 |
|---|---|---|
| 1 | 期限與發表 | 約 4 週全職（10/14–11/10 左右）。每人講 8 分鐘：自己的部分加 demo。簡報之後再做 |
| 2 | 團隊 | 4 人，程式主要由 AI 寫，大家只懂基本 Python。團隊作品，也可當個人作品 |
| 3 | 兩層模型 | 第一層：BERT 把品名分成 10 類（TF-IDF、embedding 當比較基準）。第二層：Qwen 判斷 16 個屬性 |
| 4 | 負相關 | 「相近」和「互補」兩份清單。交友本來就不一定找完全相似的人 |
| 5 | AI 亮點 | 完整管線：LLM 標註 → 小模型 → API → 配對。要能說明迴歸、餘弦相似度、向量化 |
| 6 | 配對向量 | 沿用 18 格。Qwen 只取代關鍵字規則，提供屬性來源 |
| 7 | BERT 標註 | 本機 Qwen 先預標，4 人分工複核（真實品名不上傳外部服務） |
| 8 | 資料輸入 | 上傳電子發票 CSV，另加「輸入品名馬上看分類」的小框 |
| 9 | 假用戶 | 約 300 人，產生假發票後跑完整管線 |
| 10 | 前端 | 沿用現有網頁，改成向 FastAPI 要資料 |
| 11 | 登入 | 帳號密碼 + JWT，另外保留 demo 用的快速切換。10/15 補上帳號管理：查看與修改個人資料、修改密碼、刪除帳號（含所有資料）、刪除單一月份、登出（所有裝置一起登出），見 5.11 |
| 12 | 訓練資料不足 | 先用 AI 生成假品名把稀少類別補到每類 50 個；不夠再請組員提供發票 |
| 13 | 相似度公式 | 保留現有公式（含 0.25 收縮項） |
| 14 | Qwen 執行 | 背景處理 + 快取。改用約 5 GB 的模型，要重跑選型。RTX 4060 8G 從 10/14 起可用 |
| 15 | BERT | `bert-base-chinese`，在 4060 上訓練（4060 被占用時改用 Colab） |
| 16 | 資料庫 | SQLite，相似度用 Python 算。README 註明人數擴大後再改用 pgvector，以及原因 |
| 17 | 評估 | 分類比較表 + 配對驗證 + 抽 100 個品名人工複核 Qwen。**測試集只放真實品名** |
| 18 | 公開範圍 | 程式碼公開。真實發票、真實品名與其標註、模型檔都不進 git。10/15 補充：BERT 模型權重第 3 週公開在 Hugging Face（固定版本），訓練資料不公開 |
| 19 | 測試 | GitHub Actions 每次 push 跑全部測試，模型用假替身 |
| 20 | 概念說明 | 說明文件，加上配對頁的「計算過程」面板 |
| 21 | 啟動 | Python 虛擬環境 + 一鍵啟動檔，另做無 GPU 模式。10/15 補充：另外提供 Docker（`docker compose up`，無 GPU 模式，自動下載模型、匯入假用戶），給面試官和乾淨環境驗證用 |
| 22 | GitHub Pages | 現有版本凍結成 v1，README 放 v2 的 demo 影片或動圖 |
| 23 | API | 第 5 節：9 項功能、17 個端點（第 9 項帳號管理的 6 個端點是 10/15 加的） |
| 24 | 分工 | 角色 1–4（第 7 節） |
| 25 | 時程 | 第 8 節，盡量全部做完 |
| 26 | 發表 | 4 人 × 8 分鐘，簡報稍後再做 |
| 27 | 文件 | 只寫這一份總覽 |

## 4. 架構

```
瀏覽器（現有網頁改接 API）
   │  JWT
   ▼
FastAPI（src/api/）────────── SQLite（一個檔案）
   │                              users / jobs / items / item_cache / profiles
   ├─ 上傳 CSV → 背景任務
   │     invoices.py 解析
   │     → 品名分類（src/ml/category.py：BERT → 0–9）
   │     → 品項屬性（src/ml/attributes.py：查快取，沒有才問 Qwen）
   │     → signals.py / traits.py → 18 格品味向量 → 存 profiles
   ├─ 配對：similarity.compare(我, 每個人) → 相近前 5、互補前 5
   └─ 計算過程：逐格 我 × 對方 × 權重 → 加總 → ÷（長度相乘 + 0.25）

Qwen 跑在獨立的 llama.cpp server（只有有 4060 的電腦開）
沒開時 = 無 GPU 模式：只讀快取，沒看過的品名標「待分析」
```

建議的資料夾（第一週可以調整，但要 4 個人一起改）：

| 位置 | 內容 | 負責 |
|---|---|---|
| `src/receipt/` | 現有核心邏輯，盡量不改行為 | 全體 |
| `src/api/` | FastAPI：路由、資料庫、登入、背景任務 | 角色 1 |
| `src/ml/` | 模型介面與假替身：`category.py`、`attributes.py`、`fakes.py`、`fields.py`（共用的欄位名） | 角色 2、3 |
| `src/web_v2/` | v2 網頁，FastAPI 從 `/web/` 提供；`src/web/` 是 v1 報告的建置來源，凍結不動 | 角色 4 |
| `datasets/synthetic/` | 假品名和假用戶資料（JSONL），可以進 git | 角色 2、3 |
| `docs/team/` | 這份總覽、概念說明 | 全體 |

預設套件：`fastapi`、`uvicorn`、`sqlmodel`、`python-multipart`、`pyjwt`、`pwdlib[argon2]`（密碼雜湊）、`scikit-learn`、`torch`、`transformers`。Qwen 用 llama.cpp 的 `llama-server`，後端用 HTTP 呼叫它。Python 統一用 3.12。

**Docker（10/15 補上）：** 根目錄的 `Dockerfile` 和 `docker-compose.yml` 用無 GPU 模式包起整個服務。執行 `docker compose up` 後：第一次啟動會從 Hugging Face 下載固定版本的分類模型；`DEMO_MODE=1` 而且資料庫是空的時，會自動匯入假用戶。資料庫和模型放在 volume 裡，重建容器也不會不見。容器裡不跑 Qwen；有設定 `LLAMA_SERVER_URL` 時，就連到主機上的 llama-server。組員開發時仍以虛擬環境為主，Docker 是給面試官和乾淨環境驗證用的。

## 5. API 規格（2026-10-14 定案）

9 項功能、17 個端點（第 9 項帳號管理是 10/15 補上的，見 5.11）。這一節是正式規格；程式寫好後，FastAPI 自動產生的 `/docs` 要和這一節一致，不一致時改程式。

### 5.1 共通規則

- **路徑**：API 一律以 `/api` 開頭。v2 網頁放在 `src/web_v2/`，由同一個 FastAPI 從 `/web/` 提供，同一個網域，所以不用設 CORS。`src/web/` 是 v1 報告的建置來源，不提供也不為 v2 修改，要用的頁面由角色 4 複製到 `src/web_v2/`。不掛在 `/`，是因為那樣 POST 到不存在的 `/api` 路徑會被靜態檔案接走，回 405 而不是 404
- **格式**：JSON（UTF-8），欄位名用 snake_case。唯一例外：`/api/me/profile` 的 `months` 原樣沿用現有月報格式（`invoices.build_month` 的輸出，例如 `monthNumber`），現有網頁才不用改
- **登入**：除了標「免」的端點，都要帶 `Authorization: Bearer <access_token>`。JWT 用 HS256，`sub` 放 user_id（轉成字串），`key` 放這個帳號的 `token_key`，24 小時過期。`token_key` 是每個帳號一把隨機字串：換掉它，這個帳號在所有裝置上的 token 就一起失效（登出、改密碼都靠它，見 5.11）；帳號刪掉後 id 被新帳號重用時，新帳號的 `token_key` 不同，舊 token 也不會變成新帳號的
- **錯誤**：HTTP 狀態碼加 `{"detail": "<錯誤代碼>", "message": "<說明，可省略>"}`。錯誤代碼是固定的英文 snake_case，前端自己對應成中文。欄位格式錯誤回 422，格式同 FastAPI 預設（`detail` 是清單，每項有 `type`、`loc`、`msg`），但不回傳被拒絕的輸入值，因為那可能是密碼。需要登入的端點，沒帶 token、token 過期或已經失效都回 401 `not_authenticated`；這個 401 和登入失敗的 401 `bad_credentials` 都帶 `WWW-Authenticate: Bearer`。框架自己回的錯誤（例如不存在的路徑是 404、方法不對是 405）`detail` 是英文句子而不是代碼，前端遇到不認得的 `detail` 一律顯示通用錯誤訊息。程式本身出錯時回 500 `{"detail": "internal_error"}`，細節只留在伺服器的紀錄裡
- **數字**：`score` 這類小數不先四捨五入。要顯示的整數百分比另外給 `percent`，算法同 `similarity.percent`
- **18 格順序**：一律照 `configs/traits.json` 的順序
- **null**：表示「不知道」或「資料不夠」，不能當成 0 或 `false`

### 5.2 端點一覽

| # | 功能 | 方法與路徑 | 登入 | 成功 |
|---|---|---|---|---|
| 1 | 帳號 | `POST /api/auth/register` | 免 | 201 |
| | | `POST /api/auth/login` | 免 | 200 |
| | | `GET /api/auth/demo-users` | 免，只在 `DEMO_MODE=1` | 200 |
| | | `POST /api/auth/demo-login` | 免，只在 `DEMO_MODE=1` | 200 |
| 2 | 上傳發票 | `POST /api/invoices` | 要 | 202 |
| 3 | 處理進度 | `GET /api/jobs/{job_id}` | 要 | 200 |
| 4 | 品名即時分類 | `POST /api/items/classify` | 要 | 200 |
| 5 | 我的品味向量與月報 | `GET /api/me/profile` | 要 | 200 |
| 6 | 配對清單 | `GET /api/matches` | 要 | 200 |
| 7 | 計算過程 | `GET /api/matches/{user_id}/explain` | 要 | 200 |
| 8 | 健康檢查 | `GET /api/health` | 免 | 200 |
| 9 | 帳號管理 | `GET /api/me` | 要 | 200 |
| | | `PATCH /api/me` | 要 | 200 |
| | | `POST /api/me/password` | 要 | 200 |
| | | `DELETE /api/me` | 要 | 204 |
| | | `DELETE /api/me/months/{month}` | 要 | 204 |
| | | `POST /api/auth/logout` | 要 | 204 |

### 5.3 帳號

**`POST /api/auth/register`**：JSON `{"username": "amy", "password": "…", "display_name": "Amy"}`
- `username` 3–32 字元，只能用英數字和底線，不分大小寫（一律存成小寫，登入時也轉小寫比對）；`password` 8–128 字元，雜湊和比對前都先做 Unicode NFKC 正規化；`display_name` 可省略，1–20 字元，預設同 `username`，不能含控制字元、看不見的字元、私用字元、未指派字元或換行（例如零寬空白、方向控制字元）。`username` 不能以 `demo_` 開頭，那是留給假用戶的
- 回傳 201：`{"user_id": 301, "username": "amy", "display_name": "Amy"}`
- 錯誤：409 `username_taken`

**`POST /api/auth/login`**：表單（`application/x-www-form-urlencoded`）`username`、`password`，和 FastAPI 的 OAuth2 表單相同，`/docs` 的 Authorize 按鈕可以直接用
- 回傳：`{"access_token": "…", "token_type": "bearer", "expires_in": 86400}`
- 錯誤：401 `bad_credentials`（帳號不存在和密碼錯誤用同一個代碼）
- 密碼先做 NFKC 正規化再比對；超過 512 字元的一律當作密碼錯誤，不做正規化（註冊最多 128 字元，用分解寫法輸入也放得下）

**`GET /api/auth/demo-users`**：demo 快速切換的名單，只列假用戶
- 回傳：`[{"user_id": 1, "display_name": "咖啡上班族 A", "persona": "咖啡上班族"}, …]`
- `DEMO_MODE` 沒開時回 404，假裝這個端點不存在

**`POST /api/auth/demo-login`**：JSON `{"user_id": 1}`，不用密碼
- 回傳：同 login
- 只能切換成假用戶，註冊的真實帳號一定要用密碼登入
- `user_id` 是 JSON 整數，1 到 2^63−1；`true`、字串 `"2"`、`2.0` 或超出範圍都回 422
- `DEMO_MODE=1` 時，任何連得到伺服器的人都能用 demo 用戶登入，所以只在自己電腦或 demo 現場開。關掉之後，demo 用戶的 token 立刻失效，真實帳號不受影響
- 前端用 `GET /api/health` 的 `demo_mode` 決定要不要顯示快速切換，不要靠 404 的內容判斷
- 錯誤：404（`DEMO_MODE` 沒開，或沒有這個人）、403 `not_demo_user`

### 5.4 上傳與進度

**`POST /api/invoices`**：multipart，欄位名 `file`，一次一個財政部電子發票 CSV（一份一個月），上限 2 MB
- 伺服器先**當場**用 `invoices.build_month` 的規則解析，格式有錯直接回 400；解析成功才建立背景任務
- 同一個人重新上傳同一個月份，會取代那個月的舊資料
- demo 用戶不能上傳，回 403 `demo_user_read_only`（和 5.11 同一個代碼）：demo 帳號是大家共用的，上傳會把真實消費掛到公開的假用戶上（第 2 週實作）
- 「作廢」開頭的發票狀態（例如「作廢已確認」）直接跳過，不算消費；只有「開立已確認」會被計入，其他狀態回 400
- **金額低於 10 元（含 0 元和負數的折扣）或金額有小數的明細直接略過**，不算消費、不分析。月報總金額因此是折扣前的金額
- 數量有小數的明細（加油的公升數、秤重商品）保留，**數量當 1**。不然加油次數會消失，30 公升也會被「數量 ≥ 3」誤判成囤貨
- 現有 `build_month` 遇到作廢或小數都會直接報錯，5–8 月的真實發票就有這兩種情況，第二週接上傳前要先修。3–8 月真實發票共 336 列：作廢 2 列、金額規則略過 61 列，留下 273 列
- 回傳 202：`{"job_id": 12, "month": "2026-05", "rows": 35}`
- 錯誤：400 `invalid_csv`（`message` 寫原因，例如一份 CSV 有兩個月份）、413 `file_too_large`

**`GET /api/jobs/{job_id}`**
- 回傳：`{"job_id": 12, "month": "2026-05", "status": "running", "done": 10, "total": 25, "message": "判斷品項屬性"}`
- `status`：queued / running / done / failed
- `total` 是這份 CSV 不重複的品名數，`done` 是已經分類並判斷完屬性的品名數。無 GPU 模式下，快取裡沒有的品名直接標「待分析」，也算進 `done`
- `message`：目前步驟的中文說明；failed 時寫失敗原因
- 錯誤：404（任務不存在，或不是你的任務）

**背景任務的步驟：**
1. 列出不重複品名，呼叫 `classify()`。最高機率低於 `CATEGORY_MIN_PROB`（預設 0.5）的品名存成 10 待確認，不算進品味向量
2. 呼叫 `describe_items()`：先查 `item_cache`，沒有才問 Qwen。無 GPU 模式下沒有快取的回 `None`，算進 `pending_attributes`
3. 用這個人所有月份的資料重算 18 格，存進 `profiles`
4. `status` 改成 done。GPU 恢復之後，重新上傳同一個月份就能補算待分析的品名

### 5.5 品名即時分類

**`POST /api/items/classify`**：JSON `{"name": "鮮奶茶 微糖"}`，`name` 去掉頭尾空白後 1–100 字元，不能含控制字元、看不見的字元或換行
- 回傳：
  ```json
  {"name": "鮮奶茶 微糖",
   "category": {"id": 1, "name": "飲品", "prob": 0.91},
   "probs": [0.01, 0.91, 0.03, 0.0, 0.0, 0.02, 0.0, 0.0, 0.03, 0.0],
   "attributes": {"food": true, "drink": true, "sugar": 0.3, "alcohol": false, "fun": null, "…": "共 23 個欄位"},
   "attributes_status": "ready"}
  ```
- `category` 一律是模型的第一名（0–9），`probs` 是 10 類各自的機率
- `attributes`：16 個屬性加 7 個基本旗標，欄位名見 `src/ml/fields.py`。每個欄位都可能是 `null`
- 分類框不會在請求裡等 Qwen，只查快取（`describe_items(names, ask_model=False)`）。快取裡有 → `ready`。沒有 → `attributes` 為 `null`、`attributes_status` 為 `pending`
- 第 2 週起，GPU 模式下伺服器會把 pending 的品名排進背景分析，前端每 2 秒再問一次，最多 5 次。第 1 週還沒有這個排程，pending 不會自己變成 ready，前端先顯示「待分析」就好

### 5.6 我的品味向量與月報

**`GET /api/me/profile`**
- 回傳：
  ```json
  {"user_id": 301, "display_name": "Amy", "is_demo": false,
   "ready": true, "item_count": 57, "min_items": 20, "pending_attributes": 3,
   "areas": ["臺北市大安區", "新北市板橋區"],
   "traits": [
     {"id": "spend", "name": "省錢 ↔ 享受", "kind": "two_sided", "ends": ["省錢", "享受"], "value": 0.42},
     {"id": "sport", "name": "…", "kind": "level", "habit": "運動", "value": null}],
   "categories": [{"name": "正餐", "color": "#df646b"}],
   "months": {"2026-05": {"year": 2026, "monthNumber": 5, "rows": ["…現有格式"]}}}
  ```
- `traits` 一定有 18 筆。`ready` 為 false 表示有效品項少於 `min_items`，這時 18 格的 `value` 全是 `null`
- `item_count`：有效品項數，判斷 `ready` 用的就是它
- `areas`：生活圈，最多 2 個行政區（`places.areas_of`），可能是空陣列
- `categories`：11 類的名稱和顏色（`configs/report.json`），給現有月報畫面用
- 還沒上傳過的人：`ready` 為 false，`months` 為 `{}`

### 5.7 配對

**`GET /api/matches?kind=similar&scope=all`**
- `kind`：similar（相近，`percent` ≥ +30）或 opposite（互補，`percent` ≤ −10），預設 similar。門檻來自 `configs/traits.json` 的 `match`
- `scope`：all / district / city / region，也就是不限、同區、同縣市、同地區，對應 `places.distance` ≤ 0、1、2。預設 all
- 對象：自己以外、算得出品味向量的所有使用者（包含假用戶）
- 排序：similar 分數由高到低，opposite 由低到高；同分時依 `display_name` 的字碼順序，再依 `user_id`；取前 5 名
- 回傳：
  ```json
  {"kind": "similar", "scope": "all", "ready": true, "my_areas": ["臺北市大安區"],
   "eligible": 12, "within": 12,
   "people": [{"user_id": 7, "display_name": "咖啡上班族 C", "score": 0.6234, "percent": 62,
               "area": "臺北市中山區", "distance": 1}]}
  ```
- `eligible`：過門檻的人數，不看距離；`within`：過門檻又在範圍內的人數。前端用這兩個數字照 v1 的方式寫狀態文字
- `area`：對方離我最近的生活圈（`places.closest_area`），可能是 `null`
- 我自己資料不夠時：`ready` 為 false，`people` 為空陣列，`eligible` 和 `within` 都是 0
- 錯誤：400 `no_home_area`（看不出我的生活圈，`scope` 卻不是 all）

**`GET /api/matches/{user_id}/explain`**：任何一個使用者都能看，不限前 5 名
- 回傳：
  ```json
  {"user_id": 7, "display_name": "咖啡上班族 C", "comparable": true, "reason": null,
   "cells": [{"id": "spend", "name": "省錢 ↔ 享受", "kind": "two_sided",
              "mine": 0.42, "theirs": 0.30, "weight": 1, "shared": true, "product": 0.126, "part": 0.0615}],
   "shared_two_sided": 9, "min_shared_two_sided": 5,
   "dot": 1.26, "norm_mine": 1.5, "norm_theirs": 1.2, "shrink": 0.25, "denominator": 2.05,
   "score": 0.6146, "percent": 61}
  ```
- `cells` 一定有 18 筆，算法和 `similarity.compare` 完全一樣：
  - `shared`：兩邊都有值才是 true。不是 shared 的格子，`product` 和 `part` 為 `null`，也不算進長度
  - `product` = weight × mine × theirs；`dot` = 所有 `product` 的加總（也就是內積）
  - `norm` = √(Σ weight × 值²)，只算 shared 的格子
  - `denominator` = norm_mine × norm_theirs + shrink；`score` = dot ÷ denominator
  - `part` = product ÷ denominator，是每格對分數的貢獻，全部加起來等於 `score`
- `comparable` 為 false 時，`reason` 是 `not_enough_items`（任一方有效品項不夠）或 `too_few_shared`（共同的雙向格少於 5 格），`dot` 以下的欄位全部是 `null`
- 另外有一個 `network` 欄位，給連線圖用，格式和 v1 的 `traitNetworkData` 相同（`build.trait_network_data`），只是 `friends` 換成 `mine` 和 `theirs` 兩個人：
  ```json
  "network": {"model": {"…": "同 similarity_model"}, "traits": ["…"], "signals": ["…"], "readout": {"…": "…"},
              "mine":   {"vector": ["…18 格"], "pushes": ["…"], "signals": ["…46 個訊號"], "items": [[["鮮奶茶", 6], ["美式咖啡", 2]], null]},
              "theirs": {"vector": ["…"], "pushes": ["…"], "signals": ["…"], "items": ["…"]}}
  ```
  `src/web/trait-network.js`（複製到 `src/web_v2/` 之後）可以直接拿來畫。資料不夠的人，四個欄位都是 `null`
- `items` 是每個訊號買最多次的 3 個品名和出現的發票張數，品名一律經過 5.8 的處理
- 錯誤：404（沒有這個人）、400 `self`（查自己）

### 5.8 品名隱私

API 回傳**別人**的品名時（目前只有 `explain` 的 `network.theirs.items`），一律經過 `items.label`，`mine.items` 也照同樣規則處理：

- 去掉地名：所有縣市（含「臺中」這種不帶縣市的簡稱）、縣轄市、這個人買過東西的每個行政區（含「大安」這種簡稱）、`configs/attributes.json` 的 `place_words`（例如「淡水」）。台、臺視為同一個字
- 住宿一律顯示「旅館住宿」；長途交通只顯示票種，不顯示站名
- 跟地點有關的 4 個訊號（`list_items` 為 false）不列品名
- 每個訊號最多 3 個品名，最長 20 字。去掉地名後只剩數字或符號的，改顯示類別名稱
- 不回店家名稱、發票號碼、日期、金額
- 漏網的地名（商圈、地標、分店名）加進 `place_words`，不要在 API 裡另寫一套規則

2026-10-14 用 3–8 月真實發票檢查（只看數量）：245 種商品中，2 種改顯示通用名稱、1 種去掉了地名。處理後還有 2 種含「店」字，都是 0 元明細，照 5.4 的金額規則會被略過，不會顯示

### 5.9 健康檢查

**`GET /api/health`**
- 回傳：`{"status": "ok", "gpu_mode": false, "demo_mode": true, "models": {"category": "fake", "attributes": "cache_only"}}`
- `gpu_mode`：連得到 `LLAMA_SERVER_URL` 的 llama-server 就是 true
- `models.category`：fake / tfidf / embedding / bert，設定的模型檔不存在或下載失敗時是 `unavailable`（10/15 補上，這時即時分類回 503 `model_unavailable`，上傳的背景任務變成 failed）；`models.attributes`：fake / qwen / cache_only（無 GPU 模式）

### 5.10 設定（`.env`，repo 只放 `.env.example`）

| 變數 | 預設 | 說明 |
|---|---|---|
| `JWT_SECRET` | 無，一定要設 | 簽 JWT 用的密鑰，至少 32 字元 |
| `JWT_EXPIRE_MINUTES` | 1440 | token 有效時間 |
| `DEMO_MODE` | 0 | 1 = 開放 `demo-users` 和 `demo-login` |
| `DATABASE_URL` | `sqlite:///data/app.db` | 放在 `/data/` 底下，不會進 git。相對路徑一律從 repo 根目錄算起，不管在哪個資料夾啟動 |
| `LLAMA_SERVER_URL` | `http://127.0.0.1:8080` | Qwen 的 llama-server |
| `CATEGORY_MODEL` | fake | fake / tfidf / embedding / bert |
| `ATTRIBUTES_MODEL` | fake | fake / qwen |
| `CATEGORY_MIN_PROB` | 0.5 | 低於這個機率的品名歸到 10 待確認 |
| `CATEGORY_MODEL_DIR` | `models/category` | `CATEGORY_MODEL=bert` 時讀模型的資料夾（`/models/` 不進 git）。10/15 補上 |
| `CATEGORY_MODEL_REPO` | 空 | Hugging Face 上公開的分類模型庫；資料夾裡沒有模型時從這裡下載。10/15 補上 |
| `CATEGORY_MODEL_REVISION` | 空 | 要下載的固定版本（commit），和 `CATEGORY_MODEL_REPO` 一起設定。10/15 補上 |

設定留空等於用預設值。密鑰短於 32 字元、數字寫錯或超出範圍、模型名稱不在清單裡時，伺服器啟動時停下來，用一行訊息指出是哪個變數。`src/ml/` 有真的模型之前，`CATEGORY_MODEL` 和 `ATTRIBUTES_MODEL` 只有 `fake` 能用，設成別的值同樣會停下來。

### 5.11 帳號管理（2026-10-15 補上）

格式和錯誤規則同 5.1。假用戶（`is_demo`）不能改名、改密碼、刪帳號或刪月份，一律回 403 `demo_user_read_only`（上傳發票也一樣，見 5.4）；登出照常可以用。

**`GET /api/me`**
- 回傳：`{"user_id": 301, "username": "amy", "display_name": "Amy", "is_demo": false, "months": ["2026-07", "2026-08"]}`
- `months`：已上傳的月份，由舊到新

**`PATCH /api/me`**：JSON `{"display_name": "愛喝咖啡的人"}`，1–20 字元
- 回傳：同 `GET /api/me`。`username` 不能改

**`POST /api/me/password`**：JSON `{"current_password": "…", "new_password": "…"}`，新密碼 8–128 字元
- 回傳：同 login（一個新的 token）。改完之後，這個帳號的 `token_key` 換成新的，舊的 token 全部失效，回傳的新 token 帶著新的 key
- 錯誤：403 `wrong_password`

**`DELETE /api/me`**：JSON `{"password": "…"}`
- 回傳 204。依序刪掉這個人的 `items`、`jobs`、`profiles`、`users`，再刪掉 `item_cache` 裡已經沒有任何 `items` 用到的品名
- 錯誤：403 `wrong_password`

**`DELETE /api/me/months/{month}`**：`month` 是 `YYYY-MM`
- 回傳 204。刪掉那個月的 `items` 和 `jobs`，重算 18 格；`item_cache` 的清理方式同上
- 錯誤：404 `month_not_found`、409 `job_in_progress`（那個月還有 queued 或 running 的任務）

**`POST /api/auth/logout`**
- 回傳 204。換掉這個人的 `token_key`，這個帳號在**所有裝置**上的 token 都會失效
- `users.token_key` 第 1 週就有了，不必再加欄位。登出後馬上重新登入，新拿到的 token 可以用

## 6. 模型介面（角色 2、3 交給角色 1）

```python
# src/ml/category.py
def classify(names: list[str]) -> list[dict]:
    """每個品名回傳 {"category": 0–9, "probs": [10 個機率]}。"""

# src/ml/attributes.py
def describe_items(names: list[str], ask_model: bool = True) -> list[dict | None]:
    """每個品名回傳 16 個屬性 + 7 個基本旗標（欄位名見 src/ml/fields.py），
    還沒分析過的回傳 None。null 是不知道，不是 false。
    ask_model=False 時只查快取、不呼叫 Qwen（給即時分類框用）。"""
```

`src/ml/fakes.py` 提供同樣介面的假替身，回傳固定結果。後端和 CI 一開始全部用假替身，模型好了再換成真的。

回傳值一律用一般的 Python 型別（numpy 的結果先 `.tolist()`），否則 API 會回 500。在自己的測試裡呼叫 `tests/model_contract.py` 的 `check_classify(self, classify)` 和 `check_describe(self, describe_items)`，就能確認格式對不對。`probs` 不要四捨五入（至少保留 4 位小數），檢查允許的加總誤差是 0.001。

`describe_items` 連不到 llama-server 時回 `None`，不要丟例外；呼叫 Qwen 要設 timeout。兩個函式會被不同的執行緒同時呼叫（FastAPI 用執行緒跑 `def` 路由），PyTorch 模型和 tokenizer 要自己加鎖。

## 7. 角色分工

### 角色 1：後端與配對（組長）

- **負責：** FastAPI、SQLite、登入與帳號管理、CSV 上傳與背景任務、配對和計算過程 API、一鍵啟動、無 GPU 模式、Docker、GitHub Actions
- **交出：** 第 5 節的 17 個端點，每個都有測試；`docker compose up` 能在乾淨的電腦上跑起 demo
- **先讀：** `src/receipt/invoices.py`、`signals.py`、`traits.py`、`similarity.py`、`personas.py`、`configs/traits.json`
- **每週：**
  1. API 規格和 4 人確認；FastAPI 骨架、資料表、註冊登入、`/health`；用假替身跑通
  2. 上傳 → 背景任務 → 品味向量；`/jobs`、`/me/profile`、`/matches`
  3. `/matches/{id}/explain`；換上真模型；匯入 300 個假用戶；CI 綠燈
  4. 修錯；`start.bat`；README 架構段落；8 分鐘講稿素材
- **完成標準：** 在沒有 GPU 的電腦上，一鍵啟動就能跑完整 demo；CI 全綠

### 角色 2：分類模型

- **負責：** 生成假品名、分配真實品名的複核、TF-IDF / embedding / BERT 三個模型的訓練與比較
- **交出：** `src/ml/category.py` 的 `classify()`；比較表（macro-F1、準確率、模型大小、速度）；混淆矩陣；概念說明的「迴歸」段落；第 3 週把 BERT 模型公開到 Hugging Face（固定版本，附模型卡）
- **先讀：** `experiments/category-models/README.md`、`RESULTS.md`、`RESULTS-B.md`、`LABELING.md`、`docs/category-models-brief.md`、`configs/report.json`
- **每週：**
  1. 稀少類別生成假品名，每類補到至少 50 個，存成 `datasets/synthetic/item-names.jsonl`（`name`、`category`、`source="synthetic"`）；整理真實品名測試集（只留在本機）
  2. 用新資料重跑 A、B；訓練第一版 BERT
  3. 比較表、混淆矩陣；把 `classify()` 交給角色 1
  4. 修錯；講稿素材
- **完成標準：** 三個模型在**同一份只含真實品名的測試集**上比較；測試資料不足的類別要在報告裡註明不計分

### 角色 3：LLM 屬性與假用戶

- **負責：** 在 4060 上重新選型、Qwen 介接、快取、100 筆人工複核、300 個假用戶
- **交出：** `src/ml/attributes.py` 的 `describe_items()`；假用戶資料；複核結果和 F1；配對驗證（同類型的人有沒有互相出現在相近前 5 名）
- **先讀：** `experiments/receipt-attributes/CLAUDE.md`、`README.md`、`RESULTS.md`、`INTEGRATION.md`（**接入契約，必讀**）、`SELECTED_MODEL.json`；`src/receipt/attributes.py`、`personas.py`
- **每週：**
  1. 4060 環境；用實驗資料夾的同一套評估，比較 Qwen3-4B 和約 5 GB 的候選模型（例如 Qwen3-8B Q4_K_M）；先用 0.5B 模型在 CPU 上把流程接通
  2. 屬性介接取代 `attributes.describe` 的來源（`channel_of` 保留）；快取；`personas.py` 擴充到約 300 人
  3. 4 人分著做 100 筆人工複核並算 F1；配對驗證；跑完假用戶品名的 Qwen 結果，把快取放進 git
  4. 修錯；講稿素材
- **注意：** `INTEGRATION.md` 列了幾個要明確決定的地方：甜度沒寫時回 `null`、fun 的英文值要對應成中文、`null` 不等於 `false`。`experiments/receipt-attributes/CLAUDE.md` 的限制只適用於那個實驗資料夾，正式介接寫在 `src/ml/`

### 角色 4：前端與展示

- **負責：** 現有網頁改接 API、登入和上傳畫面、帳號設定頁、品名即時分類框、計算過程面板、概念說明文件、README、發表素材整合
- **交出：** v2 網頁（由 FastAPI 提供）；`docs/team/concepts.md`（向量化、餘弦與內積，用假資料舉例）；README 的 v2 影片或動圖
- **先讀：** `src/web/` 全部（特別是 `match.html`、`match-filter.js`、`trait-similarity.js`、`taste-profile.js`）、`src/receipt/build.py`
- **每週：**
  1. 把網頁的資料來源抽成一層，先接角色 1 的假資料 API；登入畫面
  2. 上傳畫面、處理進度、品名即時分類框
  3. 計算過程面板；概念說明文件
  4. README；整合 4 人的發表素材
- **注意：** 根目錄的 `invoice-insights.html` 就是 GitHub Pages 上的 v1，**不要覆蓋它**。v2 的輸出換別的位置
- **v2 網頁放在 `src/web_v2/`：** FastAPI 從 `/web/` 提供它（現在只有一個預留的 `index.html`）。`src/web/` 是 v1 報告的建置來源，凍結不動、也不提供；需要的頁面和 JS 從 `src/web/` 複製到 `src/web_v2/` 再改（10/15 團隊決定）

## 8. 時程與砍功能順序

| 週 | 日期 | 全隊目標 |
|---|---|---|
| 1 | 10/14–10/20 | API 規格定案；後端骨架用假替身跑通；假品名；4060 環境與選型 |
| 2 | 10/21–10/27 | 上傳、背景任務、快取；分類框 pending 品名的背景分析；A/B 重跑與 BERT 第一版；Qwen 介接；300 個假用戶；登入畫面 |
| 3 | 10/28–11/03 | **整條管線串通**；評估三項；計算過程面板；CI |
| 4 | 11/04–11/10 | **11/04 起停止加功能，只修錯誤**；文件、README、發表素材 |

落後時依序砍：① 5 GB 模型退回 Qwen3-4B → ② 人工複核從 100 筆縮成 50 筆 → ③ 處理進度只顯示「處理中／完成」。

**不能砍：** 登入、上傳、品名分類、18 格品味向量、相近和互補清單、計算過程面板。

## 9. 協作規則

- 每個角色在自己的分支工作（例如 `role-1/upload-api`），開 PR 合併進 `main`，CI 通過才合併
- 介面先定好再開發；別人的部分還沒好，就用假替身，不要等
- 改到別人負責的檔案時，PR 裡要標註那個角色
- 修改 `src/receipt/` 的行為之前，先確認全部測試仍然通過（`.venv/Scripts/python.exe -m unittest discover -s tests` 和 `node --test "tests/*.test.cjs"`）
- commit 訊息用英文，文件用繁體中文

## 10. 隱私規則（repo 是公開的）

- **絕對不進 git：** 真實發票 CSV、真實品名和它們的標註、店名、模型檔、`.env`
- `.gitignore` 已經擋掉 `*.csv`、`/data/`、`/models/`、`/runtime/`，以及圖片檔（`*.png`、`*.jpg`、`*.gif` 等）
  - 假資料請存成 JSONL，放在 `datasets/`
  - README 要用的圖，要在 `.gitignore` 加 `!` 例外
- 真實品名只能用本機模型處理，不可以貼到雲端 AI 或線上服務；假品名可以
- 評估報告只放數字，逐筆結果留在本機
- 配對時，對方會看到你每個訊號買最多次的品名（去掉地名後，見 5.8），但看不到店家、日期和金額
- BERT 分類模型的權重會公開在 Hugging Face。模型卡要寫明訓練資料包含真實品名，但資料本身不公開

## 11. 評估要交出的東西

1. **分類比較表**：A / B / BERT 的 macro-F1、準確率、模型大小、1000 筆速度，加上混淆矩陣（角色 2）
2. **配對驗證**：300 個假用戶裡，同類型的人出現在彼此相近前 5 名的比例，以及相反類型出現在互補清單的比例（角色 3，角色 1 協助）
3. **Qwen 複核**：抽 100 個品名，4 人分著檢查，算出各屬性的 F1（角色 3 整理）

## 12. 換電腦交接（2026-10-14 換到有 RTX 4060 的電腦）

### 程式碼

```
git clone https://github.com/lee851104/receipt.git
git checkout feature/matching-system   # 合併進 main 之後改用 main
```

### 要手動複製的檔案（被 git 忽略，用隨身碟或私人雲端，不要放公開的地方）

| 路徑 | 內容 |
|---|---|
| `0301-0331.csv`、`0401-0430.csv`（根目錄） | 3、4 月真實發票 |
| `rawdata/` | 5–8 月真實發票 |
| `data/private/` | 人工確認的品名分類、私人報告設定。**一定要放在 `data/` 底下**，放在根目錄的 `private/` 不會被 `.gitignore` 擋住 |
| `experiments/receipt-attributes/private/`、`results/` | 屬性實驗的真實資料和結果 |
| `experiments/category-models/data/`、`outputs/` | 分類實驗的標註資料和結果 |

不用複製的：`.venv/`（重建）、`models/`（用各實驗的 `download_models.py`、`download_embedding.py` 重新下載）、`invoice-insights-private.html` 和 `report-data.js`（可以重新 build）、`__pycache__/`。

### 環境

1. 安裝 Python 3.12、Node.js 24、Git。可以順便裝 GitHub CLI（`gh`），開 PR 比較方便。用 uv 建虛擬環境最快：`uv venv --python 3.12 .venv`
2. 安裝套件，再確認現有測試通過。每個人都要裝 `requirements.txt`，API 的測試需要它；之後一律用 `.venv` 裡的 Python。不要用 `uv sync`：`pyproject.toml` 沒有列這些套件，它會把它們移除：
   ```
   uv pip install --python .venv/Scripts/python.exe -r requirements.txt
   .venv/Scripts/python.exe -m unittest discover -s tests -v
   node --test "tests/*.test.cjs"
   ```
   預期結果：Python 154 個、JS 82 個全部通過
3. 後端（角色 1 的第一週成果）：
   - 複製 `.env.example` 成 `.env`，`JWT_SECRET` 填一串至少 32 字元的亂碼：`.venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(32))"`
   - 放入 demo 用戶：`.venv/Scripts/python.exe -m src.api.seed`（跑幾次都可以，只會補上還沒有的人；名單只能往後加，資料庫裡的帳號和名單對不上時會停下來並說明，這時刪掉 `data/app.db` 再重來）
   - 啟動：`.venv/Scripts/python.exe -m uvicorn src.api.main:app --reload`，打開 `http://127.0.0.1:8000/docs`。v2 網頁在 `http://127.0.0.1:8000/web/`，角色 4 做好之前只有一個預留頁
   - 改了 `.env` 要手動重啟伺服器（`--reload` 只看 `.py` 檔）
   - `src/api/tables.py` 的資料表有變動時，刪掉 `data/app.db` 再重新放入 demo 用戶
   - `DEMO_MODE=1` 時不要加 `--host 0.0.0.0`，啟動時會印出提醒
4. 4060：
   - 安裝 NVIDIA 驅動，用 `nvidia-smi` 確認看得到顯示卡
   - PyTorch 要裝 CUDA 版：到 pytorch.org 選 Windows + pip + CUDA 12.x 取得安裝指令，然後用 `python -c "import torch; print(torch.cuda.is_available())"` 確認輸出 `True`
   - PyTorch 用 `uv pip install --python .venv/Scripts/python.exe torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128`（和分類實驗 B 同版本）
   - llama.cpp 要用 CUDA 版的 Windows 執行檔（GitHub releases 裡名稱有 `cuda` 的那個，加上同版本的 `cudart-llama-bin-win-cuda-12.4-x64.zip`），解壓到 `runtime/llama-b11557-cuda/`，`gpu_layers` 設成全部載入。用 `llama-server.exe --list-devices` 確認看得到 `CUDA0`

### 其他

- 到 GitHub repo 的 Settings → Collaborators，邀請另外 3 位組員
- Claude 的記憶只存在舊電腦上。在新電腦上開始工作時，先請 Claude 讀這份文件

## 13. 角色之間的交接

要轉告別的角色的事寫在這裡，最新的放最上面，每則註明日期和來源。改到別人負責的檔案之前，也先在這裡寫一行。

### 13.4 角色 3 接入與審查修正（2026-10-15，來源：角色 3 worktree、原 role3-handoff 與本次審查）

**給角色 1**
- 2.15：以 `AttributeDescriber(server_url=settings.llama_server_url)` 提供 `backends.describe_items`；`ATTRIBUTES_MODEL=qwen` 的正式啟用由角色 1 接入 `src/api/backends.py`。本次審查修正沒有修改角色 1 的 API 檔案。
- 每列明放 `attributes`（23 欄字典或 `None`）；省略欄位仍走 v1，`None` 才是待分析。7 個基本旗標只供儲存/API 回傳；現有訊號依舊使用類別，包含 `food = category in FOOD`。已分析的 `fun=null` 是非娛樂、`species=null` 是未寫物種；布林 null 才是未知。待分析的寵物店發票若沒有已知物種，不拆給貓狗。
- `ask_model=True` 會等同一實例的前一筆推論完成，不再因等鎖超過 60 秒而偽裝成待分析；60 秒僅限制單次 HTTP。角色 1 請由上傳背景工作呼叫，兩份上傳會排隊；即時查詢用 `ask_model=False`，不等推論鎖。預設函式的 `LLAMA_SERVER_URL` 僅在首次非空呼叫建立時檢查；無效會記錄一次不含網址／品名的錯誤並回全 `None`，修正設定後須重啟程序。直接建構實例仍會立即檢查設定。
- `(model_version, name)` mapping 是程序內快取，不是資料庫；持久化 `item_cache` 與版本清理由 2.3/2.4 負責。4.7 必須等 2.3/2.4 完成，再把假發票、屬性與 profiles 接入一般管線；不要把目前核心驗證當成完整 seed 已完成。
- 介面只有 names，merchant 固定空字串、quantity=1；品項數量的 bulk 補位只在計算副本。新版採單筆推論、輸入只去開頭「示範」、保留原名快取鍵；prompt hash 與 input-v2:batch1 已進 model_version。換版本須重算舊屬性，不能沿用舊版本 cache。
- `build_personas(calendar, total=300)` 尾端擴充、保留原 40 人順序；v1 未指定 total 仍是 40 人。先前 seed 入口改為 300 的變更請在角色 1 合併時確認，本次不再修改該檔案。
- 107 筆假品名逐筆對照見 `docs/results/synthetic-cache-review.md`，舊／新模型輸出分存 `datasets/synthetic/attribute-cache.model-v1.jsonl`、`attribute-cache.model-v2.jsonl`；有效快取保留每欄 corrections。2026-10-15 使用者檢查並確認全部 107 筆：46 筆為 `human_corrected`、61 筆為 `human_confirmed`，保留助理準備與使用者確認的來源，並用屬性雜湊避免重建或後續修改誤用核准；此確認僅涵蓋公開假品名。配對數字見 `docs/results/matching.md`，僅核心公式，尚未驗證分類/API/DB 端到端。
- 4.8（10/15 使用者續作要求）：100 筆真實品名已用新版模型全部重跑，舊 `predictions.jsonl` 與四份空白盲標檔保留。使用者改採「先由本機模型預標，再由本人審核」，所以新增稿標示 `review_method=model_assisted`，不宣稱獨立盲標。私人根目錄為主資料夾 `C:\Users\User\Desktop\AI_project\receipt\data\private\attribute-review-20261015\`；新版預測為 `predictions-01cd0f32b598.jsonl`，待審稿與中文檢查表在 `assisted-01cd0f32b598\`。2026-10-15 使用者已確認 100/100 筆，保留 1 筆／1 欄人工修正；4.8 已完成，23 欄彙總見 `docs/results/attributes.md` 與 `attributes.json`。這批為使用者審核模型預標，並非四人獨立盲標；品名只准本機腳本處理，畫面只印彙總。
- `scripts/predict_private_attributes.py` 可依目前版本產生私有預測，加 `--assisted` 產生四份各 25 筆待審稿；不覆寫既有預測或人工稿。`scripts/attribute_review.py` 檢查 ID/品名一致、23 欄型別、模型版本與全部 100 筆人工狀態，未完成就拒絕正式評分。布林以 true 為正例，三個列舉欄位用非 null 類別 micro 指標；gold=null 排除、模型 null 對已知正例計漏判，分母為零顯示 —。本批已通過人工確認門檻並產生完整指標；進度彙總見 `docs/results/attribute-review-status.json`。
- 4.7 相依更新（來源：角色 1 分支 `role-1/uploads`，`873f46c`）：2.3 已完成，2.4 的分類／快取／背景分析已完成，但 `profiles` 重算仍在下一批；因此完整 seed 尚不能驗收，本角色未另建替代的資料庫管線。
- 已確認資料可在角色 3 worktree 執行下列命令重現 `docs/results/attributes.md` 與 JSON（未完成會回傳 exit 2，不寫正式報告）：

```powershell
$reviewRoot = 'C:\Users\User\Desktop\AI_project\receipt\data\private\attribute-review-20261015'
& 'C:\Users\User\Desktop\AI_project\receipt\.venv\Scripts\python.exe' -m scripts.attribute_review --review-dir "$reviewRoot\assisted-01cd0f32b598" --predictions "$reviewRoot\predictions-01cd0f32b598.jsonl"
```

- 工作區為 `codex/role-3/attributes` worktree；共用主資料夾 Python 與 llama.cpp，不升級共用套件。本角色此次只修改自身檔案與 `src/receipt/` 新增的外部屬性邏輯。

### 13.3 角色 1 轉告（2026-10-15，第 2 週上傳管線，分支 `role-1/uploads`）

上傳（5.4）、任務進度和即時分類的屬性快取（5.5）都接好了，規格的增補都標了「10/15」。品味向量的重算（5.4 第 3 步）、`GET /api/me/profile` 和帳號管理在下一批。

**給所有人**
- 資料表變了（多了 `jobs`、`items`、`item_cache`、`profiles`，外鍵會檢查）。合併這個分支之後，在自己的 worktree 刪掉 `data/app.db*`（資料庫和它的 `-wal`、`-shm` 檔），再跑一次 seed
- 伺服器只能開一個行程（不要 `--workers`），見 5.10
- 程式的錯誤訊息和 log 都不能帶品名：資料庫的錯誤已經設定成不印參數，自己寫的例外訊息也不要把品名放進去（第 10 節）

**給角色 2**
- 上傳的背景任務對一個月份的所有不重複品名**呼叫一次** `classify(names)`（最多 2000 個）。回傳的筆數一定要等於 `len(names)`、順序相同；少一筆或丟出例外，整個任務就變成 failed
- 即時分類框每次呼叫 `classify([name])`，在請求裡同步執行，所以單筆最好在 CPU 上 1 秒內回來

**給角色 3**
- 後端自己管 `item_cache`（品名加模型名稱一筆，`ON CONFLICT DO NOTHING`）。只有快取裡沒有的品名才會交給 `describe_items`：上傳時每批最多 20 個，模型可用時 `ask_model=True`；即時分類框先用 `ask_model=False`，GPU 模式下再在背景用 `ask_model=True` 問一次。回傳的筆數一定要等於 `len(names)`
- 模型是否可用看 `gpu_probe()`（`GET {LLAMA_SERVER_URL}/health`）。上傳任務一次只跑一個，但即時分類框的背景分析可能同時呼叫，所以 `describe_items` 裡呼叫 llama-server 的地方還是要加鎖
- 上傳任務裡 `describe_items` 丟出例外會讓任務變成 failed；即時分類框的背景分析失敗只記 log，品名維持待分析。連不到 llama-server 時照第 6 節回 `None`，不要丟例外

**給角色 4**
- 上傳：`POST /api/invoices`（multipart，欄位名 `file`）回 202 的 `job_id` 之後，每 2 秒問 `GET /api/jobs/{job_id}`，直到 `done` 或 `failed`；進度條用 `done / total`，文字用 `message`。別人的任務在跑時會停在 `queued` 一陣子，是正常的
- 錯誤：400 `invalid_csv` 顯示 `message`（英文，例如缺哪個欄位）；413「檔案超過 2 MB」；403 `demo_user_read_only`「示範帳號不能上傳」
- 即時分類框：`pending` 現在會自己變成 `ready`（GPU 模式，或假模型），照 5.5 每 2 秒再問、最多 5 次；503 `model_unavailable` 顯示「分類模型暫時無法使用」

### 13.1 同一台電腦用 worktree 分開做（2026-10-15）

4060 電腦上每個角色一個 git worktree、一個自己的分支（例如角色 1 在主資料夾 `C:\Users\User\Desktop\AI_project\receipt`，角色 2 在 `C:\Users\User\.codex\worktrees\receipt-role2\receipt`）。

- **被 git 忽略的東西不會跟著 worktree 走**：`.venv`、`.env`、`data/`、`rawdata/`、根目錄的 CSV、`models/`、`runtime/` 只在主資料夾
- **Python 共用主資料夾的 `.venv`**：在自己的 worktree 根目錄執行 `C:\Users\User\Desktop\AI_project\receipt\.venv\Scripts\python.exe`。這個環境大家共用，要裝或升級套件之前先在這裡寫一行
- **私人資料用絕對路徑讀主資料夾的檔案**，不要另外複製到別的地方，更不能放進會被 git 追蹤的位置
- **連接埠**：角色 1 的 API 伺服器用 8000，角色 3 的 llama-server 用 8080。其他人要自己開 API 伺服器時用 `--port 8001` 之類的別的埠；每個 worktree 有自己的 `.env` 和 `data/app.db`
- **顯示卡只有一張 4060 8GB**：角色 2 訓練 BERT 和角色 3 跑 Qwen 不要同時進行，開始前先看 `nvidia-smi` 有沒有人在用
- **合併順序**：角色 1 的骨架（PR #7）先合併進 `main`，其他角色再把最新的 `main` 合併進自己的分支

### 13.2 角色 1 轉告（2026-10-15，PR #7 後端骨架）

**給角色 2**
- `src/ml/fields.py`（欄位名）和 `src/ml/fakes.py`（假替身）已經有了。`src/ml/category.py` 的 `classify()` 照第 6 節交出：回傳一般的 Python 型別、`probs` 不要四捨五入；在你的測試裡呼叫 `tests/model_contract.py` 的 `check_classify(self, classify)`
- 57 筆人工確認品名在主資料夾的 `data/private/category-review-20261012/labeled-items.jsonl`（JSONL，`review_status` 全是 `human_confirmed`）。重跑 A/B 實驗時，複製成 `experiments/category-models/data/items.jsonl`（被 git 忽略）
- 把模型接進後端（`src/api/backends.py`）是角色 1 的工作（OpenSpec tasks 2.15），你交出 `classify()` 就好

**給角色 3**
- `describe_items(names, ask_model=True)`：`ask_model=False` 時只查快取（即時分類框用）；沒分析過、或連不到 llama-server 時回 `None`，不要丟例外；呼叫 Qwen 要設 timeout、要加鎖。用 `tests/model_contract.py` 的 `check_describe(self, describe_items)` 測
- llama.cpp 的 CUDA 版（b11557，和實驗同一版）已經放在主資料夾的 `runtime/llama-b11557-cuda/`。後端用 `GET {LLAMA_SERVER_URL}/health` 判斷 GPU 模式，預設 `http://127.0.0.1:8080`
- 假用戶擴充到約 300 人時：seed 依位置命名（`demo_001` 起），清單只能從尾端加。`build_personas` 的順序或名字一變，seed 會停下來，要刪掉 `data/app.db` 重新 seed，擴充時請一起考慮
- demo 用戶之後不能上傳或修改資料（403 `demo_user_read_only`）

**給角色 4**
- v2 網頁放 `src/web_v2/`，伺服器從 `/web/` 提供；需要的頁面從 `src/web/` 複製過去再改，`src/web/` 本身不要改（它是 v1 的建置來源）
- 本機 API 在 `http://127.0.0.1:8000`，文件在 `/docs`。錯誤一律是 `{"detail": "<代碼>"}`；422 的 `detail` 是清單；程式出錯回 500 `internal_error`；401 時回登入畫面
- 要不要顯示 demo 快速切換，看 `GET /api/health` 的 `demo_mode`；名單用 `GET /api/auth/demo-users`
- 即時分類框：第 1 週 `attributes_status` 為 `pending` 時不會自己變成 `ready`，先顯示「待分析」
