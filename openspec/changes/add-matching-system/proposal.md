# Proposal

## Why

目前的 receipt 是一個靜態單檔網頁：只能比對 40 個寫死的假用戶，品項屬性靠關鍵字規則判斷，也沒有後端、資料庫或登入，沒辦法讓真人上傳發票後互相配對。這是 4 人職訓結案專案（2026-11-10 左右發表），也是應徵 AI 軟體工程師的作品，所以需要一條**架構完整、每一層都講得清楚**的管線：發票 → 模型 → 品味向量 → 配對 API → 網頁。模型準確度排在第二。

## What Changes

- 新增 FastAPI 後端與 SQLite 資料庫，API 一律在 `/api` 底下，共 9 項功能、17 個端點：帳號（註冊、登入、demo 名單與切換）、上傳發票 CSV、查詢處理進度、品名即時分類、我的品味向量與月報、配對清單、計算過程、健康檢查、帳號管理。路徑、欄位、錯誤代碼和設定名稱以 `docs/team/overview.md` 第 5 節為準
- 上傳時套用依真實發票訂出的規則：作廢發票略過、低於 10 元或金額有小數的明細略過、小數數量當成 1；分類信心不足的品名歸到「待確認」，不計入品味
- 新增品名分類模型：把品名分成 10 個消費類別。正式模型是 `bert-base-chinese` 微調，TF-IDF 與 embedding 加邏輯迴歸當比較基準
- 新增本機 LLM 屬性判斷：判斷每個品名的 16 個屬性和 7 個基本旗標，取代 `attributes.describe` 的關鍵字規則。結果會存進快取，並在背景處理
- 品味向量沿用現有的 18 格；配對沿用現有公式和門檻（+30% 算相近、−10% 算互補，各取前 5）
- 新增「計算過程」：逐格列出內積的每一項，網頁上也有對應的面板和兩人的關係圖；關係圖會顯示雙方常買的品名，但先去掉地名，也不顯示店家、日期和金額
- 新增約 300 個假用戶，走完整條管線產生，取代原本寫死的 40 人
- 新增評估：三個分類模型的比較表（測試集只放真實品名）、配對驗證、LLM 屬性的人工複核
- 新增帳號管理：查看與修改個人資料、修改密碼、刪除帳號（連同所有資料）、刪除單一月份資料、登出
- 新增無 GPU 模式和一鍵啟動，沒有顯示卡的組員也能跑完整 demo
- 新增 Docker：`docker compose up` 一個指令就能用無 GPU 模式啟動；分類模型公開在 Hugging Face，第一次啟動時自動下載
- 新增 GitHub Actions，每次 push 都跑全部測試，模型用假替身
- v2 網頁放在 `src/web_v2/`，從現有網頁複製過去再改成向 API 要資料，由同一個服務在 `/web/` 提供；GitHub Pages 上的 v1（根目錄 `invoice-insights.html`）和它的建置來源 `src/web/` 凍結不動

## Capabilities

### New Capabilities

- `user-auth`：帳號註冊、密碼登入取得 JWT，以及只在 demo 模式下開放的快速切換身分
- `user-account`：查看與修改個人資料、修改密碼、刪除帳號和所有資料、登出
- `invoice-ingestion`：上傳財政部電子發票 CSV、檢查格式、在背景處理、查詢處理進度，以及刪除單一月份的資料
- `item-classification`：把品名分成 10 個消費類別，包含即時分類單一品名
- `item-attributes`：用本機 LLM 判斷品名的 16 個屬性和 7 個基本旗標，包含快取，以及模型不在時的「待分析」狀態
- `taste-profile`：從一個人的品項算出 18 格品味向量和月報
- `taste-matching`：相似度計算、相近與互補清單、距離篩選，以及計算過程
- `web-app`：v2 網頁的使用流程，包括登入、上傳與進度、即時分類、我的品味、配對清單、計算過程面板
- `service-runtime`：一鍵啟動、Docker 啟動、GPU 與無 GPU 兩種模式，以及健康檢查
- `demo-population`：約 300 個假用戶與假品名資料，透過完整管線產生
- `model-evaluation`：評估資料的切分規則，以及要產出的三份評估結果

### Modified Capabilities

（無。`openspec/specs/` 目前是空的，現有功能還沒有寫成規格。）

## Impact

- **新程式：** `src/api/`（FastAPI、資料庫、登入、背景任務）、`src/ml/`（模型介面與假替身）、`src/web_v2/`（v2 網頁：從 `src/web/` 複製要用的頁面改成向 API 要資料，並新增登入、上傳和計算過程畫面）、`datasets/synthetic/`（假品名、假用戶資料，可進 git）、`.github/workflows/`、`Dockerfile`、`docker-compose.yml`、`.dockerignore`
- **外部服務：** 分類模型公開在 Hugging Face 的模型庫，以固定版本下載
- **修改現有程式：**
  - `src/receipt/invoices.py` 的解析改成略過作廢發票、低於 10 元或有小數金額的明細，小數數量當成 1（現在遇到這些會直接報錯）
  - `src/receipt/attributes.py` 的屬性來源改由模型提供，`channel_of` 保留
  - `src/receipt/personas.py` 擴充到約 300 人
  - `src/receipt/similarity.py` 的公式與 `configs/traits.json` 的門檻**不變**
- **不能變動：** 根目錄 `invoice-insights.html`（GitHub Pages v1）、`src/web/`（v1 報告的建置來源，不提供也不為 v2 修改）、現有 159 個測試的行為
- **新套件：** `fastapi`、`uvicorn`、`sqlmodel`、`python-multipart`、`pyjwt`、`pwdlib[argon2]`、`python-dotenv`，測試用 `httpx2`；BERT 上線時再加 CPU 版 `torch`、`transformers`。另外需要 llama.cpp 的 `llama-server` 執行檔（放在 `runtime/`，不進 git）
- **硬體：** 選型和訓練用 RTX 4060 8G；其他組員的電腦用無 GPU 模式
- **隱私：** 真實發票、真實品名與標註、模型檔都不進 git；真實品名只用本機模型處理。分類模型的權重會公開在 Hugging Face，但訓練資料不公開
- **參考文件：** `docs/team/overview.md`（27 項決定、第 5 節 API 規格、角色分工、時程）；`docs/superpowers/plans/2026-10-14-api-skeleton.md`（角色 1 第 1 週的實作計畫）
