# 品名分類實驗：A 與 B

只讀品名，預測 0～9 的消費類別。A 使用 TF-IDF，B 使用固定的中文 Embedding，兩者都以邏輯迴歸分類。此為獨立實驗，不改主程式、正式對照表或網頁。C 尚未實作。

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

## 訓練

```powershell
experiments/category-models/.venv/Scripts/python.exe experiments/category-models/tfidf_lr.py train --data experiments/category-models/data/items.jsonl --out experiments/category-models/outputs/tfidf-run-01
```

每次使用新的輸出資料夾。固定字元 1～3 gram、sublinear TF、C=1、balanced class weights、seed=42、CPU 單執行緒。不調參。

資料不足時採三折「開發交叉驗證」：

1. 以群組為切分單位。至少三個群組的類別可參與驗證，稀少類別只放在每折的訓練集。
2. 每折重新建立 TF-IDF 詞表與訓練分類器，每個受評品名恰好驗證一次。
3. 對照「永遠猜該折訓練集最多類別」的基準。Macro-F1 只平均有驗證樣本的類別，完整 10 類分數不足時為 `null`。
4. 另用全部已確認資料訓練最終模型。它沒有獨立測試成績，不列訓練集準確率充當效果。

若不足兩個類別各有三個群組，仍可訓練至少兩類的模型，但報告會顯示無法交叉驗證。之後蒐集足夠資料再建立固定 70/15/15 的共同實驗資料，本次程式尚未實作該最終測試流程。

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
