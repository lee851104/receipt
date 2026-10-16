# 角色2多種子分組CV Implementation Plan

> For agentic workers: Use executing-plans to implement task by task.

Goal: 在現有開發資料固定5折，比較25%與66.3%合成配方在共同seed42/43/44的成對結果。
Architecture: 重用bert_ratio_cv的split／train；新增獨立輸出與seed override，既有預設不變。新wrapper固定protocol，完整檢查30個run後才彙總。
Tech Stack: Python3.12、既有CPU/CUDA環境、PyTorch／transformers；不裝套件。
Spec: 使用者本輪與前輪已授權的分組、共同起點／lr／seed方案；本檔記錄具體實驗規格。

## Global Constraints
- worktree receipt-role2/receipt，基準b9fbb05，只改角色2認領檔案；真實名稱不上雲端。
- 既有CV plan／fold檔案唯讀；原test不開、不hash、不複製、不評分；Python audit hook防護。
- 5折不變，合成子集不變；種子42/43/44與2配方交叉，30run。不是增加資料量，禁止把重複OOF當獨立樣本。
- 公開encoder、lr2e-5、batch16、maxlen32、FP32、wd.01、clip1、最多10輪、patience2／min_delta1e-4；內層選epoch，外層每run一次。
- 現有355筆355group，無多筆群；明確揭露無來源／語義家族隔離證據。
- 每組相同epoch上限但不同更新步數，報告實際步數；本輪不擴充等計算量比較。
- 私人結果data/role2/bert-multiseed-cv-20261016-v1；不改目前候選權重、API或HF展示。

## Review Focus
- 同fold不同seed重複資料不能當15個獨立fold；不以OOF三倍筆數偽裝樣本增加。
- 新seed／輸出API不能覆寫原CV；拒絕非法seed與相同root。
- 彙總須核對plan/config/model/prediction指紋、seed/fold/regime、OOF完整性與成對對齊。
- 固定encoder與設定，資料抽樣不隨初始化seed變。
- 早停只看inner，外層不進梯度或epoch選擇。

## Task 1: 工具與虛構回歸
- [x] 新test_bert_multiseed_cv.py：設定、test guard、分組、seed/輸出隔離、30run完整彙總／缺失／竄改；先看失敗。
- [x] bert_ratio_cv.train_fold新增seed=None,output_root=None，保持原預設；seed override必須獨立root。
- [x] bert_multiseed_cv.py prepare/load/train/summarize，固定父plan/config與seed集合，拒絕未完成或竄改結果。
- [x] CPU新測試與完整實驗回歸、主tests，預期全通過；commit。
Interface: wrapper consumes verified parent folds and reports; override config includes initialization_seed, parent plan fingerprint preserved.

## Task 2: 實驗與交接
- [ ] prepare新protocol，group彙總與GPU核對。
- [ ] 30run逐一執行，進度與失敗保留；每個seed內使用同fold／同合成資料。
- [ ] 彙總：每seed五折OOF、跨seed平均與SD、各fold seedSD、15對差值、類別F1（至少5真實樣本）、步數。
- [ ] 獨立review依Task1回歸，修重要問題；結果圖／文件、README、commit與共用交接。
Interface: result doc reads aggregate summary only; no raw name printing.
Validation: 主python -m unittest discover -s tests；模型CPU python -m unittest discover -s experiments/category-models -p test_*.py；繪圖另環境。
No repeated full-suite runs after docs-only changes.

## Ledger
- Pre-flight: 設定override要與wrapper預期config一致；舊summary不可用於新override outputs，因此新wrapper獨立summary。
- Ruling: 使用者已授權共同設定的分組CV；實作採有界擴充，直接執行不重問同一許可。
- Setup: 沿用現有git-linked worktree；既有測試結果不作本輪驗證。

- Task1完成：新測試先缺模組3fail再3pass；完整回歸93項92pass/1plot skip；主tests154pass，獨立plot1pass。
- 最終獨立複查：無資料洩漏／覆寫／偽增樣本缺陷；發現P2 epochs上限漏驗證。新增11/0/True回歸3個子案例先失敗，修正type=int且1..10後完整94項93pass/1plot skip。只此一項重要問題，無deferred minor。
- Reviewer未查私人內容/真encoder/結果：由本機prepare核對355單例群、encoder指紋與完整30run驗證補齊，不由雲端讀名稱；這不是Claude正式審核。
- Task1 commits b9fbb05..6e95c85及本次修正；原CV預設不變，實際parent epochs=10，私人protocol已固定。
