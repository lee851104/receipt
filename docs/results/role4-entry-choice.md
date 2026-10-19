# 登入後兩個選項入口

2026-10-17；R4-ENTRY-CHOICE-20261017；基準55d9ef4；待Claude審核，未整合／未推送。

依使用者指定，登入後預設 #home 顯示兩張大按鈕：「看自己的品味」→現有月報、「跟陌生人配對品味」→現有配對。桌面左右並排，手機上下；深色基底，粉紅收據與粉紅／藍色連線圖示。入口隱藏功能導覽，只呈現兩項選擇；設定仍在右上角。選擇前不查詢月報／配對，功能頁提供返回選擇，既有有效深連結刷新仍保留功能。

原月報、配對、上傳與帳號流程不變。大框為原生button，Enter／Space可啟動，焦點轉到功能標題；密碼更新期間同樣禁止入口操作。極短視窗使用safe center避免上方內容不可達。文案「品味」指現有月報，沒有恢復先前移除的獨立品味特質頁。

修改：src/web_v2/index.html、styles.css、workspace-ui.js、app.js；tests/web-v2-navigation.cjs、web-v2-pages-browser.cjs、web-v2-live-browser.cjs、web-v2-page.test.cjs；web-app/spec.md、本文件。

實際驗證（原角色4worktree）：

1. 主.venv/Scripts/python.exe -X utf8 tests/run_web_v2_live.py tests/web-v2-live-browser.cjs tests/web-v2-pages-browser.cjs tests/web-v2-explanation-browser.cjs：3組通過，61184釋放。真HTTP／正式API／fake模型／臨時DB登入、上傳、配對、18格、帳號；另外契約替身驗證月報五章、配對結果／單一捲動。
2. 補短螢幕排列後，同runner跑live-browser、account-browser、recompute-browser共3組通過，64558釋放。入口1366×768、1024×640、390×844、320×568、320×453兩框均完整可見；真登入與demo均進入口、鍵盤選擇、返回／另一選項、深連結刷新通過；帳號更新與重算導覽回歸通過。
3. node --test "tests/*.test.cjs"：148/148通過。初次兩個舊單元案例仍預期登入直接#profile／自動查詢，按最新需求改為#home且不預載，401案例先選入月報再確認失效清除，重跑全通過。
4. node --check src/web_v2/workspace-ui.js 與app.js通過。
5. CUA原8001虛構帳號實際返回選擇，確認兩選項；短窄畫面可完整呈現，桌面並排與原配色保持。截圖存本聊天visualizations/role4-entry-choice.png，臨時尺寸還原，留#home。

本輪未執行Python全套、真模型、Docker、CI；未改後端／DB／環境／依賴／GPU，原8001未重啟。Claude請審核登入後導覽、延遲載入、鍵盤焦點與短視窗版面，指定commit回覆。

規格／邊界：openspec.cmd validate add-matching-system --strict、git diff --check 通過；git diff --quiet 55d9ef4 -- src/web invoice-insights.html exit0。
