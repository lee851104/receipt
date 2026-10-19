# 25%合成資料下一版BERT（2026-10-16）

已完成固定配方訓練與重載驗證，尚未部署；Claude正式審核待進行。程式基準63db6b0（準備工具a871176）。原test完全未開啟、未hash、未複製、未評分。

## 資料與選擇規則

- 保留bert-continuation-20261016-v1原真實train／validation分界：train305真實＋102合成＝407，合成占25.0614%；validation50筆真實。
- 合成由原600候選以synthetic_order(seed1042)均衡取樣，數量round(305/3)。不新增假品名；未確認／無法辨識資料未加入。
- 同交叉驗證公開google-bert/bert-base-chinese encoder，revision 8f23c25b06e129b6c986331a13d8d025a92cf0ea；重新初始化分類head。固定seed42、lr2e-5、batch16、max_length32、FP32、weight_decay.01、clip1、最多10輪、patience2、min_delta1e-4。
- 按validation loss選epoch，第7輪早停，保存第5輪。執行前後核對CV encoder與training-config完全一致；沒有選多個seed。
- validation先前已參與配方CV，因此本輪分數是開發診斷，不是新的獨立泛化證據；運動／住宿各0筆，不能推論這兩類表現。

| 指標 | 本次結果 |
|---|---:|
| Validation accuracy | 94%（47/50） |
| 最佳validation loss | 0.2614683621 |
| 保存epoch／停止epoch | 5／7 |
| 原test評估 | 未執行 |
| test.jsonl開啟嘗試 | 0 |
| CPU重載validation分類一致 | 50/50 |
| CPU重載train probe分類一致 | 10/10 |

上版validation96%（48/50），本次少答對1筆；不能稱本次驗證正確率提升。先前25%配方的5折平均89.58%、SD1.26pp，是配方比較依據，不是本次新模型的測試分數。不要用本輪94%與舊test82%比較。也不能因降低合成比例就宣稱解決過擬合。

本次3個validation錯誤全來自生鮮食材（3筆）：2筆預測正餐、1筆預測飲品。其他有樣本類別均答對，但多類僅1–4筆，證據不足。Macro-F1僅涵蓋至少5筆的正餐／飲品／零食甜點三類，96.37%，不得當作10類平均。

| Epoch | Train loss | Validation loss |
|---|---:|---:|
| 1 | 1.893631 | 1.223416 |
| 2 | 1.152778 | 0.676582 |
| 3 | 0.694403 | 0.419369 |
| 4 | 0.409586 | 0.338441 |
| 5 | 0.236343 | 0.261468 |
| 6 | 0.134917 | 0.369041 |
| 7 | 0.072638 | 0.333106 |

## 收尾失敗與修正證據

v1訓練完成但重載驗證失敗；v2同seed／同設定加診斷，確認舊通用rtol1e-7／atol1e-9拒絕FP32的2.3283064365386963e-09微小差異。修正只影響BERT重載比較：rtol1e-6／atol1e-8，仍驗證10類機率合法、分類完全一致，記錄最大差值；TF-IDF／Embedding標準不變。

v3使用相同資料、種子、訓練參數完成收尾。三個版本每輪loss相同，最終model.safetensors SHA256完全相同；不是改參數重跑挑分數。v3每次保存（epoch1–5）逐tensor與記憶體權重完全相等。validation50最大機率差2.3283e-09、train probe10最大差0。v1/v2失敗目錄保留，不作可交付完整run。

訓練內計時26.54秒（含保存／核對）、CPU1000筆循環train名稱推論27.31秒；GPU峰值allocated約2.13GB。這不是實際服務延遲測試。程序已結束，GPU回到背景使用，未停止其他角色服務。

## 本機產物與驗證

- 資料：C:/Users/User/Desktop/AI_project/receipt/data/role2/bert-next25-data-20261016-v1
- 完整run：C:/Users/User/Desktop/AI_project/receipt/data/role2/runs/bert-next25-20261016-v3
- 模型：上述run/model；report.json及execution-evidence.json含彙總／指紋；validation-predictions.jsonl含私人品名，只留本機。
- 本機啟動證據：data/role2/run-next25-verified-20261016.py及bert-next25-preflight-20261016-v3.json；audit hook全程拒絕開啟test.jsonl。
- 所有資料、權重、私人預測均確認受Git忽略；公開提交只有程式、虛構測試、彙總文件。
- 實驗CPU測試90項：89通過／1繪圖環境跳過；獨立plot環境補跑1/1通過；主tests154/154通過。
- 內部Codex獨立複查：資料／隔離4/4、BERT6/6通過，無阻擋缺陷。這不等於Claude正式通過。
- 本回合先遇沙箱繪圖暫存權限失敗及主測試停滯，改正常本機權限後通過；未變更共用套件。

後續先由Claude審查程式、證據與候選模型。若要再改善，優先補生鮮食材、運動、住宿等真實標註，另收集來源獨立的評估資料；本輪維持封存既有test，不以新結果再調參。
