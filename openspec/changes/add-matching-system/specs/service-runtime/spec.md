# Spec Delta

## Purpose

讓 4 位組員在自己的 Windows 電腦上，不論有沒有顯示卡，都能用一個動作啟動完整系統；也讓任何只裝了 Docker 的人，用一個指令就能跑起 demo，並隨時知道服務和各個模型的狀態。

## ADDED Requirements

### Requirement: 一鍵啟動
專案 SHALL 提供一個 Windows 啟動檔。在已安裝依賴套件的電腦上執行它，就會啟動服務和 v2 網頁，不需要另外輸入任何指令。

#### Scenario: 沒有顯示卡的電腦
- **WHEN** 組員在沒有 NVIDIA 顯示卡的電腦上執行啟動檔
- **THEN** 服務在本機啟動，網頁可以打開，並以無 GPU 模式運作

### Requirement: Docker 一個指令啟動
專案 SHALL 提供 Docker 設定，在只安裝了 Docker 的電腦上，執行 `docker compose up` 就能啟動服務和 v2 網頁。容器預設以無 GPU 模式運作；設定了大型語言模型的位址時，SHALL 改連到主機上的模型服務。

#### Scenario: 乾淨的電腦
- **WHEN** 在沒有 Python、沒有顯示卡、只有 Docker 的電腦上執行 `docker compose up`
- **THEN** 服務啟動，API 文件頁和 v2 網頁都能打開，健康檢查顯示無 GPU 模式

#### Scenario: 連到主機的模型服務
- **WHEN** 主機上有模型服務在跑，而且設定裡寫了它的位址
- **THEN** 容器以 GPU 模式運作，新品名的屬性可以被判斷

### Requirement: 從 Hugging Face 取得分類模型
使用 BERT 分類模型、本機卻沒有模型時，服務 SHALL 在啟動時從 Hugging Face 下載設定中指定的模型庫和**固定版本**並保存；之後的啟動 SHALL 直接使用已保存的模型。下載失敗時，服務 SHALL 照常啟動，並在健康檢查中把分類模型標示為 `unavailable`。

#### Scenario: 第一次啟動
- **WHEN** 有網路、本機沒有分類模型時第一次啟動
- **THEN** 服務下載指定版本的模型，健康檢查顯示分類模型為 `bert`

#### Scenario: 第二次啟動
- **WHEN** 服務在已經下載過模型的狀態下重新啟動
- **THEN** 服務沒有再次下載模型

#### Scenario: 下載失敗
- **WHEN** 第一次啟動時沒有網路
- **THEN** 服務照常啟動，健康檢查顯示分類模型為 `unavailable`，即時分類回應 503 `model_unavailable`

### Requirement: 容器不含真實資料與密鑰
Docker 映像檔 MUST NOT 包含真實發票、真實品名、私人設定或密鑰；密鑰 SHALL 在啟動時由環境變數或本機設定檔提供。資料庫和模型 SHALL 存放在容器外的儲存空間，重新建立容器後資料仍然存在。

#### Scenario: 檢查映像檔
- **WHEN** 列出映像檔裡的所有檔案
- **THEN** 找不到 `rawdata/`、`data/`、任何 CSV 或壓縮檔，也找不到 `.env`

#### Scenario: 重建容器
- **WHEN** 使用者註冊並上傳資料後，刪除容器再重新 `docker compose up`
- **THEN** 帳號和資料都還在，模型也不必重新下載

### Requirement: demo 資料自動就緒
demo 模式下，服務以空的資料庫啟動時，SHALL 自動匯入約 300 位假用戶，讓第一次啟動的人馬上就能看到配對結果。

#### Scenario: 面試官第一次啟動
- **WHEN** 在 demo 模式下第一次 `docker compose up`，並用 demo 快速切換成一位假用戶
- **THEN** 這位假用戶的相近和互補清單都有人

### Requirement: GPU 與無 GPU 模式
服務啟動時 SHALL 檢查本機大型語言模型服務是否可用：可用時以 GPU 模式運作；不可用時以無 GPU 模式運作。在無 GPU 模式下，除了判斷新品名的屬性以外，其他功能 MUST 都能正常使用。

#### Scenario: 無 GPU 模式下的完整 demo
- **WHEN** 服務以無 GPU 模式運作
- **THEN** 登入、上傳、分類、品味向量、配對和計算過程都能正常使用，只有新品名的屬性顯示待分析

### Requirement: 健康檢查
系統 SHALL 提供不需要登入的健康檢查，回傳服務狀態、是不是 GPU 模式、是不是 demo 模式，以及目前使用的分類模型（fake、tfidf、embedding、bert，或無法使用時的 unavailable）和屬性模型（fake、qwen，或無 GPU 時的 cache_only）。

#### Scenario: 查詢健康狀態
- **WHEN** 無 GPU 模式下，有人呼叫健康檢查
- **THEN** 回應包含 `status`、`gpu_mode` 為 false、`demo_mode`，以及 `models.attributes` 為 `cache_only`

### Requirement: API 文件頁
服務 SHALL 提供自動產生的 API 文件頁，列出全部 API 的路徑、輸入和輸出，而且可以直接在頁面上試呼叫。

#### Scenario: 打開文件頁
- **WHEN** 服務啟動後打開 API 文件頁
- **THEN** 頁面列出註冊、登入、上傳、進度、即時分類、我的品味、配對、計算過程、健康檢查這些 API

### Requirement: 機密設定不寫在程式裡
用來簽發存取權杖的密鑰 SHALL 從本機設定檔或環境變數讀取，MUST NOT 寫在程式碼或任何放進 git 的檔案裡。缺少密鑰或密鑰短於 32 個字元時，服務 SHALL 拒絕啟動並說明原因。

#### Scenario: 缺少密鑰
- **WHEN** 沒有設定 `JWT_SECRET` 就啟動服務
- **THEN** 服務不啟動，並顯示缺少哪一項設定

#### Scenario: 密鑰太短
- **WHEN** `JWT_SECRET` 只有 16 個字元
- **THEN** 服務不啟動，並說明密鑰至少要 32 個字元

### Requirement: 自動測試不需要模型
專案的自動測試 SHALL 在沒有顯示卡、沒有下載任何模型檔的環境中全部執行；每次 push 到 GitHub 時 SHALL 自動執行全部測試（包含現有的 Python 和 JS 測試），並建置一次 Docker 映像檔。

#### Scenario: GitHub 上的檢查
- **WHEN** 組員 push 一個分支到 GitHub
- **THEN** 自動檢查跑完全部測試、建置好 Docker 映像檔，而且過程中沒有下載任何模型
