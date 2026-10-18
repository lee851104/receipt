# Design

## Context

動機見 proposal.md 的 Why；詳細的 27 項決定和角色分工見 `docs/team/overview.md`。

**API 的路徑、欄位、錯誤代碼和設定名稱，以 `docs/team/overview.md` 第 5 節（2026-10-14 定案，10/15 補上 5.11 帳號管理）為準**，這份 design 不重複列出，只記錄架構層級的決定。角色 1 第 1 週的逐步實作在 `docs/superpowers/plans/2026-10-14-api-skeleton.md`。

影響做法的現況：

- 核心邏輯都在 `src/receipt/`，是只用標準函式庫的純函式，流程是 `invoices` → `attributes` → `signals` → `traits` → `similarity`，另外有 159 個測試保護。`similarity.compare` 已經會回傳每一格的貢獻（`parts`）。
- `src/web/` 的 JS 目前讀的是建置時內嵌進 HTML 的資料，相似度另外有一份 JS 版本，兩邊共用 `tests/fixtures/similarity-cases.json`。
- 常去行政區由 `places.areas_of` 從發票推算，不是使用者自己填。
- 原本的 `invoices.build_month` 遇到「作廢」發票或有小數的金額、數量會直接報錯，但 5–8 月的真實發票兩種情況都有。第 2 週加上 `for_upload=True` 的上傳規則（v1 報表照舊）：3–8 月共 336 列，作廢 2 列、依金額規則略過 56 列，留下 278 列。

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
| `users` | `id`、`username`（一律小寫）、`password_hash`（假用戶是空的）、`display_name`、`is_demo`、`persona`（假用戶的類型）、`token_key`（每個帳號一把隨機字串，權杖帶著它，見 D8） |
| `jobs` | 上傳工作：月份、狀態、`done`／`total`、訊息 |
| `items` | 品項：月份、日、發票代碼、店家、行政區、品名、數量、金額、類別（0–9，或 10 待確認）。屬性是否待分析不存欄位，看 `item_cache` 有沒有這個品名（目前的屬性模型）；用「使用者＋月份」的複合索引查詢 |
| `item_cache` | 品名、模型版本、23 個欄位的結果 |
| `profiles` | 每人的 18 格向量、常去行政區、有效品項數、更新時間 |

第 1 週只有 `users`，其餘四張在第 2 週接上傳時加入。SQLite 開 WAL 模式、每個連線都打開外鍵檢查，寫入都用短交易，呼叫模型的時候不佔著連線。`jobs` 的編號用 AUTOINCREMENT，刪掉之後也不會重複使用。資料庫的錯誤訊息不印參數（`hide_parameters`），免得品名進到 log。沒有引入資料庫遷移工具：SQLModel 的 `create_all` 會建立還不存在的資料表（第 1 週只有 `users` 的資料庫因此直接升級），但不會修改已經存在的資料表，所以開發用的資料庫只有在既有資料表的欄位或索引改變時，才刪掉 `data/app.db*`（連同 `-wal`、`-shm` 檔）重建，再跑一次 seed。

- 替代方案：PostgreSQL + pgvector。否決，因為 `compare` 會略過沒有資料的格子，還要求至少 5 格共同的雙向格，pgvector 內建的餘弦做不到這兩件事；而且每台開發用的電腦都得多跑一個資料庫服務。

### D3. 配對在每次查詢時即時計算

拿 `profiles` 裡所有人的向量逐一跑 `similarity.compare`（300 人 × 18 格不到 1 秒），再套用 `configs/traits.json` 的門檻和 `places` 的距離。計算過程直接使用 `compare` 回傳的 `parts`，另外補上分母的各項，所以「貢獻加總 = 分數」一定成立；關係圖的資料用現有的 `build.trait_network_data`，品名經過 `items.label` 去掉地名（overview 5.8）。前端只負責顯示，不再自己算分數。門檻用整數百分比判斷，和 v1 的 `src/web/match-filter.js` 同一套；清單的排名在 `src/api/matching.py`（`entries` 打分數、`pick` 判斷門檻、距離、排序和前 5 名），配對驗證（任務 4.9）也用它，不另寫一份。（10/16 補上）計算過程的關係圖資料在查詢時用兩人存著的品項和屬性快取當場算（`profiles.history` + `traits.explain`，不問模型、不寫入），關係圖整個用查詢時算出的品味（向量、push、訊號、品名），所以 push 加起來等於向量；`cells` 和分數用存起來的向量，和配對清單一致，兩者只在重算還沒跑的時候暫時不同。（10/16 補上）

- 替代方案：預先算好所有配對並存起來。否決，因為 300 × 300 約 9 萬筆，每次有人上傳就要全部重算。

### D4. 背景任務分兩段

第一段在請求裡同步完成：解析整份 CSV（略過作廢、低於 10 元、金額有小數的明細；小數數量當 1），格式不對當場回 400，不建立工作。

第二段交給背景的工作執行緒執行：
1. 列出不重複品名，呼叫 `classify()`；最高機率低於 `CATEGORY_MIN_PROB` 的存成 10 待確認
2. 後端先查自己的 `item_cache`，沒有的品名才呼叫 `describe_items()`，答案由後端存進 `item_cache`：GPU 模式下問 Qwen；無 GPU 模式下回 `None`，記成待分析（10/16 改寫：快取歸後端，見 overview 第 4 節）
3. 用這個人所有月份的資料重算 18 格，存進 `profiles`
4. 工作改成 `done`

待分析的品名，在 GPU 恢復後重新上傳同一個月份就會補算；GPU 模式下即時分類遇到新品名，會另外排一個背景分析（用 `BackgroundTasks`，不經過上傳的工作執行緒，免得等一整個上傳），同一個品名還在分析時再問不會重複排。服務重啟時，還在跑的工作標成 `failed`，請使用者重傳；每個真實使用者的 profile 也排進同一條背景執行緒重算一次（只讀品項和屬性快取，不問模型；假用戶不能刪月份，所以不算），因為刪月份之後排隊的重算只存在記憶體裡，重啟就不見了（10/16 補上）。

一次只跑一個工作：每個行程有一條專用的工作執行緒，從佇列依上傳順序（先進先出）一個一個跑，不使用回應請求的執行緒池，所以排隊的工作再多，其他 API 照常回應。上傳的請求在 commit 之後只把工作編號放進佇列；等待中的工作只是佇列裡的編號，保持 `queued`，不佔資料庫連線，也不佔執行緒。這條執行緒是 daemon：停止服務時行程不等它跑完，還在跑的工作在下次啟動時標成 `failed`。只跑一個是因為只有一個 llama-server、SQLite 只有一個寫入者，第 3 步重算品味向量也需要不被打斷；因此伺服器只能開一個行程。請求的資料庫連線在路由結束時就關閉，不會陪著背景工作。為了讓工作的時間有上限，請求本體在讀取之前就依 `Content-Length` 檢查大小（超過回 413，沒有長度回 411），一個月最多 2000 筆明細；工作裡任何例外都把工作標成 `failed`，工作已經被刪掉（帳號刪除）時直接結束。

- 替代方案：服務啟動時自動問模型，補算所有待分析的品名。否決，因為重新上傳同一個月份就能做到同樣的事，不必在每次啟動時替所有人排一批會呼叫模型的工作。啟動時的重算和這個方案不同：它只讀已存的品項和屬性快取，不問模型（10/16 補上）
- 替代方案：用 FastAPI 的 `BackgroundTasks` 執行工作，再用一把鎖讓工作一個一個跑。否決，因為等鎖的工作各佔一條回應請求的執行緒（預設共 40 條），排隊的上傳一多，整個 API 就停住；鎖也不保證先上傳的先跑，停止服務時還要等所有排隊的工作。

- 替代方案：Celery + Redis。否決，因為多一個服務要裝，在 Windows 上支援又差。

### D5. Qwen 跑在獨立的 llama.cpp `llama-server`

後端用 HTTP 呼叫 `LLAMA_SERVER_URL`（OpenAI 相容格式），連得上就是 GPU 模式。prompt 以及 `bulk_rule.py`、`sugar_guard.py` 沿用 `experiments/receipt-attributes/`。

模型用同一套評估重新選型，候選是約 5 GB 的模型（例如 Qwen3-8B Q4_K_M）；第一週結束還沒定案，就用已驗證的 Qwen3-4B。

- 替代方案：用 `llama-cpp-python` 把模型載入後端程序。否決，因為在 Windows 上編譯 CUDA 版很麻煩，而且模型和 API 綁在同一個程序，沒有 GPU 的電腦就跑不起來。

### D6. 屬性來源的接法

`src/ml/attributes.describe_items(names)` 回傳 23 個欄位，或 `None`（待分析）。屬性接入以角色 1 的 `attributes.from_model` 為準（10/16 使用者決定；角色 3 分支上的 `attributes.describe(external=...)` 會移除）。品味計算（`signals.gather`／`measure`、`traits.explain`）多一個 `attributes` 參數，內容是 `{品名: 23 個欄位或 None}`；給了就用 `attributes.from_model(row, channel, fields, vocabulary)` 把它換成 `describe` 同樣的 17 個答案，不給就照舊用 `describe`。重算 profile 時屬性只讀 `item_cache`（目前的屬性模型），不問模型，快取裡沒有的品名就是待分析。快取的鍵是屬性模型的版本（`src/ml/attributes.MODEL_VERSION`；fake 模式是 `"fake"`），換版本後舊答案不再使用，在 `fake` 和 `qwen` 之間切換也一樣：服務啟動時的重算會用新的鍵底下（大多是空的）的快取重做真實使用者的 profile，他們的屬性特徵變成待分析，要等有 GPU 時重新上傳才補得回來；假用戶要重跑 seed（10/16 補上）。換算規則（10/15 決定）：

- 店家通路 `channel_of` 照舊用規則，不交給 LLM；7 個基本旗標先不用，類別仍然來自分類模型
- **類別是已知的事實**：問題只在自己的類別門檻內才用模型的值，門檻外一律是 `False`（不適用），模型的 `null` 在門檻內保持 `null`。門檻照舊：`clearance` 只看食物、`quick` 只看正餐、`cooking` 只看生鮮、`kitchen` 只看生鮮和日用品、`sport_gear`／`car_care`／`home`／`stationery` 只看非食物（已確認的類別 4–9）
- `bulk`：數量 ≥ 3 一定是 `True`（數量是發票上的事實，模型看不到），否則用模型的值
- `sugar`：只有飲品有；模型給 `null` 時套用現有的甜度預設規則（見 taste-profile 規格）
- `fun`：`describe_items` 交出中文的 電影、唱歌、展演、遊樂（任務 4.3），照單全收；實驗的英文值 movie、singing、show、game 也接受，換成同一組中文；模型沒給，或給了這八個以外的值，改看店家名稱有沒有娛樂的字（不看品名）
- `species`：只接受 `cat`、`dog`，其他是 `null`
- 待分析的品名（`fields is None`）當成 23 個欄位都是 `null` 的模型答案，套用同一組規則：類別門檻外是 `False`，門檻內是 `null`；數量 ≥ 3 的 `bulk` 是 `True`；飲品的 `sugar` 用預設規則；`fun` 看店家名稱；`species` 是 `null`

**`null` 是沒有資料，不是「沒有」：**
- 計次型的訊號（`kitchen_per_month`、`sport_supplies`、`sport_gear`、`car_care`、`home_items`、`stationery_items`、`alcohol_items`、`pet_food_*`、`pet_supply_*`）只數 `True`；問題適用的品項（類別門檻內的品項，見上面的門檻；其他問題不分類別）至少有一筆、卻沒有任何已知答案時，這個訊號是 `null`，完全沒有適用的品項時是 0（10/16 補上）
- `fun_visits`、`fun_kinds`：判斷過的品名沒有娛樂種類就是「不是娛樂」；全部品項都待分析、而且沒有店家名稱說是娛樂時才是 `null`（10/16 補上）
- 寵物店造訪：發票上沒有已知物種、又有待分析的品項時，不算給貓也不算給狗（不套用各一半）；這個人的寵物店發票全部如此時 `pet_visits_cat`、`pet_visits_dog` 是 `null`。有已知物種時照已知物種算；判斷過但沒寫物種的照舊各算一半（10/16 補上）
- 三個只算已知品項的比例訊號（`clearance_share`、`store_clearance_share`、`weekday_quick_share`），分母只算那個答案已知的品項；`weekday_quick_share` 的分母是至少有一筆 `quick` 已知的正餐的上班日
- `fresh_share`、`bulk_share` 有一部分由規則決定：不是生鮮的食物一定不是下廚用（類別門檻），一次買 3 個以上一定是囤貨。這些答案永遠已知、而且只落在同一邊，已知的答案就不是全部的公平樣本（全部待分析時 `fresh_share` 會是 0、`bulk_share` 會是 1），所以拆成規則的部分和模型回答的部分，只用已知的答案估模型的部分（10/16 補上）：
  - `fresh_share` = 生鮮占食物的比例 × 已知的生鮮裡下廚的比例；有食物但沒有生鮮時是 0
  - `bulk_share` = 一次買 3 個以上的占比，加上其餘日用品裡由已知答案估出的囤貨比例，也就是（一次買 3 個以上的個數 + 其餘的個數 × 其餘已知答案裡囤貨的比例）÷ 全部日用品；沒有其餘的日用品時就是一次買 3 個以上的占比
- 分母裡有未知的答案、而且已知的少於 5 個（`MIN_KNOWN`）時，這個訊號是量不到（`null`），權重交給同一格的其他訊號，免得幾個碰巧已知的答案代表全部。`fresh_share`、`bulk_share` 只看模型回答的部分（生鮮、一次買不到 3 個的日用品）：那部分有未知、而且已知的少於 5 個時是 `null`，規則決定的答案不算在這 5 個裡（10/16 補上）。全部已知時（關鍵字規則一定是）照舊，所以 v1 的結果不變
- 品味格子的最低品項需求（`requires` 的 `food_items`、`store_food_items`、`daily_items`、`meal_items`）照舊數全部品項，不只數屬性已知的

API 路徑只用模型的答案，加上不需要模型的事實和店家規則：`channel_of`、類別門檻、數量 ≥ 3 是囤貨、飲品的甜度預設、店家名稱裡的娛樂字。`describe` 那一整套看品名的關鍵字規則只留給 v1 靜態建置和現有測試（10/16 補上）。

- 替代方案：品名還在待分析時，先用 `describe` 的品名關鍵字規則頂替模型的答案。否決，因為兩種來源混在一起，評估和說明都會變得不清楚；待分析的品名只套用上面那幾條不需要模型的規則。

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

- 權杖用 PyJWT 的 HS256 簽發，`sub` 是 user_id，`key` 是這個帳號的 `token_key`，有效期限 `JWT_EXPIRE_MINUTES`（預設 24 小時）
- 密碼先做 Unicode NFKC 正規化，再用 pwdlib 的 argon2 雜湊；帳號不存在時也驗一次假雜湊，讓錯帳號和錯密碼花的時間相同。登入時的密碼超過 512 字元就直接當作錯誤，不把整串拿去正規化（NFKC 處理很長的文字很慢）
- 密鑰是 `.env` 的 `JWT_SECRET`（至少 32 字元）；git 裡只放 `.env.example`
- 錯誤一律是 `{"detail": "<代碼>"}`，由 `ApiError` 統一產生；422 保留 FastAPI 的格式但不回傳被拒絕的輸入（可能是密碼），程式出錯回 500 `internal_error`，細節只留在伺服器的紀錄
- `DEMO_MODE=1` 時才有 demo 名單和快速切換，而且只能切換成假用戶；`user_id` 只接受 1 到 2^63−1 的 JSON 整數；`DEMO_MODE` 關掉之後，假用戶的權杖立刻失效
- `token_key` 在建立帳號時產生。驗證權杖時，帳號必須存在，權杖裡的 `key` 必須等於帳號現在的 `token_key`。第 1 週就為了一件事用到它：帳號刪除後 SQLite 會把同一個 id 給新帳號，但新帳號的 `token_key` 不同，舊帳號的權杖不會變成新帳號的
- 帳號管理上線時，登出和改密碼都只做一件事：換掉這個帳號的 `token_key`，所以這個帳號所有裝置上的舊權杖都會一起失效。改密碼的回應附上用新 key 簽發的權杖。假用戶例外：它是切換成它的所有人共用的，登出不換 key，只由瀏覽器丟掉自己的權杖，免得一個人登出就把其他人都登出（10/16 補上）

- 替代方案：用 session cookie 或第三方登入。否決，因為前者要另外處理 CSRF，後者要在外部服務設定帳號。
- 登出的替代方案：只讓前端丟掉權杖（舊權杖在 1 天內仍然有效），或另開一張表記錄撤銷的權杖（多一張表，也要定期清理），或權杖帶 `iat`、`users` 加 `tokens_valid_after` 欄位再比較簽發時間（多一個欄位，而且 `iat` 只到秒，同一秒內簽發的新舊權杖分不出來）。都否決，改用 `token_key`：它已經存在，不加表也不加欄位，就能真正從伺服器端登出，代價是會登出所有裝置。

### D8a. 設定項目

名稱和預設值見 overview 5.10：`JWT_SECRET`、`JWT_EXPIRE_MINUTES`、`DEMO_MODE`、`DATABASE_URL`、`LLAMA_SERVER_URL`、`CATEGORY_MODEL`、`ATTRIBUTES_MODEL`、`CATEGORY_MIN_PROB`，以及 10/15 為 Docker 補上的 `CATEGORY_MODEL_DIR`、`CATEGORY_MODEL_REPO`、`CATEGORY_MODEL_REVISION`。由 `src/api/settings.py` 的 `Settings.from_env()` 讀取並檢查：留空等於預設值；密鑰短於 32 字元、數字寫錯或超出範圍、模型名稱不認得時，服務啟動時停下來，用一行訊息指出變數名稱。能啟動的值：`CATEGORY_MODEL` 是 `fake` 或 `bert`（`bert` 還沒接上，模型一律是 `unavailable`），`ATTRIBUTES_MODEL` 是 `fake` 或 `qwen`（`qwen` 要有角色 3 的 `src/ml/attributes.py`，沒有時用一行訊息停下來）；`backends.load_backends` 會擋下其他值（10/16 改寫）。

### D9. 前端

沿用 `src/web/` 現有的頁面和 JS（複製到 `src/web_v2/` 再改），新增一個 API 客戶端模組，把原本讀內嵌資料的地方改成呼叫 API。

- v2 網頁放在 `src/web_v2/`，由同一個 FastAPI 以靜態檔案掛在 `/web/`，和 API 同網域，不用設 CORS；入口是 `src/web_v2/index.html`（第 1 週先放一個預留頁）；不使用打包工具
- `src/web/` 是 v1 報告的建置輸入，凍結：不提供，也不為 v2 修改；角色 4 把需要的頁面和 JS 從 `src/web/` 複製到 `src/web_v2/`（2026-10-15 團隊決定）。v1 的建置和它的 82 個 JS 測試因此不受 v2 影響
- 前端把 API 的錯誤代碼對應成中文
- 根目錄的 `invoice-insights.html` 不動

- 替代方案：把網頁掛在 `/`。否決，因為 POST 到不存在的 `/api` 路徑會被靜態檔案接走，回 405 而不是 404（第 1 週試做時發現的）。
- 替代方案：直接改 `src/web/` 並整個提供。否決，因為它是 v1 報告的建置輸入，要凍結不動。
- 替代方案：用 Streamlit 或 React 重做（規劃會議第 10 題已經否決）。

### D10. 假用戶與假資料

把 `personas.py` 擴充到約 300 人，每種類型 37–38 人，用固定的種子。

- 假品名詞庫、假用戶、假品名的 Qwen 屬性結果都存成 JSONL，放在 `datasets/synthetic/` 並進 git，這樣沒有 GPU 的電腦也有完整的假用戶
- `src/api/seed.py`（第 1 週先放入 40 人，帳號是 `demo_001` 起算、沒有密碼；名單只能往後加，資料庫裡的帳號和名單對不上時停下來，不默默略過）之後擴充成：把假發票寫進 `items`、把屬性結果載入 `item_cache`，再走一般的管線算出品味向量；重複執行不會重複加人

### D11. 測試與 CI

- Python 測試沿用 unittest（`python -m unittest discover -s tests`），JS 測試用 `node --test "tests/*.test.cjs"`
- API 測試用 Starlette 的 TestClient（需要 `httpx2`）加上記憶體 SQLite，模型一律用 `src/ml/fakes.py`（`CATEGORY_MODEL=fake`、`ATTRIBUTES_MODEL=fake`），不需要 GPU
- GitHub Actions 在 push 和 PR 時，用 Python 3.12 和 Node 24 執行全部測試，再執行一次 `docker build`、檢查映像檔裡沒有私人檔案，並用 `docker compose up` 啟動一次，確認健康檢查回報 demo 模式、假用戶名單不是空的（compose 預設是 `fake`，不下載模型）

- 替代方案：改用 pytest。否決，因為現有 77 個測試和第 1 週計畫都是 unittest，不需要多一套工具。

### D12. 隱私的實作方式

- 上傳的檔案寫到暫存檔，處理完就刪除
- log 不出現品名：資料庫錯誤不印參數，背景分析失敗的 log 不帶品名
- 發票號碼沿用現有的 `YYYY-MM-Rnn` 代碼
- 地址沿用 `parse_district`，只留到行政區
- 配對清單的輸出結構裡根本沒有品項欄位；計算過程裡的品名一律經過 `items.label`（去掉地名、住宿與長途交通改成通用名稱、地點相關訊號不列品名），漏網的地名加進 `configs/attributes.json` 的 `place_words`，不在 API 另寫一套規則

### D13. 帳號管理

端點和錯誤代碼見 overview 5.11（`/api/me`、`/api/me/password`、`/api/me/months/{month}`、`/api/auth/logout`）。資料表和欄位都不增加：`users.token_key` 第 1 週就有了，登出和改密碼靠它（見 D8）。

- **刪除帳號**在一個交易裡依序刪除：`items` → `jobs` → `profiles` → `users`，最後刪掉 `item_cache` 裡這個人的品項用過、而且已經沒有任何 `items` 用到的品名（只在即時分類框查過的品名沒有記錄是誰查的，不會被刪）。帳號刪除後，權杖查不到使用者，自然回應 401 `not_authenticated`。這個人還有 `queued` 或 `running` 的工作時回 409 `job_in_progress`，和刪除月份一樣，免得執行中的工作在刪除之後又把品名寫進快取。檢查之前先換掉 `token_key` 並寫進資料庫，取得 SQLite 的寫入鎖，上傳就無法在檢查和刪除之間插進來；回 409 時整個交易撤回，舊權杖照常可用。每條資料庫連線都開著 `secure_delete`，刪掉的資料會在檔案裡被覆寫，不只是標成空位。WAL 檔（`app.db-wal`）裡的舊頁要等被覆寫或 checkpoint 之後才消失（10/16 補上）
- **刪除月份**：先刪除那個月的 `items`（這一步取得 SQLite 的寫入鎖，上傳就無法在檢查和刪除之間插進來），再確認那個月份沒有 `queued` 或 `running` 的工作（有的話整個交易撤回，回 409），然後刪除那個月的 `jobs`，再重算品味向量；快取的清理方式和刪除帳號相同。重算不在請求裡做，而是用 `jobs.Worker.call` 排進上傳任務的同一條背景執行緒，排在已經排隊的上傳後面，所以同一個人的 profile 不會同時被兩個地方寫；重算還在排隊時帳號被刪掉，重算就什麼都不做。刪除規則集中在 `src/api/accounts.py`。重算跑完之前 `/api/me/profile` 的 `recomputing` 是 true；服務在重算跑之前重啟的話，啟動時會再排一次（見 D4）。（10/16 補上）
- **假用戶**（`is_demo`）的修改、刪除和上傳發票一律回 403 `demo_user_read_only`，而且這個檢查要在比對密碼之前；登出照常可用

- 替代方案：資料表加 `deleted_at`，只做「軟刪除」。否決，因為使用者要求刪除時就應該真的刪掉，軟刪除還得另外處理「刪除後的資料不能出現」的所有查詢。

### D14. Docker

- 一個映像檔，以 `python:3.12-slim` 為基底，只裝服務需要的套件：目前只裝 `requirements.txt` 和 `requirements-docker.txt`（`huggingface_hub`）；CPU 版 `torch`、`transformers` 等角色 2 交出 BERT（任務 3.6）時才加（10/16 改寫）
- `docker-compose.yml` 只有一個服務，兩個 volume：一個放 SQLite 資料庫，一個放下載的模型
- 啟動流程：
  1. 讀設定（`JWT_SECRET` 沒設時用資料 volume 裡的 `/data/jwt-secret`，第一次啟動時產生）（10/16 補上）
  2. `CATEGORY_MODEL=bert` 而且 `CATEGORY_MODEL_DIR`（在模型 volume 裡）沒有模型時，用 `huggingface_hub` 下載 `CATEGORY_MODEL_REPO` 在 `CATEGORY_MODEL_REVISION` 的版本（只有容器下載；`start.bat` 和直接跑 `uvicorn` 都不下載）（下載到暫存資料夾，完整之後才改名；失敗時服務照樣啟動，健康檢查顯示 `unavailable`）（10/16 補上）
  3. 資料庫是空的且 `DEMO_MODE=1` 時，執行和 `python -m src.api.seed` 相同的匯入
  4. 用 uvicorn 啟動 `src.api.main:app`
- 容器預設是無 GPU 模式；容器的 `LLAMA_SERVER_URL` 預設是 `http://host.docker.internal:8080`，主機上有開 `llama-server` 時就連得到，要連別的位址設 `DOCKER_LLAMA_SERVER_URL`；compose 會把 `ATTRIBUTES_MODEL` 傳進容器（預設 `fake`，10/16 改寫），預設時這個位址只改變 `gpu_mode`；設成 `qwen` 要等角色 3 的 `src/ml/attributes.py`（任務 4.3）合併，沒有時容器用一行訊息停下來，有了之後容器就透過這個位址向主機的 llama-server 問新品名。不直接用 `.env` 的 `LLAMA_SERVER_URL`：compose 會讀根目錄的 `.env`，而 `start.bat` 建立的 `.env` 寫的是 `http://127.0.0.1:8080`，在容器裡指的是容器自己（10/16 補上）
- `.dockerignore` 排除 `.git/`、`.venv/`、`rawdata/`、`data/`、`models/`、`runtime/`、`experiments/`、`prototypes/`、`*.csv`／`*.tsv`／`*.xls`／`*.xlsx`、壓縮檔（`rar`、`zip`、`7z`）、資料庫檔 `*.db`、任何資料夾裡的 `.env` 和 `.env.*`、`results/`、`outputs/`、`src/web/`、`*-data.js`、`invoice-insights-private.html`、`__pycache__/`；映像檔只 COPY `configs/` 和 `src/`，所以即使 `.dockerignore` 漏了什麼，根目錄的私人檔案也進不去（10/16 補上）
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
- [`build_month` 遇到作廢或小數會報錯] → 第 2 週接上傳之前先修，用虛構的 CSV 寫測試涵蓋作廢、折扣、0 元、小數金額和小數數量（10/15 完成，`for_upload=True`）
- [資料表結構改變，舊的開發資料庫少欄位] → 沒有遷移工具，直接刪掉 `data/app.db*` 重建再 seed；正式資料只有 demo，不會遺失真人資料
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
