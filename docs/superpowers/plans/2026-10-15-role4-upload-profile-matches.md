# 角色 4 第二批實作計畫

**Goal:** 完成 OpenSpec 5.4、5.5、5.6 的前端：CSV 上傳與工作進度、有限次屬性重查、API 月報／品味與配對。
**Spec:** docs/team/overview.md 5.4–5.7 及角色 1 第 2 週交接；web-app 規格。
**Architecture:** 延續原生 HTML/CSS/JS。flow 管理登入與分類；workspace-flow 管理上傳、profile、matches 與選中對象；從 v1 複製月報和關係圖到隔離 iframe，由父頁提供目前身分的 API 快照。沒有內嵌使用者資料、沒有前端重算配對排名。

## 決定與限制

- 使用者同意接續前次建議的三項。沿用現有視覺與 API 契約。
- 已把角色 1 已提交的 role-1/uploads（8510bc1）合併到角色 4 分支。上傳與 pending 背景處理可做本機真實 API 驗證；profile／matches／explain 尚未實作，使用虛構 fixture 驗證，不在產品自動替換假資料。
- 配對結果採 API 的 percent、eligible、within。關係圖沿用 v1，使用 explain.network；逐格計算面板 5.7 本次不做。profile 只有 18 格向量，不能捏造 46 個訊號，所以個人頁先列 18 格，選中配對對象後才用完整 network 畫雙方關係。
- v1 完全不改，新增前端檔案均在 src/web_v2/。帳號切換、401、過期時取消工作與請求並清掉 iframe 私人資料。
- 上傳每 2 秒讀工作，直到 done／failed；網路中斷提供「重新查詢進度」，不自動重傳 CSV。分類最多額外 5 次，之後「稍後再查」。
- 不刪除舊開發資料庫；新後端使用 worktree 內另一個被忽略的資料庫，以保留第一批測試資料。

## 步驟與驗證

- [x] 上傳／分類：先寫 pending→ready、5 次上限、取消、multipart、queued/running/done/failed、413/invalid_csv/403、重試與舊回應測試，再實作。
- [x] profile／matches：先寫空月份、資料不足、範圍切換、eligible/within、API 百分比、過期及競態測試，再實作控制器。
- [x] 複製月報與關係圖：保留既有視覺與互動，使用 API 快照；修改 v2 文案以符合新後端的分類／折扣規則；新增適配測試。
- [x] 接上導覽與手機版 UI；用假 API 驗證月報／配對／圖，用真實 API 驗證上傳／分類。
- [x] 全部 Python／JS、OpenSpec、v1 零差異、獨立審查；更新完成項目與交接並本機提交。

## 完成驗證（2026-10-15）

- Python：`python -m unittest discover -s tests`，212 項通過。
- JavaScript：`node --test "tests/*.test.cjs"`，127 項通過（原有 v1 82 項保持通過）。
- `openspec validate add-matching-system --strict` 通過；`git diff cfbdd35 -- src/web invoice-insights.html` 無差異。
- `tests/web-v2-browser.cjs`：真實本機 API 註冊／登入、虛構 CSV 上傳完成、分類 pending→ready（fake 模型）；未實作 profile 回 404 時顯示尚未就緒。
- 同一瀏覽器測試用受控假 API 驗證 invalid_csv 的附加說明、413、job failed、兩月切換、18 格／null／空月份、距離切換、配對百分比、關係圖滑鼠與鍵盤互動、帳號切換清空 iframe、demo 禁止上傳、1440px／390px 無橫向溢出或 JS 例外。
- 審查抓到上傳完成後舊 profile／matches／network 回應可能恢復舊資料，已取消三個 channel 並加入先失敗再通過的回歸測試；獨立覆核通過。
- HTML 實際 script 入口也納入頁面測試；轉接程式命名為 `view-adapters.js`，避免落入專案忽略私人產生資料的 `*-data.js` 規則。
- profile／matches／explain 後端未完成，這部分只確認前端契約與互動；尚未驗證真模型／GPU、全流程整合。5.7 保持未完成。

瀏覽器測試需另有 Playwright 與 Chromium；透過 `NODE_PATH`、`BROWSER_EXECUTABLE` 指定既有 runtime，預設測試服務為 `http://127.0.0.1:8001`，可用 `RECEIPT_TEST_URL` 調整。測試只使用虛構資料，會在測試服務建立測試帳號與發票；請使用獨立測試資料庫。
