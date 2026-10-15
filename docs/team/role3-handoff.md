# 角色 3 交接（2026-10-15）

工作區：`C:\Users\User\.codex\worktrees\receipt-role3\receipt`；分支 `codex/role-3/attributes`，基底 `cfbdd35`。主資料夾程式未改動；只共用其 Python 與 CUDA runtime，私人複核資料依團隊規則留在主資料夾 `data/private/`。

## 已交付

- CPU/CUDA smoke、4B 與 8B 的 54 筆同套合成評估與第二次重現，見 `docs/results/attributes-model-selection.md`。維持 4B；100 筆人工複核未完成，不能當正式準確率。
- `src/ml/attributes.py`：`describe_items(names, ask_model=True)`，23 欄、保留 null、fun 中文化、凍結 bulk/sugar 規則；timeout=60 秒、推論鎖、失敗回 None；cache-only 不等待推論鎖。固定本機 HTTP，略過代理且不跟隨重新導向。
- 名稱快取以 `(model_version, name)` 為鍵；可注入 mapping，預設是程序內快取。持久化的 `item_cache` 與清理仍由角色 1 的資料庫管線負責。不要把程序內快取當作資料庫已完成。
- 核心 `describe(..., external=...)`：省略時維持 v1 關鍵字；明傳 None 表示 pending。API 管線要在每列放 `attributes`（字典或 None），交給現有 signals/traits；不放這個欄位就會走 v1。
- 甜度只在計算副本補位；未知旗標不當 false；通路仍依店家規則。數量 >=3 的 bulk 補位在品項列計算，不污染同品名快取。
- `build_personas(calendar, total=300)` 保留原始 40 人前綴後追加；v1 不傳 total 時仍 40 人。seed CLI 改用 300，重跑不重複新增，8 類為 37/38 人。
- `datasets/synthetic/attribute-cache.jsonl` 是 107 個純假品名的實際 Qwen 結果，帶 source、model_version、未複核標記。不能混入真人資料。
- 核心配對驗證見 `docs/results/matching.md`；不需要 GPU。使用既定假類別與 Qwen 快取，沒有冒充完整分類/API/資料庫管線。

## 角色 1 接入

2.15：以 `AttributeDescriber(server_url=settings.llama_server_url)` 作為 backends.describe_items；設定 `ATTRIBUTES_MODEL=qwen` 的啟用仍由角色 1 修改 `src/api/backends.py`。本分支沒有改目前 fake 啟動設定。

2.3/2.4 完成資料表與重算管線後，再完成 4.7：將假發票寫入 items、上述快取匯入 item_cache、走一般管線計算 profiles。現階段資料庫只有 users，4.7 保留未勾選。先以新資料庫驗證，不要刪除其他角色的資料庫。

本介面只有 names，所以模型輸入 merchant 為空、quantity 為 1。不能把某張發票的店家或數量混進同品名快取。Qwen server 應載入已選定的 4B；換模型、prompt 或 guards 時，建立新 model_version 並清理舊版本程序快取。

## 人工複核

主資料夾 `data/private/attribute-review-20261015/` 有 4 份各 25 筆 JSONL，以及獨立的模型預測；由 187 個有效真實品名固定種子抽出 100 筆。請 4 位組員先各自盲標，再比較模型，確認後才改為 human_confirmed。所有品名與逐筆答案只留本機，不進 git、不上傳雲端 AI。

待 100 筆真的人工確認後，才能產出 23 欄 precision、recall、F1、null 比例；所有 gold=null 的欄位不計 F1。未產出 `docs/results/attributes.md`，避免把未審核預測寫成正式成績。4.8 保留未勾選。

## 審查與驗證

獨立審查發現 ready_meal_share 的已知/未知分母不一致；已新增失敗測試並修正，待分析正餐不再讓比例超過 1。審查未判定 GPU 品質與真人資料表現；本次另有本機合成實測，真人成效仍待複核。

取捨：保留 v1 預設 40 人、v2 顯式要求 300；如果後續呼叫端忘記 total=300 仍會得到 40 人。程序快取與持久化清楚分開；角色 1 接入前，重啟程序會失去程序快取。

驗證指令：共用 Python 執行 `-m unittest discover -s tests`；`node --test "tests/*.test.cjs"`；`python -m scripts.evaluate_matching`；`openspec validate add-matching-system --strict`。

最後驗證：Python 173/173、JavaScript 82/82、OpenSpec strict 與 git diff --check 通過。角色 3 完成 7/9；整體 11/53。剩下 4.7 完整 seed 管線、4.8 人工複核。
