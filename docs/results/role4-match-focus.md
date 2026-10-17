# 配對結果版面整理

2026-10-17；工作ID R4-MATCH-FOCUS-20261017；基準 bc8d9ea；待 Claude 審核，未整合／未推送。

## 行為與範圍

依使用者最新指示取代前版「列表下方自動捲到結果」：選人立即進入結果畫面，列表與篩選隱藏，上方保留返回與對象名稱。返回會清除結果、取消 explain、保留原清單／篩選／捲動位置，焦點回到所選對象；忽略取消的延遲回應也不能重新開啟結果。

關係圖放最上方，圖中的百分比為唯一預設分數顯示；移除原內頁品牌、宣傳標題和另一張分數卡。下方直接保留綜合解讀，圖例與計算明細預設收合；點圖才出現該連線細節，清除選取會收起細節。計算明細仍可自行展開，後端分數與 18 格完全不變。

新增 network-layout.css 與 network-embed.js；圖面高度依外層配對區可用高度計算，內頁實際內容高度回傳同源父頁，父頁只接受目前 payload 的有限合法高度。觀察外層容器與內容尺寸，避免依 iframe 自身 viewport 計算造成回饋迴圈；移除頁面時清理觀察器。內頁不建立獨立捲軸，外層負責長內容，手機不強迫縮小成不可讀的一屏。

其他修改：index.html、workspace-flow.js、workspace-ui.js、styles.css、network.html、network-view.js、四份相關測試、web-app/spec.md。沒有改後端、v1、資料庫、環境、依賴或模型。

## 實際驗證

在 C:/Users/User/.codex/worktrees/receipt-role4/receipt 執行：

1. 主 .venv/Scripts/python.exe -X utf8 tests/run_web_v2_live.py tests/web-v2-explanation-browser.cjs tests/web-v2-browser.cjs tests/web-v2-live-browser.cjs：3 組通過，60181 已釋放。前兩組含契約替身；最後一組使用正式 HTTP API、fake/fake、臨時 DB，驗證上傳／月報／配對／帳號全流程。無 GPU。
2. 補入圖上滾輪只捲外層的案例後，同 runner 單跑 web-v2-explanation-browser.cjs 通過，61571 已釋放。含 1366×768、1024×640 桌面圖與解讀一屏，390×844、320×568 無內頁垂直或橫向溢出；展開圖例仍自動調整高度；返回焦點、離頁延遲、錯誤、資料不足與 401 清理。
3. node --test "tests/*.test.cjs"：148/148 通過，新增返回列表取消查詢且保留篩選／清單案例。
4. node --check workspace-ui.js、network-view.js、network-embed.js（位於 src/web_v2）通過；git diff --check 通過。
5. 初次尺寸檢查在 58772／62745 失敗：測試於 viewport 改變後讀到前一尺寸的排版，診斷確認 main --graph-height 仍為舊值。改為等待容器對應高度及內頁尺寸穩定後，上述最終回歸通過；兩埠均釋放。
6. CUA 原 8001 假模型預覽點選虛構對象，確認列表隱藏、圖中央分數、綜合解讀與返回。1366×768 圖與解讀完整可見，內頁 scrollHeight=clientHeight=515；短窄視窗只見外層捲軸。截圖本聊天 visualizations/role4-match-focused.png。暫時尺寸覆寫已還原，預覽留結果畫面並播放既有動態。

## 限制與交接

本輪未執行 Python 全套、真模型、Docker、CI 或完整 300 人 seed；沒有重新錄製歷史 GIF。原 8001 未重啟，未推送或合併。桌面一般尺寸一屏驗證通過；極短螢幕、手機、長名稱／長解讀及展開細節允許單一外層捲動，以可讀性優先。

Claude 請審核結果切換、取消／返回防護、同源 iframe 自動高度與可及性；使用者體驗後由 Codex 調整。正式審核需指定受審 commit。

規格與邊界：openspec.cmd validate add-matching-system --strict 通過；git diff --quiet bc8d9ea -- src/web invoice-insights.html exit0。
