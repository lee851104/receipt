# 分類比較報告：待本機隱私複核

BERT 三種子微調與同一測試集的 A/B/C 比較已在本機完成。完整彙總、混淆矩陣、成本與限制保存在主專案 Git 忽略目錄：

`C:/Users/User/Desktop/AI_project/receipt/data/role2/runs/comparison-v2-20261015/report-detail.md`

本機 audit_synthetic.py 的正規化子字串掃描偵測到 1 個名稱片段重合；尚未確認是否為一般詞彙或需要遮蔽的內容。雲端 AI 沒有檢視命中的真實名稱。本檔先只保留狀態，不公開完整報告；需由使用者在本機判讀，再完成任務 3.7 的公開文件檢查。

任務 3.5 的微調、儲存重載與測試預測已完成。私人權重、逐筆品名與預測沒有加入 Git，模型尚未公開。

命中名稱與對應行號只寫入本機私人複核檔：

`C:/Users/User/Desktop/AI_project/receipt/data/role2/runs/comparison-v2-20261015/privacy-review.json`

請在本機查看，不要將真實品名貼回雲端聊天；如果 line_numbers 為空，表示是跨行正規化拼接造成的子字串命中，仍由本機判讀。
