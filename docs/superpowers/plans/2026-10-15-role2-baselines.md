# 角色 2：固定切分 A/B 模型訓練

> 依使用者在資料 v2 審查完成後的「可以繼續做」指示，沿用既定分類規格，由本聊天直接實作並以 TDD 驗證。

**Goal:** 在相同 v2 固定切分上訓練 A/B、驗證儲存重載與 CPU 1000 筆速度；保留最後測試集，結果只宣稱開發驗證。
**Spec:** docs/team/overview.md 角色 2 第 3.4 項；openspec/changes/add-matching-system/specs/model-evaluation/spec.md；docs/category-models-brief.md。
**Architecture:** 新增 fixed_split_train.py 與 fixed_split_data.py，沿用 A 的模型建構及 B 的 FrozenEncoder。舊 CV 程式不改。套件安裝在角色 2 獨立實驗 .venv。模型、特徵與逐筆資料只寫到主專案 data/role2/runs，公開文件只有彙總指標。

## 約束

- 真實品名只能由本機腳本離線處理；不得讀取或列印給雲端 AI。編碼器預先在獨立下載程序取得公開權重，訓練程序關閉 HF 網路與 telemetry。
- 不改 src/api、src/receipt、其他角色文件或共用環境。不使用 GPU。
- 固定 train/validation/test，只有 train fit，validation 計算開發分數；本輪完全不對 test 做預測／評分。單純驗證切分來源及指紋不算使用 test 調參。
- A/B 同樣 C=1、class_weight=balanced、max_iter=2000、seed=42，不調參。B 是凍結 BGE-small CLS+L2，CPU FP32，max_length=512，batch=16。
- 真實與合成來源保持原樣；禁止把合成資料標為 human_confirmed。少於5筆的類別不算 macro-F1；目前 validation 每類不足5，macro-F1=null，accuracy 只供流程檢查。
- 不覆寫既有資料集、編碼器或模型輸出。每次新 run 目錄；輸出保留資料指紋及訓練來源統計。
- 模型重新載入後，驗證機率需一致。測速使用訓練名稱循環1000筆，完整分類流程、暖機、無向量快取；不是新增準確率證據。

## Tasks

- [x] 寫 fixed_split_data.py：驗證 snapshot、完整來源/分割指紋、5筆門檻計分；虛構測試涵蓋篡改、來源污染及不足5筆不計分。
- [x] 寫 fixed_split_train.py：A/B共用run介面，只fit train、預測validation；存模型、重載一致、全流程CPU測速；CLI只印彙總。以小型本機BERT假編碼器測試B整條流程，不下載測試模型。
- [x] 在專用環境取得固定版本公開BGE模型，先跑全部實驗測試，再離線跑A與B真實資料；兩者用同一份資料manifest，不回顯任何真實名稱。
- [x] 公開彙總 docs/results/classification-baselines.md、更新實驗README與任務3.4，保存來源與測試證據。做獨立程式審查，修正後完成交付。

## Review focus

- 訓練詞表不得看見 validation/test；輸出錯誤訊息不得帶私人輸入。
- B的載入、fit、編碼與完整推論時間分開，模型大小包含編碼器，不用LR檔案大小假裝部署成本。
- 既有run及輸入不得覆寫，訓練途中變更來源時不可交出成功報告。
- 同一來源統計與指紋讓A/B能對照；驗證預測不代表獨立最終測試。
- 小模型測試只能證明管線，不代表正式BGE效果。合成訓練占多數的限制需揭露。

## Ledger

- 起點：codex/role-2/category-models，v2資料成果未commit，保留全部既有變更。
- 前置：使用者已確認資料檔路徑並要求繼續；18筆是每類簡寫數量，沒有18項待決定標籤。運動裝備繼續排除。

- 已完成：新增固定切分讀取、來源指紋重查、低樣本計分與 A/B 共用訓練 CLI；不更動舊 CV 程式。
- TDD：先見新增測試失敗，再完成實作；獨立審查發現空 validation 會跳過重載比較，先新增會失敗的回歸測試，再加入 10 筆 train 探針與有限機率檢查。修正後 targeted 9/9、實驗全套 49/49 通過；主程式 154/154 通過。
- 專用實驗環境：Python 3.12.14、torch 2.8.0+cpu；套件一致性檢查通過。固定版公開 BGE 權重已下載到主專案 data/role2/models，逐檔核對上游雜湊。
- 實際離線 run：tfidf-v2-20261015 與 embedding-v2-20261015；各以新程序依序執行，train 643、validation 7、test 未評分；兩者驗證各答對 6/7，所有類別不足 5，macro-F1=null。
- 完整 CPU 1000 筆推論：A 0.014 秒、B 2.791 秒。模型重載後 7 筆 validation 加 10 筆 train 探針一致；A/B 資料 manifest 指紋一致。
- 審查複查：空驗證集重載錯誤、NaN、錯誤維度、負值與未正規化機率均拒絕，不產生成功報告；沒有殘留實質缺陷。
- 公開結果已寫入 docs/results/classification-baselines.md，實驗 README 與角色 2 的任務 3.4 已更新。所有含品名輸出只保存在主專案 data/role2/runs；不改其他角色程式，未 commit、合併或發布。
