# 已上傳資料：月份管理視窗

基準：main `233c86b`（本輪原 role4 分支由 a6f5591 快轉至此，包含 PR #10 與 #11）。實作留在 `codex/role4-web-foundation`，待 Claude 審核；未 push／未合併。

使用者同意以月份管理，不保存或顯示每次上傳的原始檔案歷史。

## 使用方式與行為

- 設定選單、上傳頁的「已上傳資料」，以及帳號設定的多選管理入口，開啟同一個視窗。每次開啟重新取得 `GET /api/me`，含只有工作而沒有品項的月份。
- 月份由新到舊排列，可勾選／全選、刪除所選或全部刪除。保留原帳號設定的單月刪除操作。
- 確認視窗列出月份與數量；確認前不送 DELETE，取消及 Escape 保留選取。確認後逐月呼叫 `DELETE /api/me/months/{month}`，顯示進度並阻止重複提交。
- 不是交易式批次 API：成功月份移除、失敗月份保留並附原因；month_not_found 視為已不存在。遇到登入／權限失敗停止剩餘請求；登入失效關閉視窗並清除選取。示範帳號唯讀。
- 有月份移除後沿用帳號變更流程：失效月報／清單／連線圖、重新取得月報並等候重算；目前在配對頁則自動更新清單，其他頁面於再次進配對時讀新結果。全部刪除保留帳號，顯示空月報與資料不足。
- 長列表只捲動列表區，底部操作保持可見。取消回原按鈕，完成批次刪除回列表標題；關閉回入口或設定按鈕，避免刪光後焦點遺失。

## 本輪實際驗證

- TDD：先加入 4 個批次控制器測試，因 askDeleteMonths 尚未存在而失敗；實作後 12／12 帳號測試通過。
- `node --test "tests/*.test.cjs"`：153／153 通過。新增頁面模組第一次遇到舊測試 DOM 沒有 close 方法，修正為只關閉已開啟視窗後通過。
- `tests/run_web_v2_live.py tests/web-v2-months-browser.cjs`：fake API 契約全通過，包含 loading／重試、確認取消、逐筆進度、部分 409、刷新月報及配對、全刪空畫面、401 清理與示範唯讀。1366×768、390×844、320×568 的 24 月份列表與手機長確認視窗皆可操作。
- 另加「刪光後焦點留在管理視窗」檢查，重現確認按鈕停用後焦點落到外層；修正焦點回月份標題後再次通過。該次測試服務 PID35496／埠55460 已釋放；後續再驗單月刪除不沿用舊批次進度，Node 153／153 與月份瀏覽器測試再度通過，最終 PID31740／埠59132 亦釋放。
- `tests/run_web_v2_live.py tests/web-v2-live-browser.cjs tests/web-v2-account-browser.cjs tests/web-v2-recompute-browser.cjs tests/web-v2-feedback-browser.cjs`：全部通過。PID39636／埠60110 已釋放。
- live 腳本未攔截 API：臨時 SQLite、正式 API／worker、fake/fake 模型；新加兩個月份後，勾選刪除五月／六月，確認七月保留；再全刪，確認帳號保留、item_count=0、ready=false、月報空、配對不再包含此使用者。既有帳號密碼、登出、刪帳號回歸亦通過。
- `openspec validate add-matching-system --strict` 通過；`git diff --check` 通過；相對 233c86b 的 API、模型、v1、Docker、CI 及設定無變更。

瀏覽器環境使用既有 Codex runtime 的 Playwright、chromium-1208 與主目錄 .venv Python。所有刪除均為臨時假資料，8001 預覽資料沒有刪除。可檢視忽略產物 `runtime/role4-months-desktop.png`、`role4-months-320.png`、`role4-month-browser.log`、`role4-month-node.log`。

本輪未執行 Python 全套、Docker／GitHub CI、真模型、Firefox／Safari 或實際讀屏。尚待 Claude 審核本輪新提交。
