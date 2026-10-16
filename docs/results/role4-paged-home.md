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

## 章節式捲動調整（2026-10-16）

工作 ID R4-CHAPTER-SCROLL-20261016；比較基準 e6626cb，待 Claude 審核，未合併。
使用者提供 https://www.apple.com/tw/shop/buy-iphone/iphone-duo 作參考。
實際觀察固定導覽、大區塊與分段內容；本次取其閱讀節奏，未複製圖片、商標或原站程式。

- 首頁保留品味／月報兩屏，加入固定 01 品味／02 月報章節按鈕，捲動時同步 aria-current。
- 能放進一屏時，以 680ms 緩入緩出翻頁、輕量淡入淡出與桌機留白強調章節；快速切按鈕最後一次操作優先。
- PageUp／PageDown／Home／End 在頁面容器焦點下翻頁；選單與輸入不攔截。觸控、超高內容使用原生捲動。
- 減少動態效果偏好停用轉場與淡化。resize、觸控、切換工作區、資料清理可停止進行中的動畫。

本批驗證：
- node --test "tests/*.test.cjs"：145/145 通過。首次失敗源於 Node VM 測試替身缺少 ResizeObserver、matchMedia 與動畫排程，補齊後通過；實際操作另外由 Chromium 驗證。
- python -X utf8 tests/run_web_v2_live.py tests/web-v2-pages-browser.cjs tests/web-v2-browser.cjs tests/web-v2-recompute-browser.cjs：3 組通過。
- 分頁測試含四尺寸18格完整、120px滾輪翻頁、目前章節、連續按鈕切換、鍵盤、五月報表金額、Escape、舊分類路由、320px超高頁與減少動態效果；既有重算與身分失效流程回歸。
- 8001 現有 fake 預覽用 CUA 人工確認，頁面固定導航與月報全屏停靠正常。
- 本批未跑 Python 全套或真模型、未變更後端與 v1，未更新歷史 GIF。測試臨時埠 57228 已釋放，原預覽服務保留。

- 補驗 python -X utf8 tests/run_web_v2_live.py tests/web-v2-pages-browser.cjs：通過；轉場250ms後resize到320×568、離開至配對再回首頁皆可繼續操作，臨時埠62278已釋放。
- openspec validate add-matching-system --strict、git diff --check、v1差異檢查通過。
- 獨立 Codex 靜態複查無阻擋問題；子代理獨立 Chromium 啟動受沙箱限制，因此動態證據以主代理上列實跑為準，非 Claude 正式審核。
