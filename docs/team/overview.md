# 消費配對系統：團隊總覽

> 給 4 位組員和各自的 AI 先讀的唯一一份文件。最後更新：2026-10-14。
> 交給 AI 時可以這樣說：「先讀 `docs/team/overview.md`，我是角色 N，今天要做第 N 週的哪一項。」

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
| 測試 | Python 77 個（unittest）、JS 82 個（node:test），全部通過 | `tests/` |
| 分類實驗 | 品名 → 10 類。A：TF-IDF + 邏輯迴歸，macro-F1 0.62；B：bge-small-zh（512 維）+ 邏輯迴歸，macro-F1 0.66。只有 57 個人工確認品名，只能驗證 4 類 | `experiments/category-models/`、`docs/category-models-brief.md` |
| 屬性實驗 | Qwen3-4B（Q4_K_M，2.4 GB）判斷 16 個屬性。真實資料上模型單獨 F1 44%，加規則 94%（事後回測，不是獨立驗證） | `experiments/receipt-attributes/` |

**還沒有的：** 後端、資料庫、登入、CI、BERT。

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
| 11 | 登入 | 帳號密碼 + JWT，另外保留 demo 用的快速切換 |
| 12 | 訓練資料不足 | 先用 AI 生成假品名把稀少類別補到每類 50 個；不夠再請組員提供發票 |
| 13 | 相似度公式 | 保留現有公式（含 0.25 收縮項） |
| 14 | Qwen 執行 | 背景處理 + 快取。改用約 5 GB 的模型，要重跑選型。RTX 4060 8G 從 10/14 起可用 |
| 15 | BERT | `bert-base-chinese`，在 4060 上訓練（4060 被占用時改用 Colab） |
| 16 | 資料庫 | SQLite，相似度用 Python 算。README 註明人數擴大後再改用 pgvector，以及原因 |
| 17 | 評估 | 分類比較表 + 配對驗證 + 抽 100 個品名人工複核 Qwen。**測試集只放真實品名** |
| 18 | 公開範圍 | 程式碼公開。真實發票、真實品名與其標註、模型檔都不進 git |
| 19 | 測試 | GitHub Actions 每次 push 跑全部測試，模型用假替身 |
| 20 | 概念說明 | 說明文件，加上配對頁的「計算過程」面板 |
| 21 | 啟動 | Python 虛擬環境 + 一鍵啟動檔，另做無 GPU 模式 |
| 22 | GitHub Pages | 現有版本凍結成 v1，README 放 v2 的 demo 影片或動圖 |
| 23 | API | 第 5 節：8 項功能、11 個端點 |
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
| `src/ml/` | 模型介面與假替身：`category.py`、`attributes.py`、`fakes.py` | 角色 2、3 |
| `datasets/synthetic/` | 假品名和假用戶資料（JSONL），可以進 git | 角色 2、3 |
| `docs/team/` | 這份總覽、概念說明 | 全體 |

預設套件：`fastapi`、`uvicorn`、`sqlmodel`、`python-multipart`、`pyjwt`、`pwdlib[argon2]`（密碼雜湊）、`scikit-learn`、`torch`、`transformers`。Qwen 用 llama.cpp 的 `llama-server`，後端用 HTTP 呼叫它。Python 統一用 3.12。

## 5. API 規格（2026-10-14 定案）

8 項功能、11 個端點。這一節是正式規格；程式寫好後，FastAPI 自動產生的 `/docs` 要和這一節一致，不一致時改程式。

### 5.1 共通規則

- **路徑**：API 一律以 `/api` 開頭。v2 網頁由同一個 FastAPI 從 `/web/` 提供（`src/web/` 資料夾），同一個網域，所以不用設 CORS。不掛在 `/`，是因為那樣 POST 到不存在的 `/api` 路徑會被靜態檔案接走，回 405 而不是 404
- **格式**：JSON（UTF-8），欄位名用 snake_case。唯一例外：`/api/me/profile` 的 `months` 原樣沿用現有月報格式（`invoices.build_month` 的輸出，例如 `monthNumber`），現有網頁才不用改
- **登入**：除了標「免」的端點，都要帶 `Authorization: Bearer <access_token>`。JWT 用 HS256，`sub` 放 user_id（轉成字串），24 小時過期
- **錯誤**：HTTP 狀態碼加 `{"detail": "<錯誤代碼>", "message": "<說明，可省略>"}`。錯誤代碼是固定的英文 snake_case，前端自己對應成中文。欄位格式錯誤用 FastAPI 預設的 422。需要登入的端點，沒帶 token 或 token 過期都回 401 `not_authenticated`
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

### 5.3 帳號

**`POST /api/auth/register`**：JSON `{"username": "amy", "password": "…", "display_name": "Amy"}`
- `username` 3–32 字元，只能用英數字和底線；`password` 8–128 字元；`display_name` 可省略，1–20 字元，預設同 `username`
- 回傳 201：`{"user_id": 301, "username": "amy", "display_name": "Amy"}`
- 錯誤：409 `username_taken`

**`POST /api/auth/login`**：表單（`application/x-www-form-urlencoded`）`username`、`password`，和 FastAPI 的 OAuth2 表單相同，`/docs` 的 Authorize 按鈕可以直接用
- 回傳：`{"access_token": "…", "token_type": "bearer", "expires_in": 86400}`
- 錯誤：401 `bad_credentials`（帳號不存在和密碼錯誤用同一個代碼）

**`GET /api/auth/demo-users`**：demo 快速切換的名單，只列假用戶
- 回傳：`[{"user_id": 1, "display_name": "咖啡上班族 A", "persona": "咖啡上班族"}, …]`
- `DEMO_MODE` 沒開時回 404，假裝這個端點不存在

**`POST /api/auth/demo-login`**：JSON `{"user_id": 1}`，不用密碼
- 回傳：同 login
- 只能切換成假用戶，註冊的真實帳號一定要用密碼登入
- 錯誤：404（`DEMO_MODE` 沒開，或沒有這個人）、403 `not_demo_user`

### 5.4 上傳與進度

**`POST /api/invoices`**：multipart，欄位名 `file`，一次一個財政部電子發票 CSV（一份一個月），上限 2 MB
- 伺服器先**當場**用 `invoices.build_month` 的規則解析，格式有錯直接回 400；解析成功才建立背景任務
- 同一個人重新上傳同一個月份，會取代那個月的舊資料
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

**`POST /api/items/classify`**：JSON `{"name": "鮮奶茶 微糖"}`，`name` 去掉頭尾空白後 1–100 字元
- 回傳：
  ```json
  {"name": "鮮奶茶 微糖",
   "category": {"id": 1, "name": "飲品", "prob": 0.91},
   "probs": [0.01, 0.91, 0.03, 0.0, 0.0, 0.02, 0.0, 0.0, 0.03, 0.0],
   "attributes": {"food": true, "drink": true, "sugar": 0.3, "alcohol": false, "fun": null, "…": "共 23 個欄位"},
   "attributes_status": "ready"}
  ```
- `category` 一律是模型的第一名（0–9），`probs` 是 10 類各自的機率
- `attributes`：16 個屬性加 7 個基本旗標，欄位名同 `attributes.describe`。每個欄位都可能是 `null`
- 快取裡有 → `ready`。沒有 → `attributes` 為 `null`、`attributes_status` 為 `pending`；GPU 模式下伺服器會同時把它排進背景分析，前端每 2 秒再問一次，最多 5 次

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
  `src/web/trait-network.js` 可以直接拿來畫。資料不夠的人，四個欄位都是 `null`
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
- `models.category`：fake / tfidf / embedding / bert；`models.attributes`：fake / qwen / cache_only（無 GPU 模式）

### 5.10 設定（`.env`，repo 只放 `.env.example`）

| 變數 | 預設 | 說明 |
|---|---|---|
| `JWT_SECRET` | 無，一定要設 | 簽 JWT 用的密鑰，至少 32 字元 |
| `JWT_EXPIRE_MINUTES` | 1440 | token 有效時間 |
| `DEMO_MODE` | 0 | 1 = 開放 `demo-users` 和 `demo-login` |
| `DATABASE_URL` | `sqlite:///data/app.db` | 放在 `/data/` 底下，不會進 git |
| `LLAMA_SERVER_URL` | `http://127.0.0.1:8080` | Qwen 的 llama-server |
| `CATEGORY_MODEL` | fake | fake / tfidf / embedding / bert |
| `ATTRIBUTES_MODEL` | fake | fake / qwen |
| `CATEGORY_MIN_PROB` | 0.5 | 低於這個機率的品名歸到 10 待確認 |

## 6. 模型介面（角色 2、3 交給角色 1）

```python
# src/ml/category.py
def classify(names: list[str]) -> list[dict]:
    """每個品名回傳 {"category": 0–9, "probs": [10 個機率]}。"""

# src/ml/attributes.py
def describe_items(names: list[str]) -> list[dict | None]:
    """每個品名回傳 16 個屬性 + 7 個基本旗標（欄位名見 src/ml/fields.py），
    還沒分析過的回傳 None。null 是不知道，不是 false。"""
```

`src/ml/fakes.py` 提供同樣介面的假替身，回傳固定結果。後端和 CI 一開始全部用假替身，模型好了再換成真的。

回傳值一律用一般的 Python 型別（numpy 的結果先 `.tolist()`），否則 API 會回 500。在自己的測試裡呼叫 `tests/model_contract.py` 的 `check_classify(self, classify)` 和 `check_describe(self, describe_items)`，就能確認格式對不對。

## 7. 角色分工

### 角色 1：後端與配對（組長）

- **負責：** FastAPI、SQLite、登入、CSV 上傳與背景任務、配對和計算過程 API、一鍵啟動、無 GPU 模式、GitHub Actions
- **交出：** 第 5 節的 11 個端點，每個都有測試
- **先讀：** `src/receipt/invoices.py`、`signals.py`、`traits.py`、`similarity.py`、`personas.py`、`configs/traits.json`
- **每週：**
  1. API 規格和 4 人確認；FastAPI 骨架、資料表、註冊登入、`/health`；用假替身跑通
  2. 上傳 → 背景任務 → 品味向量；`/jobs`、`/me/profile`、`/matches`
  3. `/matches/{id}/explain`；換上真模型；匯入 300 個假用戶；CI 綠燈
  4. 修錯；`start.bat`；README 架構段落；8 分鐘講稿素材
- **完成標準：** 在沒有 GPU 的電腦上，一鍵啟動就能跑完整 demo；CI 全綠

### 角色 2：分類模型

- **負責：** 生成假品名、分配真實品名的複核、TF-IDF / embedding / BERT 三個模型的訓練與比較
- **交出：** `src/ml/category.py` 的 `classify()`；比較表（macro-F1、準確率、模型大小、速度）；混淆矩陣；概念說明的「迴歸」段落
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

- **負責：** 現有網頁改接 API、登入和上傳畫面、品名即時分類框、計算過程面板、概念說明文件、README、發表素材整合
- **交出：** v2 網頁（由 FastAPI 提供）；`docs/team/concepts.md`（向量化、餘弦與內積，用假資料舉例）；README 的 v2 影片或動圖
- **先讀：** `src/web/` 全部（特別是 `match.html`、`match-filter.js`、`trait-similarity.js`、`taste-profile.js`）、`src/receipt/build.py`
- **每週：**
  1. 把網頁的資料來源抽成一層，先接角色 1 的假資料 API；登入畫面
  2. 上傳畫面、處理進度、品名即時分類框
  3. 計算過程面板；概念說明文件
  4. README；整合 4 人的發表素材
- **注意：** 根目錄的 `invoice-insights.html` 就是 GitHub Pages 上的 v1，**不要覆蓋它**。v2 的輸出換別的位置

## 8. 時程與砍功能順序

| 週 | 日期 | 全隊目標 |
|---|---|---|
| 1 | 10/14–10/20 | API 規格定案；後端骨架用假替身跑通；假品名；4060 環境與選型 |
| 2 | 10/21–10/27 | 上傳、背景任務、快取；A/B 重跑與 BERT 第一版；Qwen 介接；300 個假用戶；登入畫面 |
| 3 | 10/28–11/03 | **整條管線串通**；評估三項；計算過程面板；CI |
| 4 | 11/04–11/10 | **11/04 起停止加功能，只修錯誤**；文件、README、發表素材 |

落後時依序砍：① 5 GB 模型退回 Qwen3-4B → ② 人工複核從 100 筆縮成 50 筆 → ③ 處理進度只顯示「處理中／完成」。

**不能砍：** 登入、上傳、品名分類、18 格品味向量、相近和互補清單、計算過程面板。

## 9. 協作規則

- 每個角色在自己的分支工作（例如 `role-1/upload-api`），開 PR 合併進 `main`，CI 通過才合併
- 介面先定好再開發；別人的部分還沒好，就用假替身，不要等
- 改到別人負責的檔案時，PR 裡要標註那個角色
- 修改 `src/receipt/` 的行為之前，先確認現有 159 個測試仍然通過
- commit 訊息用英文，文件用繁體中文

## 10. 隱私規則（repo 是公開的）

- **絕對不進 git：** 真實發票 CSV、真實品名和它們的標註、店名、模型檔、`.env`
- `.gitignore` 已經擋掉 `*.csv`、`/data/`、`/models/`、`/runtime/`，以及圖片檔（`*.png`、`*.jpg`、`*.gif` 等）
  - 假資料請存成 JSONL，放在 `datasets/`
  - README 要用的圖，要在 `.gitignore` 加 `!` 例外
- 真實品名只能用本機模型處理，不可以貼到雲端 AI 或線上服務；假品名可以
- 評估報告只放數字，逐筆結果留在本機
- 配對時，對方會看到你每個訊號買最多次的品名（去掉地名後，見 5.8），但看不到店家、日期和金額

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
2. 確認現有測試通過：
   ```
   python -m unittest discover -s tests -v
   node --test "tests/*.test.cjs"
   ```
   預期結果：Python 77 個、JS 82 個全部通過
3. 4060：
   - 安裝 NVIDIA 驅動，用 `nvidia-smi` 確認看得到顯示卡
   - PyTorch 要裝 CUDA 版：到 pytorch.org 選 Windows + pip + CUDA 12.x 取得安裝指令，然後用 `python -c "import torch; print(torch.cuda.is_available())"` 確認輸出 `True`
   - PyTorch 用 `uv pip install --python .venv/Scripts/python.exe torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128`（和分類實驗 B 同版本）
   - llama.cpp 要用 CUDA 版的 Windows 執行檔（GitHub releases 裡名稱有 `cuda` 的那個，加上同版本的 `cudart-llama-bin-win-cuda-12.4-x64.zip`），解壓到 `runtime/llama-b11557-cuda/`，`gpu_layers` 設成全部載入。用 `llama-server.exe --list-devices` 確認看得到 `CUDA0`

### 其他

- 到 GitHub repo 的 Settings → Collaborators，邀請另外 3 位組員
- Claude 的記憶只存在舊電腦上。在新電腦上開始工作時，先請 Claude 讀這份文件
