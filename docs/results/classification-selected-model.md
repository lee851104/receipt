# 目前選用的 BERT 方案

選用日期：2026-10-16。使用者確認先採用目前證據較支持的25%假資料方案。

- 配方：305筆已確認真實訓練資料＋102筆合成資料，合成占25.06%；維持原50筆validation與封存test的界線。
- 指定完整run：`C:/Users/User/Desktop/AI_project/receipt/data/role2/runs/bert-next25-20261016-v3`。
- 指定模型目錄：上述run的`model`；載入時須保留classifier-manifest、config、權重與tokenizer檔案。
- 使用既有事先固定seed42的完整模型，不以CV最佳seed或某一折模型替代，不重跑挑選。
- 選擇依據：固定5折×3seed比較，25%平均OOF88.73%、跨seed SD0.28pp；約66%平均88.17%、SD1.29pp。25%本輪波動較小，平均差0.56pp，不保證每次更準。
- 88.73%是配方的開發資料CV結果；此模型原validation47/50=94%，均不能宣稱獨立測試準確率。原test繼續封存。
- 現有group皆單例，沒有商品家族／消費者泛化證據；少數類別仍不足。
- 狀態：方案已由使用者選定；Claude正式審核待進行；應用程式整合／發布尚未完成。本紀錄不代表已切換任何執行中的服務。

證據：[多種子比較](classification-multiseed-cv.md)、[候選模型訓練與重載驗證](classification-bert-next25.md)。

整合交接：角色1／相關展示負責者使用以上完整模型目錄作為選定版本，依既有載入契約驗證；不使用任一CV折權重或舊高合成比例版本。角色2保留資料／模型與結果證據，依Claude具體審核回饋處理。
