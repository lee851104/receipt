# 受保護BERT下載與Docker驗收

狀態（2026-10-17）：下載器及隔離測試完成；Docker Linux乾淨建置、無憑證拒絕、本機BERT的離線HTTP及新容器啟動已實測通過。HF認證遠端下載尚待使用者本機登入，整體3.9仍未完成。原test未讀。

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

## Docker Compose（認證下載仍待驗收）

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
- Docker Desktop曾因安裝/啟動問題改為官方all-users安裝；啟用WSL功能要求重開。使用者重開後已實測Engine29.8.2、Linux amd64、WSL2 kernel6.18.54.1正常。首次建置前daemon曾退出；重新啟動後乾淨建置成功，退出原因未定，不視為長時間穩定性證明。
- 使用者選擇本機Docker，未新建遠端Space。管理員安裝WSL曾被自動審查拒絕，改由使用者要求的一步一步操作；不繞過審查，不自動重新開機。
- 尚待：HF實際登入／固定revision遠端下載到新volume、runtime secret實跑及下載後移除secret的斷網重啟；任務3.9保持未完成。

## 2026-10-17 Docker實測階段

受驗來源commit `8750154`；使用 `--pull --no-cache` 建置，image ID `sha256:fa4feb7fc24da675bc8c398fefeac0e53a3b190018bed6a0aef392a8bdeba901`。未push。最小context為56個已追蹤的Dockerfile、依賴、configs及src檔案，排除src/web與資料檔，並非整個repo打包。建置後 `/app` 54個檔案，禁止的資料集/權重/憑證檔數0；HF token檔不存在。CPU torch2.8.0+cpu，cuda_build=null。

| 情境 | 健康檢查 | 分類 | 虛構CSV上傳 | 背景任務 | profile |
|---|---|---|---|---|---|
| 新資料/模型volume，無HF token | unavailable | 503 model_unavailable | 202、3筆 | failed | 不檢查 |
| 只讀本機BERT、全新DB、network none | bert | 200、10類機率契約 | 202、3筆 | done | 200 |
| 第二個容器、相同DB及只讀模型、network none | bert | 200、10類機率契約 | 202、3筆 | done | 200 |

無憑證案例完成後模型volume檔案數0。兩個本機BERT容器都沒有token mount且網路為none；manifest與權重SHA符合上方固定值。這證明既有完整模型能在Linux容器離線載入，不能代替遠端認證下載、Compose secret或全隊整合驗收。屬性使用fake、DEMO_MODE=0；未驗Qwen、demo seed或前端。虛構資料全部寫入專用新volume；完成後只停止這次容器，保留volume供查核，未停止其他角色服務。沒有掛載或讀取rawdata、data/private或原test；這是部署驗收，不是準確率評估。

HTTP探針已納入 `scripts/verify_category_http.py`；在已啟動的隔離容器中以標準輸入執行 `python - bert`（缺模型案例為 `python - unavailable`）。例如從角色2根目錄執行下面命令，`CONTAINER_NAME`改為本次隔離容器；探針會註冊虛構帳號及上傳3筆虛構CSV，不可指向正式資料庫：

```powershell
python -c "from pathlib import Path; import subprocess; subprocess.run(['docker','exec','-i','CONTAINER_NAME','python','-','bert'],input=Path('scripts/verify_category_http.py').read_bytes(),check=True)"
```

本機證據（主資料夾data/role2，Git忽略）：`docker-build-20261017-v2.log`、`receipt-r2-noauth-1792244442386688800.json`、`receipt-r2-local-1792244453183018600.json`。本輪 `python -m unittest discover -s tests` 重跑467/467通過（30.753秒），log為 `docker-stage-regression-20261017.log`；提交探針與實跑探針SHA256一致（41af58719209c962131c4a50163c55048a48b7ed67110afeb636e1ccf2a2fef9）。待Claude審核，未合併主分支。
