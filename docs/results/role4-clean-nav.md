# 精簡導覽與圖內綜合解讀

2026-10-17；工作ID R4-CLEAN-NAV-20261017；基準a8268d2；待Claude審核，未整合／未推送。

功能頁上方僅保留返回選擇，移除「我的月報／找到同好」按鈕；換功能經過兩張選項卡。月報重新載入移至右上角設定，僅月報頁顯示，按下會關閉選單。

綜合解讀移入連線圖canvas，桌面為圖內下方置中半透明區塊，圖高預算從外層可用高度減260改減170，取回原本獨立解讀所占高度。可比較時只顯示綜合解讀標題與相投／差異內容，移除重複對象介紹（對象仍在外層標題及圖上）。資料不足時保留原因說明。手機解讀自然排在同圖卡的圖形下方，避免遮住直式圖；仍只有外層結果區捲動，計算明細仍預設收合。

修改：src/web_v2/{index.html,styles.css,workspace-ui.js,network.html,network-view.js,network-embed.js,network-layout.css}；共用瀏覽器導覽／刷新helper與4份瀏覽器回歸；OpenSpec web-app/spec.md、本文件。既有API、分數、模型、資料庫與v1不變。

## 驗證

在原角色4worktree執行：
- 主.venv/Scripts/python.exe -X utf8 tests/run_web_v2_live.py tests/web-v2-explanation-browser.cjs tests/web-v2-pages-browser.cjs tests/web-v2-live-browser.cjs：3組通過，50071釋放。
- 同runner跑 web-v2-browser.cjs、web-v2-account-browser.cjs、web-v2-recompute-browser.cjs：3組通過，63453釋放。測試包含設定內刷新、導覽、登入／上傳／月報／配對／帳號輪替／重算保護。
- node --test "tests/*.test.cjs"：148/148通過；git diff --check通過。
- 新增1366×768與1024×640圖內解讀完全位於canvas、未遮任何已顯示特質標籤或分數；延續手機無內頁溢出、外層wheel、結果返回／延遲／401清理。月報導覽僅一個button，真登入與兩選項路徑正常。
- CUA原8001虛構配對，確認功能導覽只有返回選擇，解讀位於圖內且標籤／分數碰撞數0。截圖本聊天visualizations/role4-clean-nav.png；臨時尺寸覆寫已還原，預覽保留。

本輪使用fake模型與臨時DB；部分瀏覽器為契約替身，live-browser走正式HTTP。未執行Python全套、真模型、Docker、CI；無GPU／後端／環境／依賴修改，原8001未重啟。Claude請針對commit審核導覽、選單刷新與圖內文字可讀性，Codex依回饋調整。

規格與邊界：openspec.cmd validate add-matching-system --strict、git diff --check通過；git diff --quiet a8268d2 -- src/web invoice-insights.html exit0。
