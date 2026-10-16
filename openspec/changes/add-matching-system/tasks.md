# Tasks

> 這份清單依角色分區。叫 AI 實作時要說「只做第 N 區（角色 N）」，不要讓它去做別人的區塊。第 1 區是共同基礎，由角色 1 主導；第 6 區是整合檢查，最後由全隊一起做。
> API 的路徑、欄位、錯誤代碼和設定名稱以 `docs/team/overview.md` 第 5 節為準；角色 1 第 1 週的逐步做法在 `docs/superpowers/plans/2026-10-14-api-skeleton.md`。每週目標和分工見 overview。

## 1. 共同基礎（角色 1 主導，第 1 週）

- [x] 1.1 API 規格寫進 `docs/team/overview.md` 第 5 節並定案（2026-10-14），帳號管理的 5.11 在 10/15 補上
- [x] 1.2 `.gitignore` 擋掉壓縮檔（`*.rar`、`*.zip`、`*.7z`）和 `/runtime/`，`git status` 不再列出 `rawdata.rar`
- [x] 1.3 完成第 1 週計畫的 Task 0–1：`requirements.txt`、`.env.example`、`src/ml/fields.py`、`src/ml/fakes.py`；單元測試驗證假分類回傳 10 個加總為 1 的機率、假屬性回傳剛好 23 個欄位

## 2. 角色 1：後端與配對

- [x] 2.1 完成第 1 週計畫的 Task 2–11（設定、模型接口與 GPU 偵測、健康檢查、密碼與 token、註冊登入、品名即時分類、seed、demo 名單與切換、`/web/` 網頁（`src/web_v2/` 的預留頁）、總覽的啟動說明）；Python 154 個、Node 82 個測試通過，實際啟動後 `/api/health`、`/api/auth/demo-users`、`/docs`、`/web/` 都正常
- [x] 2.2 修正發票解析：「作廢」開頭的發票略過、金額低於 10 元或有小數的明細略過、小數數量當成 1、其他不認得的狀態才報錯；用虛構的 CSV 寫測試涵蓋這幾種情況，現有測試照樣通過
- [x] 2.3 加入 `jobs`、`items`、`item_cache`、`profiles` 四張表，實作 `POST /api/invoices`（當場解析，400 `invalid_csv`、413 `file_too_large`，成功回 202 和 `job_id`、`month`、`rows`）和 `GET /api/jobs/{job_id}`；測試涵蓋 invoice-ingestion 規格的情境（含重傳取代、別人的工作回 404、假用戶上傳回 403 `demo_user_read_only`、原始檔不保留、發票號碼已編碼）
- [x] 2.4 實作背景任務：分類（最高機率低於 `CATEGORY_MIN_PROB` 存成 10）、查 `item_cache`、無 GPU 時記成待分析、重算 `profiles`；GPU 模式下即時分類遇到新品名要排進背景分析；用假模型測試 item-classification 和 item-attributes 規格的情境，包含分類模型 `unavailable` 時即時分類回 503、背景工作變成 `failed`（10/15 完成：重算 `profiles` 在 `role-1/profiles`，其他在 `role-1/uploads`）
- [x] 2.5 實作 `GET /api/me/profile`；測試 taste-profile 規格的情境（還沒上傳、`ready` 為 false 時 18 格都是 `null`、兩個月合併、`pending_attributes`、類別 10 不計入）（10/15 完成，在 `role-1/profiles`）
- [x] 2.6 實作 `GET /api/matches`；測試 taste-matching 規格的門檻、排序和同分規則、只取前 5、`eligible` 和 `within`、四種範圍、`no_home_area`、自己資料不足，以及 0.295 這個邊界值（10/16 完成，在 `role-1/matches`）
- [x] 2.7 實作 `GET /api/matches/{user_id}/explain`；測試固定 18 格、各格貢獻加總等於分數、與 `tests/fixtures/similarity-cases.json` 一致、`not_enough_items` 和 `too_few_shared`、查自己回 400 `self`、不存在回 404，以及 `network` 裡的品名已經去掉地名、沒有店家、日期和任何一筆的金額（10/16 完成，在 `role-1/matches`；另外測試假用戶查真實使用者回 404）
- [x] 2.8 實作 overview 5.11 的帳號管理（`GET`／`PATCH /api/me`、`POST /api/me/password`、`DELETE /api/me`、`POST /api/auth/logout`），改密碼和登出都換掉 `users.token_key`（假用戶登出不換）（權杖本來就帶著它，第 1 週已有，不加欄位、不比較簽發時間）；測試涵蓋 user-account 規格的全部情境（改名長度、`wrong_password`、改密碼後舊權杖 401 而新權杖可用、登出讓所有裝置失效、登出後重新登入可用、刪帳號時的快取清理、還有上傳工作時刪帳號回 409 `job_in_progress`、`demo_user_read_only`）（10/16 完成，在 `role-1/account`）
- [x] 2.9 實作 `DELETE /api/me/months/{month}`；測試刪除後品味向量重算、`month_not_found`、`job_in_progress`（10/16 完成，在 `role-1/account`）
- [ ] 2.10 新增 `start.bat`：檢查 `.env`、執行 seed、啟動 uvicorn、打開 `/web/`；在沒有 GPU 的電腦上手動確認，點兩下就能打開 `/docs` 和 v2 網頁（10/16：程式和文件在 `role-1/deploy`；還差：在沒有 GPU 的電腦上雙擊確認）
- [ ] 2.11 新增 GitHub Actions，用 Python 3.12 和 Node 24 執行 `python -m unittest discover -s tests` 和 `node --test "tests/*.test.cjs"`，模型設定為 fake；確認 PR 上是綠燈，執行紀錄裡也沒有下載任何模型（10/16：程式和文件在 `role-1/deploy`；還差：push 後 PR 上的綠燈）
- [ ] 2.12 新增 `Dockerfile`、`docker-compose.yml`、`.dockerignore`，並在 CI 加上 `docker build`；確認映像檔裡找不到 `rawdata/`、`data/`、CSV、壓縮檔和 `.env`，CI 上建置成功（10/16：程式和文件在 `role-1/deploy`；還差：push 後 CI 的 docker build、映像檔檢查和 `docker compose up` 啟動）
- [x] 2.13 實作容器的啟動流程：`CATEGORY_MODEL=bert` 而且沒有模型時，從 `CATEGORY_MODEL_REPO` 下載 `CATEGORY_MODEL_REVISION`；`DEMO_MODE=1` 而且資料庫是空的時，自動執行 seed；用無效的模型庫名稱測試下載失敗時服務照樣啟動、健康檢查顯示 `unavailable`（10/16 完成，在 `role-1/deploy`）
- [ ] 2.14 README 補上架構圖、啟動步驟（虛擬環境和 Docker 兩種），以及沒有採用 pgvector 的原因；請另一位組員照著文件從零啟動成功（10/16：程式和文件在 `role-1/deploy`；還差：請另一位組員從零照 README 啟動）
- [ ] 2.15 角色 2、3 交出真模型後（3.6、4.3），在 `src/api/backends.py` 的 `load_backends` 接上 `CATEGORY_MODEL`、`ATTRIBUTES_MODEL` 的真實作（目前只接受 `fake`）；用 `tests/model_contract.py` 的 `check_classify`、`check_describe` 確認回傳格式，健康檢查顯示實際的模型名稱

## 3. 角色 2：分類模型

- [ ] 3.1 用 AI 生成稀少類別的假品名，每類至少 50 個，存成 `datasets/synthetic/item-names.jsonl`（`name`、`category`、`source="synthetic"`）；用腳本確認各類的數量，並掃描確認沒有任何真實品名
- [ ] 3.2 在本機切分訓練集和測試集，測試集只放人工確認過的真實品名；切分檢查腳本確認測試集裡沒有假品名
- [ ] 3.3 和角色 3 合作，讓 Qwen 預標真實品名，再由 4 人分工複核；確認每個真實品名都已標示為人工確認
- [ ] 3.4 用新資料重跑 A（TF-IDF）和 B（embedding）兩個基準，產出和 `experiments/category-models/RESULTS-B.md` 同樣格式的結果
- [ ] 3.5 在 4060（或 Colab）上微調 `bert-base-chinese`，保存模型和訓練紀錄；確認模型可以重新載入，並對測試集跑完預測
- [ ] 3.6 用 BERT 實作 `src/ml/category.classify`，`CATEGORY_MODEL=bert` 時從 `CATEGORY_MODEL_DIR` 載入，並把 CPU 版的 `torch`、`transformers` 加進服務的套件清單；測試沒有模型檔時健康檢查顯示 `unavailable` 而不是猜一個類別，並記下用 CPU 分類 1000 個品名的時間
- [ ] 3.7 依 model-evaluation 規格產出三個模型的比較表和混淆矩陣（同一份測試集；測試資料少於 5 筆的類別不計分並列出），寫成 `docs/results/classification.md`；掃描確認裡面沒有任何真實品名
- [ ] 3.8 在 `docs/team/concepts.md` 寫「邏輯迴歸」段落，用 1–2 個假品名說明從向量到機率的過程
- [ ] 3.9 第 3 週把 BERT 模型公開到 Hugging Face：固定一個 revision，模型卡寫明訓練資料包含真實品名但不公開；公開前掃描模型卡和設定檔，確認沒有任何真實品名；把 `CATEGORY_MODEL_REPO`、`CATEGORY_MODEL_REVISION` 寫進 `.env.example`，並確認一台全新的電腦啟動後，健康檢查顯示 `bert`

## 4. 角色 3：LLM 屬性與假用戶

- [ ] 4.1 在 4060 電腦上照 overview 第 12 節裝好 NVIDIA 驅動和 CUDA 版的 `llama-server`（放在 `runtime/`）；確認 `nvidia-smi` 看得到顯示卡，`llama-server.exe --list-devices` 看得到 `CUDA0`，對測試 prompt 有回應
- [ ] 4.2 用 `experiments/receipt-attributes/` 的同一套評估，比較 Qwen3-4B 和約 5 GB 的候選模型，並更新選型紀錄；第 1 週結束還沒定案就用 Qwen3-4B
- [ ] 4.3 實作 `src/ml/attributes.describe_items`（`ATTRIBUTES_MODEL=qwen`）：呼叫 `LLAMA_SERVER_URL`、套用 `bulk_rule` 和 `sugar_guard`、把 fun 對應成中文值、保留 `null`；用錄下來的回應做測試，不需要 GPU
- [ ] 4.4 讓 `attributes.describe` 可以接收外部屬性，`channel_of` 照舊；現有測試照樣通過，另外新增外部屬性的測試（10/15：角色 1 已用 `attributes.from_model` 和 `signals`／`traits` 的 `attributes` 參數做完，在 `role-1/profiles`，見 design D6）
- [ ] 4.5 在品味計算中加入甜度預設補位；測試沒寫甜度的手搖奶茶，屬性回傳的 `sugar` 是 `null`，但 sweet 格把它當成全糖（10/15：預設補位已在 `attributes.from_model` 裡，角色 1 做完，在 `role-1/profiles`）
- [ ] 4.6 把 `personas.py` 擴充到約 300 人；測試 8 種類型的人數相差不超過 1 人、同一個種子產生的結果完全相同，而且 seed 之後 `/api/auth/demo-users` 列出約 300 人
- [ ] 4.7 擴充 seed：假發票寫進 `items`，假品名的屬性結果存成 `datasets/synthetic/attribute-cache.jsonl` 並載入 `item_cache`，再走一般的管線算出品味向量；在無 GPU 模式下執行，確認每位假用戶都有品項紀錄，重新計算也得到相同的向量
- [ ] 4.8 組織 4 人人工複核 100 個品名，產出 23 個欄位的 precision、recall、F1 和 `null` 比例，寫成 `docs/results/attributes.md`（只放彙總數字）；掃描確認裡面沒有任何真實品名
- [ ] 4.9 訂出「相反類型」對照表，執行配對驗證（整體和 8 種類型各自的同類型命中率，以及相反類型命中率），寫成 `docs/results/matching.md`

## 5. 角色 4：前端與展示

- [ ] 5.1 在 `src/web_v2/` 新增 API 客戶端模組：自動附上權杖、收到 401 就導向登入、把錯誤代碼對應成中文；用 `node --test` 測試這三種行為
- [ ] 5.2 把 v2 入口做在 `src/web_v2/index.html`（第 1 週放了預留頁），由服務在 `/web/` 提供；要用的頁面和 JS 從 `src/web/` 複製到 `src/web_v2/`，`src/web/` 不改；確認根目錄的 `invoice-insights.html` 和 `src/web/` 都沒有任何變動（`git diff` 是空的）
- [ ] 5.3 實作登入和註冊畫面，以及 demo 模式下用 `GET /api/auth/demo-users` 產生的切換選單；JS 測試涵蓋「401 就導向登入」和「demo 選單只在 demo 模式出現」
- [ ] 5.4 實作上傳畫面、進度輪詢和錯誤訊息（`invalid_csv` 附上系統說明、`file_too_large`、工作 `failed`）；用假 API 測試完成和失敗的畫面
- [ ] 5.5 實作品名即時分類框：先顯示類別和機率，屬性 `pending` 時顯示「分析中」，每 2 秒重查、最多 5 次，之後顯示「稍後再查」；JS 測試涵蓋這幾種狀態
- [ ] 5.6 把月報、品味關係圖和配對頁（從 `src/web/` 複製到 `src/web_v2/` 的版本）改成使用 API 資料（月報沿用 `months` 的現有格式，配對狀態文字用 `eligible` 和 `within`）；`src/web/` 不動，現有 82 個 JS 測試照樣通過；複製過去而有改動的 JS，要有對應的測試（可以餵假 API 資料）
- [ ] 5.7 實作計算過程面板，並用 `explain` 的 `network` 畫兩人的關係圖；JS 測試確認面板上的百分比和卡片上的一樣，逐格的數字也和 API 回傳的一致
- [ ] 5.8 撰寫 `docs/team/concepts.md` 的向量化、內積、餘弦和收縮項段落，用兩位假用戶舉例；確認文件裡的數字可以用計算過程 API 重現
- [ ] 5.9 更新 README：v1 連結標示為原型，放上 v2 的 demo 影片或動圖（在 `.gitignore` 為這些圖檔加上例外），並寫出 `docker compose up` 的使用方式；確認 GitHub 上的圖片和連結都能正常顯示
- [ ] 5.10 實作帳號設定頁：修改顯示名稱、修改密碼、逐月刪除（先確認）、刪除帳號（輸入密碼確認）、登出，假用戶唯讀；JS 測試涵蓋 web-app 規格的帳號設定情境

## 6. 整合檢查（第 3 週結束到第 4 週，全隊）

- [ ] 6.1 無 GPU 端到端：在沒有顯示卡的電腦一鍵啟動 → 註冊 → 上傳一份真實格式的 CSV → 進度完成 → 我的品味 → 配對 → 計算過程，依 web-app 規格的情境逐一走過並記錄結果
- [ ] 6.2 GPU 端到端：在 4060 電腦上即時分類一個新品名，確認屬性從 `pending` 變成 `ready`；再把一個有待分析品名的月份重新上傳，確認待分析數量歸零、品味向量更新
- [ ] 6.3 帳號管理端到端：在網頁上註冊 → 上傳兩個月 → 刪除其中一個月 → 改顯示名稱 → 改密碼 → 登出 → 用新密碼登入 → 刪除帳號，確認每一步都和 user-account、web-app 規格一致，最後這個帳號無法登入、也不在任何人的配對清單裡
- [ ] 6.4 Docker 端到端：在一台只裝了 Docker 的乾淨電腦上執行 `docker compose up`，確認模型自動下載、假用戶自動匯入，並用 demo 快速切換走完配對和計算過程；重建容器後資料仍在
- [ ] 6.5 執行 `openspec validate add-matching-system --strict` 並通過；確認每一個規格情境都有對應的自動測試或手動檢查紀錄，`/docs` 也和 overview 第 5 節一致
- [ ] 6.6 隱私檢查：掃描 git 追蹤的所有檔案和 Docker 映像檔，確認找不到任何真實品名或店家名稱
- [ ] 6.7 11/04 停止加功能：在 `main` 上打 `v2-feature-freeze` 標籤，之後的 PR 只能修錯誤

## Workflow follow-up

- 全部完成並審查後，執行 `/openspec-archive-change add-matching-system` 歸檔，讓 11 份規格成為 `openspec/specs/` 下的正式規格
- 歸檔後確認 `openspec/specs/` 底下有 11 個能力資料夾，而且每份規格的 Purpose 都不是 TBD
