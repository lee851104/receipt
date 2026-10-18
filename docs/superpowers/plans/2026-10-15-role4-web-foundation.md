# 角色 4 第一批實作計畫

**Goal:** 在獨立 worktree 完成可連現有 FastAPI 的 v2 登入、註冊、demo 切換與品名分類。
**Spec:** docs/team/overview.md 第 5、13 節；openspec/changes/add-matching-system/specs/web-app/spec.md。
**Architecture:** 原生 HTML/CSS/JS，沒有打包工具。API、登入狀態、分類呈現與 DOM 操作分開；模組可用 node:test 驗證。延續 v1 深色與珊瑚紅色系。

## 範圍與決定

- 使用者 2026-10-15 確認「第一批，用 worktree 方式」。實作 tasks 5.1–5.3，以及 5.5 的第 1 週版本。
- 依 overview 5.5 與 13.2，pending 顯示「待分析」，不輪詢；5.5 保持未勾選，待後端背景排程就緒才完成最終規格。
- token 放 sessionStorage，密碼不保存；分頁關閉即清除。401 清除目前身分、結果並回登入。過期與切換身分後的舊請求不得覆蓋新畫面。
- 目前沒有登出 API；提供「切換帳號」清除本分頁狀態，不宣稱撤銷其他裝置權杖。真正登出屬於後續 5.10。
- v1 檔案、後端、共用套件不改；測試只用虛構資料。開發伺服器使用 8001 與 worktree 自己的 SQLite。

## 工作順序

- [x] API 與 session 模組：先寫權杖、401、錯誤碼／422／非 JSON、過期及舊請求測試，再實作。
- [x] 登入與分類控制器：先寫表單編碼、註冊、demo 開關、失敗、null/false/0、請求競態測試，再實作。
- [x] v2 入口：建立響應式登入／註冊、demo 選單、分類結果與 23 欄屬性，接上控制器。
- [x] 執行全部 Python／JS 測試，實際瀏覽器操作桌機與手機版，確認 v1 diff 為空。
- [x] 更新 OpenSpec 完成項目與角色交接，留下第一批交付與限制。

## 驗證紀錄

27 個新增 JS 測試涵蓋 API、流程與 DOM 整合；全部 JS 109 個、Python 154 個。瀏覽器以獨立本機 API 驗證主要操作，pending 使用假回應。獨立審查的兩個競態問題已補測試修正。詳細交接見 overview 13.3。
