# 角色4展示、Docker與GitHub交付驗收

工作ID R4-DELIVERY-20261017；2026-10-17 Asia/Taipei。角色4起點4241fd6，合併角色1 d1ed44a 的提交 ef10609；合併僅overview有交接段落衝突，保留兩方內容。待Claude審核，未合併main。

## 交付內容
- 新版九幕GIF：登入、二選一入口、品項月報、文字雲、上傳、配對列表、放大連線圖與外置摘要、計算明細、帳號管理。
- 展示來源只用已追蹤公開v1合成月報與tests/web-v2-fixtures.cjs；每幕粉紅字條標示虛構資料／模擬API，全部/api/被攔截。不是後端或真模型實錄。
- 修復舊腳本等待profile首頁及overall-score的失效選擇器；新增manifest限定本次九張影格，GIF 1366×900、每幕2.2秒、循環、589195 bytes。SHA256 903b0a9388022af9d7127d5bd43ec3ebd8f7dc7b4c7a5f455dc9e32ee1c867cb。
- README改為實際Compose／start.bat操作與新版導覽，v1維持原型標示及原網址。所有共享資料／程式留在原位置。

## 實際Docker驗收
Docker Engine29.8.2，Linux containers。只從Git追蹤的src、configs、Dockerfile、.dockerignore、兩份requirements和Compose建立98檔context；不讀本機.env／私人來源／權重。
- docker compose --project-name receipt-role4-delivery-20261017 --env-file runtime/role4-delivery-context/empty.env -f runtime/role4-delivery-context/docker-compose.yml build --no-cache：成功。
- Image sha256:0e9a3a7bdfdab0f055a10eeb46132661dee61237cc00f8b902e71a810a67eeef。
- 正式Compose不改；8000已有服務，驗收另加acceptance.override.yml，只覆寫埠為127.0.0.1:0:8000；project／db與models volume全新。fake/fake，DOCKER_LLAMA_SERVER_URL=http://127.0.0.1:9，沒有GPU或模型下載。
- compose up -d --no-build後32768可用。RECEIPT_TEST_URL=http://127.0.0.1:32768、RECEIPT_ISOLATED_DELIVERY=1、RECEIPT_DELIVERY_ID=r4_20261017，node tests/web-v2-delivery-browser.cjs --prepare通過。
- 沒有route.fulfill：正式HTTP註冊2名虛構使用者，各上傳40筆CSV，worker done，月報40筆、配對95%、explain18格、Chromium登入兩大選項／月報／列表／關係圖／明細／返回／設定／登出／demo切換皆通過，pageerror0。
- compose up -d --force-recreate --no-build換新容器至32769，同探針不帶--prepare再通過；不是再次建立帳號或上傳，證明原帳號／月份／品項與配對保留。
- docker run --rm --network none --entrypoint python [image]檢查/app：81檔、禁用資料／權重／.env／壓縮檔0，src/web_v2存在、src/web與rawdata/data/models/.git不存在。只是檔案邊界檢查，不冒稱全資料內容隱私審核6.6。

## 本輪自動檢查
- 主.venv Python -X utf8 -m unittest discover -s tests：452/452，31.016秒。
- node --test "tests/*.test.cjs"：148/148。
- tests/run_web_v2_live.py scripts/capture_v2_demo.cjs：九幕成功，臨時埠58743釋放；使用隔離uv --with pillow組合GIF，不改共享依賴。
- 新探針 prepare／after-recreate均成功，結果在忽略的runtime/role4-delivery-*.json；Docker建置log同在runtime。
- 推送前追蹤檔與outgoing history路徑檢查：私人來源/權重/憑證檔類型0；現有追蹤文字的HF/GitHub/PEM/JWT憑證模式0。素材來源來自公開合成檔，不讀私人標註或原test。

## GitHub驗收
- 已推送既有公開repo [角色4分支](https://github.com/lee851104/receipt/tree/codex/role4-web-foundation)，未更改可見性、main或Pages。
- 受驗產品commit 63abd872adf61bcb39845ad463bf180242e9bb5d；[GitHub CI](https://github.com/lee851104/receipt/actions/runs/39043023447) 的tests與docker兩job均success，含Python/Node測試、映像建置／檔案檢查、Compose啟動／demo名單；沒有真模型下載。
- 匿名GET固定commit的README及6個相對目標（GIF、delivery/integration/concepts/overview、v1預覽圖）均HTTP200且與git blob逐byte相同；第一次比對working-tree因Windows CRLF與Git LF不同失敗，改用正確的git blob比對通過。
- 既有Pages invoice-insights.html HTTP200且與Git blob相同，沒有更新v1。
- CUA未登入GitHub驗證README GIF載入1366×900，點Play後動畫img可見；截圖本聊天visualizations/role4-github-delivery.png。
- 後續只整理README重複啟動段落、補驗收紀錄與任務勾選，不改受驗產品或GIF；最終HEAD／CI在共用交接記錄。

## 限制及審核
角色1當前seed只建40個帳號，不建其品項／profile；實測demo_users=40、seed_profile_ready=false。README已明列，Docker測試另外透過正式上傳建立兩人的虛構資料。角色3完整300人seed及角色2受保護BERT仍未合併到本分支，未下載／公開模型。5.9的展示與使用說明不等於共同6.4的300人／真模型／全新實體電腦驗收；不代勾其他角色任務。
請Claude審核角色4展示、README操作與本輪證據，以及合併後端相依；正式審核由Claude另寫。

本輪專用Compose project已down（不帶-v），容器與network停止，db/models volume留存供覆核；原8000與8001服務未停止。OpenSpec strict、git diff --check及v1邊界檢查通過。角色4 5.1–5.10為10/10，仍待Claude正式審核。
