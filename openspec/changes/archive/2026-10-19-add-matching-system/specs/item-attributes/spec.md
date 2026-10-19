# Spec Delta

## Purpose

用本機的大型語言模型判斷每個品名的屬性（例如含不含酒精、甜度、是不是寵物用品），提供給品味向量計算，取代原本的關鍵字規則。

## ADDED Requirements

### Requirement: 固定的屬性欄位
系統 SHALL 為每個品名回傳固定的 16 個屬性（clearance、sugar、quick、cooking、kitchen、sport_supply、sport_gear、car_care、bulk、home、stationery、fun、pet_food、pet_supply、species、alcohol）和 7 個基本旗標（food、meal、drink、fresh、daily、tech、sport），每個欄位都要出現。

#### Scenario: 欄位完整
- **WHEN** 系統完成一個品名的屬性判斷
- **THEN** 結果剛好包含這 23 個欄位，沒有缺少也沒有多出

### Requirement: 不知道與否定要分開
模型無法判斷的欄位 SHALL 是 `null`，MUST NOT 被當成 `false`。品味向量計算時，`null` 欄位 SHALL 視為沒有資料，而不是「沒有這個屬性」（比例怎麼只算已知的，見 taste-profile 規格「未知的屬性不當成『沒有』」）。類別已經說明問題不適用時（例如非生鮮品項的 `cooking`），後端不看模型的答案，直接當成已知的「沒有」。

#### Scenario: 甜度不明
- **WHEN** 品名沒有提到甜度，模型也判斷不出來
- **THEN** `sugar` 是 `null`，不是 `0` 或 `false`

#### Scenario: 類別說不適用的問題
- **WHEN** 一個正餐品項，模型把它的 `cooking` 答成 `null`
- **THEN** 屬性 API 照樣顯示 `null`，但計算生鮮占比時，它的 `cooking` 是已知的「沒有」（`false`），因為 `cooking` 只問生鮮

### Requirement: 屬性結果快取
同一個品名判斷過一次後，系統 SHALL 把結果存進快取，之後直接沿用，不再呼叫模型。快取 MUST 記錄是哪一個模型版本產生的。

#### Scenario: 第二次遇到同一個品名
- **WHEN** 一個已經判斷過的品名又出現在新的上傳裡
- **THEN** 系統直接使用快取結果，結果和第一次相同，也沒有呼叫模型

### Requirement: 屬性判斷在背景進行
即時分類 MUST NOT 因為等待大型語言模型而卡住：它只查屬性快取（`describe_items(names, ask_model=False)`），快取裡沒有的品名，回應立刻帶回類別，`attributes` 為 `null`，`attributes_status` 為 `pending`（待分析）。GPU 模式下，系統 SHALL 同時把這個品名排進背景分析，完成後寫入快取。

#### Scenario: GPU 模式下即時分類遇到新品名
- **WHEN** GPU 模式下，使用者即時分類一個從沒見過的品名
- **THEN** 回應立刻帶回類別，`attributes` 為 `null`，`attributes_status` 為 `pending`；背景分析完成後再查詢，變成 `ready`

#### Scenario: 快取裡有的品名
- **WHEN** 使用者即時分類一個快取裡已經有屬性的品名
- **THEN** 回應的 `attributes` 有完整的 23 個欄位，`attributes_status` 為 `ready`，沒有呼叫模型

### Requirement: 模型不在時的待分析狀態
大型語言模型無法使用時（例如電腦沒有顯示卡），系統 SHALL 照常完成上傳：快取裡有的品名使用快取，其他品名標示待分析，並算進處理進度的「已處理」數量和使用者的待分析品名數。模型恢復可用後，使用者重新上傳同一個月份，SHALL 補算這些待分析的品名。

#### Scenario: 無 GPU 模式上傳
- **WHEN** 模型無法使用時，上傳一份含有 3 個新品名的 CSV
- **THEN** 工作照常完成，這 3 個品名是待分析，其餘品名使用快取結果，「我的品味」顯示有 3 個待分析品名

#### Scenario: 模型恢復後重新上傳
- **WHEN** GPU 模式恢復後，使用者重新上傳同一個月份
- **THEN** 原本待分析的品名都被判斷完成，品味向量也重新計算

### Requirement: 屬性函式的回傳格式
屬性函式 `describe_items(names, ask_model=True)` SHALL 依輸入的順序，為每個品名回傳 `None`（還沒分析過）或剛好 23 個欄位的字典，值只用一般的 Python 型別（`None`、`bool`、`int`、`float`、`str`）。`ask_model=False` 時 MUST 只查快取、不呼叫模型，回傳的格式不變。專案 SHALL 提供 `tests/model_contract.py` 的 `check_describe`，讓假替身和每一個真的實作用同一套檢查驗證這個格式。

#### Scenario: 只查快取
- **WHEN** 用 `ask_model=False` 呼叫 `describe_items`，其中一個品名不在快取裡
- **THEN** 那個品名的結果是 `None`，模型沒有被呼叫，其他品名照常回傳

### Requirement: 屬性判斷只在本機執行
系統 MUST NOT 把品名送到任何外部服務來判斷屬性。

#### Scenario: 離線判斷
- **WHEN** 電腦沒有網路連線，但本機模型可用
- **THEN** 屬性判斷照常完成
