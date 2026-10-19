# 全真實與25%合成 BERT 固定版本比較

2026-10-17 Asia/Taipei。本次實際重新訓練一個全真實對照版，與既有完整 `bert-next25-20261016-v3` 比較。實驗已驗證，待 Claude 審核；沒有切換HF模型或整合主產品。

**本次50筆真實保留集，全真實版43/50＝86%，25%合成版42/50＝84%。全真實多對1筆，尚不足以判定穩定優劣。**

## 設計與資料界線

使用者本輪明確要求在同一份未參與訓練的真實資料上比較，因而本次啟用先前暫時封存的50筆保留集做一次評估。它曾被舊模型評估，標註流程也曾展示模型建議，**不是全新盲測**。本次沒有依它選種子、調參、重新訓練或修改標籤。

現有舊完整BERT使用約66%合成資料，不能當成全真實對照。新對照從與25%版本相同的公開 `google-bert/bert-base-chinese` 起點訓練，沒有從已混合訓練的分類器接續。

| 項目 | 全真實對照 | 25%合成版本 |
|---|---:|---:|
| 真實訓練資料 | 同一305筆 | 同一305筆 |
| 合成訓練資料 | 0 | 102（占25.06%） |
| 選擇權重的validation | 同一50筆真實資料 | 同一50筆真實資料 |
| 本次評估 | 同一50筆真實保留集 | 同一50筆真實保留集 |
| 固定seed | 42 | 42 |
| 保存epoch | 10 | 5 |
| 執行epoch／更新步數 | 10／200 | 7／182 |

兩版同FP32、max_length32、batch16、AdamW lr2e-5、weight_decay0.01、gradient_clip1、最多10輪、patience2、min_delta1e-4，以validation cross-entropy選權重。全真實版在既定10輪上限結束，沒有因結果較低再增加輪數。資料量及早停不同，**不是等計算量實驗，也不能將差異單獨歸因於資料真假**。

開發資料、模型、訓練報告、runner、支援程式hash與套件版本寫入protocol。訓練階段test開啟0次；兩模型固定後才讀指定test一次。ID、NFKC名稱及既有group對兩版train（含合成資料）與validation的交集檢查通過，50筆全部為human_confirmed real。未人工重審商品家族／語義近似或跨來源獨立性。

## 結果

| 指標 | 全真實 | 25%合成 |
|---|---:|---:|
| 正確筆數 | 43/50 | 42/50 |
| Accuracy | 86.00% | 84.00% |
| Macro-F1（僅支援數≥5的3類） | 86.94% | 86.70% |

上述Macro-F1只平均正餐、飲品、零食甜點，不是10類平均。整體Accuracy含全部50筆。

| 真實類別 | 筆數 | 全真實答對 | 25%合成答對 |
|---|---:|---:|---:|
| 正餐 | 19 | 18 | 19 |
| 飲品 | 8 | 7 | 7 |
| 零食甜點 | 13 | 11 | 10 |
| 生鮮食材 | 3 | 1 | 0 |
| 運動 | 0 | — | — |
| 其他服務 | 1 | 1 | 1 |
| 交通 | 1 | 1 | 1 |
| 住宿 | 0 | — | — |
| 日用品 | 4 | 3 | 4 |
| 電子產品 | 1 | 1 | 0 |

少於5筆的類別僅展示答對數，不計正式類別F1；零樣本不代表零準確率。不能據1–4筆推論類別能力。

成對結果：39筆皆對、4筆皆錯、4筆只有全真實對、3筆只有25%合成對。25%相對全真實差−2個百分點。Exact McNemar雙尾p＝1.0；沒有支持穩定優勢的證據，也不能解讀為兩版等效。單一seed與小樣本限制仍在。既有開發CV可能得到不同排序，不能與本次50筆合併成更多獨立樣本。

## 驗證與重現

實驗工具沿用角色2 `76263e69cd0f3956c7ce06a128914159a74041a7`。runner只在自身程序內替換資料loader以傳入305筆real，沒有修改原資料、共用訓練程式、共享環境或產品程式。

在主目錄，以既有 `C:/Users/User/.codex/worktrees/receipt-role2/receipt/experiments/category-models/bert-runtime/.venv/Scripts/python.exe -X utf8` 執行：

1. `data/role2/compare-real25-20261017.py selftest`：exit0，ID／名稱／group三個洩漏案例、兩個成對計分案例、real-only loader305筆；test開啟0。
2. 同runner `train`：exit0，10輪、保存epoch10、訓練31.83秒、CPU重載驗證通過；test開啟0。獨立CUDA環境torch2.8.0+cu128、transformers4.57.1。
3. 同runner `evaluate`：exit0，test實際開啟1、其他test拒絕0；50筆通過來源及交集檢查、兩版CPU推論。排他建立evaluation-started紀錄，防止同目錄重評。
4. `data/role2/verify-real25-20261017.py`：exit0，sklearn獨立重算Accuracy／混淆矩陣／F1與SciPy二項精確檢定全部一致；ID與答案順序一致50筆，沒有重開test。
5. 內部獨立Codex靜態審查沒有阻擋問題；建議補程式／套件指紋已在訓練前加入。不是Claude正式審核。未執行全產品回歸，因產品未修改。

run與本機證據：`C:/Users/User/Desktop/AI_project/receipt/data/role2/real25-holdout-20261017-v1/`。包含protocol、training-complete、evaluation-started、summary、independent-metrics-check；逐筆預測只保存在Git忽略的本機資料夾且不含品名，不公開逐筆ID。訓練報告的validation結果不能當本次test結果。

runner SHA256：`88f87b771da98c0a7d6c3c0225d3b7f849b73fab3745d57a36f7d91ee2b91fb5`。原25%權重SHA256仍為 `16997425a9b36629469d60f506d52c2771bab1e6f3a3ea1465c2c0a316fa3e79`。全真實模型在該run的`real-only/model`，hash記錄在summary及evaluation-started。

GPU結束637MiB／0%，訓練程序已退出；沒有啟停其他角色服務。HF維持原模型。後續若要決定長期取代，需另外收集未參與任何訓練／配方選擇的真實資料，補足稀少類別再預先固定評估；本次不自動開啟新一輪調參。
