# 受保護BERT下載與Docker驗收

狀態（2026-10-17）：下載器及隔離測試完成；實際認證下載、Docker Linux啟動尚待環境與本機登入，不能當作已驗收。原test未讀。

## 來源與憑證

沿用Protected Space `lee851104/receipt-model-lab` 的 `models/bert/`。既有交付記錄revision為 `29b655b96b4ced268bb0c3994e901c72dfd65420`；本輪匿名API401，需登入後確認該revision可取。權重SHA256固定為 `16997425a9b36629469d60f506d52c2771bab1e6f3a3ea1465c2c0a316fa3e79`。

在本機執行 `hf auth login`，由使用者直接貼入只讀token。不要貼在聊天、CLI參數、README、.env或Git。也可用 `HF_TOKEN_FILE` 指向Git外的既有token檔。下載器不改寫token；Docker只掛載該檔案為唯讀runtime secret，沒有build ARG或token值環境變數。

Protected Space必須明確用repo_type=space；不是public model repo。下載器只取得models/manifest.json，解析BERT白名單後個別下載；不下載整個Space、TF-IDF詞彙或原始資料。固定40位revision與64位模型hash，逐檔hash/標籤/完整model驗證通過後才發布新目錄。下載失敗清掉本次staging，既有不完整／不相關目錄不覆寫。

官方介面說明：[HF下載指南](https://huggingface.co/docs/huggingface_hub/en/guides/download)、[Protected Spaces](https://huggingface.co/docs/hub/spaces-overview)。

## 本機直接下載

在角色2repo根目錄，使用含requirements-docker.txt的CPU環境：

```powershell
& 'C:/Users/User/Desktop/AI_project/receipt/data/role2/service-runtime-20261017/Scripts/python.exe' -m scripts.download_category_model --repo lee851104/receipt-model-lab --revision 29b655b96b4ced268bb0c3994e901c72dfd65420 --sha256 16997425a9b36629469d60f506d52c2771bab1e6f3a3ea1465c2c0a316fa3e79 --destination C:/Users/User/Desktop/AI_project/receipt/data/role2/remote-category-NEW
```

目的必須不存在，或已是完整且符合指定權重hash的模型。沒有憑證的新目錄下載會失敗；已驗證本機模型可以離線重用。不完整資料夾應換新的版本路徑，不要刪既有私人資料來重試。

## Docker Compose（待本機daemon驗收）

先完成Docker Desktop與WSL2安裝。原Dockerfile使用CPU套件，以下只啟動本專案隔離的Compose project；使用者原本的其他服務不變。若8000已占用，先用獨立override改成可用的loopback埠，勿停止別的角色服務。

```powershell
$env:CATEGORY_MODEL_REPO = 'lee851104/receipt-model-lab'
$env:CATEGORY_MODEL_REVISION = '29b655b96b4ced268bb0c3994e901c72dfd65420'
$env:CATEGORY_MODEL_SHA256 = '16997425a9b36629469d60f506d52c2771bab1e6f3a3ea1465c2c0a316fa3e79'
$env:HF_TOKEN_FILE = Join-Path $env:USERPROFILE '.cache/huggingface/token'
docker compose -p receipt-role2-acceptance -f docker-compose.yml -f docker-compose.category.yml up --build
```

`docker-compose.category.yml` 設CATEGORY_MODEL=bert、CATEGORY_MODEL_REPO_TYPE=space和HF_TOKEN_FILE=/run/secrets/hf_token；密鑰檔案不進image。CATEGORY_MODEL_SHA256也在category_backend啟動時驗證，錯的權重不會因為資料夾存在而啟用。原public model下載路徑仍供既有相容用途，這次Protected部署必須使用Space路徑。

## 實際證據與尚待項目

- 新增7項測試先RED、後PASS；完整467/467（28.498秒）。測試使用虛構權重與受控下載替身，不宣稱遠端成功。
- 已驗證無效revision／SHA／repo於網路前拒絕；manifest path traversal/額外資料檔/錯類別/hash拒絕；中斷、無token、既有不相關檔保留；錯誤訊息不帶憑證。
- Docker Desktop官方安裝包數位簽章Valid/Docker Inc，per-user install exit0；CLI Docker29.8.2。WSL與daemon仍待啟用。
- 使用者選擇本機Docker，未新建遠端Space。管理員安裝WSL曾被自動審查拒絕，改由使用者要求的一步一步操作；不繞過審查，不自動重新開機。
- 尚待：HF實際登入／固定revision下載、乾淨image與新volume、虛構HTTP分類／上傳、缺憑證unavailable和離線重啟。未通過前任務3.9保持未完成。
