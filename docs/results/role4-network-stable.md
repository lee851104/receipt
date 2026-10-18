# 角色4：選取連線時維持圖形尺寸

> 歷史驗證紀錄：此版面已由 [滿版連線圖](role4-network-fullscreen.md) 取代；下列尺寸與捲動敘述只適用於當時提交。

2026-10-18；工作ID R4-NETWORK-STABLE-20261018；基準5fcda91，原角色4 worktree。依使用者要求直接調整，待Claude審核。

## 調整

- 連線圖占滿可用寬度，下方綜合解讀與線段說明並排，手機上下排列。維持原深色、粉紅／藍色人物與綠色分數風格。
- 選取文字的高度不再從canvas扣除；圖形高度只依視窗及固定綜合解讀區計算。文字較長或窄螢幕時由外層頁面往下捲，沒有iframe內層捲軸、不截斷說明。
- 常買品項與次數改在既有文字說明顯示，不再新增外圈品項節點或擴大SVG viewBox。選取、重設前後皆維持座標範圍與縮放。
- 保留點選圓點／線段、鍵盤Enter/Escape、綜合解讀、動畫及計算明細。更新資源版本避免快取沿用舊入口。

## 本輪驗證

- 先以測試重現：1366x768的線段選取使canvas高度484→431、scale .7471→.7183；修正後高度差小於2px、scale差小於.002，viewBox完全相同。
- tests/web-v2-explanation-browser.cjs：1366x768、1024x640、390x844、320x568，分別選取線段及訊號，確認高度／縮放／viewBox不變，品項文字仍可見；桌面總覽與收合計算同頁、字體與橫向占比維持門檻，iframe沒有內部捲軸。保留18格數值／不足資料／錯誤契約／返回／登出測試。
- 初次測試點選重疊路徑被遮擋，改用既有鍵盤選取；關閉圖例與重設後等待ResizeObserver完成再量測，避免讀到上一幀。未放寬圖形尺寸、字體或占比門檻。
- node --test "tests/*.test.cjs"：149/149通過。
- 桌面與手機合成fixture截圖：runtime/role4-stable-selected-1366.png、role4-stable-selected-390.png，目視確認。
- 最終隔離HTTP瀏覽器命令：主.venv Python -X utf8 tests/run_web_v2_live.py tests/web-v2-explanation-browser.cjs tests/web-v2-live-browser.cjs；結果及臨時埠釋放記在共用交接。

未更動v1、後端、模型、資料庫或其他角色分支；本輪未執行Python全套／Docker／遠端CI，不沿用舊結果。原8001預覽保留供使用者查看。手機／很長的說明會需要外層往下閱讀，圖形不因展開文字而縮小。本輪沒有新模型或300人資料整合。
