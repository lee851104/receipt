# Spec Delta

## Purpose

把一個人上傳的所有品項，整理成 18 格品味向量和月報。品味向量是配對的唯一依據，也是使用者看懂自己消費習慣的入口。

## ADDED Requirements

### Requirement: 18 格品味向量
系統 SHALL 為每位使用者算出固定順序的 18 格品味向量。10 格雙向格（spend、meals、motive、cooking、sweet、routine、travel、stock、days、holiday）的範圍是 −1 到 +1；8 格程度格（sport、driving、lifestyle、tech、fun、pets_cat、pets_dog、alcohol）的範圍是 0 到 1。

#### Scenario: 數值範圍
- **WHEN** 系統為一位品項足夠的使用者算出品味向量
- **THEN** 每一格不是 `null`，就是落在該格規定的範圍內

### Requirement: 資料不足時不硬算
某一格需要的資料不夠時，那一格 SHALL 是 `null`。使用者的有效品項（已略過的明細和類別 10 待確認的品項都不算）少於 20 個時，系統 SHALL 把這個人標示為資料不足，18 格全部是 `null`。

#### Scenario: 品項太少
- **WHEN** 使用者總共只有 12 個有效品項
- **THEN** 這個人被標示為資料不足，18 格都是 `null`，也不會出現在任何人的配對清單裡

#### Scenario: 單格資料不足
- **WHEN** 使用者的品項總數足夠，但其中一格需要的品項數不到 `configs/traits.json` 為那一格設定的最低需求
- **THEN** 那一格是 `null`，其他格照常有數值

### Requirement: 合併所有已上傳月份
品味向量 SHALL 使用這位使用者所有已上傳月份的品項一起計算。

#### Scenario: 兩個月的資料
- **WHEN** 使用者上傳了 7 月和 8 月
- **THEN** 品味向量同時反映 7 月和 8 月的品項

### Requirement: 查詢我的品味向量與月報
系統 SHALL 讓已登入使用者取得：資料是否足夠、有效品項數和門檻、待分析品名數、常去行政區（最多 2 個）、固定 18 筆的品味格（每筆有 id、名稱、種類和數值），以及沿用現有月報格式的每月消費分析。還沒上傳過任何資料時，系統 SHALL 回應 200 並標示資料不足，而不是錯誤。

#### Scenario: 已上傳
- **WHEN** 已上傳兩個月、有效品項足夠的使用者查詢自己的品味
- **THEN** 回應的 `ready` 為 true，`traits` 有 18 筆，`months` 有兩個月份

#### Scenario: 還沒上傳
- **WHEN** 新註冊的使用者查詢自己的品味
- **THEN** 系統回應 200，`ready` 為 false，18 筆 `traits` 的數值都是 `null`，`months` 是空的

### Requirement: 飲品甜度的預設值
計算 sweet 格時，若飲品的 sugar 是 `null`（模型判斷過但沒寫甜度，或品名還在待分析），系統 SHALL 套用現有的甜度預設規則（例如名稱含「奶茶」視為全糖、含「美式」視為無糖、手搖飲店家的飲品視為全糖）；套用後仍無法判斷的，才當成沒有資料。屬性 API 回傳的 MUST 仍是模型的原始結果。（10/16 決定：待分析的飲品也套用預設規則，因為規則只看品名和店家，不需要模型的答案）

#### Scenario: 沒寫甜度的奶茶
- **WHEN** 手搖飲店家的「珍珠奶茶」經模型判斷後 sugar 是 `null`
- **THEN** 屬性 API 顯示 sugar 為 `null`，但計算 sweet 時把它當成全糖

#### Scenario: 待分析的奶茶
- **WHEN** 手搖飲店家的「珍珠奶茶」還在待分析
- **THEN** 計算 sweet 時同樣把它當成全糖；名稱和店家都看不出甜度的待分析飲品，才當成沒有資料

### Requirement: 待分析品項不影響已知結果
屬性還在待分析的品項，SHALL 只在需要屬性的格子裡被當成沒有資料；類別、金額和日期仍然照常計入其他格子。不需要模型就知道的事實照常使用：類別門檻外的問題是已知的「沒有」、數量 ≥ 3 是囤貨、飲品套用甜度預設規則（見「飲品甜度的預設值」）、店家名稱裡的娛樂字照算。待分析的品名數 SHALL 顯示在查詢結果中。

#### Scenario: 部分品項待分析
- **WHEN** 使用者有 30 個品項，其中 5 個不同品名的屬性是待分析
- **THEN** 品味向量照常算出，只有依賴那 5 個品項屬性的計算少了它們（已知的答案太少時，那個訊號整個量不到，見「已知的答案太少時量不到」），`pending_attributes` 是 5

### Requirement: 未知的屬性不當成「沒有」
用模型屬性計算時，`null`（未知，包含還在待分析的品名）SHALL 視為沒有資料，MUST NOT 當成 `false`。三個只算已知品項的比例訊號（`clearance_share`、`store_clearance_share`、`weekday_quick_share`）的分母 SHALL 只算那個屬性已知的品項；`weekday_quick_share` 的分母是至少有一筆 `quick` 已知的正餐的上班日。`fresh_share`、`bulk_share` 只用已知的答案估模型回答的部分，見「規則決定的部分不拿來代表模型的答案」。類別已經說明問題不適用時（例如正餐的 `cooking`），答案是已知的「沒有」，不是未知。

#### Scenario: 未知的答案不算進分母
- **WHEN** 使用者有 12 個食物品項，其中 4 個品名還在待分析，其餘 8 個的 `clearance` 已知，而且其中 2 個是 `true`
- **THEN** `clearance_share` 是 2 ÷ 8 = 0.25，不是 2 ÷ 12

#### Scenario: 類別不適用
- **WHEN** 使用者的食物品項裡有一個正餐，它的品名還在待分析
- **THEN** 它的 `cooking` 是已知的「沒有」（正餐不是生鮮）：它照樣算進 `fresh_share` 的食物總數，但不算進估下廚比例的生鮮；它的 `clearance` 是未知，不算進 `clearance_share` 的分母

### Requirement: 規則決定的部分不拿來代表模型的答案
`fresh_share` 和 `bulk_share` 有一部分不需要模型就知道：不是生鮮的食物一定不是下廚用，一次買 3 個以上的日用品一定是囤貨。這些答案永遠已知、而且只落在同一邊，所以兩個訊號 SHALL 拆成規則的部分和模型回答的部分，只用模型回答的部分裡已知的答案估那一部分：`fresh_share` = 生鮮占食物的比例 × 已知的生鮮裡下廚的比例（有食物但沒有生鮮時是 0）；`bulk_share` = 一次買 3 個以上的占比，加上其餘日用品裡由已知答案估出的囤貨比例（其餘日用品的個數 × 其中已知答案裡囤貨的比例 ÷ 全部日用品）。每個答案都已知時，結果 MUST 和照原本的比例算出的一樣。（10/16 補上）

#### Scenario: 待分析的生鮮
- **WHEN** 使用者有 20 個食物品項，其中 10 個是生鮮：6 個的 `cooking` 已知而且都是 `true`，4 個還在待分析；10 個正餐也都還在待分析
- **THEN** `fresh_share` 是 10 ÷ 20 × 6 ÷ 6 = 0.5；正餐只算進食物總數，它們已知的「沒有」不會把下廚的比例拉低

#### Scenario: 一次買 3 個的日用品
- **WHEN** 使用者有 12 個日用品，其中 2 個一次買 3 個；其餘 10 個裡 6 個的 `bulk` 已知、其中 3 個是 `true`，4 個還在待分析
- **THEN** `bulk_share` 是 (2 + 10 × 3 ÷ 6) ÷ 12 = 7/12，不是把數量規則的「是」也當成已知答案算出的 5 ÷ 8

#### Scenario: 模型回答的部分全部待分析
- **WHEN** 使用者的品項全部還在待分析，裡面有生鮮，也有一次買不到 3 個的日用品
- **THEN** `fresh_share` 和 `bulk_share` 都是 `null`（量不到），不是 0 和 1

### Requirement: 已知的答案太少時量不到
比例訊號的分母裡有未知的答案、而且已知的少於 5 個時，那個訊號 SHALL 是 `null`（量不到），權重交給同一格的其他訊號。`fresh_share`、`bulk_share` 只看模型回答的部分（生鮮、一次買不到 3 個的日用品）：那部分有未知、而且已知的少於 5 個時是 `null`，規則決定的答案不算在這 5 個裡（10/16 補上）。每個答案都已知時，結果 MUST 和照原本的比例算出的一樣。

#### Scenario: 已知的答案太少
- **WHEN** 使用者有 12 個食物品項，其中 9 個品名還在待分析，只有 3 個的 `clearance` 已知
- **THEN** `clearance_share` 是 `null`，不拿那 3 個碰巧已知的答案代表全部，權重交給同一格的其他訊號

#### Scenario: 答案全部已知
- **WHEN** 同一份品項，每個答案都已知，而且和關鍵字規則給的答案一樣
- **THEN** 品味向量和用關鍵字規則算出的完全一樣；已知的答案再少，比例訊號也不會因為少於 5 個而變成 `null`

### Requirement: 最低品項需求照舊數全部品項
品味格子的最低品項需求（`food_items`、`store_food_items`、`daily_items`、`meal_items` 等）SHALL 照舊數全部品項，不只數屬性已知的。`known_sugar_drinks` 本來就只數甜度已知（包含套用預設規則之後）的飲品，不在此列。

#### Scenario: 待分析的品項照樣算進最低品項需求
- **WHEN** 使用者有 10 個食物品項，其中 6 個品名還在待分析
- **THEN** `food_items` 仍然是 10，需要 10 個食物品項的格子不因此被判為資料不足

### Requirement: 沒有已知答案的次數不是 0
用模型屬性計算時，計次的訊號（`kitchen_per_month`、`sport_supplies`、`sport_gear`、`car_care`、`home_items`、`stationery_items`、`alcohol_items`、`pet_food_cat`、`pet_food_dog`、`pet_supply_cat`、`pet_supply_dog`）在「問題適用的品項」至少有一筆、但沒有任何一筆的答案已知時，SHALL 是 `null`（量不到），MUST NOT 是 0。問題適用的品項就是類別門檻內的品項：`kitchen` 是生鮮和日用品，`sport_gear`、`car_care`、`home`、`stationery` 是非食物（類別 4–9），其他問題不分類別。只要有一筆答案已知，就只數答案是 `true` 的品項；完全沒有適用的品項時是 0。不給模型屬性時，算法不變。（10/16 補上）

#### Scenario: 全部待分析的酒類問題
- **WHEN** 使用者的 3 筆飲品都還在待分析
- **THEN** `alcohol_items` 是 `null`，alcohol 格只看其他訊號；其中一筆判斷過、答案是「不是酒」時，`alcohol_items` 是 0

#### Scenario: 問題不適用任何品項
- **WHEN** 使用者只有正餐，品名都還在待分析
- **THEN** 只問生鮮、日用品或非食物的次數（`kitchen_per_month`、`sport_gear`、`car_care`、`home_items`、`stationery_items`）是 0；不分類別的問題（例如 `alcohol_items`）是 `null`

### Requirement: 全部待分析時的娛樂
模型判斷過的品名沒有娛樂種類，SHALL 視為「不是娛樂」照算。只有全部品項都還在待分析、而且沒有任何店家名稱說是娛樂時，`fun_visits` 和 `fun_kinds` SHALL 是 `null`。（10/16 補上）

#### Scenario: 娛樂
- **WHEN** 使用者的品項全部還在待分析
- **THEN** 沒有娛樂店家時 `fun_visits` 是 `null`；有一筆在名稱含「影城」的店家時照算；品項判斷過但都沒有娛樂種類時是 0

### Requirement: 待分析的寵物店造訪
一張寵物店發票上沒有任何已知物種、又有品項還在待分析時，這次造訪 SHALL NOT 算給貓或狗（不拆成各一半）；這個人的寵物店發票全部如此時，`pet_visits_cat` 和 `pet_visits_dog` SHALL 是 `null`。同一張發票上有已知物種時照已知物種算；判斷過但沒寫物種的寵物商品，照舊貓狗各算一半。（10/16 補上）

#### Scenario: 待分析的寵物店發票
- **WHEN** 養狗的使用者每張寵物店發票上的品項都還在待分析
- **THEN** 這些造訪不算給貓也不算給狗，`pet_visits_cat` 和 `pet_visits_dog` 是 `null`，pets_cat 格不會因此高於用關鍵字規則算出的值

#### Scenario: 已知物種優先
- **WHEN** 一張寵物店發票上有一筆判斷過的「犬用飼料」（species 是 dog）和一筆待分析的品項
- **THEN** 這次造訪只算給狗
