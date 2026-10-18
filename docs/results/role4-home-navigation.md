# 角色 4 首頁與導覽調整

日期：2026-10-16。工作 ID：R4-HOME-NAV-20261016。基準：85983c2。
分支：codex/role4-web-foundation。實作與本機驗證完成，待 Claude 審核；未推送或合併主分支。

## 行為

- 登入／無功能網址的入口預設我的品味與月報，保留有效功能深連結。
- 主導覽只保留我的品味與月報、找到同好；右上角設定收納上傳檔案、帳號設定、品名分類、切換帳號。
- 選單支援鍵盤開啟、Escape 返回觸發鈕、外部點擊、焦點離開與選項選取時收合。
- 空首頁提示設定 → 上傳檔案。設定頁與上傳處理功能維持原契約。
- 點配對卡才取得 explain 資料並顯示關係圖；計算面板預設收合且尚未渲染，點 summary 才建立明細。更換對象／篩選／身分會清除舊內容。
- 改動的 CSS／JS 加版本查詢參數，避免已開啟的預覽混用舊快取。未修改 API、模型、v1。

## 本次驗證

在角色 4 worktree 執行，Python 為主專案 .venv/Scripts/python.exe：
- node --test "tests/*.test.cjs"：145/145 通過。
- python -X utf8 tests/run_web_v2_live.py tests/web-v2-live-browser.cjs tests/web-v2-browser.cjs tests/web-v2-account-browser.cjs tests/web-v2-explanation-browser.cjs tests/web-v2-recompute-browser.cjs：五組通過。
- 加入靜態檔版本後重跑 python -X utf8 tests/run_web_v2_live.py tests/web-v2-live-browser.cjs scripts/capture_v2_demo.cjs：真 API 全流程通過，產出 10 幕合成契約截圖。
- openspec validate add-matching-system --strict：通過。
- git diff --check：通過；git diff --quiet 85983c2 -- src/web invoice-insights.html：exit 0，v1 未變。
- CUA 實際確認預覽首頁、右上角設定、配對明細預設收合且點開後渲染。
- Codex 獨立只讀複查：未發現阻擋缺陷，不等於 Claude 正式審核。

新增驗證先在舊版本失敗（profile-panel 仍隱藏），實作後通過。首次 Node 回歸發現測試用 DOM 缺少 document.addEventListener/querySelector，補齊測試替身後通過。預覽曾混用舊資源，加入版本後重新載入確認。

瀏覽器涵蓋新首頁與空首頁、重新整理、兩項主導覽、設定開關及手機不溢出、明細延後渲染與既有錯誤清除；同時回歸兩月上傳、刪月重算、名稱／密碼／登出／刪帳號。後端使用 fake 模型與臨時 SQLite。測試埠 53744（預期失敗）、62163、49448 都已釋放。

## 限制與交接

本次未執行 Python 全套單元測試；不沿用前回 409 項作本次結果。沒有真模型、GPU、Docker、CI 或 GitHub 線上驗收。5.9 仍待。README 舊 GIF 已明確標註為 10/15 導覽；重錄腳本已更新，但未替換 GIF。

沿用 127.0.0.1:8001／PID30772 的專用預覽、fake/fake 與三位虛構示範帳號，未重啟服務、修改 .env 或原資料。請 Claude 依本批提交審核上述導覽、收合及帳號競態回歸。
