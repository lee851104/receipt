# 角色 4：等待與操作狀態 UX 檢查

2026-10-18，基準 be55274；本機實作，待 Claude 審核，未推送或整合。

## 檢查與修正

| 流程 | 等待時 | 完成／異常時 |
|---|---|---|
| 服務、登入、註冊、示範登入 | 同風格旋轉提示、操作文字、送出按鈕忙碌狀態 | 正常轉頁；既有中文錯誤／重新連線保留 |
| 月報 | 區分 API 載入、背景重新計算、圖表資源準備 | 圖表真正就緒才移除提示；API／腳本失敗可重試，空月份提示保留 |
| 配對列表 | 尋找中文字、骨架佔位、查詢按鈕暫停 | 保留無符合者／距離／資料不足說明 |
| 滿版連線圖 | 分開顯示取得配對資料與繪圖中 | 就緒才顯示圖；錯誤／20 秒未就緒提供重新查詢；返回入口一直可用 |
| 上傳 | 上傳、排隊、分析；未知總數使用不定進度，不顯示 0/0 | 有總數才顯示真實 done/total；零筆完成不留動畫；背景狀態可返回進度，完成可進月報 |
| 帳號操作 | 載入、儲存名稱、改密碼、刪除、登出均有明確文字與按鈕狀態 | 成功／失敗訊息保留；示範登出說明改為只影響本瀏覽器 |
| 窄／低視窗 | 小高度節奏頁收起重複標題；320px 背景上傳不擠壞頁首 | 月報圖表與底部控制在同屏，滿版線圖大小不因 loading 改變 |

遵循 reduced motion；狀態使用 role=status／aria-live，相關內容與按鈕使用 aria-busy。沒有加入假進度，也不刻意延遲快速回應。

圖表就緒通知攜帶目前 payload 與載入序號；舊 iframe 晚到回呼不會覆蓋新狀態，20 秒逾時後也不會自行清除錯誤。離開配對頁不被晚到結果拉回。後端 API、資料庫與 v1 未改。

## 驗證

- RED：新慢速測試先失敗於缺少 auth-status。
- 149/149：node --test "tests/*.test.cjs"。
- 七組瀏覽器檢查皆有本輪通過結果：web-v2-feedback-browser、web-v2-browser、web-v2-pages-browser、web-v2-account-browser、web-v2-recompute-browser、web-v2-explanation-browser、web-v2-live-browser。
- 透過主 .venv Python -X utf8 tests/run_web_v2_live.py 執行：fake/fake、暫存 DB。第一批 PID37452／port56012 完成前四組後因重算測試沿用舊文案而停止；修正測試使用新版文案及檢查停用按鈕後，PID16104／port55747 的重算、配對、真 HTTP 全流程通過；兩埠已釋放。
- 新 feedback 測試實際等待 20 秒逾時，驗證晚到回覆仍保留重試、腳本失敗、重算、未知總數、零筆完成、背景上傳與完成入口、手機、reduced motion，以及各表單等待狀態。最終直接以8001提供靜態資源，所有 API route.fulfill 為合成 fixture，未寫入原預覽資料庫。
- 整體測試發現 558×510 節奏頁可用高度306px、內容333.9px，修正重複標題後四尺寸五章節均同屏。保留原高度斷言。
- 真 HTTP 流程含80筆合成上傳、月報、配對18格、帳號改名／改密碼／刪除／登出，pageerror 0。
- OpenSpec strict、git diff --check、v1／後端邊界檢查通過。
- 日誌：runtime/role4-ux-node.log、role4-ux-browser.log（含早期失敗）、role4-ux-browser-rest.log、role4-ux-feedback-final.log。
- 目視截圖：runtime/role4-loading-report.png、role4-loading-network.png、role4-loading-mobile.png、role4-upload-background-mobile.png。

本輪沒有重跑 Python 全套、Docker、遠端 CI 或真模型；本地8001保留原資料庫，已更新瀏覽器到 ux1 的配對圖。待 Claude 審核後再由角色1整合。這是既有主要流程的自動化與視覺檢查，不代表所有瀏覽器或所有裝置的完整可用性研究。
