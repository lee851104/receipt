# 獨立發票屬性實驗：先讀這份

這是使用者授權的本機模型比較實驗，不是正式功能。所有改動限此資料夾。

- 不修改 ../../src、../../configs、../../tests、根目錄 HTML、pyproject.toml 或現有 .venv。
- 不啟動正式報表 build，不自動把模型預測灌入正式資料。主專案由其他工作維護。
- private/ 是真實 CSV 副本、品名、店家及暫定參考答案；results/ 也含真實資料。兩者禁止提交或上傳。
- models/ 與 runtime/ 是可刪除再下載的本機資產，不提交。不使用 HF API，不上傳發票。
- 入口與目前成果見 README.md、RESULTS.md；範圍與決策見 PLAN.md。
- 追加的四項指標流程見 FOLLOWUP-PLAN.md、METRICS.md、run_followup.py、followup_report.py；54 筆補充情境是合成診斷資料，不是真實獨立測試集。
- 模型輸出是「16 個屬性欄位」，不是互斥的 16 類。布林 null 代表未知，不能當 false。
- 人工基準由本次助理依品名初步標註，尚未由使用者複核；模型準確率不得當成正式成效。
- 未來接入需在正式專案另做 adapter，取代 attributes.describe/channel_of 的資料來源並處理目前對 category 的依賴。
- 執行器使用 CPU、2 threads、Windows IDLE priority，依序跑模型，結束即關閉子行程。

## 已完成的選型

- 選 Qwen3-4B-Instruct-2507 Q4_K_M，搭配 bulk_rule.py 與 sugar_guard.py；固定資產與設定見 SELECTED_MODEL.json。
- 可供日後 adapter 讀取的結果：results/followup/selected-output.json，含來源 SHA、35 筆明細及待複核狀態；目前沒有被主程式引用。
- 真實資料純模型 F1 44.44%，加規則後 94.12%；甜度驗證是在看過錯誤後加入，後者只是開發資料事後回測，不是獨立驗證。
- production_ready=false；沒有人工確認的獨立測試集。7 個 basic 旗標 F1 85.39%，不能把這份實驗當作已完成移除原 10 類的整合。
- 實驗測試 22 項、主專案 Python 77 項、最後 JavaScript 82 項通過；其他工作對主專案的同步修改均保留。
