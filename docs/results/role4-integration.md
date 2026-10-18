# 角色 4：假模型前後端整合驗證（2026-10-16）

狀態：本機整合已驗證，待 Claude 審核；尚未合併 main、推送或部署。

## 版本與範圍

- 角色 4 原始基準：`8a63b72`。
- 整合角色 1 已提交後端：`324874deef08a4245f951f0a17e59fcb0332d85a`。
- 合併提交：`aef2d4c`，僅 overview 交接段落衝突，保留雙方紀錄；後端程式依原提交帶入。
- 在原 `codex/role4-web-foundation` worktree 執行；測試不使用既有 .env 或資料庫，不安裝共享套件。
- 本批兩個模型均為 fake，GPU 探測指向未提供服務的 loopback 位址，health 確認 `gpu_mode=false`。

## 行為修正

1. 刪除月份後立即讀 profile；若 `recomputing=true`，每兩秒重查，暫時隱藏舊輪廓、月報與配對。期間取消舊讀取、禁止新的配對／explain 查詢；完成後更新目前開啟的配對頁。切換帳號、401 或重新查詢會取消舊輪詢；改名保留正在進行的輪詢，改密碼暫停舊請求後以有效權杖恢復。
2. 關係圖區分「仍有已存向量、目前圖資料為 null」的重新計算中，與完全沒有向量的資料不夠；不可比較時仍能顯示圖形狀態。分數與逐格貢獻直接採 API。
3. demo 設定頁顯示「登出此瀏覽器」，一般帳號顯示「登出所有裝置」。
4. 更新舊瀏覽器測試：profile 端點已存在，正常 fake 分類直接 ready，不能把過去的缺少端點／pending 行為當成現況。

## 實際驗證

合併前 baseline：JS 140／140，Python 213／213。
整合後：JS 145／145，Python 409／409（26.732 秒）。五份瀏覽器腳本全部通過，沒有 pageerror；桌機 1440 px／手機 390 px 檢查無橫向溢出。前端重算／取消請求／圖形缺失測試先失敗、修正後通過。

### 真 HTTP：不攔截或替換 API 回應

`tests/web-v2-live-browser.cjs` 由 `tests/run_web_v2_live.py` 啟動正式 app、路由、背景 worker、SQLite 及 fake 模型載入器，以 Chromium 實際操作：

- 註冊、登入、即時分類的 23 欄。
- 上傳兩個合成月份，各 40 筆有效品項；月報、18 格品味與 80 筆數量。
- 第二位虛構使用者也走正式上傳管線；實際配對卡片、18 格 explain 數字、關係圖與 API 百分比一致。
- 取消刪月份不動資料；確認刪除後重算為 40 筆，月份清單只保留另一個月。
- 改名、改密碼；舊 token 401、新 token 有效。
- 所有裝置登出後另一 session token 401；新密碼可重新登入。
- 錯誤密碼不能刪帳號；正確密碼刪除後無法登入、不再出現在另一人的配對清單，explain 回 404。
- demo 登出不撤銷另一 session 的權杖。

### 教學數字的實際 HTTP 驗收

隔離 DB 另建立兩個僅供數學教學的 demo profiles，向量取自 `scripts/concepts_example.py`，呼叫真實 `/api/matches/2/explain`，核對 1.88／2.29／82%、18 格及 13 格 null。這兩人沒有發票，關係圖應顯示重新計算中；不冒充角色 3 的完整 seed。上述一般使用者的配對與圖形則來自真正上傳管線。

### 契約與錯誤回歸

- `web-v2-recompute-browser.cjs`：控制重算延遲，驗證舊資料隱藏、兩秒輪詢、暫停配對、改名與改密碼成功／失敗仍維持重算等待，以及完成後更新。
- `web-v2-browser.cjs`：真 HTTP 註冊／上傳／profile／分類，另用 fixture 驗證錯誤、月報、XSS 防護與篩選。
- `web-v2-account-browser.cjs`：fixture 覆蓋 409、錯誤密碼、失敗登出、密碼輪替競態、demo 唯讀。
- `web-v2-explanation-browser.cjs`：fixture 覆蓋負分、不可比較、精度、格式錯誤、401 與切換清除。

## 重跑

在角色 4 worktree 根目錄執行，Python 可換成主專案共用虛擬環境的絕對路徑：

```powershell
node --test "tests/*.test.cjs"
python -m unittest discover -s tests
# NODE_PATH 指向已有 Playwright 的 node_modules；
# BROWSER_EXECUTABLE 可指定已有 Chromium，未設定時使用 Playwright 預設。
python -X utf8 tests/run_web_v2_live.py tests/web-v2-live-browser.cjs tests/web-v2-recompute-browser.cjs tests/web-v2-browser.cjs tests/web-v2-account-browser.cjs tests/web-v2-explanation-browser.cjs
openspec validate add-matching-system --strict
```

runner 自動選擇空閒 loopback 埠，每次建立臨時 DB，結束關閉服務並清理；不連接預覽服務。截圖保存在忽略的 `runtime/role4-live-matches-{desktop,mobile}.png`。

## 驗收界線

- 5.8 的核心與 HTTP 數字重現、6.3 的假模型帳號流程可結案。
- 6.1 僅完成假模型／GPU 關閉的 HTTP 子流程；乾淨無顯示卡電腦與一鍵啟動驗收尚未完成，保持未勾選。
- 5.9 的 Docker 與 GitHub 素材線上驗收仍未完成；README 的 GIF 仍標示模擬 API。
- 真 BERT／Qwen、300 人完整 seed、Docker、CI、遠端環境未在本批驗收。
- 內部 Codex 複查不是 Claude 審核；正式結論須由 Claude 對送審 HEAD 追加共用交接紀錄。

## 內部複查修正

獨立 Codex 複查發現重算時改名會取消輪詢，讓配對可提前讀舊值；已加入瀏覽器案例，確認原版失敗後修正通過。也覆蓋同時改密碼成功／失敗的恢復與新權杖使用。這項複查與 Claude 正式審核分開記錄。
