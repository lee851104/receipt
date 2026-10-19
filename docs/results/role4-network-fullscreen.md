# 角色 4：配對線圖滿版

2026-10-18，基準 519b6e6；待 Claude 審核，未推送／整合。

使用者最新要求「線圖占滿整個畫面」。本版取代下方常駐並排解讀：配對結果使用完整瀏覽器內容區，移除頁首、最大內容寬度與卡片框線；返回列表／返回選擇保留左上浮動按鈕，圖例與動態控制在右上。綜合解讀／線段說明平時收合，選取線段或訊號自動開啟浮層，可用按鈕或 Escape 收起；計算過程也以浮層開啟。浮層不參與圖形大小計算。長文字僅於開啟的浮層捲動，圖與頁面本身不捲動。

手機沿用上下兩人圖，但依完整視窗高度拉開兩人距離；文字和圓點不拉伸。返回後恢復原首頁、月報與設定版面。沒有呼叫瀏覽器原生全螢幕 API，不影響使用者的瀏覽器工具列。

## 本次驗證

- RED：1440×1000 的原 iframe 位於 (80,147)，大小 1280×805，未滿版。
- GREEN：1440×1000、1920×1080、1366×768、1024×640、390×844、320×568 六尺寸，iframe 位於 (0,0) 並等於視窗寬高（誤差 <2px）；無頁面或 iframe 內層捲軸。
- 線段／訊號選取前後 viewBox 相同，圖高差 <2px、scale 差 <.002；解讀開關、Escape、計算過程開啟皆不縮圖。
- 桌面字級約 18.3／24.5／17.4／12.9px，文字未裁切。節點垂直占圖高約 92%，維持比例。
- node --test "tests/*.test.cjs"：149/149。既有頁面 DOM 替身新增 body/classList.toggle 支援。
- 主 .venv Python -X utf8 tests/run_web_v2_live.py tests/web-v2-explanation-browser.cjs tests/web-v2-live-browser.cjs：全通過，fake/fake、暫存 DB，PID 36728／port 65500 已釋放。包含真 HTTP 登入、80 筆合成上傳、月報、配對 18 格及帳號全流程，pageerror 0。
- 測試初次讀取新 iframe 過早、設定舊導覽路徑仍直點已隱藏頁首；已改等圖就緒，以及使用可見的返回選擇後進設定，未放寬尺寸或資料斷言。
- OpenSpec strict、git diff --check、v1／後端邊界檢查通過。
- runtime/role4-full-browser.log、role4-full-node.log；role4-full-desktop.png、role4-full-320.png、role4-full-selected-390.png 為本次合成 fixture 截圖。
- 使用者 8001 已重載到 full1、顯示晨光 × 青禾，維持原資料庫與服務。

本輪未執行 Python 全套、Docker、遠端 CI 或真模型驗收。Claude 審核本提交後，再由角色 1 決定整合；既有展示 GIF 為歷史版。
