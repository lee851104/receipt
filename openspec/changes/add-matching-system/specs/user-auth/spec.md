# Spec Delta

## Purpose

讓每位使用者用自己的帳號登入，系統才知道「我是誰」，也才能把上傳的發票、品味向量和配對結果綁在同一個人身上。

## ADDED Requirements

### Requirement: 註冊帳號
系統 SHALL 允許使用者以帳號名稱、密碼和可省略的顯示名稱註冊。帳號名稱 MUST 是 3–32 個英數字或底線而且不重複；密碼 MUST 是 8–128 個字元，只能以單向雜湊保存；顯示名稱是 1–20 個字元，省略時等於帳號名稱。

#### Scenario: 註冊成功
- **WHEN** 使用者送出還沒被使用的帳號名稱 `amy` 和 8 個字元以上的密碼，沒有給顯示名稱
- **THEN** 系統回應 201，回傳 `user_id`、`username` 和等於 `amy` 的 `display_name`

#### Scenario: 帳號名稱重複
- **WHEN** 使用者送出已經存在的帳號名稱
- **THEN** 系統回應 409 `username_taken`，不建立新帳號

#### Scenario: 格式不符
- **WHEN** 使用者送出少於 8 個字元的密碼，或含有空白的帳號名稱
- **THEN** 系統回應 422，不建立帳號

### Requirement: 登入取得存取權杖
系統 SHALL 在帳號和密碼都正確時，回傳 bearer 存取權杖和它的有效秒數。帳號不存在和密碼錯誤 MUST 回應同一個錯誤 401 `bad_credentials`，而且花費的時間相近，不透露是哪一項錯誤。

#### Scenario: 登入成功
- **WHEN** 使用者送出正確的帳號和密碼
- **THEN** 系統回傳 `access_token`、值為 `bearer` 的 `token_type`，以及 `expires_in`

#### Scenario: 密碼錯誤
- **WHEN** 使用者送出存在的帳號和錯誤的密碼
- **THEN** 系統回應 401 `bad_credentials`，和「帳號不存在」時完全相同

### Requirement: 受保護的功能需要權杖
除了註冊、登入、demo 名單、demo 快速切換、健康檢查和 API 文件頁以外，所有 API SHALL 要求有效的存取權杖。沒有權杖、權杖過期、被竄改或已經失效時，系統 MUST 回應 401 `not_authenticated`。

#### Scenario: 沒有權杖
- **WHEN** 請求沒有附上存取權杖就查詢配對清單
- **THEN** 系統回應 401 `not_authenticated`

#### Scenario: 權杖已過期
- **WHEN** 請求附上超過有效時間的權杖
- **THEN** 系統回應 401 `not_authenticated`

### Requirement: demo 名單與快速切換
系統 SHALL 只在 demo 模式開啟時，提供假用戶名單，並允許不輸入密碼就以某位**假用戶**的身分取得存取權杖。demo 模式關閉時，這兩個功能 MUST 回應 404，就像不存在一樣。真實註冊的帳號 MUST NOT 能用快速切換登入。

#### Scenario: demo 模式下切換
- **WHEN** demo 模式開啟，請求切換成名單上的一位假用戶
- **THEN** 系統回傳這位假用戶的存取權杖

#### Scenario: 想切換成真實帳號
- **WHEN** demo 模式開啟，請求切換成一個真實註冊的帳號
- **THEN** 系統回應 403 `not_demo_user`

#### Scenario: 一般模式下無法使用
- **WHEN** demo 模式關閉，有人查詢假用戶名單或呼叫快速切換
- **THEN** 系統回應 404

### Requirement: 不外流密碼
系統的任何回應 MUST NOT 包含密碼或密碼雜湊。

#### Scenario: 註冊後的回應
- **WHEN** 註冊成功
- **THEN** 回應內容沒有密碼，也沒有密碼雜湊
