# 角色2：Claude審查修正與重新驗收

2026-10-18 Asia/Taipei。回覆 `CLAUDE-REVIEW-R2-20261018-121500-5e07`，工作ID `R2-REVIEW-FIX-20261018`。起點 `8bf1722`；本輪必修完成，**待Claude複核，尚未整合主分支**。

## 逐項處理

| 審查項目 | 處理結果 |
|---|---|
| 1 空白品名契約 | overview第6節明列非空白字串；保留BERT的ValueError。上傳略過空白明細由角色1 followups處理，角色2沒有改invoices.py。 |
| 2 BERT遠端model來源 | Settings.from_env對bert＋非空repo＋type=model明確拒絕，容器在下載前一行退出；有效Space及無repo本機設定仍可用。test_container只更新MainTests舊環境fixture，不改原本啟動順序斷言。 |
| 3 過期文件 | 更新overview第4節、第5.10節、第6節與公開範圍決定；第13.11節改寫並移至13.10前。design/proposal歸角色1，替換文字見下方。 |
| 4 鎖範圍 | 改為逐批取得與釋放鎖；測試5筆／batch2，釋放時已完成批次數為1、2、3。不保證鎖排程公平或即時延遲上限。 |
| 5 內部原因碼 | 本輪未實作。保留對外固定category_model_unavailable；固定、去識別的內部原因碼可另案加入並驗證不含路徑、輸入或秘密。 |
| 6 真ML小測試 | 新增隨機小型BERT與虛構tokenizer的離線CPU實載測試，檢查並行、長文字截斷、缺分類head拒絕；缺少ML套件時跳過。無網路下載，沒有真實品名。 |
| 7 強制終止清理／hash成本 | 本輪未實作。SIGKILL仍可能留下暫存目錄；自動清理需先有程序所有權／鎖，避免刪除其他下載。多次hash的效能成本仍在，不在沒有替代完整性保障時移除。 |
| 8 Compose與token | REPO、REVISION改為必填插值，缺任一值config即拒絕。文件建議fine-grained Read僅限此Space；既有token未擅自輪替。 |
| 9 歷史測試集敘述 | classification.md與selected-model改連既有8bf1722彙總：全真實43/50、25%合成42/50，非新盲測、不能判定穩定優劣。本輪沒有開啟、hash、複製或評分原test。 |
| 10 驗收可重現 | 將三個Docker驗收工具移為可攜scripts入口，新增build_category_acceptance.py保存來源hash；只建立來源context，不推送image。 |

新回歸先得到2個預期失敗（設定未拒絕、整批只釋放一次鎖），修正後通過。獨立Codex審查另發現驗收腳本的argparse變數被Docker引數遮蔽，已改名並以local模式實跑通過；複查沒有確認的新缺陷。這不代替Claude審核。

## 本輪驗證

使用主目錄 `data/role2/service-runtime-20261017/Scripts/python.exe`，CPU、虛構資料與暫存DB：

- `-X utf8 -m unittest tests.test_category_review tests.test_category_tiny_bert tests.test_category_model tests.test_category_remote`：18項通過。
- `-X utf8 -m unittest tests.test_container.MainTests tests.test_category_review`：7項通過。
- `-X utf8 -m unittest discover -s tests`：472項全部通過，37.362秒；小型真BERT確實執行，缺head時的transformers警告為測試預期。
- 將torch、transformers、safetensors、huggingface_hub、tokenizers以import hook禁止載入，再執行相同discover：472項中471項通過、1項正確跳過，38.875秒。這是缺選用套件的相容性模擬，不冒稱另一個全新Windows虛擬環境。
- `openspec validate add-matching-system --strict`與`git diff --check`通過。
- Compose缺REPO、缺REVISION分別被拒絕；56個image來源檔hash與修正後worktree一致。

完整回歸最初有1失敗、2錯誤，原因是container MainTests仍用type=model舊fixture；更新為有效Space fixture後得到上述472通過。沒有降低既有斷言。

### Docker實跑

image：`receipt-role2-acceptance:review-20261018`
image ID：`sha256:24fe4623f858449eb9900c841fcdaaa2936fa16ff09bcd61308ffe4fea3a4e13`

由標準Dockerfile與56個tracked來源檔建置，排除src/web、資料與權重。使用`--pull`並重用可用build cache，**不是本輪無快取建置，也不是repo根目錄完整compose build**。context的acceptance-source.json記錄基準HEAD 8bf1722、working_tree_dirty=true及逐檔SHA；建置時包含本次Settings和逐批鎖修正，建置後已比對所有來源hash一致。這個manifest不含私人資料。

| 情境 | 實際結果 |
|---|---|
| 全新volume、無token | health unavailable；classify 503；上傳202且3筆虛構資料的job failed；模型檔0；服務照常啟動 |
| 本機模型唯讀掛載、network none | health bert；classify 200；上傳202、job done、profile 200 |
| 全新volume、受保護遠端下載 | 同上成功；固定revision與權重SHA一致；torch 2.8.0+cpu、CUDA build為null |
| local與remote的新容器重啟 | 移除token掛載、network none，兩種情境均成功完成相同HTTP流程 |
| 正式base＋category Compose | 全新專用volume、runtime secret唯讀、主機loopback health 200；分類／上傳／profile通過；模型7檔，HF cache token不存在 |
| 憑證稽核 | 本輪6個容器logs／inspect及image history的本機token字串命中0；6個容器均已停止 |
| 遠端模型volume | 只有manifest允許的7個推論檔，無額外檔案或暫存cache |

固定來源：`lee851104/receipt-model-lab`，Space revision `29b655b96b4ced268bb0c3994e901c72dfd65420`；模型SHA256 `16997425a9b36629469d60f506d52c2771bab1e6f3a3ea1465c2c0a316fa3e79`。憑證只在本機讀取與唯讀掛載，未寫進Git、image或聊天。token稽核僅涵蓋表列範圍，不能推論整台電腦完全沒有秘密。

首次build因Docker engine未啟動失敗，啟動Docker後另建v2 context成功；失敗與成功log均保留。專用volume／停止容器保留供查核；沒有停止其他角色服務，沒有使用GPU或修改模型。

## 重現方式

於角色2 repo根目錄執行；需Docker及安裝huggingface_hub的Python。token須事先以本機hf auth login登入，推薦僅限該Space的fine-grained Read。以下PowerShell範例刻意使用新的輸出目錄；腳本以目前checkout的正式Compose和HTTP probe執行，不讀datasets：

```powershell
$pythonExe = 'C:/Users/User/Desktop/AI_project/receipt/data/role2/service-runtime-20261017/Scripts/python.exe'
$dockerExe = 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'
$contextDir = 'C:/Users/User/Desktop/AI_project/receipt/data/role2/docker-context-review-NEW'
$evidenceDir = 'C:/Users/User/Desktop/AI_project/receipt/data/role2/review-docker-NEW'
$imageTag = 'receipt-role2-acceptance:review-new'
& $pythonExe scripts/build_category_acceptance.py --context $contextDir --image $imageTag --docker $dockerExe
& $pythonExe scripts/run_docker_acceptance.py noauth --image $imageTag --out-dir $evidenceDir --docker $dockerExe
& $pythonExe scripts/run_docker_acceptance.py local --model-dir 'C:/Users/User/Desktop/AI_project/receipt/data/role2/service-model-20261017-v1' --image $imageTag --out-dir $evidenceDir --docker $dockerExe
& $pythonExe scripts/run_docker_acceptance.py remote --image $imageTag --out-dir $evidenceDir --docker $dockerExe
& $pythonExe scripts/check_compose_remote.py --image $imageTag --context $contextDir --out-dir $evidenceDir --docker $dockerExe
# 使用前述輸出的實際容器名稱；可重複--container。REMOTE_NAME-models是該次專用模型volume。
& $pythonExe scripts/audit_remote_runtime.py --image $imageTag --container REMOTE_NAME --container REMOTE_NAME-offline --model-volume REMOTE_NAME-models --out "$evidenceDir/runtime-audit.json" --docker $dockerExe
```

每條命令應先確認exit code為0再繼續。audit範例僅檢查列出的兩個容器；本輪實跑另列local、noauth及Compose，共6個。build腳本不接受既有context，audit不覆寫既有輸出。腳本固定使用上列已選定的模型版本，不是任意模型的下載工具。

可提交彙總：[classification-review-fixes-20261018.json](classification-review-fixes-20261018.json)。本機證據位於主目錄`data/role2/review-docker-20261018/`，包括noauth/local/remote各JSON、`receipt-r2-compose-1792296031618029700/result.json`、runtime-audit.json、config-and-source-check.json。測試log為主目錄data/role2的review-regression-20261018-v2.log及review-no-ml-20261018.log；image來源manifest在docker-context-review-20261018-v2。

## 給角色1的design／proposal替換文字

> 分類模型權重維持受保護，不公開。首次取得模型時，使用本機只讀憑證，從Hugging Face Space下載固定commit，並核對指定SHA256、白名單manifest及分類標籤。Docker透過runtime唯讀secret提供token；token不進環境值、Git或映像檔。全新環境沒有憑證或下載失敗時，分類器顯示unavailable，其餘服務仍可啟動；已有完整且已驗證模型時，可以無憑證、無網路重啟。設定錯誤（例如BERT遠端type=model或不完整固定來源）在啟動時明確拒絕。首次下載需要該Space的讀取權限與網路，因此不能宣稱陌生使用者無憑證即可取得真BERT。

請角色1套用至proposal來源／限制段、design D7與相關風險；角色2不修改角色1正在編輯的檔案。整合時保留各角色overview新增內容，處理13.11編號衝突。

本輪是角色2分類服務的修正與容器驗收，屬性使用fake、DEMO_MODE=0。尚非Qwen、300人seed、前端或全隊整合驗收；也沒有產生新的準確率證據。必修項完成，建議5與7保留後續，Claude複核及合併仍待。
