# 角色 2：已確認資料續訓 BERT（2026-10-16）

使用者要求以已確認名單繼續微調、保留獨立測試集、階段 commit。本輪沿用已授權的本機訓練與角色 2 worktree，不調整其他角色檔案、不上傳私人名稱、不部署。

## 固定實驗設計

- 真實來源為使用者確認的 366 筆；原審核池其餘 12 筆排除，若與舊訓練重疊亦不作 replay。
- 從舊 train/validation/test 全部未見的品名／明確群組中，按類別與群組 seed42 分層 70/15/15；不足三個群組的類別僅入 train。新 test 不供梯度、早停、選種子或選超參數。
- 舊訓練資料作 replay（已確認真實資料與原合成資料），舊 holdout 不移入新 train；所有新 holdout 不得與舊已暴露品名重疊。
- 續訓從既有 BERT seed42 完整分類權重開始，保留分類 head。三個續訓 seed42/43/44；AdamW lr1e-5、batch16、FP32、max_length32、epochs最多10、patience2、min_delta1e-4、weight_decay .01。不做超參數搜尋。
- 將原模型作 epoch0 候選，最低 validation loss 保存；選種子只看 validation loss，平手較小 seed。最後凍結舊模型與選定新模型，在相同新 test 各評估一次，exclusive claim 防誤重跑。
- 重要限制：這 366 筆已在前一輪比較過模型，而且審核看過模型建議。新 test 是本輪訓練隔離的固定保留集，不是全新盲測或來源獨立性的證明。名稱／既有群組去重未保證語義近似完全排除。

## 執行清單

- [x] 虛構測試：舊暴露名稱不能入新 holdout、未確認排除、組別隔離、指紋損壞拒絕。
- [x] 新版續訓切分與本機 check；保存版本、指紋、曝光排除數。
- [x] BERT warm-start 與 epoch0 候選測試；訓練不預測 test。
- [x] 三種子續訓與模型重載檢查，只看 validation。
- [x] 凍結候選、一次性 test 比較與圖表；結果不回饋本輪調參。
- [x] 公開程式審查、完整測試、彙總報告、階段 commit。

## 執行紀錄

- 已建立 `data/role2/bert-continuation-20261016-v1`：366 筆人工確認中，4 筆與舊資料曝光重疊，362 筆新資料分為 train262／validation50／test50。12 筆未確認不納入；未發現未確認項目需從舊 replay 移除。
- 合併 replay 後 train905＝305 real＋600 synthetic，validation/test 各50 real。測試集運動、住宿沒有樣本；只有正餐、飲品、零食甜點各至少5筆。
- 已完成三種子 GPU 續訓。seed42/43 最低驗證 loss 仍是 epoch0 的 0.3118474769（47/50）；seed44 在 epoch1 降到0.2173331145（48/50），依事前規則選 seed44 epoch1。後續輪次 loss 反升即早停，沒有因 test 調參。
- peak GPU 約2GiB；三次訓練迴圈約10.9／10.3／16.9秒（另有重載及CPU完整流程1000筆測速各約22秒）。所有模型重載完整機率一致。
- 全變更獨立程式審查指出舊 split 遺失原始群組名稱可能漏判曝光，以及報告寫死類別與每筆百分點。先寫失敗回歸再修正：必須核對舊人工來源 SHA256，非 name 原始群組需映射否則拒絕；新未知群組亦拒絕；報告改動態計算。
- 本機只印彙總的來源稽核確認舊資料檔符合 parent manifest 指紋，舊與新皆沒有非 name 顯式群組。`group-audit.json` 已保存並綁入最終評估 plan，因此本輪已完成切分及權重不受此修正影響。仍不保證未標記語義近似名稱的完全隔離。
- 虛構端到端測試證明：暖啟動保留分類 head、epoch0可還原、test 不送入梯度或訓練期預測、最後僅比較 parent 與 validation 贏家，改輸出路徑不能繞過資料夾上的單次 test claim。
- 已完成審查修正的聚焦複查，無新增重要缺陷。使用者已授權本輪工作，不需要外部人工程式審查批准；只在本機保留模型與私人輸出。

- 2026-10-16 最終評估已完成，test50：原模型40/50（80%），seed44 epoch1為41/50（82%）。改善3、退步2、兩者皆對38、兩者皆錯7。Macro-F1（有樣本8類）68.60%→71.03%；只計每類至少5筆的3類則82.14%→83.86%。未依test再訓練或挑選候選。
- 最終 `report.json`、`comparison.md`（兩張數值混淆矩陣）、凍結 `evaluation-plan.json` 與私人逐筆預測皆保存在主目錄 `data/role2/runs/bert-continuation-comparison-20261016-v1`；測試claim保留。50筆每一筆影響2個百分點，不宣稱統計顯著或穩定提升。
- 完整分類實驗單元測試：81項，80通過、1項因CPU模型環境沒有Matplotlib而skip，35.046秒。真實模型評估成功，所有指紋前後核對一致。最後GPU為731MiB／0%，本次訓練程序已釋放。
- 階段提交 `ece24da` 已保存程式與測試；後續文件提交記錄結果。新建立的共用AGENTS.md／CLAUDE.md不納入角色2提交。交接狀態為待Claude審核、未整合，內部程式複查不等於Claude通過。- 補充驗證：獨立 plot-runtime 執行 `-m unittest discover -s experiments/category-models -p test_plot_reviewed.py`，1/1通過（3.192秒），因此分類實驗81項已分環境全部覆蓋；主專案Python執行 `-m unittest discover -s tests`，154/154通過（9.100秒）。
- 續訓資料check通過；audit_synthetic.py 對兩份人工標註共419個去重名稱比對，600筆合成名稱精確撞名0，README與本計畫公開文字命中0。稽核只輸出彙總。
