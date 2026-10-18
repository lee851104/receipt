# 角色 4：連線圖填滿可用高度

> 歷史驗證紀錄：此版面已由 [滿版連線圖](role4-network-fullscreen.md) 取代；下列尺寸與捲動敘述只適用於當時提交。

2026-10-18，基準 1ba1ce4；待 Claude 審核，本機修改，未推送或整合。

使用者要求減少線圖上下留白，盡量同頁看清楚。桌面圖不再固定 1700×600：根據實際 canvas 比例展開扇形節點與連線，文字、圓點與分數保留等比，分數隨新中心定位。ResizeObserver 在實際尺寸改變時重排，保留選取；選線／訊號不改圖高或 viewBox。手機沿用原直式圖，長說明由外層頁面捲動。

## 本次驗證

- RED：1440×1000 原圖垂直占比 58.8%，未達 82% 門檻。
- GREEN：1440×1000 占比 92.1%；1920×1080 為 92.7%；1366×768 為 89.3%；1024×640 為 89.4%。字級不縮小，文字未裁切。
- 加上 390×844、320×568 共六尺寸，線段及訊號選取前後圖高差 <2px、scale 差 <.002、viewBox 相同；無 iframe 內捲軸，桌面圖和解讀同頁。
- node --test "tests/*.test.cjs"：149/149。
- 主 .venv Python -X utf8 tests/run_web_v2_live.py tests/web-v2-explanation-browser.cjs tests/web-v2-live-browser.cjs：全通過；fake/fake、獨立暫存 DB、PID 31120／port 60451 已釋放。實際 HTTP 登入、80 筆測試上傳、月報、配對 18 格、帳號流程通過。
- runtime/role4-fill-browser.log、role4-fill-node.log；runtime/role4-fill-desktop.png 與 role4-stable-selected-desktop.png 為本次合成 fixture 畫面。
- 原 8001 預覽已重載至 network.html?v=20261018-fill1，晨光 × 青禾；未重建資料庫。

v1／後端／模型未改。本輪未跑 Python 全套、Docker、遠端 CI 或真模型。下一步 Claude 審核此提交與前一個 1ba1ce4，再由角色 1 整合。
