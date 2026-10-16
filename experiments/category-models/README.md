# 品名分類實驗：A 與 B

只讀品名，預測 0～9 的消費類別。A 使用 TF-IDF，B 使用固定的中文 Embedding，兩者都以邏輯迴歸分類。此為獨立實驗，不改主程式、正式對照表或網頁。C 的 BERT 三種子微調已實作，使用方式見最後章節。

## 安裝與測試

從專案根目錄執行（本次使用 Python 3.12）：

```powershell
python -m venv experiments/category-models/.venv
experiments/category-models/.venv/Scripts/python.exe -m pip install -r experiments/category-models/requirements.txt
experiments/category-models/.venv/Scripts/python.exe -m unittest discover -s experiments/category-models -p "test_category_models.py" -v
```

套件和資料在本機使用。沒有模型 API，也不需要 GPU。

## 標註格式

UTF-8 JSONL，每行一筆。下例是虛構資料：

```json
{"id":"example-001","name":"測試無糖茶","category":1,"review_status":"human_confirmed","name_only_context_needed":false}
```

- 輸入只取 `name`；`category` 是學習目標，其他欄位只供稽核與切分。
- `review_status` 必須是 `human_confirmed`。不接受空品名、重複 ID、類別 10 或未確認標籤。
- 品名先 NFKC 正規化、去除頭尾空白；同名同類合併，同名異類拒絕。原始 CSV 不修改。
- 可增加 `group` 欄位，把同商品的不同寫法放在同一折。未指定時，依品名去空白、忽略英文字母大小寫分組；不同群組仍可能存在未標記的近似名稱。
- `name_only_context_needed` 註記標籤依賴交易背景，但不把背景說明提供給模型。
- 類別順序：正餐、飲品、零食甜點、生鮮食材、運動、其他服務、交通、住宿、日用品、電子產品。

也可從另一份已人工確認的對照表及 CSV 準備資料：

```powershell
experiments/category-models/.venv/Scripts/python.exe experiments/category-models/prepare_data.py --csv path/to/month.csv --catalog path/to/catalog.json --out experiments/category-models/data/new-items.jsonl
```

只取正金額，略過對照表未確認或無對應的品項。品名重複購買不增加獨立樣本數。此命令不等於再次人工核對，也不自動加入變體群組。

## 舊版開發 CV 訓練

以下 CV 指令保留供歷史重現。角色 2 的 v2 混合來源資料請使用本文最後的「固定切分 A/B」流程；真實品名及模型輸出統一使用主專案 `C:/Users/User/Desktop/AI_project/receipt/data/role2/`，不要放入 worktree。

```powershell
experiments/category-models/.venv/Scripts/python.exe experiments/category-models/tfidf_lr.py train --data experiments/category-models/data/items.jsonl --out experiments/category-models/outputs/tfidf-run-01
```

每次使用新的輸出資料夾。固定字元 1～3 gram、sublinear TF、C=1、balanced class weights、seed=42、CPU 單執行緒。不調參。

資料不足時採三折「開發交叉驗證」：

1. 以群組為切分單位。至少三個群組的類別可參與驗證，稀少類別只放在每折的訓練集。
2. 每折重新建立 TF-IDF 詞表與訓練分類器，每個受評品名恰好驗證一次。
3. 對照「永遠猜該折訓練集最多類別」的基準。Macro-F1 只平均有驗證樣本的類別，完整 10 類分數不足時為 `null`。
4. 另用全部已確認資料訓練最終模型。它沒有獨立測試成績，不列訓練集準確率充當效果。

若不足兩個類別各有三個群組，仍可訓練至少兩類的模型，但報告會顯示無法交叉驗證。之後蒐集足夠資料再建立固定 70/15/15 的共同實驗資料，本輪固定切分程式已支援保留測試集，但尚未執行正式最終測試。

輸出：

| 檔案 | 用途 |
|---|---|
| `model.joblib` | 最終模型、類別順序、訓練名稱／群組與環境資訊 |
| `report.json` | 各類分數、混淆矩陣、基準、時間、尖峰程序記憶體與限制 |
| `splits.json` | 各折品項 ID 與資料指紋，供後續方法重用 |
| `validation-predictions.jsonl` | 每筆真正留出的驗證結果 |

`data/`、`outputs/`、`models/` 全部排除 Git；模型詞表及逐筆結果含私人品名。`joblib` 使用 pickle，只能載入自己產生或可信來源的模型。

## 預測新名稱

建立本機 JSONL，每行至少有 `name`，不需標籤：

```json
{"name":"測試奶茶"}
```

```powershell
experiments/category-models/.venv/Scripts/python.exe experiments/category-models/tfidf_lr.py predict --model experiments/category-models/outputs/tfidf-run-01/model.joblib --data experiments/category-models/data/new-names.jsonl --out experiments/category-models/outputs/new-predictions.jsonl
```

逐筆結果寫入檔案，終端只印筆數。`probabilities` 固定依類別 0～9 排列；模型未訓練過的類別填 0。全部字詞皆未見過時 `out_of_vocabulary=true`，仍保留模型輸出但不表示可靠。機率未校準，不應當作正確率保證。

Python 介面：`Classifier.load(model_path).predict(names)`。

## 外部驗證

```powershell
experiments/category-models/.venv/Scripts/python.exe experiments/category-models/evaluate_external.py --model experiments/category-models/outputs/tfidf-run-01/model.joblib --catalog path/to/reviewed-catalog.json --csv path/to/new-month.csv --out experiments/category-models/outputs/external-01
```

或對新的已標註 JSONL 使用 `tfidf_lr.py evaluate --model ... --data ... --out ...`。

輸出會分開計算訓練名稱重疊數及未見名稱分數。未見名稱不等於已證明為獨立測試集，仍需確認資料來源及是否曾用於調參；目前不會把所有重疊資料說成外部泛化效果。

## 效能計量

同一程序記錄開發 CV 時間、最終 fit 時間、暖機後完整分類流程處理 1,000 筆的時間、OS 尖峰程序 RSS 及模型檔大小。1,000 筆由目前品名循環重複，用於效能測量，不是新增資料或分類正確率證據。RSS 包含 Python 與原生套件，也受程序先前工作影響；不同方案應各開乾淨程序。執行環境及來源指紋在報告內。

## B：Embedding＋邏輯迴歸

使用 [BAAI/bge-small-zh-v1.5](https://huggingface.co/BAAI/bge-small-zh-v1.5)，固定 revision `7999e1d3359715c523056ef9478215996d62a620`。品名經 tokenizer、預訓練模型、CLS pooling 與 L2 正規化後成為向量，再交給邏輯迴歸。編碼器凍結、不微調，不加檢索指令前綴。設定為 CPU、FP32、單計算執行緒、batch 16、最長 512 tokens；超長名稱會截斷。

首次安裝 B 套件並下載公開模型（需要網路）：

```powershell
experiments/category-models/.venv/Scripts/python.exe -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
experiments/category-models/.venv/Scripts/python.exe -m pip install -r experiments/category-models/requirements-b.txt
experiments/category-models/.venv/Scripts/python.exe experiments/category-models/download_embedding.py --out experiments/category-models/models/bge-small-zh-v1.5
experiments/category-models/.venv/Scripts/python.exe -m unittest discover -s experiments/category-models -p "test_*.py" -v
```

下載程式只取得指定版本的公開模型，不讀取消費資料；下載後依上游雜湊驗證檔案。後續訓練與預測只載入本機模型並強制離線，品名不送到 API。

沿用已產生的 A 切分訓練 B，每次指定新的輸出目錄：

```powershell
experiments/category-models/.venv/Scripts/python.exe experiments/category-models/embedding_lr.py train --data experiments/category-models/data/items.jsonl --splits experiments/category-models/outputs/tfidf-20261013/splits.json --encoder-dir experiments/category-models/models/bge-small-zh-v1.5 --cache experiments/category-models/data/bge-small-vectors.npz --out experiments/category-models/outputs/embedding-run-01
```

程式驗證資料指紋與群組邊界，直接重用 A 的 train/validation ID。向量可先一次計算，因為編碼器固定且不使用標籤、不從本批資料學習統計量；邏輯迴歸仍只用每折訓練資料 fit。LR 與 A 同樣使用 C=1、balanced、max_iter=2000，沒有調參。

向量快取使用獨立 `.npz` 檔，不可指向輸入檔、編碼器目錄或本次輸出目錄；會核對品名順序、模型檔案與版本、設定及陣列完整性，資料改變就重算。報告分開記錄編碼時間、LR 訓練時間與完整預測時間；1,000 筆測速不使用向量快取。完整模型大小包括編碼器與 LR，不能只比較小型 `model.joblib`。

B 的輸出檔名與 A 相同。預測與評估：

```powershell
experiments/category-models/.venv/Scripts/python.exe experiments/category-models/embedding_lr.py predict --model experiments/category-models/outputs/embedding-run-01/model.joblib --data experiments/category-models/data/new-names.jsonl --out experiments/category-models/outputs/b-new-predictions.jsonl
experiments/category-models/.venv/Scripts/python.exe experiments/category-models/embedding_lr.py evaluate --model experiments/category-models/outputs/embedding-run-01/model.joblib --data experiments/category-models/data/new-items.jsonl --out experiments/category-models/outputs/b-external-01
```

`predict` 接受每行只有 `name` 的 JSONL；`evaluate` 必須提供已人工確認的標籤，可先使用上方 `prepare_data.py` 從 CSV 準備。兩者皆固定輸出類別 0～9 的機率，尚未校準。B 沒有 A 的 TF-IDF `out_of_vocabulary` 欄位；能產生向量不代表一定分對。

搬移模型時須保留編碼器資料夾及 `encoder-manifest.json`。預設依 `model.joblib` 記錄的相對路徑尋找編碼器，也可用 `--encoder-dir` 指定新位置；檔案、編碼設定及相關套件版本必須符合訓練紀錄。只載入可信的 joblib。B 與 A 的比較見 [RESULTS-B.md](RESULTS-B.md)。

## 角色 2：新版訓練資料切分（2026-10-15，v2 修訂）

資料工具只用 Python 標準函式庫。請在角色 2 worktree 根目錄執行：
`C:\Users\User\.codex\worktrees\receipt-role2\receipt`。

### 可重現的合成品名

`synthetic_names.py` 包含可進 Git 的候選清單、子類配額與生成指令，取代舊的 `data/role2/synthetic_candidates.py`。只根據公開的 `docs/category-models-brief.md` 和常識撰寫，不讀取或參考任何真實品名。

每類分配 6 個子類，每子類 10 筆（3 筆發票式簡寫、7 筆完整描述），全部輸出，不再取每類前 50 筆。總計 600 筆，每類 60 筆、簡寫 18 筆（30%）。運動補給、汽柴油／充換電、寵物飼料與用品都有獨立配額；球鞋、瑜伽墊等待決定運動裝備沒有納入。各子類數量見 `docs/results/classification-data.md`。

```powershell
$role2Python = 'C:\Users\User\Desktop\AI_project\receipt\.venv\Scripts\python.exe'
& $role2Python experiments/category-models/synthetic_names.py --out datasets/synthetic/item-names.jsonl --force
& $role2Python experiments/category-models/synthetic_names.py --out datasets/synthetic/item-names.jsonl --check
```

`--force` 只用於明確指定的合成輸出；不加時拒絕覆寫已存在檔案。`--check` 逐位元組確認 JSONL 與候選清單一致。公開 JSONL 仍只有 `name`、`category`、`source="synthetic"`，子類與樣式僅用於生成和覆蓋檢查，不作為分類模型輸入。合成資料不等於人工確認標籤，只供訓練；30% 簡寫也不能保證模型已能泛化到真實發票。

### 本機隱私比對

比對真實資料只執行 `audit_synthetic.py`，不讀取或列印私人品名。以下來源是主資料夾實際存在的人工標註、私人對照表與 CSV，指令只回報彙總數字：

```powershell
$role2Python = 'C:\Users\User\Desktop\AI_project\receipt\.venv\Scripts\python.exe'
$role2AuditArgs = @(
    'experiments/category-models/audit_synthetic.py',
    '--synthetic', 'datasets/synthetic/item-names.jsonl',
    '--reviewed', 'C:\Users\User\Desktop\AI_project\receipt\data\private\category-review-20261012\labeled-items.jsonl',
    '--catalog', 'C:\Users\User\Desktop\AI_project\receipt\data\private\item-categories.json'
)
$role2Invoices = @(Get-ChildItem -LiteralPath 'C:\Users\User\Desktop\AI_project\receipt' -Filter '*.csv' -File) + @(Get-ChildItem -LiteralPath 'C:\Users\User\Desktop\AI_project\receipt\rawdata' -Filter '*.csv' -File -Recurse)
foreach ($role2Invoice in $role2Invoices) { $role2AuditArgs += @('--invoice', $role2Invoice.FullName) }
& $role2Python @role2AuditArgs
```

至少提供一份非空的私人參考資料；撞名或格式錯誤回非零 exit code，不印品名。本輪查核 6 份 CSV、對照表與標註，232 個正規化不同品名的完全撞名數為 0。此檢查僅涵蓋指定來源的正規化完全比對，不代表世界上不存在同名商品。

### 固定切分與資料位置

含真實品名的切分結果統一放在主資料夾的 `C:\Users\User\Desktop\AI_project\receipt\data\role2\`，不放 worktree。舊版 `split-20261015` 已搬到該位置；新版為 `split-20261015-v2`，舊版不覆寫。

以下是本輪實際執行的命令。**v2 已存在，重新 prepare 請將輸出改為新的版本名稱（例如 v3）**；check 可直接重跑：

```powershell
$role2Python = 'C:\Users\User\Desktop\AI_project\receipt\.venv\Scripts\python.exe'
& $role2Python experiments/category-models/dataset_split.py prepare --real 'C:\Users\User\Desktop\AI_project\receipt\data\private\category-review-20261012\labeled-items.jsonl' --legacy-real --synthetic datasets/synthetic/item-names.jsonl --out 'C:\Users\User\Desktop\AI_project\receipt\data\role2\split-20261015-v2'
& $role2Python experiments/category-models/dataset_split.py check --dataset 'C:\Users\User\Desktop\AI_project\receipt\data\role2\split-20261015-v2'
```

真實輸入需要 `id`、`name`、0–9 整數 `category`、`source="real"`、`review_status="human_confirmed"`，可附 `group` 和 `name_only_context_needed`。上述歷史檔缺少 `source`，因此明確加 `--legacy-real`，manifest 會記錄這個聲明；它不會覆蓋已存在的 synthetic 來源，也不會自動把待複核資料變成已確認。

- seed=42，按類別分群後切出約 15% 驗證群與 15% 測試群。3 群以上的類別至少各留 1 群；不足 3 群只進訓練。群組大小不一，筆數比例不保證精確 70/15/15。
- NFKC、忽略大小寫與空白後同名，以及明確 group 的傳遞關係會一起切分。先保留群組關係，再將正規化同名合併為一筆；語義近似仍需人工標記。
- 合成資料只進訓練；與真實名稱正規化撞名的合成項目剔除。驗證與測試只接受 real + human_confirmed。
- 輸出 train/validation/test JSONL 與 manifest，包含來源及輸出指紋、數量與不足 5 筆真實測試品名的類別；既有目錄拒絕覆寫。SHA256 用於偵測意外修改，不是防惡意竄改的簽章。
- **逐筆檔與 manifest 都含私人資訊，只留在主資料夾被 Git 忽略的 data/role2；不可提交或上傳雲端。** CLI 只印彙總數字。舊 57 筆曾用於 A/B 開發驗證，新的留出切分不能宣稱為獨立最終測試。
- 舊 A/B CLI 要求 human_confirmed 並使用三折 CV，不能直接餵新混合訓練檔，也不能把 synthetic 改成 human_confirmed。第 3.4 已新增下方共用固定切分流程。

### 驗證

```powershell
$role2Python = 'C:\Users\User\Desktop\AI_project\receipt\.venv\Scripts\python.exe'
& $role2Python -m unittest discover -s experiments/category-models -p 'test_synthetic_names.py'
& $role2Python -m unittest discover -s experiments/category-models -p 'test_dataset_split.py'
& $role2Python -m unittest discover -s experiments/category-models -p 'test_audit_synthetic.py'
& $role2Python -m unittest discover -s tests
```

## 固定切分 A/B（角色 2 第 3.4 項，2026-10-15）

`fixed_split_train.py` 只用 train 擬合，保留 real/synthetic 來源，validation 只作開發驗證，test 不預測、不計分。每次輸出使用新的目錄；已有目錄會拒絕。模型與逐筆預測含私人品名，一律輸出到主專案的 Git 忽略目錄。

下列從角色 2 worktree 執行。公開 BGE 權重已下載到主專案指定位置；首次需另用 `download_embedding.py --out` 下載到該位置（不要覆寫既有模型）。CPU 套件安裝步驟同上方 B 章節。

```powershell
$role2ModelPython = '.\experiments\category-models\.venv\Scripts\python.exe'
$role2Dataset = 'C:\Users\User\Desktop\AI_project\receipt\data\role2\split-20261015-v2'
$role2Runs = 'C:\Users\User\Desktop\AI_project\receipt\data\role2\runs'
$role2Encoder = 'C:\Users\User\Desktop\AI_project\receipt\data\role2\models\bge-small-zh-v1.5'

& $role2ModelPython experiments/category-models/fixed_split_train.py --model tfidf --dataset $role2Dataset --out "$role2Runs/tfidf-v2-reproduction-01"
& $role2ModelPython experiments/category-models/fixed_split_train.py --model embedding --dataset $role2Dataset --encoder-dir $role2Encoder --out "$role2Runs/embedding-v2-reproduction-01"
& $role2ModelPython -m unittest discover -s experiments/category-models -p 'test_*.py'
```

本次實際 run 為 `tfidf-v2-20261015` 與 `embedding-v2-20261015`。每個 run 有 `model.joblib`、`report.json`、`validation-predictions.jsonl`；沒有 test 預測檔。模型使用既有 A/B 的 `Classifier.load` 介面，bundle 保留訓練來源與資料指紋。只載入自己產生或可信來源的 joblib。

- 載入與輸出前核對資料 manifest、來源／切分指紋及來源邊界，資料變動則失敗。
- 模型儲存前後比較所有 validation 與最多 10 筆 train 探針的類別及完整 10 維機率；空 validation 也不能跳過重載檢查。探針不加入分數。
- 驗證類別少於 5 筆時，precision／recall／F1 不計分，macro-F1 只平均合格類別；全都不足時為 null。空 validation 的 accuracy 為 null。
- CPU 1000 筆測速採循環訓練名稱，暖機後執行完整分類，B 不使用向量快取；報告分開記錄編碼、fit、初次載入及重載時間，B 模型大小包含編碼器。
- CLI 成功時只印彙總，失敗不回顯輸入內容。下載與訓練分離，訓練強制離線。

目前 train 643（43 real、600 synthetic）、validation 7、test 7。A/B 在驗證集各答對 6/7；每類不足 5，macro-F1 不可計算，test 未評分。資料曾用於早期開發 CV，且近似名稱群組仍待人工複核，不能宣稱獨立最終測試。完整彙總及成本見 [classification-baselines.md](../../docs/results/classification-baselines.md)。

## C：本機 BERT 微調與三模型比較

`bert_finetune.py` 全參數微調 [google-bert/bert-base-chinese](https://huggingface.co/google-bert/bert-base-chinese/tree/8f23c25b06e129b6c986331a13d8d025a92cf0ea)，固定 revision `8f23c25b06e129b6c986331a13d8d025a92cf0ea`。分類 head 為 10 類；從預訓練模型載入時提示 head 為新初始化是預期行為。公開下載程式不讀取任何品名，逐檔核對上游雜湊。

GPU 訓練另建環境，保留 A/B 的 CPU 環境。以下在角色 2 worktree 執行，CUDA 安裝入口依 [PyTorch 官方歷史版本說明](https://pytorch.org/get-started/previous-versions/)：

```powershell
$role2GpuPython = '.\experiments\category-models\bert-runtime\.venv\Scripts\python.exe'
# 環境已存在時，省略 venv 建立。
uv venv --python .\experiments\category-models\.venv\Scripts\python.exe experiments/category-models/bert-runtime/.venv
uv pip install --python $role2GpuPython torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
uv pip install --python $role2GpuPython -r experiments/category-models/requirements-bert.txt
uv pip check --python $role2GpuPython

$role2Data = 'C:\Users\User\Desktop\AI_project\receipt\data\role2'
& $role2GpuPython experiments/category-models/download_bert.py --out "$role2Data/models/bert-base-chinese"
foreach ($role2Seed in @(42,43,44)) {
    & $role2GpuPython experiments/category-models/bert_finetune.py --dataset "$role2Data/split-20261015-v2" --pretrained "$role2Data/models/bert-base-chinese" --out "$role2Data/runs/bert-v2-reproduction-seed$role2Seed" --seed $role2Seed --device cuda
    if ($LASTEXITCODE -ne 0) { break }
}
```

每個種子必須使用新的輸出目錄。設定固定為 max_length=32、batch=16、AdamW lr=2e-5、weight_decay=.01、gradient clipping=1、FP32、最多 10 輪、patience=2、min_delta=1e-4。只有 train 參與梯度；每輪 validation cross entropy 決定是否保存。微小 loss 改善仍保存最小值，但不重設 patience。沒有根據測試集調參。

模型保存在 run 的 `model/`，包含完整 safetensors、tokenizer、設定與檔案指紋；不包含明文訓練名稱清單，仍視為私人模型，不能進 Git 或自行公開。run 另外保存 `report.json`（每輪 loss、最佳 epoch、資料指紋與成本）及私人 `validation-predictions.jsonl`。`bert_model.Classifier.load(model_dir).predict(names)` 回傳類別 0～9 與 10 維機率，模型載入全離線，損壞或多出的未驗證模型檔會拒絕。

訓練結束先在 CPU 比對保存前與重載後的驗證集及 10 筆 train 探針，完整機率一致才寫成功報告。`test` 在訓練中不預測、不評分。CPU 1000 筆測速是循環 train 名稱，不是額外評估樣本；訓練報告的 RSS 包含訓練，正式比較另以乾淨 CPU 子程序量測推論 RSS。

### 凍結後的一次性測試

`compare_fixed_models.py` 要求 A、B、三個不同種子的 BERT 來自同一份固定切分；BERT 必須同一預訓練來源及超參數。候選種子只依最低 validation loss 選擇，再凍結模型／報告／資料指紋。下方是本次執行紀錄，**已完成的資料集不可再次執行**：

```powershell
$role2CpuPython = '.\experiments\category-models\.venv\Scripts\python.exe'
$role2Data = 'C:\Users\User\Desktop\AI_project\receipt\data\role2'
& $role2CpuPython experiments/category-models/compare_fixed_models.py --dataset "$role2Data/split-20261015-v2" --a "$role2Data/runs/tfidf-v2-20261015" --b "$role2Data/runs/embedding-v2-20261015" --bert "$role2Data/runs/bert-v2-20261015-seed42" --bert "$role2Data/runs/bert-v2-20261015-seed43" --bert "$role2Data/runs/bert-v2-20261015-seed44" --out "$role2Data/runs/comparison-v2-20261015"
```

一次性標記 `test-evaluation-claimed.json` 與 `test-evaluation-model-claims/` 留在該資料集；每模型只預測一次相同 test 名稱。標記綁定評估計畫 SHA256，不能換輸出目錄、負索引或重跑 worker 繞過。中途中斷也保留標記；不要刪除標記重跑以挑結果，應保留失敗紀錄並人工確認是否已消耗 test。後續新實驗需另收集資料與新切分，不能把重新複製舊 test 當作新的獨立測試。

每模型以既有 CPU 環境啟動獨立程序，量測完整 tokenizer／模型／分類流程 1000 筆時間、模型大小與程序峰值 RSS。BERT 三種子列出各自分數及平均±母體標準差，不挑 test 最好的一次。所有結果仍屬開發留出：57 筆資料曾用於舊 CV，而且各類 test 少於 5 筆，macro-F1 全部為 null。

驗證指令（測試皆使用虛構資料與隨機 tiny BERT，無須下載模型或 GPU）：

```powershell
& $role2CpuPython -m unittest discover -s experiments/category-models -p 'test_*.py'
& 'C:\Users\User\Desktop\AI_project\receipt\.venv\Scripts\python.exe' -m unittest discover -s tests
node --test "tests/*.test.cjs"
```

彙總與限制見 [classification.md](../../docs/results/classification.md)。BERT 微調不等於已接上 API；服務整合與模型公開另行處理。

### 公開報告隱私複核狀態

`audit_synthetic.py` 可在既有私人來源參數後加 `--public-text <公開文字檔>`，逐檔做正規化子字串掃描，只輸出命中數，不列出命中文字。命中可能包括一般詞彙，需本機人工判讀，不能視為必然揭露了私人購買資訊。

本輪比較計算已完成，但完整報告的文字掃描有 1 個名稱片段重合。完整報告先保留於主專案 `data/role2/runs/comparison-v2-20261015/report-detail.md`（Git 忽略），`docs/results/classification.md` 只保留待複核狀態。不要把命中的真實品名貼回聊天；使用者可在本機確認後再決定公開版本。

如需在本機人工判讀，可另外加 `--local-match-report <新的私人JSON檔路徑>`；名稱與行號只寫入該檔，終端仍只有數字。此檔必須放主專案被 Git 忽略的 `data/role2/`，不應提交、列印或貼給雲端。已有檔案會拒絕覆寫。本輪已產生 `data/role2/runs/comparison-v2-20261015/privacy-review.json`，雲端 AI 未讀回內容。

## 新增真實資料：先預標，再由使用者審核

`prelabel_review.py` 只在本機使用既有 BERT seed 42 及 TF-IDF；不更新權重、不評估舊測試集，也不把預標當作人工標籤。輸入只取品名，交易欄位僅用於過濾：排除無日期的結尾、作廢發票、非整數或低於 10 元的明細；其餘狀態與格式錯誤直接停止。品名依 NFKC、去空白、忽略大小寫分組去重。

從角色 2 worktree 執行；每次使用新的輸出資料夾：

```powershell
experiments/category-models/.venv/Scripts/python.exe experiments/category-models/prelabel_review.py --input-dir C:/Users/User/Desktop/AI_project/receipt/rawdata/receipt_2/receipt_2 --private-root C:/Users/User/Desktop/AI_project/receipt/data/role2 --out C:/Users/User/Desktop/AI_project/receipt/data/role2/category-review-20261016-v1 --bert C:/Users/User/Desktop/AI_project/receipt/data/role2/runs/bert-v2-20261015-seed42/model --tfidf C:/Users/User/Desktop/AI_project/receipt/data/role2/runs/tfidf-v2-20261015/model.joblib
```

輸出 `draft-items.jsonl`、`review.html`、只含彙總的 `summary.json`、來源／模型雜湊 `provenance.json` 和本機推論日誌。所有輸出都留在主資料夾被 Git 忽略的 `data/role2/`。終端只印彙總數字，失敗不回顯儲存格或例外內容。

開啟 `review.html` 後：

1. 預設列出待審核，將模型分歧或低分品項排在前面；可篩選「優先審核」。BERT 分數與分歧只是審核排序依據，沒有校準成正確率。
2. 逐筆修改類別，必要時勾選「需背景」，最後勾選「已確認」。未知或運動裝備等尚未決定的品項選 10「待決定」，不能確認、不能匯出成訓練標籤。
3. 離開前按「儲存進度 HTML」，確認下載完成，存回本次審核資料夾；下次開啟該檔繼續。原始審核頁不會自動覆寫，也不使用雲端或瀏覽器儲存服務。
4. 完成後按「匯出已確認 JSONL」，存回審核資料夾，再提供本機路徑。匯出只包含使用者明確確認的 0–9 類，帶有 `source=real`、`review_status=human_confirmed`。其餘品項留待後續審核；修改類別或背景註記會取消該筆確認。

待審核草稿固定 `category=null`、`review_status=model_pending`，現有訓練資料驗證器會拒絕。人工確認後，仍須另行合併、去重與檢查標籤衝突，再建立新版本資料切分；不能直接宣稱新增資料構成獨立測試集。

虛構資料測試：

```powershell
experiments/category-models/.venv/Scripts/python.exe -m unittest discover -s experiments/category-models -p "test_prelabel_review.py"
node --test experiments/category-models/test_review_core.cjs
```

## 人工審核後的三模型比較

`evaluate_reviewed.py` 只評估人工已確認的 0–9 類，排除未確認及類別 10。人工答案先驗證去重及標籤衝突；按照 ID 與模型實際使用的 NFKC／頭尾空白正規化品名，精確對齊預標草稿。TF-IDF 與 BERT 使用審核前保存的分類，Embedding 用既有模型補跑；不 fit、不改權重、不重跑舊切分的最終測試。

```powershell
experiments/category-models/.venv/Scripts/python.exe experiments/category-models/evaluate_reviewed.py --reviewed "C:/Users/User/Downloads/labeled-items-5092c3e897c490e4041e (1).jsonl" --draft-dir C:/Users/User/Desktop/AI_project/receipt/data/role2/category-review-20261016-v1 --dataset C:/Users/User/Desktop/AI_project/receipt/data/role2/split-20261015-v2 --a C:/Users/User/Desktop/AI_project/receipt/data/role2/runs/tfidf-v2-20261015 --b C:/Users/User/Desktop/AI_project/receipt/data/role2/runs/embedding-v2-20261015 --c C:/Users/User/Desktop/AI_project/receipt/data/role2/runs/bert-v2-20261015-seed42 --private-root C:/Users/User/Desktop/AI_project/receipt/data/role2 --out C:/Users/User/Desktop/AI_project/receipt/data/role2/runs/reviewed-comparison-20261016-v1
```

每次使用不存在的輸出資料夾。程式先保存 `evaluation-plan.json` 的輸入／模型指紋，再補跑 Embedding；完成時再次核對來源與模型未變。`reviewed-source.jsonl`、`confirmed-items.jsonl`、`private-predictions.jsonl` 含真實品名，僅留在本機忽略資料夾，不能貼給雲端或提交 Git。`report.json` 與 `comparison.md` 僅含彙總指標。

報告分成全部已確認、與訓練重疊、訓練未見、訓練／驗證／測試皆未見四個子集。重疊比對包含正規化同名及明確連結的群組；不代表已排除所有語義近似品項或證明來源獨立。Macro-F1 平均該子集中有真實樣本的類別，另列每類至少 5 筆的平均；低樣本類別仍有描述性指標，但明確警示不穩定。審核時已展示模型建議，故這不是盲測；排除無法辨識項目亦須揭露。

繪圖使用獨立環境，避免改動模型依賴版本：建立 `data/role2/plot-runtime/.venv`，依 `requirements-plots.txt` 安裝 Matplotlib，再執行：

```powershell
C:/Users/User/Desktop/AI_project/receipt/data/role2/plot-runtime/.venv/Scripts/python.exe experiments/category-models/plot_reviewed_comparison.py --report C:/Users/User/Desktop/AI_project/receipt/data/role2/runs/reviewed-comparison-20261016-v1/report.json --out C:/Users/User/Desktop/AI_project/receipt/data/role2/runs/reviewed-comparison-20261016-v1
C:/Users/User/Desktop/AI_project/receipt/data/role2/plot-runtime/.venv/Scripts/python.exe -m unittest discover -s experiments/category-models -p "test_plot_reviewed.py"
```

輸出三組 PNG／PDF：全部、訓練未見、排除所有舊切分已見名稱。格內是計數，色階是同一真實類別內比例；列為人工答案、欄為模型預測。繪圖腳本只讀彙總報告；預設字型為 Windows 微軟正黑體，可用 `--font` 指定本機字型。

## 已確認資料續訓 BERT（2026-10-16）

續訓沿用完整分類權重與 head，舊 train 作 replay；未確認項目排除。`bert_continuation.py` 依正規化名稱與明確群組排除舊 train/validation/test 曝光，再切分新資料。必須提供與舊 manifest 指紋一致的 `--parent-source`；若舊來源有非名稱群組而沒有跨版本映射，直接拒絕，不能假裝已完成隔離。

下列為本次已執行的重現指令。輸出已存在時會拒絕；不得刪除 test claim 或複製同一測試集來挑選結果。未來實驗應使用新版本與另收集的測試資料。

```powershell
$role2Data = 'C:/Users/User/Desktop/AI_project/receipt/data/role2'
$role2CpuPython = './experiments/category-models/.venv/Scripts/python.exe'
$role2CudaPython = './experiments/category-models/bert-runtime/.venv/Scripts/python.exe'
& $role2CpuPython experiments/category-models/bert_continuation.py prepare --reviewed 'C:/Users/User/Downloads/labeled-items-5092c3e897c490e4041e (1).jsonl' --draft-dir "$role2Data/category-review-20261016-v1" --parent-dataset "$role2Data/split-20261015-v2" --parent-model "$role2Data/runs/bert-v2-20261015-seed42/model" --parent-source 'C:/Users/User/Desktop/AI_project/receipt/data/private/category-review-20261012/labeled-items.jsonl' --private-root $role2Data --out "$role2Data/bert-continuation-20261016-v1"
& $role2CpuPython experiments/category-models/bert_continuation.py check --dataset "$role2Data/bert-continuation-20261016-v1"
foreach ($role2Seed in 42,43,44) {
    & $role2CudaPython experiments/category-models/bert_finetune.py --warm-start --lr 0.00001 --device cuda --seed $role2Seed --dataset "$role2Data/bert-continuation-20261016-v1" --pretrained "$role2Data/runs/bert-v2-20261015-seed42/model" --out "$role2Data/runs/bert-continuation-20261016-seed$role2Seed"
    if ($LASTEXITCODE -ne 0) { break }
}
& $role2CpuPython experiments/category-models/bert_continuation_eval.py --dataset "$role2Data/bert-continuation-20261016-v1" --parent-run "$role2Data/runs/bert-v2-20261015-seed42" --candidate "$role2Data/runs/bert-continuation-20261016-seed42" --candidate "$role2Data/runs/bert-continuation-20261016-seed43" --candidate "$role2Data/runs/bert-continuation-20261016-seed44" --private-root $role2Data --out "$role2Data/runs/bert-continuation-comparison-20261016-v1"
```

固定 lr1e-5、batch16、max_length32、FP32、最多10輪、patience2。epoch0 保留原模型；只依 validation loss 保存及選擇種子，最後才執行一次 parent 與勝出候選的相同 test 比較。模型與資料指紋凍結於 `evaluation-plan.json`，單次標記留在資料集資料夾；含名稱的預測只留本機。

本輪 train905（305真實、600合成）／validation50／test50。選出 seed44 epoch1，validation 94%→96%，test 80%→82%（40/50→41/50），3筆改善、2筆退步。測試結果未回饋調參；只屬小幅描述性改善。這批來源曾參與上一輪模型比較，且人工審核看過模型建議，不能稱為全新盲測；運動、住宿沒有 test 樣本。

完整彙總與前後混淆矩陣：`C:/Users/User/Desktop/AI_project/receipt/data/role2/runs/bert-continuation-comparison-20261016-v1/comparison.md`。權重：`C:/Users/User/Desktop/AI_project/receipt/data/role2/runs/bert-continuation-20261016-seed44/model`。本輪未部署或公開模型。
