# 角色 4：移除分類介面與整屏首頁

2026-10-16；工作 ID R4-PAGED-HOME-20261016。
原 worktree／codex/role4-web-foundation；比較基準 443bd82。
實作與本機驗證完成，待 Claude 審核，未推送／合併主分支。

## 使用流程

前端分類入口、表單、結果 DOM 與事件全部移除；舊 #classify 導回首頁。後端分類 API、發票分類管線與核心契約測試保留，未修改別的角色程式。

登入首頁第一屏完整呈現 18 格品味與頁尾操作，第二屏呈現所選月份涵蓋金額、去重發票張數、有紀錄日數及類別金額。原完整月報改成明確點開的閱讀視窗，帶入摘要所選月份，Escape 關閉並回到按鈕。重算、失效與切換帳號會清理舊資料。

一般滾輪在能容納一屏的頁面翻到相鄰一頁，累積門檻與手勢抑制避免觸控板慣性連翻；Ctrl 縮放、水平、選單與過高內容保留原生處理。觸控用原生 scroll snap，另有上下頁按鈕。低高度／放大時保留可捲動內容，不能以裁切換取一屏。

## 本次驗證

在角色 4 worktree，Python 使用主專案 .venv/Scripts/python.exe：
- node --test "tests/*.test.cjs"：145/145。
- python -X utf8 tests/run_web_v2_live.py tests/web-v2-live-browser.cjs tests/web-v2-browser.cjs tests/web-v2-account-browser.cjs tests/web-v2-explanation-browser.cjs tests/web-v2-recompute-browser.cjs tests/web-v2-pages-browser.cjs：6 組通過。
- python -X utf8 tests/run_web_v2_live.py tests/web-v2-pages-browser.cjs scripts/capture_v2_demo.cjs：分頁通過、錄製 9 幕虛構契約畫面。
- openspec validate add-matching-system --strict：通過。
- git diff --check：通過；git diff --quiet 443bd82 -- src/web invoice-insights.html：exit 0，v1 未變。

分頁檢查：1366×768、1024×640、558×510、390×844 的 18 格與頁尾都在首屏；320×568 與 reduced motion 仍可捲動並操作月報，無橫向溢出。一般 120px 滾輪可翻頁；摘要切月份的金額正確，完整報表跟隨 2026-05；Escape、舊網址回首頁通過。原先上傳、兩月月報、配對計算、帳號刪月／密碼輪替／登出／刪帳號與重算競態均回歸。

新增驗證先在舊版確認分類元素仍存在而失敗；實作後通過。小幅滾輪測試曾失敗（原生 snap 吸回首屏），針對完整一屏補上手勢翻頁後通過。錄影腳本的字幕曾攔住按鈕，改為 pointer-events:none 後通過。服務錯誤提示採 flex 讓出空間，不再擠掉頁底。

獨立 Codex 複查沒有阻擋問題；另確認服務提示、320×568 超高頁原生捲動、月份帶入、Escape焦點，以及 Ctrl／水平／選單事件不攔截。不是 Claude 正式審核。

CUA 實際查看原 8001 預覽：分類元素 0、品味 18 格，月報摘要有資料，兩頁截圖存本聊天視覺化資料夾。瀏覽器最後停在 #profile。

## 資源與界線

測試均用假模型／隔離 DB／臨時埠，結束已釋放。保留原 127.0.0.1:8001／PID30772、三個虛構帳號與獨立預覽 DB，未改 .env、重啟服務或占 GPU。

本次未執行 Python 全套單元測試。真模型、300 人 seed、Docker／CI、GitHub 素材未驗收；本批未合併角色1最新 models。README 舊 GIF 已標明歷史版，尚未重建，本次以實際介面與新版錄製腳本為準。5.5 標註依使用者指示退休，5.9 仍待驗收。
