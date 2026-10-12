# 發票屬性模型獨立實驗

先讀 **CLAUDE.md**（操作邊界）、**RESULTS.md**（實測結果）、**METRICS.md**（四項指標）、**INTEGRATION.md**（日後接入）。

本資料夾不被正式報表匯入，不改根目錄套件、設定或 HTML。Python 僅用標準函式庫，不需安裝套件或使用 API key。這次只下載公開模型，不會把真實發票送到 HF。

已選 **Qwen3 4B + 大量購買規則 + 甜度文字驗證**，供離線輔助標註。設定見 `SELECTED_MODEL.json`，逐列成果見 `results/followup/selected-output.json`。真實資料純模型 F1 44.44%，加規則事後回測 94.12%；沒有人工確認的獨立測試集，尚不能直接投入正式自動分類。完整比較見 RESULTS.md。

## 檔案
- `private/0301-0331.csv`：三月 CSV 原樣副本。使用者提到 0301-0330，實際找到的是 0301-0331。
- `private/prepared.json`：35 筆明細及按店家、品名、數量分開的 28 組資料，有來源 SHA256、列號及 ID。
- `private/human-review.json`：等待使用者填寫的參考答案；目前沒有完成使用者人工審核。
- `private/draft-reference.json`：助理初步判讀的診斷對照，不能當正式標準答案。
- `models/`：四個固定 revision 的 Q4_K_M 模型，共約 6.21 GB；新增 Qwen3 4B 為 bartowski 轉換版本。
- `runtime/`：官方 llama.cpp b11557 Windows CPU x64 與下載 SHA256 manifest。
- `results/<模型>/`：逐批原始回應、耗時、完整預測、逐列標註與差異報告，均含私人資料。
- `prompt-named-v2.txt`：四個模型共用的具名標籤提示；`prompt.txt` / `prompt-array-v1.txt` 保留初輪陣列提示。`lab_core.py`：資料格式、驗證、逐列接回。
- `test_lab.py`：資料相容性與未知值的邊界測試。
- `benchmark_cases.json`：推論前凍結的 54 筆合成情境，不是真實發票；每個屬性均有正例。
- `metrics.py` / `test_metrics.py`：Accuracy、Precision、Recall、F1 與缺失／未知值計分測試。
- `bulk_rule.py` / `sugar_guard.py`：獨立規則與對應測試；不覆寫原始模型輸出。實驗測試共 22 項通過。
- `results/followup/`：四模型補充測試、Qwen3 真實資料測試，以及可重算的 metrics.csv / comparison.json；仍屬私人結果。

private、results、models、runtime 都由本資料夾的 .gitignore 排除；不要移到公開資料夾。

## 四項指標比較重現（PowerShell，在專案根目錄）
已有 private/prepared.json 和 private/draft-reference.json 時：

```powershell
python -B experiments/receipt-attributes/download_extra.py
python -B -m unittest discover -s experiments/receipt-attributes -p "test_*.py"
python -B experiments/receipt-attributes/run_followup.py
python -B experiments/receipt-attributes/followup_report.py
```

followup_report.py 重用原三模型的 March 結果，並核對來源、提示 hash 與完整 ID 覆蓋。首次建立環境時也要先跑下方第一輪流程。所有模型的補充測試用同一份提示；不使用答案作為推論輸入。只重跑 Qwen3 真實資料可用 `run_followup.py --models qwen3-4b --real-only`。

## 第一輪重現
```powershell
python -B experiments/receipt-attributes/download_models.py
python -B experiments/receipt-attributes/prepare_data.py
python -B experiments/receipt-attributes/make_draft_reference.py
python -B -m unittest discover -s experiments/receipt-attributes -p test_lab.py
python -B experiments/receipt-attributes/run_models.py
python -B experiments/receipt-attributes/evaluate.py
```

先少量測試可加 `--models 0.5b --limit 3`。同模型重跑前，舊結果會整份移到 results/archive/，避免舊的完整標註混進新的部分結果。完整執行依序跑 0.5b、1.5b、3b；CPU 2 threads、IDLE priority，不使用顯卡。每個模型結束或出錯都只會關閉它啟動的 server，不會關閉其他服務。不要同時另開一份 run_models.py。

若有任何批次未通過驗證，run_models.py 會在跑完所有指定模型後回傳 exit code 1；檢查 predictions.json 的 failures，仍可執行 evaluate.py 查看結果。只有完整成功的模型才會產生 annotated-rows.json。不要把部分結果直接接進主程式。

本輪使用現成模型推論，沒有微調或訓練。參考初稿固定綁定這份 CSV；換資料後，需另建對應的人工標註，不能沿用舊 ID 的答案。prepare_data.py 不覆寫已存在的 human-review.json；換資料時也需核對其 source_sha256。

這是實驗工具，沒有自動接進正式產品。效能、資料不足及標註分歧需看 RESULTS.md。真實資料只涵蓋三月；另有 54 筆合成診斷情境，仍不能證明全部 16 項屬性的真實泛化能力。

## 模型來源
- https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF
- https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF
- https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF
- https://github.com/ggml-org/llama.cpp/releases/tag/b11557
- https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507 （新增模型原始來源）
- https://huggingface.co/bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF （實際下載的量化轉換版本）

0.5B、1.5B 模型頁授權 Apache-2.0；3B 使用 Qwen Research License，正式部署前必須另檢查授權適用條件。下載完整性依官方 HF LFS SHA256 與 GitHub asset SHA256 驗證。程式不執行遠端模型自訂 Python 程式。
