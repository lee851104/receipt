# 選定BERT的本機部署與驗收

本頁對應角色2任務3.6/3.8及3.9的非公開交付部分。程式已在角色2分支與role1/models d1ed44a整合；主工作目錄、現有服務及DB未切換。Claude正式審核仍待。

## 選定模型

- bert-next25-20261016-v3，305筆確認真實訓練資料＋102筆合成，seed42。
- 權重SHA256：16997425a9b36629469d60f506d52c2771bab1e6f3a3ea1465c2c0a316fa3e79。
- CPU FP32，max_length32（含特殊token），超長文字截斷；每批16，加鎖處理並行請求。
- 分類0–9順序固定，load(model_dir)回傳callable；不從環境偷偷讀第二個模型路徑。startup只load一次，換權重需重啟。
- 白名單檔案與SHA256、標籤對應、完整分類head均須吻合；缺檔、損壞、依賴缺失回unavailable，禁止隨機初始化head繼續使用。
- 只讀本機，local_files_only=True、trust_remote_code=False、use_safetensors=True；不保存品名或逐筆推論。
- 權重基於google-bert/bert-base-chinese，revision8f23c25b06e129b6c986331a13d8d025a92cf0ea，上游Apache-2.0。含真實人工確認資料微調，原始資料不公開。模型分數未校準、稀少類別證據不足；不得宣稱88.73%為此模型獨立test正確率。

## 安裝（PowerShell；角色2repo根目錄）

不修改共用venv。以下建立新的隔離環境；若同名目錄存在，請換新版本名稱。

```powershell
uv venv --python 3.12 .venv-category
uv pip install --python .venv-category/Scripts/python.exe --index-strategy unsafe-best-match -r requirements.txt -r requirements-docker.txt
```

依賴只用PyPI與PyTorch官方CPU索引；torch固定2.8.0+cpu，不會安裝CUDA版本。uv的預設first-index會在CPU索引找到舊idna而遮蔽PyPI相容版本，因此本組已驗證指令明確跨這兩個來源解析。一般pip可用同兩份requirements；不要把不可信索引加進來。容器原Dockerfile也會安裝這兩份清單。

```powershell
$categorySource = 'C:/Users/User/Desktop/AI_project/receipt/data/role2/runs/bert-next25-20261016-v3/model'
$categoryTarget = 'C:/Users/User/Desktop/AI_project/receipt/data/role2/service-model-NEW'
& .venv-category/Scripts/python.exe -m scripts.install_category_model --source $categorySource --destination $categoryTarget --sha256 16997425a9b36629469d60f506d52c2771bab1e6f3a3ea1465c2c0a316fa3e79
```

來源必須是可信的完整模型目錄，不能指到整個run。安裝器複製推論白名單並精簡manifest，驗證後才就位；目的已存在就失敗，不覆寫。完整安裝僅7個檔案，沒有訓練資料或預測。模型仍放Git忽略目錄。

設定CATEGORY_MODEL=bert、CATEGORY_MODEL_DIR為新目錄，ATTRIBUTES_MODEL=fake（角色3尚未整合時），DATABASE_URL使用獨立SQLite，JWT_SECRET自行設定至少32字元。使用目前未占用的本機埠啟動：
```powershell
& .venv-category/Scripts/python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8017
```
先核對該埠未占用。健康檢查models.category應為bert。不可將驗收範例當作要求去改現有8000/8001服務或私人DB。

## 可重跑驗收

只使用腳本內公開虛構品名/發票，啟用audit hook拒絕JSONL、rawdata與data/private，禁止外部連線（驗收HTTP只准loopback）。不傳資料集參數。

```powershell
# 原實驗環境產生12筆虛構probe參考；output須新檔。
& experiments/category-models/.venv/Scripts/python.exe -m scripts.category_service_reference --model-dir $categorySource --source-code experiments/category-models --out C:/Users/User/Desktop/AI_project/receipt/data/role2/reference-NEW.json
# 新CPU服務環境與已安裝模型
& .venv-category/Scripts/python.exe -m scripts.verify_category_service --model-dir $categoryTarget --reference-json C:/Users/User/Desktop/AI_project/receipt/data/role2/reference-NEW.json --out C:/Users/User/Desktop/AI_project/receipt/data/role2/acceptance-NEW.json
```

驗收輸出只有統計、版本、HTTP狀態與指紋，不印名稱。單次benchmark不代表壓測或所有品名延遲。

## 本次實際結果（2026-10-17）

環境：主data/role2/service-runtime-20261017全新venv，torch2.8.0+cpu/transformers4.57.1；主data/role2/service-model-20261017-v1全新安裝目錄。

| 驗收 | 結果 |
|---|---|
| 與原實驗載入器12筆虛構probe | 類別相同、機率最大差0 |
| check_classify、批次/逆序/並行 | 通過 |
| CPU 1000筆（10種虛構名稱輪流，batch16） | 12.9486秒 |
| 暖機後單筆 | 0.0335秒 |
| 啟動（含權重完整性檢查） | 9.5417秒 |
| 真HTTP健康檢查/登入/分類 | bert / 200 |
| 真HTTP虛構CSV上傳/工作/profile | 202 / done / 200 |
| 缺模型健康檢查/分類/上傳工作 | unavailable / 503 / failed |
| 私人資料開啟/外部連線嘗試 | 0 / 0 |

使用真正選定BERT、fake屬性、臨時DB與自動釋放的loopback埠；不是全系統Qwen/300人/前端驗收。原test未開/hash/copy/評分。HTTP結果主data/role2/service-acceptance-20261017/result-v1.json。

## 發布政策與未涵蓋範圍

使用者後來選擇Protected展示、程式/模型不公開，取代原3.9「公開模型庫」方案。已有Protected Space展示交付紀錄；本輪沒有改可見性、上傳或重新驗證HF線上狀態。受保護模型不可填成匿名public model repo下載來源。

因此CATEGORY_MODEL_REPO與CATEGORY_MODEL_REVISION仍留空，採上面完整本機白名單安裝；不要填入Space ID給目前只支援model repo的下載器。未授權改成公開權重。若未來要遠端自動取得Protected權重，須另做受保護artifact下載介面、憑證注入與revision驗收。

本機沒有Docker命令。本輪完成全新venv＋全新模型目錄的Windows CPU真HTTP驗收，不宣稱全新實體電腦、Docker建置、Linux執行、遠端自動下載或主分支正式上線完成。這些應由角色1/整合環境接續；角色2提供可重現的模型/載入契約與證據。

本輪回歸：主環境457/457通過；新增安裝工具後，新CPU環境459/459通過。Linux x86_64 Python3.12依賴解析成功（非Linux實跑）。OpenSpec strict通過。三份新/重建文件用audit_synthetic.py對既有57筆私人reference僅本機比對，public_text_private_matches=0、synthetic exact matches=0；不是所有私人來源的全面掃描。
