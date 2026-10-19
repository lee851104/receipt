# BERT 固定分組切分、多種子配方比較（2026-10-16）

本輪30run全部完成；原test未開啟、未hash、未複製、未評分。沿用既有355筆真實開發資料、5折及各折固定合成子集，初始化seed42/43/44和兩個比例交叉。每個seed各產生355筆OOF，不增加獨立樣本數。

| 配方 | seed42 OOF | seed43 OOF | seed44 OOF | 平均 | 三個seed平均分數的SD | 同fold跨seed SD的平均 |
|---|---:|---:|---:|---:|---:|---:|
| 25% 假資料 | 89.01% | 88.45% | 88.73% | 88.73% | 0.28 pp | 1.54 pp |
| 約 66% 假資料 | 89.30% | 88.45% | 86.76% | 88.17% | 1.29 pp | 2.16 pp |

SD皆為描述性樣本標準差，不是信賴區間。三個seed平均分數的SD反映整體OOF在這3個初始化下的變動；同fold跨seed SD較直接反映固定切分下的初始化變動。不能把同資料的15次fold結果當15個獨立資料集。

## 成對差異

25%相對約66%平均差 +0.56 個百分點；15對中25%勝 7、平 3、負 5。

| Seed | 25%改對／改錯 | 平均差（pp） | 五折差（pp） |
|---|---:|---:|---|
| 42 | 14／15 | -0.28 | +1.41, +1.41, +1.41, -4.23, -1.41 |
| 43 | 20／20 | +0.00 | +0.00, +5.63, +2.82, -7.04, -1.41 |
| 44 | 15／8 | +1.97 | +0.00, +0.00, +5.63, +5.63, -1.41 |

## 每類OOF F1（三個seed各自計算後平均）

| 類別 | 真實獨立筆數 | 25% | 約66% |
|---|---:|---:|---:|
| 正餐 | 125 | 94.07% | 93.99% |
| 飲品 | 60 | 93.33% | 92.10% |
| 零食甜點 | 86 | 91.39% | 91.32% |
| 生鮮食材 | 20 | 62.09% | 63.84% |
| 運動 | 3 | 不計（少於5筆） | 不計（少於5筆） |
| 其他服務 | 14 | 71.56% | 68.69% |
| 交通 | 10 | 73.82% | 76.41% |
| 住宿 | 2 | 不計（少於5筆） | 不計（少於5筆） |
| 日用品 | 27 | 86.71% | 87.36% |
| 電子產品 | 8 | 68.66% | 83.42% |

## 設定與限制

- 公開google-bert/bert-base-chinese固定encoder起點；兩組每折共用相同seed，lr2e-5、batch16、maxlen32、FP32、wd.01、clip1、最多10輪、patience2。內層真實驗證loss選epoch，外折每run只評一次。
- 實際群組盤點355筆／355群／0多筆群。現有group只能保證正規化同名與明確group隔離，沒有消費者／商品家族標記，不能宣稱跨人或語義家族泛化。
- 重用原CV的fold及合成子集，因此此次隔離的是初始化種子變動，不評估換切分或換合成樣本的變動。
- 各組同epoch上限與早停規則，但更新步數與每個真實樣本曝光次數不同；不是等計算量的純比例因果實驗。
- 開發資料已用於配方選擇，且標註時看過模型建議；不是新來源盲測。稀少類別無法由這個樣本數得出穩定保證。
- 不挑最好seed或某一折作新部署模型，現有next25-v3候選保持不變。
- 25% 假資料：實際梯度步數合計2646；訓練內計時合計287.8秒；各seed最佳epoch：42: [7, 5, 7, 5, 6]；43: [5, 9, 8, 4, 10]；44: [9, 5, 6, 6, 9]
- 約 66% 假資料：實際梯度步數合計4186；訓練內計時合計382.4秒；各seed最佳epoch：42: [5, 4, 5, 3, 3]；43: [3, 5, 3, 3, 6]；44: [6, 3, 4, 3, 5]

## 產物與驗證

私人實驗根目錄：C:/Users/User/Desktop/AI_project/receipt/data/role2/bert-multiseed-cv-20261016-v1。protocol.json固定父plan/config；training-execution.json記錄30run與test開啟嘗試；summary.json為彙總。模型與逐筆OOF不得公開。
圖表：同目錄multiseed-comparison.png／.pdf。繪圖只讀summary，不讀逐筆資料。
程式提交6e95c85及b8a6014；獨立複查的epochs上限問題已用11/0/True失敗回歸修正。模型完整回歸94項93pass/1plot skip，獨立plot1pass，主tests154pass。Claude正式審核仍待。
彙總驗證所有30run的plan/config/model/prediction指紋、seed/fold/regime、來源與OOF對齊、各seed355筆完整唯一，從保存預測重算分數一致。沒有重跑挑結果；固定來源與protocol未變。

## 結果解讀與下一步

- 25%平均88.73%，約66%平均88.17%，差距只有0.56百分點。三個完整OOF結果中，一次25%較低、一次相同、一次較高；15對fold/seed結果為7勝3平5負。此次不支持「25%必然更準」或顯著優勝的宣稱。
- 25%的完整OOF跨seed SD為0.28pp，約66%為1.29pp；固定fold內跨seed SD平均1.54pp對2.16pp。可說在本次固定切分與3個seed下，25%波動較小；不能外推成新資料的穩定準確率保證。
- 前次單次5折比較的25%優勢約2.54pp，本次縮小至0.56pp，顯示先前優勢有部分依賴初始化與切分的組合。多seed結果仍傾向保留25%作候選，但平均準確率優勢證據弱。
- 這解釋「CV較穩定但單次validation下降」並不矛盾：單次分數仍受抽樣、初始化與選epoch影響；本輪沒有隔離舊模型warm-start、不同學習率與多seed挑選等因素，因此不能把先前96%降到94%的原因完全歸給假資料比例。
- 生鮮20筆的平均F1為62.09%對63.84%，電子8筆為68.66%對83.42%；總體較佳不代表每類較佳。運動3筆、住宿2筆尤其不足，不能以總正確率取代少數類別驗證。
- 建議下一步先補充並審核弱類別真實開發資料，以及商品家族／來源的group標記；再固定同一驗證流程比較。若要分離假資料比例本身的影響，另行預先固定梯度步數或真實資料曝光預算。這些後續工作本輪未執行。
- 此次沒有可靠的多筆商品家族群：355筆恰好355群。所以雖使用分組切分程式，仍不能作為「近似品項跨折洩漏已排除」的證據。需要新增group資訊才能測到這個問題。

## 本回合實際執行紀錄

以下cwd均為角色2worktree；私人runner只向終端輸出彙總，並攔截任何test.jsonl開啟：

```powershell
# 模型完整測試：94項，93通過、1繪圖環境跳過
& ./experiments/category-models/.venv/Scripts/python.exe -m unittest discover -s experiments/category-models -p "test_*.py"
# 主測試：154項通過
& C:/Users/User/Desktop/AI_project/receipt/.venv/Scripts/python.exe -m unittest discover -s tests
# 繪圖獨立環境：1項通過
& C:/Users/User/Desktop/AI_project/receipt/data/role2/plot-runtime/.venv/Scripts/python.exe -m unittest discover -s experiments/category-models -p "test_plot_reviewed.py"
# 30次CUDA訓練，795.78秒；test存取嘗試0
& ./experiments/category-models/bert-runtime/.venv/Scripts/python.exe -X utf8 C:/Users/User/Desktop/AI_project/receipt/data/role2/run-multiseed-cv-20261016.py train
# 全部30次指紋與重算分數核對通過；test存取嘗試0
& ./experiments/category-models/.venv/Scripts/python.exe -X utf8 C:/Users/User/Desktop/AI_project/receipt/data/role2/run-multiseed-cv-20261016.py summarize
```

訓練程序正常退出；nvidia-smi顯示891MiB／0%（背景占用），本輪GPU工作已結束。未重啟其他服務。圖表已用僅讀summary的腳本產生並檢視；PNG與PDF保存在私人實驗目錄。上述資料、模型、逐筆預測均未進git。
