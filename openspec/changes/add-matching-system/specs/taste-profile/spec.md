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
計算 sweet 格時，若飲品的 sugar 是 `null`，系統 SHALL 套用現有的甜度預設規則（例如名稱含「奶茶」視為全糖、含「美式」視為無糖、手搖飲店家的飲品視為全糖）；套用後仍無法判斷的，才當成沒有資料。屬性 API 回傳的 MUST 仍是模型的原始結果。

#### Scenario: 沒寫甜度的奶茶
- **WHEN** 手搖飲店家的「珍珠奶茶」經模型判斷後 sugar 是 `null`
- **THEN** 屬性 API 顯示 sugar 為 `null`，但計算 sweet 時把它當成全糖

### Requirement: 待分析品項不影響已知結果
屬性還在待分析的品項，SHALL 只在需要屬性的格子裡被當成沒有資料；類別、金額和日期仍然照常計入其他格子。待分析的品名數 SHALL 顯示在查詢結果中。

#### Scenario: 部分品項待分析
- **WHEN** 使用者有 30 個品項，其中 5 個不同品名的屬性是待分析
- **THEN** 品味向量照常算出，只有依賴那 5 個品項屬性的計算少了它們，`pending_attributes` 是 5
