# 角色2：合成比例交叉驗證
使用者授權現有開發資料比較三種比例，test不讀不評。基準18126bb，限定角色2實驗工具。

設計：train和validation合併真實開發池。5個分層群組外折；每折其餘資料內留約15%真實資料早停。0%、25%、原train的600/905約66.3%合成比例，共用切分及seed42+fold。依實際梯度訓練real筆數決定合成筆數；10類均衡取樣，小集合為大集合子集。各折從公開預訓練BERT重新初始化head，不能使用已見過假資料或開發池的分類權重。

固定AdamW lr2e-5、batch16、FP32、max_length32、weight_decay.01、clip1、最多10epochs、patience2、min_delta1e-4。內層選epoch；外折最後只評一次。5折平均accuracy排序，並列樣本標準差、最差折、OOF macro-F1及低樣本類別、成對差異。平均最高不等於波動最小，不宣稱獨立測試或穩定正確率。合成多會增加每輪步數，本次為資料配方比較而非等計算量實驗。固定每折seed無法涵蓋全部訓練隨機性。

- [ ] 虛構回歸：不讀test、分組隔離、相同外折、比例及子集、損壞拒絕、內層早停和外層單次評分。
- [ ] 實作工具、完整測試、階段commit。
- [ ] 確認GPU資源並順序15次真模型訓練。
- [ ] 彙總圖表、獨立程式複查、最終驗證、commit與交接。

介面：prepare保存train/inner/outer及hash；load_fold核對來源和檔案；train_fold訓練train、inner選epoch、outer評分；summarize_runs要求15run齊全且外折完整覆蓋。只在主資料夾data/role2保存名稱與權重，對外只有彙總。

## 執行紀錄
- 第一階段虛構回歸先確認缺實作而失敗，再實作通過。完整實驗測試84項：83通過、1繪圖環境skip，35.779秒。Windows文字管線初次編碼失敗已改ASCII JSON傳遞；重跑參數不一致的測試已改同epochs驗證，未影響真實資料。
- 建立私人版本bert-ratio-cv-20261016-v1，355real＋600synthetic候選；每折outer71、inner40或41、梯度real243或244。三組synthetic分別0／81／478或480。沒有開啟原test。
- 獨立靜態程式複查未見阻擋缺陷；建議補完整15-run虛構彙總測試，將在真訓練期間完成。本複查不等於Claude審核。
