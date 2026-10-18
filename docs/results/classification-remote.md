# 受保護BERT下載與Docker驗收

狀態（2026-10-17）：角色2分支已完成固定revision認證下載、Docker乾淨建置、新volume啟動、Compose runtime secret與無憑證離線重啟驗收。任務3.9依使用者指定的受保護發布方案完成；待Claude審核、未合併主分支。原test未讀取、hash、複製或重新評分。

## 固定來源與憑證

沿用既有受保護Space `lee851104/receipt-model-lab`，沒有修改可見性或上傳內容。認證 `space_info` 實際取得revision `29b655b96b4ced268bb0c3994e901c72dfd65420`；同來源用 `token=False` 回401。API回報private=true（未由此區分Private與Protected UI模式），不宣稱公開模型庫。

模型為 `bert-next25-20261016-v3`；`model.safetensors` SHA256固定為 `16997425a9b36629469d60f506d52c2771bab1e6f3a3ea1465c2c0a316fa3e79`。明確設定 `CATEGORY_MODEL_REPO_TYPE=space`；不得把Space ID當作public model repo。

使用者在本機 `hf auth login` 輸入token，輸入不經聊天；部署建議使用僅授予此Space讀取權限的fine-grained token。此前驗收使用使用者建立的Read token，未聲稱當時已限制到單一Space。Docker以唯讀runtime secret檔案掛載到 `/run/secrets/hf_token`；程式只接收 `HF_TOKEN_FILE` 路徑，不把token值放在CLI參數、環境變數、build ARG、image或Git。BERT設定repo且TYPE=model會在Settings拒絕；純本機無repo不受影響。下載器只讀models/manifest.json及BERT推論白名單，逐檔hash與完整模型驗證通過後才發布；不取TF-IDF詞彙、訓練資料或整個Space snapshot。

官方介面：[HF下載指南](https://huggingface.co/docs/huggingface_hub/en/guides/download)、[Protected Spaces](https://huggingface.co/docs/hub/spaces-overview)。

## 實測結果

受驗產品commit `8750154`，後續 `8604d9d` 僅新增驗收探針及文件，Docker所需src/configs/依賴/設定未變。image `receipt-role2-acceptance:8750154`，ID `sha256:fa4feb7fc24da675bc8c398fefeac0e53a3b190018bed6a0aef392a8bdeba901`，以 `--pull --no-cache` 建置，未push。Linux amd64、Docker Engine29.8.2、WSL2 kernel6.18.54.1、torch2.8.0+cpu，cuda_build=null。

| 情境 | 健康檢查 | 分類 | 虛構CSV上傳 | 背景任務 | profile |
|---|---|---|---|---|---|
| 新volume、無HF token（上一階段） | unavailable | 503 model_unavailable | 202、3筆 | failed | 不檢查 |
| 只讀本機BERT、network none（上一階段） | bert | 200 | 202、3筆 | done | 200 |
| 認證遠端下載到全新model/data volume | bert | 200 | 202、3筆 | done | 200 |
| 沿用下載volume，新容器network none且無token掛載 | bert | 200 | 202、3筆 | done | 200 |
| 已提交Compose base+category secret，全新project/volume | bert | 200 | 202、3筆 | done | 200 |

遠端與Compose兩次均從空volume下載，SHA256符合固定模型；分類結果通過10類、有限機率、機率加總及類別範圍檢查。離線案例是建立新的容器、保留下載模型及DB，完全不掛token且Docker網路模式為none；不是只設定離線旗標或沿用原行程的記憶體。Compose另外從Windows主機透過動態loopback埠取得health200/bert。

Compose驗證實際使用repo的docker-compose.yml及docker-compose.category.yml，只有驗收override指定既有image、動態loopback埠、DEMO_MODE=0與fake屬性。config確認Space型別/revision/hash/secret傳入正確，inspect確認token掛載readonly。不是使用另一套模擬下載器。

## 資料與憑證邊界

- 建置context為56個已追蹤Dockerfile/依賴/configs/src檔案，排除src/web及資料檔，並非整個repo打包。image內/app54檔，禁止資料集/權重/憑證檔0；HF token檔不存在。
- 下載後模型volume僅7個已驗證推論檔（含service manifest），沒有殘留暫存cache或額外檔案。Compose容器沒有/root/.cache/huggingface/token。
- 在本機比對本次3個容器的stdout/stderr log、inspect和image history，token字串命中0；只輸出數字，不輸出token。此檢查範圍不等於整台電腦的秘密掃描。
- 驗收只使用scripts/verify_category_http.py內3筆虛構資料；未掛載rawdata、data/private或原test。屬性fake、DEMO_MODE=0，不是Qwen/demo seed/前端/全隊整合，也不是分類準確率評估。
- 本輪容器已停止，專用volume保留供查核；未停止其他角色服務、未用GPU。Docker曾在先前第一次build前退出，重開後實測成功；沒有宣稱長時間穩定性或壓測通過。

## 重現入口

在角色2repo根目錄使用CPU環境。Windows CLI下載入口如下（本輪實際認證下載由Linux容器正式入口執行，不另宣稱這條CLI本輪已實跑）：

```powershell
& 'C:/Users/User/Desktop/AI_project/receipt/data/role2/service-runtime-20261017/Scripts/python.exe' -m scripts.download_category_model --repo lee851104/receipt-model-lab --revision 29b655b96b4ced268bb0c3994e901c72dfd65420 --sha256 16997425a9b36629469d60f506d52c2771bab1e6f3a3ea1465c2c0a316fa3e79 --destination C:/Users/User/Desktop/AI_project/receipt/data/role2/remote-category-NEW
```

目的必須是新路徑，或已有完整且符合指定SHA的模型；不覆寫不完整或不相關資料夾。已驗證模型存在時可在無憑證及無網路下重用。

Compose需要設定以下環境變數；HF_TOKEN_FILE是路徑，不能填token值。如果HF_HOME有自訂，使用該登入環境的huggingface_hub.constants.HF_TOKEN_PATH。

```powershell
$env:CATEGORY_MODEL_REPO = 'lee851104/receipt-model-lab'
$env:CATEGORY_MODEL_REVISION = '29b655b96b4ced268bb0c3994e901c72dfd65420'
$env:CATEGORY_MODEL_SHA256 = '16997425a9b36629469d60f506d52c2771bab1e6f3a3ea1465c2c0a316fa3e79'
$env:HF_TOKEN_FILE = Join-Path $env:USERPROFILE '.cache/huggingface/token'
```

本次額外acceptance.yml內容如下；搭配空的empty.env避免讀主產品.env，使用不同的PROJECT名稱建立新volume：

```yaml
services:
  app:
    image: receipt-role2-acceptance:8750154
    ports: !override
      - "127.0.0.1::8000"
    environment:
      DEMO_MODE: "0"
      ATTRIBUTES_MODEL: fake
    labels:
      receipt.role: 2-acceptance
```

```powershell
docker compose --env-file PATH/empty.env -p PROJECT -f docker-compose.yml -f docker-compose.category.yml -f PATH/acceptance.yml up -d --no-build --pull never
# 只對本次新project取得容器名稱；probe會註冊虛構帳號並上傳3筆CSV，勿指向正式DB。
python -c "from pathlib import Path; import subprocess; subprocess.run(['docker','exec','-i','CONTAINER_NAME','python','-','bert'],input=Path('scripts/verify_category_http.py').read_bytes(),check=True)"
```

範例依賴前述已建置image；沒有該image時應先以不含私人資料的context建置，不能把--no-build當成已驗證build。完整本機實跑命令由data/role2/check_compose_remote.py與run_docker_acceptance.py保留；2026-10-18已將可攜版腳本提交到scripts/run_docker_acceptance.py、scripts/check_compose_remote.py及scripts/audit_remote_runtime.py；參數及新版驗證見classification-review-fixes.md。

## 證據與審核

可進Git的彙總：[classification-remote-20261017.json](classification-remote-20261017.json)。本機主資料夾data/role2保留：

- remote-identity-20261017.json：認證revision、匿名401。
- receipt-r2-remote-1792246266448231300.json：遠端與新容器離線HTTP、固定權重hash。
- receipt-r2-compose-1792246333306158200/result.json：真Compose、全新volume、唯讀secret、主機loopback。
- remote-runtime-audit-20261017.json：token命中0、模型volume7個白名單檔、3個驗收容器皆停止。
- remote-final-regression-20261017.log：本輪完整467/467，28.168秒。

下載器原7項隔離測試涵蓋無效來源/revision/SHA、manifest路徑/檔案白名單、錯hash、無token/中斷及不覆寫既有檔。原產品8750154已做Codex獨立程式審查，未發現確認問題，非Claude審核。本輪OpenSpec strict及git diff --check通過，未改產品邏輯；角色2受保護遠端/Docker驗收完成，Claude正式審核與主分支整合仍待。
