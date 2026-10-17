# You are what you buy.

## v2 本機應用（開發中）

v2 由 FastAPI 提供 `/web/`，包含登入、CSV 上傳與進度、消費月報、配對計算及帳號設定。登入首頁直接顯示「我的月報」：首屏以類別金額圖與可點選的品項排行呈現，往下分頁查看消費節奏、動態文字雲、日期分布與月份比較。文字雲提供播放／暫停，並尊重減少動態偏好。已移除獨立品名分類畫面；右上角「設定」提供上傳檔案、帳號設定。配對點選對象後先顯示關係圖，計算明細需自行展開。資料保留在本機 SQLite；API 規格與各角色進度見 [團隊總覽](docs/team/overview.md)。

**本分支已驗證的實際串接（2026-10-16）：** 已整合角色 1 後端，使用 fake 模型與隔離 SQLite，完成註冊／登入、兩個月上傳、月報／品味／配對／計算過程、改名／改密碼／刪月份／登出／刪帳號的實際 HTTP 與瀏覽器驗證。真模型、完整 300 人 seed、Docker 與 CI 尚未驗收。詳見 [整合驗證紀錄](docs/results/role4-integration.md)，產出待 Claude 審核。

### v2 前端展示

以下是 **虛構資料與模擬 API 的前端契約展示**，不是完整後端或真模型驗收影片。每個畫面下方均標示模擬狀態。

![v2 前端契約展示：登入、分類、上傳、月報、配對、計算與帳號管理；使用虛構資料與模擬 API](docs/assets/v2-contract-demo.gif)

上方 GIF 為 10/15 舊版導覽的契約展示；10/17 新版月報首頁與設定選單以實際介面為準，重錄腳本已同步。

可重現錄製方式：在有 Playwright／Chromium 的工具環境啟動本機服務，執行 `node scripts/capture_v2_demo.cjs`，再在有 Pillow 的工具環境執行 `python scripts/build_v2_demo_gif.py`。錄製腳本攔截全部 `/api/` 請求，不建立真實帳號或發票；中間截圖留在被忽略的 `runtime/`。

### 目前可用的啟動方式（Windows）

使用 Python 3.12、Node 24。建立虛擬環境並安裝 `requirements.txt`，不要使用 `uv sync`（`pyproject.toml` 未列服務套件）。

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

在本機 `.env` 設定至少 32 字元的隨機 `JWT_SECRET`，保持 `CATEGORY_MODEL=fake`、`ATTRIBUTES_MODEL=fake` 以驗證流程。不要提交 `.env`；已有設定時不要重新覆蓋。

```powershell
.venv/Scripts/python.exe -m src.api.seed
.venv/Scripts/python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8001
```

開啟 [v2 本機頁面](http://127.0.0.1:8001/web/) 或 [API 文件](http://127.0.0.1:8001/docs)。demo 帳號為唯讀；上傳請註冊自己的帳號。角色 worktree 可共用主資料夾 `.venv`，但 `.env`／資料庫各自獨立，做法見團隊總覽 13.1。

### Docker 交付狀態

**目前本分支沒有 Dockerfile 或 Compose 設定，不能用 Docker 一鍵啟動。** 角色 1 完成容器交付並合併後，預定操作為在專案根目錄設定 `.env`，執行 `docker compose up`，依容器啟動輸出開啟 `/web/`；停止時執行 `docker compose down`。實際 port、模型下載與持久化設定須等 Compose 檔確認，之後才補上可照做的完整步驟。這段是待整合操作說明，尚未通過乾淨電腦驗收。

### 概念與驗證

- [向量化、內積、餘弦與收縮項](docs/team/concepts.md)：兩位虛構人物的 +82% 範例，附本機重算腳本；已用真正 explain API 在隔離資料庫重現。
- `node --test "tests/*.test.cjs"`：前端與既有 v1 回歸。
- `.venv/Scripts/python.exe -m unittest discover -s tests`：後端及計算核心回歸。
- 真 HTTP 瀏覽器整合：`python -X utf8 tests/run_web_v2_live.py` 自動建立臨時 DB、選擇空閒埠並於結束清理；需既有 Playwright／Chromium。
- 瀏覽器契約驗證：`tests/web-v2-account-browser.cjs`、`tests/web-v2-explanation-browser.cjs`；可設定 `NODE_PATH`、`BROWSER_EXECUTABLE` 指向既有 Playwright／Chromium。

## v1 靜態原型

以下內容為 v1 原型的功能與歷史技術規劃；v2 以本頁上方與團隊總覽的現況為準。v1 原始檔維持不變。

## 主要功能

製作自己的每月消費回顧（Recap），分析消費習慣，也和朋友比較品味相似度。

## 後續規劃

很少人會為了展現品味，一直買不喜歡的東西。讓日常消費成為認識彼此的起點。

| 規劃功能 | 使用者用途 | 預期延伸效益 |
|---|---|---|
| 配對品味相近的朋友 | 依喜好與生活圈找同好、交友 | 以交友誘因，協助財政部推廣雲端發票使用 |
| 補登無發票消費 | 補足紀錄，解鎖更多配對 | 無發票消費紀錄做為查稅參考依據 |

[開啟 v1 靜態原型：消費洞察＋朋友品味比較](https://lee851104.github.io/receipt/invoice-insights.html)

![專題網頁預覽：虛構示範人物的品味特質連線圖，中間是品味相似度](readme_pic1.png)

網頁已內含兩個月的**虛構示範資料**與所需程式，店家、品項、日期及金額皆為合成，不代表任何人的實際消費。只要下載 `invoice-insights.html` 一個檔案，即可離線查看消費報告並切換朋友品味比較，不需要其他網頁、程式或資料檔。

## 使用流程

### 黃金圓（Golden Circle）

| 層次 | 專題的回答 |
|---|---|
| 為什麼（Why） | 從日常消費了解自己，也發現與朋友的共同喜好。 |
| 如何做（How） | 整理發票明細、分類消費，呈現每月變化並比較彼此的消費偏好。 |
| 做什麼（What） | 製作每月消費回顧（Recap）與朋友品味相似度比較網頁。 |

### 操作流程

1. **不用記帳，自動拆到品項**：匯入雲端發票 CSV，讀取明細並分類。
2. **看見自己的消費模式**：用動畫、文字雲、日期圖呈現習慣。
3. **選一個標籤，自己跟自己比**：本月與上月兩欄並排，只呈現改變，不評斷好壞。

## 資料

以下皆為虛構示範，包含折扣、零元贈品與待確認分類，用來展示不同情境。

| 月份 | 明細 | 發票 | 金額 |
|---|---|---|---|
| 2026 年 3 月（示範） | 50 筆 | 48 張 | NT$ 7,910 |
| 2026 年 4 月（示範） | 53 筆 | 51 張 | NT$ 8,095 |

- 示範資料由 `src/receipt/demo.py` 獨立產生，不讀取或改寫私人消費紀錄。
- 分類標籤與配色放在 `configs/report.json`；公開品名對照表也只包含示範品項。
- 沒有 2 月資料，所以 3 月不計算月增減；沒有時分資料，所以不做 24 小時分析。
- `python scripts/build_report.py` 預設產生包含報告與朋友比較的單檔示範版 `invoice-insights.html`，不讀取私人資料。
- 私人原始檔與設定保留在本機 `data/`；含真實資料的 `invoice-insights-private.html` 不納入版本追蹤，可單檔直接分享。

## 分類標籤

共 10 種：正餐、飲品、零食甜點、生鮮食材、運動、其他服務、交通、住宿、日用品、電子產品。

- 「待確認」是審核狀態，不列入比較選單
- `configs/item-categories.json` 包含 23 個虛構示範品名，其中未分類商品標記為暫定
- 沒有對照到的品名，會自動歸為「待確認」

### 與既有雲端發票服務的差別

以下以「雲端發票」應用程式（Application，App）的官方說明為例，不代表所有發票服務都相同。

| 比較項目 | 雲端發票 App | 本專題 |
|---|---|---|
| 分類方式 | 已有商品類別與次類別，也能調整商品所屬分類 | 目前用人工對照表，將品項歸入上述 10 個標籤；自動分類模型仍在規劃 |
| 分類調整 | 使用者可在 App 內變更商品的類別與次類別 | 目前需修改分類對照表；未對應的品項標示「待確認」 |
| 查看消費 | 提供消費圓餅圖，可自訂日期區間查看 | 提供文字雲、日期分布，以及所選標籤的本月與上月並排比較 |
| 資料使用 | 在 App 內查看發票與消費分析 | 目前先將下載的發票資料在本機轉換，再用網頁查看 |

既有服務已能進行商品分類。本專題著重把分類結果整理成容易理解的消費回顧，並呈現自己每月的變化。

參考：[雲端發票官方說明：消費分析、自訂日期與編輯商品類別](https://www.ecloudlife.com/w/faq/4)（查閱日期：2026-10-06）。

## v2 系統：啟動與架構

v2 把報告做成一個可以註冊、上傳發票並和朋友配對的服務：一個 FastAPI 行程提供網頁和 API，資料存在一個 SQLite 檔。上方的報告與朋友比較仍是不需要伺服器的單檔網頁（v1），兩者各自獨立。

### 架構

```mermaid
flowchart LR
    B["瀏覽器"] -->|"/web/ 網頁、/api JSON"| F["FastAPI（一個行程）"]
    F --> D[("SQLite：data/app.db")]
    subgraph T["FastAPI 裡的背景執行緒"]
        W["上傳任務、重算"]
    end
    F --> W
    W --> M["src/ml：分類（fake／BERT）、屬性（fake／Qwen，經 llama-server）"]
    M --> R["src/receipt：品味計算、配對、品名隱私"]
```

- 上傳的發票在背景執行緒裡依序處理：品名分類、品項屬性、再算出 18 格品味向量存進資料庫；一次只跑一個任務，所以伺服器只能開一個行程（不要加 `--workers`）。
- 模型都放在 `src/ml` 後面，開發時用 `fake` 假模型就能跑完整流程。`llama-server` 沒開時是無 GPU 模式，沒看過的品名標「待分析」。

### 啟動方式一：Windows，雙擊 `start.bat`

1. 先照 [`docs/team/overview.md`](docs/team/overview.md) 第 12 節「環境」裝好 Python 3.12，在專案根目錄建立虛擬環境 `.venv`，再安裝 `requirements.txt`。用 Python 3.12 內建的 `venv` 和 `pip`（用 `py -3.12` 建立，因為 PATH 上的 `python` 可能是別的版本）：

   ```
   py -3.12 -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

   或者用 uv（要先安裝 uv）：

   ```
   uv venv --python 3.12 .venv
   uv pip install --python .venv/Scripts/python.exe -r requirements.txt
   ```

2. 雙擊 `start.bat`。它會：
   - 沒有 `.env` 時，從 `.env.example` 自動建立，並填入新的 `JWT_SECRET`；已經有 `.env` 就照用，不會改它
   - 放入假用戶（demo 用戶），跑幾次都可以
   - 把伺服器啟動在 `http://127.0.0.1:8000`（只有這台電腦連得到），準備好之後自動打開 `http://127.0.0.1:8000/web/`；API 文件在 `http://127.0.0.1:8000/docs`

手動的等價指令（要自己先把 `.env.example` 複製成 `.env`，`JWT_SECRET` 填一串至少 32 字元的亂碼）：

```
.venv\Scripts\python.exe -m src.api.seed
.venv\Scripts\python.exe -m uvicorn src.api.main:app
```

### 啟動方式二：Docker

```
docker compose up
```

- 打開 `http://127.0.0.1:8000/web/`（網頁）和 `http://127.0.0.1:8000/docs`（API 文件）。埠只開在這台電腦的 `127.0.0.1`，因為 `DEMO_MODE=1` 時，任何連得到伺服器的人都能用假用戶登入。
- 資料庫和下載的模型放在 Docker 的 volume 裡，重建容器資料還在（`docker compose down` 不會刪 volume）。容器自己在資料 volume 裡產生並保存 `JWT_SECRET`（第一次啟動時產生）；compose 不會把環境變數或 `.env` 裡的 `JWT_SECRET` 傳進容器。
- 拉了新的程式碼之後，用 `docker compose up --build` 重新建置映像檔（只打 `docker compose up` 會沿用舊的映像檔）。資料表的欄位或索引改過之後，用 `docker compose down -v`：它會刪掉兩個 volume，等於虛擬環境裡刪掉 `data/app.db*`；資料庫、容器產生的 `JWT_SECRET`（登入過的 token 全部失效）和下載的模型都會重來。
- 容器沒有 GPU，屬性模型預設用假的：`docker-compose.yml` 會把 `ATTRIBUTES_MODEL` 傳進容器，預設是 `fake`，這時主機上有沒有開 `llama-server` 都一樣。設成 `qwen`（用 `docker compose` 的環境變數或根目錄的 `.env`）要等角色 3 的程式（`src/ml/attributes.py`）合併才能用，沒有它時容器會用一行訊息停下來。容器預設會去連主機的 `http://host.docker.internal:8080`，連得到時 `/api/health` 的 `gpu_mode` 是 `true`，連不到是 `false`（無 GPU 模式；`ATTRIBUTES_MODEL=qwen` 時 `models.attributes` 會是 `cache_only`，只用快取裡的答案）；要連別的位址，設 `DOCKER_LLAMA_SERVER_URL`，`ATTRIBUTES_MODEL` 是 `fake` 時它只會改變 `gpu_mode`。容器不用 `.env` 裡的 `LLAMA_SERVER_URL`，因為那是給虛擬環境用的 `http://127.0.0.1:8080`，在容器裡指的是容器自己。
- `CATEGORY_MODEL`、`CATEGORY_MODEL_REPO`、`CATEGORY_MODEL_REVISION` 從執行 `docker compose` 的環境變數，或專案根目錄的 `.env` 讀取（compose 會讀它）。`CATEGORY_MODEL` 預設是 `fake`。設成 `bert`，並同時設 `CATEGORY_MODEL_REPO`（Hugging Face 上公開的模型庫）和 `CATEGORY_MODEL_REVISION`（固定版本）時，第一次啟動會把分類模型下載到 volume；下載失敗時服務照樣啟動，`/api/health` 的 `models.category` 顯示 `unavailable`。只有容器會下載：`start.bat` 和直接跑 `uvicorn` 都不會（`huggingface_hub` 只裝在 `requirements-docker.txt`）。目前真的 BERT 還沒接上（任務 2.15），就算模型下載好了，`bert` 也一律顯示 `unavailable`，所以先用預設的 `fake`。
- 映像檔只放 `configs/` 和 `src/`，不含 `data/`、`rawdata/`、CSV 和 `.env`。GitHub Actions 在每次 push 都會建置映像檔、檢查裡面沒有私人檔案，並用 `docker compose up` 啟動一次，確認 `/api/health` 回報 demo 模式、`/api/auth/demo-users` 列得出假用戶。

### 為什麼沒有用 pgvector

pgvector 是 PostgreSQL 的向量搜尋外掛。這個專題沒有用它，理由記在 `openspec/changes/add-matching-system/design.md` 的 D2：

- 品味相似度不是單純的餘弦。`compare` 會略過其中一方沒有資料的格子，還要求至少 5 格雙方都有的雙向格才給分數；pgvector 內建的餘弦做不到這兩件事。
- 用它就得多跑一個資料庫服務，每台開發電腦都要裝；SQLite 只有一個檔案。
- 配對在每次查詢時當場算：300 人 × 18 格不到 1 秒，不需要向量索引。

## 技術規劃

| 工作 | 技術 | 狀態 |
|---|---|---|
| 讀取與清理 | Python（目前用標準函式庫 csv；規劃改用 pandas） | 部分完成 |
| 品項分類 | 比較 TF-IDF＋邏輯回歸、Embedding＋邏輯回歸、BERT 微調 | 未開始 |
| 儲存與統計 | DuckDB | 未開始 |
| 前端 | HTML、CSS、JavaScript、SVG | 原型完成 |

### 三種分類模型比較

用相同資料比較三種方法，把發票品名分成 10 類。目前尚未實測，F1 待測，成本先列預估。

| 模型 | 做法 | F1 分數 | 成本（預估） |
|---|---|---|---|
| TF-IDF＋邏輯迴歸 | 看品名中的字詞來分類。 | 待測 | 較低，一般電腦即可執行。 |
| Embedding＋邏輯迴歸 | 先把品名轉成代表語意的數字，再分類。 | 待測 | 依向量模型大小而定，需額外計算與儲存向量。 |
| BERT 微調 | 用商品資料調整現成模型，讓它更適合分類品名。 | 待測 | 訓練成本通常較高，需要較多時間與記憶體。 |

**F1**：各類別分數取平均，介於 0–1，越高代表分類效果越好。[評分定義](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.f1_score.html)

**選擇原則**：比較分類效果、執行時間與硬體費用；效果差不多，就選成本較低的。

<details>
<summary>名詞全名</summary>

- TF-IDF：詞頻－逆向文件頻率（Term Frequency–Inverse Document Frequency）。
- 邏輯迴歸：Logistic Regression。
- Embedding：文字向量嵌入（Text Embedding）。
- BERT：轉換器雙向編碼器表示模型（Bidirectional Encoder Representations from Transformers）；微調為 Fine-tuning。
- 本表 F1 採宏平均 F1 分數（Macro-averaged F1 Score）。

</details>

### 專案結構

```text
receipt/
├── README.md                     # 專題說明與操作指令
├── pyproject.toml                # Python 版本與相依套件設定
├── .gitignore
├── invoice-insights.html         # 已內嵌示範資料與程式的公開成品
├── invoice-insights-private.html # 真實資料原版，僅留本機、不上傳
├── presentation.html             # 可直接開啟的兩頁簡報
├── readme_pic.jpg                # 消費洞察預覽圖
├── readme_pic1.png               # README 使用的朋友品味比較預覽圖
├── configs/
│   ├── report.json               # 輸入資料清單、分類名稱與配色
│   └── item-categories.json      # 品名與分類的人工對照
├── src/
│   ├── receipt/
│   │   ├── __init__.py
│   │   ├── demo.py               # 獨立產生虛構示範消費
│   │   ├── invoices.py           # 解析、分類與發票號碼代碼化
│   │   └── build.py              # 整合資料、樣式與程式，產生單檔網頁
│   └── web/
│       ├── invoice-insights.html # 網頁原始模板，不含發票資料
│       ├── styles.css            # 網頁樣式
│       ├── insights-ui.js        # 消費洞察與圖表
│       ├── monthly-comparison.js # 月份比較計算
│       ├── comparison-ui.js      # 比較介面
│       ├── flow-navigation.js    # 三區域導覽
│       ├── taste-comparison.html # 內嵌朋友比較畫面的來源
│       ├── taste-profile.js      # 偏好摘要與分享連結格式
│       ├── taste-export.js       # 報告匯出與比較入口
│       └── taste-navigation.js   # 單檔內的畫面切換與返回
├── scripts/
│   └── build_report.py           # 產生網頁的執行入口
├── tests/                        # 資料、產生流程與前端測試
├── data/                         # 僅留本機，不追蹤到 Git
│   ├── raw/                      # 原始發票 CSV
│   ├── processed/                # 產生的示範 report-data.js
│   └── private/                  # 私人設定、品名對照與備份
└── prototypes/
    └── annual-review.html        # 保留的早期年度回顧原型
```

報表核心程式（`src/receipt/`）只使用標準函式庫，需 Python 3.10 以上；後端（`src/api/`）需要的套件列在 `requirements.txt`；前端測試另需 Node.js。

```sh
python scripts/build_report.py
python -m unittest discover -s tests -v
node --test tests/monthly-comparison.test.cjs tests/comparison-interface.test.cjs tests/taste-profile.test.cjs
```

公開示範版與全部測試都不需要私人資料，可在剛下載的專案直接執行。

若要重新產生自己的報告，先在 `data/private/report.json` 設定 `input_files`（原始 CSV 路徑）、`category_catalog`（私人品名對照表路徑）與 `categories`（分類名稱及配色，可參考公開設定）。所有路徑相對於專案根目錄，再執行：

```sh
python scripts/build_report.py --private
```

此指令只更新 `invoice-insights-private.html`，不覆寫公開示範版。CSV 指逗號分隔值（Comma-Separated Values）檔案，目前接受電子發票匯出欄位，一份檔案一個月。

`data/`、`invoice-insights-private.html` 與未來的 `models/` 已排除版本追蹤。私人版本仍含真實店家、品名、日期與金額，請自行決定分享對象。

目前尚未訓練模型或提供後端服務，因此不建立空的模型訓練、特徵工程、筆記本或服務目錄，待功能實作時再加入。

## 與朋友比較偏好

報告上方可點「比較跟朋友品味差多少」開啟朋友比較，預設以左側小安、右側小宇進行比較，兩側網址欄會自動填入示範人物。按「匯出我的品味連結」會產生你的品味連結，面板會列出朋友會看到的品名，可以先檢查再分享；按「帶到朋友比較頁」會把你放在左側，直接和示範的小宇比較。到[朋友比較畫面](https://lee851104.github.io/receipt/invoice-insights.html#friends)貼上兩人的連結；兩人都有品味特質時顯示品味特質連線圖，圖中間寫著品味相似度；只匯入一人，或連結沒有品味特質時，圖的位置會說明原因。點「返回消費洞察」即可回到同一檔案內的報告。

品味連結包含暱稱、涵蓋月份、10 類已確認品項的筆數、17 項品味特質、各消費訊號的彙總值（例如每餐平均花費、每月 3C 花費、每月次數），以及每個訊號最常買的品名；不包含店名、行政區、地址、日期、單筆金額或發票號碼。品名裡的地名會拿掉，住宿只寫「旅館住宿」，長途交通只寫交通方式。舊版連結只有暱稱、月份與 10 類筆數，仍可貼上，但沒有品味特質，畫不出連線圖。資料放在網址片段（URL Fragment）內，不上傳至伺服器；這不是加密，取得完整連結的人可以讀取這些內容。公開示範版匯出的仍是虛構資料。

品味相似度是兩人 17 項品味特質的餘弦相似度（Cosine Similarity），範圍 −100%～+100%，寫在上方的大字與連線圖中間。圖中間的光越亮，代表分數離 0 越遠（綠光是合拍、橘光是相反）；中間每條線加減的分數越多，線就越亮。

本機 `file:` 連結不能讓朋友直接開啟你的電腦檔案。示範時直接傳送 `invoice-insights.html` 即可；對方下載後可離線操作報告與比較畫面，再把你的完整連結貼進比較畫面。線上示範也使用同一個整合檔案。
