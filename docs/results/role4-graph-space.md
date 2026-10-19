# 配對圖空間與外置摘要

2026-10-17；工作ID R4-GRAPH-SPACE-20261017；基準 de9066a；待 Claude 審核，未整合／未推送。

依最新回饋取代圖內浮動解讀：圖上方獨立窄摘要，桌面相投／差異兩欄、手機上下。維持原暗色、粉紅標題與綠／橘語意；沒有新增側欄。縮小結果標題與圖例工具列，圖高依面板實際可用高度減去摘要、工具列、返回列及收合計算入口量測，不再固定減170px。

桌面 SVG 概覽改用1700×600，不預留全部品項外圈，增加圖形與字的實際大小。選有品項的訊號時才展開原完整viewBox，取消恢復放大；手機保留原直式圖。分數仍由API供應，光暈／流動與原互動保留。只有外層面板捲動。

修改 src/web_v2/{index.html,styles.css,workspace-ui.js,network.html,network-view.js,network-embed.js,network-layout.css}、tests/web-v2-explanation-browser.cjs、OpenSpec web-app/spec.md、本文件。

## 本輪驗證
- 主 .venv/Scripts/python.exe -X utf8 tests/run_web_v2_live.py tests/web-v2-explanation-browser.cjs tests/web-v2-browser.cjs：2組通過，50648釋放。fake/fake臨時DB；browser含真HTTP註冊上傳及契約替身介面。
- 補上品項展開／取消後，單跑同runner explanation-browser通過，53625釋放。初次響應式檢查在ResizeObserver完成前量測失敗，改等待實際內頁與frame高度吻合後重跑通過。
- 1366×768、1024×640摘要／圖／收合計算入口同屏；字體實際尺寸至少15／11.5px，特質節點橫跨圖寬74%以上，標籤無裁切。390×844、320×568沒有內層溢出；wheel由外層承接。品項展開標籤在viewBox內、取消恢復原viewBox。
- 既有18格精度、負分、資料不足、失敗／401、返回焦點與延遲離頁回應驗證通過；無pageerror。
- node --test "tests/*.test.cjs"：148/148通過。
- CUA原8001虛構帳號桌面與手機檢視，截圖本聊天visualizations/role4-graph-space.png；尺寸覆寫還原，留配對結果。
- OpenSpec strict、git diff --check與v1未變檢查另見交接實際結果。

邊界：未跑Python全套、真模型、Docker、CI；後端／DB／依賴／GPU未改，原8001服務未重啟。點選節點展開詳細文字、窄螢幕或放大文字時允許外層捲動，不犧牲閱讀完整性。Claude下一步審核本輪commit的實際高度量測、展開恢復、手機與摘要可讀性。
