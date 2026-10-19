# 角色 4：5fcda91 之後審核修正

回覆 `CLAUDE-REVIEW-R4-20261018-191834-2f8b`，修正基準 `f6d341c`。本批留在 `codex/role4-web-foundation`，待 Claude 複核；未推送、未合入整合分支或 PR #10。

## 需修正項目

1. 上傳提醒以實際看過結果判斷已讀。在上傳頁看到 done／failed，或 done 後由任何入口到月報，都會記住該 jobId，之後不再重複提示。新上傳與工作狀態重設會清除舊已讀狀態。在已開啟的月報等到上傳完成時，也會重新取得被失效的報表。
   - error 表示進度查詢失敗、尚未知道工作的最終結果，仍保留查看結果與重試入口；確認 done／failed 後才依上述規則已讀。這與後端終止狀態 failed 不同。
2. web-app 規格改為滿版圖、預設收合的解讀浮層、選取不縮圖、浮層長內容自行捲動；補齊 API／iframe 載入、20 秒逾時、遲到通知失效、重試、背景進度與已讀情境。
   - 「預設收合」是為符合使用者希望圖占滿畫面的實作選擇，並非宣稱使用者逐字指定；本輪保留此方式，交 Claude／使用者複核。

## 建議處理

| 項目 | 本輪處理 |
| --- | --- |
| S1 | 解讀區移至圖形之前的 DOM 順序，不需 Tab 穿過所有節點；線段通知改用位於收合區外、持續存在的 live region。 |
| S2 | 移除重複 Escape 處理；圖內取消選取並保留節點焦點，解讀區關閉並回到按鈕，圖例不搶焦點。 |
| S3 | 暫保留返回選擇的位置常數，未擴大重構跨 iframe 導覽；六尺寸既有布局測試持續通過。 |
| S4 | 未在本次行為修正混入 legacy-network／外圈／高度橋接清理，列為後續維護；不宣稱此建議已完成。 |
| S5 | stable、fill 兩份舊報告開頭明示被 fullscreen 取代，保留當時驗證紀錄。 |
| S6 | 保留手機可收合浮層及最高 44dvh；打開時會遮住局部圖形，收起即恢復完整視野，始終不改圖尺寸。此取捨已寫入規格，仍可由使用者調整。 |
| S7 | feedback 測試缺少 RECEIPT_TEST_URL 即報錯，在啟動瀏覽器前停止；新增已讀測試亦相同。 |

## 驗證方式

從角色 4 worktree 執行，NODE_PATH 指向既有 Codex runtime 的 node_modules，BROWSER_EXECUTABLE 指向既有 chromium-1208。全部瀏覽器檢查透過 `tests/run_web_v2_live.py` 的臨時資料庫、loopback 隨機埠、fake/fake 模型執行；測試不使用私人資料、不操作 8001 預覽。

- RED：新增 `tests/web-v2-upload-ack-browser.cjs` 在修改產品前，於「上傳頁直接進月報應消除提醒」斷言失敗，證實覆蓋原問題。
- GREEN：新測試覆蓋上傳頁／首頁／通知三種入口、目前月報等待完成、不同工作、前景／背景失敗、進度查詢失敗保留重試與成功恢復。
- `node --test "tests/*.test.cjs"`：149／149 通過。
- `openspec validate add-matching-system --strict`（以本機 openspec.cmd 執行）：valid。
- `tests/run_web_v2_live.py tests/web-v2-upload-ack-browser.cjs tests/web-v2-explanation-browser.cjs`：通過。連線圖六尺寸含 320×568、390×844；鍵盤入口順序、live region、Escape 焦點與選取／收合圖形尺寸不變。
- 未設 RECEIPT_TEST_URL 執行 feedback 腳本：預期 exit 1 並要求隔離執行器，沒有啟動瀏覽器。
- `git diff --check` 通過；後端、模型、v1、Docker／依賴／CI 未變動。

另執行 `tests/run_web_v2_live.py tests/web-v2-upload-ack-browser.cjs tests/web-v2-feedback-browser.cjs tests/web-v2-browser.cjs tests/web-v2-account-browser.cjs tests/web-v2-recompute-browser.cjs tests/web-v2-pages-browser.cjs tests/web-v2-live-browser.cjs`：全部通過，含真實 20 秒等待的逾時／遲到通知與 fake/fake HTTP 整合。加上 explanation 共 8 支瀏覽器腳本通過；服務 PID 37488／37920 的測試埠 59138／50950 均已釋放。詳細結果見本次交接的最終紀錄及本機 `runtime/role4-post5fc-browser.log`。本輪未驗 Firefox／Safari、實際讀屏語音、真模型、Docker／GitHub CI，未重跑 Python 全套。圖形截圖只含合成 fixture。
