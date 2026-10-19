# 照 README 從零啟動驗收（2026-10-19，任務 2.14、6.4）

驗收對象：main 的 ea11f67（PR #13 合併後）。使用者要求後，由 Claude 在**另一台電腦**上從 GitHub 重新 clone，完全照 README 的指令走 Docker 與虛擬環境兩種啟動方式。

這台電腦和 10/18 整合驗收用的開發電腦不同：Windows 10 Pro 19045、GTX 1050 Ti、Docker 29.7.2、Compose v5.4.0、Python 3.12.10。它**不是只裝了 Docker 的電腦**（另外裝有 Python、Node 等工具，Docker 裡也有其他專案的映像檔，包括 `python:3.12-slim`），但開始前沒有任何 receipt 的映像檔、volume、`.venv`、`.env` 或模型檔，也沒有登入 Hugging Face；clone 放在暫存資料夾，沒有用到主資料夾的任何檔案。執行的是 Claude，不是組員本人。

所有資料都是虛構的：示範帳號來自 seed；測試帳號由驗收腳本隨機建立，密碼不寫進任何紀錄；上傳的 CSV 是 `scripts.make_demo_upload` 產生的「示範…」品名。

## 結果一覽

| 項目 | 結果 | 對應任務 |
|---|---|---|
| Docker：`docker compose up --build -d`（預設 fake／qwen） | 通過 | 2.14、6.4 |
| Docker：示範帳號自動匯入、API 走完配對與計算過程 | 通過 | 6.4 |
| Docker：網頁 demo 快速切換 → 配對 → 連線圖 → 計算過程 | 通過 | 6.4 |
| Docker：`docker compose down` → `up -d` 後資料仍在 | 通過 | 6.4 |
| 虛擬環境：建 `.venv`、安裝 requirements.txt、start.bat | 通過 | 2.14 |
| 模型自動下載：全新 volume 疊 `docker-compose.category.yml` 下載 BERT | 通過 | 6.4 |
| 不帶權杖重啟：模型與資料都還在 | 通過 | 6.4 |

## 驗收腳本

一支只用標準函式庫的 Python 腳本（放在暫存資料夾，沒有提交），經真正的 HTTP 打服務，只印狀態和數字：

1. `/api/health`；`/api/auth/demo-users` 是 300 位
2. 第一位與最後一位示範帳號 demo 登入：`/api/me/profile` 是 ready、`pending_attributes` 0；相似與互補清單都有人；對清單第一位的 `/explain` 回 200、18 格
3. 註冊新帳號、上傳 2026-05 和 2026-06 兩個月（各 40 行），等背景工作 done；自己的 profile ready、配對清單有人、`/explain` 回 200、18 格
4. 重建後加 `--recheck`：同一個帳號用原密碼登入，兩個月與配對都還在

## Docker（預設設定）

在 clone 的根目錄，沒有 `.env`，也沒有設定任何模型環境變數：

```powershell
docker compose up --build -d
```

- 建置加啟動 139 秒結束，映像檔 1.67 GB。基底映像 `python:3.12-slim` 這台電腦本來就有，所以沒有計入下載它的時間；真正只裝 Docker 的電腦第一次會多花下載基底映像的時間
- 記錄寫 `demo users: 300 in all, 300 added, purchases and profiles rewritten`；health 是 `demo_mode: true`、`models: {category: fake, attributes: cache_only}`、`gpu_mode: false`（這台沒有開 llama-server）
- 驗收腳本全部通過：示範第一位 ready、待分析 0，相似 176 位（顯示 5）、互補 6 位（顯示 5）；最後一位相似 161 位、互補 3 位；新帳號兩個月都 done，profile ready、待分析 0，相似 204 位
- **網頁**（內建瀏覽器，`http://127.0.0.1:8000/web/`）：登入頁的示範選單有 300 位；選「省錢上班族 A」→ 進入體驗 → 二選一首頁 → 跟陌生人配對品味（「176 位品味相似度 +30% 以上，顯示前 5 位」）→ 點「省錢上班族 13」→ 連線圖中間 +97% → 查看計算過程（內積、分母、相似度三步，18 格計算明細）；console 沒有錯誤
- **重建後資料仍在**：`docker compose down`（不加 `-v`）再 `docker compose up -d`，6 秒後回應，記錄寫 `0 added (already complete)`；`--recheck` 全部通過

## 虛擬環境（start.bat）

照 README「Windows Python 啟動」：

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

安裝 41 秒完成。先停掉 Docker 讓出 8000 埠，再執行 start.bat：

- 它印出「已建立 .env（含一組新的 JWT_SECRET）」，`.env` 裡是 `DEMO_MODE=1`、`CATEGORY_MODEL=fake`、`ATTRIBUTES_MODEL=qwen`，JWT_SECRET 超過 32 字元（只檢查長度，沒有印出）
- seed 結果 `users 300, profiles 300, added_users 300`；32 秒後 `/api/health` 回應（`cache_only`）
- 同一支驗收腳本全部通過（數字和 Docker 相同）

## 模型自動下載（受保護的 Hugging Face Space）

使用者在這台電腦用 `hf auth login` 自己輸入權杖；Claude 沒有讀取或印出權杖，只把權杖檔的路徑交給 Compose。用新的專案名稱讓 db 和 models 兩個 volume 都是全新的（等同沒有模型的電腦）：

```powershell
$env:CATEGORY_MODEL_REPO = "lee851104/receipt-model-lab"
$env:CATEGORY_MODEL_REVISION = "29b655b96b4ced268bb0c3994e901c72dfd65420"
$env:CATEGORY_MODEL_SHA256 = "16997425a9b36629469d60f506d52c2771bab1e6f3a3ea1465c2c0a316fa3e79"
$env:HF_TOKEN_FILE = "<本機的 Hugging Face 權杖檔>"
docker compose -p receipt-bert -f docker-compose.yml -f docker-compose.category.yml up --build -d
```

- 67 秒後 health 回應：`models: {category: bert, attributes: cache_only}`
- 容器裡 `/models/category` 有 7 個項目（檔案與資料夾）、共約 410 MB；`verified_manifest` 通過，`model.safetensors` 的 SHA-256 和設定的一致；torch 是 CPU 版（`cuda_build: null`）
- 驗收腳本全部通過；BERT 分類下新帳號的相似清單是 258 位

**不帶權杖重啟**：清掉 `CATEGORY_MODEL_REPO`、`CATEGORY_MODEL_REVISION`、`HF_TOKEN_FILE`，只設 `CATEGORY_MODEL=bert` 和 SHA，不疊 category 設定：

```powershell
docker compose -p receipt-bert up -d
```

容器重建（設定改變），沒有掛權杖，只有 `/data` 和 `/models` 兩個 volume；9 秒後 health 仍是 `bert`，記錄寫 `0 added (already complete)`，`--recheck` 全部通過。

## 照著 README 時發現的問題

- README 的 Docker 段落還寫著「v2 尚未合併 main（10/18：……還沒有推送）」，但 v2 已經在 main，這次就是從 main clone 的。本次已改掉
- 用 `docker-compose.category.yml` 啟動的專案，停止時若沒有同時設定那幾個變數，`docker compose -f docker-compose.yml -f docker-compose.category.yml down` 會因為 `${...:?}` 必填而報錯；只用基本設定 `docker compose -p <專案> down` 就可以停。README 沒有寫，這次沒有改
- `docs/results/classification-service.md` 第 75 行還寫「`CATEGORY_MODEL_REPO`、`CATEGORY_MODEL_REVISION` 留空……不要填入 Space ID」，和 README 與這次的實測（容器從 Space 下載）不一致，屬於角色 2 的文件，這次沒有改

## 留在這台電腦上的東西

驗收的 clone 和 `.venv` 在暫存資料夾。Docker 留下兩個專案的 volume（`receipt_db`、`receipt_models`、`receipt-bert_db`、`receipt-bert_models`，後者含下載的模型）供複查，容器都已停止。不需要時可以在 clone 裡執行 `docker compose down -v` 與 `docker compose -p receipt-bert down -v` 刪除。
