# 角色2受保護遠端下載與Docker驗收

沿用 bert-next25-20261016-v3。工作分支 codex/role-2/category-models；起點d44c5cd。
使用者已指定在本機安裝Docker Desktop，不建立另一個HF Space；測試集不開啟、不hash、不copy、不重新評分。

## 交付契約
- 來源是既有Protected Space `lee851104/receipt-model-lab`，repo_type=space。
- 40位完整revision、固定model.safetensors SHA256；先讀models/manifest.json，只下載其BERT推論白名單，轉成既有service manifest，全部驗證後發布新目錄。
- HF_TOKEN_FILE或本機HF登入讀token，不允許token命令列參數／log／Docker build ARG。Docker用runtime唯讀secret file。
- 新模型/資料volume與臨時埠；正式容器入口下載、健康檢查bert、虛構分類/CSV/job/profile；無token新目錄unavailable，已下載模型可離線重啟。不改其他服務、資料庫或GPU。
- Windows新venv已於前一回合驗收；本次Docker/Linux實際通過後才能勾3.9，不能拿依賴解析代替實跑。

## 工作清單
- [x] 下載器、Settings、容器接線和權重pin檢查；7項新測試先missing-module RED，後PASS，完整467/467（28.498s）。
- [x] CLI與runtime secret Compose範例。
- [ ] 本機HF登入、固定revision遠端可取與匿名拒絕。
- [ ] Docker Desktop/WSL2安裝、daemon正常與乾淨image build。
- [ ] 全新volume下載和正式入口HTTP驗收、失敗/離線重啟驗證。
- [ ] 最終回歸、獨立程式審查、分段commit、交接讀回。

## 環境紀錄
- 2026-10-17：無docker/podman/WSL、無本機HF token。使用者選本機Docker並請協助登入。
- 已開本機hf auth login視窗與HF身分確認頁；密碼/token由使用者直接輸入，不經聊天。
- Docker官方Windows安裝包636811696bytes，Authenticode Valid/Docker Inc，per-user/wsl-2安裝exit0，CLI Docker29.8.2；daemon尚待WSL。
- WSL管理員安裝被automatic approval review拒絕，要求取得啟用Windows功能的具體同意；已詢問使用者。不能繞過拒絕、不自動重開機。

## Review Focus
- 惡意manifest路徑/額外檔、錯hash/分類順序、mutable revision在網路動作前拒絕。
- 任何失敗不發布半模型、不覆蓋既有不相關檔；錯誤不回傳第三方文字或token。
- 憑證不進image/compose env/git；容器來源型別與hash傳入正確；pin mismatch不得啟用舊模型。
- 明確區分mock測試、Windows新環境、真正Docker和主分支整合；無test集存取。

- 使用者要求一步一步帶領安裝，已開管理員終端並提供wsl --install --no-distribution --web-download；等待使用者回報，不自動執行被拒絕的管理員變更。
