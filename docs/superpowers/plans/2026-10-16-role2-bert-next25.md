# 角色2：25%合成配方下一版BERT
基準813aa2e；使用者授權訓練、封存原test、commit及Claude交接。

固定方案：保留來源train／validation邊界，305real＋102synthetic（round(real/3)，25.06%），validation50；synthetic以既有synthetic_order(seed1042)均衡各類取樣。從公開encoder初始化、seed42、lr2e-5、batch16、FP32、max_length32、最多10epoch、patience2/min_delta1e-4、weight_decay.01、clip1，只按validation loss選epoch。原test不開啟、不複製、不hash或評分。

新development-only loader綁定CV plan／summary與原source train／validation指紋，只讀兩個part；新的版本不建立test.jsonl。既有training run新增development_only選項，拒絕warm-start與分類checkpoint，其他模式維持原行為。權重保存在主目錄data/role2/runs新版本，重載完整機率一致與CPU推論介面驗證。

- [x] 虛構測試先失敗：不開test、比例、保持partition、CV來源／summary損壞拒絕、訓練重載與禁止warmstart。
- [x] 實作、完整回歸、階段commit。
- [ ] 確認GPU資源、真模型訓練及重載。
- [ ] 獨立複查、彙總文件、隱私稽核、結果commit與交接。

限制：validation已參與配方選擇，分數只為開發診斷；不能稱全新盲測或保證超過舊test82%。本輪不部署、不接管角色1 API，不公開私人權重。預覽8001不動。所有真實名稱僅本機處理，輸出彙總。

### 執行紀錄
- 新測試先因缺少模組失敗；新增比例描述檢查先失敗後修正。4項虛構測試通過，實際防止開啟test.jsonl。
- CPU實驗完整回歸89項，88通過／1繪圖環境跳過；獨立Codex複查另跑4/4通過，無阻擋缺陷。正式Claude審核仍待。
- 本機資料bert-next25-data-20261016-v1已建立：train407（305real＋102synthetic）、validation50；只含train／validation與manifest，保留來源分界。
- 複查建議訓練前核對CV encoder／training-config，採執行前後彙總核對，保留證據。未更改來源測試集。
