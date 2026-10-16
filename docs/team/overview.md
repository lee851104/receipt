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
| 測試 | Python 295 個（unittest）、JS 82 個（node:test），全部通過 | `tests/` |
| 分類實驗 | 品名 → 10 類。A：TF-IDF + 邏輯迴歸，macro-F1 0.62；B：bge-small-zh（512 維）+ 邏輯迴歸，macro-F1 0.66。只有 57 個人工確認品名，只能驗證 4 類 | `experiments/category-models/`、`docs/category-models-brief.md` |
| 屬性實驗 | Qwen3-4B（Q4_K_M，2.4 GB）判斷 16 個屬性。真實資料上模型單獨 F1 44%，加規則 94%（事後回測，不是獨立驗證） | `experiments/receipt-attributes/` |

**還沒有的：** 配對的 API、帳號管理、真的分類和屬性模型、CI、BERT。上傳與背景任務（5.4）已經有了（10/15 完成角色 1 第 2 週第一批，分支 `role-1/uploads`，PR #8）；任務最後的品味向量重算和 `GET /api/me/profile`（5.6）也有了（第 2 週第二批，分支 `role-1/profiles`）。

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
| 11 | 登入 | 帳號密碼 + JWT，另外保留 demo 用的快速切換。10/15 補上帳號管理：查看與修改個人資料、修改密碼、刪除帳號（含所有資料）、刪除單一月份、登出（所有裝置一起登出，假用戶除外），見 5.11（10/16 補上） |
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
   │     → 品項屬性（後端先查 item_cache，沒有的才交給 src/ml/attributes.py 問 Qwen，結果由後端存進 item_cache）
   │     → signals.py / traits.py → 18 格品味向量 → 存 profiles
   ├─ 配對：similarity.compare(我, 每個人) → 相近前 5、互補前 5
   └─ 計算過程：逐格 我 × 對方 × 權重 → 加總 → ÷（長度相乘 + 0.25）

Qwen 跑在獨立的 llama.cpp server（只有有 4060 的電腦開）
沒開時 = 無 GPU 模式：只讀後端的 item_cache，沒看過的品名標「待分析」
```

**屬性快取歸後端（10/16 補上，見 13.3）：** `item_cache` 是後端資料庫裡的資料表，刪帳號、刪月份時一起清理（5.11）。`describe_items` 最多只能在記憶體裡留一份快取，不能把真實品名寫到磁碟或 git；會進 git 的屬性結果只有假用戶的假品名（design D10，`datasets/synthetic/`）。

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

**Docker（10/15 補上）：** 根目錄的 `Dockerfile` 和 `docker-compose.yml` 用無 GPU 模式包起整個服務。執行 `docker compose up` 後：第一次啟動會從 Hugging Face 下載固定版本的分類模型；`DEMO_MODE=1` 而且資料庫是空的時，會自動匯入假用戶。資料庫和模型放在 volume 裡，重建容器也不會不見。容器裡不跑 Qwen；有設定 `LLAMA_SERVER_URL` 時，就連到主機上的 llama-server。組員開發時仍以虛擬環境為主，Docker 是給面試官和乾淨環境驗證用的。（10/16 補上）埠只開在主機的 `127.0.0.1`（`DEMO_MODE=1` 時任何連得到伺服器的人都能用假用戶登入）；`JWT_SECRET` 沒設時，用資料 volume 裡的 `/data/jwt-secret`，第一次啟動時產生；映像檔只 COPY `configs/` 和 `src/`，不含 `data/`、`rawdata/`、CSV 和 `.env`。下載分類模型只發生在 `CATEGORY_MODEL=bert`、模型資料夾沒有 `config.json`，而且設了 `CATEGORY_MODEL_REPO` 和 `CATEGORY_MODEL_REVISION` 的時候。

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
- `DEMO_MODE=1` 時，任何連得到伺服器的人都能用 demo 用戶登入，所以只在自己電腦或 demo 現場開。關掉之後，demo 用戶的 token 立刻失效，真實帳號不受影響。也因為這樣，demo 用戶查配對時只會看到假用戶，看不到任何真實使用者（見 5.7）（10/16 補上）
- 前端用 `GET /api/health` 的 `demo_mode` 決定要不要顯示快速切換，不要靠 404 的內容判斷
- 錯誤：404（`DEMO_MODE` 沒開，或沒有這個人）、403 `not_demo_user`

### 5.4 上傳與進度

**`POST /api/invoices`**：multipart，欄位名 `file`，一次一個財政部電子發票 CSV（一份一個月），上限 2 MB
- 伺服器先**當場**用 `invoices.build_month(..., for_upload=True)` 的規則解析，格式有錯直接回 400，既有資料不變；解析成功才建立背景任務
- 整個請求超過 2 MB 加 64 KB 時，伺服器在讀取內容之前（甚至在檢查登入之前）就回 413；沒有 `Content-Length` 的請求（分段傳送）回 411 `length_required`。瀏覽器用 `fetch` 加 `FormData` 一定會帶 `Content-Length`，前端不必處理 411（10/15 補上）
- 一個月最多 2000 筆留下來的明細，超過回 400 `invalid_csv`（真實的月份大約 50 筆；這樣一次上傳的背景任務不會跑超過大約一小時）（10/15 補上）
- 同一個人重新上傳同一個月份，會取代那個月的舊資料：舊的品項和已經結束的任務刪掉；還在排隊或執行中的舊任務照樣跑完
- demo 用戶不能上傳，回 403 `demo_user_read_only`（和 5.11 同一個代碼）：demo 帳號是大家共用的，上傳會把真實消費掛到公開的假用戶上（第 2 週實作）
- 「作廢」開頭的發票狀態（例如「作廢已確認」）直接跳過，不算消費；只有「開立已確認」會被計入，其他狀態回 400
- **金額低於 10 元（含 0 元和負數的折扣）或金額有小數的明細直接略過**，不算消費、不分析。月報總金額因此是折扣前的金額
- 數量有小數的明細（加油的公升數、秤重商品）保留，**數量當 1**。不然加油次數會消失，30 公升也會被「數量 ≥ 3」誤判成囤貨
- 這些規則只在 `for_upload=True` 時套用，v1 報表的建置照舊（原本遇到作廢或小數會直接報錯）。3–8 月真實發票共 336 列：作廢 2 列、金額規則略過 56 列，留下 278 列（10/14 的 273 是決定保留小數數量之前算的，差的 5 列就是小數數量）
- 回傳 202：`{"job_id": 12, "month": "2026-05", "rows": 35}`
- 錯誤：400 `invalid_csv`（`message` 寫原因，例如一份 CSV 有兩個月份；某一列的數字、日期或發票狀態不對時寫第幾行、哪一欄，例如 `Line 3: 消費明細_金額 is not a number`，不重複儲存格的內容，因為欄位錯位時那一格可能是品名的一部分（10/15 補上））、401、403 `demo_user_read_only`、411 `length_required`、413 `file_too_large`

**`GET /api/jobs/{job_id}`**
- 回傳：`{"job_id": 12, "month": "2026-05", "status": "running", "done": 10, "total": 25, "message": "判斷品項屬性"}`
- `status`：queued / running / done / failed
- `total` 是這份 CSV 不重複的品名數，`done` 是已經分類並判斷完屬性的品名數。無 GPU 模式下，快取裡沒有的品名直接標「待分析」，也算進 `done`。全部品名判斷完之後 `done` 就等於 `total`，但任務還要重算品味向量（步驟 3），要等 `status` 是 `done` 才算做完（10/15 補上）
- `message`：目前步驟的中文說明；failed 時寫失敗原因：「分類模型無法使用，請稍後重新上傳」「處理失敗，請重新上傳」「服務重新啟動，請重新上傳」
- 伺服器一次只跑一個任務（只有一個 llama-server，SQLite 也只有一個寫入者）：所有任務交給同一條背景執行緒，依上傳順序（先進先出）一個一個跑，不佔用回應請求的執行緒，所以排隊的任務再多，其他 API 照常回應。別人的任務在跑時，新任務的 `status` 停在 `queued`，前端照常每 2 秒問一次就好。停止伺服器時不會等任務跑完，還沒跑完的任務在下次啟動時標成 failed（10/15 補上）
- `job_id` 不會重複使用，任務刪掉之後也不會（10/15 補上）
- 錯誤：404 `not_found`（任務不存在，或不是你的任務，兩種回應完全一樣）、422（`job_id` 不是 1 到 2^63−1 的整數）

**背景任務的步驟：**
1. 列出不重複品名，呼叫 `classify()`。最高機率低於 `CATEGORY_MIN_PROB`（預設 0.5）的品名存成 10 待確認，不算進品味向量
2. 後端先查 `item_cache`，沒有的品名才呼叫 `describe_items()` 問 Qwen，答案由後端存進 `item_cache`。無 GPU 模式下沒有快取的回 `None`，算進 `pending_attributes`
3. 用這個人所有月份的資料重算 18 格，存進 `profiles`（`message` 是「重算品味向量」）。屬性只讀 `item_cache`（目前的屬性模型），不問模型，沒有的品名當成待分析，見 5.6。重算出錯時任務變成 failed（「處理失敗，請重新上傳」），舊的 profile 不變（10/15 補上）
4. `status` 改成 done，這是任務的最後一次寫入：看到 done 時 profile 已經更新。GPU 恢復之後，重新上傳同一個月份就能補算待分析的品名

任務 failed 時，那個月的品項不會刪掉：可能還是類別 10（待確認），或只做了一部分（例如已經分類、屬性還沒判斷完），一直留到重新上傳同一個月份把它們取代為止（10/16 補上）。

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
- 屬性先查後端的 `item_cache`，沒有才問 `describe_items(..., ask_model=False)`。GPU 模式下（假模型也算），pending 的品名在回應送出之後排進背景分析，結果寫進 `item_cache`，下次查詢就是 `ready`；前端每 2 秒再問一次，最多 5 次。同一個品名還在分析時再問，不會再排一次（10/15 補上）。無 GPU 模式下不排程，pending 不會自己變成 ready，顯示「待分析」就好（10/15 實作）
- 現在用的假屬性模型一次就答完每個品名，所以分類框從來不會是 `pending`；`ATTRIBUTES_MODEL=qwen` 要等角色 3 的模型接上（任務 2.15）才能用，在那之前看不到 pending 變成 ready（10/16 補上）
- 錯誤：401、422、503 `model_unavailable`（分類模型沒有載入，見 5.9）

### 5.6 我的品味向量與月報

**`GET /api/me/profile`**
- 回傳：
  ```json
  {"user_id": 301, "display_name": "Amy", "is_demo": false,
   "ready": true, "recomputing": false, "item_count": 57, "min_items": 20, "pending_attributes": 3,
   "areas": ["臺北市大安區", "新北市板橋區"],
   "traits": [
     {"id": "spend", "name": "省錢 ↔ 享受", "kind": "two_sided", "ends": ["省錢", "享受"], "value": 0.42},
     {"id": "sport", "name": "…", "kind": "level", "habit": "運動", "value": null}],
   "categories": [{"name": "正餐", "color": "#df646b"}],
   "months": {"2026-05": {"year": 2026, "monthNumber": 5, "rows": ["…現有格式"]}}}
  ```
- `traits` 一定有 18 筆。`ready` 為 false 時 18 格的 `value` 全是 `null`；`ready` 為 true 時，某一格資料不夠（沒到 `configs/traits.json` 為那一格設的最低需求，或那一格的訊號都量不到）還是 `null`，其他格有數值
- `ready`：只有存起來的品味向量存在時才是 true。有效品項（已略過的明細和類別 10 待確認的品項都不算）少於 `min_items`、還沒上傳過、第一個上傳的任務還沒做完，都是 false
- `recomputing`（10/16 補上）：這個人的 profile 有一次重算還在背景執行緒排隊或正在跑時是 true（刪了一個月之後，或服務剛啟動時），這時 `ready`、`item_count`、`areas`、`traits` 可能還是重算之前的；變回 false 之後就是重算好的結果。上傳的任務不算在內，上傳的進度照 5.4 問 `/api/jobs/{job_id}`
- `item_count`：有效品項數，判斷 `ready` 用的就是它。有效品項是金額大於 0、類別不是 10 的品項，而且同一張發票上同一個品名只算一次，所以不能拿 `months` 的列數自己數（10/16 補上）
- `pending_attributes`（10/15 補上）：這個人所有品項裡，`item_cache` 沒有（以目前的屬性模型）的不重複品名數；每次查詢當場數，不問模型，也不會寫入。品名一進快取就不再算（例如 GPU 恢復後重新上傳同一個月份補算，或即時分類框在背景分析了這個品名），但 profile 要等下一次重算（上傳的任務、刪月份，或伺服器重新啟動）才會用到新的答案（10/16 補上）。用假模型時，任務判斷完每個品名都有答案（全是 `null`），所以任務結束後是 0；換上真的 Qwen 之後，沒有 GPU 時新品名都算
- `areas`：生活圈，最多 2 個行政區（`places.areas_of`），可能是空陣列
- `categories`：11 類的名稱和顏色（`configs/report.json`），給現有月報畫面用
- `months`：由存起來的品項當場整理，格式同月報（10/15 補上：類別 10 待確認的品項也在裡面，`provisional` 一律是 `false`）。上傳一被接受就有了，所以 `months` 不是空的不代表 profile 做好了；`ready`、`item_count`、`areas`、`traits` 是最後一次重算存起來的 profile，只在上傳的任務結束、刪月份的重算跑完，或伺服器重新啟動時的重算跑完才變，剛上傳時要先照 5.4 問任務到 `done`（10/16 補上）
- profile 在每次上傳的任務最後重算一次（用這個人所有月份），這個端點只讀存好的結果，從不重算。另外服務每次啟動時，都把每個真實使用者（有 profile 的）的 profile 排進背景執行緒重算一次，只讀存著的品項和屬性快取，不問模型；假用戶不算，因為他們不能刪月份。這是因為刪月份之後排隊的重算只在記憶體裡，服務在它跑之前重新啟動就不見了（10/16 補上）
- 存起來的品味向量是 `configs/traits.json` 的每個 trait 一個值。新增或刪掉 trait 之後，每個人的 profile 都要重算（重新上傳），否則存著舊長度的 profile 查詢時會回 500（10/16 補上）。真實使用者在伺服器重新啟動時會自動重算；假用戶要重跑 seed（10/16 補上）
- 啟動時的重算只讀資料庫裡的品項和屬性快取，所以重新啟動之後，有兩種情況會讓 profile 和重啟之前不同：上傳失敗的月份（品項在上傳被接受時就存了，任務失敗時 profile 沒有重算）會算進去；換了屬性模型（例如 `fake` 換成 `qwen`），profile 會改用目前模型的屬性答案。這是預期的行為，不是錯誤（10/16 補上）
- 還沒上傳過的人：`ready` 為 false，`item_count` 為 0，`months` 為 `{}`。假用戶的品項和 profile 要等 seed 擴充時才放入（任務 4.7），在那之前查假用戶一樣是 `ready` 為 false
- 休假日和連假看 `configs/calendar-2026.json`：它目前只列了 2026 年 3–4 月的補假（檔案的 `covers`）。其他月份（包括其他年份）只有週末算休假日，沒有國定假日、補班和連假：`days` 格只用週末算，整個期間沒有任何一段連續三天以上的休假日時，`holiday` 格是 `null`

### 5.7 配對

**`GET /api/matches?kind=similar&scope=all`**
- `kind`：similar（相近，`percent` ≥ +30）或 opposite（互補，`percent` ≤ −10），預設 similar。門檻來自 `configs/traits.json` 的 `match`；不是這兩個值（含大小寫不同）回 422（10/16 補上）
- `scope`：all / district / city / region，也就是不限、同區、同縣市、同地區，對應 `places.distance` ≤ 0、1、2。預設 all；不是這四個值（含大小寫不同）回 422（10/16 補上）
- 對象：自己以外、存起來的 profile 有品味向量的所有使用者（包含假用戶）；和我不可比較的人（共同的雙向格少於 5 格，見 `explain` 的 `too_few_shared`）不算進任何人數；假用戶不管 `DEMO_MODE` 有沒有開都算（`DEMO_MODE` 只管 demo 名單和快速切換，見 5.10）；但查詢的人如果是 demo 用戶（用快速切換登入，不用密碼），清單只有假用戶，真實使用者一個都不會出現，`eligible` 和 `within` 也只算假用戶（10/16 補上）
- 門檻：看整數百分比，和 v1 的 `match-filter.js` 一樣：相近是 `percent` ≥ `similarity.percent(min_score)`（+30），互補是 `percent` ≤ `similarity.percent(−opposite_score)`（−10）。所以 0.295 是 +30%、列入，−0.095 是 −9%（四捨五入往上）、不列入；分數剛好 0 兩邊都不列（10/16 補上）
- 排序：similar 分數由高到低，opposite 由低到高；同分時依 `display_name` 的字碼順序，再依 `user_id`；取前 5 名
- 回傳：
  ```json
  {"kind": "similar", "scope": "all", "ready": true, "my_areas": ["臺北市大安區"],
   "eligible": 12, "within": 12,
   "people": [{"user_id": 7, "display_name": "咖啡上班族 C", "score": 0.6234, "percent": 62,
               "area": "臺北市中山區", "distance": 1}]}
  ```
- `eligible`：過門檻的人數，不看距離；`within`：過門檻又在範圍內的人數。前端用這兩個數字照 v1 的方式寫狀態文字
- `area`：對方離我最近的生活圈（`places.closest_area`）；我看不出生活圈時是對方的第一個。對方看不出生活圈時是 `null`（10/16 補上）
- `distance`：0 同區、1 同縣市、2 同地區、3 更遠；我或對方看不出生活圈時是 `null`（不知道），這樣的人只會出現在 `scope=all`（10/16 補上）
- `my_areas`：我存起來的 profile 的生活圈，同 `/api/me/profile` 的 `areas`，資料不夠時也照實給（10/16 補上）
- 我自己資料不夠時（沒有存起來的品味向量）：不管 `scope` 是什麼，`ready` 為 false，`people` 為空陣列，`eligible` 和 `within` 都是 0，不回 `no_home_area`（10/16 補上）
- 錯誤：400 `no_home_area`（我的資料夠，但看不出我的生活圈，`scope` 卻不是 all）、422（`kind`、`scope` 不是列出的值）（10/16 補上）
- 分數每次查詢當場算，不存（design D3，`src/api/matching.py`）。任何一個人存著舊長度的向量（改了 `configs/traits.json` 的 trait 卻沒重算），配對清單回 500，不拿錯位的格子算分數；改 trait 之後要把每個人的 profile 重算（同 5.6）（10/16 補上）

**`GET /api/matches/{user_id}/explain`**：任何一個使用者都能看，不限前 5 名（demo 用戶查真實使用者除外，見最後一點）（10/16 補上）
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
- 分數和清單一致：`cells` 的 `mine`／`theirs` 是存起來的向量，`score`、`percent` 和配對清單上的完全一樣；`part` 依序加總剛好等於 `score`（10/16 補上）
- `comparable` 為 false 時，`reason` 是 `not_enough_items`（任一方沒有存起來的品味向量：有效品項不夠，或還沒上傳）或 `too_few_shared`（共同的雙向格少於 5 格），`dot` 以下的欄位全部是 `null`；每一格的 `product` 和 `part` 也是 `null`；`mine`、`theirs`、`weight`、`shared` 照實給，`shared_two_sided` 照實數（任一方沒有向量時是 0）（10/16 補上）
- 另外有一個 `network` 欄位，給連線圖用，格式和 v1 的 `traitNetworkData` 相同（`build.trait_network_data`），只是 `friends` 換成 `mine` 和 `theirs` 兩個人：
  ```json
  "network": {"model": {"…": "同 similarity_model"}, "traits": ["…"], "signals": ["…"], "readout": {"…": "…"},
              "mine":   {"vector": ["…18 格"], "pushes": ["…"], "signals": ["…46 個訊號"], "items": [[["鮮奶茶", 6], ["美式咖啡", 2]], null]},
              "theirs": {"vector": ["…"], "pushes": ["…"], "signals": ["…"], "items": ["…"]}}
  ```
  `src/web/trait-network.js`（複製到 `src/web_v2/` 之後）可以直接拿來畫。資料不夠的人，四個欄位都是 `null`；`vector` 和 `pushes`、`signals`、`items` 一樣是查詢時算出的，所以 push 加起來一定等於 `vector`；通常和 `cells` 的值一樣，只有上次重算之後品項或屬性答案變了的時候（例如刪了一個月、重算還在排隊）會暫時不同，重算跑完就一樣（10/16 補上）。四個欄位都是用那個人存著的品項和屬性快取當場算的，不問模型、不寫入。沒有存起來的向量，或品項現在已經算不出品味（例如剛刪掉一個月、重算還在排隊）時，那一邊四個欄位都是 `null`。上次重算之後才有答案的品名，`vector`、`pushes`、`signals` 會先反映，`cells` 和分數要等下一次重算（上傳或刪月份的任務）才跟上（10/16 補上）。連線圖和 v1 一樣會顯示對方兩個花費的彙總值（`meal_cost` 每餐花費的中位數、`tech_spend` 每月 3C 花費），每個特質的 pushes 加起來等於 vector，可以直接用 `trait-network.js` 的檢查（10/16 補上）
- `items` 是每個訊號買最多次的 3 個品名和出現的發票張數，品名一律經過 5.8 的處理
- 錯誤：404 `not_found`（沒有這個人，或我是假用戶而對方不是）、400 `self`（查自己）、422（`user_id` 不是 1 到 2^63−1 的整數）。我是假用戶而對方不是時，當作沒有這個人，回應內容和真的沒有這個人完全一樣，和配對清單同一條規則（10/16 補上）

### 5.8 品名隱私

API 回傳**別人**的品名時（目前只有 `explain` 的 `network.theirs.items`），一律經過 `items.label`，`mine.items` 也照同樣規則處理：

- 去掉地名：所有縣市（含「臺中」這種不帶縣市的簡稱）、縣轄市、這個人買過東西的每個行政區（含「大安」這種簡稱）、`configs/attributes.json` 的 `place_words`（例如「淡水」）。台、臺視為同一個字
- 住宿一律顯示「旅館住宿」；長途交通只顯示票種，不顯示站名
- 跟地點有關的 4 個訊號（`list_items` 為 false）不列品名
- 每個訊號最多 3 個品名，最長 20 字。去掉地名後只剩數字或符號的，改顯示類別名稱
- 不回店家名稱、發票號碼、日期
- 不回任何一筆消費或一張發票的金額。連線圖的兩個花費彙總值（每餐花費中位數、每月 3C 花費）會顯示，它們本來就算在 18 格裡。已知風險：某段期間只有一筆 3C 消費時，每月 3C 花費乘以月數就是那一筆的價格（要不要再收緊，由組長決定）（10/16 補上）
- 漏網的地名（商圈、地標、分店名）加進 `place_words`，不要在 API 裡另寫一套規則

2026-10-14 用 3–8 月真實發票檢查（只看數量）：245 種商品中，2 種改顯示通用名稱、1 種去掉了地名。處理後還有 2 種含「店」字，都是 0 元明細，照 5.4 的金額規則會被略過，不會顯示

### 5.9 健康檢查

**`GET /api/health`**
- 回傳：`{"status": "ok", "gpu_mode": false, "demo_mode": true, "models": {"category": "fake", "attributes": "cache_only"}}`
- `gpu_mode`：連得到 `LLAMA_SERVER_URL` 的 llama-server 就是 true
- `models.category`：fake / tfidf / embedding / bert，設定的模型檔不存在或下載失敗時是 `unavailable`（10/15 補上，這時即時分類回 503 `model_unavailable`，上傳的背景任務變成 failed）；`CATEGORY_MODEL=bert` 而模型資料夾沒有 `config.json`，或 `src/ml/category.py` 還沒合併時，也是 `unavailable`（10/16 補上）；`models.attributes`：fake / qwen / cache_only（無 GPU 模式）

### 5.10 設定（`.env`，repo 只放 `.env.example`）

| 變數 | 預設 | 說明 |
|---|---|---|
| `JWT_SECRET` | 無，一定要設 | 簽 JWT 用的密鑰，至少 32 字元 |
| `JWT_EXPIRE_MINUTES` | 1440 | token 有效時間 |
| `DEMO_MODE` | 0 | 1 = 開放 `demo-users` 和 `demo-login` |
| `DATABASE_URL` | `sqlite:///data/app.db` | 放在 `/data/` 底下，不會進 git。相對路徑一律從 repo 根目錄算起，不管在哪個資料夾啟動。只接受 `sqlite:///…`（檔案）和 `sqlite://`（記憶體，測試用），錯誤訊息不會印出設定的值 |
| `LLAMA_SERVER_URL` | `http://127.0.0.1:8080` | Qwen 的 llama-server |
| `CATEGORY_MODEL` | fake | `fake` 和 `bert` 可以設；`bert` 在真模型接上（任務 2.15）之前一律是 `unavailable`（10/16 補上） |
| `ATTRIBUTES_MODEL` | fake | fake / qwen |
| `CATEGORY_MIN_PROB` | 0.5 | 低於這個機率的品名歸到 10 待確認 |
| `CATEGORY_MODEL_DIR` | `models/category` | `CATEGORY_MODEL=bert` 時讀模型的資料夾（`/models/` 不進 git）。10/15 補上。設了 `CATEGORY_MODEL_REPO` 就一定要設 `CATEGORY_MODEL_REVISION`（10/16 補上） |
| `CATEGORY_MODEL_REPO` | 空 | Hugging Face 上公開的分類模型庫；資料夾裡沒有模型時從這裡下載。10/15 補上。設了 `CATEGORY_MODEL_REPO` 就一定要設 `CATEGORY_MODEL_REVISION`，沒設的話伺服器啟動時停下來（10/16 補上） |
| `CATEGORY_MODEL_REVISION` | 空 | 要下載的固定版本（commit），和 `CATEGORY_MODEL_REPO` 一起設定。10/15 補上。設了 `CATEGORY_MODEL_REPO` 就一定要設 `CATEGORY_MODEL_REVISION`（10/16 補上） |

設定留空等於用預設值。密鑰短於 32 字元、數字寫錯或超出範圍、模型名稱不在清單裡時，伺服器啟動時停下來，用一行訊息指出是哪個變數。伺服器只能開**一個行程**：不要加 `--workers`，也不要兩個伺服器共用同一個資料庫，因為啟動時會把還沒做完的任務標成 failed，「一次只跑一個任務」的背景執行緒也只管得到同一個行程裡的任務。`src/ml/` 有真的模型之前，`CATEGORY_MODEL` 和 `ATTRIBUTES_MODEL` 只有 `fake` 能用，設成別的值同樣會停下來；唯一的例外是 `CATEGORY_MODEL=bert`，它能啟動，但模型一律是 `unavailable`（10/16 補上）。

### 5.11 帳號管理（2026-10-15 補上）

格式和錯誤規則同 5.1。假用戶（`is_demo`）不能改名、改密碼、刪帳號或刪月份，一律回 403 `demo_user_read_only`（上傳發票也一樣，見 5.4）；登出照常可以用。

**`GET /api/me`**
- 回傳：`{"user_id": 301, "username": "amy", "display_name": "Amy", "is_demo": false, "months": ["2026-07", "2026-08"]}`
- `months`：有品項或有上傳任務的月份，由舊到新（只有任務、沒有留下品項的月份也算）（10/16 補上）

**`PATCH /api/me`**：JSON `{"display_name": "愛喝咖啡的人"}`，1–20 字元
- 回傳：同 `GET /api/me`。`username` 不能改
- 規則和註冊一樣：去掉前後空白後 1–20 字元，不能有看不見的字元或換行，否則 422，名稱不變；`username` 帶了也不理（10/16 補上）

**`POST /api/me/password`**：JSON `{"current_password": "…", "new_password": "…"}`，新密碼 8–128 字元
- 回傳：同 login（一個新的 token）。改完之後，這個帳號的 `token_key` 換成新的，舊的 token 全部失效，回傳的新 token 帶著新的 key
- 錯誤：403 `wrong_password`
- 新密碼不合格回 422，不回傳送出的值（10/16 補上）

**`DELETE /api/me`**：JSON `{"password": "…"}`
- 回傳 204。依序刪掉這個人的 `items`、`jobs`、`profiles`、`users`，再刪掉 `item_cache` 裡這個人用過、而且已經沒有任何 `items` 用到的品名。品名的屬性結果只存在後端的 `item_cache`（`describe_items` 最多只在記憶體裡留快取，不寫到磁碟），所以清掉這裡就清乾淨了（10/16 補上，見 13.3）
- 品名的屬性快取只刪「這個人的品項用過、刪完後已經沒有任何品項用到」的品名（每個屬性模型的答案都刪）。只在即時分類框查過、從沒上傳過的品名沒有記錄是誰查的，不會被刪（10/16 補上）
- 錯誤：403 `wrong_password`、409 `job_in_progress`（還有 queued 或 running 的上傳任務，等它做完再刪；不然那個任務會在刪除之後又把品名寫進快取）（10/15 補上）

**`DELETE /api/me/months/{month}`**：`month` 是 `YYYY-MM`
- 回傳 204。刪掉那個月的 `items` 和 `jobs`，重算 18 格；`item_cache` 的清理方式同上
- 錯誤：404 `month_not_found`、409 `job_in_progress`（那個月還有 queued 或 running 的任務）
- `month` 不是 `YYYY-MM`（月份 01–12）回 422；那個月沒有品項也沒有任務回 404；只有那個月的任務才擋（409），別的月份的任務不擋。重算排進背景執行緒，排在已經排隊的上傳任務後面，不在請求裡算：重算跑完之前，`/api/me/profile` 的 `ready`、`item_count`、`areas`、`traits` 還是舊的（`months` 立刻是新的）。前面有上傳任務在排隊時，要等它們做完（10/16 補上）
- 重算跑完之前，`/api/me/profile` 的 `recomputing` 是 true，跑完變回 false。服務在重算跑之前重新啟動的話，啟動時會再排一次（見 5.6），`recomputing` 一樣會是 true 直到它跑完（10/16 補上）

**`POST /api/auth/logout`**
- 回傳 204。真實使用者登出時換掉這個人的 `token_key`，這個帳號在**所有裝置**上的 token 都會失效
- `users.token_key` 第 1 週就有了，不必再加欄位。登出後馬上重新登入，新拿到的 token 可以用
- 假用戶是共用的：用假用戶登出不換掉共用的 `token_key`，只結束這個瀏覽器的登入（前端丟掉自己的 token），切換成同一個假用戶的其他人照常登入著（10/16 補上）

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

- **負責：** 在 4060 上重新選型、Qwen 介接、100 筆人工複核、300 個假用戶。屬性結果的快取 `item_cache` 歸後端（資料庫，刪帳號時清理）；`describe_items` 最多只在記憶體裡留快取，不能把真實品名寫到磁碟或 git（10/16 補上，見 13.3）
- **交出：** `src/ml/attributes.py` 的 `describe_items()`；假用戶資料；複核結果和 F1；配對驗證（同類型的人有沒有互相出現在相近前 5 名）
- **先讀：** `experiments/receipt-attributes/CLAUDE.md`、`README.md`、`RESULTS.md`、`INTEGRATION.md`（**接入契約，必讀**）、`SELECTED_MODEL.json`；`src/receipt/attributes.py`、`personas.py`
- **每週：**
  1. 4060 環境；用實驗資料夾的同一套評估，比較 Qwen3-4B 和約 5 GB 的候選模型（例如 Qwen3-8B Q4_K_M）；先用 0.5B 模型在 CPU 上把流程接通
  2. 屬性介接：交出 `describe_items()`（接進品味計算的是後端的 `attributes.from_model`，見 13.5；`channel_of` 保留）；`personas.py` 擴充到約 300 人
  3. 4 人分著做 100 筆人工複核並算 F1；配對驗證；跑完假用戶品名的 Qwen 結果，存成 `datasets/synthetic/attribute-cache.jsonl` 放進 git（任務 4.7；只有假品名，design D10）
  4. 修錯；講稿素材
- **注意：** `INTEGRATION.md` 列了幾個要明確決定的地方：甜度沒寫時回 `null`、fun 的英文值要對應成中文、`null` 不等於 `false`（10/15 決定：`describe_items` 照任務 4.3 把 fun 對應成中文值交出；後端的 `attributes.from_model` 也接受實驗的英文值，兩種以外的 fun 一律當成沒給。甜度預設由後端補，見 13.4）。`experiments/receipt-attributes/CLAUDE.md` 的限制只適用於那個實驗資料夾，正式介接寫在 `src/ml/`

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
- 配對時，對方會看到你每個訊號買最多次的品名（去掉地名後，見 5.8），但看不到店家、日期和每一筆的金額（連線圖的花費彙總值除外，見 5.8）
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
   預期結果：Python 295 個、JS 82 個全部通過
3. 後端（角色 1 的第一週成果）：
   - 複製 `.env.example` 成 `.env`，`JWT_SECRET` 填一串至少 32 字元的亂碼：`.venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(32))"`
   - 放入 demo 用戶：`.venv/Scripts/python.exe -m src.api.seed`（跑幾次都可以，只會補上還沒有的人；名單只能往後加，資料庫裡的帳號和名單對不上時會停下來並說明，這時刪掉 `data/app.db*` 再重來）
   - 啟動：`.venv/Scripts/python.exe -m uvicorn src.api.main:app --reload`，打開 `http://127.0.0.1:8000/docs`。v2 網頁在 `http://127.0.0.1:8000/web/`，角色 4 做好之前只有一個預留頁
   - 或者直接雙擊 `start.bat`（沒有 `.env` 會自動建立）：它一次做完上面三項，建立 `.env`（含新的 `JWT_SECRET`）、放入 demo 用戶、啟動在 `http://127.0.0.1:8000` 並打開 `/web/`；已經有 `.env` 的人不受影響（10/16 補上）
   - 改了 `.env` 要手動重啟伺服器（`--reload` 只看 `.py` 檔）
   - `src/api/tables.py` 多了新的資料表時不用動，伺服器或 seed 啟動時會自動建立；已經存在的資料表改了欄位或索引時，才要刪掉 `data/app.db*`（資料庫和它的 `-wal`、`-shm` 檔）再重新放入 demo 用戶
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

### 13.9 角色 1 轉告（2026-10-16，第 3 週第六批，分支 `role-1/deploy`）

`start.bat`、GitHub Actions、`Dockerfile`／`docker-compose.yml` 都有了。這台電腦沒有 Docker，映像檔要等 push 之後在 CI 上建置才算驗證過。

**給所有人**
- 雙擊 `start.bat` 就能啟動：沒有 `.env` 會自動建立（含新的 `JWT_SECRET`），會放入假用戶並打開 `http://127.0.0.1:8000/web/`。已經有 `.env` 的人不受影響
- CI 在每次 push 和 PR 跑兩套測試（模型一律 fake），再建一次映像檔、檢查裡面沒有私人檔案、啟動一次確認健康檢查。測試不要依賴 Windows 才有的行為

**給角色 2**
- 交出 BERT（任務 3.6）時：把 CPU 版的 `torch`、`transformers` 加進 `requirements-docker.txt`（用 PyTorch 的 CPU index），模型存成 `save_pretrained` 的格式（資料夾裡要有 `config.json`）。`CATEGORY_MODEL=bert` 在接上之前一律回報 `unavailable`
- 公開模型（任務 3.9）後，把 repo 和 revision 給角色 1，填進 `.env.example` 和 `docker-compose.yml` 的預設值

**給角色 3**
- 容器啟動時，資料庫是空的而且 `DEMO_MODE=1` 才匯入假用戶（`container.seed_if_empty`，用的是 `seed.seed_demo_users`）。任務 4.7 擴充 seed 之後，請讓容器也走同一個函式，品項和 profile 才會一起進去

### 13.8 角色 1 轉告（2026-10-16，第 3 週第五批，分支 `role-1/account`）

帳號管理（5.11）都可以用了：`GET`／`PATCH /api/me`、`POST /api/me/password`、`DELETE /api/me`、`DELETE /api/me/months/{month}`、`POST /api/auth/logout`。

**給角色 4**（任務 5.10 帳號設定頁）
- 改密碼成功會回一個新的 token（和登入一樣的格式），請換成它；舊的 token（包括其他裝置的）都失效了
- 登出回 204。真實使用者登出後，所有裝置的 token 都是 401。用假用戶登出只結束這個瀏覽器的登入：前端自己丟掉 token，同一個假用戶的其他人不會被登出（10/16 補上）
- `DELETE /api/me` 和改密碼要使用者再輸入密碼，密碼錯是 403 `wrong_password`。還有上傳在處理時，刪帳號回 409 `job_in_progress`（請使用者等上傳做完）；改密碼沒有這個限制（10/16 補上）
- 刪月份回 204 之後，品味向量在背景重算：`months` 立刻少了那個月，`ready`、`item_count`、`areas`、`traits` 這四個要等重算跑完才變（前面有上傳在排隊時要等更久）。畫面先顯示「重新計算中」，每 2 秒查一次 `/api/me/profile`，直到 `recomputing` 變回 false，再用那次的回應更新畫面（10/16 補上）
- 設定頁的月份清單（要刪哪個月）用 `GET /api/me` 的 `months`（有品項或有上傳任務的月份），不要用 `/api/me/profile` 的 `months`（只有留下品項的月份）：整個月的明細都被略過的月份只在前者，也要能刪（10/16 補上）
- 假用戶改名、改密碼、刪帳號、刪月份都是 403 `demo_user_read_only`，設定頁對假用戶唯讀
- 計算過程（13.7 補充）：關係圖用 `network`，逐格的面板用 `cells`。`network` 的向量現在是查詢時算的，push 加起來一定等於它；刪了一個月、重算還沒跑完時，圖上的點可能和 `cells` 的值暫時不同，重算跑完就一樣。上次重算之後才有屬性答案的品名也會讓兩者暫時不同（見 5.7），要等下一次重算才一樣（10/16 補上）

**給角色 3**
- seed 寫入的假用戶不能被這些端點修改或刪除（403），重建假用戶請照舊刪掉資料庫重跑 seed

### 13.7 角色 1 轉告（2026-10-16，第 3 週第四批，分支 `role-1/matches`）

計算過程 `GET /api/matches/{user_id}/explain`（5.7）可以用了。

**給角色 4**
- 計算過程面板（任務 5.7）：`cells` 一定 18 筆，順序同 `configs/traits.json`；`part` 加起來就是 `score`，`percent` 和配對清單卡片上的一樣，面板直接顯示 API 的數字，不要自己算
- `comparable` 為 false 時看 `reason`：`not_enough_items`（任一方沒有存起來的品味向量）或 `too_few_shared`（共同的雙向格不到 `min_shared_two_sided`，`shared_two_sided` 是實際格數）；這時總數和每格的 `product`、`part` 都是 `null`
- 關係圖：`network` 的格式同 v1 的 `traitNetworkData`，只是 `friends` 換成 `mine` 和 `theirs` 兩個人，`src/web/trait-network.js` 複製到 `src/web_v2/` 後可以直接畫。沒有存起來的向量時（那一邊的 `cells` 也是 `null`），那一邊的 `vector`、`pushes`、`signals`、`items` 都是 `null`，要畫成「資料不夠」
- 任何人都能查，不限清單前 5 名；查自己是 400 `self`，沒有這個人是 404 `not_found`。用假用戶登入時查真實使用者也是 404
- 品名已經去掉地名（5.8），回應裡沒有店家、發票號碼、日期，也沒有任何一筆消費的金額，前端不用再處理
- 對方的兩個花費彙總值（`meal_cost` 每餐花費、`tech_spend` 每月 3C 花費）和 v1 一樣照常顯示；每個特質的 `pushes` 加起來等於 `vector`，所以 `trait-network.js` 的 `validate` 兩邊都會通過
- 只要某一邊的 `cells` 有值、圖的四個欄位卻全部是 `null`（不管 `comparable` 是不是 true），就是存起來的向量還在，可是現在的品項已經算不出品味（例如剛刪掉一個月、重算還沒跑完）。`cells` 和分數照常顯示，那一邊的圖畫成「重新計算中」，不要畫成「資料不夠」；那一邊的 `cells` 也是 `null`（沒有向量）才畫成「資料不夠」。自己這一邊的重算什麼時候跑完，看 `/api/me/profile` 的 `recomputing` 變回 false（13.8，10/16 補上）
- `not_enough_items` 時，沒有向量的那一邊，每一格的 `mine` 或 `theirs` 都是 `null`
- 使用者打開某個人的面板時才呼叫 `explain`，不要為清單上的 5 張卡片事先全部呼叫：每次呼叫都要從品項當場算兩個人的品味，一般的人大約 0.3–0.6 秒

### 13.6 角色 1 轉告（2026-10-16，第 2–3 週第三批，分支 `role-1/matches`）

`GET /api/matches`（5.7）可以用了；計算過程 `GET /api/matches/{user_id}/explain` 還沒做（任務 2.7）。分數由後端當場算，前端不再自己算（design D3）。

**給角色 4**
- 參數：`kind` 是 `similar`／`opposite`，`scope` 是 `all`／`district`／`city`／`region`（不限、同一區、同縣市、同地區），都要小寫；其他值回 422
- 先看 `ready`：false 時不管選哪個範圍都是 200、清單空的，畫面照 v1 顯示「資料還不夠」（還差幾個品項用 `/api/me/profile` 的 `item_count` 和 `min_items`）
- `ready` 為 true 而且 `my_areas` 是空陣列時，只能選「不限」：其他範圍請在畫面上停用，選了會回 400 `no_home_area`
- 狀態文字照 v1 `match-filter.js` 的 `status`：`eligible` 是 0 →「目前沒有品味夠相似的人」（互補是「目前沒有和你明顯相反的人」）；`eligible` 大於 0、`within` 是 0 →「這個距離內沒有…，試試放寬距離」；`within` 大於 5 → 加「顯示前 5 位」
- 門檻（+30%、−10%）和前 5 名的 5，來自 `configs/traits.json` 的 `match`（`min_score`、`opposite_score`、`top`），回應裡沒有這幾個數字，所以畫面要把它們寫成固定的數字，改了那個檔就要一起改畫面
- 用假用戶快速切換登入時，配對清單只有假用戶，真實使用者不會出現，`eligible` 和 `within` 也只算假用戶；真實帳號則看得到假用戶
- `people` 已經排好序、最多 5 人，不要再排。`score` 沒有四捨五入，卡片上的數字用 `percent`
- `area` 可能是 `null`（對方看不出生活圈）；`distance` 是 0–3，我或對方看不出生活圈時是 `null`，這時不要顯示距離
- 不要在畫面上自己依距離篩選或重新排序：`people`、`eligible`、`within` 已經照選的 `scope` 算好。v1 的 `src/web/match-filter.js` 用 `distance <= range` 篩選，JavaScript 裡 `null <= 0` 是 true，照搬到 API 資料上，看不出生活圈（`distance` 是 `null`）的人會跑進每一種範圍
- 清單只有對方的編號、顯示名稱、生活圈、距離和分數；畫連線圖的資料要等 `explain`

**給角色 3**
- 假用戶要等 seed 擴充（任務 4.7）讓他們在 `profiles` 有向量之後，才會出現在別人的配對清單裡
- 配對驗證（任務 4.9）請用 `src/api/matching.py` 的 `entries` 和 `pick`，門檻、排序和同分規則才會和 API 一樣

### 13.5 屬性接入以 `from_model` 為準（2026-10-16，使用者決定，角色 1 轉告，分支 `role-1/profiles`）

- 「讓品味計算讀取模型屬性」以角色 1 的 `src/receipt/attributes.from_model` 為準；角色 3 分支上的 `attributes.describe(..., external=...)` 會移除，之後不要再接它
- 介面：`signals.measure(rows, period, context, attributes)`、`traits.explain(rows, period, context, attributes)`、`traits.build_vector(rows, period, context, attributes)`，`attributes` 是 `{品名: 23 個欄位的 dict，或 None（待分析）}`；字典裡沒有的品名也當成待分析。不給 `attributes` 就照舊用 v1 的關鍵字規則，結果完全不變
- 從角色 3 的版本搬過來兩條規則（design D6、taste-profile 規格「沒有已知答案的次數不是 0」，測試在 `tests/test_model_attributes.py`）：
  1. 計次的訊號（`kitchen_per_month`、`sport_supplies`、`sport_gear`、`car_care`、`home_items`、`stationery_items`、`alcohol_items`、`pet_food_*`、`pet_supply_*`）在問題適用的品項裡沒有任何已知答案時是 `null`，不是 0；完全沒有適用的品項時是 0。娛樂（`fun_visits`、`fun_kinds`）只有在全部品項都待分析、而且店家名稱也沒有娛樂字時才是 `null`，判斷過的品名沒有娛樂種類就是「不是娛樂」
  2. 寵物店發票上沒有已知物種、又有待分析的品項時，這次造訪不算給貓也不算給狗；這個人的寵物店發票全部如此時，`pet_visits_cat`、`pet_visits_dog` 是 `null`（角色 3 的版本這時是 0）。有已知物種時照已知物種算，判斷過但沒寫物種的照舊各算一半
- 待分析的飲品照樣套用甜度預設規則（taste-profile 規格「飲品甜度的預設值」）
- `fresh_share`、`bulk_share` 拆成規則的部分和模型回答的部分（10/16 補上，使用者決定；design D6、taste-profile 規格「規則決定的部分不拿來代表模型的答案」）：`fresh_share` = 生鮮占食物的比例 × 已知的生鮮裡下廚的比例；`bulk_share` = 一次買 3 個以上的占比，加上其餘日用品裡由已知答案估出的囤貨比例。`MIN_KNOWN`（5 個）只看模型回答的部分。原本規則決定的「沒有」（不是生鮮的食物）和「是」（數量 ≥ 3）也被當成已知答案，全部待分析時 `fresh_share` 會是 0、`bulk_share` 會是 1；現在兩個都是 `null`。每個答案都已知時和 v1 一樣
- 給角色 3（10/16 補上）：屬性結果的快取 `item_cache` 歸後端（資料庫，刪帳號、刪月份時清理，見 13.3、5.11）。`describe_items` 最多只在記憶體裡留快取，不能把真實品名寫到磁碟或 git；進 git 的只有假用戶假品名的結果（design D10）。你現在的 `src/ml/attributes.py` 只用記憶體裡的 dict，已經符合
- 用 40 個 v1 假用戶、全部品項待分析實測：不需要屬性的 25 個訊號和 v1 完全一樣；sweet、routine、travel、stock、tech、days、holiday 七格不變，其他格子只因為依賴屬性的訊號量不到而改變（例如 alcohol 格只剩 `bar_visits`，pets 格是 `null`）。給角色 4：沒有 GPU、很多品名待分析時，這些格子可能是 `null`，畫面照「沒有資料」顯示

### 13.4 角色 1 轉告（2026-10-15，第 2 週第二批，分支 `role-1/profiles`）

品味向量接好了：每次上傳的任務最後用這個人所有月份的品項重算 18 格，存進 `profiles`（5.4 第 3 步，`message` 是「重算品味向量」），`GET /api/me/profile`（5.6）可以用了。配對和計算過程的 API（5.7）還沒做。

**給角色 4**
- 5.6 可以用了。上傳照 13.3：拿到 `job_id` 之後每 2 秒問 `GET /api/jobs/{job_id}`，直到 `done` 或 `failed`，再查 `GET /api/me/profile`。進度條到 100%（`done` 等於 `total`）之後還有一小段 `message` 是「重算品味向量」，`status` 還是 `running`，要等 `done`，這時 profile 才更新
- `months` 由存起來的品項當場整理，上傳一被接受就有了；`ready`、`item_count`、`areas`、`traits` 是任務最後存起來的 profile，任務結束才變。`months` 不是空的不代表 profile 做好了，要先問任務到 `done`。任務 `failed` 時，`months` 已經是新上傳的月份，profile 還是上一次成功的結果，請使用者重新上傳
- `ready` 為 true 才有品味向量（有效品項至少 `min_items` 個）。false 時 18 筆 `traits` 的 `value` 全是 `null`，畫面可以用 `item_count` 和 `min_items` 顯示「還差幾個品項」。`ready` 為 true 時，個別格子還是可能是 `null`（那一格資料不夠），畫面要畫得出「沒有資料」
- `item_count` 是有效品項數（略過的明細和類別 10 待確認的品項不算）：金額大於 0、類別不是 10，同一張發票上同一個品名只算一次，所以不能拿 `months` 的列數自己數（10/16 補上）。`months` 裡的品項照樣包含類別 10，`provisional` 一律是 `false`，畫面用 `category` 是不是 10 顯示「待確認」
- `pending_attributes` 是屬性模型還沒判斷過的不重複品名數，大於 0 時可以提示「有 N 個品名還在分析」。現在用假模型，任務結束後是 0，換上真的 Qwen、沒有 GPU 時新品名才會算進去
- 還沒上傳過的人和假用戶（`is_demo`，假用戶的資料要等 seed 擴充，任務 4.7）：`ready` 為 false、`item_count` 為 0、`months` 為 `{}`，不是錯誤
- `configs/calendar-2026.json` 只列了 2026 年 3–4 月的補假，其他月份只算週末，所以沒有連假的期間 `holiday` 格是 `null`（見 5.6 最後一點）

**給角色 3**
- 品味計算現在讀你的 `describe_items` 結果：上傳任務把它存進 `item_cache`，重算 profile 時只讀快取，不問模型。換成訊號用的答案時（`src/receipt/attributes.from_model`），`null` 是「不知道」，比例的分母只算已知的答案（`fresh_share`、`bulk_share` 只用已知答案估規則決定不了的部分，見 13.5），所以不確定就給 `null`，不要猜 `false`（design D6）
- `fun`：`describe_items` 照任務 4.3 把它對應成中文值交出（電影、唱歌、展演、遊樂），後端照單全收；實驗的英文值 `movie`、`singing`、`show`、`game` 後端也接受，換成同一組中文。兩種以外的值會被當成沒給，改看店家名稱有沒有娛樂的字
- `species` 只認 `cat`、`dog`，其他是 `null`（不知道）
- `sugar` 是 0 到 1 的數字，不知道給 `null`：後端會套現有的甜度預設規則（奶茶、手搖店的飲品全糖，美式無糖……）。後端不檢查範圍，給了就直接拿去算，請自己保證在 0–1
- 類別決定問題適不適用：`clearance` 只看食物、`quick` 只看正餐、`cooking` 只看生鮮、`kitchen` 只看生鮮和日用品、`sport_gear`／`car_care`／`home`／`stationery` 只看非食物，不適用的類別不管模型怎麼答，都當成已知的「沒有」。數量 ≥ 3 的 `bulk` 也由後端直接當 `true`
- 任務 4.4（讓品味計算接收外部屬性）和 4.5（甜度預設補位）的內容已經由 `from_model` 和 `attributes` 參數做完，不要再另外做一份。這兩項在你的章節，看過後請自行打勾（10/16 補上）

**給做帳號管理（任務 2.8、2.9）的人**
- `profiles.user_id` 是外鍵：刪帳號要先刪 `profiles` 的那一列，再刪 `users`（5.11 的順序已經是這樣）。每個跑完任務的人都有一列
- 刪掉一個月之後重算 profile 用 `profiles.recompute(session, backends, context, user_id)`（`src/api/profiles.py`），沒有任何品項時它存成 `ready` 為 false 的空 profile。但不要在回應請求的執行緒上直接呼叫：同一個人的上傳任務可能正在跑，舊的讀取可能蓋掉比較新的 profile。要把重算排進 app 的上傳背景執行緒（`app.state.worker`，和上傳任務同一條，profile 的寫入就不會重疊），例如當成一種任務排進去（10/16 補上）

### 13.3 角色 1 轉告（2026-10-15，第 2 週上傳管線，分支 `role-1/uploads`）

上傳（5.4）、任務進度和即時分類的屬性快取（5.5）都接好了，規格的增補都標了「10/15」。品味向量的重算（5.4 第 3 步）和 `GET /api/me/profile` 在下一批做好了，見 13.4；帳號管理還沒做。

**給所有人**
- 資料表變了（多了 `jobs`、`items`、`item_cache`、`profiles`，外鍵會檢查）。第 1 週的資料庫（只有 `users`）不用刪：啟動時會自動補上新的資料表。只有用這個分支較早的 commit 建出來的資料庫要刪掉 `data/app.db*`（資料庫和它的 `-wal`、`-shm` 檔）再跑一次 seed，因為那時的 `items` 等資料表和現在的欄位、索引不同，啟動時不會被改過來
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
- 錯誤：400 `invalid_csv` 顯示 `message`（英文，例如缺哪個欄位，或 `Line 3: 消費明細_金額 is not a number` 這樣的第幾行、哪一欄）；413「檔案超過 2 MB」；403 `demo_user_read_only`「示範帳號不能上傳」
- 即時分類框：GPU 模式下 `pending` 會自己變成 `ready`，照 5.5 每 2 秒再問、最多 5 次；503 `model_unavailable` 顯示「分類模型暫時無法使用」。現在的假屬性模型一次就答完每個品名，分類框從來不會是 `pending`；`ATTRIBUTES_MODEL=qwen` 要等角色 3 的模型接上（任務 2.15）才能用，所以目前還看不到 pending 變成 ready，這段先照 5.5 寫好（10/16 補上）

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
- 假用戶擴充到約 300 人時：seed 依位置命名（`demo_001` 起），清單只能從尾端加。`build_personas` 的順序或名字一變，seed 會停下來，要刪掉 `data/app.db*` 重新 seed，擴充時請一起考慮
- demo 用戶之後不能上傳或修改資料（403 `demo_user_read_only`）

**給角色 4**
- v2 網頁放 `src/web_v2/`，伺服器從 `/web/` 提供；需要的頁面從 `src/web/` 複製過去再改，`src/web/` 本身不要改（它是 v1 的建置來源）
- 本機 API 在 `http://127.0.0.1:8000`，文件在 `/docs`。錯誤一律是 `{"detail": "<代碼>"}`；422 的 `detail` 是清單；程式出錯回 500 `internal_error`；401 時回登入畫面
- 要不要顯示 demo 快速切換，看 `GET /api/health` 的 `demo_mode`；名單用 `GET /api/auth/demo-users`
- 即時分類框：第 1 週 `attributes_status` 為 `pending` 時不會自己變成 `ready`，先顯示「待分析」
