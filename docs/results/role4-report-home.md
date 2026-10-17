# 角色 4：月報首頁與動態文字雲

日期：2026-10-17。原 worktree：`C:/Users/User/.codex/worktrees/receipt-role4/receipt`；分支 `codex/role4-web-foundation`，比較基準 `226d2c7`。實作已驗證，待 Claude 審核；未推送、未合併。

## 使用者要求與實作

- 移除「我的品味」首頁及另外開啟月報的視窗，直接呈現「我的月報」。上傳與帳號管理仍在設定。
- 首屏是金額／發票／消費日摘要、類別金額占比、點選類別後的品項排行。同類同名品項加總，預設前六項；其餘項數及金額有揭露，可展開全部。原始表格預設收合。
- 月報五章：品項、節奏、文字雲、日期、月比較。保留章節停靠、緩動轉場、月份同步；短螢幕或較長內容可原生捲動，不裁切。
- 參考使用者照片的縱深與光感，以既有深灰、粉紅、薄荷及類別配色做慢速漂浮文字與柔光。照片不足以確認原作動畫，沒有複製其動作。
- 文字雲保留頻率大小及點選日期／金額功能。播放／暫停選擇只保留於分頁；首次尊重 reduced-motion，離開可視區、hover／focus 時暫停。
- profile 更新或身分失效清除 iframe，品名以 textContent 呈現。後端、配對公式與 v1 不變。

## 本輪實際驗證

命令均於原角色4 worktree；Python 使用主資料夾 .venv，NODE_PATH 指向既有 Codex runtime，Chromium 使用既有 ms-playwright chromium-1208。沒有安裝套件。

1. `node --test "tests/*.test.cjs"`：147/147 通過。
2. `python -X utf8 tests/run_web_v2_live.py tests/web-v2-pages-browser.cjs tests/web-v2-browser.cjs tests/web-v2-recompute-browser.cjs`：3 組通過，fake 模型／臨時資料庫，port 56719 已釋放。
3. `python -X utf8 tests/run_web_v2_live.py tests/web-v2-pages-browser.cjs tests/web-v2-live-browser.cjs tests/web-v2-account-browser.cjs tests/web-v2-explanation-browser.cjs`：4 組通過，port 62537 已釋放。
4. 1366×768、1024×640、558×510、390×844 首屏圖表可見且無橫向溢出；320×568 保留長內容捲動。桌機滾輪切章、月份同步、分類點選、前六項／全部、空月份、注入字串純文字、文字雲播放／暫停與 transform 變化均通過。
5. 實際 HTTP／瀏覽器回歸：上傳兩月份、重算、配對與正負／不足資料解釋、改名／改密碼／登出／刪月份／刪測試帳號及401清理通過。
6. CUA 在原 8001 的虛構示範帳號確認直接月報、第一屏完整圖表、文字雲與播放控制；使用者系統偏好 reduce，經畫面按鈕開啟動態，未修改系統設定。
7. 初次瀏覽器測試因 frame-status 尚未建立就判定 hidden 而提前取值；改為先等資料後通過。實際預覽發現舊 model-note flex-basis 擠壓 iframe，已限制為固定內容高度並以上列尺寸重驗。

獨立 Codex 靜態複查無阻擋問題，另跑聚合測試2/2與diff檢查；其額外 Chromium 檢查因模組解析失敗未執行，動態證據以上列主代理測試為準。此非 Claude 正式審核。

規格與邊界檢查：`openspec.cmd validate add-matching-system --strict`、`git diff --check` 通過；`git diff --quiet 226d2c7 -- src/web invoice-insights.html` exit 0。

## 範圍與下一步

本輪未執行 Python 全套、真模型、Docker、CI 或完整300人seed。歷史GIF保持10/15版本並註明舊版，錄製腳本已配合首頁同步但未重新錄製；OpenSpec 5.9 不因此結案。原8001保留，無GPU、私人資料或.env變更。

請 Claude 審核本次提交相對226d2c7的首頁替換、品項聚合、動態偏好與iframe清理。使用者可於原預覽體驗速度與畫面；Codex依回饋調整。


## 2026-10-17：各頁比例與動態速度修正

基準 cebc1c3，工作ID R4-REPORT-PROPORTION-20261017，依使用者「每頁比例怪、動態不明顯，稍微快一點」調整；仍在原角色4 worktree。

- 移除重複的視覺月報標題列（保留可及性標題），重新載入移到功能導覽右側，增加內容高度。
- 新增 report-layout.css，依月報可用容器高度控制圖表比例及斷點，限制桌機閱讀寬度；五章預設同屏高。節奏解讀、雲計數說明與完整月比較表改為可展開，資料未刪除。
- 短視窗日曆保留足夠圖高，所有圓以相同比例縮放；文字雲／日期圖旁放小型讀值區，手機改上下排列。密集類別自動長高並原生捲動，避免裁切或撐開橫向寬度。
- 漂浮週期由8–14秒改4.8–6.3秒；水平／垂直幅度約加倍，新增5.5秒柔光框呼吸。滑鼠或鍵盤只暫停當前詞，其他詞與光暈繼續；整區離開可視範圍及手動暫停維持有效，首次仍尊重減少動態偏好。
- 新增失敗後修復的四尺寸 × 五章完整高度回歸、11類文字雲邊界與手機橫向溢出檢查、動畫時長／單詞hover暫停檢查。實際畫面另找出舊手機折行與日曆過扁問題，已修正後重驗。

本次最終驗證（2026-10-17）：

1. 主.venv/Scripts/python.exe -X utf8 tests/run_web_v2_live.py tests/web-v2-pages-browser.cjs tests/web-v2-live-browser.cjs：2組通過，port49607釋放。包括1366×768、1024×640、558×510、390×844五章單屏，320×568密集資料可讀；實際fake後端上傳、月報、配對、帳號修改／刪除與401清理。
2. node --test "tests/*.test.cjs"：147/147通過。
3. openspec.cmd validate add-matching-system --strict、git diff --check通過；git diff --quiet cebc1c3 -- src/web invoice-insights.html exit0。
4. CUA檢查原尺寸及桌機／手機；最終視窗可用高度522px，五個預設章節皆約522px，文字雲4.8秒及cloud-light生效。圖存本聊天visualizations/role4-report-proportions.png，預覽留在文字雲播放中，臨時尺寸覆寫已復原。
5. 續作時原8001已停止，先啟動一般入口後發現它使用原app.db的40位舊demo，遂只停止本次自建程序2932/8524，改用既有 runtime/role4_preview.py 與 data/role4-preview-20261016.db。三位虛構示範月報恢復，沒有重建或刪除資料庫；啟動器PID23312（實際listener另於交接核對）。

限制：本輪未跑Python全套、真模型、Docker、CI或重錄GIF；僅前端比例與動態調整，無GPU、依賴、後端或v1變更。待Claude正式審核，未推送／未合併。
