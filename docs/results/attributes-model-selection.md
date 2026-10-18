# 角色 3：RTX 4060 屬性模型選型

日期：2026-10-15。選用 **Qwen3-4B-Instruct-2507 Q4_K_M**，資產與 revision 固定於 `configs/attribute-models.json`。原 CPU 實驗紀錄保持原樣。

Windows、RTX 4060 8GB、NVIDIA 610.88、llama.cpp b11557 CUDA。`CUDA0` 可見；0.5B CPU 與 CUDA 的測試 prompt 皆有回應。GPU 評估時沒有其他模型工作，完成後關閉本次啟動的 server。

沿用實驗資料夾的 54 筆凍結合成資料、prompt-named-v2、解碼器、bulk_rule、sugar_guard 與 metrics.score。設定 temperature=0、seed=42、batch=3、context=4096、threads=2、gpu_layers=99、enable_thinking=false。結果計算沿用原實驗的 16 屬性指標；不是 23 欄真人複核成績。

| 模型 | GGUF GB | 純模型 macro-F1 | 加規則 macro-F1 | 加規則 micro-F1 | 第一次秒數 | 重跑秒數 | 格式失敗批次 |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen3-4b | 2.50 | 84.50% | 91.24% | 90.11% | 26.25 | 25.53 | 0 |
| qwen3-8b | 5.03 | 83.32% | 89.57% | 88.89% | 41.18 | 40.30 | 0 |

兩次結果的逐欄統計相同。時間包含載入與逐批 HTTP 呼叫，只是這台電腦的兩次觀察；不宣稱穩定吞吐量。4B 在這組診斷資料較快且指標較高，所以維持原選型。

限制：合成資料早已參與開發，不是獨立真實 holdout；本次沒有重建原三月的助理初稿評估。本次選型時尚未完成 100 筆人工複核。10/15 後續已由使用者確認新版 prompt 的 100 筆模型輔助標註，結果見 [attributes.md](attributes.md)；那是不同 prompt 的人工複核結果，非盲標，不能與本表混稱同一套評估，也不代表 API／資料庫整合已完成。

重現（在角色 3 worktree，先確認顯卡無其他訓練）：
```powershell
& 'C:\Users\User\Desktop\AI_project\receipt\.venv\Scripts\python.exe' scripts/evaluate_attributes.py --runtime 'C:\Users\User\Desktop\AI_project\receipt\runtime\llama-b11557-cuda\llama-server.exe'
```

模型需先依 configs 中的固定 revision 下載到 models/，腳本執行前會驗 SHA256。原始回應保留於被 Git 忽略的 data/role3；公開 JSON 只有彙總指標與資產識別。

來源：[4B 量化模型](https://huggingface.co/bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF)、[Qwen 8B GGUF](https://huggingface.co/Qwen/Qwen3-8B-GGUF)。
