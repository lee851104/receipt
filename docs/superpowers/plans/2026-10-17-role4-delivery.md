# 角色4展示與交付驗收計畫
**Goal:** 完成 add-matching-system 5.9，將新版展示與可重現 Docker 操作交付到既有 GitHub 角色4分支。
**Spec:** openspec/changes/add-matching-system/tasks.md 5.9；web-app/spec.md；service-runtime/spec.md。
**Architecture:** 合併角色1已交付容器與CI，保留角色4介面；展示只用公開合成fixture；Docker正式API使用隔離volume及虛構CSV。
**Tech Stack:** FastAPI、SQLite、Docker Compose、Playwright、Pillow、GitHub。
**執行:** 由目前工作者依序執行，不派新聊天或改動其他worktree。

- [x] 合併role1 d1ed44a，overview衝突保留兩方增量。
- [ ] 修復舊capture腳本（登入後二選一、文字雲、放大配對圖），產生9幕標示模擬API的GIF並視覺檢查。
- [ ] 從追蹤來源建立乾淨Docker context、新project/volume；驗證啟動、註冊、上傳、月報、配對、計算及重建保留。
- [ ] README說明實際啟動、資料持久化、已知seed/真模型整合界線；只勾角色4 5.9，不代勾6.4。
- [ ] 本機Python/Node回歸、OpenSpec、容器內容與Git待推送隱私檢查。
- [ ] 推送角色4分支；驗證GitHub README/GIF/相對連結與既有v1網址，核對CI，追加唯一交接供Claude審核。

**驗證重點:** 不使用私人來源、舊GIF/舊selector不混入；容器不含秘密或資料；沒有.env仍可預設啟動；停止後保留volume；GitHub展示不宣稱真模型/300人全系統完成。
