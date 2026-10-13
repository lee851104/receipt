# 日後接入契約（目前未整合）

## 輸入與輸出
- `prepare(csv_path)` 回傳原始檔 SHA256、逐列資料、待標註項目。`row_id` 必須連同 `source_sha256` 使用，不能當跨 CSV 的全域 ID。
- 標註單位 `(merchant, stripped_name, quantity)`；同名不同店家或不同數量不合併。原始品名與各列金額保留。
- 模型 wire protocol 使用具名 yes/unknown 標籤清單與 sugar/fun/species。`decode_sparse` 依明確契約將未列出的布林欄位解為 false，再經 `decode_prediction` 驗證成完整 16+7 個有名稱欄位的 JSON。unknown 保留 null，與未列出的 false 分開。舊位置陣列測試保留在 results/archive；其結果不作最終模型比較。
- 儲存的屬性欄位與現有 `attributes.describe` 同名：clearance、sugar、quick、cooking、kitchen、sport_supply、sport_gear、car_care、bulk、home、stationery、fun、pet_food、pet_supply、species、alcohol。
- 額外 basic：food、meal、drink、fresh、daily、tech、sport。這些支援未來逐步取代 10 類；尚未涵蓋交通/住宿等所有消費報表分類需求。
- null 與 false 不可混用；模型結果一律 `review_status=unreviewed_model_prediction`。
- `attach(dataset, predictions)` 強制所有 item ID 各出現一次，將預測接回 35 筆資料，保留金額、數量與 csv_line。重跑、換資料必須驗證 source hash。

## 接現有程式時需要另做的事
1. 現有 `invoices.build_month` 用品名查 category catalog；這個實驗沒有替換它，也不產生假裝已確認的正式分類表。
2. 現有 `signals.gather` 呼叫 `attributes.describe` 並根據 category 計算。未來由 adapter 對上 row_id，讀人工確認的屬性；模型缺漏要保留未知。
3. 移除 10 類時，修改 `valid_items` 的確認條件，以及各訊號對 MEAL/DRINK/FRESH/DAILY/TECH/SPORT 的依賴。不能把 basic 布林直接假裝成舊 category。
4. 店家通路 `channel_of` 仍需保留或另外辨識；日期、金額、行政區、休假日由原 CSV 與現有程式處理，模型不推測。
5. 本次為避免無證據猜測，未明示甜度回 null；與現有 sugar_defaults（奶茶/手搖預設甜度）不同。這是實驗政策，正式接入須明確決定，不可靜默改變。
6. 實驗 fun enum movie/singing/show/game 需轉為現有 電影/唱歌/展演/遊樂。
7. 以相同發票檢查明細數、發票數、總金額、訊號及向量；之後才能修改分析介面。本次不證明配對效果。

## 本輪已備妥的交接成果

`SELECTED_MODEL.json` 固定 Qwen3 4B 的模型 revision、SHA、推論設定與兩個規則的 SHA。`results/followup/selected-output.json` 封裝來源 SHA、35 筆明細、規則改動及 REQUIRES_HUMAN_REVIEW 狀態；各列仍保留原有未複核標記。已驗證逐列原始欄位與金額不變。

採離線批次產生、人工複核後讀檔的接法；本機 28 組資料推論約 10.8 分鐘。16 屬性修正後成績只是事後開發回測，7 個 basic 旗標 F1 85.39% 且生鮮不足；必須先有人工確認的獨立資料，才可評估自動接入。不能只因輸出格式相容，就視為整條流水線已驗證。

## 評估語意
`draft-reference.json` 是助理初稿，不是使用者核准答案。`evaluation.json` 只代表和初稿的一致程度，逐欄列出 positive precision/recall、未知保留與差異。
大量 false 會使整體一致率看起來很高，所以不能單靠總一致率選模型。沒有正例的屬性標成未覆蓋；需追加其他月份或獨立測試資料。
