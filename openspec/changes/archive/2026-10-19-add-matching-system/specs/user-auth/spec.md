# Spec Delta

## Purpose

讓每位使用者用自己的帳號登入，系統才知道「我是誰」，也才能把上傳的發票、品味向量和配對結果綁在同一個人身上。

## ADDED Requirements

### Requirement: 註冊帳號
系統 SHALL 允許使用者以帳號名稱、密碼和可省略的顯示名稱註冊。帳號名稱 MUST 是 3–32 個英數字或底線而且不重複，不分大小寫（一律存成小寫，登入時也轉成小寫比對），也不能以 `demo_` 開頭，那是留給假用戶的；密碼 MUST 是 8–128 個字元，先做 Unicode NFKC 正規化，再以單向雜湊保存；顯示名稱是 1–20 個字元，省略時等於帳號名稱，不能含控制字元、看不見的字元、私用字元、未指派字元或換行。

#### Scenario: 註冊成功
- **WHEN** 使用者送出還沒被使用的帳號名稱 `amy` 和 8 個字元以上的密碼，沒有給顯示名稱
- **THEN** 系統回應 201，回傳 `user_id`、`username` 和等於 `amy` 的 `display_name`

#### Scenario: 帳號名稱重複
- **WHEN** 使用者送出已經存在的帳號名稱
- **THEN** 系統回應 409 `username_taken`，不建立新帳號

#### Scenario: 格式不符
- **WHEN** 使用者送出少於 8 個字元的密碼，或含有空白的帳號名稱
- **THEN** 系統回應 422，不建立帳號

#### Scenario: 帳號名稱不分大小寫
- **WHEN** 使用者註冊 `Amy`，之後有人再註冊 `amy`
- **THEN** 第一個帳號存成 `amy`，第二次註冊回應 409 `username_taken`；用 `AMY` 也能登入第一個帳號

#### Scenario: 留給假用戶的名稱
- **WHEN** 使用者註冊 `demo_001` 或 `Demo_123`
- **THEN** 系統回應 422，不建立帳號

#### Scenario: 看不見的顯示名稱
- **WHEN** 使用者送出的顯示名稱只有零寬空白，或含有換行、方向控制字元
- **THEN** 系統回應 422，不建立帳號

### Requirement: 登入取得存取權杖
系統 SHALL 在帳號和密碼都正確時，回傳 bearer 存取權杖和它的有效秒數。帳號不存在和密碼錯誤 MUST 回應同一個錯誤 401 `bad_credentials`（帶 `WWW-Authenticate: Bearer`），而且花費的時間相近，不透露是哪一項錯誤。密碼 SHALL 先做 Unicode NFKC 正規化再比對；超過 512 個字元的密碼 MUST 直接視為密碼錯誤，不把整串拿去正規化。

#### Scenario: 登入成功
- **WHEN** 使用者送出正確的帳號和密碼
- **THEN** 系統回傳 `access_token`、值為 `bearer` 的 `token_type`，以及 `expires_in`

#### Scenario: 密碼錯誤
- **WHEN** 使用者送出存在的帳號和錯誤的密碼
- **THEN** 系統回應 401 `bad_credentials`，和「帳號不存在」時完全相同，兩種都帶 `WWW-Authenticate: Bearer`

#### Scenario: 密碼的寫法不同
- **WHEN** 使用者註冊時密碼裡的 é 是單一字元，登入時輸入的是 e 加上組合用的重音符號
- **THEN** 登入成功

#### Scenario: 過長的密碼
- **WHEN** 使用者送出超過 512 個字元的密碼
- **THEN** 系統回應 401 `bad_credentials`

### Requirement: 受保護的功能需要權杖
除了註冊、登入、demo 名單、demo 快速切換、健康檢查和 API 文件頁以外，所有 API SHALL 要求有效的存取權杖。存取權杖 SHALL 帶著簽發時這個帳號的 `token_key`（每個帳號一把隨機字串）；帳號已經不存在，或權杖裡的 key 和帳號現在的 `token_key` 不同，權杖就算失效。沒有權杖、權杖過期、被竄改或已經失效時，系統 MUST 回應 401 `not_authenticated`，並帶 `WWW-Authenticate: Bearer`。

#### Scenario: 沒有權杖
- **WHEN** 請求沒有附上存取權杖就查詢配對清單
- **THEN** 系統回應 401 `not_authenticated`

#### Scenario: 權杖已過期
- **WHEN** 請求附上超過有效時間的權杖
- **THEN** 系統回應 401 `not_authenticated`

#### Scenario: 帳號的 id 被新帳號重用
- **WHEN** 一個帳號被刪除，新註冊的帳號拿到相同的 user id，有人拿舊帳號的權杖呼叫 API
- **THEN** 系統回應 401 `not_authenticated`；新帳號用自己的權杖則可以正常使用

### Requirement: demo 名單與快速切換
系統 SHALL 只在 demo 模式開啟時，提供假用戶名單，並允許不輸入密碼就以某位**假用戶**的身分取得存取權杖。demo 模式關閉時，這兩個功能 MUST 回應 404，就像不存在一樣。真實註冊的帳號 MUST NOT 能用快速切換登入。快速切換的 `user_id` MUST 是 1 到 2^63−1 的 JSON 整數。demo 模式關閉後，假用戶先前取得的權杖 MUST 立刻失效，真實帳號的權杖不受影響。

#### Scenario: demo 模式下切換
- **WHEN** demo 模式開啟，請求切換成名單上的一位假用戶
- **THEN** 系統回傳這位假用戶的存取權杖

#### Scenario: 想切換成真實帳號
- **WHEN** demo 模式開啟，請求切換成一個真實註冊的帳號
- **THEN** 系統回應 403 `not_demo_user`

#### Scenario: 一般模式下無法使用
- **WHEN** demo 模式關閉，有人查詢假用戶名單或呼叫快速切換
- **THEN** 系統回應 404

#### Scenario: user_id 不是整數
- **WHEN** demo 模式開啟，快速切換送出 `true`、字串 `"2"`、`2.0`、0 或超過 2^63−1 的 `user_id`
- **THEN** 系統回應 422，不簽發權杖

#### Scenario: 關閉 demo 模式之後
- **WHEN** 假用戶已經取得權杖，之後 demo 模式被關閉
- **THEN** 這個權杖回應 401 `not_authenticated`；真實帳號的權杖照常可以使用

### Requirement: 不外流密碼
系統的任何回應 MUST NOT 包含密碼或密碼雜湊。

#### Scenario: 註冊後的回應
- **WHEN** 註冊成功
- **THEN** 回應內容沒有密碼，也沒有密碼雜湊

#### Scenario: 被拒絕的輸入
- **WHEN** 註冊的密碼太短，系統回應 422
- **THEN** 回應說明哪個欄位格式不符，但沒有包含被拒絕的密碼
